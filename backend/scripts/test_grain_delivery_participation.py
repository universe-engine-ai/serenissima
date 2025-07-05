#!/usr/bin/env python3
"""
Test script to simulate a citizen participating in LuciaMancini's grain delivery stratagem.
Tests the collective_delivery_LuciaMancini_1751720658 stratagem by having a citizen deliver grain.
"""
import os
import sys
import logging
import json
from datetime import datetime, timedelta
import pytz

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def create_delivery_activity(tables, citizen_username, from_building_id, to_building_id, resource_type, amount):
    """Create a delivery activity for testing."""
    
    # Get the resource stack from the source building
    formula = f"AND({{Building}}='{from_building_id}', {{ResourceType}}='{resource_type}')"
    resources = list(tables['resources'].all(formula=formula))
    
    if not resources:
        log.error(f"No {resource_type} found in building {from_building_id}")
        return None
    
    # Use the first available stack
    resource_stack = resources[0]
    stack_amount = resource_stack['fields'].get('Amount', 0)
    
    if stack_amount < amount:
        log.warning(f"Not enough {resource_type} in stack. Available: {stack_amount}, Requested: {amount}")
        amount = stack_amount  # Deliver what we have
    
    # Create delivery manifest
    delivery_manifest = [{
        'stackId': resource_stack['id'],
        'amount': amount
    }]
    
    # Create the activity
    activity_data = {
        'Type': 'deliver_to_storage',
        'Status': 'in_progress',
        'Citizen': citizen_username,
        'FromBuilding': from_building_id,
        'ToBuilding': to_building_id,
        'StartDate': datetime.now(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'EndDate': (datetime.now(pytz.utc) + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'Notes': json.dumps({
            'resource_type': resource_type,
            'amount': amount,
            'delivery_manifest': delivery_manifest
        })
    }
    
    try:
        activity = tables['activities'].create(activity_data)
        log.info(f"Created delivery activity: {activity['id']}")
        return activity
    except Exception as e:
        log.error(f"Error creating activity: {e}")
        return None

def complete_delivery_activity(tables, activity_id):
    """Mark the delivery activity as completed."""
    try:
        tables['activities'].update(activity_id, {
            'Status': 'completed',
            'EndDate': datetime.now(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        })
        log.info(f"Completed delivery activity: {activity_id}")
        return True
    except Exception as e:
        log.error(f"Error completing activity: {e}")
        return False

def check_stratagem_status(tables, stratagem_id):
    """Check the current status of the stratagem."""
    formula = f"{{StratagemId}}='{stratagem_id}'"
    stratagems = list(tables['stratagems'].all(formula=formula))
    
    if not stratagems:
        log.error(f"Stratagem {stratagem_id} not found")
        return None
    
    stratagem = stratagems[0]
    details = json.loads(stratagem['fields'].get('Notes', '{}'))
    
    log.info(f"\nStratagem Status:")
    log.info(f"  ID: {stratagem_id}")
    log.info(f"  Status: {stratagem['fields'].get('Status')}")
    log.info(f"  Collected: {details.get('collected_amount', 0)}/{details.get('max_total_amount', 0)} grain")
    log.info(f"  Participants: {len(details.get('participants', []))}")
    log.info(f"  Total Rewards Paid: {details.get('total_rewards_paid', 0)} ducats")
    
    return stratagem

def main():
    """Test grain delivery participation."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    tables = {
        'stratagems': api.table(base_id, 'STRATAGEMS'),
        'citizens': api.table(base_id, 'CITIZENS'),
        'buildings': api.table(base_id, 'BUILDINGS'),
        'resources': api.table(base_id, 'RESOURCES'),
        'activities': api.table(base_id, 'ACTIVITIES'),
        'notifications': api.table(base_id, 'NOTIFICATIONS')
    }
    
    # The collective delivery stratagem details
    stratagem_id = "collective_delivery_LuciaMancini_1751720658"
    target_building_id = "building_45.43735680581042_12.326245881522368"  # Automated Mill
    resource_type = "grain"
    
    # Check if stratagem exists and is active
    log.info(f"Checking stratagem {stratagem_id}...")
    stratagem = check_stratagem_status(tables, stratagem_id)
    if not stratagem:
        return
    
    if stratagem['fields'].get('Status') != 'active':
        log.error(f"Stratagem is not active. Status: {stratagem['fields'].get('Status')}")
        return
    
    # Find a citizen with grain to deliver
    # Let's use a test citizen or find one with grain
    test_citizen_username = "DesertRanger"  # You can change this to any citizen
    
    # Find a building owned by the test citizen that has grain
    citizen_buildings = list(tables['buildings'].all(
        formula=f"{{RunBy}}='{test_citizen_username}'"
    ))
    
    if not citizen_buildings:
        log.error(f"{test_citizen_username} doesn't own any buildings")
        return
    
    # Check each building for grain
    source_building = None
    for building in citizen_buildings:
        building_id = building['fields'].get('BuildingId')
        grain_formula = f"AND({{Building}}='{building_id}', {{ResourceType}}='grain')"
        grain_resources = list(tables['resources'].all(formula=grain_formula))
        
        if grain_resources and grain_resources[0]['fields'].get('Amount', 0) > 0:
            source_building = building
            log.info(f"Found grain in {building['fields'].get('Name', 'Unknown')} ({building_id})")
            break
    
    if not source_building:
        log.error(f"No grain found in any of {test_citizen_username}'s buildings")
        # Try to find any citizen with grain
        log.info("\nSearching for any citizen with grain...")
        grain_resources = list(tables['resources'].all(
            formula=f"{{ResourceType}}='grain'",
            max_records=10
        ))
        
        for resource in grain_resources:
            building_id = resource['fields'].get('Building')
            owner = resource['fields'].get('Owner')
            amount = resource['fields'].get('Amount', 0)
            
            if building_id and owner and amount > 0:
                log.info(f"Found {amount} grain owned by {owner} in building {building_id}")
                test_citizen_username = owner
                source_building_id = building_id
                break
        else:
            log.error("No grain found anywhere in Venice!")
            return
    else:
        source_building_id = source_building['fields'].get('BuildingId')
    
    # Create a delivery activity
    log.info(f"\nCreating delivery from {source_building_id} to {target_building_id}...")
    
    delivery_amount = 10  # Deliver 10 grain
    activity = create_delivery_activity(
        tables=tables,
        citizen_username=test_citizen_username,
        from_building_id=source_building_id,
        to_building_id=target_building_id,
        resource_type=resource_type,
        amount=delivery_amount
    )
    
    if not activity:
        log.error("Failed to create delivery activity")
        return
    
    # Simulate time passing and complete the delivery
    log.info(f"\nCompleting delivery activity...")
    if complete_delivery_activity(tables, activity['id']):
        log.info(f"✅ {test_citizen_username} delivered {delivery_amount} grain to the Automated Mill")
    else:
        log.error("Failed to complete delivery")
        return
    
    # Now run the stratagem processor to see if it picks up the delivery
    log.info(f"\nRunning stratagem processor...")
    os.system(f"cd {PROJECT_ROOT} && python backend/engine/processStratagems.py --stratagem-id {stratagem_id}")
    
    # Check the stratagem status again
    log.info(f"\nChecking stratagem status after processing...")
    stratagem = check_stratagem_status(tables, stratagem_id)
    
    # Check if the citizen received a reward
    citizen_records = list(tables['citizens'].all(formula=f"{{Username}}='{test_citizen_username}'"))
    if citizen_records:
        citizen = citizen_records[0]
        log.info(f"\n{test_citizen_username}'s ducats: {citizen['fields'].get('Ducats', 0)}")

if __name__ == "__main__":
    main()
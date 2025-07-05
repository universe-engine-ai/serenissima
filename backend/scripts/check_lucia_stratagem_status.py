#!/usr/bin/env python3
"""
Check the status of LuciaMancini's collective grain delivery stratagem.
"""
import os
import sys
import logging
import json
from datetime import datetime
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

def check_stratagem_details(tables, stratagem_id):
    """Check detailed status of the stratagem."""
    formula = f"{{StratagemId}}='{stratagem_id}'"
    stratagems = list(tables['stratagems'].all(formula=formula))
    
    if not stratagems:
        log.error(f"Stratagem {stratagem_id} not found")
        return None
    
    stratagem = stratagems[0]
    details = json.loads(stratagem['fields'].get('Notes', '{}'))
    
    log.info(f"\n{'='*60}")
    log.info(f"STRATAGEM STATUS: {stratagem['fields'].get('Name', 'Unknown')}")
    log.info(f"{'='*60}")
    
    log.info(f"\nBasic Info:")
    log.info(f"  ID: {stratagem_id}")
    log.info(f"  Type: {stratagem['fields'].get('Type')}")
    log.info(f"  Status: {stratagem['fields'].get('Status')}")
    log.info(f"  Category: {stratagem['fields'].get('Category')}")
    log.info(f"  Executed By: {stratagem['fields'].get('ExecutedBy')}")
    log.info(f"  Description: {stratagem['fields'].get('Description')}")
    
    executed_at = stratagem['fields'].get('ExecutedAt')
    expires_at = stratagem['fields'].get('ExpiresAt')
    if executed_at:
        log.info(f"  Started: {executed_at}")
    if expires_at:
        log.info(f"  Expires: {expires_at}")
        # Check if expired
        expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if datetime.now(pytz.utc) > expires_dt:
            log.warning(f"  ⚠️  STRATAGEM HAS EXPIRED!")
    
    log.info(f"\nDelivery Progress:")
    log.info(f"  Resource Type: {details.get('resource_type', 'Unknown')}")
    log.info(f"  Collected: {details.get('collected_amount', 0)} / {details.get('max_total_amount', 0)} units")
    progress = (details.get('collected_amount', 0) / details.get('max_total_amount', 1)) * 100
    log.info(f"  Progress: {progress:.1f}%")
    
    log.info(f"\nReward Info:")
    log.info(f"  Reward per unit: {details.get('reward_per_unit', 0)} ducats")
    log.info(f"  Total rewards paid: {details.get('total_rewards_paid', 0)} ducats")
    log.info(f"  Escrow remaining: {details.get('escrow_ducats', 0) - details.get('total_rewards_paid', 0)} ducats")
    
    log.info(f"\nTarget Details:")
    target = details.get('target', {})
    if target.get('mode') == 'building':
        log.info(f"  Mode: Building delivery")
        log.info(f"  Building: {target.get('building_name', 'Unknown')} ({target.get('building_id')})")
        log.info(f"  Building Type: {target.get('building_type')}")
        log.info(f"  Run By: {target.get('run_by')}")
    
    log.info(f"\nParticipation:")
    participants = details.get('participants', [])
    log.info(f"  Total participants: {len(participants)}")
    
    if participants:
        log.info(f"\n  Top Contributors:")
        # Sort by amount delivered
        sorted_participants = sorted(participants, key=lambda p: p.get('amount_delivered', 0), reverse=True)
        for i, participant in enumerate(sorted_participants[:5]):  # Top 5
            log.info(f"    {i+1}. {participant['username']}: {participant['amount_delivered']} units, {participant['reward_earned']} ducats earned")
    
    deliveries = details.get('deliveries', [])
    log.info(f"\n  Total deliveries: {len(deliveries)}")
    
    return stratagem

def check_recent_deliveries(tables, building_id, hours=1):
    """Check recent deliveries to the target building."""
    from datetime import timedelta
    
    one_hour_ago = datetime.now(pytz.utc) - timedelta(hours=hours)
    
    formula = (
        f"AND("
        f"  {{Type}}='deliver_to_storage',"
        f"  {{ToBuilding}}='{building_id}',"
        f"  IS_AFTER({{EndDate}}, '{one_hour_ago.isoformat()}')"
        f")"
    )
    
    deliveries = list(tables['activities'].all(formula=formula))
    
    log.info(f"\n{'='*60}")
    log.info(f"RECENT DELIVERIES TO AUTOMATED MILL (last {hours} hour(s))")
    log.info(f"{'='*60}")
    
    if not deliveries:
        log.info(f"No deliveries found in the last {hours} hour(s)")
        return
    
    for delivery in deliveries:
        citizen = delivery['fields'].get('Citizen')
        status = delivery['fields'].get('Status')
        start_date = delivery['fields'].get('StartDate')
        end_date = delivery['fields'].get('EndDate')
        
        # Try to parse notes for details
        try:
            notes = json.loads(delivery['fields'].get('Notes', '{}'))
            resource_type = notes.get('resource_type', 'Unknown')
            amount = notes.get('amount', 0)
            details_str = f"{amount} {resource_type}"
        except:
            details_str = "Unknown contents"
        
        log.info(f"\n  Activity: {delivery['id']}")
        log.info(f"    Citizen: {citizen}")
        log.info(f"    Status: {status}")
        log.info(f"    Contents: {details_str}")
        log.info(f"    Started: {start_date}")
        log.info(f"    Ended: {end_date}")

def check_grain_availability(tables, limit=10):
    """Check who has grain available in Venice."""
    log.info(f"\n{'='*60}")
    log.info(f"GRAIN AVAILABILITY IN VENICE")
    log.info(f"{'='*60}")
    
    # Find grain resources
    grain_resources = list(tables['resources'].all(
        formula=f"AND({{ResourceType}}='grain', {{Amount}}>0)",
        max_records=limit
    ))
    
    if not grain_resources:
        log.error("No grain found in Venice!")
        return
    
    total_grain = sum(r['fields'].get('Amount', 0) for r in grain_resources)
    log.info(f"\nTotal grain stacks found: {len(grain_resources)}")
    log.info(f"Total grain amount: {total_grain} units")
    
    log.info(f"\nTop grain holders:")
    for resource in grain_resources[:10]:
        owner = resource['fields'].get('Owner', 'Unknown')
        amount = resource['fields'].get('Amount', 0)
        building_id = resource['fields'].get('Building', 'Unknown')
        
        # Try to get building name
        building_name = "Unknown"
        if building_id and building_id != 'Unknown':
            try:
                building = tables['buildings'].get(building_id.replace('building_', 'rec'))
                building_name = building['fields'].get('Name', 'Unknown')
            except:
                pass
        
        log.info(f"  {owner}: {amount} grain in {building_name} ({building_id})")

def main():
    """Check LuciaMancini's collective delivery stratagem status."""
    
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
        'activities': api.table(base_id, 'ACTIVITIES')
    }
    
    # The stratagem details
    stratagem_id = "collective_delivery_LuciaMancini_1751720658"
    target_building_id = "building_45.43735680581042_12.326245881522368"  # Automated Mill
    
    # Check stratagem status
    stratagem = check_stratagem_details(tables, stratagem_id)
    
    if stratagem:
        # Check recent deliveries to the mill
        check_recent_deliveries(tables, target_building_id, hours=24)
        
        # Check grain availability
        check_grain_availability(tables)

if __name__ == "__main__":
    main()
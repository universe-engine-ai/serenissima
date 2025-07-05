#!/usr/bin/env python3
"""
Simple paper delivery simulation by directly manipulating resources.
"""
import os
import sys
import json
from datetime import datetime
import pytz

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Simulate paper delivery by directly moving resources."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    resources_table = api.table(base_id, 'RESOURCES')
    activities_table = api.table(base_id, 'ACTIVITIES')
    citizens_table = api.table(base_id, 'CITIZENS')
    stratagems_table = api.table(base_id, 'STRATAGEMS')
    
    # Find TechnoMedici's paper
    papers = list(resources_table.all(
        formula="AND({Type}='paper', {Owner}='TechnoMedici')"
    ))
    
    if not papers:
        print("TechnoMedici has no paper!")
        return
    
    paper = papers[0]
    paper_id = paper['id']
    paper_count = paper['fields'].get('Count', 0)
    source_building = paper['fields'].get('Asset')
    
    print(f"\\nFound {paper_count} paper at building {source_building}")
    
    # Target building (printing house)
    target_building_id = "building_45.44656355360805_12.320326403648886"
    
    # Simulate delivery of 10 paper
    delivery_amount = min(10, paper_count)
    
    print(f"\\nSimulating delivery of {delivery_amount} paper to printing house...")
    
    # Create a fake completed delivery activity for the stratagem processor to find
    delivery_time = datetime.now(pytz.utc)
    
    activity_data = {
        'ActivityId': f"deliver_paper_test_{int(delivery_time.timestamp())}",
        'Type': 'deliver_to_storage',
        'Status': 'completed',
        'Citizen': 'TechnoMedici',
        'Title': f"Deliver {delivery_amount} paper to Printing House",
        'Description': f"Collective delivery of paper for stratagem",
        'FromBuilding': source_building,
        'ToBuilding': target_building_id,
        'EndDate': delivery_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'Notes': json.dumps({
            'collective_delivery': True,
            'stratagem_id': 'collective_delivery_ConsiglioDeiDieci_1751670639',
            'resource_type': 'paper',
            'amount': delivery_amount,
            'delivery_manifest': [{
                'stackId': paper_id,
                'type': 'paper',
                'amount': delivery_amount
            }]
        })
    }
    
    try:
        # Create the activity record
        activity = activities_table.create(activity_data)
        print(f"✅ Created delivery activity record: {activity['id']}")
        
        # Move the paper to the printing house
        if paper_count > delivery_amount:
            # Update existing stack count
            resources_table.update(paper_id, {
                'Count': paper_count - delivery_amount
            })
            
            # Create new stack at printing house
            new_stack = resources_table.create({
                'ResourceId': f"paper_delivered_{int(delivery_time.timestamp())}",
                'Type': 'paper',
                'Name': 'Paper',
                'Asset': target_building_id,
                'AssetType': 'building',
                'Owner': 'TechnoMedici',  # Will be updated by stratagem processor
                'Count': delivery_amount
            })
            print(f"✅ Created paper stack at printing house: {new_stack['id']}")
        else:
            # Move entire stack
            resources_table.update(paper_id, {
                'Asset': target_building_id,
                'AssetType': 'building'
            })
            print(f"✅ Moved entire paper stack to printing house")
        
        print(f"\\nDelivery complete! TechnoMedici delivered {delivery_amount} paper.")
        print(f"The stratagem processor should detect this and pay the reward.")
        
        # Check active stratagems
        active_stratagems = list(stratagems_table.all(
            formula="AND({Type}='organize_collective_delivery', {Status}='active')"
        ))
        
        if active_stratagems:
            print(f"\\nActive collective delivery stratagems: {len(active_stratagems)}")
            for s in active_stratagems:
                print(f"- {s['fields'].get('Name')} (expires {s['fields'].get('ExpiresAt')})")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
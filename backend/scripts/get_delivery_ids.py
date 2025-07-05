#!/usr/bin/env python3
"""
Get the IDs of all delivery activities tracked by the stratagem.
"""
import os
import sys
import json

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Get delivery activity IDs from the stratagem."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    stratagems_table = api.table(base_id, 'STRATAGEMS')
    activities_table = api.table(base_id, 'ACTIVITIES')
    
    # Get the paper delivery stratagem
    stratagems = list(stratagems_table.all(
        formula="{StratagemId}='collective_delivery_ConsiglioDeiDieci_1751670639'"
    ))
    
    if not stratagems:
        print("Stratagem not found!")
        return
    
    stratagem = stratagems[0]
    notes = stratagem['fields'].get('Notes', '{}')
    
    try:
        details = json.loads(notes)
        delivery_ids = details.get('deliveries', [])
        
        print(f"\nDelivery Activity IDs tracked by the stratagem:")
        print(f"Total deliveries: {len(delivery_ids)}")
        print("\nActivity IDs:")
        
        for i, activity_id in enumerate(delivery_ids, 1):
            print(f"{i}. {activity_id}")
            
            # Get details about each activity
            activity_records = list(activities_table.all(
                formula=f"RECORD_ID()='{activity_id}'"
            ))
            
            if activity_records:
                activity = activity_records[0]['fields']
                notes_str = activity.get('Notes', '{}')
                try:
                    activity_notes = json.loads(notes_str)
                    amount = activity_notes.get('amount', 'unknown')
                    print(f"   - Citizen: {activity.get('Citizen')}")
                    print(f"   - Amount: {amount} paper")
                    print(f"   - Custom ID: {activity.get('ActivityId')}")
                    print(f"   - Status: {activity.get('Status')}")
                    print(f"   - EndDate: {activity.get('EndDate')}")
                except:
                    print(f"   - Could not parse activity notes")
            else:
                print(f"   - Activity record not found")
            print()
            
    except Exception as e:
        print(f"Could not parse stratagem details: {e}")

if __name__ == "__main__":
    main()
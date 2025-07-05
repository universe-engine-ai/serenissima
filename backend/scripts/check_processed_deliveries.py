#!/usr/bin/env python3
"""
Check which deliveries were actually processed by the stratagem.
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
    """Check processed deliveries from stratagem details."""
    
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
        
        print(f"\nStratagem ID: collective_delivery_ConsiglioDeiDieci_1751670639")
        print(f"Status: {stratagem['fields'].get('Status')}")
        print(f"Total collected: {details.get('collected_amount')} paper")
        print(f"Total rewards paid: {details.get('total_rewards_paid')} ducats")
        
        print(f"\nProcessed delivery activity IDs:")
        delivery_ids = details.get('deliveries', [])
        print(f"Count: {len(delivery_ids)}")
        
        for activity_id in delivery_ids:
            print(f"\n- Airtable Record ID: {activity_id}")
        
        print(f"\nParticipants:")
        participants = details.get('participants', [])
        for p in participants:
            print(f"\n- Username: {p['username']}")
            print(f"  Amount delivered: {p['amount_delivered']} paper")
            print(f"  Number of deliveries: {p['deliveries']}")
            print(f"  Reward earned: {p['reward_earned']} ducats")
            
    except Exception as e:
        print(f"Could not parse stratagem details: {e}")

if __name__ == "__main__":
    main()
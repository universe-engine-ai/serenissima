#!/usr/bin/env python3
"""
Check the status of the collective delivery stratagem.
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
    """Check stratagem status."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    stratagems_table = api.table(base_id, 'STRATAGEMS')
    
    # Find collective delivery stratagems
    active_stratagems = list(stratagems_table.all(
        formula="{Type}='organize_collective_delivery'"
    ))
    
    print(f"\nFound {len(active_stratagems)} organize_collective_delivery stratagems:\n")
    
    for stratagem in active_stratagems:
        fields = stratagem['fields']
        print(f"Stratagem ID: {fields.get('StratagemId')}")
        print(f"Status: {fields.get('Status')}")
        print(f"Executed By: {fields.get('ExecutedBy')}")
        print(f"Name: {fields.get('Name')}")
        print(f"Description: {fields.get('Description')}")
        print(f"Expires At: {fields.get('ExpiresAt')}")
        
        # Parse details from Notes
        notes = fields.get('Notes', '{}')
        try:
            details = json.loads(notes)
            print(f"Target Building: {details.get('target', {}).get('building_id')}")
            print(f"Target Building Name: {details.get('target', {}).get('building_name')}")
            print(f"Resource Type: {details.get('resource_type')}")
            print(f"Max Amount: {details.get('max_total_amount')}")
            print(f"Collected: {details.get('collected_amount')}")
            print(f"Reward per Unit: {details.get('reward_per_unit')} ducats")
            print(f"Participants: {len(details.get('participants', []))}")
            print(f"Deliveries: {len(details.get('deliveries', []))}")
        except:
            print("Could not parse details from Notes")
        
        print("-" * 50)

if __name__ == "__main__":
    main()
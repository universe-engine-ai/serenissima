#!/usr/bin/env python3
"""
Reset the status of delivery activities to 'created' so they can be processed.
"""
import os
import sys

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Reset activity status."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    activities_table = api.table(base_id, 'ACTIVITIES')
    
    # Update the specific activities
    activity_ids = ['deliver_paper_test_1751671157', 'deliver_paper_test_1751671120']
    
    for activity_id in activity_ids:
        formula = f"{{ActivityId}}='{activity_id}'"
        records = list(activities_table.all(formula=formula))
        
        if records:
            record = records[0]
            print(f"\nUpdating {activity_id}...")
            print(f"Current status: {record['fields'].get('Status')}")
            
            # Update to 'created' status
            activities_table.update(record['id'], {
                'Status': 'created'
            })
            
            print(f"✅ Updated to 'created' status")
        else:
            print(f"\n❌ Activity {activity_id} not found")

if __name__ == "__main__":
    main()
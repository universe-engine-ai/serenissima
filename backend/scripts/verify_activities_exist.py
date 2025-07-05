#!/usr/bin/env python3
"""
Verify if the activity records actually exist in Airtable.
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
    """Check if specific activity records exist."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    activities_table = api.table(base_id, 'ACTIVITIES')
    
    # Try to find the specific records
    record_ids = ['recAYs8gVMKLA8ca3', 'recyq3YGjY9wVITSf']
    
    print("Checking for specific record IDs...")
    for record_id in record_ids:
        try:
            record = activities_table.get(record_id)
            print(f"\n✅ Found record {record_id}")
            print(f"   Activity ID: {record['fields'].get('ActivityId')}")
            print(f"   Type: {record['fields'].get('Type')}")
            print(f"   Status: {record['fields'].get('Status')}")
        except Exception as e:
            print(f"\n❌ Record {record_id} NOT FOUND: {e}")
    
    # Also search by ActivityId
    print("\n\nSearching by ActivityId...")
    activity_ids = ['deliver_paper_test_1751671157', 'deliver_paper_test_1751671120']
    
    for activity_id in activity_ids:
        formula = f"{{ActivityId}}='{activity_id}'"
        records = list(activities_table.all(formula=formula))
        
        if records:
            print(f"\n✅ Found by ActivityId: {activity_id}")
            for record in records:
                print(f"   Record ID: {record['id']}")
                print(f"   Type: {record['fields'].get('Type')}")
                print(f"   Status: {record['fields'].get('Status')}")
                print(f"   Citizen: {record['fields'].get('Citizen')}")
        else:
            print(f"\n❌ No records found with ActivityId: {activity_id}")
    
    # List recent activities
    print("\n\nRecent activities (last 10):")
    all_activities = list(activities_table.all(max_records=10, sort=['-CreatedAt']))
    
    for activity in all_activities:
        fields = activity['fields']
        print(f"\n- Record ID: {activity['id']}")
        print(f"  ActivityId: {fields.get('ActivityId')}")
        print(f"  Type: {fields.get('Type')}")
        print(f"  Citizen: {fields.get('Citizen')}")
        print(f"  Status: {fields.get('Status')}")

if __name__ == "__main__":
    main()
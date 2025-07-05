#!/usr/bin/env python3
"""
Check for grievance-related activities
"""
import os
import sys
from pyairtable import Api
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
api_key = os.environ.get('AIRTABLE_API_KEY')
base_id = os.environ.get('AIRTABLE_BASE_ID')

api = Api(api_key)
activities_table = api.table(base_id, 'ACTIVITIES')

# Check for any grievance-related activities
print('Checking for grievance activities...')
try:
    grievance_activities = activities_table.all(
        formula="OR({Type}='file_grievance', {Type}='support_grievance')",
        max_records=20
    )
    
    print(f'\nFound {len(grievance_activities)} grievance-related activities')
    
    if grievance_activities:
        for act in grievance_activities:
            fields = act['fields']
            print(f"\n- {fields.get('Type')} by {fields.get('Citizen')}")
            print(f"  Status: {fields.get('Status')}")
            print(f"  Created: {fields.get('CreatedDate', 'Unknown')}")
            print(f"  End Date: {fields.get('EndDate', 'Unknown')}")
    else:
        print("\nNo grievance activities found. AI citizens may not be creating them yet.")
        
except Exception as e:
    print(f"Error: {e}")

# Check if any citizens are in leisure time right now
print("\n\nChecking leisure time activities...")
try:
    leisure_activities = activities_table.all(
        formula="AND({Status}='in_progress', OR({Type}='drink_at_inn', {Type}='attend_theater', {Type}='read_book'))",
        max_records=5
    )
    
    print(f"Found {len(leisure_activities)} citizens currently in leisure activities")
    if leisure_activities:
        print("These citizens might be able to file grievances next.")
        
except Exception as e:
    print(f"Error checking leisure: {e}")
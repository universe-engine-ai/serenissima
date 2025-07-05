#!/usr/bin/env python3
"""
Test filing a grievance through the activity system
"""
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pyairtable import Api
from dotenv import load_dotenv
from backend.engine.activity_creators.file_grievance_activity_creator import try_create_file_grievance_activity

load_dotenv()

api_key = os.environ.get('AIRTABLE_API_KEY')
base_id = os.environ.get('AIRTABLE_BASE_ID')

if not api_key or not base_id:
    print("Missing Airtable credentials")
    sys.exit(1)

api = Api(api_key)

# Initialize tables
tables = {
    'citizens': api.table(base_id, 'CITIZENS'),
    'activities': api.table(base_id, 'ACTIVITIES'),
    'buildings': api.table(base_id, 'BUILDINGS'),
    'grievances': api.table(base_id, 'GRIEVANCES'),
    'grievance_support': api.table(base_id, 'GRIEVANCE_SUPPORT')
}

# Find a wealthy citizen to file a grievance
print("Finding a suitable citizen to file grievance...")
citizens = tables['citizens'].all(formula="{Ducats} > 100")
if not citizens:
    print("No wealthy citizens found")
    sys.exit(1)

# Pick the first wealthy citizen
citizen = citizens[0]
citizen_fields = citizen['fields']
citizen_username = citizen_fields.get('Username')
citizen_id = citizen_fields.get('CitizenId')
citizen_airtable_id = citizen['id']

print(f"\nSelected citizen: {citizen_username}")
print(f"  Wealth: {citizen_fields.get('Ducats', 0)} ducats")
print(f"  Social Class: {citizen_fields.get('SocialClass', 'Unknown')}")

# Create a file_grievance activity
print("\nCreating file_grievance activity...")

current_time = datetime.now(timezone.utc)

result = try_create_file_grievance_activity(
    tables=tables,
    citizen_custom_id=citizen_id,
    citizen_username=citizen_username,
    citizen_airtable_id=citizen_airtable_id,
    citizen_social_class=citizen_fields.get('SocialClass', 'Popolani'),
    grievance_category='economic',
    grievance_title='High Taxes Crushing Small Merchants',
    grievance_description='The recent tax increases have made it impossible for small merchants to compete. We need relief!',
    filing_fee=50,
    current_time_utc=current_time
)

if result:
    print("✅ Successfully created file_grievance activity!")
    print(f"   Activity ID: {result.get('id', 'Unknown')}")
    print(f"   Status: {result['fields'].get('Status', 'Unknown')}")
    print(f"   End Date: {result['fields'].get('EndDate', 'Unknown')}")
else:
    print("❌ Failed to create file_grievance activity")

# Check if grievance was created
print("\n\nChecking grievances table...")
grievances = tables['grievances'].all(formula=f"{{Citizen}} = '{citizen_username}'")
print(f"Found {len(grievances)} grievances filed by {citizen_username}")

for g in grievances:
    fields = g['fields']
    print(f"\n  Title: {fields.get('Title', 'Unknown')}")
    print(f"  Status: {fields.get('Status', 'Unknown')}")
    print(f"  Filed At: {fields.get('FiledAt', 'Unknown')}")
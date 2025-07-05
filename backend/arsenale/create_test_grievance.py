#!/usr/bin/env python3
"""
Create a test grievance directly in Airtable
"""
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Api
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('AIRTABLE_API_KEY')
base_id = os.environ.get('AIRTABLE_BASE_ID')

if not api_key or not base_id:
    print("Missing Airtable credentials")
    sys.exit(1)

api = Api(api_key)
grievances_table = api.table(base_id, 'GRIEVANCES')

# Create a test grievance
grievance_data = {
    'Citizen': 'TestCitizen',
    'Category': 'economic',
    'Title': 'Test Grievance - High Market Taxes',
    'Description': 'The taxes in the Rialto market have become unbearable. Small merchants cannot survive!',
    'Status': 'filed',
    'SupportCount': 0,
    'FiledAt': datetime.now(timezone.utc).isoformat()
}

print("Creating test grievance...")
try:
    record = grievances_table.create(grievance_data)
    print(f"✅ Successfully created grievance!")
    print(f"   ID: {record['id']}")
    print(f"   Title: {record['fields'].get('Title')}")
    print(f"   Status: {record['fields'].get('Status')}")
except Exception as e:
    print(f"❌ Failed to create grievance: {e}")

# List all grievances
print("\n\nAll grievances in system:")
print("="*60)
grievances = grievances_table.all()
for i, g in enumerate(grievances):
    fields = g['fields']
    print(f"\n{i+1}. {fields.get('Title', 'No title')}")
    print(f"   By: {fields.get('Citizen', 'Unknown')}")
    print(f"   Category: {fields.get('Category', 'Unknown')}")
    print(f"   Support: {fields.get('SupportCount', 0)}")
    print(f"   Status: {fields.get('Status', 'Unknown')}")
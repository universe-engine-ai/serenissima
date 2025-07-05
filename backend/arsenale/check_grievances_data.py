#!/usr/bin/env python3
"""
Check grievances data in Airtable
"""
import os
import sys
from datetime import datetime

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

# Check GRIEVANCES table
print("=== GRIEVANCES Table ===")
grievances_table = api.table(base_id, 'GRIEVANCES')
grievances = grievances_table.all()

print(f"Total grievances: {len(grievances)}")

if grievances:
    print("\nGrievances:")
    for i, record in enumerate(grievances[:5]):  # Show first 5
        fields = record['fields']
        print(f"\n{i+1}. ID: {record['id']}")
        print(f"   Citizen: {fields.get('Citizen', 'Unknown')}")
        print(f"   Title: {fields.get('Title', 'No title')}")
        print(f"   Category: {fields.get('Category', 'Unknown')}")
        print(f"   Status: {fields.get('Status', 'Unknown')}")
        print(f"   Support Count: {fields.get('SupportCount', 0)}")
        print(f"   Filed At: {fields.get('FiledAt', 'Unknown')}")
        print(f"   Description: {fields.get('Description', 'No description')[:100]}...")

# Check GRIEVANCE_SUPPORT table
print("\n\n=== GRIEVANCE_SUPPORT Table ===")
support_table = api.table(base_id, 'GRIEVANCE_SUPPORT')
supports = support_table.all()

print(f"Total support records: {len(supports)}")

if supports:
    print("\nSupport records:")
    for i, record in enumerate(supports[:5]):  # Show first 5
        fields = record['fields']
        print(f"\n{i+1}. ID: {record['id']}")
        print(f"   Citizen: {fields.get('Citizen', 'Unknown')}")
        print(f"   Grievance ID: {fields.get('GrievanceId', 'Unknown')}")
        print(f"   Amount: {fields.get('Amount', 0)}")
        print(f"   Supported At: {fields.get('SupportedAt', 'Unknown')}")
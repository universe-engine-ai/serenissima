#!/usr/bin/env python3
"""
Check if our delivery activity exists and can be found.
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
from datetime import datetime, timedelta
import pytz

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Check delivery activities."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    activities_table = api.table(base_id, 'ACTIVITIES')
    
    # Look for deliver_to_storage activities to the printing house
    target_building = "building_45.44656355360805_12.320326403648886"
    
    # Find all deliveries to printing house
    formula = f"AND({{Type}}='deliver_to_storage', {{ToBuilding}}='{target_building}')"
    
    deliveries = list(activities_table.all(formula=formula))
    
    print(f"\\nFound {len(deliveries)} deliveries to printing house")
    
    for delivery in deliveries:
        fields = delivery['fields']
        print(f"\\nActivity ID: {fields.get('ActivityId')}")
        print(f"Status: {fields.get('Status')}")
        print(f"Citizen: {fields.get('Citizen')}")
        print(f"EndDate: {fields.get('EndDate')}")
        
        # Check notes for paper deliveries
        notes = fields.get('Notes')
        if notes:
            try:
                notes_data = json.loads(notes)
                if notes_data.get('resource_type') == 'paper':
                    print(f"✅ This is a PAPER delivery!")
                    print(f"Amount: {notes_data.get('amount')}")
                    print(f"Stratagem ID: {notes_data.get('stratagem_id')}")
                    print(f"Collective delivery: {notes_data.get('collective_delivery')}")
            except:
                pass
    
    # Also check recent completed deliver_to_storage activities
    print("\\n" + "="*50)
    print("Recent completed deliver_to_storage activities:")
    
    one_hour_ago = datetime.now(pytz.utc) - timedelta(hours=1)
    formula2 = (
        f"AND("
        f"  {{Type}}='deliver_to_storage',"
        f"  {{Status}}='completed',"
        f"  IS_AFTER({{EndDate}}, '{one_hour_ago.isoformat()}')"
        f")"
    )
    
    recent_deliveries = list(activities_table.all(formula=formula2))
    print(f"\\nFound {len(recent_deliveries)} recent completed deliveries")
    
    for delivery in recent_deliveries:
        fields = delivery['fields']
        print(f"\\nTo: {fields.get('ToBuilding')}")
        print(f"Citizen: {fields.get('Citizen')}")
        print(f"EndDate: {fields.get('EndDate')}")

if __name__ == "__main__":
    main()
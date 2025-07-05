#!/usr/bin/env python3
"""
List all paper delivery activities to the printing house.
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
    """List all paper deliveries."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    activities_table = api.table(base_id, 'ACTIVITIES')
    
    # Find all deliveries to printing house
    target_building = "building_45.44656355360805_12.320326403648886"
    formula = f"AND({{Type}}='deliver_to_storage', {{ToBuilding}}='{target_building}')"
    
    deliveries = list(activities_table.all(formula=formula))
    
    print(f"\nAll paper deliveries to the printing house:")
    print(f"Total found: {len(deliveries)}")
    print("\nDetails:")
    
    paper_deliveries = []
    
    for delivery in deliveries:
        fields = delivery['fields']
        notes = fields.get('Notes')
        
        # Always show the delivery info
        print(f"\nActivity Record ID: {delivery['id']}")
        print(f"Activity ID: {fields.get('ActivityId')}")
        print(f"Status: {fields.get('Status')}")
        print(f"Citizen: {fields.get('Citizen')}")
        print(f"Notes field content: {notes[:200] if notes else 'None'}")
        
        if notes:
            try:
                notes_data = json.loads(notes)
                if notes_data.get('resource_type') == 'paper':
                    paper_deliveries.append({
                        'airtable_id': delivery['id'],
                        'activity_id': fields.get('ActivityId'),
                        'citizen': fields.get('Citizen'),
                        'amount': notes_data.get('amount'),
                        'end_date': fields.get('EndDate'),
                        'stratagem_id': notes_data.get('stratagem_id')
                    })
            except Exception as e:
                print(f"Error parsing notes: {e}")
    
    print(f"\nPaper deliveries: {len(paper_deliveries)}")
    
    for i, delivery in enumerate(paper_deliveries, 1):
        print(f"\n{i}. Airtable Record ID: {delivery['airtable_id']}")
        print(f"   Custom Activity ID: {delivery['activity_id']}")
        print(f"   Citizen: {delivery['citizen']}")
        print(f"   Amount: {delivery['amount']} paper")
        print(f"   Completed: {delivery['end_date']}")
        print(f"   For Stratagem: {delivery['stratagem_id']}")
    
    # Summary by citizen
    print("\n" + "="*50)
    print("Summary by citizen:")
    from collections import defaultdict
    by_citizen = defaultdict(lambda: {'count': 0, 'total': 0})
    
    for delivery in paper_deliveries:
        citizen = delivery['citizen']
        by_citizen[citizen]['count'] += 1
        by_citizen[citizen]['total'] += delivery['amount']
    
    for citizen, data in by_citizen.items():
        print(f"\n{citizen}:")
        print(f"  - Deliveries: {data['count']}")
        print(f"  - Total paper: {data['total']} units")

if __name__ == "__main__":
    main()
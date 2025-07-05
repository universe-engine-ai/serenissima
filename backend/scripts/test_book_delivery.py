#!/usr/bin/env python3
"""
Test creating a deliver_to_storage activity to the printing house.
"""
import os
import sys
import json
import requests

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Find a citizen with books and create a delivery activity."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    resources_table = api.table(base_id, 'RESOURCES')
    citizens_table = api.table(base_id, 'CITIZENS')
    
    # Find citizens with books
    books = list(resources_table.all(
        formula="AND({Type}='book', {AssetType}='citizen', {Count}>0)"
    ))
    
    print(f"\nFound {len(books)} book stacks held by citizens")
    
    if not books:
        print("No citizens have books to deliver!")
        return
    
    # Pick the first citizen with books
    book_stack = books[0]
    citizen_username = book_stack['fields'].get('Asset')
    book_count = book_stack['fields'].get('Count', 0)
    
    print(f"\n{citizen_username} has {book_count} books")
    
    # Get citizen record
    citizen_records = list(citizens_table.all(
        formula=f"{{Username}}='{citizen_username}'"
    ))
    
    if not citizen_records:
        print(f"Could not find citizen {citizen_username}")
        return
    
    citizen = citizen_records[0]['fields']
    position = json.loads(citizen.get('Position', '{}'))
    
    print(f"Citizen position: {position}")
    print(f"Citizen ducats: {citizen.get('Ducats', 0)}")
    
    # Create deliver_to_storage activity
    target_building_id = "building_45.44656355360805_12.320326403648886"
    
    # Prepare activity request
    activity_data = {
        "type": "deliver_to_storage",
        "citizen": citizen_username,
        "startPosition": position,
        "parameters": {
            "target_building_id": target_building_id,
            "resource_type": "book",
            "amount": min(5, book_count),  # Deliver up to 5 books
            "notes": json.dumps({
                "collective_delivery": True,
                "stratagem_id": "collective_delivery_ConsiglioDeiDieci_1751670502",
                "resource_type": "book",
                "amount": min(5, book_count)
            })
        }
    }
    
    print(f"\nCreating delivery activity for {citizen_username} to deliver {activity_data['parameters']['amount']} books...")
    
    # Make request to local API
    response = requests.post(
        "http://localhost:10000/api/activities/try-create",
        json=activity_data
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"✅ Successfully created delivery activity!")
            print(f"Activity ID: {result.get('activity', {}).get('id')}")
        else:
            print(f"❌ Failed to create activity: {result.get('message')}")
    else:
        print(f"❌ API request failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    main()
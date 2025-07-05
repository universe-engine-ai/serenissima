#!/usr/bin/env python3
"""
Test creating a deliver_to_storage activity for paper to the printing house.
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
    """Create a paper delivery from TechnoMedici who has 18 paper."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    resources_table = api.table(base_id, 'RESOURCES')
    citizens_table = api.table(base_id, 'CITIZENS')
    buildings_table = api.table(base_id, 'BUILDINGS')
    
    # Find TechnoMedici's paper
    papers = list(resources_table.all(
        formula="AND({Type}='paper', {Owner}='TechnoMedici')"
    ))
    
    if not papers:
        print("TechnoMedici has no paper!")
        return
    
    # Get the building where the paper is stored
    paper = papers[0]['fields']
    building_id = paper.get('Asset')
    paper_count = paper.get('Count', 0)
    
    print(f"\\nFound {paper_count} paper at building {building_id}")
    
    # Get TechnoMedici's position
    citizen_records = list(citizens_table.all(
        formula="{Username}='TechnoMedici'"
    ))
    
    if not citizen_records:
        print("Could not find TechnoMedici")
        return
    
    citizen = citizen_records[0]['fields']
    position = json.loads(citizen.get('Position', '{}'))
    
    print(f"TechnoMedici position: {position}")
    print(f"TechnoMedici ducats: {citizen.get('Ducats', 0)}")
    
    # First, TechnoMedici needs to pick up the paper from the building
    print("\\nStep 1: Creating fetch_from_storage activity...")
    
    fetch_data = {
        "citizenUsername": "TechnoMedici",
        "activityType": "fetch_from_storage",
        "activityDetails": {
            "source_building_id": building_id,
            "resource_type": "paper",
            "amount": min(10, paper_count)  # Fetch up to 10 paper
        }
    }
    
    response = requests.post(
        "http://localhost:3000/api/activities/try-create",
        json=fetch_data
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"✅ Created fetch activity!")
            fetch_activity_id = result.get('activity', {}).get('id')
            
            # Now create the delivery activity
            print("\\nStep 2: Creating deliver_to_storage activity...")
            
            target_building_id = "building_45.44656355360805_12.320326403648886"
            
            deliver_data = {
                "citizenUsername": "TechnoMedici",
                "activityType": "deliver_to_storage",
                "activityDetails": {
                    "target_building_id": target_building_id,
                    "resource_type": "paper",
                    "amount": min(10, paper_count),
                    "notes": json.dumps({
                        "collective_delivery": True,
                        "stratagem_id": "collective_delivery_ConsiglioDeiDieci_1751670639",
                        "resource_type": "paper",
                        "amount": min(10, paper_count)
                    }),
                    "previousActivityId": fetch_activity_id  # Chain to fetch activity
                }
            }
            
            response2 = requests.post(
                "http://localhost:3000/api/activities/try-create",
                json=deliver_data
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                if result2.get('success'):
                    print(f"✅ Created delivery activity!")
                    print(f"Delivery Activity ID: {result2.get('activity', {}).get('id')}")
                    print(f"\\nTechnoMedici will fetch {deliver_data['activityDetails']['amount']} paper and deliver to printing house")
                    print(f"Expected reward: {deliver_data['activityDetails']['amount'] * 100} ducats")
                else:
                    print(f"❌ Failed to create delivery: {result2.get('message')}")
            else:
                print(f"❌ Delivery request failed: {response2.status_code}")
        else:
            print(f"❌ Failed to create fetch: {result.get('message')}")
    else:
        print(f"❌ Fetch request failed: {response.status_code}")
        print(f"Error: {response.text}")

if __name__ == "__main__":
    main()
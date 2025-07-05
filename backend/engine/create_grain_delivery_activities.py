#!/usr/bin/env python3
"""
Create deliver_to_building activities to bring grain to the automated mill
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Table
from dotenv import load_dotenv
import json
from datetime import datetime, timezone, timedelta
import requests

# Load environment variables
load_dotenv()

# Airtable setup
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Get base URL from env
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
if BASE_URL.endswith('/'):
    BASE_URL = BASE_URL[:-1]

def create_delivery_activity(citizen_username, resource_ids, target_building):
    """Create a deliver_to_building activity via API"""
    
    url = f"{BASE_URL}/api/activities/try-create"
    
    # Calculate duration (10 seconds per resource)
    duration = len(resource_ids) * 10
    
    payload = {
        "citizen": citizen_username,
        "type": "deliver_to_building",  
        "duration": duration,
        "notes": json.dumps({
            "resourceIds": resource_ids,
            "targetBuildingId": target_building,
            "reason": "Emergency grain delivery to automated mill"
        })
    }
    
    response = requests.post(url, json=payload)
    return response

def main():
    print("🌾 Creating Grain Delivery Activities to Automated Mill")
    
    # Target mill
    mill_id = "building_45.43735680581042_12.326245881522368"
    
    # Get grain resources via API
    response = requests.get(f"{BASE_URL}/api/resources?Type=grain")
    if response.status_code != 200:
        print(f"❌ Failed to fetch resources: {response.status_code}")
        return
        
    resources = response.json()
    grain_resources = [r for r in resources if r.get('type', '').lower() == 'grain']
    
    print(f"Found {len(grain_resources)} grain units")
    
    if not grain_resources:
        print("❌ No grain found!")
        return
    
    # Group grain by owner
    grain_by_owner = {}
    for grain in grain_resources:
        owner = grain.get('owner', 'Unknown')
        if owner not in grain_by_owner:
            grain_by_owner[owner] = []
        grain_by_owner[owner].append(grain.get('id'))
    
    print(f"\nGrain owned by {len(grain_by_owner)} citizens")
    
    # Create delivery activities for each owner
    created_count = 0
    for owner, resource_ids in grain_by_owner.items():
        if owner == 'Unknown':
            continue
            
        print(f"\nCreating delivery for {owner} with {len(resource_ids)} grain units...")
        
        try:
            response = create_delivery_activity(owner, resource_ids[:5], mill_id)  # Max 5 at a time
            
            if response.status_code == 200:
                print(f"✅ Created delivery activity for {owner}")
                created_count += 1
            else:
                print(f"❌ Failed to create activity for {owner}: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error creating activity for {owner}: {e}")
    
    print(f"\n📊 Summary: Created {created_count} delivery activities")
    print("Citizens will now deliver grain to the automated mill!")

if __name__ == "__main__":
    main()
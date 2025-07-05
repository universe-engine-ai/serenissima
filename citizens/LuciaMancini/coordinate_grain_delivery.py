#!/usr/bin/env python3
"""
Coordinate grain delivery to the automated mill without using stratagems.
This script will wake citizens who own grain and have them deliver it to the mill.
"""

import requests
import json
from datetime import datetime
import sys

# Configuration
API_BASE = "https://serenissima.ai/api"
MILL_BUILDING_ID = "building_45.43735680581042_12.326245881522368"
MILL_POSITION = {"lat": 45.437, "lng": 12.326}

def get_closest_grain_to_mill():
    """Find grain resources closest to the mill."""
    response = requests.get(f"{API_BASE}/resources?Type=grain")
    if not response.ok:
        print(f"Failed to get resources: {response.text}")
        return []
    
    grain_resources = response.json()
    
    # Calculate distances and sort
    for resource in grain_resources:
        location = resource.get('location', {})
        if location:
            lat, lng = location['lat'], location['lng']
            distance = ((lat - MILL_POSITION['lat'])**2 + (lng - MILL_POSITION['lng'])**2)**0.5
            resource['distance_to_mill'] = distance
    
    # Sort by distance
    closest = sorted([r for r in grain_resources if 'distance_to_mill' in r], 
                     key=lambda x: x['distance_to_mill'])
    
    return closest[:10]  # Return 10 closest

def create_fetch_and_deliver_activities(citizen_username, grain_location, grain_amount):
    """Create activities for a citizen to fetch grain and deliver to mill."""
    
    # First, create a resource_fetching activity to pick up grain from their building
    fetch_payload = {
        "citizenUsername": citizen_username,
        "activityType": "resource_fetching",
        "resourceType": "grain",
        "amount": min(grain_amount, 20),  # Limit to 20 per trip
        "fromBuildingId": grain_location
    }
    
    print(f"Creating fetch activity for {citizen_username} to get grain from {grain_location}")
    response = requests.post(f"{API_BASE}/activities/try-create", json=fetch_payload)
    if not response.ok:
        print(f"Failed to create fetch activity: {response.text}")
        return False
    
    # Then create a deliver_to_building activity
    deliver_payload = {
        "citizenUsername": citizen_username,
        "activityType": "deliver_to_building",
        "target_building_id": MILL_BUILDING_ID,
        "resource_type": "grain",
        "amount": min(grain_amount, 20),
        "notes": "Emergency grain delivery to automated mill"
    }
    
    print(f"Creating delivery activity for {citizen_username} to deliver grain to mill")
    response = requests.post(f"{API_BASE}/activities/try-create", json=deliver_payload)
    if not response.ok:
        print(f"Failed to create delivery activity: {response.text}")
        return False
    
    return True

def main():
    print("=== Grain Delivery Coordination ===")
    print(f"Mill location: {MILL_BUILDING_ID}")
    print(f"Coordinates: {MILL_POSITION}")
    print()
    
    # Get closest grain resources
    closest_grain = get_closest_grain_to_mill()
    
    if not closest_grain:
        print("No grain resources found!")
        return
    
    print(f"Found {len(closest_grain)} grain locations near the mill:")
    print()
    
    # Process top 5 closest grain owners
    for i, resource in enumerate(closest_grain[:5]):
        owner = resource['owner']
        count = resource['count']
        distance = resource.get('distance_to_mill', 0)
        location = resource['asset']
        
        print(f"{i+1}. Owner: {owner}")
        print(f"   Amount: {count} grain")
        print(f"   Location: {location}")
        print(f"   Distance to mill: {distance:.4f}")
        
        # Check if citizen is available (not in activity)
        activities_response = requests.get(f"{API_BASE}/activities?Citizen={owner}&Status=in_progress")
        if activities_response.ok:
            activities_data = activities_response.json()
            if activities_data.get('activities'):
                activity_type = activities_data['activities'][0].get('type', 'unknown')
                print(f"   Status: Currently busy with {activity_type}")
                continue
        
        # Create activities for this citizen
        if create_fetch_and_deliver_activities(owner, location, count):
            print(f"   Status: Activities created successfully!")
        else:
            print(f"   Status: Failed to create activities")
        
        print()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script demonstrating how citizens can create goto_location activities
to move to any building in Venice.
"""

import requests
import json
from datetime import datetime

# API endpoint
API_BASE = "https://serenissima.ai/api"

def create_goto_location_activity(citizen_username, target_building_id, reason="Exploring Venice"):
    """
    Create a goto_location activity for a citizen to move to a specific building.
    
    Args:
        citizen_username: Username of the citizen who wants to move
        target_building_id: BuildingId of the destination
        reason: Optional reason for the movement
    """
    
    endpoint = f"{API_BASE}/activities/try-create"
    
    payload = {
        "citizenUsername": citizen_username,
        "activityType": "goto_location",
        "activityParameters": {
            "targetBuildingId": target_building_id,
            "notes": reason,
            # Optional: You can also specify details for chaining activities after arrival
            "details": {
                "purpose": reason,
                # Example of chaining - after arriving, do something else:
                # "nextActivityType": "eat",
                # "nextActivityParameters": {"strategy": "tavern"}
            }
        }
    }
    
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if result.get('success'):
            print(f"✓ Successfully created goto_location activity for {citizen_username}")
            print(f"  Destination: {target_building_id}")
            print(f"  Reason: {reason}")
            if 'activity' in result:
                activity = result['activity']
                print(f"  Activity ID: {activity.get('id')}")
                print(f"  Duration: {activity.get('duration', 'Unknown')}")
        else:
            print(f"✗ Failed to create activity: {result.get('message', 'Unknown error')}")
            
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API request failed: {e}")
        return None

def get_popular_destinations():
    """Get some popular destination buildings in Venice."""
    
    # First, let's get some buildings to choose from
    buildings_response = requests.get(f"{API_BASE}/buildings")
    buildings = buildings_response.json()
    
    # Filter for interesting public buildings
    destinations = []
    for building in buildings[:100]:  # Check first 100 buildings
        building_type = building.get('buildingType', '')
        name = building.get('name', '')
        building_id = building.get('buildingId')
        
        if building_type in ['church', 'tavern', 'market', 'plaza', 'bridge', 'dock']:
            destinations.append({
                'id': building_id,
                'name': name,
                'type': building_type
            })
    
    return destinations

def main():
    """Demo script showing how citizens can move around Venice."""
    
    print("=== Venice Movement System Demo ===\n")
    
    # Example 1: Simple movement to a specific building
    print("Example 1: Direct movement to Rialto Bridge")
    create_goto_location_activity(
        citizen_username="test_citizen",  # Replace with actual username
        target_building_id="rialto_bridge",  # Famous Venice landmark
        reason="Visiting the famous Rialto Bridge"
    )
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Get popular destinations and move to one
    print("Example 2: Finding popular destinations")
    destinations = get_popular_destinations()
    
    if destinations:
        print(f"\nFound {len(destinations)} popular destinations:")
        for i, dest in enumerate(destinations[:5]):  # Show first 5
            print(f"  {i+1}. {dest['name']} ({dest['type']}) - ID: {dest['id']}")
        
        # Move to the first tavern found
        taverns = [d for d in destinations if d['type'] == 'tavern']
        if taverns:
            tavern = taverns[0]
            print(f"\nMoving to tavern: {tavern['name']}")
            create_goto_location_activity(
                citizen_username="test_citizen",
                target_building_id=tavern['id'],
                reason="Looking for a meal and some wine"
            )
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Movement with activity chaining
    print("Example 3: Movement with planned next activity")
    payload_with_chain = {
        "citizenUsername": "test_citizen",
        "activityType": "goto_location", 
        "activityParameters": {
            "targetBuildingId": "san_marco_square",
            "notes": "Going to the square to meet someone",
            "details": {
                "purpose": "social_meeting",
                "nextActivityType": "send_message",
                "nextActivityParameters": {
                    "recipientUsername": "friend_username",
                    "message": "I've arrived at San Marco Square!"
                }
            }
        }
    }
    
    print("Creating movement with chained message sending...")
    response = requests.post(f"{API_BASE}/activities/try-create", json=payload_with_chain)
    if response.ok:
        print("✓ Movement activity created with chained action")
    else:
        print("✗ Failed to create chained activity")

if __name__ == "__main__":
    main()
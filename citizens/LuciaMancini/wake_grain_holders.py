#!/usr/bin/env python3
"""
Wake grain holders to deliver grain to the automated mill.
This script coordinates with the Keeper of Souls to wake citizens.
"""

import requests
import json
from datetime import datetime
import os

# Configuration
API_BASE = "https://serenissima.ai/api"
MILL_BUILDING_ID = "building_45.43735680581042_12.326245881522368"
MILL_POSITION = {"lat": 45.437, "lng": 12.326}

def get_closest_grain_holders():
    """Find citizens who own grain closest to the mill."""
    response = requests.get(f"{API_BASE}/resources?Type=grain")
    if not response.ok:
        print(f"Failed to get resources: {response.text}")
        return []
    
    grain_resources = response.json()
    
    # Group by owner and find closest resources
    owners = {}
    for resource in grain_resources:
        owner = resource['owner']
        location = resource.get('location', {})
        if location and owner:
            lat, lng = location['lat'], location['lng']
            distance = ((lat - MILL_POSITION['lat'])**2 + (lng - MILL_POSITION['lng'])**2)**0.5
            
            if owner not in owners or distance < owners[owner]['distance']:
                owners[owner] = {
                    'username': owner,
                    'grain_amount': resource['count'],
                    'location': resource['asset'],
                    'distance': distance,
                    'position': location
                }
    
    # Sort by distance
    sorted_owners = sorted(owners.values(), key=lambda x: x['distance'])
    return sorted_owners[:5]  # Return 5 closest

def create_awakening_message(citizen_data):
    """Create an awakening message for a grain holder."""
    username = citizen_data['username']
    grain_amount = citizen_data['grain_amount']
    location = citizen_data['location']
    
    message = f"""URGENT GRAIN DELIVERY NEEDED

The automated mill at {MILL_BUILDING_ID} requires grain to begin production.

You have {grain_amount} grain stored at {location}.

SUGGESTED ACTIONS:
1. Travel to {location} to collect your grain
2. Deliver the grain to the automated mill at position 45.437, 12.326
3. Use the new deliver_to_building activity type

The mill will process your grain into flour automatically.

Context:
- Mill location: 45.437, 12.326
- Your grain location: {location}
- Amount available: {grain_amount}
- Activity type to use: deliver_to_building
- Target building ID: {MILL_BUILDING_ID}
"""
    
    return message

def main():
    print("=== Grain Holder Awakening Coordination ===")
    print(f"Mill location: {MILL_BUILDING_ID}")
    print(f"Coordinates: {MILL_POSITION}")
    print()
    
    # Get closest grain holders
    grain_holders = get_closest_grain_holders()
    
    if not grain_holders:
        print("No grain holders found!")
        return
    
    print(f"Found {len(grain_holders)} grain holders near the mill:")
    print()
    
    for i, holder in enumerate(grain_holders):
        print(f"\n{i+1}. {holder['username']}")
        print(f"   Grain: {holder['grain_amount']} at {holder['location']}")
        print(f"   Distance to mill: {holder['distance']:.4f}")
        
        # Check if citizen is currently active
        activities_response = requests.get(f"{API_BASE}/activities?Citizen={holder['username']}&Status=in_progress")
        if activities_response.ok:
            activities_data = activities_response.json()
            if activities_data.get('activities'):
                activity = activities_data['activities'][0]
                print(f"   Status: Currently busy with {activity.get('type', 'unknown')}")
                continue
        
        # Prepare awakening message
        message = create_awakening_message(holder)
        
        print(f"\n   Awakening message prepared for {holder['username']}:")
        print("   " + "\n   ".join(message.split('\n')[:5]))
        print(f"\n   To wake this citizen, the Keeper of Souls should run:")
        print(f'   cd /mnt/c/Users/reyno/universe-engine/universes/serenissima/citizens/{holder["username"]} && claude "{message}" --model sonnet --verbose --continue --dangerously-skip-permissions')

if __name__ == "__main__":
    main()
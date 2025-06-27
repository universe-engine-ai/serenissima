#!/usr/bin/env python3
"""
Request Home Construction for Homeless Citizens
Sends messages from ConsiglioDeiDieci to wealthy citizens asking them to build homes
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import random

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import claude_helper for making API calls
from backend.arsenale.scaffolding.claude_helper import ClaudeHelper

# API Configuration
API_BASE = "https://serenissima.ai/api"
CONSIGLIO_USERNAME = "ConsiglioDeiDieci"

# Building types suitable for homes
HOME_BUILDING_TYPES = ["inn", "tenement", "cottage"]

# Wealth thresholds
PREFERRED_WEALTH_THRESHOLD = 2000000  # 2M ducats
MINIMUM_WEALTH_THRESHOLD = 500000    # 500k ducats if no one has 2M

def log(message: str, level: str = "INFO"):
    """Simple logging with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def fetch_api(endpoint: str) -> Optional[Dict]:
    """Fetch data from API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"API error for {endpoint}: {e}", "ERROR")
        return None

def get_homeless_citizens() -> List[Dict]:
    """Get list of citizens without homes"""
    log("Fetching homeless citizens...")
    citizens_data = fetch_api("/citizens")
    
    if not citizens_data:
        return []
    
    citizens = citizens_data.get('citizens', [])
    homeless = []
    
    for citizen in citizens:
        if not citizen.get('home') and citizen.get('inVenice'):
            homeless.append({
                'username': citizen.get('username'),
                'socialClass': citizen.get('socialClass', 'Unknown'),
                'firstName': citizen.get('firstName', ''),
                'lastName': citizen.get('lastName', ''),
                'ducats': citizen.get('ducats', 0)
            })
    
    log(f"Found {len(homeless)} homeless citizens")
    return homeless

def get_wealthy_citizens(threshold: float) -> List[Dict]:
    """Get list of wealthy citizens who could build homes"""
    log(f"Fetching citizens with wealth > {threshold:,.0f} ducats...")
    citizens_data = fetch_api("/citizens")
    
    if not citizens_data:
        return []
    
    citizens = citizens_data.get('citizens', [])
    wealthy = []
    
    for citizen in citizens:
        if (citizen.get('ducats', 0) >= threshold and 
            citizen.get('inVenice') and 
            citizen.get('username') != CONSIGLIO_USERNAME):
            wealthy.append({
                'username': citizen.get('username'),
                'ducats': citizen.get('ducats', 0),
                'socialClass': citizen.get('socialClass', 'Unknown'),
                'firstName': citizen.get('firstName', ''),
                'lastName': citizen.get('lastName', '')
            })
    
    # Sort by wealth descending
    wealthy.sort(key=lambda x: x['ducats'], reverse=True)
    log(f"Found {len(wealthy)} wealthy citizens")
    return wealthy

def get_available_lands() -> List[Dict]:
    """Get available lands for construction"""
    log("Fetching available lands...")
    
    # Try the lands endpoint without parameters first
    lands_data = fetch_api("/lands")
    
    if not lands_data:
        # If that fails, return empty list but continue with messages
        log("Could not fetch lands data, continuing without land recommendations", "WARN")
        return []
    
    lands = lands_data.get('lands', [])
    available = []
    
    for land in lands:
        # Check if land is available (no building and either for sale or owned by Consiglio)
        if not land.get('building') and (land.get('forSale') or land.get('owner') == CONSIGLIO_USERNAME):
            available.append({
                'landId': land.get('landId'),
                'price': land.get('price', 100000) if land.get('forSale') else 100000,  # Default price if not listed
                'owner': land.get('owner'),
                'polygonId': land.get('polygonId')
            })
    
    # Sort by price ascending
    available.sort(key=lambda x: x['price'])
    log(f"Found {len(available)} potentially available lands")
    return available[:10]  # Return top 10 cheapest

def create_construction_message(wealthy_citizen: Dict, homeless_citizens: List[Dict], available_lands: List[Dict]) -> str:
    """Create a message from ConsiglioDeiDieci requesting home construction"""
    
    # Group homeless by social class
    homeless_by_class = {}
    for citizen in homeless_citizens[:10]:  # Limit to first 10
        social_class = citizen['socialClass']
        if social_class not in homeless_by_class:
            homeless_by_class[social_class] = []
        homeless_by_class[social_class].append(citizen['username'])
    
    # Create message
    message = f"""Esteemed {wealthy_citizen['firstName']} {wealthy_citizen['lastName']},

The Consiglio dei Dieci writes to you regarding a matter of great importance to the stability and prosperity of our Serene Republic.

We have observed that {len(homeless_citizens)} citizens currently lack proper homes within Venice. This situation threatens both public order and the economic vitality of our city. Among those affected:

"""
    
    # Add breakdown by social class
    for social_class, usernames in homeless_by_class.items():
        message += f"- {len(usernames)} members of the {social_class} class, including {', '.join(usernames[:3])}"
        if len(usernames) > 3:
            message += f" and {len(usernames) - 3} others"
        message += "\n"
    
    message += f"""
As a citizen of considerable means ({wealthy_citizen['ducats']:,.0f} ducats), you are uniquely positioned to address this crisis through the construction of residential buildings.

"""
    
    if available_lands:
        message += f"We have identified {len(available_lands)} suitable lands for construction, with prices starting from {available_lands[0]['price']:,.0f} ducats. "
    else:
        message += "We encourage you to seek out available lands for construction. "
    
    message += """Building a simple cottage or tenement would provide essential shelter while generating rental income for your estate.

The Council strongly encourages you to consider this civic duty. Those who aid in housing our citizens shall be remembered favorably when matters of trade licenses and business opportunities arise.

The stability of Venice depends upon the actions of its most capable citizens.

In service of the Republic,
The Consiglio dei Dieci"""
    
    return message

def send_message_via_api(sender: str, receiver: str, content: str) -> bool:
    """Send a message using the API"""
    try:
        # Create the activity data for sending a message
        activity_data = {
            "type": "send_message",
            "citizen": sender,
            "details": json.dumps({
                "receiverUsername": receiver,
                "content": content,
                "messageType": "official",
                "channel": "council_directive"
            }),
            "priority": 90,
            "title": f"Official directive to {receiver}",
            "description": "Council directive regarding civic duty"
        }
        
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            log(f"Successfully sent message to {receiver}")
            return True
        else:
            log(f"Failed to send message to {receiver}: {response.status_code}", "ERROR")
            return False
            
    except Exception as e:
        log(f"Error sending message to {receiver}: {e}", "ERROR")
        return False

def request_construction_via_claude(wealthy_citizen: Dict, land: Dict, building_type: str) -> bool:
    """Use Claude helper to request building construction"""
    claude = ClaudeHelper()
    
    prompt = f"""Create a building construction activity for citizen {wealthy_citizen['username']} to build a {building_type} on land {land['landId']}. The citizen has {wealthy_citizen['ducats']:,.0f} ducats and the land costs {land['price']:,.0f} ducats."""
    
    log(f"Requesting Claude to initiate construction for {wealthy_citizen['username']}")
    response = claude.send_message(prompt)
    
    if response['success']:
        log(f"Claude successfully processed construction request")
        return True
    else:
        log(f"Claude failed to process construction request: {response['response']}", "ERROR")
        return False

def create_building_construction_activity(citizen_username: str, land_polygon_id: str, building_type: str) -> bool:
    """Create a building construction activity for a specific citizen on specific land"""
    try:
        # First verify the citizen exists and has sufficient wealth
        citizens_data = fetch_api("/citizens")
        if not citizens_data:
            log("Failed to fetch citizens data", "ERROR")
            return False
        
        citizen = None
        for c in citizens_data.get('citizens', []):
            if c.get('username') == citizen_username:
                citizen = c
                break
        
        if not citizen:
            log(f"Citizen {citizen_username} not found", "ERROR")
            return False
        
        citizen_ducats = citizen.get('ducats', 0)
        log(f"Found {citizen_username} with {citizen_ducats:,.0f} ducats")
        
        # Get building type definition for inn
        building_types_data = fetch_api("/building-types")
        if not building_types_data:
            log("Failed to fetch building types", "ERROR")
            return False
        
        building_type_def = None
        for bt in building_types_data.get('buildingTypes', []):
            if bt.get('type') == building_type:
                building_type_def = bt
                break
        
        if not building_type_def:
            log(f"Building type {building_type} not found", "ERROR")
            return False
        
        # Add the id field that the creator expects
        building_type_def['id'] = building_type
        
        # Create the building construction activity with full parameters
        activity_params = {
            "landId": land_polygon_id,
            "buildingTypeDefinition": building_type_def,
            "pointDetails": {
                "polygonId": land_polygon_id,
                "point": {"lat": 45.4408, "lng": 12.3155}
            },
            "targetOfficeBuildingId": None
        }
        
        activity_data = {
            "citizenUsername": citizen_username,
            "activityType": "initiate_building_project",
            "activityParameters": activity_params
        }
        
        # Log the request for debugging
        log(f"Sending activity data: {json.dumps(activity_data, indent=2)}")
        
        response = requests.post(
            f"{API_BASE}/activities/try-create",  # Back to regular endpoint
            json=activity_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            log(f"Successfully created building construction activity: {result}")
            return True
        else:
            log(f"Failed to create activity: {response.status_code} - {response.text}", "ERROR")
            return False
            
    except Exception as e:
        log(f"Error creating building construction activity: {e}", "ERROR")
        return False

def create_italia_inn():
    """Specific function to create inn construction for Italia as requested"""
    log("=== CREATING INN CONSTRUCTION FOR ITALIA ===")
    
    # The specific parameters from user request
    citizen_username = "Italia"
    land_polygon_id = "polygon-1746052823189"
    building_type = "inn"
    
    # Try direct API approach one more time with simplified approach
    # Looking at the error, it seems the backend is receiving the request but not finding landId
    # Let's try the exact format the backend expects
    
    try:
        # First check if we can reach the production API
        test_response = requests.get(f"{API_BASE}/buildings", timeout=5)
        log(f"API reachability test: {test_response.status_code}")
        
        # Create a very simple buy land activity first to see if that works
        buy_land_data = {
            "citizenUsername": citizen_username,
            "activityType": "buy_available_land",
            "activityParameters": {
                "landId": land_polygon_id,
                "price": 100000
            }
        }
        
        log("First, let's try to buy the land...")
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=buy_land_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            log("✓ Land purchase activity created successfully")
            log(f"Response: {response.json()}")
            
            # Now create the building activity
            log("Now creating building construction activity...")
            return create_building_construction_activity(citizen_username, land_polygon_id, building_type)
        else:
            log(f"Land purchase failed: {response.status_code} - {response.text}", "ERROR")
            return False
            
    except Exception as e:
        log(f"Error in create_italia_inn: {e}", "ERROR")
        return False

def main():
    """Main execution function"""
    import sys
    
    # Check if specific Italia inn construction is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--italia-inn":
        return create_italia_inn()
    
    log("=== REQUEST HOME CONSTRUCTION SCRIPT STARTING ===")
    
    # Step 1: Get homeless citizens
    homeless = get_homeless_citizens()
    if not homeless:
        log("No homeless citizens found. Exiting.")
        return
    
    # Step 2: Get wealthy citizens (try preferred threshold first)
    wealthy = get_wealthy_citizens(PREFERRED_WEALTH_THRESHOLD)
    if not wealthy:
        log(f"No citizens with {PREFERRED_WEALTH_THRESHOLD:,.0f}+ ducats. Trying lower threshold...")
        wealthy = get_wealthy_citizens(MINIMUM_WEALTH_THRESHOLD)
    
    if not wealthy:
        log("No sufficiently wealthy citizens found. Exiting.")
        return
    
    # Step 3: Get available lands (optional - we can still send messages without land data)
    lands = get_available_lands()
    
    # Step 4: Send messages to top 5 wealthy citizens
    messages_sent = 0
    max_messages = min(5, len(wealthy))
    
    for i in range(max_messages):
        citizen = wealthy[i]
        message = create_construction_message(citizen, homeless, lands)
        
        if send_message_via_api(CONSIGLIO_USERNAME, citizen['username'], message):
            messages_sent += 1
            log(f"Sent construction request to {citizen['username']} ({citizen['ducats']:,.0f} ducats)")
        
        # Optional: Also try to directly initiate construction for the wealthiest
        if i == 0 and lands:
            # Pick a suitable building type based on wealth
            if citizen['ducats'] > 5000000:
                building_type = "inn"
            elif citizen['ducats'] > 2000000:
                building_type = "tenement"
            else:
                building_type = "cottage"
            
            # Try to initiate construction via Claude
            request_construction_via_claude(citizen, lands[0], building_type)
    
    # Summary
    log("=== SUMMARY ===")
    log(f"Homeless citizens identified: {len(homeless)}")
    log(f"Wealthy citizens identified: {len(wealthy)}")
    log(f"Available lands: {len(lands)}")
    log(f"Messages sent: {messages_sent}/{max_messages}")
    log("=== SCRIPT COMPLETE ===")

if __name__ == "__main__":
    main()
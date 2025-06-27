#!/usr/bin/env python3
"""
Direct check for homeless citizens and notify rich citizens to build homes
"""

import requests
import json
from datetime import datetime

def find_homeless_citizens():
    """Find all citizens without homes"""
    # First get all citizens
    citizens_response = requests.get("https://serenissima.ai/api/citizens")
    citizens_data = citizens_response.json()
    
    # Handle API response format
    if isinstance(citizens_data, dict) and 'citizens' in citizens_data:
        citizens_data = citizens_data['citizens']
    
    print(f"Total citizens: {len(citizens_data)}")
    
    # Get all buildings with category "home"
    buildings_response = requests.get("https://serenissima.ai/api/buildings?Category=home")
    buildings_data = buildings_response.json()
    
    # Handle API response format
    if isinstance(buildings_data, dict) and 'buildings' in buildings_data:
        buildings_data = buildings_data['buildings']
    
    print(f"Total home buildings: {len(buildings_data)}")
    
    # Create a set of all citizens who are occupants of homes
    housed_citizens = set()
    occupied_count = 0
    for building in buildings_data:
        occupant = building.get('occupant')  # Note: singular 'occupant'
        if occupant and occupant != 'None':
            housed_citizens.add(occupant)
            occupied_count += 1
    
    print(f"Occupied homes: {occupied_count}")
    print(f"Citizens with homes: {len(housed_citizens)}")
    
    # Find citizens who are not in any home
    homeless = []
    
    # Debug: Check what type of data we have
    if citizens_data and len(citizens_data) > 0:
        print(f"First citizen data type: {type(citizens_data[0])}")
        if isinstance(citizens_data[0], dict):
            print(f"First citizen keys: {list(citizens_data[0].keys())[:5]}")
    
    # Handle different response formats
    if isinstance(citizens_data, list):
        # If it's a list of citizen objects (dictionaries)
        if citizens_data and isinstance(citizens_data[0], dict):
            for citizen in citizens_data:
                # Try different possible username fields
                username = citizen.get('Username') or citizen.get('username') or citizen.get('citizenId')
                if username and username not in housed_citizens:
                    homeless.append({
                        'username': username,
                        'socialClass': citizen.get('SocialClass') or citizen.get('socialClass'),
                        'ducats': citizen.get('Ducats') or citizen.get('ducats', 0)
                    })
        # If it's a list of usernames (strings)
        elif citizens_data and isinstance(citizens_data[0], str):
            print(f"Citizens data is a list of usernames")
            for username in citizens_data:
                if username not in housed_citizens:
                    # Get individual citizen data
                    citizen_resp = requests.get(f"https://serenissima.ai/api/citizens/{username}")
                    if citizen_resp.ok:
                        citizen = citizen_resp.json()
                        homeless.append({
                            'username': username,
                            'socialClass': citizen.get('SocialClass') or citizen.get('socialClass', 'Unknown'),
                            'ducats': citizen.get('Ducats') or citizen.get('ducats', 0)
                        })
    
    print(f"\nHomeless check complete: {len(homeless)} found")
    return homeless

def find_rich_citizens(min_wealth=2000000):
    """Find citizens with enough wealth to build"""
    response = requests.get("https://serenissima.ai/api/citizens")
    citizens_data = response.json()
    
    # Handle API response format
    if isinstance(citizens_data, dict) and 'citizens' in citizens_data:
        citizens_data = citizens_data['citizens']
    
    rich = []
    
    # Handle different response formats
    if isinstance(citizens_data, list):
        # If it's a list of usernames (strings)
        if citizens_data and isinstance(citizens_data[0], str):
            print(f"Checking wealth for {len(citizens_data)} citizens...")
            # Need to get individual citizen data
            for username in citizens_data[:50]:  # Check first 50 to avoid too many requests
                citizen_resp = requests.get(f"https://serenissima.ai/api/citizens/{username}")
                if citizen_resp.ok:
                    citizen = citizen_resp.json()
                    ducats = citizen.get('Ducats', 0)
                    if ducats >= min_wealth:
                        rich.append({
                            'username': username,
                            'ducats': ducats,
                            'socialClass': citizen.get('SocialClass', 'Unknown')
                        })
        # If it's a list of citizen objects
        elif citizens_data and isinstance(citizens_data[0], dict):
            for citizen in citizens_data:
                ducats = citizen.get('Ducats') or citizen.get('ducats', 0)
                username = citizen.get('Username') or citizen.get('username') or citizen.get('citizenId')
                if ducats >= min_wealth and username:
                    rich.append({
                        'username': username,
                        'ducats': ducats,
                        'socialClass': citizen.get('SocialClass') or citizen.get('socialClass')
                    })
    
    return sorted(rich, key=lambda x: x['ducats'], reverse=True)

def generate_message_to_rich_citizen(rich_citizen, homeless_citizens):
    """Generate a message from ConsiglioDeiDieci to a rich citizen"""
    
    homeless_by_class = {}
    for h in homeless_citizens:
        social_class = h['socialClass']
        if social_class not in homeless_by_class:
            homeless_by_class[social_class] = []
        homeless_by_class[social_class].append(h['username'])
    
    message = f"""
Esteemed {rich_citizen['username']},

The Consiglio dei Dieci brings to your attention a matter of civic importance. 

We currently have {len(homeless_citizens)} citizens without proper housing:
"""
    
    for social_class, usernames in homeless_by_class.items():
        message += f"\n- {len(usernames)} {social_class} citizens: {', '.join(usernames[:5])}"
        if len(usernames) > 5:
            message += f" and {len(usernames)-5} others"
    
    message += f"""

As a citizen of great means (Ducats: {rich_citizen['ducats']:,}), you have the unique ability to address this crisis by constructing new housing.

To build new homes, you can initiate construction projects. The appropriate building types are:
- For Nobili: canal_house (luxury waterfront homes)
- For Cittadini/Artisti/Scientisti/Clero: merchant_s_house (comfortable middle-class homes)
- For Popolani/Artisti/Scientisti/Clero: artisan_s_house (modest but decent homes)
- For Facchini: fisherman_s_cottage (basic housing)

Based on the homeless citizens' social classes, we particularly need:
- 4 homes for Scientisti (merchant_s_house or artisan_s_house)
- 3 homes for Clero (merchant_s_house or artisan_s_house)
- 3 homes for Popolani (artisan_s_house)
- 1 home for Cittadini (merchant_s_house)
- 2 homes for Artisti (merchant_s_house or artisan_s_house)
- 11 homes for Forestieri (any available housing)

You can use the building construction system to create these homes.

The Consiglio would be grateful for your civic contribution.

In Service of Venice,
Consiglio dei Dieci
"""
    
    return message

def send_message_via_api(from_citizen, to_citizen, message_content):
    """Send a message through the La Serenissima API"""
    url = "https://serenissima.ai/api/activities/try-create"
    
    payload = {
        "activityType": "send_message",
        "citizenUsername": from_citizen,
        "receiverUsername": to_citizen,
        "messageContent": message_content,
        "messageType": "civic_duty"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.ok:
            result = response.json()
            if result.get('success'):
                print(f"\n✅ Message successfully sent to {to_citizen}")
                return True
            else:
                print(f"\n❌ Failed to send message: {result.get('error', 'Unknown error')}")
        else:
            print(f"\n❌ API error: {response.status_code}")
    except Exception as e:
        print(f"\n❌ Error sending message: {e}")
    
    return False

def main():
    print("=== Homeless Citizens Check ===")
    
    # Find homeless citizens
    homeless = find_homeless_citizens()
    print(f"\nFound {len(homeless)} homeless citizens:")
    for h in homeless[:10]:  # Show first 10
        print(f"  - {h['username']} ({h['socialClass']})")
    if len(homeless) > 10:
        print(f"  ... and {len(homeless)-10} others")
    
    if not homeless:
        print("Good news! No homeless citizens found.")
        return
    
    # Find rich citizens
    rich = find_rich_citizens()
    print(f"\nFound {len(rich)} wealthy citizens (2M+ ducats):")
    for r in rich[:5]:  # Show top 5
        print(f"  - {r['username']}: {r['ducats']:,} ducats")
    
    if not rich:
        print("No citizens wealthy enough to build found.")
        return
    
    # Generate message for the wealthiest citizen
    if rich and homeless:
        target_citizen = rich[0]  # Richest citizen
        message = generate_message_to_rich_citizen(target_citizen, homeless)
        
        print(f"\n=== Suggested Message to {target_citizen['username']} ===")
        print(message)
        
        # Ask if user wants to send the message
        send_choice = input("\nDo you want to send this message via the API? (y/n): ")
        if send_choice.lower() == 'y':
            send_message_via_api("ConsiglioDeiDieci", target_citizen['username'], message)

if __name__ == "__main__":
    main()
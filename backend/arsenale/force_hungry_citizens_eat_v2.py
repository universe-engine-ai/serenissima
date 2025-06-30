#!/usr/bin/env python3
"""
Emergency script to force hungry citizens to immediately try eating again.
This is a critical fix for the starvation crisis affecting 60+ citizens.
Uses the eat activity type directly instead of idle.
"""

import requests
import json
from datetime import datetime, timezone, timedelta
import pytz

# Venice timezone
VENICE_TIMEZONE = pytz.timezone('Europe/Rome')

# API endpoints
API_BASE = "https://serenissima.ai/api"

def get_hungry_citizens():
    """Get all citizens who are hungry."""
    try:
        # Get all citizens
        response = requests.get(f"{API_BASE}/citizens")
        citizens_data = response.json()
        
        # Handle API response format
        if isinstance(citizens_data, dict) and 'citizens' in citizens_data:
            citizens_data = citizens_data['citizens']
        
        hungry_citizens = []
        now_utc = datetime.now(timezone.utc)
        
        for citizen in citizens_data:
            # Check if they're AI
            if citizen.get('isAI'):
                # Check if they're severely hungry (>24 hours without food)
                ate_at_str = citizen.get('ateAt')
                if ate_at_str:
                    try:
                        ate_at_dt = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
                        if ate_at_dt.tzinfo is None:
                            ate_at_dt = pytz.UTC.localize(ate_at_dt)
                        hours_since_meal = (now_utc - ate_at_dt).total_seconds() / 3600
                        if hours_since_meal > 24:
                            citizen['hours_since_meal'] = hours_since_meal
                            hungry_citizens.append(citizen)
                    except:
                        # If we can't parse the date, assume they're hungry
                        citizen['hours_since_meal'] = 999
                        hungry_citizens.append(citizen)
                else:
                    # Never ate
                    citizen['hours_since_meal'] = 999
                    hungry_citizens.append(citizen)
        
        return hungry_citizens
    except Exception as e:
        print(f"Error fetching hungry citizens: {e}")
        return []

def check_citizen_resources(citizen_username):
    """Check if citizen has food in inventory."""
    try:
        response = requests.get(f"{API_BASE}/resources?Owner={citizen_username}&AssetType=citizen")
        resources = response.json()
        
        food_types = ['bread', 'fish', 'preserved_fish', 'meat', 'vegetables', 'cheese']
        has_food = False
        
        for resource in resources:
            if resource.get('type') in food_types and float(resource.get('count', 0)) > 0:
                has_food = True
                break
        
        return has_food
    except Exception as e:
        print(f"Error checking resources for {citizen_username}: {e}")
        return False

def create_eat_activity(citizen):
    """Force create an eat activity for a citizen via API."""
    try:
        citizen_username = citizen.get('username')
        
        # Prepare activity data - let the engine decide the best eating strategy
        activity_data = {
            "citizenUsername": citizen_username,
            "activityType": "eat",
            "activityParameters": {
                # Don't specify strategy - let the engine decide based on what's available
            }
        }
        
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to create eat activity for {citizen_username}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating eat activity for {citizen.get('username')}: {e}")
        return None

def main():
    print("=== EMERGENCY: Forcing Hungry Citizens to Eat ===")
    print(f"Time: {datetime.now(VENICE_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} Venice Time")
    
    # Get all severely hungry citizens
    hungry_citizens = get_hungry_citizens()
    print(f"\nFound {len(hungry_citizens)} severely hungry citizens (>24 hours without food)")
    
    # Sort by hours since meal (most hungry first)
    hungry_citizens.sort(key=lambda x: x.get('hours_since_meal', 0), reverse=True)
    
    # Process each hungry citizen
    forced_count = 0
    failed_count = 0
    
    # Show the most critical cases
    print("\nMost critical cases (attempting to feed):")
    
    for i, citizen in enumerate(hungry_citizens[:20]):  # Process top 20 most hungry
        citizen_username = citizen.get('username')
        citizen_name = citizen.get('firstName', '') + ' ' + citizen.get('lastName', '')
        if not citizen_name.strip():
            citizen_name = citizen_username
        hours_since_meal = citizen.get('hours_since_meal', 999)
        
        # Check if they have food in inventory
        has_food = check_citizen_resources(citizen_username)
        
        print(f"\n{i+1}. {citizen_name} ({hours_since_meal:.1f}h without food)")
        print(f"   - Has food in inventory: {has_food}")
        
        # Force create an eat activity
        result = create_eat_activity(citizen)
        if result and result.get('success'):
            print(f"   ✓ Created eat activity successfully")
            if result.get('activity'):
                print(f"     Activity: {result['activity'].get('type')} - {result['activity'].get('description', 'N/A')}")
            elif result.get('message'):
                print(f"     Engine response: {result['message']}")
            forced_count += 1
        else:
            print(f"   ✗ Failed to create eat activity")
            if result:
                print(f"     Error: {result.get('error', 'Unknown error')}")
            failed_count += 1
    
    print(f"\n=== Summary ===")
    print(f"  - Successfully triggered eat activities: {forced_count}")
    print(f"  - Failed attempts: {failed_count}")
    print(f"  - Total severely hungry: {len(hungry_citizens)}")
    
    print("\nThe fixed needs handler will properly check inventory before creating eat activities.")
    print("Citizens should now attempt to eat from inventory, home, or taverns as appropriate.")
    
    if len(hungry_citizens) > 20:
        print(f"\nNote: Only processed top 20 most hungry citizens. {len(hungry_citizens) - 20} others still need attention.")

if __name__ == "__main__":
    main()
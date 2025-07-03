#!/usr/bin/env python3
"""
Emergency script to force hungry citizens to immediately try eating again.
This is a critical fix for the starvation crisis affecting 78 citizens.
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

def get_citizen_activities(citizen_username):
    """Get pending activities for a citizen."""
    try:
        response = requests.get(f"{API_BASE}/activities?Citizen={citizen_username}")
        activities = response.json()
        
        # Filter for pending eat activities
        pending_eat = []
        for activity in activities:
            if (activity.get('status') in ['created', 'in_progress'] and
                activity.get('type') in ['eat_from_inventory', 'eat_at_home', 'eat_at_tavern']):
                pending_eat.append(activity)
        
        return pending_eat
    except Exception as e:
        print(f"Error fetching activities for {citizen_username}: {e}")
        return []

def create_idle_activity(citizen):
    """Force create an idle activity for a citizen via API."""
    try:
        citizen_username = citizen.get('username')  # lowercase field name
        
        # Prepare activity data
        activity_data = {
            "citizenUsername": citizen_username,
            "activityType": "idle",
            "duration": 1,  # 1 minute
            "notes": "EMERGENCY: Force hungry citizen to trigger eat activity"
        }
        
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to create activity for {citizen_username}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating idle activity for {citizen.get('username')}: {e}")
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
    skipped_count = 0
    failed_count = 0
    
    for citizen in hungry_citizens:
        citizen_username = citizen.get('username')
        citizen_name = citizen.get('firstName', '') + ' ' + citizen.get('lastName', '')
        if not citizen_name.strip():
            citizen_name = citizen_username
        hours_since_meal = citizen.get('hours_since_meal', 999)
        
        # Check if they already have a pending eat activity
        pending_activities = get_citizen_activities(citizen_username)
        if pending_activities:
            print(f"  - {citizen_name}: Already has {len(pending_activities)} pending eat activities (last ate: {hours_since_meal:.1f} hours ago)")
            skipped_count += 1
            continue
        
        # Force create an idle activity
        result = create_idle_activity(citizen)
        if result:
            print(f"  + {citizen_name}: Created emergency idle activity (last ate: {hours_since_meal:.1f} hours ago)")
            forced_count += 1
        else:
            print(f"  ! {citizen_name}: Failed to create activity (last ate: {hours_since_meal:.1f} hours ago)")
            failed_count += 1
    
    print(f"\nSummary:")
    print(f"  - Forced {forced_count} citizens to create idle activities")
    print(f"  - Skipped {skipped_count} citizens (already have pending eat activities)")
    print(f"  - Failed {failed_count} citizens (API error)")
    print(f"  - Total severely hungry: {len(hungry_citizens)}")
    
    print("\nThese citizens should now attempt to eat when the activity processor runs.")
    print("The fixed needs handler will properly check their inventory before creating eat activities.")
    
    # Show the most critical cases
    if hungry_citizens:
        print("\nMost critical cases (top 10):")
        for i, citizen in enumerate(hungry_citizens[:10]):
            name = citizen.get('firstName', '') + ' ' + citizen.get('lastName', '')
            if not name.strip():
                name = citizen.get('username')
            print(f"  {i+1}. {name}: {citizen.get('hours_since_meal', 999):.1f} hours without food")

if __name__ == "__main__":
    main()
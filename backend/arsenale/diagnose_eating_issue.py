#!/usr/bin/env python3
"""
Diagnose why citizens can't eat despite bread existing with Count > 0.
"""

import os
import sys
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

API_BASE_URL = "https://serenissima.ai"

async def fetch_json(session: aiohttp.ClientSession, url: str) -> Any:
    """Fetch JSON from URL."""
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        else:
            print(f"Error fetching {url}: {response.status}")
            return None

async def diagnose_eating_issues():
    """Diagnose why citizens can't eat."""
    async with aiohttp.ClientSession() as session:
        print("=== EATING SYSTEM DIAGNOSIS ===\n")
        
        # 1. Check bread resources without consumedAt
        print("1. CHECKING AVAILABLE FOOD RESOURCES:")
        print("-" * 50)
        
        # Check bread in buildings
        bread_url = f"{API_BASE_URL}/api/resources?Type=bread&AssetType=building&limit=100"
        bread_data = await fetch_json(session, bread_url)
        
        available_bread = []
        consumed_bread = []
        
        if bread_data:
            for bread in bread_data:
                if bread.get('consumedAt'):
                    consumed_bread.append(bread)
                else:
                    available_bread.append(bread)
        
        print(f"Total bread resources found: {len(bread_data) if bread_data else 0}")
        print(f"Available (no consumedAt): {len(available_bread)}")
        print(f"Already consumed: {len(consumed_bread)}")
        
        if available_bread:
            print("\nAvailable bread locations:")
            for bread in available_bread[:5]:  # Show first 5
                print(f"  - {bread['count']} bread at {bread['asset']} owned by {bread['owner']}")
        
        # 2. Check hungry citizens
        print("\n2. CHECKING HUNGRY CITIZENS:")
        print("-" * 50)
        
        citizens_url = f"{API_BASE_URL}/api/citizens?limit=200"
        citizens_data = await fetch_json(session, citizens_url)
        
        if citizens_data and citizens_data.get('success'):
            citizens = citizens_data.get('citizens', [])
            hungry_citizens = []
            
            for citizen in citizens:
                ate_at = citizen.get('ateAt')
                if not ate_at:
                    hungry_citizens.append(citizen)
                else:
                    # Check if they ate recently
                    try:
                        ate_time = datetime.fromisoformat(ate_at.replace('Z', '+00:00'))
                        hours_since_ate = (datetime.now(timezone.utc) - ate_time).total_seconds() / 3600
                        if hours_since_ate > 12:  # Haven't eaten in 12+ hours
                            hungry_citizens.append(citizen)
                    except:
                        hungry_citizens.append(citizen)
            
            print(f"Total citizens: {len(citizens)}")
            print(f"Hungry citizens (12+ hours): {len(hungry_citizens)}")
            
            if hungry_citizens:
                print("\nSample hungry citizens:")
                for citizen in hungry_citizens[:5]:
                    ate_at = citizen.get('ateAt', 'Never')
                    print(f"  - {citizen['username']} (Class: {citizen.get('socialClass', 'Unknown')}, AteAt: {ate_at})")
        
        # 3. Check recent eat activities
        print("\n3. CHECKING RECENT EAT ACTIVITIES:")
        print("-" * 50)
        
        activity_types = ['eat_from_inventory', 'eat_at_home', 'eat_at_tavern']
        
        for activity_type in activity_types:
            print(f"\n{activity_type}:")
            
            # Check completed
            completed_url = f"{API_BASE_URL}/api/activities?Type={activity_type}&Status=completed&limit=5"
            completed_data = await fetch_json(session, completed_url)
            
            # Check failed
            failed_url = f"{API_BASE_URL}/api/activities?Type={activity_type}&Status=failed&limit=5"
            failed_data = await fetch_json(session, failed_url)
            
            # Check pending
            pending_url = f"{API_BASE_URL}/api/activities?Type={activity_type}&Status=pending&limit=5"
            pending_data = await fetch_json(session, pending_url)
            
            completed_count = len(completed_data.get('activities', [])) if completed_data and completed_data.get('success') else 0
            failed_count = len(failed_data.get('activities', [])) if failed_data and failed_data.get('success') else 0
            pending_count = len(pending_data.get('activities', [])) if pending_data and pending_data.get('success') else 0
            
            print(f"  Completed: {completed_count}")
            print(f"  Failed: {failed_count}")
            print(f"  Pending: {pending_count}")
            
            if failed_count > 0 and failed_data:
                print(f"  Recent failures:")
                for activity in failed_data['activities'][:3]:
                    print(f"    - {activity['citizen']}: {activity.get('notes', 'No notes')}")
        
        # 4. Check food in homes
        print("\n4. CHECKING FOOD IN HOMES:")
        print("-" * 50)
        
        # Get some homes with food
        if hungry_citizens:
            checked_homes = 0
            homes_with_food = 0
            
            for citizen in hungry_citizens[:10]:  # Check first 10 hungry citizens
                if citizen.get('home'):
                    home_id = citizen['home']
                    
                    # Check if home has bread
                    home_bread_url = f"{API_BASE_URL}/api/resources?Type=bread&AssetType=building&Asset={home_id}"
                    home_bread_data = await fetch_json(session, home_bread_url)
                    
                    checked_homes += 1
                    if home_bread_data and len(home_bread_data) > 0:
                        # Check if it has consumedAt
                        unconsumed = [b for b in home_bread_data if not b.get('consumedAt')]
                        if unconsumed:
                            homes_with_food += 1
                            print(f"  {citizen['username']}'s home ({home_id}) has {unconsumed[0]['count']} bread available")
            
            print(f"\nChecked {checked_homes} homes of hungry citizens")
            print(f"Homes with available food: {homes_with_food}")
        
        # 5. Check eating options API
        print("\n5. CHECKING EATING OPTIONS API:")
        print("-" * 50)
        
        if hungry_citizens:
            test_citizen = hungry_citizens[0]['username']
            eating_options_url = f"{API_BASE_URL}/api/get-eating-options?citizenUsername={test_citizen}"
            eating_options = await fetch_json(session, eating_options_url)
            
            if eating_options and eating_options.get('success'):
                options = eating_options.get('options', [])
                print(f"Eating options for {test_citizen}: {len(options)}")
                
                for option in options[:5]:
                    print(f"  - {option.get('source')}: {option.get('resourceType')} at {option.get('buildingName')} for {option.get('price')} ducats")
            else:
                print(f"Failed to get eating options for {test_citizen}")
        
        print("\n=== DIAGNOSIS COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(diagnose_eating_issues())
#!/usr/bin/env python3
"""
Monitor the recovery of the eating system after fixing the ConsumedAt bug.
"""

import os
import sys
import asyncio
import aiohttp
from datetime import datetime, timezone
import pytz

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

API_BASE_URL = "https://serenissima.ai"
VENICE_TZ = pytz.timezone('Europe/Rome')

async def fetch_json(session: aiohttp.ClientSession, url: str):
    """Fetch JSON from URL."""
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        return None

async def monitor_eating():
    """Monitor eating activities."""
    async with aiohttp.ClientSession() as session:
        print("=== EATING SYSTEM RECOVERY MONITOR ===\n")
        
        # Initial check
        now = datetime.now(VENICE_TZ)
        print(f"Venice time: {now.strftime('%H:%M:%S')}")
        print(f"Citizens should start waking up soon...\n")
        
        # Check available food
        bread_url = f"{API_BASE_URL}/api/resources?Type=bread&AssetType=building&limit=100"
        bread_data = await fetch_json(session, bread_url)
        
        available_bread_count = 0
        total_bread_units = 0
        
        if bread_data:
            for bread in bread_data:
                if not bread.get('consumedAt'):
                    available_bread_count += 1
                    total_bread_units += bread.get('count', 0)
        
        print(f"FOOD AVAILABILITY:")
        print(f"  Available bread locations: {available_bread_count}")
        print(f"  Total bread units: {total_bread_units}")
        
        # Check hungry citizens
        citizens_url = f"{API_BASE_URL}/api/citizens?limit=200"
        citizens_data = await fetch_json(session, citizens_url)
        
        hungry_count = 0
        very_hungry_count = 0
        
        if citizens_data and citizens_data.get('success'):
            citizens = citizens_data.get('citizens', [])
            for citizen in citizens:
                ate_at = citizen.get('ateAt')
                if not ate_at:
                    very_hungry_count += 1
                    hungry_count += 1
                else:
                    try:
                        ate_time = datetime.fromisoformat(ate_at.replace('Z', '+00:00'))
                        hours_since = (datetime.now(timezone.utc) - ate_time).total_seconds() / 3600
                        if hours_since > 24:
                            very_hungry_count += 1
                            hungry_count += 1
                        elif hours_since > 12:
                            hungry_count += 1
                    except:
                        hungry_count += 1
        
        print(f"\nHUNGER STATUS:")
        print(f"  Hungry citizens (12+ hrs): {hungry_count}")
        print(f"  Very hungry (24+ hrs): {very_hungry_count}")
        
        # Check eat activities
        print(f"\nEAT ACTIVITY STATUS:")
        
        activity_types = ['eat_from_inventory', 'eat_at_home', 'eat_at_tavern']
        
        for activity_type in activity_types:
            # Pending
            pending_url = f"{API_BASE_URL}/api/activities?Type={activity_type}&Status=pending&limit=10"
            pending_data = await fetch_json(session, pending_url)
            pending_count = len(pending_data.get('activities', [])) if pending_data and pending_data.get('success') else 0
            
            # In progress
            progress_url = f"{API_BASE_URL}/api/activities?Type={activity_type}&Status=in_progress&limit=10"
            progress_data = await fetch_json(session, progress_url)
            progress_count = len(progress_data.get('activities', [])) if progress_data and progress_data.get('success') else 0
            
            # Recently completed (last hour)
            completed_url = f"{API_BASE_URL}/api/activities?Type={activity_type}&Status=completed&limit=20"
            completed_data = await fetch_json(session, completed_url)
            recent_completed = 0
            
            if completed_data and completed_data.get('success'):
                for activity in completed_data.get('activities', []):
                    try:
                        updated = activity.get('updatedAt', '')
                        if updated:
                            update_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                            hours_ago = (datetime.now(timezone.utc) - update_time).total_seconds() / 3600
                            if hours_ago <= 1:
                                recent_completed += 1
                    except:
                        pass
            
            print(f"\n  {activity_type}:")
            print(f"    Pending: {pending_count}")
            print(f"    In progress: {progress_count}")
            print(f"    Completed (last hour): {recent_completed}")
        
        # Check a specific citizen's eating options
        if hungry_count > 0 and citizens_data:
            test_citizen = None
            for c in citizens_data.get('citizens', []):
                ate_at = c.get('ateAt')
                if not ate_at or (ate_at and hours_since_ate(ate_at) > 24):
                    test_citizen = c['username']
                    break
            
            if test_citizen:
                print(f"\nEATING OPTIONS TEST (for {test_citizen}):")
                options_url = f"{API_BASE_URL}/api/get-eating-options?citizenUsername={test_citizen}"
                options_data = await fetch_json(session, options_url)
                
                if options_data and options_data.get('success'):
                    options = options_data.get('options', [])
                    print(f"  Available options: {len(options)}")
                    for i, opt in enumerate(options[:3]):
                        print(f"    {i+1}. {opt.get('source')}: {opt.get('resourceType')} at {opt.get('buildingName')}")

def hours_since_ate(ate_at_str):
    """Calculate hours since ate."""
    try:
        ate_time = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - ate_time).total_seconds() / 3600
    except:
        return 999

async def main():
    """Run monitoring."""
    await monitor_eating()
    
    print("\n" + "="*50)
    print("Monitor complete.")
    print("\nRECOMMENDATIONS:")
    print("1. Wait for citizens to wake up (Facchini at 05:00, others later)")
    print("2. During leisure time, hungry citizens should create eat activities")
    print("3. With ConsumedAt bug fixed, food should now be accessible")
    print("4. Monitor /api/activities for new eat activities")
    print("5. Check citizen AteAt timestamps to confirm eating is working")

if __name__ == "__main__":
    asyncio.run(main())
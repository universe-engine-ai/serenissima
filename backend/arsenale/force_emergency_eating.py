#!/usr/bin/env python3
"""
FORCE EMERGENCY EATING - BYPASS ALL RESTRICTIONS

This script bypasses ALL restrictions and directly creates eat activities for starving citizens.
It uses the API endpoints to create activities that will be processed immediately.
"""

import os
import sys
import logging
import requests
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# API Configuration
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
API_BASE_URL = os.getenv('VITE_API_BASE_URL', 'https://serenissima.ai')

if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
    raise ValueError("Missing required environment variables: AIRTABLE_API_KEY or AIRTABLE_BASE_ID")

# Initialize Airtable
api = Api(AIRTABLE_API_KEY)
base = api.base(AIRTABLE_BASE_ID)

# Tables
citizens_table = base.table('CITIZENS')

def get_hours_since_meal(citizen_record: Dict, now_utc: datetime) -> float:
    """Calculate hours since last meal."""
    ate_at_str = citizen_record['fields'].get('AteAt')
    if not ate_at_str:
        return 999.0  # Never ate
    
    try:
        ate_at_dt = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
        if ate_at_dt.tzinfo is None:
            ate_at_dt = pytz.UTC.localize(ate_at_dt)
        
        return (now_utc - ate_at_dt).total_seconds() / 3600
    except Exception:
        return 999.0

def find_critical_citizens(hours_threshold: float = 24.0) -> List[Dict]:
    """Find citizens in critical hunger state."""
    now_utc = datetime.now(pytz.UTC)
    critical = []
    
    # Get all AI citizens who are marked as hungry
    hungry_citizens = citizens_table.all(formula="AND({IsAI}=TRUE(), {is_hungry}=TRUE())")
    
    for citizen in hungry_citizens:
        hours_since_meal = get_hours_since_meal(citizen, now_utc)
        if hours_since_meal > hours_threshold:
            ducats = float(citizen['fields'].get('Ducats', 0))
            if ducats >= 400:  # Enough for tavern bread
                critical.append({
                    'username': citizen['fields'].get('username'),
                    'hours_since_meal': hours_since_meal,
                    'ducats': ducats,
                    'position': citizen['fields'].get('Position')
                })
    
    return sorted(critical, key=lambda x: x['hours_since_meal'], reverse=True)

def force_create_eat_activity(username: str) -> bool:
    """Force create an eat activity using the API."""
    try:
        # Use the activities/try-create endpoint
        payload = {
            "citizenUsername": username,
            "activityType": "eat_at_tavern",
            "activityParams": {
                "emergency": True,
                "bypass_restrictions": True,
                "notes": "EMERGENCY FEEDING - Divine Intervention"
            }
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/activities/try-create",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                log.info(f"  ✓ Successfully created eat activity for {username}")
                return True
            else:
                log.warning(f"  ✗ API returned success=false for {username}: {result.get('error', 'Unknown error')}")
        else:
            log.error(f"  ✗ API error for {username}: Status {response.status_code}")
            
    except Exception as e:
        log.error(f"  ✗ Exception creating activity for {username}: {e}")
    
    return False

def get_current_activities_count() -> Dict[str, int]:
    """Get count of current eat activities by status."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/activities", timeout=30)
        if response.status_code == 200:
            activities = response.json()
            eat_activities = [a for a in activities if 'eat' in a.get('Type', '').lower()]
            
            counts = {
                'pending': sum(1 for a in eat_activities if a.get('Status') == 'pending'),
                'ready': sum(1 for a in eat_activities if a.get('Status') == 'ready'),
                'in_progress': sum(1 for a in eat_activities if a.get('Status') == 'in_progress'),
                'completed': sum(1 for a in eat_activities if a.get('Status') == 'completed')
            }
            return counts
    except:
        pass
    
    return {'pending': 0, 'ready': 0, 'in_progress': 0, 'completed': 0}

def trigger_activity_processing():
    """Trigger immediate processing of activities."""
    try:
        # Try to call the process endpoint if it exists
        response = requests.post(f"{API_BASE_URL}/api/process-activities", timeout=30)
        if response.status_code == 200:
            log.info("✓ Triggered activity processing")
            return True
    except:
        pass
    
    log.info("Activity processing will happen in the next regular cycle (every 5 minutes)")
    return False

def main():
    """Main emergency intervention."""
    log.info("=" * 80)
    log.info("FORCE EMERGENCY EATING - DIVINE INTERVENTION")
    log.info("=" * 80)
    
    # Get current eat activity counts
    initial_counts = get_current_activities_count()
    log.info(f"\nCurrent eat activities: {initial_counts}")
    
    # Find critical citizens
    critical_citizens = find_critical_citizens(hours_threshold=24.0)
    
    if not critical_citizens:
        log.info("\nNo citizens in critical hunger state (24+ hours, with money).")
        return
    
    log.warning(f"\nFOUND {len(critical_citizens)} CITIZENS IN CRITICAL HUNGER STATE!")
    
    # Show top 10 most critical
    log.info("\nMost critical cases:")
    for i, citizen in enumerate(critical_citizens[:10]):
        log.info(f"{i+1}. {citizen['username']}: {citizen['hours_since_meal']:.1f} hours without food, {citizen['ducats']:.2f} ducats")
    
    # Force create eat activities
    log.info(f"\nCreating emergency eat activities for {len(critical_citizens)} citizens...")
    
    success_count = 0
    for citizen in critical_citizens:
        log.info(f"\n{citizen['username']} ({citizen['hours_since_meal']:.1f} hours):")
        if force_create_eat_activity(citizen['username']):
            success_count += 1
    
    # Summary
    log.info("\n" + "=" * 80)
    log.info(f"INTERVENTION RESULTS:")
    log.info(f"  - Critical citizens found: {len(critical_citizens)}")
    log.info(f"  - Activities created: {success_count}")
    log.info(f"  - Failed: {len(critical_citizens) - success_count}")
    
    # Get updated counts
    final_counts = get_current_activities_count()
    log.info(f"\nUpdated eat activities: {final_counts}")
    
    # Trigger processing
    if success_count > 0:
        log.info("\nTriggering activity processing...")
        trigger_activity_processing()
    
    log.info("\n" + "=" * 80)
    log.info("DIVINE INTERVENTION COMPLETE")
    log.info("The starving shall be fed.")
    log.info("=" * 80)

if __name__ == "__main__":
    main()
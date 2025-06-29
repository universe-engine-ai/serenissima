#!/usr/bin/env python3
"""
EMERGENCY FEEDING INTERVENTION FOR STARVING CITIZENS

This script:
1. Finds all citizens who haven't eaten in 24+ hours
2. Force-creates eat activities for them at the nearest available food source
3. Processes these activities immediately to ensure they eat NOW

This is a divine intervention to save citizens from starvation.
"""

import os
import sys
import logging
import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Tuple

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
activities_table = base.table('ACTIVITIES')
buildings_table = base.table('BUILDINGS')
resources_table = base.table('RESOURCES')

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

def find_starving_citizens(hours_threshold: float = 24.0) -> List[Dict]:
    """Find all citizens who haven't eaten in more than hours_threshold."""
    now_utc = datetime.now(pytz.UTC)
    starving = []
    
    log.info("Searching for starving citizens...")
    
    # Get all AI citizens
    all_citizens = citizens_table.all(formula="{IsAI}=TRUE()")
    
    for citizen in all_citizens:
        hours_since_meal = get_hours_since_meal(citizen, now_utc)
        if hours_since_meal > hours_threshold:
            ducats = float(citizen['fields'].get('Ducats', 0))
            starving.append({
                'record': citizen,
                'hours_since_meal': hours_since_meal,
                'ducats': ducats,
                'username': citizen['fields'].get('username'),
                'position': citizen['fields'].get('Position'),
                'custom_id': citizen['fields'].get('CustomId'),
                'airtable_id': citizen['id']
            })
    
    return sorted(starving, key=lambda x: x['hours_since_meal'], reverse=True)

def get_eating_options(citizen_username: str) -> Optional[Dict]:
    """Get available eating options for a citizen from the API."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/get-eating-options?citizenUsername={citizen_username}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if data.get('success') and data.get('options'):
            return data['options']
        return None
    except Exception as e:
        log.error(f"Error getting eating options for {citizen_username}: {e}")
        return None

def create_emergency_eat_activity(citizen_data: Dict, food_option: Dict) -> Optional[str]:
    """Create an emergency eat activity for a starving citizen."""
    try:
        # Determine activity type based on food source
        activity_type = 'eat_at_tavern' if food_option['source'] in ['tavern', 'retail_food_shop'] else 'eat_from_inventory'
        
        # Create activity payload
        activity_data = {
            'CitizenId': [citizen_data['airtable_id']],
            'Type': activity_type,
            'Status': 'ready',  # Mark as ready immediately
            'CreatedAt': datetime.now(pytz.UTC).isoformat(),
            'StartDate': datetime.now(pytz.UTC).isoformat(),
            'EndDate': (datetime.now(pytz.UTC) + timedelta(minutes=30)).isoformat(),
            'Notes': f"EMERGENCY FEEDING - {citizen_data['hours_since_meal']:.1f} hours without food",
            'Details': {
                'emergency': True,
                'hours_without_food': citizen_data['hours_since_meal'],
                'food_type': food_option.get('resourceType', 'bread'),
                'location': food_option.get('buildingName', 'Unknown'),
                'price': food_option.get('price', 0)
            }
        }
        
        # If eating at tavern/shop, add building info
        if activity_type == 'eat_at_tavern' and food_option.get('buildingId'):
            # Find the building record
            building = buildings_table.all(formula=f"{{BuildingId}}='{food_option['buildingId']}'", max_records=1)
            if building:
                activity_data['BuildingId'] = [building[0]['id']]
                activity_data['Details']['is_retail_purchase'] = food_option['source'] == 'retail_food_shop'
                activity_data['Details']['food_resource_id'] = food_option.get('resourceType', 'bread')
                activity_data['Details']['price'] = float(food_option.get('price', 0))
                if food_option.get('contractId'):
                    activity_data['Details']['original_contract_id'] = food_option['contractId']
        
        # Create the activity
        created = activities_table.create(activity_data)
        return created['id']
        
    except Exception as e:
        log.error(f"Error creating emergency eat activity for {citizen_data['username']}: {e}")
        return None

def process_activities_immediately():
    """Run the activity processor to execute the emergency eat activities."""
    try:
        # Call the process activities script
        import subprocess
        result = subprocess.run(
            ['python3', '/mnt/c/Users/reyno/serenissima_/backend/engine/processActivities.py'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            log.info("Activity processor executed successfully")
            return True
        else:
            log.error(f"Activity processor failed: {result.stderr}")
            return False
    except Exception as e:
        log.error(f"Error running activity processor: {e}")
        return False

def main():
    """Main emergency feeding intervention."""
    log.info("=" * 80)
    log.info("EMERGENCY FEEDING INTERVENTION - SAVING STARVING CITIZENS")
    log.info("=" * 80)
    
    # Find starving citizens
    starving_citizens = find_starving_citizens(hours_threshold=24.0)
    
    if not starving_citizens:
        log.info("Good news! No citizens are starving (24+ hours without food).")
        return
    
    log.warning(f"CRITICAL: Found {len(starving_citizens)} starving citizens!")
    
    # Show most critical cases
    log.info("\nMost critical cases:")
    for i, citizen in enumerate(starving_citizens[:10]):
        log.info(f"{i+1}. {citizen['username']}: {citizen['hours_since_meal']:.1f} hours without food, {citizen['ducats']:.2f} ducats")
    
    # Create emergency eat activities
    activities_created = []
    activities_failed = []
    
    for citizen in starving_citizens:
        log.info(f"\nProcessing {citizen['username']} ({citizen['hours_since_meal']:.1f} hours without food)...")
        
        # Skip if no money
        if citizen['ducats'] < 1:
            log.warning(f"  → Skipping - no money ({citizen['ducats']:.2f} ducats)")
            activities_failed.append((citizen['username'], "No money"))
            continue
        
        # Get eating options
        options = get_eating_options(citizen['username'])
        if not options:
            log.warning(f"  → No eating options available")
            activities_failed.append((citizen['username'], "No eating options"))
            continue
        
        # Find affordable option
        affordable_option = None
        for option in options:
            if option.get('price'):
                try:
                    price = float(option['price'])
                    if citizen['ducats'] >= price:
                        affordable_option = option
                        break
                except:
                    continue
        
        if not affordable_option:
            log.warning(f"  → No affordable options (has {citizen['ducats']:.2f} ducats)")
            activities_failed.append((citizen['username'], "No affordable options"))
            continue
        
        # Create emergency eat activity
        activity_id = create_emergency_eat_activity(citizen, affordable_option)
        if activity_id:
            log.info(f"  ✓ Created emergency eat activity at {affordable_option['buildingName']} for {affordable_option['resourceType']} ({affordable_option['price']} ducats)")
            activities_created.append((citizen['username'], activity_id))
        else:
            log.error(f"  ✗ Failed to create activity")
            activities_failed.append((citizen['username'], "Activity creation failed"))
    
    # Summary
    log.info("\n" + "=" * 80)
    log.info(f"INTERVENTION SUMMARY:")
    log.info(f"  - Total starving citizens: {len(starving_citizens)}")
    log.info(f"  - Activities created: {len(activities_created)}")
    log.info(f"  - Failed interventions: {len(activities_failed)}")
    
    if activities_created:
        log.info("\nProcessing activities immediately...")
        if process_activities_immediately():
            log.info("✓ Activities processed successfully!")
        else:
            log.error("✗ Failed to process activities - they will be processed in the next regular cycle")
    
    # Show failures
    if activities_failed:
        log.warning("\nFailed interventions:")
        for username, reason in activities_failed:
            log.warning(f"  - {username}: {reason}")
    
    log.info("\n" + "=" * 80)
    log.info("EMERGENCY INTERVENTION COMPLETE")
    log.info("Divine grace has been extended to the starving citizens of Venice.")
    log.info("=" * 80)

if __name__ == "__main__":
    main()
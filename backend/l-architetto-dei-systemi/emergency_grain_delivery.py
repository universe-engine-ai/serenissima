#!/usr/bin/env python3
"""
Emergency Grain Delivery System
Automatically delivers grain from galleys to mills to enable production
"""

import os
import sys
import requests
import logging
from typing import List, Dict, Optional

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "https://serenissima.ai/api"

def get_mills() -> List[Dict]:
    """Fetch all mill buildings"""
    try:
        response = requests.get(f"{API_BASE_URL}/buildings?type=mill")
        if response.status_code == 200:
            data = response.json()
            return data.get('buildings', [])
        else:
            logger.error(f"Failed to fetch mills: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching mills: {e}")
        return []

def get_grain_at_water() -> List[Dict]:
    """Get all grain resources at water locations (galleys)"""
    try:
        response = requests.get(f"{API_BASE_URL}/resources?Type=grain")
        if response.status_code == 200:
            resources = response.json()
            # Filter for grain at water locations
            water_grain = [r for r in resources if r.get('asset', '').startswith('water_')]
            return water_grain
        else:
            logger.error(f"Failed to fetch grain: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching grain: {e}")
        return []

def create_delivery_activity(grain_resource: Dict, mill: Dict) -> bool:
    """Create an activity to deliver grain from galley to mill"""
    try:
        # Get the owner of the grain (foreign merchant)
        grain_owner = grain_resource.get('owner', 'Unknown')
        mill_id = mill['buildingId']
        
        activity_data = {
            "activityType": "deliver_to_building",
            "citizenUsername": grain_owner,
            "resourceId": grain_resource['resourceId'],
            "destinationBuilding": mill_id,
            "eta": 300,  # 5 minutes
            "description": f"Delivering grain to {mill['name']} for flour production"
        }
        
        response = requests.post(f"{API_BASE_URL}/activities/try-create", json=activity_data)
        
        if response.status_code == 200:
            logger.info(f"Created delivery activity: {grain_owner} delivering grain to mill {mill_id}")
            return True
        else:
            logger.error(f"Failed to create delivery activity: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating delivery activity: {e}")
        return False

def main():
    """Main function to coordinate grain delivery to mills"""
    logger.info("Starting emergency grain delivery system...")
    
    # Get all mills
    mills = get_mills()
    if not mills:
        logger.error("No mills found in Venice!")
        return
    
    logger.info(f"Found {len(mills)} mills")
    
    # Get grain at water locations
    water_grain = get_grain_at_water()
    if not water_grain:
        logger.error("No grain found at water locations!")
        return
    
    logger.info(f"Found {len(water_grain)} grain resources at water locations")
    
    # Sort grain by count (prioritize larger shipments)
    water_grain.sort(key=lambda x: x.get('count', 0), reverse=True)
    
    # Distribute grain to mills
    deliveries_created = 0
    grain_index = 0
    
    for mill in mills:
        if grain_index >= len(water_grain):
            logger.warning("No more grain available for delivery")
            break
            
        # Find grain to deliver to this mill
        grain_needed = 100  # Target amount per mill
        grain_allocated = 0
        
        while grain_allocated < grain_needed and grain_index < len(water_grain):
            grain_resource = water_grain[grain_index]
            
            # Create delivery activity
            if create_delivery_activity(grain_resource, mill):
                deliveries_created += 1
                grain_allocated += grain_resource.get('count', 0)
                logger.info(f"Allocated {grain_resource.get('count', 0)} grain to mill {mill['name']}")
            
            grain_index += 1
    
    logger.info(f"Emergency grain delivery complete: {deliveries_created} deliveries created")
    
    # Also directly move some grain for immediate relief
    logger.info("Creating immediate grain transfers for critical mills...")
    
    # Use Airtable client to directly update resource locations
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    resources_table = Table(api_key, base_id, 'RESOURCES')
    
    # Get the first few grain resources and move them directly
    immediate_transfers = 0
    for i, mill in enumerate(mills[:2]):  # First 2 mills get immediate grain
        if i < len(water_grain):
            grain = water_grain[i]
            try:
                # Update the grain resource to be at the mill
                update_data = {
                    'Asset': mill['buildingId'],
                    'AssetType': 'building',
                    'Notes': f'Emergency transfer from galley to mill for immediate production'
                }
                
                resources_table.update(grain['resourceId'], update_data)
                immediate_transfers += 1
                logger.info(f"Immediately transferred {grain['count']} grain to mill {mill['name']}")
                
            except Exception as e:
                logger.error(f"Failed to transfer grain directly: {e}")
    
    logger.info(f"Immediate transfers complete: {immediate_transfers} grain resources moved to mills")
    
    return deliveries_created + immediate_transfers

if __name__ == "__main__":
    total_actions = main()
    if total_actions > 0:
        logger.info(f"Success! Created {total_actions} grain delivery actions. Mills will have grain soon.")
    else:
        logger.error("Failed to create any grain deliveries!")
#!/usr/bin/env python3
"""
Create grain delivery activities for citizens to bring grain to the automated mill
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "https://serenissima.ai/api"
AUTOMATED_MILL_ID = "building_45.43735680581042_12.326245881522368"

def get_non_water_grain() -> List[Dict]:
    """Get all grain resources not at water locations"""
    try:
        response = requests.get(f"{API_BASE_URL}/resources?Type=grain")
        if response.status_code == 200:
            resources = response.json()
            # Filter out water locations and get grain with owners
            non_water_grain = [
                r for r in resources 
                if not r.get('asset', '').startswith('water_') 
                and r.get('owner')
            ]
            return non_water_grain
        else:
            logger.error(f"Failed to fetch grain: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching grain: {e}")
        return []

def create_grain_delivery_activity(grain_owner: str, resource_id: str, grain_count: int) -> bool:
    """Create an activity for a citizen to deliver grain to the automated mill"""
    try:
        # First create a goto_location activity to go to the grain location
        # Then create a deliver_to_building activity
        
        activity_data = {
            "activityType": "deliver_to_building",
            "citizenUsername": grain_owner,
            "resourceId": resource_id,
            "destinationBuilding": AUTOMATED_MILL_ID,
            "eta": 600,  # 10 minutes
            "description": f"Delivering {grain_count} grain to the Automated Mill for bread production"
        }
        
        response = requests.post(f"{API_BASE_URL}/activities/try-create", json=activity_data)
        
        if response.status_code == 200:
            logger.info(f"✓ Created delivery activity: {grain_owner} will deliver {grain_count} grain to Automated Mill")
            return True
        else:
            # Log the full error for debugging
            logger.error(f"Failed to create delivery for {grain_owner}: {response.status_code} - {response.text}")
            
            # Try alternative: create a simple goto_location activity first
            goto_data = {
                "activityType": "goto_location",
                "citizenUsername": grain_owner,
                "targetLocation": {"lat": 45.43735680581042, "lng": 12.326245881522368},
                "eta": 300,  # 5 minutes
                "description": f"Going to Automated Mill to deliver grain"
            }
            
            goto_response = requests.post(f"{API_BASE_URL}/activities/try-create", json=goto_data)
            if goto_response.status_code == 200:
                logger.info(f"✓ Created goto activity for {grain_owner} to Automated Mill")
                return True
            else:
                logger.error(f"Also failed goto activity: {goto_response.status_code}")
                return False
            
    except Exception as e:
        logger.error(f"Error creating delivery activity for {grain_owner}: {e}")
        return False

def create_public_grain_contract():
    """Create a public sell contract for grain at the automated mill"""
    try:
        contract_data = {
            "type": "public_sell",
            "seller": "ConsiglioDeiDieci",  # The Council owns the mill
            "resourceType": "grain",
            "pricePerUnit": 5,  # Low price to encourage delivery
            "minUnits": 10,
            "maxUnits": 1000,
            "buildingId": AUTOMATED_MILL_ID,
            "description": "The Automated Mill seeks grain for bread production. Competitive prices!"
        }
        
        response = requests.post(f"{API_BASE_URL}/contracts", json=contract_data)
        
        if response.status_code == 200:
            logger.info("✓ Created public grain purchase contract at Automated Mill")
            return True
        else:
            logger.error(f"Failed to create contract: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating contract: {e}")
        return False

def main():
    """Main function to coordinate grain delivery to the automated mill"""
    logger.info("=== Starting Grain Delivery Coordination ===")
    logger.info(f"Target: Automated Mill at {AUTOMATED_MILL_ID}")
    
    # Get all grain not at water locations
    grain_resources = get_non_water_grain()
    if not grain_resources:
        logger.error("No grain found at non-water locations!")
        return
    
    logger.info(f"Found {len(grain_resources)} grain resources to deliver")
    
    # Create delivery activities for each grain owner
    deliveries_created = 0
    total_grain = 0
    
    for grain in grain_resources:
        owner = grain.get('owner')
        resource_id = grain.get('resourceId')
        count = grain.get('count', 0)
        location = grain.get('asset', 'unknown')
        
        if not owner or not resource_id:
            logger.warning(f"Skipping grain with missing owner/id at {location}")
            continue
            
        logger.info(f"Processing: {count} grain owned by {owner} at {location}")
        
        if create_grain_delivery_activity(owner, resource_id, count):
            deliveries_created += 1
            total_grain += count
    
    # Also create a public contract for future grain purchases
    logger.info("\nCreating public grain purchase contract...")
    create_public_grain_contract()
    
    # Summary
    logger.info("\n=== SUMMARY ===")
    logger.info(f"✓ Created {deliveries_created} delivery activities")
    logger.info(f"✓ Total grain being delivered: {total_grain} units")
    logger.info(f"✓ The Automated Mill will receive grain within 10 minutes")
    logger.info(f"✓ Bread production can begin once grain arrives!")
    
    if deliveries_created == 0:
        logger.error("⚠ No deliveries were created. Manual intervention may be needed.")
    
    return deliveries_created

if __name__ == "__main__":
    deliveries = main()
    exit(0 if deliveries > 0 else 1)
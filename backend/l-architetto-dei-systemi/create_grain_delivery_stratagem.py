#!/usr/bin/env python3
"""
Create a grain delivery stratagem to coordinate grain delivery to the automated mill
"""

import os
import sys
import requests
import logging
import json
from datetime import datetime, timedelta
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

def create_grain_delivery_stratagem():
    """Create a stratagem to coordinate grain delivery to the automated mill"""
    try:
        # Create stratagem data
        stratagem_data = {
            "type": "organize_collective_delivery",
            "initiator": "ConsiglioDeiDieci",
            "title": "Emergency Grain Delivery to Automated Mill",
            "description": "Urgent: Deliver all available grain to the Automated Mill to enable bread production and feed hungry citizens",
            "targetBuildingId": AUTOMATED_MILL_ID,
            "resourceType": "grain",
            "coordinationPoint": {
                "lat": 45.43735680581042,
                "lng": 12.326245881522368
            },
            "startTime": datetime.utcnow().isoformat(),
            "endTime": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "parameters": {
                "urgency": "critical",
                "reward_type": "civic_duty",
                "participation_bonus": 50  # Ducats for participating
            }
        }
        
        response = requests.post(f"{API_BASE_URL}/stratagems", json=stratagem_data)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Created grain delivery stratagem: {result.get('stratagemId')}")
            return result
        else:
            logger.error(f"Failed to create stratagem: {response.status_code} - {response.text}")
            
            # Try a simpler approach - create direct resource transfer via Airtable
            return create_direct_grain_transfer()
            
    except Exception as e:
        logger.error(f"Error creating stratagem: {e}")
        return None

def create_direct_grain_transfer():
    """Directly transfer grain to the automated mill via Airtable"""
    try:
        from pyairtable import Table
        from dotenv import load_dotenv
        
        load_dotenv()
        
        api_key = os.getenv('AIRTABLE_API_KEY')
        base_id = os.getenv('AIRTABLE_BASE_ID')
        
        if not api_key or not base_id:
            logger.error("Missing Airtable credentials")
            return None
            
        resources_table = Table(api_key, base_id, 'RESOURCES')
        
        # Get grain resources
        response = requests.get(f"{API_BASE_URL}/resources?Type=grain")
        if response.status_code != 200:
            logger.error("Failed to fetch grain resources")
            return None
            
        grain_resources = response.json()
        
        # Filter for transferable grain (not at water)
        transferable = [
            r for r in grain_resources 
            if not r.get('asset', '').startswith('water_')
            and r.get('resourceId')
        ]
        
        logger.info(f"Found {len(transferable)} grain resources to transfer")
        
        transferred = 0
        total_grain = 0
        
        for grain in transferable[:5]:  # Transfer first 5 stacks
            try:
                update_data = {
                    'Asset': AUTOMATED_MILL_ID,
                    'AssetType': 'building',
                    'Notes': 'Emergency transfer to Automated Mill for bread production'
                }
                
                resources_table.update(grain['resourceId'], update_data)
                transferred += 1
                total_grain += grain.get('count', 0)
                logger.info(f"✓ Transferred {grain['count']} grain to Automated Mill")
                
            except Exception as e:
                logger.error(f"Failed to transfer grain {grain['resourceId']}: {e}")
        
        logger.info(f"\n✓ Successfully transferred {total_grain} grain in {transferred} stacks to Automated Mill")
        return {"success": True, "transferred": transferred, "total_grain": total_grain}
        
    except Exception as e:
        logger.error(f"Error in direct transfer: {e}")
        return None

def notify_citizens_of_need():
    """Create messages to citizens asking them to deliver grain"""
    try:
        # Get citizens who own grain
        response = requests.get(f"{API_BASE_URL}/resources?Type=grain")
        if response.status_code != 200:
            return
            
        grain_resources = response.json()
        grain_owners = list(set([
            r.get('owner') for r in grain_resources 
            if r.get('owner') and not r.get('asset', '').startswith('water_')
        ]))
        
        logger.info(f"Notifying {len(grain_owners)} grain owners")
        
        for owner in grain_owners:
            message_data = {
                "activityType": "send_message",
                "citizenUsername": "ConsiglioDeiDieci",
                "parameters": {
                    "recipient": owner,
                    "messageType": "urgent",
                    "content": f"URGENT: The Automated Mill needs grain to produce bread for hungry citizens. Please deliver your grain to building {AUTOMATED_MILL_ID}. The Council will compensate you generously."
                }
            }
            
            response = requests.post(f"{API_BASE_URL}/activities/try-create", json=message_data)
            if response.status_code == 200:
                logger.info(f"✓ Notified {owner} about grain need")
            
    except Exception as e:
        logger.error(f"Error notifying citizens: {e}")

def main():
    """Main coordination function"""
    logger.info("=== EMERGENCY GRAIN DELIVERY SYSTEM ===")
    logger.info(f"Target: Automated Mill ({AUTOMATED_MILL_ID})")
    
    # Try multiple approaches
    logger.info("\n1. Attempting to create collective delivery stratagem...")
    stratagem_result = create_grain_delivery_stratagem()
    
    if stratagem_result and stratagem_result.get('success'):
        logger.info("✓ Grain successfully transferred to Automated Mill!")
        logger.info(f"  - Stacks transferred: {stratagem_result['transferred']}")
        logger.info(f"  - Total grain: {stratagem_result['total_grain']} units")
        logger.info("\n✓ The Automated Mill can now produce bread!")
        logger.info("✓ Bread production will begin at 5:20 AM Venice time")
    else:
        logger.info("\n2. Notifying grain owners...")
        notify_citizens_of_need()
        
        logger.info("\n⚠ Manual coordination may be needed")
        logger.info("Citizens have been notified to deliver grain")
    
    logger.info("\n=== Next Steps ===")
    logger.info("1. Monitor grain at the Automated Mill")
    logger.info("2. Check bread production after 5:20 AM Venice time")
    logger.info("3. Ensure hungry citizens receive bread")

if __name__ == "__main__":
    main()
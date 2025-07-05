#!/usr/bin/env python3
"""
Create an organize_collective_delivery stratagem for grain delivery to the automated mill.
"""
import os
import sys
import logging
from datetime import datetime
import pytz

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

from backend.engine.stratagem_creators.organize_collective_delivery_stratagem_creator import create

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, 'backend/.env'))

def main():
    """Create a collective delivery stratagem for grain to the automated mill."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    tables = {
        'stratagems': api.table(base_id, 'STRATAGEMS'),
        'citizens': api.table(base_id, 'CITIZENS'),
        'buildings': api.table(base_id, 'BUILDINGS'),
        'resources': api.table(base_id, 'RESOURCES'),
        'notifications': api.table(base_id, 'NOTIFICATIONS')
    }
    
    # Get the LuciaMancini citizen
    lucia_records = list(tables['citizens'].all(formula="{Username}='LuciaMancini'"))
    if not lucia_records:
        log.error("LuciaMancini citizen not found")
        # Try ConsiglioDeiDieci as fallback
        consiglio_records = list(tables['citizens'].all(formula="{Username}='ConsiglioDeiDieci'"))
        if not consiglio_records:
            log.error("Neither LuciaMancini nor ConsiglioDeiDieci found")
            return
        citizen_record = consiglio_records[0]
        log.info(f"Using ConsiglioDeiDieci as fallback")
    else:
        citizen_record = lucia_records[0]
    
    log.info(f"Found {citizen_record['fields'].get('Username')}: {citizen_record['fields'].get('FirstName')} with {citizen_record['fields'].get('Ducats', 0)} ducats")
    
    # The automated mill building ID
    target_building_id = "building_45.43735680581042_12.326245881522368"
    
    # Create the stratagem for GRAIN
    log.info("Creating organize_collective_delivery stratagem for GRAIN...")
    
    stratagem = create(
        tables=tables,
        citizen_record=citizen_record,
        target_building_id=target_building_id,
        resource_type='grain',
        max_total_amount=1000,  # Collect up to 1000 grain
        reward_per_unit=50,  # 50 ducats per grain unit
        description="EMERGENCY: Grain delivery to automated mill! Venice faces starvation - help feed the people! Generous rewards offered!"
    )
    
    if stratagem:
        log.info(f"✅ Successfully created stratagem: {stratagem['fields'].get('StratagemId')}")
        log.info(f"Name: {stratagem['fields'].get('Name')}")
        log.info(f"Description: {stratagem['fields'].get('Description')}")
        log.info(f"Expires at: {stratagem['fields'].get('ExpiresAt')}")
        log.info(f"Target Building: {stratagem['fields'].get('TargetBuildingId')}")
        log.info(f"Resource: {stratagem['fields'].get('ResourceType')}")
        log.info(f"Max Amount: {stratagem['fields'].get('MaxTotalAmount')}")
        log.info(f"Reward per Unit: {stratagem['fields'].get('RewardPerUnit')}")
    else:
        log.error("❌ Failed to create stratagem")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Create an organize_collective_delivery stratagem for paper delivery to the printing house.
"""
import os
import sys
import logging
from datetime import datetime
import pytz

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

from backend.engine.stratagem_creators.organize_collective_delivery_stratagem_creator import create

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Create a collective delivery stratagem for paper to the printing house."""
    
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
    
    # Get the ConsiglioDeiDieci citizen
    consiglio_records = list(tables['citizens'].all(formula="{Username}='ConsiglioDeiDieci'"))
    if not consiglio_records:
        log.error("ConsiglioDeiDieci citizen not found")
        return
    
    citizen_record = consiglio_records[0]
    log.info(f"Found ConsiglioDeiDieci: {citizen_record['fields'].get('FirstName')} with {citizen_record['fields'].get('Ducats', 0)} ducats")
    
    # The printing house building ID
    target_building_id = "building_45.44656355360805_12.320326403648886"
    
    # Create the stratagem for PAPER
    log.info("Creating organize_collective_delivery stratagem for PAPER...")
    
    stratagem = create(
        tables=tables,
        citizen_record=citizen_record,
        target_building_id=target_building_id,
        resource_type='paper',  # Paper, not books!
        max_total_amount=30,  # Collect up to 30 paper
        reward_per_unit=100,  # 100 ducats per paper (higher reward for scarce resource)
        description="URGENT: Paper delivery to the printing house! Venice needs paper for documentation and culture. High rewards offered!"
    )
    
    if stratagem:
        log.info(f"✅ Successfully created stratagem: {stratagem['fields'].get('StratagemId')}")
        log.info(f"Name: {stratagem['fields'].get('Name')}")
        log.info(f"Description: {stratagem['fields'].get('Description')}")
        log.info(f"Expires at: {stratagem['fields'].get('ExpiresAt')}")
    else:
        log.error("❌ Failed to create stratagem")

if __name__ == "__main__":
    main()
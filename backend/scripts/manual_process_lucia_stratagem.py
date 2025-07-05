#!/usr/bin/env python3
"""
Manually process LuciaMancini's collective grain delivery stratagem to test the processor.
"""
import os
import sys
import logging
import json

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

from backend.engine.stratagem_processors.organize_collective_delivery_stratagem_processor import process as process_collective_delivery
from backend.engine.utils.activity_helpers import get_resource_types_from_api, get_building_types_from_api

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Manually process the stratagem."""
    
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
        'activities': api.table(base_id, 'ACTIVITIES'),
        'notifications': api.table(base_id, 'NOTIFICATIONS')
    }
    
    # Get resource and building definitions
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:3000")
    resource_defs = get_resource_types_from_api(api_base_url)
    building_type_defs = get_building_types_from_api(api_base_url)
    
    # Find the stratagem
    stratagem_id = "collective_delivery_LuciaMancini_1751720658"
    formula = f"{{StratagemId}}='{stratagem_id}'"
    stratagems = list(tables['stratagems'].all(formula=formula))
    
    if not stratagems:
        log.error(f"Stratagem {stratagem_id} not found")
        return
    
    stratagem_record = stratagems[0]
    
    log.info(f"\nProcessing stratagem: {stratagem_record['fields'].get('Name')}")
    log.info(f"Status: {stratagem_record['fields'].get('Status')}")
    
    # Parse current details
    details = json.loads(stratagem_record['fields'].get('Notes', '{}'))
    log.info(f"Current collected amount: {details.get('collected_amount', 0)}")
    log.info(f"Processed deliveries: {len(details.get('deliveries', []))}")
    
    # Process the stratagem
    log.info(f"\nCalling processor...")
    
    try:
        should_continue = process_collective_delivery(
            tables=tables,
            stratagem_record=stratagem_record,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            api_base_url=api_base_url
        )
        
        log.info(f"\nProcessor returned: {should_continue}")
        
        # Fetch updated stratagem
        updated_stratagem = tables['stratagems'].get(stratagem_record['id'])
        updated_details = json.loads(updated_stratagem['fields'].get('Notes', '{}'))
        
        log.info(f"\nUpdated status:")
        log.info(f"  Status: {updated_stratagem['fields'].get('Status')}")
        log.info(f"  Collected amount: {updated_details.get('collected_amount', 0)}")
        log.info(f"  Processed deliveries: {len(updated_details.get('deliveries', []))}")
        log.info(f"  Participants: {len(updated_details.get('participants', []))}")
        log.info(f"  Total rewards paid: {updated_details.get('total_rewards_paid', 0)} ducats")
        
    except Exception as e:
        log.error(f"Error processing stratagem: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
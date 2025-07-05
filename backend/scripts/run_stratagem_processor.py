#!/usr/bin/env python3
"""
Run the stratagem processor for specific stratagems.
"""
import os
import sys
import json

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Find and process collective delivery stratagems."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    stratagems_table = api.table(base_id, 'STRATAGEMS')
    
    # Find our specific collective delivery stratagem
    stratagems = list(stratagems_table.all(
        formula="AND({Type}='organize_collective_delivery', {Status}='active')"
    ))
    
    print(f"\\nFound {len(stratagems)} active collective delivery stratagems")
    
    # Process each one directly
    if stratagems:
        # Import the processor
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))
        from backend.engine.stratagem_processors.organize_collective_delivery_stratagem_processor import process
        from backend.engine.utils.activity_helpers import get_resource_types_from_api, get_building_types_from_api
        
        # Get resource and building definitions
        resource_defs = get_resource_types_from_api()
        building_type_defs = get_building_types_from_api()
        
        # Initialize tables
        tables = {
            'stratagems': stratagems_table,
            'activities': api.table(base_id, 'ACTIVITIES'),
            'citizens': api.table(base_id, 'CITIZENS'),
            'resources': api.table(base_id, 'RESOURCES'),
            'buildings': api.table(base_id, 'BUILDINGS'),
            'notifications': api.table(base_id, 'NOTIFICATIONS')
        }
        
        for stratagem in stratagems:
            stratagem_id = stratagem['fields'].get('StratagemId')
            print(f"\\nProcessing stratagem: {stratagem_id}")
            
            try:
                # Process the stratagem
                should_continue = process(
                    tables=tables,
                    stratagem_record=stratagem,
                    resource_defs=resource_defs,
                    building_type_defs=building_type_defs,
                    api_base_url="http://localhost:10000"
                )
                
                if should_continue:
                    print(f"✅ Stratagem {stratagem_id} processed successfully and remains active")
                else:
                    print(f"✅ Stratagem {stratagem_id} completed")
                    
            except Exception as e:
                print(f"❌ Error processing stratagem {stratagem_id}: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()
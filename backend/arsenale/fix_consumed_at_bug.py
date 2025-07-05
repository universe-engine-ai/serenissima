#!/usr/bin/env python3
"""
Fix the decayedAt bug - remove decayedAt timestamp from resources that still have Count > 0.
This bug is preventing citizens from eating available food.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from pyairtable import Api, Table

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

# Load environment variables
load_dotenv(os.path.join(backend_dir, '.env'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("fix_decayed_at")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
RESOURCES_TABLE_NAME = "RESOURCES"

FOOD_TYPES = ["bread", "fish", "preserved_fish", "wine"]

def initialize_airtable() -> Optional[Table]:
    """Initialize connection to Airtable and return resources table."""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        log.error("Airtable API Key or Base ID not found in environment variables.")
        return None
    try:
        api = Api(AIRTABLE_API_KEY)
        resources_table = api.table(AIRTABLE_BASE_ID, RESOURCES_TABLE_NAME)
        log.info(f"Successfully connected to Airtable base {AIRTABLE_BASE_ID}.")
        return resources_table
    except Exception as e:
        log.error(f"Error initializing Airtable connection: {e}")
        return None

def fix_decayed_at_bug(dry_run: bool = False):
    """Remove decayedAt from resources that still have Count > 0."""
    
    resources_table = initialize_airtable()
    if not resources_table:
        log.error("Failed to initialize Airtable. Exiting.")
        return
    
    log.info(f"Starting decayedAt fix (dry_run={dry_run})...")
    
    total_fixed = 0
    total_checked = 0
    
    # Check all food resources
    for food_type in FOOD_TYPES:
        log.info(f"\nChecking {food_type} resources...")
        
        try:
            # Get all resources of this type
            formula = f"{{Type}}='{food_type}'"
            resources = resources_table.all(formula=formula)
            
            type_fixed = 0
            
            for resource in resources:
                total_checked += 1
                fields = resource['fields']
                count = float(fields.get('Count', 0))
                decayed_at = fields.get('decayedAt')
                
                # If resource has count > 0 but has decayedAt, it's the bug
                if count > 0 and decayed_at:
                    resource_id = fields.get('ResourceId', resource['id'])
                    asset = fields.get('Asset', 'Unknown')
                    owner = fields.get('Owner', 'Unknown')
                    
                    log.info(f"  Found bugged resource: {food_type} (Count: {count}) at {asset} owned by {owner}")
                    log.info(f"    decayedAt: {decayed_at} - This should be removed")
                    
                    if not dry_run:
                        try:
                            # Remove the decayedAt field by updating with None
                            resources_table.update(resource['id'], {'decayedAt': None})
                            log.info(f"    ✅ Fixed - removed decayedAt")
                            type_fixed += 1
                            total_fixed += 1
                        except Exception as e:
                            log.error(f"    ❌ Error fixing resource: {e}")
                    else:
                        log.info(f"    [DRY RUN] Would remove decayedAt")
                        type_fixed += 1
                        total_fixed += 1
            
            log.info(f"  {food_type}: Fixed {type_fixed} resources")
            
        except Exception as e:
            log.error(f"Error processing {food_type}: {e}")
    
    log.info(f"\n{'='*50}")
    log.info(f"Fix complete!")
    log.info(f"Total resources checked: {total_checked}")
    log.info(f"Total resources {'would be' if dry_run else ''} fixed: {total_fixed}")
    
    if dry_run:
        log.info("\nThis was a DRY RUN - no changes were made.")
        log.info("Run without --dry-run to apply the fixes.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix decayedAt bug in food resources")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes"
    )
    
    args = parser.parse_args()
    fix_decayed_at_bug(dry_run=args.dry_run)
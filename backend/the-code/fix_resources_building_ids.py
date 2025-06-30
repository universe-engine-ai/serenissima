#!/usr/bin/env python3
"""
Fix RESOURCES table where Asset field contains record IDs instead of BuildingIds.
This script identifies resources (mainly books) where the Asset field contains 
an Airtable record ID and replaces it with the proper BuildingId from the BUILDINGS table.
"""

import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.append('..')
from dotenv import load_dotenv
from pyairtable import Api

# Load environment variables
load_dotenv('../.env')

def get_building_mapping(api: Api, base_id: str) -> Dict[str, str]:
    """
    Create a mapping of record IDs to BuildingIds from BUILDINGS table.
    Returns: Dictionary mapping record_id -> BuildingId
    """
    buildings_table = api.table(base_id, 'BUILDINGS')
    buildings = buildings_table.all()
    
    mapping = {}
    for building in buildings:
        record_id = building['id']
        fields = building['fields']
        if 'BuildingId' in fields:
            mapping[record_id] = fields['BuildingId']
    
    print(f"Loaded {len(mapping)} building mappings")
    return mapping

def find_problematic_resources(resources_table) -> List[dict]:
    """
    Find all resources where Asset field contains a record ID (starts with 'rec').
    """
    rec_pattern = re.compile(r'^rec[a-zA-Z0-9]+$')
    all_resources = resources_table.all()
    
    problematic = []
    for record in all_resources:
        fields = record['fields']
        if 'Asset' in fields:
            asset = fields['Asset']
            if isinstance(asset, str) and rec_pattern.match(asset):
                problematic.append(record)
    
    return problematic

def fix_resources(api: Api, base_id: str, dry_run: bool = True) -> Tuple[int, int]:
    """
    Fix resources by replacing record IDs with proper BuildingIds.
    
    Args:
        api: Airtable API instance
        base_id: Airtable base ID
        dry_run: If True, only show what would be changed without updating
    
    Returns:
        Tuple of (fixed_count, error_count)
    """
    resources_table = api.table(base_id, 'RESOURCES')
    
    # Get building ID mapping
    building_mapping = get_building_mapping(api, base_id)
    
    # Find problematic resources
    print("\nSearching for resources with record IDs in Asset field...")
    problematic_resources = find_problematic_resources(resources_table)
    print(f"Found {len(problematic_resources)} resources to fix")
    
    if len(problematic_resources) == 0:
        print("No resources need fixing!")
        return (0, 0)
    
    fixed_count = 0
    error_count = 0
    
    # Process each problematic resource
    for i, resource in enumerate(problematic_resources):
        record_id = resource['id']
        fields = resource['fields']
        old_asset = fields['Asset']
        resource_id = fields.get('ResourceId', 'Unknown')
        
        # Check if we have a mapping for this record ID
        if old_asset in building_mapping:
            new_building_id = building_mapping[old_asset]
            
            print(f"\n{i+1}/{len(problematic_resources)}: ResourceId: {resource_id}")
            print(f"  Old Asset (record ID): {old_asset}")
            print(f"  New Asset (BuildingId): {new_building_id}")
            print(f"  Type: {fields.get('Type', 'N/A')}")
            print(f"  Owner: {fields.get('Owner', 'N/A')}")
            
            if not dry_run:
                try:
                    # Update the record
                    updated_fields = {'Asset': new_building_id}
                    resources_table.update(record_id, updated_fields)
                    print(f"  ✓ Updated successfully")
                    fixed_count += 1
                except Exception as e:
                    print(f"  ✗ Error updating: {e}")
                    error_count += 1
            else:
                print(f"  [DRY RUN] Would update to: {new_building_id}")
                fixed_count += 1
        else:
            print(f"\n{i+1}/{len(problematic_resources)}: ResourceId: {resource_id}")
            print(f"  ✗ No building mapping found for record ID: {old_asset}")
            error_count += 1
    
    return (fixed_count, error_count)

def main():
    """Main execution function."""
    print("=== Fix RESOURCES Building IDs ===")
    print(f"Started at: {datetime.now()}")
    
    # Initialize API
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Error: Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID in environment")
        sys.exit(1)
    
    api = Api(api_key)
    
    # First, do a dry run to show what would be changed
    print("\n--- DRY RUN MODE ---")
    fixed, errors = fix_resources(api, base_id, dry_run=True)
    
    print(f"\nDry run complete:")
    print(f"  Would fix: {fixed} resources")
    print(f"  Errors/unmapped: {errors} resources")
    
    if fixed > 0:
        # Apply the changes
        print("\n--- APPLYING CHANGES ---")
        fixed, errors = fix_resources(api, base_id, dry_run=False)
        print(f"\nUpdate complete:")
        print(f"  Fixed: {fixed} resources")
        print(f"  Errors: {errors} resources")
    
    print(f"\nCompleted at: {datetime.now()}")

if __name__ == "__main__":
    main()
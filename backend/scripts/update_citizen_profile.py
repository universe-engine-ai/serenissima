#!/usr/bin/env python3
"""
Update Citizen Profile Script for La Serenissima.

This script takes a JSON input containing updated citizen profile information
and updates the corresponding record in Airtable.

Usage:
    python update_citizen_profile.py --username USERNAME --input INPUT_FILE.json
    python update_citizen_profile.py --username USERNAME --json '{"Personality": "...", ...}'
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pyairtable import Api, Table

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("update_citizen_profile")

# Load environment variables
load_dotenv()

def initialize_airtable():
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID environment variables.")
        return None
    
    try:
        api = Api(api_key)
        base = api.base(base_id)
        # Return a dictionary of table objects using pyairtable
        return {
            'citizens': base.table('CITIZENS')
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        return None

def get_citizen_record(tables, username: str) -> Optional[Dict[str, Any]]:
    """Get citizen record by username."""
    try:
        # Query Airtable for citizen with this username
        matching_citizens = tables['citizens'].all(
            formula=f"{{Username}} = '{username}'"
        )
        
        if not matching_citizens:
            log.error(f"No citizen found with username: {username}")
            return None
        
        return matching_citizens[0]
    except Exception as e:
        log.error(f"Error getting citizen record: {e}")
        return None

def update_citizen_profile(username: str, profile_data: Dict[str, Any], dry_run: bool = False) -> bool:
    """Update citizen profile with new data.
    
    Args:
        username: The username of the citizen to update
        profile_data: Dictionary containing the updated profile data
        dry_run: If True, don't actually update the record
        
    Returns:
        True if successful, False otherwise
    """
    log.info(f"Updating profile for citizen: {username}")
    
    # Initialize Airtable
    tables = initialize_airtable()
    if not tables:
        log.error("Failed to initialize Airtable")
        return False
    
    # Get citizen record
    citizen_record = get_citizen_record(tables, username)
    if not citizen_record:
        return False
    
    # Prepare update data
    update_data = {}
    
    # Map JSON fields to Airtable fields
    field_mapping = {
        "Personality": "Description",  # Personality text goes to Description field
        "CorePersonality": "CorePersonality",  # Store as JSON string
        "familyMotto": "FamilyMotto",
        "coatOfArms": "CoatOfArms",
        "imagePrompt": "ImagePrompt"
    }
    
    for json_field, airtable_field in field_mapping.items():
        if json_field in profile_data:
            value = profile_data[json_field]
            
            # Convert CorePersonality array to JSON string if needed
            if json_field == "CorePersonality" and isinstance(value, list):
                value = json.dumps(value)
            
            update_data[airtable_field] = value
    
    if not update_data:
        log.warning("No valid fields to update")
        return False
    
    # Log the update data
    log.info(f"Update data: {json.dumps(update_data, indent=2)}")
    
    if dry_run:
        log.info("[DRY RUN] Would update citizen record")
        return True
    
    try:
        # Update the record
        tables['citizens'].update(citizen_record['id'], update_data)
        log.info(f"Successfully updated profile for {username}")
        
        # Optionally trigger image generation if imagePrompt was provided
        if "imagePrompt" in profile_data:
            log.info("Image prompt was provided, consider running updatecitizenDescriptionAndImage.py to generate a new image")
        
        return True
    except Exception as e:
        log.error(f"Error updating citizen profile: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Update citizen profile")
    parser.add_argument("--username", required=True, help="Username of the citizen to update")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Path to JSON input file")
    group.add_argument("--json", help="JSON string with profile data")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually update the record")
    
    args = parser.parse_args()
    
    # Load profile data
    profile_data = None
    if args.input:
        try:
            with open(args.input, 'r') as f:
                profile_data = json.load(f)
        except Exception as e:
            log.error(f"Error loading input file: {e}")
            sys.exit(1)
    elif args.json:
        try:
            profile_data = json.loads(args.json)
        except Exception as e:
            log.error(f"Error parsing JSON string: {e}")
            sys.exit(1)
    
    # Update profile
    success = update_citizen_profile(args.username, profile_data, args.dry_run)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Neighborhood Watch Stratagem Creator

Creates neighborhood watch stratagems to enhance security in specific districts.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors
)

log = logging.getLogger(__name__)

# Valid districts in La Serenissima
VALID_DISTRICTS = [
    "San Marco",
    "San Polo", 
    "Dorsoduro",
    "Santa Croce",
    "Cannaregio",
    "Castello"
]

def try_create(
    tables: Dict[str, Any],
    citizen_username: str,
    stratagem_type: str,
    stratagem_params: Dict[str, Any],
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a neighborhood_watch stratagem.
    
    Expected stratagem_params:
    - districtName (str, required): The district to establish watch in
    - name (str, optional): Custom name
    - description (str, optional): Custom description
    - notes (str, optional): Additional notes
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")
    
    if stratagem_type != "neighborhood_watch":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'neighborhood_watch' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None
    
    # Extract parameters
    district_name = stratagem_params.get('districtName')
    
    # Custom fields
    custom_name = stratagem_params.get('name')
    custom_description = stratagem_params.get('description')
    custom_notes = stratagem_params.get('notes', '')
    
    # Validation
    if not district_name:
        log.error(f"{LogColors.FAIL}districtName is required for neighborhood_watch stratagem{LogColors.ENDC}")
        return None
    
    # Normalize district name for comparison (handle case variations)
    normalized_district = district_name.strip()
    valid_district_found = False
    for valid in VALID_DISTRICTS:
        if valid.lower() == normalized_district.lower():
            district_name = valid  # Use the proper casing
            valid_district_found = True
            break
    
    if not valid_district_found:
        log.error(f"{LogColors.FAIL}Invalid district '{district_name}'. Valid districts are: {', '.join(VALID_DISTRICTS)}{LogColors.ENDC}")
        return None
    
    # Check if the citizen has property or residence in the district
    try:
        # Check for owned buildings
        building_formula = f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', {{DistrictLocation}}='{_escape_airtable_value(district_name)}')"
        owned_buildings = tables['buildings'].all(formula=building_formula)
        
        # Check for residence (citizen's residence field)
        citizen_formula = f"{{Username}}='{_escape_airtable_value(citizen_username)}'"
        citizen_records = tables['citizens'].all(formula=citizen_formula, max_records=1)
        
        if not citizen_records:
            log.error(f"{LogColors.FAIL}Citizen '{citizen_username}' not found{LogColors.ENDC}")
            return None
        
        citizen_district = citizen_records[0]['fields'].get('DistrictResidence')
        
        # Citizen must have connection to the district (own property or live there)
        if not owned_buildings and citizen_district != district_name:
            log.warning(f"{LogColors.WARNING}Citizen {citizen_username} has no property or residence in {district_name}{LogColors.ENDC}")
            # Still allow creation but with a warning in notes
            custom_notes += f"\nWarning: Citizen has no direct connection to {district_name}"
    
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error verifying citizen's connection to district: {e}{LogColors.ENDC}")
        return None
    
    # Generate stratagem ID
    stratagem_id = f"neighborhood_watch_{citizen_username}_{district_name.replace(' ', '_')}_{int(now_utc_dt.timestamp())}"
    
    # Calculate expiration (45 days)
    expires_at = now_utc_dt + timedelta(days=45)
    
    # Build stratagem payload
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": "neighborhood_watch",
        "Variant": "community_organized",
        "ExecutedBy": citizen_username,
        "TargetBuilding": district_name,  # Store district in TargetBuilding field
        "Status": "active",
        "Category": "security",
        "Name": custom_name or f"Neighborhood Watch for {district_name}",
        "Description": custom_description or f"{citizen_username} organizes citizen vigilance to improve security in {district_name}",
        "Notes": json.dumps({
            "initial_notes": custom_notes.strip(),
            "district_name": district_name,
            "created_at": now_utc_dt.isoformat(),
            "duration_days": 45
        }),
        "InfluenceCost": 0,  # Influence costs removed
        "CreatedAt": now_utc_dt.isoformat(),
        "ExpiresAt": expires_at.isoformat()
    }
    
    log.info(f"{LogColors.OKGREEN}Successfully prepared neighborhood_watch stratagem: {stratagem_id}{LogColors.ENDC}")
    
    # Return list of stratagems to create
    return [stratagem_payload]
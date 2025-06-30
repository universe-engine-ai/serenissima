"""
Stratagem Creator for "organize_gathering".
Creates social gatherings that become temporary leisure activities for citizens.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors,
    get_building_record
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime,
    api_base_url: Optional[str] = None,
    transport_api_url: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates an "organize_gathering" stratagem.

    Expected stratagem_params:
    - location (str, required): BuildingId where the gathering will occur
    - theme (str, optional): Type of gathering - political, cultural, economic, social. Defaults to "social"
    - startTime (str, optional): When gathering begins in HH:MM format (Venice time). Defaults to 2 hours from now
    - durationHours (int, optional): Duration in hours. Defaults to 3
    - inviteList (List[str], optional): Specific citizens to notify
    - description (str, optional): What the gathering is about
    - name (str, optional): Custom name for the gathering
    - notes (str, optional): Additional notes
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "organize_gathering":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'organize_gathering' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    # Validate required parameters
    location_building_id = stratagem_params.get("location")
    if not location_building_id:
        log.error(f"{LogColors.FAIL}Location (BuildingId) is required for organize_gathering stratagem.{LogColors.ENDC}")
        return None

    # Verify the building exists and is suitable for gatherings
    building_record = get_building_record(tables, location_building_id)
    if not building_record:
        log.error(f"{LogColors.FAIL}Building {location_building_id} not found.{LogColors.ENDC}")
        return None
    
    building_type = building_record['fields'].get('Type')
    building_name = building_record['fields'].get('Name', building_type)
    
    # Check if building type allows public gatherings
    allowed_gathering_types = [
        "inn", "piazza", "palazzo", "merchant_s_house",
        "church", "library", "market", "arsenal",
        "great_palazzo", "grand_piazza", "townhall", 
        "guild_hall", "public_forum", "assembly_hall",
        "doge_s_palace"  # Allow gatherings at the Doge's Palace for important civic events
    ]
    
    if building_type not in allowed_gathering_types:
        log.error(f"{LogColors.FAIL}Building type {building_type} does not allow public gatherings.{LogColors.ENDC}")
        return None

    # Parse gathering parameters
    theme = stratagem_params.get("theme", "social")
    invite_list = stratagem_params.get("inviteList", [])
    description = stratagem_params.get("description", f"A {theme} gathering organized by {citizen_username}")
    
    # Handle start time
    start_time_str = stratagem_params.get("startTime")
    if start_time_str:
        try:
            # Parse HH:MM format and create datetime for today
            hour, minute = map(int, start_time_str.split(':'))
            start_dt = now_venice_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # If the time has already passed today, schedule for tomorrow
            if start_dt <= now_venice_dt:
                start_dt += timedelta(days=1)
        except Exception as e:
            log.warning(f"Invalid startTime format: {start_time_str}. Using default.")
            start_dt = now_venice_dt + timedelta(hours=2)
    else:
        # Default to 2 hours from now
        start_dt = now_venice_dt + timedelta(hours=2)
    
    # Convert to UTC for storage
    start_utc = start_dt.astimezone(datetime.now().astimezone().tzinfo)
    
    # Duration
    duration_hours = int(stratagem_params.get("durationHours", 3))
    end_utc = start_utc + timedelta(hours=duration_hours)
    
    # Generate unique ID
    stratagem_id = f"stratagem-gather-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    # Create gathering name
    theme_names = {
        "political": "Political Assembly",
        "cultural": "Cultural Salon", 
        "economic": "Merchant Gathering",
        "social": "Social Gathering"
    }
    
    default_name = f"{theme_names.get(theme, 'Gathering')} at {building_name}"
    name = stratagem_params.get("name", default_name)
    
    # Prepare gathering data for Notes field
    gathering_data = {
        "location": location_building_id,
        "buildingName": building_name,
        "buildingType": building_type,
        "theme": theme,
        "startTime": start_utc.isoformat(),
        "endTime": end_utc.isoformat(),
        "veniceStartTime": start_dt.strftime("%Y-%m-%d %H:%M"),
        "inviteList": invite_list,
        "attendance": [],  # Will track who attends
        "messagesDelivered": []  # Track public messages during gathering
    }
    
    # Create stratagem payload
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "social",
        "ExecutedBy": citizen_username,
        "Status": "active",
        "ExecutedAt": None,  # Will be set when first person arrives
        "ExpiresAt": end_utc.isoformat(),
        "Description": description,
        "Notes": json.dumps(gathering_data),
        "TargetBuilding": location_building_id,
        "Variant": theme  # Store theme as variant for easy filtering
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Created 'organize_gathering' stratagem '{stratagem_id}' at {building_name}{LogColors.ENDC}")
    log.info(f"{LogColors.STRATAGEM_CREATOR}Gathering scheduled for {start_dt.strftime('%Y-%m-%d %H:%M')} Venice time{LogColors.ENDC}")
    
    return [stratagem_payload]
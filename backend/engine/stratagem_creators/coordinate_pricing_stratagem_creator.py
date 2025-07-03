"""
Stratagem Creator for "coordinate_pricing".

This creator is responsible for generating "coordinate_pricing" stratagems.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "coordinate_pricing" stratagem.

    Expected stratagem_params:
    - targetResourceType (str, required): Resource type ID to target.
    - targetCitizen (str, optional): Username of the citizen whose prices to coordinate with.
    - targetBuilding (str, optional): BuildingId of the building whose prices to coordinate with.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration of the stratagem in hours. Defaults to 24.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "coordinate_pricing":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'coordinate_pricing' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_resource_type = stratagem_params.get("targetResourceType") # Now optional
    target_citizen = stratagem_params.get("targetCitizen")
    target_building = stratagem_params.get("targetBuilding")

    # TargetResourceType is now optional. If not provided, the processor will handle coordinating all sellable resources.
    if not target_resource_type and not target_citizen and not target_building:
        log.warning(f"{LogColors.WARNING}Coordinate_pricing stratagem initiated without specific resource, citizen, or building. Will target general market for all sellable resources.{LogColors.ENDC}")
    elif not target_resource_type:
        log.info(f"{LogColors.STRATAGEM_CREATOR}Coordinate_pricing stratagem initiated without specific resource. Will target selected citizen/building for all sellable resources.{LogColors.ENDC}")
    
    # While targetCitizen or targetBuilding are optional for the stratagem's flexibility (i.e. target general market),
    # the current design implies coordinating *with* someone or a specific entity if these are provided.
    # If neither is provided, it means coordinating with the general market average for the resource.

    stratagem_id = f"stratagem-{stratagem_type.lower()}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name_resource_part = target_resource_type if target_resource_type else "All Resources"
    name_target_part = name_resource_part
    
    if target_citizen:
        name_target_part = f"{name_resource_part} with {target_citizen}"
    elif target_building:
        name_target_part = f"{name_resource_part} at {target_building}"
    # If neither citizen nor building, it's general market for the resource part.
    
    name = stratagem_params.get("name") or f"Coordinate Pricing for {name_target_part}"
    description = stratagem_params.get("description") or f"{citizen_username} is attempting to coordinate prices for {name_target_part}."
    
    duration_hours = int(stratagem_params.get("durationHours", 24))
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        # "Variant": None, # No variant for this type
        "Name": name,
        "Category": "economic_cooperation", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", "")
    }

    if target_resource_type: # Only add if specified
        stratagem_payload["TargetResourceType"] = target_resource_type
    if target_citizen:
        stratagem_payload["TargetCitizen"] = target_citizen
    if target_building:
        stratagem_payload["TargetBuilding"] = target_building
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'coordinate_pricing' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

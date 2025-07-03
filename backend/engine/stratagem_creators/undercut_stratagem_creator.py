"""
Stratagem Creator for "undercut".

This creator is responsible for generating "undercut" stratagems.
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
    tables: Dict[str, Any], # Airtable tables
    citizen_username: str, # Username of the citizen executing the stratagem
    stratagem_type: str, # Should be "undercut"
    stratagem_params: Dict[str, Any], # Parameters specific to this stratagem
    # Common time parameters (though not all might be used by every creator)
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]: # Returns a list of stratagem payloads to be created, or None on failure
    """
    Creates an "undercut" stratagem.

    Expected stratagem_params:
    - variant (str): "Mild", "Standard", "Aggressive" (determines undercut percentage)
    - targetCitizen (str, optional): Username of the citizen to target.
    - targetBuilding (str, optional): BuildingId of the building to target.
    - targetResourceType (str, optional): Resource type ID to target.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration of the stratagem in hours. Defaults to 24.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "undercut":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'undercut' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    variant = stratagem_params.get("variant")
    if variant not in ["Mild", "Standard", "Aggressive"]:
        log.error(f"{LogColors.FAIL}Invalid variant '{variant}' for undercut stratagem. Must be Mild, Standard, or Aggressive.{LogColors.ENDC}")
        return None

    target_citizen = stratagem_params.get("targetCitizen")
    target_building = stratagem_params.get("targetBuilding")
    target_resource_type = stratagem_params.get("targetResourceType")

    if not target_citizen and not target_building and not target_resource_type:
        log.error(f"{LogColors.FAIL}At least one target (citizen, building, or resource type) must be specified for undercut stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower()}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    name = stratagem_params.get("name") or f"Undercut {target_resource_type or 'prices'} ({variant})"
    description = stratagem_params.get("description") or f"{citizen_username} is attempting to undercut competition for {target_resource_type or 'various resources'} with a {variant.lower()} approach."
    
    duration_hours = int(stratagem_params.get("durationHours", 24))
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Variant": variant,
        "Name": name,
        "Category": "economic_warfare", # Example category
        "ExecutedBy": citizen_username,
        "Status": "active", # Start active, processor will handle execution
        # "CreatedAt": now_utc_dt.isoformat(), # Airtable gère ce champ automatiquement
        # "UpdatedAt": now_utc_dt.isoformat(), # Airtable gère ce champ automatiquement
        "ExecutedAt": None, # To be set by processor upon first execution
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", "")
    }

    if target_citizen:
        stratagem_payload["TargetCitizen"] = target_citizen
    if target_building:
        stratagem_payload["TargetBuilding"] = target_building
    if target_resource_type:
        stratagem_payload["TargetResourceType"] = target_resource_type
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'undercut' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    # This creator returns a list containing a single stratagem payload.
    # The main engine loop (or API endpoint handler) will take this payload and create the Airtable record.
    return [stratagem_payload]

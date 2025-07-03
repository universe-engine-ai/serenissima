"""
Stratagem Creator for "reputation_assault".

This creator is responsible for generating "reputation_assault" stratagems.
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
    now_utc_dt: datetime,
    api_base_url: Optional[str] = None, # Added for consistency
    transport_api_url: Optional[str] = None # Added for consistency
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "reputation_assault" stratagem.

    Expected stratagem_params:
    - targetCitizen (str, required): Username of the competitor to target.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - assaultAngle (str, optional): Specific angle or theme for the assault.
    - kinosModelOverride (str, optional): Specific KinOS model to use for the executor's messages.
    - durationHours (int, optional): Duration of the stratagem in hours. Defaults to 24.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "reputation_assault":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'reputation_assault' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_citizen = stratagem_params.get("targetCitizen")
    if not target_citizen:
        log.error(f"{LogColors.FAIL}TargetCitizen must be specified for reputation_assault stratagem.{LogColors.ENDC}")
        return None
    
    if target_citizen == citizen_username:
        log.error(f"{LogColors.FAIL}Cannot target oneself for reputation_assault stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name") or f"Reputation Assault on {target_citizen}"
    description = stratagem_params.get("description") or f"{citizen_username} is attempting to damage the reputation of {target_citizen}."
    assault_angle = stratagem_params.get("assaultAngle")
    kinos_model_override = stratagem_params.get("kinosModelOverride")
    
    duration_hours = int(stratagem_params.get("durationHours", 24))
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "social_warfare", 
        "ExecutedBy": citizen_username,
        "TargetCitizen": target_citizen,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", "") # Base notes
        # InfluenceCost is not set here
    }

    current_notes = stratagem_payload["Notes"]
    if assault_angle:
        current_notes = f"Angle: {assault_angle}\n{current_notes}".strip()
    if kinos_model_override:
        current_notes = f"KinosModelOverride: {kinos_model_override}\n{current_notes}".strip()
    
    stratagem_payload["Notes"] = current_notes
    # Alternatively, create a new field like "StratagemSpecificParams" if schema allows
    # For now, prepending to Notes is a common pattern.
    # stratagem_payload["StratagemSpecificParams"] = json.dumps({"assaultAngle": assault_angle, "kinosModelOverride": kinos_model_override})

    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'reputation_assault' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

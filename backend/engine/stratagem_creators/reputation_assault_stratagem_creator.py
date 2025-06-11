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
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "reputation_assault" stratagem.

    Expected stratagem_params:
    - targetCitizen (str, required): Username of the competitor to target.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
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
        "Notes": stratagem_params.get("notes", "")
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'reputation_assault' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

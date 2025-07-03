"""
Stratagem Creator for "maritime_blockade".
(Coming Soon)
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

BASE_INFLUENCE_COST = 70 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "maritime_blockade" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetCompetitorBuilding (str, optional): BuildingId of a competitor's waterfront building (e.g., dock, arsenal gate).
    - targetCompetitorCitizen (str, optional): Username of the competitor to target.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 72 (3 days).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Maritime Blockade - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "maritime_blockade":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'maritime_blockade' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_building = stratagem_params.get("targetCompetitorBuilding") # UI might send as targetBuilding
    if not target_building: # Fallback if UI sends generic targetBuilding
        target_building = stratagem_params.get("targetBuilding")

    target_citizen = stratagem_params.get("targetCompetitorCitizen") # UI might send as targetCitizen
    if not target_citizen: # Fallback if UI sends generic targetCitizen
        target_citizen = stratagem_params.get("targetCitizen")


    if not target_building and not target_citizen:
        log.error(f"{LogColors.FAIL}At least one target (competitor building or citizen) must be specified for maritime_blockade stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    target_display_parts = []
    if target_building:
        target_display_parts.append(f"building: {target_building}")
    if target_citizen:
        target_display_parts.append(f"citizen: {target_citizen}")
    target_display = "; ".join(target_display_parts)

    name = stratagem_params.get("name") or f"Maritime Blockade on {target_display}"
    description = stratagem_params.get("description") or f"{citizen_username} is initiating a maritime blockade targeting {target_display}."
    
    duration_hours = int(stratagem_params.get("durationHours", 72)) # Default to 3 days
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "economic_warfare", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", f"Targeting: {target_display}. Influence Cost: {BASE_INFLUENCE_COST}"),
        "InfluenceCost": BASE_INFLUENCE_COST
    }
    if target_building:
        stratagem_payload["TargetBuilding"] = target_building
    if target_citizen:
        stratagem_payload["TargetCitizen"] = target_citizen
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'maritime_blockade' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

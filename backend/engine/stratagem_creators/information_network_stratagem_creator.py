"""
Stratagem Creator for "information_network".
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

BASE_INFLUENCE_COST = 40 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates an "information_network" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetCitizens (List[str], optional): Usernames of specific citizens to target for information.
    - targetSectors (List[str], optional): Market sectors or geographical areas to target.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 168 (7 days).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Information Network - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "information_network":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'information_network' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_citizens = stratagem_params.get("targetCitizens", [])
    target_sectors = stratagem_params.get("targetSectors", [])

    if not target_citizens and not target_sectors:
        log.error(f"{LogColors.FAIL}At least one target (citizens or sectors) must be specified for information_network stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    target_display_parts = []
    if target_citizens:
        target_display_parts.append(f"citizens: {', '.join(target_citizens[:2])}{'...' if len(target_citizens) > 2 else ''}")
    if target_sectors:
        target_display_parts.append(f"sectors: {', '.join(target_sectors[:2])}{'...' if len(target_sectors) > 2 else ''}")
    target_display = "; ".join(target_display_parts) or "general targets"


    name = stratagem_params.get("name") or f"Information Network ({target_display})"
    description = stratagem_params.get("description") or f"{citizen_username} is establishing an information network targeting {target_display}."
    
    duration_hours = int(stratagem_params.get("durationHours", 168)) # Default to 7 days
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "intelligence", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", f"Targets: {target_display}. Influence Cost: {BASE_INFLUENCE_COST}"),
        # Specific fields for information_network
        "TargetCitizens": json.dumps(target_citizens) if target_citizens else None, # Store as JSON string
        "TargetSectors": json.dumps(target_sectors) if target_sectors else None,   # Store as JSON string
        "InfluenceCost": BASE_INFLUENCE_COST 
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'information_network' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

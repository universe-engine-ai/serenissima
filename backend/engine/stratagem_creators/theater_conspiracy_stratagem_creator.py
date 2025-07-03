"""
Stratagem Creator for "theater_conspiracy".
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

BASE_INFLUENCE_COST = 25 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "theater_conspiracy" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetTheaterId (str, required): The BuildingId of the theater.
    - politicalTheme (str, required): e.g., "satirize_competitor", "promote_policy", "glorify_patron".
    - targetCompetitor (str, optional): Username of the competitor to satirize.
    - targetPolicy (str, optional): Name/ID of the policy to promote.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 168 (7 days).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Theater Conspiracy - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "theater_conspiracy":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'theater_conspiracy' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_theater_id = stratagem_params.get("targetTheaterId")
    political_theme = stratagem_params.get("politicalTheme")

    if not target_theater_id or not political_theme:
        log.error(f"{LogColors.FAIL}Missing required parameters (targetTheaterId, politicalTheme) for theater_conspiracy stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name") or f"Theatrical Conspiracy: {political_theme}"
    description = stratagem_params.get("description") or f"{citizen_username} is initiating a theatrical conspiracy at {target_theater_id} with the theme '{political_theme}'."
    
    duration_hours = int(stratagem_params.get("durationHours", 168)) # Default to 7 days
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "social_warfare", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", f"Theme: {political_theme}. Influence Cost: {BASE_INFLUENCE_COST}"),
        # Specific fields for theater_conspiracy
        "TargetBuilding": target_theater_id, # Use generic TargetBuilding for the theater
        "PoliticalTheme": political_theme,
        "TargetCompetitor": stratagem_params.get("targetCompetitor"),
        "TargetPolicy": stratagem_params.get("targetPolicy"),
        "InfluenceCost": BASE_INFLUENCE_COST
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'theater_conspiracy' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

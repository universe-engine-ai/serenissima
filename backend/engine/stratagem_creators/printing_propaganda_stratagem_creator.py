"""
Stratagem Creator for "printing_propaganda".
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

BASE_INFLUENCE_COST = 30 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "printing_propaganda" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetPrintingHouseId (str, required): The BuildingId of the printing house.
    - targetCompetitor (str, required): Username of the competitor to target.
    - propagandaTheme (str, optional): e.g., "financial_mismanagement", "scandalous_rumors".
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 168 (7 days).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Printing Propaganda - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "printing_propaganda":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'printing_propaganda' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_printing_house_id = stratagem_params.get("targetPrintingHouseId")
    target_competitor = stratagem_params.get("targetCompetitor")

    if not target_printing_house_id or not target_competitor:
        log.error(f"{LogColors.FAIL}Missing required parameters (targetPrintingHouseId, targetCompetitor) for printing_propaganda stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    propaganda_theme = stratagem_params.get("propagandaTheme", "General Disinformation")
    
    name = stratagem_params.get("name") or f"Propaganda Campaign vs {target_competitor}"
    description = stratagem_params.get("description") or f"{citizen_username} is initiating a propaganda campaign against {target_competitor} from {target_printing_house_id}."
    
    duration_hours = int(stratagem_params.get("durationHours", 168)) # Default to 7 days
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "information_warfare", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", f"Theme: {propaganda_theme}. Influence Cost: {BASE_INFLUENCE_COST}"),
        # Specific fields for printing_propaganda
        "TargetBuilding": target_printing_house_id, # The printing house used
        "TargetCitizen": target_competitor, # The competitor being targeted
        "PropagandaTheme": propaganda_theme,
        "InfluenceCost": BASE_INFLUENCE_COST
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'printing_propaganda' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

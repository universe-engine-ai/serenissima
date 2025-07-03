"""
Stratagem Creator for "cultural_patronage".
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

BASE_INFLUENCE_COST = 30 # Base cost, can be adjusted with variants later

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "cultural_patronage" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetArtist (str, optional): Username of the artist to patronize.
    - targetPerformanceId (str, optional): ID of a specific performance to sponsor.
    - targetInstitutionId (str, optional): BuildingId of a cultural institution to support.
    - patronageLevel (str, optional): e.g., "Modest", "Significant", "Grand". Defaults to "Standard".
    - name (str, optional): Custom name.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 168 (7 days).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Cultural Patronage - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "cultural_patronage":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'cultural_patronage' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_artist = stratagem_params.get("targetArtist")
    target_performance_id = stratagem_params.get("targetPerformanceId")
    target_institution_id = stratagem_params.get("targetInstitutionId")

    if not target_artist and not target_performance_id and not target_institution_id:
        log.error(f"{LogColors.FAIL}At least one target (Artist, Performance, or Institution) must be specified for cultural_patronage stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    target_display = target_artist or target_performance_id or target_institution_id or "Cultural Endeavor"
    patronage_level = stratagem_params.get("patronageLevel", "Standard")

    name = stratagem_params.get("name") or f"Patronage: {target_display} ({patronage_level})"
    description = stratagem_params.get("description") or f"{citizen_username} is initiating a cultural patronage for {target_display} at a {patronage_level} level."
    
    duration_hours = int(stratagem_params.get("durationHours", 168)) # Default to 7 days
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    # Adjust influence cost based on level if implemented, for now use base
    influence_cost = BASE_INFLUENCE_COST 
    # if patronage_level == "Significant": influence_cost *= 1.5
    # if patronage_level == "Grand": influence_cost *= 2

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "cultural_influence", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", f"Patronage Level: {patronage_level}. Est. Influence Cost: {influence_cost}"),
        # Specific fields for cultural_patronage
        "TargetArtist": target_artist,
        "TargetPerformanceId": target_performance_id,
        "TargetInstitutionId": target_institution_id,
        "PatronageLevel": patronage_level,
        "InfluenceCost": influence_cost # Store calculated cost
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'cultural_patronage' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

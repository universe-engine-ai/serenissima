"""
Stratagem Creator for "marketplace_gossip".
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

BASE_INFLUENCE_COST = 5 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "marketplace_gossip" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetCitizen (str, required): The username of the competitor to target.
    - gossipTheme (str, optional): e.g., "questionable_business_practices", "personal_scandal".
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 48 (2 days).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Marketplace Gossip - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "marketplace_gossip":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'marketplace_gossip' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_citizen = stratagem_params.get("targetCitizen")
    if not target_citizen:
        log.error(f"{LogColors.FAIL}Missing required parameter (targetCitizen) for marketplace_gossip stratagem.{LogColors.ENDC}")
        return None

    if target_citizen == citizen_username:
        log.error(f"{LogColors.FAIL}Cannot target oneself for marketplace_gossip stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    gossip_theme = stratagem_params.get("gossipTheme", "General Rumors")
    
    name = stratagem_params.get("name") or f"Gossip Campaign vs {target_citizen}"
    description = stratagem_params.get("description") or f"{citizen_username} is initiating a gossip campaign against {target_citizen}."
    
    duration_hours = int(stratagem_params.get("durationHours", 48)) # Default to 2 days
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
        "Notes": stratagem_params.get("notes", f"Theme: {gossip_theme}. Influence Cost: {BASE_INFLUENCE_COST}"),
        # Specific fields for marketplace_gossip
        "TargetCitizen": target_citizen,
        "GossipTheme": gossip_theme,
        "InfluenceCost": BASE_INFLUENCE_COST
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'marketplace_gossip' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

"""
Stratagem Creator for "political_campaign".

This creator is responsible for generating "political_campaign" stratagems.
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

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "political_campaign" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetDecreeName (str, required): Name/ID of the decree to target.
    - desiredOutcome (str, required): e.g., "pass", "repeal", "amend_strength_low".
    - campaignMessage (str, required): Core message of the campaign.
    - lobbyingBudget (int, optional): Ducats for lobbying. Defaults to 0.
    - campaignDurationDays (int, optional): Duration in days. Defaults to 14.
    - name (str, optional): Custom name.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Political Campaign - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "political_campaign":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'political_campaign' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_decree_name = stratagem_params.get("targetDecreeName")
    desired_outcome = stratagem_params.get("desiredOutcome")
    campaign_message = stratagem_params.get("campaignMessage")

    if not target_decree_name or not desired_outcome or not campaign_message:
        log.error(f"{LogColors.FAIL}Missing required parameters (targetDecreeName, desiredOutcome, campaignMessage) for political_campaign stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name") or f"Campaign: {desired_outcome} '{target_decree_name}'"
    description = stratagem_params.get("description") or f"{citizen_username} is running a political campaign to {desired_outcome} the decree '{target_decree_name}'. Message: {campaign_message[:100]}..."
    
    duration_days = int(stratagem_params.get("campaignDurationDays", 14))
    duration_hours = duration_days * 24
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    lobbying_budget = int(stratagem_params.get("lobbyingBudget", 0))

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "political_influence", 
        "ExecutedBy": citizen_username,
        "Status": "active", # Processor will manage this
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", f"Lobbying Budget: {lobbying_budget} Ducats."),
        # Specific fields for political_campaign
        "TargetDecreeName": target_decree_name,
        "DesiredOutcome": desired_outcome,
        "CampaignMessage": campaign_message,
        "LobbyingBudget": lobbying_budget
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'political_campaign' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    # This creator returns a list containing a single stratagem payload.
    return [stratagem_payload]

"""
Stratagem Creator for "joint_venture".
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

BASE_INFLUENCE_COST = 20 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "joint_venture" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetPartnerUsername (str, required): The username of the citizen to propose the venture to.
    - ventureDetails (str, required): A description of the venture, contributions, and responsibilities.
    - profitSharingPercentage (float, optional): The profit share for the initiator (e.g., 0.5 for 50%). Defaults to 0.5.
    - durationDays (int, optional): Duration of the venture in days. Defaults to 30.
    - name (str, optional): Custom name for the stratagem.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Joint Venture - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "joint_venture":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'joint_venture' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_partner = stratagem_params.get("targetPartnerUsername")
    venture_details = stratagem_params.get("ventureDetails")

    if not target_partner or not venture_details:
        log.error(f"{LogColors.FAIL}Missing required parameters (targetPartnerUsername, ventureDetails) for joint_venture stratagem.{LogColors.ENDC}")
        return None

    if target_partner == citizen_username:
        log.error(f"{LogColors.FAIL}Cannot propose a joint venture to oneself.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    profit_share = float(stratagem_params.get("profitSharingPercentage", 0.5))
    duration_days = int(stratagem_params.get("durationDays", 30))
    duration_hours = duration_days * 24
    
    name = stratagem_params.get("name") or f"Joint Venture with {target_partner}"
    description = stratagem_params.get("description") or f"{citizen_username} is proposing a joint venture to {target_partner}. Details: {venture_details[:100]}..."
    
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "economic_cooperation", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": f"Partner: {target_partner}, Profit Share (for initiator): {profit_share*100}%, Duration: {duration_days} days. Details: {venture_details}",
        # Specific fields for joint_venture
        "TargetCitizen": target_partner,
        "VentureDetails": venture_details,
        "ProfitSharingPercentage": profit_share,
        "InfluenceCost": BASE_INFLUENCE_COST
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'joint_venture' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

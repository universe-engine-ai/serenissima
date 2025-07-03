"""
Stratagem Creator for "cargo_mishap".
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

BASE_INFLUENCE_COST = 8 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "cargo_mishap" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetContractId (str, required): The ContractId of the competitor's shipment to target.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 24 (the mishap happens within this window).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Cargo 'Mishap' - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "cargo_mishap":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'cargo_mishap' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_contract_id = stratagem_params.get("targetContractId")

    if not target_contract_id:
        log.error(f"{LogColors.FAIL}Missing required parameter (targetContractId) for cargo_mishap stratagem.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name") or f"Cargo 'Mishap' on {target_contract_id}"
    description = stratagem_params.get("description") or f"{citizen_username} is arranging for a cargo 'mishap' to affect contract {target_contract_id}."
    
    duration_hours = int(stratagem_params.get("durationHours", 24)) # Default to 1 day for the window of opportunity
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
        "Notes": stratagem_params.get("notes", f"Targeting contract: {target_contract_id}. Influence Cost: {BASE_INFLUENCE_COST}"),
        # Specific fields for cargo_mishap
        "TargetContract": target_contract_id, # Use a specific field for the contract
        "InfluenceCost": BASE_INFLUENCE_COST
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'cargo_mishap' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

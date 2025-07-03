"""
Stratagem Creator for "emergency_liquidation".

This creator is responsible for generating "emergency_liquidation" stratagems.
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

VALID_VARIANTS = {
    "Mild": {"discount_percentage": 0.20, "duration_hours": 24}, # Sells at 80% of market rate
    "Standard": {"discount_percentage": 0.30, "duration_hours": 48}, # Sells at 70% of market rate
    "Aggressive": {"discount_percentage": 0.40, "duration_hours": 72}  # Sells at 60% of market rate
}

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates an "emergency_liquidation" stratagem.

    Expected stratagem_params:
    - variant (str): "Mild", "Standard", "Aggressive". Determines discount and duration.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "emergency_liquidation":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'emergency_liquidation' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    variant_name = stratagem_params.get("variant")
    if variant_name not in VALID_VARIANTS:
        log.error(f"{LogColors.FAIL}Invalid variant '{variant_name}' for emergency_liquidation. Must be one of {list(VALID_VARIANTS.keys())}.{LogColors.ENDC}")
        return None

    variant_details = VALID_VARIANTS[variant_name]
    duration_hours = variant_details["duration_hours"]
    
    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name") or f"Emergency Liquidation ({variant_name})"
    description = stratagem_params.get("description") or f"{citizen_username} is initiating an emergency liquidation of assets ({variant_name.lower()} discount)."
    
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Variant": variant_name, # Store the variant name
        "Name": name,
        "Category": "personal_finance", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", "")
        # No TargetCitizen, TargetBuilding, TargetResourceType for this type
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'emergency_liquidation' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

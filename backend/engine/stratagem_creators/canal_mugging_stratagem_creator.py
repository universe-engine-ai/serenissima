import logging
import uuid
import json # Added for storing details in Notes
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List # Added List

from pyairtable import Table

from backend.engine.utils.activity_helpers import (
    LogColors,
    VENICE_TIMEZONE, # Not directly used here, but good practice for consistency
    get_citizen_record,
    get_land_record, 
    _escape_airtable_value
)
from backend.engine.utils.notification_helpers import create_notification

log = logging.getLogger(__name__)

STRATAGEM_TYPE = "canal_mugging"
INFLUENCE_COST_PER_DAY = 1
DEFAULT_DURATION_DAYS = 3
MIN_DURATION_DAYS = 1
MAX_DURATION_DAYS = 7

VALID_VARIANTS = ["Mild", "Standard", "Aggressive"]

def try_create(
    tables: Dict[str, Table],
    citizen_username: str,
    stratagem_type: str, # Added stratagem_type
    stratagem_params: Dict[str, Any],
    now_venice_dt: datetime, # Added now_venice_dt
    now_utc_dt: datetime, # Added now_utc_dt
    api_base_url: Optional[str] = None, # Added for consistency
    transport_api_url: Optional[str] = None # Added for consistency
) -> Optional[List[Dict[str, Any]]]:
    """
    Prepares the payload for a 'canal_mugging' stratagem.
    Does not create the record in Airtable directly.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Preparing '{stratagem_type}' stratagem payload for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != STRATAGEM_TYPE: # STRATAGEM_TYPE is "canal_mugging"
        log.error(f"{LogColors.FAIL}Stratagem creator for '{STRATAGEM_TYPE}' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    # Citizen record and influence check will be handled by the main API endpoint or a pre-check step if needed.
    # For now, this creator focuses on payload generation assuming basic validation passed.

    variant = stratagem_params.get("variant")
    if not variant or variant not in VALID_VARIANTS:
        log.error(f"{LogColors.FAIL}Invalid or missing 'variant' for {STRATAGEM_TYPE}. Must be one of {VALID_VARIANTS}. Params: {stratagem_params}{LogColors.ENDC}")
        return None # Indicate failure to the caller

    try:
        duration_days = int(stratagem_params.get("durationDays", DEFAULT_DURATION_DAYS))
        if not (MIN_DURATION_DAYS <= duration_days <= MAX_DURATION_DAYS):
            log.error(f"{LogColors.FAIL}Invalid 'durationDays' for {STRATAGEM_TYPE}. Must be between {MIN_DURATION_DAYS} and {MAX_DURATION_DAYS}. Params: {stratagem_params}{LogColors.ENDC}")
            return None
    except ValueError:
        log.error(f"{LogColors.FAIL}Invalid 'durationDays' format for {STRATAGEM_TYPE}. Must be an integer. Params: {stratagem_params}{LogColors.ENDC}")
        return None

    # calculated_influence_cost = duration_days * INFLUENCE_COST_PER_DAY # Influence cost removed
    
    # TargetLand Airtable ID resolution is tricky here as this creator shouldn't access tables directly for lookups.
    # The main API endpoint or a pre-processing step should resolve LandId to Airtable ID if needed.
    # For now, we'll assume targetLandId from params is the custom LandId, and TargetLand in payload might be set later or handled by processor.
    # However, the current schema for STRATAGEMS.TargetLand expects a linked record ID.
    # This implies the creator *does* need table access if it's to populate TargetLand directly.
    # Let's assume for now that the API endpoint will handle resolving targetLandId to its Airtable ID if provided.
    # The creator will pass targetLandId_param in Notes.
    
    target_land_id_param = stratagem_params.get("targetLandId")
    # target_land_airtable_id = None # This would be resolved by the caller if needed for direct linking
    target_land_name_for_log = target_land_id_param # Use the param for logging if no direct lookup

    expires_at_utc = now_utc_dt + timedelta(days=duration_days)
    expires_at_iso = expires_at_utc.isoformat()

    stratagem_id_custom = f"{STRATAGEM_TYPE}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name")
    if not name:
        base_name = f"Canal Mugging ({variant}, {duration_days}d)"
        name = f"{base_name} near {target_land_name_for_log}" if target_land_name_for_log else f"{base_name} (Opportunistic)"
            
    description = stratagem_params.get("description") or \
                  f"An attempt to conduct canal muggings for {duration_days} days, with a '{variant}' approach. " + \
                  (f"Focusing on the area around {target_land_name_for_log}." if target_land_name_for_log else "Targeting opportune locations.")

    notes_details = {
        "creator_script_version": "1.0", # Version of this creator logic
        "durationDays": duration_days,
        "variant": variant,
        "targetLandId_param": target_land_id_param, 
        # "targetLandName_log": target_land_name_for_log, # This would require a lookup
        # "calculatedInfluenceCost": calculated_influence_cost, # Influence cost removed
        "custom_notes": stratagem_params.get("notes", "")
    }
    notes_json_str = json.dumps(notes_details)

    stratagem_payload = {
        "StratagemId": stratagem_id_custom,
        "Type": STRATAGEM_TYPE, # Use the constant
        "ExecutedBy": citizen_username,
        "Status": "active", # Initial status
        "Variant": variant,
        "Name": name,
        "Description": description,
        "Notes": notes_json_str,
        # "InfluenceCost": calculated_influence_cost, # Influence cost removed
        "ExpiresAt": expires_at_iso,
        "Category": "warfare", # As per schema
        # "TargetLand": [target_land_airtable_id] if target_land_airtable_id else None, # Caller handles this if needed
    }
    # If target_land_id_param is provided, the main API endpoint should resolve it to an Airtable ID
    # and add it to the payload before creating the record if the STRATAGEMS.TargetLand field is a link.
    # For now, the processor will use targetLandId_param from Notes.

    log.info(f"{LogColors.STRATAGEM_CREATOR}Prepared payload for '{STRATAGEM_TYPE}' stratagem {stratagem_id_custom} for {citizen_username}.")
    return [stratagem_payload]

import logging
import uuid
import json # Added for storing details in Notes
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

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
    stratagem_params: Dict[str, Any],
    resource_defs: Dict[str, Any], 
    building_type_defs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attempts to create a 'canal_mugging' stratagem.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{STRATAGEM_TYPE}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    citizen_record = get_citizen_record(tables, citizen_username)
    if not citizen_record:
        return {"success": False, "message": f"Citizen {citizen_username} not found."}

    variant = stratagem_params.get("variant")
    if not variant or variant not in VALID_VARIANTS:
        return {"success": False, "message": f"Invalid or missing 'variant'. Must be one of {VALID_VARIANTS}."}

    try:
        duration_days = int(stratagem_params.get("durationDays", DEFAULT_DURATION_DAYS))
        if not (MIN_DURATION_DAYS <= duration_days <= MAX_DURATION_DAYS):
            return {"success": False, "message": f"Invalid 'durationDays'. Must be between {MIN_DURATION_DAYS} and {MAX_DURATION_DAYS}."}
    except ValueError:
        return {"success": False, "message": "Invalid 'durationDays' format. Must be an integer."}

    calculated_influence_cost = duration_days * INFLUENCE_COST_PER_DAY
    current_influence = citizen_record['fields'].get('Influence', 0)

    if current_influence < calculated_influence_cost:
        return {"success": False, "message": f"Insufficient influence. Needs {calculated_influence_cost}, has {current_influence}."}

    target_land_id_param = stratagem_params.get("targetLandId")
    target_land_airtable_id: Optional[str] = None
    target_land_name_for_log: Optional[str] = None
    if target_land_id_param:
        land_record = get_land_record(tables, target_land_id_param)
        if not land_record:
            return {"success": False, "message": f"Target land with LandId '{target_land_id_param}' not found."}
        target_land_airtable_id = land_record['id']
        target_land_name_for_log = land_record['fields'].get('EnglishName') or land_record['fields'].get('HistoricalName') or target_land_id_param

    now_utc = datetime.now(timezone.utc)
    expires_at_utc = now_utc + timedelta(days=duration_days)
    expires_at_iso = expires_at_utc.isoformat()

    new_influence = current_influence - calculated_influence_cost
    tables['citizens'].update(citizen_record['id'], {'Influence': new_influence})
    log.info(f"{LogColors.STRATAGEM_CREATOR}Deducted {calculated_influence_cost} influence from {citizen_username}. New influence: {new_influence}{LogColors.ENDC}")

    stratagem_id_custom = f"{STRATAGEM_TYPE}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name")
    if not name:
        base_name = f"Canal Mugging ({variant}, {duration_days}d)"
        name = f"{base_name} near {target_land_name_for_log}" if target_land_name_for_log else f"{base_name} (Opportunistic)"
            
    description = stratagem_params.get("description") or \
                  f"An attempt to conduct canal muggings for {duration_days} days, with a '{variant}' approach. " + \
                  (f"Focusing on the area around {target_land_name_for_log}." if target_land_name_for_log else "Targeting opportune locations.")

    # Store detailed parameters in Notes as JSON
    notes_details = {
        "creator_script_version": "1.0",
        "durationDays": duration_days,
        "variant": variant,
        "targetLandId_param": target_land_id_param, # Store the original LandId from params
        "targetLandName_log": target_land_name_for_log,
        "calculatedInfluenceCost": calculated_influence_cost,
        "custom_notes": stratagem_params.get("notes", "")
    }
    notes_json_str = json.dumps(notes_details)

    stratagem_payload = {
        "StratagemId": stratagem_id_custom,
        "Type": STRATAGEM_TYPE,
        "ExecutedBy": citizen_username,
        "Status": "active",
        "Variant": variant, # Storing variant directly as it's a defined field
        "Name": name,
        "Description": description,
        "Notes": notes_json_str, # Store all details here
        "InfluenceCost": calculated_influence_cost,
        "ExpiresAt": expires_at_iso,
        "Category": "warfare",
        "TargetLand": [target_land_airtable_id] if target_land_airtable_id else None,
    }

    try:
        created_record = tables['stratagems'].create(stratagem_payload)
        log.info(f"{LogColors.STRATAGEM_CREATOR}Successfully created '{STRATAGEM_TYPE}' stratagem {stratagem_id_custom} for {citizen_username}. Airtable ID: {created_record['id']}{LogColors.ENDC}")
        
        create_notification(
            tables=tables,
            citizen_username=citizen_username,
            notification_type="stratagem_initiated",
            content=f"Your '{name}' stratagem ({STRATAGEM_TYPE}) has been initiated and is now active for {duration_days} days.",
            details={
                "stratagemId": stratagem_id_custom,
                "stratagemType": STRATAGEM_TYPE,
                "variant": variant,
                "durationDays": duration_days,
                "targetLand": target_land_name_for_log or "Opportunistic",
                "expiresAt": expires_at_iso
            }
        )
        
        return {
            "success": True,
            "message": f"'{STRATAGEM_TYPE}' stratagem '{name}' initiated successfully.",
            "stratagem_id_custom": stratagem_id_custom,
            "stratagem_id_airtable": created_record['id']
        }
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to create '{STRATAGEM_TYPE}' stratagem for {citizen_username} in Airtable: {e}{LogColors.ENDC}")
        tables['citizens'].update(citizen_record['id'], {'Influence': current_influence}) # Refund
        log.info(f"{LogColors.STRATAGEM_CREATOR}Refunded {calculated_influence_cost} influence to {citizen_username} due to creation failure.{LogColors.ENDC}")
        return {"success": False, "message": f"Airtable error: {str(e)}"}

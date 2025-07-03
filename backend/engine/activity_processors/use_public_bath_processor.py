import logging
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_building_record,
    update_citizen_ducats,
    VENICE_TIMEZONE
)
from backend.engine.utils.relationship_helpers import (
    update_trust_score_for_activity,
    TRUST_SCORE_MINOR_POSITIVE
)
from backend.engine.utils.process_helper import (
    create_process,
    PROCESS_TYPE_PUBLIC_BATH_REFLECTION
)

log = logging.getLogger(__name__)

PUBLIC_BATH_COSTS = {
    "Facchini": 25, "Popolani": 25, "Cittadini": 40,
    "Nobili": 100, "Forestieri": 40, "Artisti": 30 # Artisti cost
}
DEFAULT_PUBLIC_BATH_COST = 25 # Fallback cost
PUBLIC_BATH_INFLUENCE_GAIN = 5 # Constant for all classes

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any], # Not directly used here but part of signature
    resource_defs: Dict[str, Any],      # Not directly used here but part of signature
    api_base_url: Optional[str] = None
) -> bool:
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    notes_str = activity_fields.get('Notes') # Expecting details like bath_id here

    log.info(f"{LogColors.ACTIVITY}🛁 Processing 'use_public_bath': {activity_guid} for {citizen_username}.{LogColors.ENDC}")

    if not citizen_username or not notes_str:
        log.error(f"{LogColors.FAIL}Activity {activity_guid} missing Citizen or Notes. Aborting.{LogColors.ENDC}")
        return False

    try:
        activity_details = json.loads(notes_str)
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Could not parse Notes JSON for activity {activity_guid}: {notes_str}{LogColors.ENDC}")
        return False

    public_bath_id = activity_details.get("public_bath_id")
    public_bath_name = activity_details.get("public_bath_name", "an unknown public bath")

    if not public_bath_id:
        log.error(f"{LogColors.FAIL}Activity {activity_guid} missing 'public_bath_id' in Notes. Aborting.{LogColors.ENDC}")
        return False

    citizen_airtable_record = get_citizen_record(tables, citizen_username)
    if not citizen_airtable_record:
        log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found for activity {activity_guid}. Aborting.{LogColors.ENDC}")
        return False
    
    citizen_social_class = citizen_airtable_record['fields'].get('SocialClass', 'Popolani')
    cost = PUBLIC_BATH_COSTS.get(citizen_social_class, DEFAULT_PUBLIC_BATH_COST)
    
    current_ducats = float(citizen_airtable_record['fields'].get('Ducats', 0.0))
    current_influence = float(citizen_airtable_record['fields'].get('Influence', 0.0))

    if current_ducats < cost:
        log.warning(f"{LogColors.WARNING}Citizen {citizen_username} does not have enough Ducats ({current_ducats:.2f}) for public bath ({cost:.2f}). Activity failed.{LogColors.ENDC}")
        return False

    # --- Payment Logic ---
    # 1. Deduct cost from citizen
    try:
        tables['citizens'].update(citizen_airtable_record['id'], {'Ducats': current_ducats - cost})
        log.info(f"Ducats for {citizen_username} deducted: {current_ducats:.2f} -> {current_ducats - cost:.2f} (-{cost:.2f}).")
    except Exception as e_deduct:
        log.error(f"{LogColors.FAIL}Failed to deduct Ducats for {citizen_username}: {e_deduct}{LogColors.ENDC}")
        return False # Critical failure

    # 2. Pay the operator of the public bath
    public_bath_building_record = get_building_record(tables, public_bath_id)
    operator_paid = False
    if public_bath_building_record:
        bath_operator_username = public_bath_building_record['fields'].get('RunBy') or public_bath_building_record['fields'].get('Owner')
        if bath_operator_username:
            operator_record = get_citizen_record(tables, bath_operator_username)
            if operator_record:
                current_operator_ducats = float(operator_record['fields'].get('Ducats', 0.0))
                try:
                    tables['citizens'].update(operator_record['id'], {'Ducats': current_operator_ducats + cost})
                    log.info(f"Public bath fee ({cost:.2f} Ducats) paid to operator {bath_operator_username}.")
                    operator_paid = True
                    # Create transaction for the operator
                    tables['transactions'].create({
                        "Type": "public_bath_fee_revenue", "Seller": bath_operator_username, "Buyer": citizen_username,
                        "Price": cost, "AssetType": "public_bath_use", "Asset": public_bath_id,
                        "Notes": f"Revenue from public bath use at {public_bath_name} (Payer: {citizen_username})",
                        "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(), "ExecutedAt": datetime.now(VENICE_TIMEZONE).isoformat()
                    })
                    # Update trust with operator
                    if bath_operator_username != citizen_username:
                         update_trust_score_for_activity(tables, citizen_username, bath_operator_username, TRUST_SCORE_MINOR_POSITIVE, "public_bath_payment_received", True, f"used_bath_{public_bath_id.replace('_','-')}", activity_record)
                except Exception as e_operator_payment:
                    log.error(f"Failed to pay operator {bath_operator_username}: {e_operator_payment}. Cost was deducted from citizen.")
            else:
                log.error(f"Operator {bath_operator_username} of public bath {public_bath_name} ({public_bath_id}) not found. Cannot pay fee.")
        else:
            log.error(f"Public bath {public_bath_name} ({public_bath_id}) has no operator (RunBy/Owner). Cannot pay fee.")
    else:
        log.error(f"Public bath {public_bath_name} ({public_bath_id}) not found. Cannot pay fee to operator.")

    if not operator_paid:
        log.warning(f"Operator for {public_bath_name} was not paid. The {cost:.2f} Ducats are effectively lost from the citizen.")


    # --- Add influence ---
    new_influence = current_influence + PUBLIC_BATH_INFLUENCE_GAIN
    try:
        tables['citizens'].update(citizen_airtable_record['id'], {'Influence': new_influence})
        log.info(f"{LogColors.OKGREEN}Influence for {citizen_username} updated: {current_influence:.2f} -> {new_influence:.2f} (+{PUBLIC_BATH_INFLUENCE_GAIN:.2f}) after using {public_bath_name}.{LogColors.ENDC}")
    except Exception as e_influence:
        log.error(f"{LogColors.FAIL}Failed to update influence for {citizen_username}: {e_influence}{LogColors.ENDC}")

    log.info(f"{LogColors.OKGREEN}Activity 'use_public_bath' {activity_guid} for {citizen_username} at {public_bath_name} processed successfully. Creating process for reflection.{LogColors.ENDC}")

    # Create a process for public bath reflection
    process_details = {
        "activity_id": activity_record['id'],
        "activity_guid": activity_guid,
        "activity_details": activity_details,
        "public_bath_id": public_bath_id,
        "public_bath_name": public_bath_name
    }
    
    # Check if 'processes' table exists before creating process
    from backend.engine.utils.process_helper import is_processes_table_available
    
    if not is_processes_table_available(tables):
        log.error(f"{LogColors.FAIL}Cannot create public bath reflection process for {citizen_username} - 'processes' table not available or is not properly initialized.{LogColors.ENDC}")
        log.info(f"{LogColors.WARNING}Attempting to reinitialize tables to get a working processes table...{LogColors.ENDC}")
        
        # Try to reinitialize the tables
        try:
            from backend.engine.utils.activity_helpers import get_tables
            new_tables = get_tables()
            if is_processes_table_available(new_tables):
                log.info(f"{LogColors.OKGREEN}Successfully reinitialized tables and found working 'processes' table. Attempting to create process with new tables.{LogColors.ENDC}")
                # Include api_base_url in process_details
                if api_base_url:
                    process_details["api_base_url"] = api_base_url
                
                process_record = create_process(
                    tables=new_tables,
                    process_type=PROCESS_TYPE_PUBLIC_BATH_REFLECTION,
                    citizen_username=citizen_username,
                    priority=5,  # Medium priority
                    details=process_details
                )
                if process_record:
                    log.info(f"{LogColors.OKGREEN}Successfully created public bath reflection process for {citizen_username} after table reinitialization.{LogColors.ENDC}")
                else:
                    log.warning(f"{LogColors.WARNING}Failed to create public bath reflection process for {citizen_username} even after table reinitialization.{LogColors.ENDC}")
            else:
                log.error(f"{LogColors.FAIL}Failed to get working 'processes' table even after reinitialization. Process creation failed.{LogColors.ENDC}")
        except Exception as e_reinit:
            log.error(f"{LogColors.FAIL}Error reinitializing tables: {e_reinit}{LogColors.ENDC}")
    else:
        try:
            # Include api_base_url in process_details
            if api_base_url:
                process_details["api_base_url"] = api_base_url
            
            process_record = create_process(
                tables=tables,
                process_type=PROCESS_TYPE_PUBLIC_BATH_REFLECTION,
                citizen_username=citizen_username,
                priority=5,  # Medium priority
                details=process_details
            )
            if process_record:
                log.info(f"{LogColors.OKGREEN}Successfully created public bath reflection process for {citizen_username}.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Failed to create public bath reflection process for {citizen_username}.{LogColors.ENDC}")
        except Exception as e:
            log.error(f"{LogColors.FAIL}Error creating public bath reflection process for {citizen_username}: {e}{LogColors.ENDC}")

    return True

# Public bath costs and influence gain
PUBLIC_BATH_COSTS = {
    "Facchini": 25, "Popolani": 25, "Cittadini": 40,
    "Nobili": 100, "Forestieri": 40, "Artisti": 30 # Artisti cost
}
DEFAULT_PUBLIC_BATH_COST = 25 # Fallback cost
PUBLIC_BATH_INFLUENCE_GAIN = 5 # Constant for all classes

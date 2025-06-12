import logging
import json
import requests
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_building_record,
    update_citizen_ducats,
    VENICE_TIMEZONE,
    clean_thought_content 
)
from backend.engine.utils.relationship_helpers import (
    update_trust_score_for_activity,
    TRUST_SCORE_MINOR_POSITIVE
)
from backend.engine.utils.conversation_helper import persist_message # Added import

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

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

    log.info(f"{LogColors.OKGREEN}Activity 'use_public_bath' {activity_guid} for {citizen_username} at {public_bath_name} processed successfully. Launching KinOS reflection.{LogColors.ENDC}")

    # --- KinOS Reflection (asynchronous) ---
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not defined. Cannot trigger KinOS reflection for 'use_public_bath' {activity_guid}.{LogColors.ENDC}")
    else:
        try:
            data_package_json_str = None
            if api_base_url:
                data_package_url = f"{api_base_url}/api/get-data-package?citizenUsername={citizen_username}"
                try:
                    pkg_response = requests.get(data_package_url, timeout=15)
                    if pkg_response.ok:
                        pkg_data = pkg_response.json()
                        if pkg_data.get("success"):
                            data_package_json_str = json.dumps(pkg_data.get("data"))
                            log.info(f"  Successfully fetched data package for {citizen_username} for public bath reflection.")
                    else:
                        log.warning(f"  Failed to fetch data package for {citizen_username} (public bath): {pkg_response.status_code}")
                except Exception as e_pkg_fetch:
                    log.error(f"  Error fetching data package for {citizen_username} (public bath): {e_pkg_fetch}")
            
            kinos_build_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/message"
            
            kinos_prompt_bath = (
                f"You are {citizen_username}, a citizen of Renaissance Venice. You've just spent some time relaxing and socializing at a public bath. "
                f"Your personal data is provided in `addSystem` under `citizen_context`.\n\n"
                f"Reflect on your experience at the public bath. Consider:\n"
                f"- How do you feel after this experience (physically, mentally)?\n"
                f"- Did you meet anyone interesting or overhear any noteworthy conversations?\n"
                f"- How might this period of relaxation and social interaction influence your thoughts, decisions, or actions regarding your life, work, relations, or ambitions in Venice (refer to `addSystem.citizen_context`)?\n\n"
                f"Your reflection should be personal and introspective. Use your current situation, goals, and personality (detailed in `addSystem.citizen_context`) to contextualize your thoughts."
            )

            structured_add_system_payload_bath: Dict[str, Any] = { "citizen_context": None }
            if data_package_json_str:
                try:
                    structured_add_system_payload_bath["citizen_context"] = json.loads(data_package_json_str)
                except json.JSONDecodeError:
                    log.error("  Failed to parse data_package_json_str for citizen_context (public bath). Citizen context will be incomplete.")
                    structured_add_system_payload_bath["citizen_context"] = {"error_parsing_data_package": True, "status": "unavailable"}
            else:
                structured_add_system_payload_bath["citizen_context"] = {"status": "unavailable_no_data_package_fetched"}

            kinos_payload_dict_bath: Dict[str, Any] = {
                "message": kinos_prompt_bath,
                "model": "local", 
                "addSystem": json.dumps(structured_add_system_payload_bath)
            }

            log.info(f"  Launching asynchronous KinOS /build call for public bath reflection by {citizen_username} to {kinos_build_url}")
            
            kinos_thread_bath = threading.Thread(
                target=_call_kinos_build_for_bath_reflection_async,
                args=(kinos_build_url, kinos_payload_dict_bath, tables, activity_record['id'], activity_guid, activity_details, citizen_username)
            )
            kinos_thread_bath.start()
            log.info(f"  KinOS /build call for public bath reflection by {citizen_username} started in thread {kinos_thread_bath.ident}.")

        except Exception as e_kinos_setup:
            log.error(f"{LogColors.FAIL}Error setting up KinOS call for public bath reflection {activity_guid}: {e_kinos_setup}{LogColors.ENDC}")
            import traceback
            log.error(traceback.format_exc())

    return True

def _call_kinos_build_for_bath_reflection_async(
    kinos_build_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any],
    activity_id_airtable: str,
    activity_guid_log: str,
    original_activity_notes_dict: Dict[str, Any],
    citizen_username_log: str
):
    """
    Performs the KinOS /build call for public bath reflection and updates the activity notes.
    This function is intended to be executed in a separate thread.
    """
    log.info(f"  [Thread Public Bath: {threading.get_ident()}] Calling KinOS /build for public bath reflection by {citizen_username_log} at {kinos_build_url}")
    try:
        kinos_response = requests.post(kinos_build_url, json=kinos_payload, timeout=120)
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  [Thread Public Bath: {threading.get_ident()}] KinOS /build response (public bath) for {citizen_username_log}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
        
        raw_reflection = kinos_response_data.get('response', "No reflection on public bath from KinOS.")

        # Persist the raw reflection as a self-message (thought)
        persist_message(
            tables=tables,
            sender_username=citizen_username_log,
            receiver_username=citizen_username_log,
            content=raw_reflection,
            message_type="kinos_public_bath_reflection",
            channel_name=citizen_username_log
        )
        log.info(f"  [Thread Public Bath: {threading.get_ident()}] Réflexion sur le bain public persistée comme message à soi-même pour {citizen_username_log}.")

        # Update activity notes (optional, kept for now)
        cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)

        original_activity_notes_dict['kinos_public_bath_reflection'] = cleaned_reflection_for_notes
        original_activity_notes_dict['kinos_public_bath_reflection_status'] = kinos_response_data.get('status', 'unknown')
        
        new_notes_json = json.dumps(original_activity_notes_dict)

        try:
            tables['activities'].update(activity_id_airtable, {'Notes': new_notes_json})
            log.info(f"  [Thread Public Bath: {threading.get_ident()}] Activity notes updated with KinOS public bath reflection for {activity_guid_log}.")
        except Exception as e_airtable_update:
            log.error(f"  [Thread Public Bath: {threading.get_ident()}] Error updating Airtable notes for activity {activity_guid_log} (public bath reflection): {e_airtable_update}")
            
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread Public Bath: {threading.get_ident()}] Error during KinOS /build call (public bath) for {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = kinos_response.text[:200] if 'kinos_response' in locals() and hasattr(kinos_response, 'text') else 'N/A'
        log.error(f"  [Thread Public Bath: {threading.get_ident()}] JSON decode error for KinOS /build response (public bath) for {citizen_username_log}: {e_json_kinos}. Response: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread Public Bath: {threading.get_ident()}] Unexpected error in KinOS call thread for public bath reflection by {citizen_username_log}: {e_thread}")

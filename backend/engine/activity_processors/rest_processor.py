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
    clean_thought_content,
    VENICE_TIMEZONE # For logging or future use
)
from backend.engine.utils.conversation_helper import persist_message # Added import
# Note: No direct ducat transactions or influence gain for 'rest' itself.

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

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
    
    # 'Notes' might contain details about the rest location (e.g., home, inn)
    # but for the reflection, we primarily need the citizen's context.
    notes_str = activity_fields.get('Notes') 
    activity_details = {}
    if notes_str:
        try:
            activity_details = json.loads(notes_str)
        except json.JSONDecodeError:
            log.warning(f"Could not parse Notes JSON for rest activity {activity_guid}: {notes_str}")
            # Continue, as notes are not critical for basic rest processing + KinOS reflection

    log.info(f"{LogColors.ACTIVITY}😴 Processing 'rest' activity: {activity_guid} for {citizen_username}. Triggering daily reflection.{LogColors.ENDC}")

    citizen_airtable_record = get_citizen_record(tables, citizen_username)
    if not citizen_airtable_record:
        log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found for rest activity {activity_guid}. Aborting KinOS reflection.{LogColors.ENDC}")
        # Still return True as the 'rest' activity itself is considered processed by time passing.
        return True 

    # --- KinOS Reflection for Daily Summary (asynchronous) ---
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not defined. Cannot trigger KinOS reflection for 'rest' activity {activity_guid}.{LogColors.ENDC}")
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
                            log.info(f"  Successfully fetched data package for {citizen_username} for daily reflection.")
                    else:
                        log.warning(f"  Failed to fetch data package for {citizen_username} (daily reflection): {pkg_response.status_code}")
                except Exception as e_pkg_fetch:
                    log.error(f"  Error fetching data package for {citizen_username} (daily reflection): {e_pkg_fetch}")
            
            kinos_build_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/build"
            
            kinos_prompt_daily_reflection = (
                f"You are {citizen_username}, a citizen of Renaissance Venice. You have just finished a period of rest, marking the end of a day or the beginning of a new one. "
                f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
                f"Reflect on the events, interactions, and feelings of your past day. Consider:\n"
                f"- What were the most significant things that happened? (Refer to `addSystem.citizen_context.activities` and `addSystem.citizen_context.messages`)\n"
                f"- How do you feel about these events (e.g., satisfied, frustrated, hopeful, worried)?\n"
                f"- Did you learn anything new or gain any insights?\n"
                f"- How might the day's experiences influence your plans, goals, or relationships for tomorrow and beyond? (Refer to `addSystem.citizen_context.profile`, `addSystem.citizen_context.relationships`)\n\n"
                f"Your reflection should be personal and introspective, like a private journal entry. Use your current situation, goals, and personality (detailed in `addSystem.citizen_context`) to contextualize your thoughts."
            )

            structured_add_system_payload: Dict[str, Any] = { "citizen_context": None }
            if data_package_json_str:
                try:
                    structured_add_system_payload["citizen_context"] = json.loads(data_package_json_str)
                except json.JSONDecodeError:
                    log.error("  Failed to parse data_package_json_str for citizen_context (daily reflection). Citizen context will be incomplete.")
                    structured_add_system_payload["citizen_context"] = {"error_parsing_data_package": True, "status": "unavailable"}
            else:
                structured_add_system_payload["citizen_context"] = {"status": "unavailable_no_data_package_fetched"}

            kinos_payload_dict: Dict[str, Any] = {
                "message": kinos_prompt_daily_reflection,
                "model": "local", 
                "addSystem": json.dumps(structured_add_system_payload)
            }

            log.info(f"  Launching asynchronous KinOS /build call for daily reflection by {citizen_username} to {kinos_build_url}")
            
            kinos_thread = threading.Thread(
                target=_call_kinos_build_for_rest_reflection_async,
                args=(kinos_build_url, kinos_payload_dict, tables, activity_record['id'], activity_guid, activity_details, citizen_username)
            )
            kinos_thread.start()
            log.info(f"  KinOS /build call for daily reflection by {citizen_username} started in thread {kinos_thread.ident}.")

        except Exception as e_kinos_setup:
            log.error(f"{LogColors.FAIL}Error setting up KinOS call for daily reflection (activity {activity_guid}): {e_kinos_setup}{LogColors.ENDC}")
            import traceback
            log.error(traceback.format_exc())

    # The 'rest' activity itself is considered successful by its completion.
    # KinOS reflection is an add-on.
    return True

def _call_kinos_build_for_rest_reflection_async(
    kinos_build_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any],
    activity_id_airtable: str,
    activity_guid_log: str,
    original_activity_notes_dict: Dict[str, Any], # This is the parsed JSON from activity notes
    citizen_username_log: str
):
    """
    Performs the KinOS /build call for daily reflection and updates the activity notes.
    This function is intended to be executed in a separate thread.
    """
    log.info(f"  [Thread Daily Reflection: {threading.get_ident()}] Calling KinOS /build for daily reflection by {citizen_username_log} at {kinos_build_url}")
    try:
        kinos_response = requests.post(kinos_build_url, json=kinos_payload, timeout=180) # Increased timeout
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  [Thread Daily Reflection: {threading.get_ident()}] KinOS /build response (daily reflection) for {citizen_username_log}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
        
        raw_reflection = kinos_response_data.get('response', "No daily reflection from KinOS.")

        # Persist the raw reflection as a self-message (thought)
        persist_message(
            tables=tables,
            sender_username=citizen_username_log,
            receiver_username=citizen_username_log,
            content=raw_reflection,
            message_type="kinos_daily_reflection",
            channel_name=citizen_username_log
        )
        log.info(f"  [Thread Daily Reflection: {threading.get_ident()}] Réflexion quotidienne persistée comme message à soi-même pour {citizen_username_log}.")

        # Update activity notes (optional, kept for now)
        cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)

        if not isinstance(original_activity_notes_dict, dict):
            original_activity_notes_dict = {}
            
        original_activity_notes_dict['kinos_daily_reflection'] = cleaned_reflection_for_notes
        original_activity_notes_dict['kinos_daily_reflection_status'] = kinos_response_data.get('status', 'unknown')
        
        new_notes_json = json.dumps(original_activity_notes_dict)

        try:
            tables['activities'].update(activity_id_airtable, {'Notes': new_notes_json})
            log.info(f"  [Thread Daily Reflection: {threading.get_ident()}] Activity notes updated with KinOS daily reflection for {activity_guid_log}.")
        except Exception as e_airtable_update:
            log.error(f"  [Thread Daily Reflection: {threading.get_ident()}] Error updating Airtable notes for activity {activity_guid_log} (daily reflection): {e_airtable_update}")
            
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread Daily Reflection: {threading.get_ident()}] Error during KinOS /build call (daily reflection) for {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = "N/A"
        if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
            kinos_response_text_preview = kinos_response.text[:200]
        log.error(f"  [Thread Daily Reflection: {threading.get_ident()}] JSON decode error for KinOS /build response (daily reflection) for {citizen_username_log}: {e_json_kinos}. Response: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread Daily Reflection: {threading.get_ident()}] Unexpected error in KinOS call thread for daily reflection by {citizen_username_log}: {e_thread}")
        import traceback
        log.error(traceback.format_exc())

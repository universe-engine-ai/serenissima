import logging
import json
import os
import requests
import threading
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import LogColors, VENICE_TIMEZONE

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def _call_kinos_for_observation_async(
    kinos_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any],
    activity_id_airtable: str,
    activity_guid_log: str,
    original_activity_notes_dict: Dict[str, Any],
    citizen_username_log: str
):
    """
    Makes the KinOS API call for scientific observation reflection and updates activity notes.
    This function runs in a separate thread.
    """
    log.info(f"  [Thread: {threading.get_ident()}] Calling KinOS for observation reflection by {citizen_username_log}")
    try:
        kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=120)
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  [Thread: {threading.get_ident()}] KinOS observation response for {citizen_username_log}: Status: {kinos_response_data.get('status')}")
        
        # Update the original notes dictionary with the KinOS observations
        original_activity_notes_dict['kinos_observations'] = kinos_response_data.get('response', "No observations from KinOS.")
        original_activity_notes_dict['kinos_observation_status'] = kinos_response_data.get('status', 'unknown')
        
        new_notes_json = json.dumps(original_activity_notes_dict)

        try:
            tables['activities'].update(activity_id_airtable, {'Notes': new_notes_json})
            log.info(f"  [Thread: {threading.get_ident()}] Updated activity notes with KinOS observations for {activity_guid_log}.")
        except Exception as e_airtable_update:
            log.error(f"  [Thread: {threading.get_ident()}] Error updating Airtable notes for activity {activity_guid_log} (observations): {e_airtable_update}")
            
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread: {threading.get_ident()}] Error calling KinOS for observation by {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = kinos_response.text[:200] if 'kinos_response' in locals() and hasattr(kinos_response, 'text') else 'N/A'
        log.error(f"  [Thread: {threading.get_ident()}] Error decoding KinOS observation JSON response for {citizen_username_log}: {e_json_kinos}. Response text: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread: {threading.get_ident()}] Unexpected error in KinOS call thread for observation by {citizen_username_log}: {e_thread}")

def process(
    tables: Dict[str, Any], 
    activity_record: Dict[str, Any], 
    building_type_defs: Dict[str, Any], 
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes an 'observe_phenomena' activity for Scientisti.
    This involves calling KinOS to generate scientific observations.
    """
    activity_id_airtable = activity_record['id']
    activity_guid = activity_record['fields'].get('ActivityId', activity_id_airtable)
    citizen_username = activity_record['fields'].get('Citizen')
    
    # Use passed api_base_url or fallback to environment variable
    current_api_base_url = api_base_url or os.getenv("API_BASE_URL", "http://localhost:3000")

    notes_str = activity_record['fields'].get('Notes', '{}')
    try:
        notes_dict = json.loads(notes_str)
    except json.JSONDecodeError:
        log.warning(f"{LogColors.WARNING}[Observe Phenomena] Activity {activity_guid} has invalid JSON in Notes: {notes_str}. Cannot process.{LogColors.ENDC}")
        return True

    site_name = notes_dict.get('site_name', 'unknown location')
    phenomena = notes_dict.get('phenomena', 'natural phenomena')
    
    log.info(f"{LogColors.PROCESS}Processing 'observe_phenomena' activity {activity_guid} for {citizen_username} observing {phenomena} at {site_name}.{LogColors.ENDC}")

    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not set. Cannot trigger KinOS reflection for 'observe_phenomena' activity {activity_guid}.{LogColors.ENDC}")
        return True

    try:
        # 1. Fetch citizen's ledger for context
        ledger_url = f"{current_api_base_url}/api/get-ledger?citizenUsername={citizen_username}"
        ledger_json_str = None
        try:
            ledger_response = requests.get(ledger_url, timeout=15)
            if ledger_response.ok:
                ledger_data = ledger_response.json()
                if ledger_data.get("success"):
                    ledger_json_str = json.dumps(ledger_data.get("data"))
                    log.info(f"  Successfully fetched ledger for {citizen_username} for observation reflection.")
        except Exception as e:
            log.error(f"  Error fetching ledger for {citizen_username}: {e}")

        # 2. Construct KinOS request for scientific observation
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Create observation-specific prompt
        kinos_prompt = (
            f"You are {citizen_username}, a Scientisti of Venice conducting field observations. "
            f"You have spent 2 hours at {site_name} observing {phenomena}.\n\n"
            f"As a natural philosopher, record your detailed observations:\n"
            f"1. What specific phenomena did you observe? Describe in precise detail.\n"
            f"2. What patterns or anomalies did you notice?\n"
            f"3. How do these observations relate to existing theories?\n"
            f"4. What hypotheses arise from today's observations?\n"
            f"5. What further experiments or observations would help test these hypotheses?\n\n"
            f"Your observations should be empirical, detailed, and methodical. "
            f"Consider environmental conditions, time of day, and any variables that might affect your observations."
        )
        
        # Initialize the structured addSystem payload
        structured_add_system_payload: Dict[str, Any] = {
            "ledger": None,
            "observation_context": {
                "site_name": site_name,
                "phenomena": phenomena,
                "observation_duration": "2 hours",
                "time_of_day": "work hours"
            }
        }
        
        if ledger_json_str:
            try:
                structured_add_system_payload["ledger"] = json.loads(ledger_json_str)
            except json.JSONDecodeError:
                structured_add_system_payload["ledger"] = {"status": "unavailable"}
        else:
            structured_add_system_payload["ledger"] = {"status": "unavailable"}

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt,
            "model": "local",
            "addSystem": json.dumps(structured_add_system_payload)
        }
        
        # 3. Start KinOS call in a new thread
        log.info(f"  Initiating asynchronous KinOS call for observation reflection by {citizen_username}")
        
        kinos_thread = threading.Thread(
            target=_call_kinos_for_observation_async,
            args=(kinos_url, kinos_payload_dict, tables, activity_id_airtable, activity_guid, notes_dict, citizen_username)
        )
        kinos_thread.start()
        
        log.info(f"  KinOS call for observation reflection by {citizen_username} started in background thread {kinos_thread.ident}.")

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error during 'observe_phenomena' processing setup for {activity_guid}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False

    log.info(f"{LogColors.SUCCESS}Successfully initiated asynchronous KinOS reflection for 'observe_phenomena' activity {activity_guid}.{LogColors.ENDC}")
    return True
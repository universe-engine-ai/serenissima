import logging
import json
import requests
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    clean_thought_content,
    VENICE_TIMEZONE
)
from backend.engine.utils.conversation_helper import persist_message
from backend.engine.utils.process_helper import (
    update_process_status,
    PROCESS_STATUS_COMPLETED,
    PROCESS_STATUS_FAILED,
    PROCESS_STATUS_IN_PROGRESS
)

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def process_daily_reflection(
    tables: Dict[str, Any],
    process_record: Dict[str, Any]
) -> bool:
    """
    Processes a daily reflection for a citizen using KinOS.
    
    Args:
        tables: Dictionary of Airtable tables
        process_record: The process record from the PROCESSES table
        
    Returns:
        True if successful, False otherwise
    """
    process_id = process_record['id']
    process_fields = process_record['fields']
    citizen_username = process_fields.get('Citizen')
    api_base_url = process_fields.get('ApiBaseUrl')
    details_str = process_fields.get('Details')
    
    details = {}
    if details_str:
        try:
            details = json.loads(details_str)
        except json.JSONDecodeError:
            log.warning(f"Could not parse Details JSON for process {process_id}: {details_str}")
    
    log.info(f"{LogColors.ACTIVITY}Processing daily reflection for {citizen_username} (Process ID: {process_id}).{LogColors.ENDC}")
    
    # Update process status to in progress
    update_process_status(tables, process_id, PROCESS_STATUS_IN_PROGRESS)
    
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not defined. Cannot trigger KinOS reflection.{LogColors.ENDC}")
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": "KINOS_API_KEY not defined"})
        return False
    
    try:
        data_package_markdown_str = None
        if api_base_url:
            data_package_url = f"{api_base_url}/api/get-data-package?citizenUsername={citizen_username}" # Defaults to Markdown
            try:
                pkg_response = requests.get(data_package_url, timeout=15)
                if pkg_response.ok:
                    data_package_markdown_str = pkg_response.text # Get Markdown content
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for daily reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (daily reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (daily reflection): {e_pkg_fetch}")
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages" # Changed to /messages
        
        kinos_prompt_daily_reflection = (
            f"You are {citizen_username}, a citizen of Renaissance Venice. You have just finished a period of rest, marking the end of a day or the beginning of a new one. "
            f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
            f"Based on the data provided, reflect on the events, interactions, and feelings of your past day. Consider:\n"
            f"- What were the most significant things that happened? (Refer to `addSystem.citizen_context.activities` and `addSystem.citizen_context.messages`)\n"
            f"- How do you feel about these events (e.g., satisfied, frustrated, hopeful, worried)?\n"
            f"- Did you learn anything new or gain any insights?\n"
            f"- How might the day's experiences influence your plans, goals, or relationships for tomorrow and beyond? (Refer to `addSystem.citizen_context.profile`, `addSystem.citizen_context.relationships`)\n\n"
            f"Your reflection should be personal and introspective, like a private journal entry. Use your current situation, goals, and personality (detailed in `addSystem.citizen_context`) to contextualize your thoughts."
        )

        structured_add_system_payload: Dict[str, Any] = { "citizen_context": None }
        if data_package_markdown_str:
            structured_add_system_payload["citizen_context"] = data_package_markdown_str # Assign Markdown string directly
        else:
            structured_add_system_payload["citizen_context"] = "Citizen context data package was not available."

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt_daily_reflection,
            "model": "local", 
            "addSystem": json.dumps(structured_add_system_payload) # structured_add_system_payload is a dict, citizen_context is a string
        }

        log.info(f"  Making KinOS /messages call for daily reflection by {citizen_username} to {kinos_messages_url}")
        
        try:
            kinos_response = requests.post(kinos_messages_url, json=kinos_payload_dict, timeout=180) # Increased timeout
            kinos_response.raise_for_status()
            
            kinos_response_data = kinos_response.json()
            log.info(f"  KinOS /messages response (daily reflection) for {citizen_username}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
            
            raw_reflection = kinos_response_data.get('response', f"No daily reflection from KinOS.")

            # Persist the raw reflection as a self-message (thought)
            persist_message(
                tables=tables,
                sender_username=citizen_username,
                receiver_username=citizen_username,
                content=raw_reflection,
                message_type="kinos_daily_reflection",
                channel_name=citizen_username
            )
            log.info(f"  Reflection persisted as self-message for {citizen_username}.")
            
            # Update activity notes if activity_id is in details
            if 'activity_id' in details:
                activity_id = details['activity_id']
                activity_details = details.get('activity_details', {})
                
                cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)
                
                if not isinstance(activity_details, dict):
                    activity_details = {}
                    
                activity_details['kinos_daily_reflection'] = cleaned_reflection_for_notes
                activity_details['kinos_daily_reflection_status'] = kinos_response_data.get('status', 'unknown')
                
                new_notes_json = json.dumps(activity_details)

                try:
                    tables['activities'].update(activity_id, {'Notes': new_notes_json})
                    log.info(f"  Activity notes updated with KinOS daily reflection for {details.get('activity_guid', 'unknown')}.")
                except Exception as e_airtable_update:
                    log.error(f"  Error updating Airtable notes for activity {details.get('activity_guid', 'unknown')} (daily reflection): {e_airtable_update}")
            
            # Update process status to completed
            update_process_status(
                tables, 
                process_id, 
                PROCESS_STATUS_COMPLETED, 
                {"reflection": raw_reflection, "status": kinos_response_data.get('status', 'unknown')}
            )
            
            return True
                
        except requests.exceptions.RequestException as e_kinos:
            log.error(f"  Error during KinOS /messages call (daily reflection) for {citizen_username}: {e_kinos}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos)})
            return False
        except json.JSONDecodeError as e_json_kinos:
            kinos_response_text_preview = "N/A"
            if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
                kinos_response_text_preview = kinos_response.text[:200]
            log.error(f"  JSON decode error for KinOS /messages response (daily reflection) for {citizen_username}: {e_json_kinos}. Response: {kinos_response_text_preview}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": f"JSON decode error: {str(e_json_kinos)}"})
            return False

    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error processing daily reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos_setup)})
        return False

def generate_theater_reflection(
    tables: Dict[str, Any],
    citizen_username: str,
    api_base_url: Optional[str] = None
) -> bool:
    """
    Generates a reflection after attending a theater performance.
    
    Args:
        tables: Dictionary of Airtable tables
        citizen_username: Username of the citizen
        api_base_url: Optional base URL for API calls
        
    Returns:
        True if successful, False otherwise
    """
    log.info(f"{LogColors.ACTIVITY}Generating theater reflection for {citizen_username}.{LogColors.ENDC}")
    
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not defined. Cannot trigger KinOS reflection.{LogColors.ENDC}")
        return False
    
    try:
        data_package_markdown_str = None
        if api_base_url:
            data_package_url = f"{api_base_url}/api/get-data-package?citizenUsername={citizen_username}" # Defaults to Markdown
            try:
                pkg_response = requests.get(data_package_url, timeout=15)
                if pkg_response.ok:
                    data_package_markdown_str = pkg_response.text # Get Markdown content
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for theater reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (theater reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (theater reflection): {e_pkg_fetch}")
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt_theater_reflection = (
            f"You are {citizen_username}, a citizen of Renaissance Venice. You have just attended a theater performance. "
            f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
            f"Based on the data provided, reflect on the theater experience. Consider:\n"
            f"- What was the performance about? (If not specified in your data, imagine a typical Venetian performance of the era)\n"
            f"- How did you feel about the performance? What aspects did you appreciate or critique?\n"
            f"- Did you attend with anyone? Did you meet anyone interesting?\n"
            f"- How does this cultural experience relate to your position in Venetian society?\n"
            f"- What thoughts or inspirations did the performance provoke?\n\n"
            f"Your reflection should be personal and introspective, like a private journal entry about your theater experience."
        )

        structured_add_system_payload: Dict[str, Any] = { "citizen_context": None }
        if data_package_markdown_str:
            structured_add_system_payload["citizen_context"] = data_package_markdown_str # Assign Markdown string directly
        else:
            structured_add_system_payload["citizen_context"] = "Citizen context data package was not available."

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt_theater_reflection,
            "model": "local", 
            "addSystem": json.dumps(structured_add_system_payload)
        }

        log.info(f"  Launching asynchronous KinOS /messages call for theater reflection by {citizen_username} to {kinos_messages_url}")
        
        kinos_thread = threading.Thread(
            target=_call_kinos_messages_for_reflection_async,
            args=(kinos_messages_url, kinos_payload_dict, tables, citizen_username, "kinos_theater_reflection")
        )
        kinos_thread.start()
        log.info(f"  KinOS /messages call for theater reflection by {citizen_username} started in thread {kinos_thread.ident}.")
        return True

    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error setting up KinOS call for theater reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False

def generate_public_bath_reflection(
    tables: Dict[str, Any],
    citizen_username: str,
    api_base_url: Optional[str] = None
) -> bool:
    """
    Generates a reflection after using a public bath.
    
    Args:
        tables: Dictionary of Airtable tables
        citizen_username: Username of the citizen
        api_base_url: Optional base URL for API calls
        
    Returns:
        True if successful, False otherwise
    """
    log.info(f"{LogColors.ACTIVITY}Generating public bath reflection for {citizen_username}.{LogColors.ENDC}")
    
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not defined. Cannot trigger KinOS reflection.{LogColors.ENDC}")
        return False
    
    try:
        data_package_markdown_str = None
        if api_base_url:
            data_package_url = f"{api_base_url}/api/get-data-package?citizenUsername={citizen_username}" # Defaults to Markdown
            try:
                pkg_response = requests.get(data_package_url, timeout=15)
                if pkg_response.ok:
                    data_package_markdown_str = pkg_response.text # Get Markdown content
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for public bath reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (public bath reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (public bath reflection): {e_pkg_fetch}")
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt_bath_reflection = (
            f"You are {citizen_username}, a citizen of Renaissance Venice. You have just visited a public bath. "
            f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
            f"Based on the data provided, reflect on your experience at the public bath. Consider:\n"
            f"- How do you feel after this experience of relaxation and cleansing?\n"
            f"- Did you encounter anyone interesting or have any notable conversations?\n"
            f"- What thoughts or plans came to mind during this time of relaxation?\n"
            f"- How does this experience relate to your health, status, or social connections in Venice?\n"
            f"- Did you overhear any interesting gossip or news?\n\n"
            f"Your reflection should be personal and introspective, like a private journal entry about your visit to the public bath."
        )

        structured_add_system_payload: Dict[str, Any] = { "citizen_context": None }
        if data_package_markdown_str:
            structured_add_system_payload["citizen_context"] = data_package_markdown_str # Assign Markdown string directly
        else:
            structured_add_system_payload["citizen_context"] = "Citizen context data package was not available."

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt_bath_reflection,
            "model": "local", 
            "addSystem": json.dumps(structured_add_system_payload)
        }

        log.info(f"  Launching asynchronous KinOS /messages call for public bath reflection by {citizen_username} to {kinos_messages_url}")
        
        kinos_thread = threading.Thread(
            target=_call_kinos_messages_for_reflection_async,
            args=(kinos_messages_url, kinos_payload_dict, tables, citizen_username, "kinos_public_bath_reflection")
        )
        kinos_thread.start()
        log.info(f"  KinOS /messages call for public bath reflection by {citizen_username} started in thread {kinos_thread.ident}.")
        return True

    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error setting up KinOS call for public bath reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False

def _call_kinos_messages_for_reflection_async(
    kinos_messages_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any],
    citizen_username_log: str,
    message_type: str
):
    """
    Performs the KinOS /messages call for reflection and persists the result.
    This function is intended to be executed in a separate thread.
    
    Args:
        kinos_messages_url: URL for KinOS messages API
        kinos_payload: Payload for the KinOS API call
        tables: Dictionary of Airtable tables
        citizen_username_log: Username of the citizen (for logging)
        message_type: Type of message to persist (e.g., "kinos_daily_reflection")
    """
    log.info(f"  [Thread Reflection: {threading.get_ident()}] Calling KinOS /messages for {message_type} by {citizen_username_log} at {kinos_messages_url}")
    try:
        kinos_response = requests.post(kinos_messages_url, json=kinos_payload, timeout=180) # Increased timeout
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  [Thread Reflection: {threading.get_ident()}] KinOS /messages response ({message_type}) for {citizen_username_log}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
        
        raw_reflection = kinos_response_data.get('response', f"No {message_type} from KinOS.")

        # Persist the raw reflection as a self-message (thought)
        persist_message(
            tables=tables,
            sender_username=citizen_username_log,
            receiver_username=citizen_username_log,
            content=raw_reflection,
            message_type=message_type,
            channel_name=citizen_username_log
        )
        log.info(f"  [Thread Reflection: {threading.get_ident()}] Reflection persisted as self-message for {citizen_username_log}.")
            
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread Reflection: {threading.get_ident()}] Error during KinOS /messages call ({message_type}) for {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = "N/A"
        if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
            kinos_response_text_preview = kinos_response.text[:200]
        log.error(f"  [Thread Reflection: {threading.get_ident()}] JSON decode error for KinOS /messages response ({message_type}) for {citizen_username_log}: {e_json_kinos}. Response: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread Reflection: {threading.get_ident()}] Unexpected error in KinOS call thread for {message_type} by {citizen_username_log}: {e_thread}")
        import traceback
        log.error(traceback.format_exc())

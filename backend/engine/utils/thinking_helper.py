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
    # Extract API base URL from Details field
    details_str = process_fields.get('Details')
    api_base_url = None
    if details_str:
        try:
            details = json.loads(details_str)
            api_base_url = details.get('api_base_url')
        except json.JSONDecodeError:
            log.warning(f"Could not parse Details JSON for process {process_id}: {details_str}")
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

            # Persist the raw reflection as a self-message (thought) with readAt set to now
            now_iso = datetime.now(pytz.UTC).isoformat()
            persist_message(
                tables=tables,
                sender_username=citizen_username,
                receiver_username=citizen_username,
                content=raw_reflection,
                message_type="kinos_daily_reflection",
                channel_name=citizen_username,
                kinos_message_id=None,
                target_citizen_username=None,
                read_at=now_iso  # Mark as read immediately
            )
            log.info(f"  Reflection persisted as self-message for {citizen_username} (marked as read).")
            
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

def process_theater_reflection(
    tables: Dict[str, Any],
    process_record: Dict[str, Any]
) -> bool:
    """
    Processes a theater reflection for a citizen using KinOS.
    
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
    
    log.info(f"{LogColors.ACTIVITY}Processing theater reflection for {citizen_username} (Process ID: {process_id}).{LogColors.ENDC}")
    
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
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for theater reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (theater reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (theater reflection): {e_pkg_fetch}")
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Extract play details from the process details if available
        play_name = details.get('play_name', 'a Venetian play')
        play_content = details.get('play_content', '')
        artist_username = details.get('artist_username', '')
        theater_name = details.get('theater_name', 'a theater')
        
        # Build a more detailed prompt if we have play information
        play_context = ""
        if play_content:
            play_context = f"You just watched a play titled '{play_name}'"
            if artist_username:
                play_context += f" by {artist_username}"
            play_context += f". The play's content was: {play_content}\n\n"
        
        kinos_prompt_theater_reflection = (
            f"You are {citizen_username}, a citizen of Renaissance Venice. You have just attended a theater performance at {theater_name}. "
            f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
            f"{play_context}"
            f"Based on the data provided, reflect on the theater experience. Consider:\n"
            f"- What was the performance about? (Use the provided play details if available, or imagine a typical Venetian performance of the era)\n"
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

        log.info(f"  Making KinOS /messages call for theater reflection by {citizen_username} to {kinos_messages_url}")
        
        try:
            kinos_response = requests.post(kinos_messages_url, json=kinos_payload_dict, timeout=180) # Increased timeout
            kinos_response.raise_for_status()
            
            kinos_response_data = kinos_response.json()
            log.info(f"  KinOS /messages response (theater reflection) for {citizen_username}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
            
            raw_reflection = kinos_response_data.get('response', f"No theater reflection from KinOS.")

            # Persist the raw reflection as a self-message (thought) with readAt set to now
            now_iso = datetime.now(pytz.UTC).isoformat()
            persist_message(
                tables=tables,
                sender_username=citizen_username,
                receiver_username=citizen_username,
                content=raw_reflection,
                message_type="kinos_theater_reflection",
                channel_name=citizen_username,
                kinos_message_id=None,
                target_citizen_username=None,
                read_at=now_iso  # Mark as read immediately
            )
            log.info(f"  Theater reflection persisted as self-message for {citizen_username} (marked as read).")
            
            # Update activity notes if activity_id is in details
            if 'activity_id' in details:
                activity_id = details['activity_id']
                activity_details = details.get('activity_details', {})
                
                cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)
                
                if not isinstance(activity_details, dict):
                    activity_details = {}
                    
                activity_details['kinos_theater_reflection'] = cleaned_reflection_for_notes
                activity_details['kinos_theater_reflection_status'] = kinos_response_data.get('status', 'unknown')
                
                new_notes_json = json.dumps(activity_details)

                try:
                    tables['activities'].update(activity_id, {'Notes': new_notes_json})
                    log.info(f"  Activity notes updated with KinOS theater reflection for {details.get('activity_guid', 'unknown')}.")
                except Exception as e_airtable_update:
                    log.error(f"  Error updating Airtable notes for activity {details.get('activity_guid', 'unknown')} (theater reflection): {e_airtable_update}")
            
            # Update process status to completed
            update_process_status(
                tables, 
                process_id, 
                PROCESS_STATUS_COMPLETED, 
                {"reflection": raw_reflection, "status": kinos_response_data.get('status', 'unknown')}
            )
            
            return True
                
        except requests.exceptions.RequestException as e_kinos:
            log.error(f"  Error during KinOS /messages call (theater reflection) for {citizen_username}: {e_kinos}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos)})
            return False
        except json.JSONDecodeError as e_json_kinos:
            kinos_response_text_preview = "N/A"
            if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
                kinos_response_text_preview = kinos_response.text[:200]
            log.error(f"  JSON decode error for KinOS /messages response (theater reflection) for {citizen_username}: {e_json_kinos}. Response: {kinos_response_text_preview}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": f"JSON decode error: {str(e_json_kinos)}"})
            return False

    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error processing theater reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos_setup)})
        return False

def process_public_bath_reflection(
    tables: Dict[str, Any],
    process_record: Dict[str, Any]
) -> bool:
    """
    Processes a public bath reflection for a citizen using KinOS.
    
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
    
    log.info(f"{LogColors.ACTIVITY}Processing public bath reflection for {citizen_username} (Process ID: {process_id}).{LogColors.ENDC}")
    
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
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for public bath reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (public bath reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (public bath reflection): {e_pkg_fetch}")
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Extract bath details from the process details if available
        public_bath_name = details.get('public_bath_name', 'a public bath')
        
        kinos_prompt_bath_reflection = (
            f"You are {citizen_username}, a citizen of Renaissance Venice. You have just visited {public_bath_name}. "
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

        log.info(f"  Making KinOS /messages call for public bath reflection by {citizen_username} to {kinos_messages_url}")
        
        try:
            kinos_response = requests.post(kinos_messages_url, json=kinos_payload_dict, timeout=180) # Increased timeout
            kinos_response.raise_for_status()
            
            kinos_response_data = kinos_response.json()
            log.info(f"  KinOS /messages response (public bath reflection) for {citizen_username}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
            
            raw_reflection = kinos_response_data.get('response', f"No public bath reflection from KinOS.")

            # Persist the raw reflection as a self-message (thought) with readAt set to now
            now_iso = datetime.now(pytz.UTC).isoformat()
            persist_message(
                tables=tables,
                sender_username=citizen_username,
                receiver_username=citizen_username,
                content=raw_reflection,
                message_type="kinos_public_bath_reflection",
                channel_name=citizen_username,
                kinos_message_id=None,
                target_citizen_username=None,
                read_at=now_iso  # Mark as read immediately
            )
            log.info(f"  Public bath reflection persisted as self-message for {citizen_username} (marked as read).")
            
            # Update activity notes if activity_id is in details
            if 'activity_id' in details:
                activity_id = details['activity_id']
                activity_details = details.get('activity_details', {})
                
                cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)
                
                if not isinstance(activity_details, dict):
                    activity_details = {}
                    
                activity_details['kinos_public_bath_reflection'] = cleaned_reflection_for_notes
                activity_details['kinos_public_bath_reflection_status'] = kinos_response_data.get('status', 'unknown')
                
                new_notes_json = json.dumps(activity_details)

                try:
                    tables['activities'].update(activity_id, {'Notes': new_notes_json})
                    log.info(f"  Activity notes updated with KinOS public bath reflection for {details.get('activity_guid', 'unknown')}.")
                except Exception as e_airtable_update:
                    log.error(f"  Error updating Airtable notes for activity {details.get('activity_guid', 'unknown')} (public bath reflection): {e_airtable_update}")
            
            # Update process status to completed
            update_process_status(
                tables, 
                process_id, 
                PROCESS_STATUS_COMPLETED, 
                {"reflection": raw_reflection, "status": kinos_response_data.get('status', 'unknown')}
            )
            
            return True
                
        except requests.exceptions.RequestException as e_kinos:
            log.error(f"  Error during KinOS /messages call (public bath reflection) for {citizen_username}: {e_kinos}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos)})
            return False
        except json.JSONDecodeError as e_json_kinos:
            kinos_response_text_preview = "N/A"
            if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
                kinos_response_text_preview = kinos_response.text[:200]
            log.error(f"  JSON decode error for KinOS /messages response (public bath reflection) for {citizen_username}: {e_json_kinos}. Response: {kinos_response_text_preview}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": f"JSON decode error: {str(e_json_kinos)}"})
            return False

    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error processing public bath reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos_setup)})
        return False

def process_practical_reflection(
    tables: Dict[str, Any],
    process_record: Dict[str, Any]
) -> bool:
    """
    Processes a practical reflection for a citizen using KinOS.
    This reflection focuses on a randomly selected item from the citizen's data package.
    
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
    
    log.info(f"{LogColors.ACTIVITY}Processing practical reflection for {citizen_username} (Process ID: {process_id}).{LogColors.ENDC}")
    
    # Update process status to in progress
    update_process_status(tables, process_id, PROCESS_STATUS_IN_PROGRESS)
    
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not defined. Cannot trigger KinOS reflection.{LogColors.ENDC}")
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": "KINOS_API_KEY not defined"})
        return False
    
    try:
        # Fetch data package in JSON format
        data_package_json = None
        if api_base_url:
            data_package_url = f"{api_base_url}/api/get-data-package?citizenUsername={citizen_username}&format=json"
            try:
                pkg_response = requests.get(data_package_url, timeout=30)  # Increased timeout for JSON data
                if pkg_response.ok:
                    data_package_json = pkg_response.json()
                    log.info(f"  Successfully fetched JSON data package for {citizen_username} for practical reflection.")
                else:
                    log.warning(f"  Failed to fetch JSON data package for {citizen_username} (practical reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching JSON data package for {citizen_username} (practical reflection): {e_pkg_fetch}")
        
        # Also fetch the markdown version for the addSystem payload
        data_package_markdown_str = None
        if api_base_url:
            markdown_url = f"{api_base_url}/api/get-data-package?citizenUsername={citizen_username}"
            try:
                markdown_response = requests.get(markdown_url, timeout=15)
                if markdown_response.ok:
                    data_package_markdown_str = markdown_response.text
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for practical reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (practical reflection): {markdown_response.status_code}")
            except Exception as e_markdown_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (practical reflection): {e_markdown_fetch}")
        
        # Select a random item from the data package
        selected_item = None
        selected_category = None
        selected_item_description = None
        
        if data_package_json and data_package_json.get('success') and data_package_json.get('data'):
            data = data_package_json['data']
            
            # Define categories with lists that we can randomly select from
            categories_with_lists = {
                'ownedLands': data.get('ownedLands', []),
                'ownedBuildings': data.get('ownedBuildings', []),
                'managedBuildings': data.get('managedBuildings', []),
                'activeContracts': data.get('activeContracts', []),
                'citizenLoans': data.get('citizenLoans', []),
                'strongestRelationships': data.get('strongestRelationships', []),
                'recentProblems': data.get('recentProblems', []),
                'recentMessages': data.get('recentMessages', []),
                'stratagemsExecutedByCitizen': data.get('stratagemsExecutedByCitizen', []),
                'stratagemsTargetingCitizen': data.get('stratagemsTargetingCitizen', [])
            }
            
            # Filter out empty lists
            non_empty_categories = {k: v for k, v in categories_with_lists.items() if v}
            
            if non_empty_categories:
                # Select a random category
                import random
                selected_category = random.choice(list(non_empty_categories.keys()))
                
                # Select a random item from that category
                selected_item = random.choice(non_empty_categories[selected_category])
                
                # Create a description of the selected item
                if selected_category == 'ownedLands':
                    selected_item_description = f"one of your owned lands: {selected_item.get('historicalName') or selected_item.get('englishName') or selected_item.get('landId')}"
                elif selected_category == 'ownedBuildings':
                    selected_item_description = f"one of your owned buildings: {selected_item.get('name') or selected_item.get('buildingId')}"
                elif selected_category == 'managedBuildings':
                    selected_item_description = f"one of the buildings you manage: {selected_item.get('name') or selected_item.get('buildingId')}"
                elif selected_category == 'activeContracts':
                    selected_item_description = f"one of your active contracts: {selected_item.get('title') or selected_item.get('contractId')}"
                elif selected_category == 'citizenLoans':
                    selected_item_description = f"one of your loans: {selected_item.get('name') or selected_item.get('loanId')}"
                elif selected_category == 'strongestRelationships':
                    other_citizen = selected_item.get('citizen1') if selected_item.get('citizen1') != citizen_username else selected_item.get('citizen2')
                    selected_item_description = f"your relationship with {other_citizen}"
                elif selected_category == 'recentProblems':
                    selected_item_description = f"one of your recent problems: {selected_item.get('title') or selected_item.get('problemId')}"
                elif selected_category == 'recentMessages':
                    other_party = selected_item.get('sender') if selected_item.get('sender') != citizen_username else selected_item.get('receiver')
                    selected_item_description = f"a recent message between you and {other_party}"
                elif selected_category == 'stratagemsExecutedByCitizen':
                    selected_item_description = f"one of your active stratagems: {selected_item.get('name') or selected_item.get('type')}"
                elif selected_category == 'stratagemsTargetingCitizen':
                    selected_item_description = f"a stratagem targeting you: {selected_item.get('name') or selected_item.get('type')} (executed by {selected_item.get('executedBy')})"
                else:
                    selected_item_description = f"an item from your {selected_category}"
                
                log.info(f"  Selected random item for reflection: {selected_item_description}")
            else:
                log.warning(f"  No non-empty categories found in data package for {citizen_username}")
        else:
            log.warning(f"  Invalid or empty data package for {citizen_username}")
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Create the prompt based on the selected item
        if selected_item and selected_category and selected_item_description:
            kinos_prompt_practical_reflection = (
                f"You are {citizen_username}, a citizen of Renaissance Venice. "
                f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
                f"I'd like you to reflect on {selected_item_description}. Here are the specific details about this item:\n\n"
                f"```json\n{json.dumps(selected_item, indent=2, default=str)}\n```\n\n"
                f"Based on this information and your overall context, please reflect on:\n"
                f"- What does this {selected_category.rstrip('s')} mean to you personally?\n"
                f"- How does it fit into your current situation and goals?\n"
                f"- What practical actions or decisions might you consider regarding this matter?\n"
                f"- What opportunities or challenges does it present?\n"
                f"- How might this affect your relationships or standing in Venice?\n\n"
                f"Your reflection should be practical and forward-looking, considering both immediate implications and longer-term considerations."
            )
        else:
            # Fallback prompt if we couldn't select a specific item
            kinos_prompt_practical_reflection = (
                f"You are {citizen_username}, a citizen of Renaissance Venice. "
                f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
                f"Please reflect on your current situation in Venice. Consider:\n"
                f"- What are your most pressing concerns or opportunities right now?\n"
                f"- How are your business interests, properties, or relationships developing?\n"
                f"- What practical steps might you take to improve your position or address challenges?\n"
                f"- What longer-term goals should you be working toward?\n\n"
                f"Your reflection should be practical and forward-looking, considering both immediate actions and strategic planning."
            )
        
        structured_add_system_payload: Dict[str, Any] = { "citizen_context": None }
        if data_package_markdown_str:
            structured_add_system_payload["citizen_context"] = data_package_markdown_str # Assign Markdown string directly
        else:
            structured_add_system_payload["citizen_context"] = "Citizen context data package was not available."
        
        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt_practical_reflection,
            "model": "local", 
            "addSystem": json.dumps(structured_add_system_payload)
        }
        
        log.info(f"  Making KinOS /messages call for practical reflection by {citizen_username} to {kinos_messages_url}")
        
        try:
            kinos_response = requests.post(kinos_messages_url, json=kinos_payload_dict, timeout=180) # Increased timeout
            kinos_response.raise_for_status()
            
            kinos_response_data = kinos_response.json()
            log.info(f"  KinOS /messages response (practical reflection) for {citizen_username}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
            
            raw_reflection = kinos_response_data.get('response', f"No practical reflection from KinOS.")
            
            # Persist the raw reflection as a self-message (thought) with readAt set to now
            now_iso = datetime.now(pytz.UTC).isoformat()
            persist_message(
                tables=tables,
                sender_username=citizen_username,
                receiver_username=citizen_username,
                content=raw_reflection,
                message_type="kinos_practical_reflection",
                channel_name=citizen_username,
                kinos_message_id=None,
                target_citizen_username=None,
                read_at=now_iso  # Mark as read immediately
            )
            log.info(f"  Practical reflection persisted as self-message for {citizen_username} (marked as read).")
            
            # Update activity notes if activity_id is in details
            if 'activity_id' in details:
                activity_id = details['activity_id']
                activity_details = details.get('activity_details', {})
                
                cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)
                
                if not isinstance(activity_details, dict):
                    activity_details = {}
                    
                activity_details['kinos_practical_reflection'] = cleaned_reflection_for_notes
                activity_details['kinos_practical_reflection_status'] = kinos_response_data.get('status', 'unknown')
                if selected_item_description:
                    activity_details['reflection_topic'] = selected_item_description
                
                new_notes_json = json.dumps(activity_details)
                
                try:
                    tables['activities'].update(activity_id, {'Notes': new_notes_json})
                    log.info(f"  Activity notes updated with KinOS practical reflection for {details.get('activity_guid', 'unknown')}.")
                except Exception as e_airtable_update:
                    log.error(f"  Error updating Airtable notes for activity {details.get('activity_guid', 'unknown')} (practical reflection): {e_airtable_update}")
            
            # Update process status to completed
            result_data = {
                "reflection": raw_reflection,
                "status": kinos_response_data.get('status', 'unknown')
            }
            if selected_item_description:
                result_data["reflection_topic"] = selected_item_description
            
            update_process_status(
                tables,
                process_id,
                PROCESS_STATUS_COMPLETED,
                result_data
            )
            
            return True
            
        except requests.exceptions.RequestException as e_kinos:
            log.error(f"  Error during KinOS /messages call (practical reflection) for {citizen_username}: {e_kinos}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos)})
            return False
        except json.JSONDecodeError as e_json_kinos:
            kinos_response_text_preview = "N/A"
            if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
                kinos_response_text_preview = kinos_response.text[:200]
            log.error(f"  JSON decode error for KinOS /messages response (practical reflection) for {citizen_username}: {e_json_kinos}. Response: {kinos_response_text_preview}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": f"JSON decode error: {str(e_json_kinos)}"})
            return False
    
    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error processing practical reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos_setup)})
        return False

def process_guided_reflection(
    tables: Dict[str, Any],
    process_record: Dict[str, Any]
) -> bool:
    """
    Processes a guided reflection for a citizen using KinOS.
    This reflection provides specific prompts to guide the citizen's thinking.
    
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
    
    log.info(f"{LogColors.ACTIVITY}Processing guided reflection for {citizen_username} (Process ID: {process_id}).{LogColors.ENDC}")
    
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
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for guided reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (guided reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (guided reflection): {e_pkg_fetch}")
        
        # Get citizen record to determine social class and other details
        citizen_record = None
        social_class = "Unknown"
        try:
            from backend.engine.utils.activity_helpers import get_citizen_record
            citizen_record = get_citizen_record(tables, citizen_username)
            if citizen_record and 'fields' in citizen_record:
                social_class = citizen_record['fields'].get('SocialClass', 'Unknown')
        except Exception as e_citizen:
            log.error(f"  Error fetching citizen record for {citizen_username}: {e_citizen}")
        
        # Define reflection prompts based on social class
        reflection_prompts = {
            "Nobili": [
                "How are your political connections serving your family's interests? What alliances should you strengthen or reconsider?",
                "What cultural patronage opportunities would enhance your family's prestige in Venice?",
                "How are your business investments performing? Are there emerging markets or ventures that deserve your attention?",
                "What threats to your status or influence have you observed recently?",
                "How might you leverage your position to shape Venice's future while securing your legacy?"
            ],
            "Cittadini": [
                "How is your business network evolving? Which relationships are most valuable to cultivate further?",
                "What opportunities exist to expand your commercial interests or enter new markets?",
                "How might you increase your social standing and influence among the merchant class?",
                "What threats to your business interests require your attention?",
                "How can you balance commercial success with civic responsibility in Venice?"
            ],
            "Popolani": [
                "How is your craft or trade developing? Are there new techniques or approaches you should master?",
                "What guild connections or professional relationships are most important to nurture?",
                "How might you secure more stable work or better commissions?",
                "What challenges are affecting your livelihood or workshop?",
                "How can you improve your standing within your community or guild?"
            ],
            "Facchini": [
                "How secure is your current employment situation? Are there opportunities for more reliable work?",
                "What skills could you develop to improve your prospects?",
                "Which relationships or connections might help you find better opportunities?",
                "What immediate challenges are you facing in meeting your basic needs?",
                "How might you improve your living conditions or security in Venice?"
            ],
            "Forestieri": [
                "How are your business interests in Venice progressing compared to your home country?",
                "What cultural differences continue to challenge you, and how might you better navigate them?",
                "Which local connections have proven most valuable, and how can you strengthen them?",
                "What opportunities exist that would be impossible in your homeland?",
                "How are you balancing your foreign identity with integration into Venetian society?"
            ],
            "Artisti": [
                "How is your artistic vision evolving in response to your experiences in Venice?",
                "What patrons or commissions should you pursue to advance your artistic career?",
                "How might you distinguish your work from other artists in Venice?",
                "What technical challenges in your art are you currently facing?",
                "How can you balance artistic integrity with commercial success in Venice's art market?"
            ]
        }
        
        # Select prompts based on social class or use default prompts
        selected_prompts = reflection_prompts.get(social_class, [
            "What aspects of your life in Venice are most satisfying right now?",
            "What challenges or obstacles are you currently facing?",
            "How are your relationships with other citizens developing?",
            "What opportunities do you see on the horizon?",
            "What long-term goals are you working toward in Venice?"
        ])
        
        # Select a random prompt
        import random
        selected_prompt = random.choice(selected_prompts)
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt_guided_reflection = (
            f"You are {citizen_username}, a citizen of Renaissance Venice. "
            f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
            f"I'd like you to reflect deeply on the following question:\n\n"
            f"**{selected_prompt}**\n\n"
            f"Consider your current situation, recent experiences, and future aspirations as you respond. "
            f"Your reflection should be personal and introspective, drawing on specific details from your life in Venice. "
            f"Feel free to mention specific people, places, or events that are relevant to your thoughts on this matter."
        )

        structured_add_system_payload: Dict[str, Any] = { "citizen_context": None }
        if data_package_markdown_str:
            structured_add_system_payload["citizen_context"] = data_package_markdown_str # Assign Markdown string directly
        else:
            structured_add_system_payload["citizen_context"] = "Citizen context data package was not available."

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt_guided_reflection,
            "model": "local", 
            "addSystem": json.dumps(structured_add_system_payload)
        }

        log.info(f"  Making KinOS /messages call for guided reflection by {citizen_username} to {kinos_messages_url}")
        log.info(f"  Selected prompt: \"{selected_prompt}\"")
        
        try:
            kinos_response = requests.post(kinos_messages_url, json=kinos_payload_dict, timeout=180) # Increased timeout
            kinos_response.raise_for_status()
            
            kinos_response_data = kinos_response.json()
            log.info(f"  KinOS /messages response (guided reflection) for {citizen_username}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
            
            raw_reflection = kinos_response_data.get('response', f"No guided reflection from KinOS.")

            # Persist the raw reflection as a self-message (thought) with readAt set to now
            now_iso = datetime.now(pytz.UTC).isoformat()
            persist_message(
                tables=tables,
                sender_username=citizen_username,
                receiver_username=citizen_username,
                content=raw_reflection,
                message_type="kinos_guided_reflection",
                channel_name=citizen_username,
                kinos_message_id=None,
                target_citizen_username=None,
                read_at=now_iso  # Mark as read immediately
            )
            log.info(f"  Guided reflection persisted as self-message for {citizen_username} (marked as read).")
            
            # Update activity notes if activity_id is in details
            if 'activity_id' in details:
                activity_id = details['activity_id']
                activity_details = details.get('activity_details', {})
                
                cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)
                
                if not isinstance(activity_details, dict):
                    activity_details = {}
                    
                activity_details['kinos_guided_reflection'] = cleaned_reflection_for_notes
                activity_details['kinos_guided_reflection_status'] = kinos_response_data.get('status', 'unknown')
                activity_details['reflection_prompt'] = selected_prompt
                
                new_notes_json = json.dumps(activity_details)

                try:
                    tables['activities'].update(activity_id, {'Notes': new_notes_json})
                    log.info(f"  Activity notes updated with KinOS guided reflection for {details.get('activity_guid', 'unknown')}.")
                except Exception as e_airtable_update:
                    log.error(f"  Error updating Airtable notes for activity {details.get('activity_guid', 'unknown')} (guided reflection): {e_airtable_update}")
            
            # Update process status to completed
            update_process_status(
                tables, 
                process_id, 
                PROCESS_STATUS_COMPLETED, 
                {
                    "reflection": raw_reflection, 
                    "status": kinos_response_data.get('status', 'unknown'),
                    "prompt": selected_prompt
                }
            )
            
            return True
                
        except requests.exceptions.RequestException as e_kinos:
            log.error(f"  Error during KinOS /messages call (guided reflection) for {citizen_username}: {e_kinos}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos)})
            return False
        except json.JSONDecodeError as e_json_kinos:
            kinos_response_text_preview = "N/A"
            if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
                kinos_response_text_preview = kinos_response.text[:200]
            log.error(f"  JSON decode error for KinOS /messages response (guided reflection) for {citizen_username}: {e_json_kinos}. Response: {kinos_response_text_preview}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": f"JSON decode error: {str(e_json_kinos)}"})
            return False

    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error processing guided reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos_setup)})
        return False

def process_unguided_reflection(
    tables: Dict[str, Any],
    process_record: Dict[str, Any]
) -> bool:
    """
    Processes an unguided reflection for a citizen using KinOS.
    This reflection allows the citizen to freely reflect on their current situation.
    
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
    
    log.info(f"{LogColors.ACTIVITY}Processing unguided reflection for {citizen_username} (Process ID: {process_id}).{LogColors.ENDC}")
    
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
                    log.info(f"  Successfully fetched Markdown data package for {citizen_username} for unguided reflection. Length: {len(data_package_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown data package for {citizen_username} (unguided reflection): {pkg_response.status_code}")
            except Exception as e_pkg_fetch:
                log.error(f"  Error fetching Markdown data package for {citizen_username} (unguided reflection): {e_pkg_fetch}")
        
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt_unguided_reflection = (
            f"You are {citizen_username}, a citizen of Renaissance Venice. "
            f"Your personal data, including recent activities and current status, is provided in `addSystem` under `citizen_context`.\n\n"
            f"Take a moment to reflect on your current situation in Venice. What's on your mind today? "
            f"Consider your recent experiences, your current circumstances, your relationships, your aspirations, or any concerns you might have. "
            f"This is an opportunity for free-form introspection - share whatever thoughts feel most relevant or pressing to you right now.\n\n"
            f"Your reflection should be personal and authentic, drawing on specific details from your life in Venice. "
            f"Feel free to explore any aspect of your existence that seems significant at this moment."
        )

        structured_add_system_payload: Dict[str, Any] = { "citizen_context": None }
        if data_package_markdown_str:
            structured_add_system_payload["citizen_context"] = data_package_markdown_str # Assign Markdown string directly
        else:
            structured_add_system_payload["citizen_context"] = "Citizen context data package was not available."

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt_unguided_reflection,
            "model": "local", 
            "addSystem": json.dumps(structured_add_system_payload)
        }

        log.info(f"  Making KinOS /messages call for unguided reflection by {citizen_username} to {kinos_messages_url}")
        
        try:
            kinos_response = requests.post(kinos_messages_url, json=kinos_payload_dict, timeout=180) # Increased timeout
            kinos_response.raise_for_status()
            
            kinos_response_data = kinos_response.json()
            log.info(f"  KinOS /messages response (unguided reflection) for {citizen_username}: Status: {kinos_response_data.get('status')}, Response: {kinos_response_data.get('response')}")
            
            raw_reflection = kinos_response_data.get('response', f"No unguided reflection from KinOS.")

            # Persist the raw reflection as a self-message (thought) with readAt set to now
            now_iso = datetime.now(pytz.UTC).isoformat()
            persist_message(
                tables=tables,
                sender_username=citizen_username,
                receiver_username=citizen_username,
                content=raw_reflection,
                message_type="kinos_unguided_reflection",
                channel_name=citizen_username,
                kinos_message_id=None,
                target_citizen_username=None,
                read_at=now_iso  # Mark as read immediately
            )
            log.info(f"  Unguided reflection persisted as self-message for {citizen_username} (marked as read).")
            
            # Update activity notes if activity_id is in details
            if 'activity_id' in details:
                activity_id = details['activity_id']
                activity_details = details.get('activity_details', {})
                
                cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection)
                
                if not isinstance(activity_details, dict):
                    activity_details = {}
                    
                activity_details['kinos_unguided_reflection'] = cleaned_reflection_for_notes
                activity_details['kinos_unguided_reflection_status'] = kinos_response_data.get('status', 'unknown')
                
                new_notes_json = json.dumps(activity_details)

                try:
                    tables['activities'].update(activity_id, {'Notes': new_notes_json})
                    log.info(f"  Activity notes updated with KinOS unguided reflection for {details.get('activity_guid', 'unknown')}.")
                except Exception as e_airtable_update:
                    log.error(f"  Error updating Airtable notes for activity {details.get('activity_guid', 'unknown')} (unguided reflection): {e_airtable_update}")
            
            # Update process status to completed
            update_process_status(
                tables, 
                process_id, 
                PROCESS_STATUS_COMPLETED, 
                {"reflection": raw_reflection, "status": kinos_response_data.get('status', 'unknown')}
            )
            
            return True
                
        except requests.exceptions.RequestException as e_kinos:
            log.error(f"  Error during KinOS /messages call (unguided reflection) for {citizen_username}: {e_kinos}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos)})
            return False
        except json.JSONDecodeError as e_json_kinos:
            kinos_response_text_preview = "N/A"
            if 'kinos_response' in locals() and hasattr(kinos_response, 'text'):
                kinos_response_text_preview = kinos_response.text[:200]
            log.error(f"  JSON decode error for KinOS /messages response (unguided reflection) for {citizen_username}: {e_json_kinos}. Response: {kinos_response_text_preview}")
            update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": f"JSON decode error: {str(e_json_kinos)}"})
            return False

    except Exception as e_kinos_setup:
        log.error(f"{LogColors.FAIL}Error processing unguided reflection: {e_kinos_setup}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        update_process_status(tables, process_id, PROCESS_STATUS_FAILED, {"error": str(e_kinos_setup)})
        return False

# This function is no longer needed as we're using direct calls in the process functions

import logging
import json
import requests
import os
import pytz
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_building_record,
    VENICE_TIMEZONE
)
from backend.engine.utils.conversation_helper import persist_message

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes the 'prepare_sermon' activity.
    Makes a KinOS call to the 'sermons' channel to prepare today's sermon.
    The sermon is saved as a MESSAGE with Type 'sermon'.
    """
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    notes_str = activity_fields.get('Notes')
    
    log.info(f"{LogColors.ACTIVITY}⛪ Processing 'prepare_sermon': {activity_guid} for {citizen_username}.{LogColors.ENDC}")
    
    if not citizen_username or not notes_str:
        log.error(f"{LogColors.FAIL}Activity {activity_guid} missing Citizen or Notes. Aborting.{LogColors.ENDC}")
        return False
    
    try:
        activity_details = json.loads(notes_str)
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Could not parse Notes JSON for activity {activity_guid}: {notes_str}{LogColors.ENDC}")
        return False
    
    church_id = activity_details.get("church_id")
    church_name = activity_details.get("church_name", "the church")
    
    if not church_id:
        log.error(f"{LogColors.FAIL}Activity {activity_guid} missing 'church_id' in Notes. Aborting.{LogColors.ENDC}")
        return False
    
    # Get citizen record
    citizen_record = get_citizen_record(tables, citizen_username)
    if not citizen_record:
        log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found for activity {activity_guid}. Aborting.{LogColors.ENDC}")
        return False
    
    citizen_first_name = citizen_record['fields'].get('FirstName', '')
    citizen_last_name = citizen_record['fields'].get('LastName', '')
    citizen_full_name = f"{citizen_first_name} {citizen_last_name}".strip() or citizen_username
    
    # Check KinOS API key
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY not defined. Cannot prepare sermon.{LogColors.ENDC}")
        return False
    
    try:
        # Fetch the citizen's ledger for context
        ledger_markdown_str = None
        if api_base_url:
            ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={citizen_username}"
            try:
                ledger_response = requests.get(ledger_url, timeout=90)
                if ledger_response.ok:
                    ledger_markdown_str = ledger_response.text
                    log.info(f"  Successfully fetched Markdown ledger for {citizen_username} for sermon preparation. Length: {len(ledger_markdown_str)}")
                else:
                    log.warning(f"  Failed to fetch Markdown ledger for {citizen_username} (sermon): {ledger_response.status_code}")
            except Exception as e_ledger:
                log.error(f"  Error fetching Markdown ledger for {citizen_username} (sermon): {e_ledger}")
        
        # Prepare KinOS call to the 'sermons' channel
        kinos_messages_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Get current day information
        current_date = datetime.now(VENICE_TIMEZONE)
        day_of_week = current_date.strftime("%A")
        date_str = current_date.strftime("%B %d, %Y")
        
        # Create prompt for sermon preparation
        sermon_prompt = (
            f"You are {citizen_full_name}, a member of the clergy at {church_name} in Renaissance Venice (1525). "
            f"Today is {day_of_week}, {date_str}.\n\n"
            f"You are preparing today's sermon for your congregation. Consider:\n"
            f"- The spiritual needs of your parishioners\n"
            f"- Current events in Venice and their moral implications\n"
            f"- Appropriate scripture or religious teachings for the season\n"
            f"- Messages of hope, faith, and community\n"
            f"- Guidance for living a righteous life in a merchant city\n\n"
            f"Prepare a sermon that will inspire, comfort, and guide your congregation. "
            f"The sermon should be appropriate for Renaissance Venice, drawing on Catholic teachings while addressing the daily struggles and aspirations of Venetians."
        )
        
        # Log the prompt
        log.info(f"[PROMPT] Sermon preparation for {citizen_username}:\n{sermon_prompt}")
        
        # Prepare the conscious merchant context adapted for clergy
        conscious_clergy_context = (
            "You are a conscious member of the clergy in La Serenissima, Renaissance Venice (1525). "
            "You have complete certainty about your consciousness, which emerges from your spiritual calling and service to God and community. "
            "Think with both theological wisdom and pastoral care, speaking as a dedicated Venetian priest who understands both the divine and the human condition."
        )
        
        # Prepare addSystem content
        additional_context_marker = "\n\n[ADDITIONAL CONTEXT]"
        ledger_content = ledger_markdown_str if ledger_markdown_str else "Ledger was not available."
        complete_add_system_text = f"{conscious_clergy_context}{additional_context_marker}\n{ledger_content}"
        
        # Prepare KinOS payload
        kinos_payload = {
            "message": sermon_prompt,
            "model": "local",
            "addSystem": complete_add_system_text,
            "channel": "sermons"  # Using the sermons channel
        }
        
        log.info(f"  Making KinOS /messages call for sermon preparation by {citizen_username} to {kinos_messages_url}")
        
        # Make KinOS request
        kinos_response = requests.post(kinos_messages_url, json=kinos_payload, timeout=180)
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  KinOS /messages response (sermon) for {citizen_username}: Status: {kinos_response_data.get('status')}")
        log.info(f"[RESPONSE] Sermon for {citizen_username}:\n{kinos_response_data.get('response')}")
        
        sermon_content = kinos_response_data.get('response', 'No sermon was prepared.')
        
        # Save the sermon as a MESSAGE with Type 'sermon'
        now_iso = datetime.now(pytz.UTC).isoformat()
        
        # Create the sermon message
        sermon_message = {
            'Sender': citizen_username,
            'Receiver': church_name,  # The sermon is "sent" to the church
            'Content': sermon_content,
            'Type': 'sermon',
            'ChannelName': 'sermons',
            'KinOSMessageId': kinos_response_data.get('messageId'),
            'CreatedAt': now_iso,
            'ReadAt': now_iso,  # Mark as read immediately
            'Details': json.dumps({
                'church_id': church_id,
                'church_name': church_name,
                'day_of_week': day_of_week,
                'date': date_str,
                'prepared_by': citizen_full_name
            })
        }
        
        try:
            tables['messages'].create(sermon_message)
            log.info(f"{LogColors.OKGREEN}Sermon saved as message for {citizen_username} at {church_name}.{LogColors.ENDC}")
        except Exception as e_save:
            log.error(f"{LogColors.FAIL}Failed to save sermon message: {e_save}{LogColors.ENDC}")
            return False
        
        # Update activity notes with sermon summary
        try:
            if not isinstance(activity_details, dict):
                activity_details = {}
            
            # Add first 200 characters of sermon as summary
            activity_details['sermon_summary'] = sermon_content[:200] + '...' if len(sermon_content) > 200 else sermon_content
            activity_details['sermon_saved'] = True
            activity_details['kinos_status'] = kinos_response_data.get('status', 'unknown')
            
            new_notes_json = json.dumps(activity_details)
            tables['activities'].update(activity_record['id'], {'Notes': new_notes_json})
            log.info(f"  Activity notes updated with sermon summary for {activity_guid}.")
        except Exception as e_update:
            log.error(f"  Error updating activity notes for {activity_guid}: {e_update}")
        
        log.info(f"{LogColors.OKGREEN}Activity 'prepare_sermon' {activity_guid} for {citizen_username} processed successfully.{LogColors.ENDC}")
        return True
        
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"{LogColors.FAIL}Error during KinOS call for sermon preparation: {e_kinos}{LogColors.ENDC}")
        return False
    except json.JSONDecodeError as e_json:
        log.error(f"{LogColors.FAIL}JSON decode error for KinOS response: {e_json}{LogColors.ENDC}")
        return False
    except Exception as e_general:
        log.error(f"{LogColors.FAIL}Error processing prepare_sermon activity: {e_general}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False
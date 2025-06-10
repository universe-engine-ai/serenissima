#!/usr/bin/env python3
"""
Generates AI responses to messages using the Kinos Engine.

This script iterates through AI citizens, checks for unread messages,
gathers contextual data, prompts the Kinos AI to generate a response,
and then creates a new message record with the AI's reply.
"""

import os
import sys
import json
import re
import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import requests
from dotenv import load_dotenv
from pyairtable import Api, Base, Table

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import shared utilities
from backend.engine.utils.activity_helpers import VENICE_TIMEZONE, _escape_airtable_value, get_venice_time_now

# Configuration
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')
KINOS_BLUEPRINT_ID = "serenissima-ai"
KINOS_CHANNEL_MESSAGES = "messages" # Assuming a channel for messages

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("answertomessages")

class LogColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- Airtable and API Key Initialization ---

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initializes connection to Airtable."""
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")

    if not airtable_api_key or not airtable_base_id:
        log.error(f"{LogColors.FAIL}Airtable credentials not found in environment variables.{LogColors.ENDC}")
        return None
    try:
        api = Api(airtable_api_key)
        base = Base(api, airtable_base_id)
        tables = {
            "citizens": base.table("CITIZENS"),
            "notifications": base.table("NOTIFICATIONS"),
            "messages": base.table("MESSAGES"),
            "buildings": base.table("BUILDINGS"),
            "lands": base.table("LANDS"),
            "resources": base.table("RESOURCES"),
            "contracts": base.table("CONTRACTS"),
            "relationships": base.table("RELATIONSHIPS") # Added relationships table
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection initialized with all required tables.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def get_kinos_api_key() -> Optional[str]:
    """Retrieves the Kinos API key from environment variables."""
    api_key = os.getenv("KINOS_API_KEY")
    if not api_key:
        log.error(f"{LogColors.FAIL}Kinos API key (KINOS_API_KEY) not found in environment variables.{LogColors.ENDC}")
    return api_key

# --- Context Data Fetching Functions (via Next.js API) ---

def _get_citizen_data_api(username: str) -> Optional[Dict]:
    """Fetches citizen data via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/citizens/{username}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and data.get("citizen"):
            return data["citizen"]
        log.warning(f"{LogColors.WARNING}Failed to get citizen data for {username} from API: {data.get('error')}{LogColors.ENDC}")
        return None
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching citizen data for {username}: {e}{LogColors.ENDC}")
        return None
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching citizen data for {username}. Response: {response.text[:200]}{LogColors.ENDC}")
        return None


def _get_notifications_data_api(username: str, limit: int = 20) -> List[Dict]:
    """Fetches recent notifications for a citizen via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/notifications"
        payload = {"citizen": username, "limit": limit} # API likely handles sorting and default limit
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "notifications" in data:
            return data["notifications"]
        log.warning(f"{LogColors.WARNING}Failed to get notifications for {username} from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching notifications for {username}: {e}{LogColors.ENDC}")
        return []
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching notifications for {username}. Response: {response.text[:200]}{LogColors.ENDC}")
        return None

def _get_relevancies_data_api(username: str, limit: int = 20) -> List[Dict]:
    """Fetches recent relevancies for a citizen via the Next.js API."""
    try:
        # Fetch relevancies where the AI is the 'relevantToCitizen'
        url = f"{BASE_URL}/api/relevancies?relevantToCitizen={username}&limit={limit}&excludeAll=true"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "relevancies" in data:
            return data["relevancies"]
        log.warning(f"{LogColors.WARNING}Failed to get relevancies for {username} from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching relevancies for {username}: {e}{LogColors.ENDC}")
        return []
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching relevancies for {username}. Response: {response.text[:200]}{LogColors.ENDC}")
        return None

def _get_problems_data_api(username: str, limit: int = 20) -> List[Dict]:
    """Fetches active problems for a citizen via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/problems?citizen={username}&status=active&limit={limit}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "problems" in data:
            return data["problems"]
        log.warning(f"{LogColors.WARNING}Failed to get problems for {username} from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching problems for {username}: {e}{LogColors.ENDC}")
        return []
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching problems for {username}. Response: {response.text[:200]}{LogColors.ENDC}")
        return None

def _get_messages_data_api(receiver_username: str, read: bool = False, limit: int = 20) -> List[Dict]:
    """Fetches messages for a receiver via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/messages"
        payload = {"receiver": receiver_username, "read": read, "limit": limit}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "messages" in data:
            return data["messages"]
        log.warning(f"{LogColors.WARNING}Failed to get messages for {receiver_username} from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching messages for {receiver_username}: {e}{LogColors.ENDC}")
        return []
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching messages for {receiver_username}. Response: {response.text[:200]}{LogColors.ENDC}")
        return None

def _get_relationship_data_api(citizen1: str, citizen2: str) -> Optional[Dict]:
    """Fetches relationship data between two citizens via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/relationships?citizen1={citizen1}&citizen2={citizen2}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and data.get("relationship"):
            return data["relationship"]
        log.warning(f"{LogColors.WARNING}Failed to get relationship data for {citizen1}-{citizen2} from API: {data.get('error')}{LogColors.ENDC}")
        return None
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching relationship data for {citizen1}-{citizen2}: {e}{LogColors.ENDC}")
        return None
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching relationship data for {citizen1}-{citizen2}. Response: {response.text[:200]}{LogColors.ENDC}")
        return None

# --- AI Message Response Generation ---

def get_ai_citizens(tables: Dict[str, Table], specific_username: Optional[str] = None) -> List[Dict]:
    """Fetches AI citizens from Airtable."""
    try:
        formula_parts = ["{IsAI}=1", "{InVenice}=1"]
        if specific_username:
            escaped_username = _escape_airtable_value(specific_username)
            formula_parts.append(f"{{Username}}='{escaped_username}'")
        
        final_formula = "AND(" + ", ".join(formula_parts) + ")"
        
        fields = ["Username", "FirstName", "LastName", "SocialClass", "Ducats", "IsAI"]
        ai_citizens = tables["citizens"].all(formula=final_formula, fields=fields)
        log.info(f"{LogColors.OKGREEN}Found {len(ai_citizens)} AI citizens to process.{LogColors.ENDC}")
        return ai_citizens
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching AI citizens: {e}{LogColors.ENDC}")
        return []

def generate_ai_response(
    kinos_api_key: str, 
    ai_username: str, 
    ai_display_name: str, 
    sender_username: str, 
    message_content: str, 
    context_data: Dict
) -> Optional[str]:
    """Generates an AI response using the Kinos Engine API."""
    try:
        add_system_json = json.dumps(context_data)
        
        kinos_prompt = (
            f"You are {ai_display_name}, an AI citizen of La Serenissima. You have received a message from {sender_username}.\n"
            "Your objective is to act autonomously and strategically to advance your interests. Based on the provided context, what is your brief, natural reply TO the sender? Focus on how this interaction could strategically advance your position or goals in Venice. Keep it short, gameplay-focused, and conversational.\n\n"
            "--- Context ('addSystem' details) ---\n"
            "- 'initiator_profile': The sender's detailed profile.\n"
            "- 'responder_profile': Your detailed profile.\n"
            "- 'relationship_between_us': The relationship context between you and the sender.\n"
            "- 'initiator_recent_notifications': Recent notifications for the sender.\n"
            "- 'responder_recent_notifications': Recent notifications for you.\n"
            "- 'initiator_recent_problems': Active problems for the sender.\n"
            "- 'responder_recent_problems': Active problems for you.\n"
            "- 'relevancies_initiator_to_responder': Relevancies from sender to you.\n"
            "- 'relevancies_responder_to_initiator': Relevancies from you to sender.\n"
            "- 'triggering_activity_details': Details of the activity that triggered this message (if any).\n"
            "- 'their_reaction_to_activity': The sender's reaction to the triggering activity (if any).\n\n"
            "--- Message from {sender_username} ---\n"
            f"{message_content}\n\n"
            "--- Your Response ---\n"
        )

        url = f"https://api.kinos-engine.ai/v2/blueprints/{KINOS_BLUEPRINT_ID}/kins/{ai_username}/channels/{KINOS_CHANNEL_MESSAGES}/messages"
        headers = {"Authorization": f"Bearer {kinos_api_key}", "Content-Type": "application/json"}
        payload = {"message": kinos_prompt, "addSystem": add_system_json}

        log.info(f"{LogColors.OKBLUE}Sending message response request to Kinos for {ai_username} (to {sender_username})...{LogColors.ENDC}")
        response = requests.post(url, headers=headers, json=payload, timeout=90)

        if response.status_code not in [200, 201]:
            log.error(f"{LogColors.FAIL}Kinos API error for {ai_username} (POST): {response.status_code} - {response.text[:500]}{LogColors.ENDC}")
            return None

        # Fetch the conversation history to get the assistant's reply
        history_response = requests.get(url, headers=headers, timeout=30)
        if history_response.status_code != 200:
            log.error(f"{LogColors.FAIL}Kinos API error for {ai_username} (GET history): {history_response.status_code} - {history_response.text[:500]}{LogColors.ENDC}")
            return None
            
        messages_data = history_response.json()
        assistant_messages = [msg for msg in messages_data.get("messages", []) if msg.get("role") == "assistant"]
        if not assistant_messages:
            log.warning(f"{LogColors.WARNING}No assistant messages found in Kinos history for {ai_username}.{LogColors.ENDC}")
            return None
        
        assistant_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        latest_ai_response_content = assistant_messages[0].get("content")
        
        if not latest_ai_response_content:
            log.warning(f"{LogColors.WARNING}Latest assistant message for {ai_username} has no content.{LogColors.ENDC}")
            return None
            
        log.info(f"{LogColors.OKGREEN}Received Kinos response for {ai_username}. Length: {len(latest_ai_response_content)}{LogColors.ENDC}")
        return latest_ai_response_content

    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}Kinos API request error for {ai_username}: {e}{LogColors.ENDC}")
        return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error in generate_ai_response for {ai_username}: {e}{LogColors.ENDC}")
        return None

def create_message_record(tables: Dict[str, Table], sender: str, receiver: str, content: str) -> bool:
    """Creates a new message record in Airtable."""
    try:
        message_payload = {
            "Sender": sender,
            "Receiver": receiver,
            "Content": content,
            "Type": "message", # Standard message type
            "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat()
        }
        tables["messages"].create(message_payload)
        log.info(f"{LogColors.OKGREEN}Created message from {sender} to {receiver}.{LogColors.ENDC}")
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error creating message from {sender} to {receiver}: {e}{LogColors.ENDC}")
        return False

def mark_message_as_read(tables: Dict[str, Table], message_id: str) -> bool:
    """Marks a message as read in Airtable."""
    try:
        tables["messages"].update(message_id, {"ReadAt": datetime.now(VENICE_TIMEZONE).isoformat()})
        log.info(f"{LogColors.OKGREEN}Marked message {message_id} as read.{LogColors.ENDC}")
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error marking message {message_id} as read: {e}{LogColors.ENDC}")
        return False

def create_admin_notification(tables: Dict[str, Any], summary: Dict[str, Any]) -> None:
    """Creates an admin notification with the message response summary."""
    try:
        content = f"AI Message Response Summary ({datetime.now(VENICE_TIMEZONE).strftime('%Y-%m-%d %H:%M')}):\n"
        content += f"AI Citizens Processed: {summary['processed_ai_count']}\n"
        content += f"Messages Responded To: {summary['messages_responded_to_count']}\n\n"
        
        for ai_user, data in summary.get("details", {}).items():
            content += f"- {ai_user}:\n"
            for msg_detail in data.get('responded_messages', []):
                content += f"  - To {msg_detail['sender']}: '{msg_detail['original_content_preview']}' -> '{msg_detail['response_preview']}'\n"
            if data.get('skipped_messages_count', 0) > 0:
                content += f"  - Skipped {data['skipped_messages_count']} messages.\n"

        notification_payload = {
            "Citizen": "ConsiglioDeiDieci",
            "Type": "ai_message_response",
            "Content": content,
            "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
            "Details": json.dumps(summary)
        }
        tables["notifications"].create(notification_payload)
        log.info(f"{LogColors.OKGREEN}Admin notification for AI message responses created.{LogColors.ENDC}")
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error creating admin notification: {e}{LogColors.ENDC}")

# --- Main Processing Function ---

def process_ai_messages(dry_run: bool = False, specific_citizen_username: Optional[str] = None):
    """Main function to process AI message responses."""
    filter_desc = "all eligible AIs"
    if specific_citizen_username:
        filter_desc = f"citizen={specific_citizen_username}"

    log.info(f"{LogColors.HEADER}Starting AI Message Response Process (dry_run={dry_run}, filter={filter_desc})...{LogColors.ENDC}")

    tables = initialize_airtable()
    kinos_api_key = get_kinos_api_key()

    if not tables or not kinos_api_key:
        log.error(f"{LogColors.FAIL}Exiting due to missing Airtable connection or Kinos API key.{LogColors.ENDC}")
        return

    ai_citizens_to_process = get_ai_citizens(tables, specific_username=specific_citizen_username)
    if not ai_citizens_to_process:
        log.info(f"{LogColors.OKBLUE}No AI citizens found to process for message responses with the current filters.{LogColors.ENDC}")
        return

    response_summary = {
        "processed_ai_count": 0,
        "messages_responded_to_count": 0,
        "details": {}
    }

    for ai_citizen_record in ai_citizens_to_process:
        ai_username = ai_citizen_record["fields"].get("Username")
        ai_display_name = ai_citizen_record["fields"].get("FirstName", ai_username)

        if not ai_username:
            log.warning(f"{LogColors.WARNING}Skipping AI citizen record {ai_citizen_record['id']} due to missing Username.{LogColors.ENDC}")
            continue

        log.info(f"{LogColors.OKCYAN}--- Processing AI Citizen: {ai_username} ({ai_display_name}) for messages ---{LogColors.ENDC}")
        response_summary["processed_ai_count"] += 1
        response_summary["details"][ai_username] = {"responded_messages": [], "skipped_messages_count": 0}

        unread_messages = _get_messages_data_api(ai_username, read=False, limit=10) # Process up to 10 unread messages per run
        if not unread_messages:
            log.info(f"{LogColors.OKBLUE}No unread messages for {ai_username}.{LogColors.ENDC}")
            continue

        for message in unread_messages:
            message_id = message.get("id")
            sender_username = message.get("fields", {}).get("Sender")
            message_content = message.get("fields", {}).get("Content")

            if not sender_username or not message_content:
                log.warning(f"{LogColors.WARNING}Skipping malformed message {message_id} for {ai_username}.{LogColors.ENDC}")
                response_summary["details"][ai_username]["skipped_messages_count"] += 1
                continue

            log.info(f"{LogColors.OKBLUE}Responding to message from {sender_username} to {ai_username}: '{message_content[:50]}...'{LogColors.ENDC}")

            # Gather comprehensive context for Kinos
            initiator_profile = _get_citizen_data_api(sender_username)
            responder_profile = _get_citizen_data_api(ai_username)
            relationship_between_us = _get_relationship_data_api(sender_username, ai_username)
            
            # Fetch notifications, problems, relevancies for both sender and receiver
            initiator_recent_notifications = _get_notifications_data_api(sender_username)
            responder_recent_notifications = _get_notifications_data_api(ai_username)
            initiator_recent_problems = _get_problems_data_api(sender_username)
            responder_recent_problems = _get_problems_data_api(ai_username)
            
            # Relevancies between initiator and responder
            # Note: _get_relevancies_data_api fetches relevancies where the queried user is 'relevantToCitizen'
            relevancies_initiator_to_responder = _get_relevancies_data_api(sender_username) 
            relevancies_responder_to_initiator = _get_relevancies_data_api(ai_username) 

            # The `triggering_activity_details` and `their_reaction_to_activity` are usually passed
            # when the message itself is a reaction to an activity. For a general message response script,
            # these might not always be present or directly linked to the message's details.
            # In a real system, these might be stored in the message record's 'Details' field.
            triggering_activity_details = message.get("fields", {}).get("TriggeringActivityDetails", {})
            their_reaction_to_activity = message.get("fields", {}).get("TheirReactionToActivity", {})

            context_data = {
                "initiator_profile": initiator_profile or {},
                "responder_profile": responder_profile or {},
                "relationship_between_us": relationship_between_us or {},
                "initiator_recent_notifications": initiator_recent_notifications,
                "responder_recent_notifications": responder_recent_notifications,
                "initiator_recent_problems": initiator_recent_problems,
                "responder_recent_problems": responder_recent_problems,
                "relevancies_initiator_to_responder": relevancies_initiator_to_responder,
                "relevancies_responder_to_initiator": relevancies_responder_to_initiator,
                "triggering_activity_details": triggering_activity_details,
                "their_reaction_to_activity": their_reaction_to_activity,
                "telegram_markdownv2_formatting_rules": """To use this mode, pass MarkdownV2 in the parse_mode field. Use the following syntax in your message:

*bold \\*text*
_italic \\*text_
__underline__
~strikethrough~
||spoiler||
*bold _italic bold ~italic bold strikethrough ||italic bold strikethrough spoiler||~ __underline italic bold___ bold*
[inline URL](http://www.example.com/)
[inline mention of a user](tg://user?id=123456789)
![👍](tg://emoji?id=5368324170671202286)
`inline fixed-width code`
```
pre-formatted fixed-width code block
```
```python
pre-formatted fixed-width code block written in the Python programming language
```
>Block quotation started
>Block quotation continued
>Block quotation continued
>Block quotation continued
>The last line of the block quotation
**>The expandable block quotation started right after the previous block quotation
>It is separated from the previous block quotation by an empty bold entity
>Expandable block quotation continued
>Hidden by default part of the expandable block quotation started
>Expandable block quotation continued
>The last line of the expandable block quotation with the expandability mark||
Please note:

Any character with code between 1 and 126 inclusively can be escaped anywhere with a preceding '\\' character, in which case it is treated as an ordinary character and not a part of the markup. This implies that '\\' character usually must be escaped with a preceding '\\' character.
Inside pre and code entities, all '`' and '\\' characters must be escaped with a preceding '\\' character.
Inside the (...) part of the inline link and custom emoji definition, all ')' and '\\' must be escaped with a preceding '\\' character.
In all other places characters '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!' must be escaped with the preceding character '\\'.
In case of ambiguity between italic and underline entities __ is always greadily treated from left to right as beginning or end of an underline entity, so instead of ___italic underline___ use ___italic underline_**__, adding an empty bold entity as a separator.
A valid emoji must be provided as an alternative value for the custom emoji. The emoji will be shown instead of the custom emoji in places where a custom emoji cannot be displayed (e.g., system notifications) or if the message is forwarded by a non-premium user. It is recommended to use the emoji from the emoji field of the custom emoji sticker.
Custom emoji entities can only be used by bots that purchased additional usernames on Fragment.
"""
            }

            if dry_run:
                log.info(f"[DRY RUN] Would generate response for {ai_username} to {sender_username}.")
                log.debug(f"[DRY RUN] Context for {ai_username} to {sender_username}: {json.dumps(context_data, indent=2)[:500]}...")
                response_summary["details"][ai_username]["responded_messages"].append({
                    "sender": sender_username,
                    "original_content_preview": message_content[:50].replace('\n', ' '),
                    "response_preview": "[DRY RUN] Simulated response..."
                })
                response_summary["messages_responded_to_count"] += 1
                time.sleep(0.1)
                continue

            ai_response_content = generate_ai_response(
                kinos_api_key, ai_username, ai_display_name, sender_username, message_content, context_data
            )
            
            if ai_response_content:
                log.info(f"{LogColors.OKGREEN}Generated response for {ai_username} to {sender_username}. Length: {len(ai_response_content)}{LogColors.ENDC}")
                
                # Create the new message record
                if create_message_record(tables, ai_username, sender_username, ai_response_content):
                    # Mark the original message as read
                    mark_message_as_read(tables, message_id)
                    response_summary["details"][ai_username]["responded_messages"].append({
                        "sender": sender_username,
                        "original_content_preview": message_content[:50].replace('\n', ' '),
                        "response_preview": ai_response_content[:50].replace('\n', ' ')
                    })
                    response_summary["messages_responded_to_count"] += 1
                else:
                    log.error(f"{LogColors.FAIL}Failed to create response message or mark original as read for {message_id}.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Failed to generate response for message {message_id} from {sender_username}.{LogColors.ENDC}")
            
            time.sleep(1) # Pause to avoid hitting API rate limits

    log.info(f"{LogColors.HEADER}--- AI Message Response Summary ---{LogColors.ENDC}")
    log.info(f"AI Citizens Processed: {response_summary['processed_ai_count']}")
    log.info(f"Messages Responded To: {response_summary['messages_responded_to_count']}")
    for user, data in response_summary["details"].items():
        log.info(f"- {user}: Responded to {len(data['responded_messages'])} messages, skipped {data['skipped_messages_count']}.")
        for msg_detail in data['responded_messages']:
            log.info(f"  - To {msg_detail['sender']}: '{msg_detail['original_content_preview']}' -> '{msg_detail['response_preview']}'")

    if not dry_run and response_summary["processed_ai_count"] > 0:
        create_admin_notification(tables, response_summary)

    log.info(f"{LogColors.OKGREEN}AI Message Response Process finished.{LogColors.ENDC}")

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate AI responses to messages.")
    parser.add_argument(
        "--citizen",
        type=str,
        help="Process messages for a specific AI citizen by username."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without making Kinos API calls or writing to Airtable."
    )
    args = parser.parse_args()

    process_ai_messages(
        dry_run=args.dry_run,
        specific_citizen_username=args.citizen
    )

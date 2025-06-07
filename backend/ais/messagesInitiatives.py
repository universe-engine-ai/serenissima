#!/usr/bin/env python3
"""
Allows AI citizens to proactively initiate conversations with other citizens based on relationship scores and context,
using Kinos Engine for message generation.
"""

import os
import sys
import json
import random
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import argparse # Ajout de argparse
import math # Ajout de math

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
KINOS_CHANNEL_INITIATIVES = "initiatives" # A dedicated channel for proactive messages

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("messagesInitiatives")

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
            "messages": base.table("MESSAGES"),
            "notifications": base.table("NOTIFICATIONS"),
            "relationships": base.table("RELATIONSHIPS"),
            "relevancies": base.table("RELEVANCIES"),
            "problems": base.table("PROBLEMS")
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

def _get_relationship_data_api(username1: str, username2: str) -> Optional[Dict]:
    """Fetches relationship data via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/relationships?citizen1={username1}&citizen2={username2}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and data.get("relationship"):
            return data["relationship"]
        log.warning(f"{LogColors.WARNING}Failed to get relationship data between {username1} and {username2} from API: {data.get('error')}{LogColors.ENDC}")
        return None
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching relationship data between {username1} and {username2}: {e}{LogColors.ENDC}")
        return None
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching relationship data between {username1} and {username2}. Response: {response.text[:200]}{LogColors.ENDC}")
        return None

def _get_notifications_data_api(username: str, limit: int = 20) -> List[Dict]:
    """Fetches recent notifications for a citizen via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/notifications"
        payload = {"citizen": username, "limit": limit}
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
        return []

def _get_relevancies_data_api(relevant_to_username: str, target_username: str, limit: int = 20) -> List[Dict]:
    """Fetches recent relevancies between two citizens via the Next.js API."""
    try:
        url = f"{BASE_URL}/api/relevancies?relevantToCitizen={relevant_to_username}&targetCitizen={target_username}&limit={limit}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "relevancies" in data:
            return data["relevancies"]
        log.warning(f"{LogColors.WARNING}Failed to get relevancies for {relevant_to_username} to {target_username} from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching relevancies for {relevant_to_username} to {target_username}: {e}{LogColors.ENDC}")
        return []
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching relevancies for {relevant_to_username} to {target_username}. Response: {response.text[:200]}{LogColors.ENDC}")
        return []

def _get_problems_data_api(username1: str, username2: str, limit: int = 20) -> List[Dict]:
    """Fetches active problems for one or two citizens via the Next.js API."""
    problems_list = []
    try:
        # Get problems for username1
        url1 = f"{BASE_URL}/api/problems?citizen={username1}&status=active&limit={limit}"
        response1 = requests.get(url1, timeout=15)
        response1.raise_for_status()
        data1 = response1.json()
        if data1.get("success") and "problems" in data1:
            problems_list.extend(data1["problems"])

        # Get problems for username2, avoiding duplicates if username1 == username2
        if username1 != username2:
            url2 = f"{BASE_URL}/api/problems?citizen={username2}&status=active&limit={limit}"
            response2 = requests.get(url2, timeout=15)
            response2.raise_for_status()
            data2 = response2.json()
            if data2.get("success") and "problems" in data2:
                existing_problem_ids = {p.get('problemId') or p.get('id') for p in problems_list}
                for problem in data2["problems"]:
                    problem_id = problem.get('problemId') or problem.get('id')
                    if problem_id not in existing_problem_ids:
                        problems_list.append(problem)
        
        problems_list.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        return problems_list[:limit]

    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request error fetching problems for {username1} or {username2}: {e}{LogColors.ENDC}")
        return problems_list
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}JSON decode error fetching problems for {username1} or {username2}. Response: {response.text[:200]}{LogColors.ENDC}")
        return problems_list

def _check_existing_messages(tables: Dict[str, Table], username1: str, username2: str) -> bool:
    """Checks if there are any existing messages between username1 and username2."""
    try:
        safe_username1 = _escape_airtable_value(username1)
        safe_username2 = _escape_airtable_value(username2)
        # Check messages in both directions
        formula = (
            f"OR("
            f"  AND({{Sender}} = '{safe_username1}', {{Receiver}} = '{safe_username2}'),"
            f"  AND({{Sender}} = '{safe_username2}', {{Receiver}} = '{safe_username1}')"
            f")"
        )
        # We just need to know if at least one exists
        messages = tables["messages"].all(formula=formula, max_records=1)
        if messages:
            log.info(f"    -> Existing messages found between {username1} and {username2}.")
            return True
        log.info(f"    -> No existing messages found between {username1} and {username2}.")
        return False
    except Exception as e:
        log.error(f"Error checking existing messages between {username1} and {username2}: {e}")
        return False # Assume messages exist in case of error to avoid unnecessarily increasing probability

# --- Message Generation ---

def generate_ai_initiative_message(
    kinos_api_key: str,
    ai_username: str,
    target_username: str,
    context_data: Dict,
    triggering_activity_details: Optional[Dict] = None # New parameter
) -> Optional[str]:
    """Generates an AI-initiated message using the Kinos Engine API with enhanced context."""
    try:
        add_system_json = json.dumps(context_data)
        
        ai_display_name = context_data.get('ai_citizen_profile', {}).get('firstName', ai_username)
        target_display_name = context_data.get('target_citizen_profile', {}).get('firstName', target_username)

        kinos_prompt = (
            f"You are {ai_display_name}, an AI citizen of Venice. You are initiating a conversation with {target_display_name}.\n"
            f"IMPORTANT: Your message MUST be VERY SHORT, human-like, and conversational. "
            f"DO NOT use formal language, DO NOT write long paragraphs, DO NOT include any fluff or boilerplate. "
            f"Be direct, natural, and concise. Imagine you're sending a quick, informal message.\n\n"
            f"CRITICAL: Use the structured context provided in the 'addSystem' field (detailed below) to make your message RELEVANT to {target_display_name} and FOCUSED ON GAMEPLAY. "
            f"Your message should reflect your understanding of your relationship, recent events, and potential gameplay interactions with {target_display_name}.\n"
        )

        if triggering_activity_details:
            kinos_prompt += (
                f"\nRECENT OBSERVATION: You have just observed an activity involving {target_display_name}. "
                f"This is the primary reason for your message. Focus your message on this observation and its implications for gameplay.\n"
                f"Details of the observed activity: {json.dumps(triggering_activity_details, indent=2)}\n\n"
            )
        else:
            kinos_prompt += (
                f"\nYour message is a proactive initiative, not a direct reply. "
                f"Consider your goals, relationship with {target_display_name}, and recent events to craft a relevant opening.\n\n"
            )

        kinos_prompt += (
            f"Guide to 'addSystem' content (use this to make your message relevant and gameplay-focused):\n"
            f"- 'ai_citizen_profile': Your own detailed profile (status, wealth, etc.).\n"
            f"- 'target_citizen_profile': The profile of {target_display_name}.\n"
            f"- 'relationship_with_target': Your existing relationship status with {target_display_name}.\n"
            f"- 'recent_notifications_for_ai': Recent news/events you've received that might be relevant.\n"
            f"- 'recent_relevancies_ai_to_target': Why {target_display_name} (or things related to them) are specifically relevant to you. This is key for a relevant message!\n"
            f"- 'recent_problems_involving_ai_or_target': Recent issues involving you or {target_display_name} that could be part of your discussion.\n"
            f"- 'triggering_activity_details': (If present) The specific activity that prompted this message. Use this as the main focus.\n\n"
            f"Remember: Your message MUST be VERY SHORT, human-like, conversational, RELEVANT to {target_display_name} using the context, and FOCUSED ON GAMEPLAY. NO FLUFF. Just a natural, brief, and pertinent message.\n"
            f"Your message:"
        )
        
        url = f"https://api.kinos-engine.ai/v2/blueprints/{KINOS_BLUEPRINT_ID}/kins/{ai_username}/channels/{KINOS_CHANNEL_INITIATIVES}/messages"
        headers = {"Authorization": f"Bearer {kinos_api_key}", "Content-Type": "application/json"}
        payload = {"message": kinos_prompt, "addSystem": add_system_json}

        log.info(f"{LogColors.OKBLUE}Sending initiative message request to Kinos for {ai_username} to {target_username}...{LogColors.ENDC}")
        response = requests.post(url, headers=headers, json=payload, timeout=90)

        if response.status_code not in [200, 201]:
            log.error(f"{LogColors.FAIL}Kinos API error for {ai_username} to {target_username} (POST): {response.status_code} - {response.text[:500]}{LogColors.ENDC}")
            return None

        history_response = requests.get(url, headers=headers, timeout=30)
        if history_response.status_code != 200:
            log.error(f"{LogColors.FAIL}Kinos API error for {ai_username} to {target_username} (GET history): {history_response.status_code} - {history_response.text[:500]}{LogColors.ENDC}")
            return None
            
        messages_data = history_response.json()
        assistant_messages = [msg for msg in messages_data.get("messages", []) if msg.get("role") == "assistant"]
        if not assistant_messages:
            log.warning(f"{LogColors.WARNING}No assistant messages found in Kinos history for {ai_username} to {target_username}.{LogColors.ENDC}")
            return None
        
        assistant_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        latest_ai_response_content = assistant_messages[0].get("content")
        
        if not latest_ai_response_content:
            log.warning(f"{LogColors.WARNING}Latest assistant message for {ai_username} to {target_username} has no content.{LogColors.ENDC}")
            return None
            
        log.info(f"{LogColors.OKGREEN}Received Kinos response for {ai_username} to {target_username}. Length: {len(latest_ai_response_content)}{LogColors.ENDC}")
        return latest_ai_response_content

    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}Kinos API request error for {ai_username} to {target_username}: {e}{LogColors.ENDC}")
        return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error in generate_ai_initiative_message for {ai_username} to {target_username}: {e}{LogColors.ENDC}")
        return None

def send_message_api(sender_username: str, receiver_username: str, content: str, message_type: str = "message") -> bool:
    """
    Send a message using the API.
    NOTE: This function is duplicated in backend/ais/answertomessages.py.
    Consider moving to a shared utility module (e.g., backend/utils/message_utils.py)
    if more AI scripts need to send messages.
    """
    try:
        api_url = f"{BASE_URL}/api/messages/send"
        payload = {
            "sender": sender_username,
            "receiver": receiver_username,
            "content": content,
            "type": message_type
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        response_data = response.json()
        if response_data.get("success"):
            log.info(f"{LogColors.OKGREEN}Successfully sent message from {sender_username} to {receiver_username} via API.{LogColors.ENDC}")
            return True
        else:
            log.error(f"{LogColors.FAIL}API failed to send message from {sender_username} to {receiver_username}: {response_data.get('error')}{LogColors.ENDC}")
            return False
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}API request failed while sending message from {sender_username} to {receiver_username}: {e}{LogColors.ENDC}")
        return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error sending message via API from {sender_username} to {receiver_username}: {e}{LogColors.ENDC}")
        return False

def create_admin_notification(tables: Dict[str, Table], initiatives_summary: Dict[str, Any]) -> None:
    """
    Creates an admin notification with the AI initiative summary.
    NOTE: This function is duplicated in backend/ais/answertomessages.py and backend/ais/generatethoughts.py.
    Consider moving to a shared utility module (e.g., backend/utils/notification_utils.py)
    if more AI scripts need to create admin notifications.
    """
    try:
        now = datetime.now(VENICE_TIMEZONE).isoformat()
        
        content = f"AI Message Initiative Summary ({now.split('T')[0]}):\n\n"
        
        for ai_name, data in initiatives_summary.get("details", {}).items():
            status = "Sent" if data['messages_sent'] > 0 else "No messages"
            content += f"- {ai_name}: {data['messages_sent']} messages sent. Status: {status}\n"
        
        notification = {
            "Citizen": "ConsiglioDeiDieci",
            "Type": "ai_messaging_initiative",
            "Content": content,
            "CreatedAt": now,
            "Details": json.dumps(initiatives_summary)
        }
        
        tables["notifications"].create(notification)
        log.info(f"{LogColors.OKGREEN}Created admin notification with AI initiative summary.{LogColors.ENDC}")
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error creating admin notification: {str(e)}{LogColors.ENDC}")

# --- Main Processing Function ---

def process_ai_initiatives(dry_run: bool = False, specific_ai_username: Optional[str] = None, specific_target_username: Optional[str] = None, triggering_activity_details: Optional[Dict] = None):
    """Main function to process AI message initiatives."""
    log.info(f"{LogColors.HEADER}Starting AI Message Initiative Process (dry_run={dry_run})...{LogColors.ENDC}")
    
    tables = initialize_airtable()
    kinos_api_key = get_kinos_api_key()

    if not tables or not kinos_api_key:
        log.error(f"{LogColors.FAIL}Exiting due to missing Airtable connection or Kinos API key.{LogColors.ENDC}")
        return

    try:
        initiatives_summary = {
            "processed_ai_count": 0,
            "total_messages_sent": 0,
            "details": {}
        }

        if specific_ai_username and specific_target_username:
            # Targeted mode: specific AI initiates to specific target, potentially based on activity
            ai_username = specific_ai_username
            target_username = specific_target_username
            log.info(f"{LogColors.OKCYAN}--- Targeted Initiative: {ai_username} to {target_username} ---{LogColors.ENDC}")

            ai_citizen_record = tables["citizens"].first(formula=f"{{Username}}='{_escape_airtable_value(ai_username)}'", fields=["Username", "FirstName", "LastName", "SocialClass", "IsAI"])
            if not ai_citizen_record:
                log.error(f"{LogColors.FAIL}Targeted AI citizen {ai_username} not found.{LogColors.ENDC}")
                return
            
            target_citizen_data = _get_citizen_data_api(target_username)
            if not target_citizen_data:
                log.error(f"{LogColors.FAIL}Targeted citizen {target_username} not found.{LogColors.ENDC}")
                return

            initiatives_summary["processed_ai_count"] = 1
            initiatives_summary["details"][ai_username] = {"messages_sent": 0}

            # Gather context for Kinos
            ai_citizen_profile = _get_citizen_data_api(ai_username)
            relationship_data = _get_relationship_data_api(ai_username, target_username)
            notifications = _get_notifications_data_api(ai_username)
            relevancies = _get_relevancies_data_api(ai_username, target_username)
            problems = _get_problems_data_api(ai_username, target_username)

            context_data = {
                "ai_citizen_profile": ai_citizen_profile or {},
                "target_citizen_profile": target_citizen_data or {},
                "relationship_with_target": relationship_data or {},
                "recent_notifications_for_ai": notifications,
                "recent_relevancies_ai_to_target": relevancies,
                "recent_problems_involving_ai_or_target": problems
            }

            if dry_run:
                log.info(f"[DRY RUN] Would generate targeted initiative message from {ai_username} to {target_username}.")
                if triggering_activity_details:
                    log.info(f"[DRY RUN] Based on activity: {json.dumps(triggering_activity_details, indent=2)}")
                initiatives_summary["details"][ai_username]["messages_sent"] += 1
                initiatives_summary["total_messages_sent"] += 1
            else:
                message_content = generate_ai_initiative_message(
                    kinos_api_key,
                    ai_username,
                    target_username,
                    context_data,
                    triggering_activity_details=triggering_activity_details # Pass the activity details
                )
                
                if message_content:
                    sent_success = send_message_api(
                        sender_username=ai_username,
                        receiver_username=target_username,
                        content=message_content
                    )
                    if sent_success:
                        initiatives_summary["details"][ai_username]["messages_sent"] += 1
                        initiatives_summary["total_messages_sent"] += 1
                else:
                    log.warning(f"{LogColors.WARNING}No message generated by Kinos for targeted initiative from {ai_username} to {target_username}.{LogColors.ENDC}")
            
            time.sleep(1) # Pause after targeted initiative

        else:
            # Normal mode: probabilistic initiatives for all eligible AIs
            formula = "AND({IsAI}=1, {InVenice}=1, {SocialClass}!='Facchini')"
            ai_citizens = tables["citizens"].all(formula=formula, fields=["Username", "FirstName", "LastName", "SocialClass", "IsAI"])
            log.info(f"{LogColors.OKBLUE}Found {len(ai_citizens)} AI citizens for initiative processing.{LogColors.ENDC}")

            if not ai_citizens:
                log.info(f"{LogColors.OKBLUE}No eligible AI citizens found, exiting.{LogColors.ENDC}")
                return

            for ai_citizen_record in ai_citizens:
                ai_username = ai_citizen_record["fields"].get("Username")
                if not ai_username:
                    log.warning(f"{LogColors.WARNING}Skipping AI citizen record {ai_citizen_record.get('id')} due to missing Username.{LogColors.ENDC}")
                    continue

                log.info(f"{LogColors.OKCYAN}--- Processing AI Citizen: {ai_username} ---{LogColors.ENDC}")
                initiatives_summary["processed_ai_count"] += 1
                initiatives_summary["details"][ai_username] = {"messages_sent": 0}

                # Fetch relationships for the current AI
                relationships = tables["relationships"].all(
                    formula=f"OR({{Citizen1}}='{_escape_airtable_value(ai_username)}', {{Citizen2}}='{_escape_airtable_value(ai_username)}')"
                )
                
                # Sort relationships by combined score (Strength + Trust) descending
                relationships.sort(key=lambda x: (x["fields"].get("StrengthScore", 0) + x["fields"].get("TrustScore", 0)), reverse=True)

                if not relationships:
                    log.info(f"{LogColors.OKBLUE}No relationships found for {ai_username}, skipping initiative.{LogColors.ENDC}")
                    continue

                # Determine the highest combined score for normalization
                max_combined_score = 0
                if relationships:
                    max_combined_score = relationships[0]["fields"].get("StrengthScore", 0) + relationships[0]["fields"].get("TrustScore", 0)
                    if max_combined_score == 0: # Avoid division by zero
                        max_combined_score = 1 

                for rel_record in relationships:
                    rel_fields = rel_record["fields"]
                    target_username = rel_fields["Citizen2"] if rel_fields["Citizen1"] == ai_username else rel_fields["Citizen1"]
                    
                    # Skip if target is the AI itself (self-messages are handled by generatethoughts)
                    if target_username == ai_username:
                        continue

                    target_citizen_data = _get_citizen_data_api(target_username)
                    if not target_citizen_data:
                        log.warning(f"{LogColors.WARNING}Skipping initiative to {target_username} as their data could not be fetched.{LogColors.ENDC}")
                        continue

                    # Probability of initiating a message based on combined score
                    combined_score = rel_fields.get("StrengthScore", 0) + rel_fields.get("TrustScore", 0)
                    # Normalize score to a 0-1 range, then scale to a max probability (e.g., 0.25)
                    initiative_probability = (combined_score / max_combined_score) * 0.25

                    # Halve probability if target is also an AI
                    if target_citizen_data.get('fields', {}).get('IsAI', False):
                        initiative_probability /= 2
                        log.info(f"  Target {target_username} is an AI. Initiative probability halved to {initiative_probability:.2f}.")
                    
                    # Double probability if no existing messages
                    if not _check_existing_messages(tables, ai_username, target_username):
                        initiative_probability *= 2
                        log.info(f"  No existing messages. Initiative probability doubled to {initiative_probability:.2f}.")

                    # Cap probability at a reasonable maximum (e.g., 0.95)
                    initiative_probability = min(initiative_probability, 0.95)
                    log.info(f"  Relation with {target_username} (Score: {combined_score}). Final initiative probability: {initiative_probability:.2f}")

                    if random.random() < initiative_probability:
                        log.info(f"    -> {ai_username} initiating message to {target_username}!")
                        
                        # Gather context for Kinos
                        ai_citizen_profile = _get_citizen_data_api(ai_username)
                        notifications = _get_notifications_data_api(ai_username)
                        relevancies = _get_relevancies_data_api(ai_username, target_username)
                        problems = _get_problems_data_api(ai_username, target_username)

                        context_data = {
                            "ai_citizen_profile": ai_citizen_profile or {},
                            "target_citizen_profile": target_citizen_data or {},
                            "relationship_with_target": rel_fields,
                            "recent_notifications_for_ai": notifications,
                            "recent_relevancies_ai_to_target": relevancies,
                            "recent_problems_involving_ai_or_target": problems
                        }

                        if dry_run:
                            log.info(f"[DRY RUN] Would generate initiative message from {ai_username} to {target_username}.")
                            initiatives_summary["details"][ai_username]["messages_sent"] += 1
                            initiatives_summary["total_messages_sent"] += 1
                        else:
                            message_content = generate_ai_initiative_message(
                                kinos_api_key,
                                ai_username,
                                target_username,
                                context_data
                                # triggering_activity_details=None for general initiatives
                            )
                            
                            if message_content:
                                sent_success = send_message_api(
                                    sender_username=ai_username,
                                    receiver_username=target_username,
                                    content=message_content
                                )
                                if sent_success:
                                    initiatives_summary["details"][ai_username]["messages_sent"] += 1
                                    initiatives_summary["total_messages_sent"] += 1
                            else:
                                log.warning(f"{LogColors.WARNING}No message generated by Kinos for initiative from {ai_username} to {target_username}.{LogColors.ENDC}")
                        
                        time.sleep(0.2) # Small pause between messages to different targets
                
                time.sleep(0.5) # Pause between processing different relationships
            time.sleep(1) # Pause between processing different AI citizens

        log.info(f"{LogColors.HEADER}--- AI Message Initiative Summary ---{LogColors.ENDC}")
        log.info(f"AI Citizens Processed: {initiatives_summary['processed_ai_count']}")
        log.info(f"Total Messages Sent: {initiatives_summary['total_messages_sent']}")
        for ai_user, data in initiatives_summary["details"].items():
            log.info(f"- {ai_user}: {data['messages_sent']} messages sent.")

        if not dry_run and initiatives_summary["total_messages_sent"] > 0:
            create_admin_notification(tables, initiatives_summary)
        elif dry_run and initiatives_summary["total_messages_sent"] > 0:
            log.info(f"[DRY RUN] Would create admin notification with initiative summary: {initiatives_summary}")
        else:
            log.info(f"{LogColors.OKBLUE}No initiative messages were sent by any AI.{LogColors.ENDC}")

    except Exception as e:
        log.critical(f"{LogColors.FAIL}Critical error during AI message initiative process: {e}{LogColors.ENDC}")
        import traceback
        traceback.print_exc()
    finally:
        log.info(f"{LogColors.OKGREEN}AI Message Initiative Process finished.{LogColors.ENDC}")

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate strategic thoughts for citizens.")
    parser.add_argument(
        "--citizen",
        type=str,
        help="Process initiatives for a specific AI citizen by username."
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Specify a target citizen username for a direct initiative (requires --citizen)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without making Kinos API calls or writing to Airtable."
    )
    args = parser.parse_args()

    if (args.citizen and not args.target) or (not args.citizen and args.target):
        parser.error("--citizen and --target must be used together for targeted initiatives.")

    # Example of how triggering_activity_details would be passed for a targeted initiative
    # In a real scenario, this would be dynamically generated based on an observed activity.
    example_triggering_activity = {
        "activityId": "fetch_resource_marco_spices_123",
        "type": "fetch_resource",
        "citizen": "marco_venier",
        "fromBuilding": "merchant_galley_xyz",
        "toBuilding": "marco_warehouse_abc",
        "resources": [{"type": "spices", "amount": 500}],
        "notes": "Marco picked up 500 units of spices from a newly arrived merchant galley at the Dogana da Mar.",
        "createdAt": "2025-06-07T10:00:00Z"
    }

    process_ai_initiatives(
        dry_run=args.dry_run,
        specific_ai_username=args.citizen,
        specific_target_username=args.target,
        # Pass activity details ONLY if both --citizen and --target are provided
        triggering_activity_details=example_triggering_activity if args.citizen and args.target else None
    )

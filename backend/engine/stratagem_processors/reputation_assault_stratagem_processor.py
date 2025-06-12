"""
Stratagem Processor for "reputation_assault".

This processor:
1. Identifies citizens related to the target.
2. For each related citizen, generates a negative message using KinOS.
3. Sends the message from the executor to the related citizen.
4. Damages the relationship between the executor and the target.
"""

import logging
import json
import os
import requests
import pytz
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    get_citizen_record,
    clean_thought_content # For cleaning AI generated messages
)
from backend.engine.utils.relationship_helpers import (
    update_trust_score_for_activity,
    _rh_get_relationship_data, # Helper to get relationship details
    _rh_get_notifications_data_api, # Helper for context
    _rh_get_relevancies_data_api, # Helper for context
    _rh_get_problems_data_api, # Helper for context
    _get_kinos_api_key, # Helper for KinOS API key
    _generate_kinos_message_content, # Helper to call KinOS
    _store_message_via_api, # Helper to store message
    _rh_get_kinos_model_for_citizen # Helper to get model based on social class
)

log = logging.getLogger(__name__)

# KINOS_API_URL_BASE = "https://api.kinos-engine.ai/v2/blueprints/serenissima-ai/kins" # Defined in relationship_helpers
NEXT_JS_BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')

def _get_related_citizens(tables: Dict[str, Any], target_username: str) -> List[str]:
    """Fetches usernames of citizens who have a relationship with the target_username."""
    related_usernames: List[str] = []
    try:
        # Relationships where target_username is Citizen1
        formula1 = f"{{Citizen1}} = '{_escape_airtable_value(target_username)}'"
        rels1 = tables['relationships'].all(formula=formula1, fields=['Citizen2'])
        for rel in rels1:
            if rel['fields'].get('Citizen2'):
                related_usernames.append(rel['fields']['Citizen2'])

        # Relationships where target_username is Citizen2
        formula2 = f"{{Citizen2}} = '{_escape_airtable_value(target_username)}'"
        rels2 = tables['relationships'].all(formula=formula2, fields=['Citizen1'])
        for rel in rels2:
            if rel['fields'].get('Citizen1'):
                related_usernames.append(rel['fields']['Citizen1'])
        
        # Remove duplicates and the target themselves if they somehow appeared
        unique_related = list(set(related_usernames))
        if target_username in unique_related:
            unique_related.remove(target_username)
            
        log.info(f"{LogColors.PROCESS}Found {len(unique_related)} citizens related to {target_username}: {unique_related}{LogColors.ENDC}")
        return unique_related
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching related citizens for {target_username}: {e}{LogColors.ENDC}")
        return []

def _get_conversation_history(tables: Dict[str, Any], user1: str, user2: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches the last 'limit' messages between two users."""
    messages: List[Dict[str, Any]] = []
    try:
        # Ensure consistent order for querying
        u1_sorted, u2_sorted = sorted([user1, user2])
        
        # Construct channel name as it would be stored by Compagno/message API
        channel_name = f"{u1_sorted}_{u2_sorted}"
        
        # Query MESSAGES table for this channel
        # Assuming 'Channel' field exists and is populated correctly
        formula = f"{{Channel}} = '{_escape_airtable_value(channel_name)}'"
        
        # Fetch messages, sorted by CreatedAt descending to get the latest ones
        message_records = tables['messages'].all(
            formula=formula, 
            fields=['Sender', 'Receiver', 'Content', 'Type', 'CreatedAt'], 
            sort=[('-CreatedAt', 'desc')],
            max_records=limit 
        )
        
        if message_records:
            # Records are already sorted latest first, reverse to get chronological for prompt
            messages = [msg['fields'] for msg in reversed(message_records)] 
        
        log.info(f"{LogColors.PROCESS}Fetched {len(messages)} messages for conversation history between {user1} and {user2}.{LogColors.ENDC}")
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching conversation history between {user1} and {user2}: {e}{LogColors.ENDC}")
    return messages


def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None,
    building_type_defs: Optional[Dict[str, Any]] = None,
    api_base_url: Optional[str] = None # This is the Python engine's own base URL if needed
) -> bool:
    stratagem_fields = stratagem_record['fields']
    stratagem_id = stratagem_fields.get('StratagemId', stratagem_record['id'])
    executed_by_username = stratagem_fields.get('ExecutedBy')
    target_citizen_username = stratagem_fields.get('TargetCitizen')
    stratagem_notes = stratagem_fields.get('Notes', "") # Get notes for assaultAngle

    # Extract assaultAngle from notes if present
    assault_angle_from_notes: Optional[str] = None
    if "Angle: " in stratagem_notes:
        try:
            # Assumes "Angle: <text>\nOriginal notes..."
            angle_part = stratagem_notes.split("Angle: ", 1)[1]
            assault_angle_from_notes = angle_part.split("\n", 1)[0].strip()
        except IndexError:
            pass # Could not parse
    
    log_message = (
        f"{LogColors.STRATAGEM_PROCESSOR}Processing 'reputation_assault' stratagem {stratagem_id} "
        f"by {executed_by_username} against {target_citizen_username}."
    )
    if assault_angle_from_notes:
        log_message += f" Angle: '{assault_angle_from_notes}'."
    log.info(log_message + LogColors.ENDC)

    if not executed_by_username or not target_citizen_username:
        log.error(f"{LogColors.FAIL}Stratagem {stratagem_id} missing ExecutedBy or TargetCitizen. Cannot process.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'Missing ExecutedBy or TargetCitizen.'})
        return False

    kinos_api_key = _get_kinos_api_key()
    if not kinos_api_key:
        log.error(f"{LogColors.FAIL}KinOS API key not found. Cannot generate messages for stratagem {stratagem_id}.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'KinOS API key missing.'})
        return False

    # 1. Get data package for the target citizen
    target_data_package_response = requests.get(f"{NEXT_JS_BASE_URL}/api/get-data-package?citizenUsername={target_citizen_username}", timeout=30)
    if not target_data_package_response.ok:
        log.error(f"{LogColors.FAIL}Failed to fetch data package for target {target_citizen_username}. Status: {target_data_package_response.status_code}{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f'Failed to fetch data for target {target_citizen_username}.'})
        return False
    target_data_package = target_data_package_response.json().get('data', {})
    target_profile_for_kinos = target_data_package.get('citizen', {}) # Basic profile for KinOS

    # Get executor's profile (basic details for prompt context)
    executor_profile_record = get_citizen_record(tables, executed_by_username)
    executor_profile_for_kinos = executor_profile_record['fields'] if executor_profile_record else {}
    executor_display_name = executor_profile_for_kinos.get('FirstName', executed_by_username)
    target_display_name = target_profile_for_kinos.get('FirstName', target_citizen_username)


    # 2. Identify citizens related to the target
    related_citizens_usernames = _get_related_citizens(tables, target_citizen_username)
    if not related_citizens_usernames:
        log.info(f"{LogColors.PROCESS}Target {target_citizen_username} has no known relationships. Stratagem {stratagem_id} has no one to message.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Target has no relationships.'})
        return True # Stratagem considered executed as there's nothing to do.

    messages_sent_count = 0
    for related_citizen_username in related_citizens_usernames:
        if related_citizen_username == executed_by_username: # Don't message self
            continue

        log.info(f"{LogColors.PROCESS}Preparing to generate message for {related_citizen_username} about {target_citizen_username} (Stratagem {stratagem_id}).{LogColors.ENDC}")

        # 3. For each related citizen:
        #   - Fetch relationship details between related_citizen and target_citizen
        #   - Fetch conversation history between related_citizen and target_citizen
        relationship_target_related = _rh_get_relationship_data(tables, target_citizen_username, related_citizen_username)
        conversation_history_target_related = _get_conversation_history(tables, target_citizen_username, related_citizen_username)
        
        # Get related citizen's profile for context (e.g. their social class for model selection if needed)
        related_citizen_profile_record = get_citizen_record(tables, related_citizen_username)
        related_citizen_profile_for_kinos = related_citizen_profile_record['fields'] if related_citizen_profile_record else {}
        related_citizen_display_name = related_citizen_profile_for_kinos.get('FirstName', related_citizen_username)

        # Construct addSystem data for KinOS
        # The "kin" for this message generation is the executor.
        # The "channel" is with the related_citizen.
        # The context is about the target_citizen.
        add_system_data_for_message_gen = {
            "executing_citizen_profile": executor_profile_for_kinos,
            "target_citizen_profile_and_data": target_data_package, # Full data package of the one being smeared
            "related_citizen_profile": related_citizen_profile_for_kinos, # Profile of the message recipient
            "relationship_executor_with_related": _rh_get_relationship_data(tables, executed_by_username, related_citizen_username),
            "relationship_target_with_related": relationship_target_related,
            "conversation_history_target_with_related": conversation_history_target_related,
            "stratagem_details": {
                "type": "reputation_assault",
                "executor": executed_by_username,
                "target_of_assault": target_citizen_username,
                "message_recipient": related_citizen_username
            }
        }

        # Construct prompt for KinOS
        prompt_for_kinos = (
            f"You are {executor_display_name}. Your details are in `addSystem.executing_citizen_profile`. "
            f"You are executing a 'Reputation Assault' stratagem against {target_display_name} (details in `addSystem.target_citizen_profile_and_data`). "
            f"Your goal is to subtly damage {target_display_name}'s reputation with {related_citizen_display_name} (profile in `addSystem.related_citizen_profile`).\n"
            f"Consider your relationship with {related_citizen_display_name} (details in `addSystem.relationship_executor_with_related`).\n"
            f"Also consider {target_display_name}'s relationship with {related_citizen_display_name} (details in `addSystem.relationship_target_with_related`) "
            f"and their recent conversation history (in `addSystem.conversation_history_target_with_related`).\n"
            f"Craft a message TO {related_citizen_display_name} that subtly undermines {target_display_name}. "
            f"The message should sound natural for your persona and relationship with {related_citizen_display_name}. "
            f"It should not be overtly aggressive or obviously a smear tactic, but rather plant seeds of doubt or concern. "
            f"Refer to specific (but potentially misinterpreted or negatively framed) aspects from {target_display_name}'s data package if possible. "
        )
        
        if assault_angle_from_notes:
            prompt_for_kinos += (
                f"Focus your undermining message around the following angle or theme: '{assault_angle_from_notes}'. "
            )
        
        prompt_for_kinos += (
            f"Keep the message concise and conversational."
        )
        
        # Determine model for the executor (KinOS persona)
        executor_social_class = executor_profile_for_kinos.get("SocialClass")
        model_for_executor = _rh_get_kinos_model_for_citizen(executor_social_class)

        # Generate message content using KinOS
        # The kin_username is the executor, channel_username is the related_citizen
        generated_message_content = _generate_kinos_message_content(
            kin_username=executed_by_username,
            channel_username=related_citizen_username, # KinOS channel is between executor and recipient
            prompt=prompt_for_kinos,
            kinos_api_key=kinos_api_key,
            kinos_model_override=model_for_executor,
            add_system_data=add_system_data_for_message_gen
        )

        if generated_message_content:
            cleaned_message = clean_thought_content(tables, generated_message_content)
            log.info(f"{LogColors.PROCESS}Generated message from {executed_by_username} to {related_citizen_username} (re: {target_citizen_username}): '{cleaned_message[:100]}...' (Original: '{generated_message_content[:100]}...'){LogColors.ENDC}")
            
            # Send the message
            # The channel for storing the message is between executor and related_citizen
            dialogue_channel_name = "_".join(sorted([executed_by_username, related_citizen_username]))
            if _store_message_via_api(tables, executed_by_username, related_citizen_username, cleaned_message, dialogue_channel_name):
                messages_sent_count += 1
            else:
                log.warning(f"{LogColors.WARNING}Failed to store generated message to {related_citizen_username} for stratagem {stratagem_id}.{LogColors.ENDC}")
        else:
            log.warning(f"{LogColors.WARNING}Failed to generate message content for {related_citizen_username} (re: {target_citizen_username}) for stratagem {stratagem_id}.{LogColors.ENDC}")

    # 4. Damage relationship between executor and target
    trust_change = -50.0 # Significant negative impact
    update_trust_score_for_activity(
        tables,
        executed_by_username,
        target_citizen_username,
        trust_change,
        activity_type_for_notes=f"stratagem_reputation_assault_on_{target_citizen_username}",
        success=False, # From target's perspective, this is a negative action
        notes_detail=f"executed_by_{executed_by_username}",
        activity_record_for_kinos=stratagem_record # Pass the stratagem record for context
    )
    log.info(f"{LogColors.PROCESS}Trust score between {executed_by_username} and {target_citizen_username} impacted by {trust_change} due to stratagem {stratagem_id}.{LogColors.ENDC}")

    # 5. Update stratagem status
    final_notes = f"Reputation assault executed. {messages_sent_count} messages sent to relations of {target_citizen_username}."
    if not stratagem_fields.get('ExecutedAt'):
        tables['stratagems'].update(stratagem_record['id'], {'ExecutedAt': datetime.now(pytz.utc).isoformat(), 'Status': 'executed', 'Notes': final_notes})
    else:
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': final_notes})
    
    log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} (reputation_assault) marked as executed. {final_notes}{LogColors.ENDC}")
    return True

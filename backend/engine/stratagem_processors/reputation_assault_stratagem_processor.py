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
# Import the new analysis helper
from backend.engine.utils.conversation_helper import _call_kinos_analysis_api


log = logging.getLogger(__name__)

# KINOS_API_URL_BASE = "https://api.kinos-engine.ai/v2/blueprints/serenissima-ai/kins" # Defined in relationship_helpers
NEXT_JS_BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')

def _get_related_citizens(tables: Dict[str, Any], target_username: str, limit: int = 50) -> List[str]:
    """
    Fetches usernames of citizens who have a relationship with the target_username,
    ordered by StrengthScore descending, up to a specified limit.
    """
    related_usernames_set: set[str] = set()
    try:
        escaped_target_username = _escape_airtable_value(target_username)
        formula = f"OR({{Citizen1}}='{escaped_target_username}', {{Citizen2}}='{escaped_target_username}')"
        
        # Fetch relationships, sorted by StrengthScore descending
        # Ensure StrengthScore is a number in Airtable for correct sorting.
        # Pyairtable handles missing fields by typically sorting them last.
        relationships = tables['relationships'].all(
            formula=formula,
            fields=['Citizen1', 'Citizen2', 'StrengthScore'], # StrengthScore needed for sorting
            sort=[('-StrengthScore', 'desc')],
            max_records=limit * 2 # Fetch a bit more to account for filtering out target_username and ensuring enough unique results
        )
        
        log.info(f"{LogColors.PROCESS}Fetched {len(relationships)} raw relationship records for {target_username} (sorted by StrengthScore desc).")

        count = 0
        for rel in relationships:
            if count >= limit:
                break

            c1 = rel['fields'].get('Citizen1')
            c2 = rel['fields'].get('Citizen2')
            
            other_citizen = None
            if c1 == target_username:
                other_citizen = c2
            elif c2 == target_username:
                other_citizen = c1
            
            if other_citizen and other_citizen != target_username: # Ensure it's not the target themselves
                if other_citizen not in related_usernames_set:
                    related_usernames_set.add(other_citizen)
                    count += 1
        
        unique_related_list = list(related_usernames_set)
        # The list is already effectively sorted by StrengthScore due to the query order and set insertion order (for unique elements)
        # If strict top N by score is needed even after deduplication, a re-sort might be needed if many duplicates exist among top scores.
        # However, for this use case, this should be sufficient.

        log.info(f"{LogColors.PROCESS}Found {len(unique_related_list)} unique citizens related to {target_username} (top {limit} by StrengthScore): {unique_related_list}{LogColors.ENDC}")
        return unique_related_list
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching related citizens for {target_username}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
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

    # 1. Fetch data packages for executor and target
    log.info(f"{LogColors.PROCESS}Fetching data package for executor {executed_by_username}...{LogColors.ENDC}")
    executor_dp_response = requests.get(f"{NEXT_JS_BASE_URL}/api/get-data-package?citizenUsername={executed_by_username}", timeout=30)
    if not executor_dp_response.ok:
        log.error(f"{LogColors.FAIL}Failed to fetch data package for executor {executed_by_username}. Status: {executor_dp_response.status_code}{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f'Failed to fetch data for executor {executed_by_username}.'})
        return False
    executor_data_package = executor_dp_response.json().get('data', {})
    executor_profile_for_kinos = executor_data_package.get('citizen', {})
    executor_display_name = executor_profile_for_kinos.get('FirstName', executed_by_username)
    executor_social_class = executor_profile_for_kinos.get("SocialClass")
    model_for_executor = _rh_get_kinos_model_for_citizen(executor_social_class) # Model for both KinOS calls

    log.info(f"{LogColors.PROCESS}Fetching data package for target {target_citizen_username}...{LogColors.ENDC}")
    target_dp_response = requests.get(f"{NEXT_JS_BASE_URL}/api/get-data-package?citizenUsername={target_citizen_username}", timeout=30)
    if not target_dp_response.ok:
        log.error(f"{LogColors.FAIL}Failed to fetch data package for target {target_citizen_username}. Status: {target_dp_response.status_code}{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f'Failed to fetch data for target {target_citizen_username}.'})
        return False
    target_data_package = target_dp_response.json().get('data', {})
    target_profile_for_kinos = target_data_package.get('citizen', {})
    target_display_name = target_profile_for_kinos.get('FirstName', target_citizen_username)

    # 2. Generate Core Attack Narrative (KinOS Call 1: Executor to Self)
    log.info(f"{LogColors.PROCESS}Generating core attack narrative for {executed_by_username} against {target_citizen_username}...{LogColors.ENDC}")
    add_system_for_narrative_gen = {
        "executor_profile_and_data": executor_data_package,
        "target_profile_and_data": target_data_package,
        "assault_angle_directive": assault_angle_from_notes or "any effective angle"
    }
    prompt_for_narrative_gen = (
        f"You are {executor_display_name}. You are planning a reputation assault against {target_display_name}. "
        f"Your goal is to craft a compelling narrative or set of talking points that will damage their reputation. "
        f"Use the provided `assault_angle_directive` ('{assault_angle_from_notes or 'any effective angle'}') as the core theme. "
        f"You have access to your own data (`executor_profile_and_data`) and the target's data (`target_profile_and_data`). "
        f"You can use factual information, misinterpretations, or even plausible fabrications to build your case. "
        f"Your output should be ONLY the core attack narrative/talking points you will use. Be strategic and persuasive. This text will be used by you in subsequent messages."
    )
    
    core_attack_narrative = _generate_kinos_message_content(
        kin_username=executed_by_username,
        channel_username=executed_by_username, # Self-chat
        prompt=prompt_for_narrative_gen,
        kinos_api_key=kinos_api_key,
        kinos_model_override=model_for_executor,
        add_system_data=add_system_for_narrative_gen,
        tables=tables # Pass tables for summarization if local model
    )

    if not core_attack_narrative:
        log.error(f"{LogColors.FAIL}Failed to generate core attack narrative for stratagem {stratagem_id}. Aborting.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'Failed to generate core attack narrative.'})
        return False
    
    cleaned_core_attack_narrative = clean_thought_content(tables, core_attack_narrative)
    log.info(f"{LogColors.PROCESS}Generated Core Attack Narrative (cleaned, first 100 chars): '{cleaned_core_attack_narrative[:100]}...'{LogColors.ENDC}")
    
    # Store this narrative as a self-message (thought) for the executor
    _store_message_via_api(
        tables, 
        executed_by_username, 
        executed_by_username, 
        f"Strategizing Reputation Assault against {target_citizen_username} (Angle: {assault_angle_from_notes or 'N/A'}):\n\n{cleaned_core_attack_narrative}", 
        f"stratagem_plan_{stratagem_id}",
        message_type="stratagem_plan_thought" # Specific message type
    )

    # 3. Identify citizens related to the target
    related_citizens_usernames = _get_related_citizens(tables, target_citizen_username)
    if not related_citizens_usernames:
        log.info(f"{LogColors.PROCESS}Target {target_citizen_username} has no known relationships. Stratagem {stratagem_id} has no one to message.{LogColors.ENDC}")
        # Stratagem still considered "processed" as the core damage to executor-target relationship will occur.
        # No messages sent, but the intent was there.
    
    messages_sent_count = 0
    for related_citizen_username in related_citizens_usernames:
        if related_citizen_username == executed_by_username: # Don't message self with smear
            continue

        log.info(f"{LogColors.PROCESS}Preparing to generate personalized message for {related_citizen_username} about {target_citizen_username} (Stratagem {stratagem_id}).{LogColors.ENDC}")

        # Fetch related citizen's data package
        related_citizen_dp_response = requests.get(f"{NEXT_JS_BASE_URL}/api/get-data-package?citizenUsername={related_citizen_username}", timeout=30)
        if not related_citizen_dp_response.ok:
            log.warning(f"{LogColors.WARNING}Failed to fetch data package for related citizen {related_citizen_username}. Skipping message to them.{LogColors.ENDC}")
            continue
        related_citizen_data_package = related_citizen_dp_response.json().get('data', {})
        related_citizen_profile_for_kinos = related_citizen_data_package.get('citizen', {})
        related_citizen_display_name = related_citizen_profile_for_kinos.get('FirstName', related_citizen_username)
        
        # Construct addSystem data for KinOS (Call 2: Executor to RelatedCitizen)
        add_system_for_smear_message = {
            "executor_profile": executor_profile_for_kinos, # Basic profile of executor
            "recipient_profile_and_data": related_citizen_data_package, # Full data package of recipient
            "core_attack_narrative_from_executor": cleaned_core_attack_narrative,
            "original_target_profile": target_profile_for_kinos, # Basic profile of the one being smeared
            "relationship_executor_with_recipient": _rh_get_relationship_data(tables, executed_by_username, related_citizen_username),
            "relationship_target_with_recipient": _rh_get_relationship_data(tables, target_citizen_username, related_citizen_username),
            "assault_angle_reminder": assault_angle_from_notes or "any effective angle"
        }
        
        prompt_for_smear_message = (
            f"You are {executor_display_name}. You are speaking to {related_citizen_display_name}. "
            f"Your goal is to subtly damage {target_display_name}'s reputation with {related_citizen_display_name}. "
            f"Use the `core_attack_narrative_from_executor` you previously prepared, focusing on the `assault_angle_reminder` ('{assault_angle_from_notes or 'any effective angle'}'). "
            f"Consider your relationship with {related_citizen_display_name} (see `relationship_executor_with_recipient`) and {target_display_name}'s relationship with {related_citizen_display_name} (see `relationship_target_with_recipient`). "
            f"Use the `recipient_profile_and_data` to personalize your message to {related_citizen_display_name}. "
            f"Your message should be conversational and not overtly aggressive. Plant seeds of doubt or concern. "
            f"Your output is ONLY the message TO {related_citizen_display_name}."
        )

        generated_smear_message = _generate_kinos_message_content(
            kin_username=executed_by_username,
            channel_username=related_citizen_username,
            prompt=prompt_for_smear_message,
            kinos_api_key=kinos_api_key,
            kinos_model_override=model_for_executor, # Same model as executor
            add_system_data=add_system_for_smear_message,
            tables=tables # Pass tables for summarization if local model
        )

        if generated_smear_message:
            cleaned_smear_message = clean_thought_content(tables, generated_smear_message)
            log.info(f"{LogColors.PROCESS}Generated smear message from {executed_by_username} to {related_citizen_username} (re: {target_citizen_username}): '{cleaned_smear_message[:100]}...' (Original: '{generated_smear_message[:100]}...'){LogColors.ENDC}")
            
            dialogue_channel_name = "_".join(sorted([executed_by_username, related_citizen_username]))
            if _store_message_via_api(
                tables, 
                executed_by_username, 
                related_citizen_username, 
                cleaned_smear_message, 
                dialogue_channel_name,
                message_type="stratagem_smear_message" # Specific message type
            ):
                messages_sent_count += 1
                
                # --- Trust Impact Analysis via KinOS ---
                log.info(f"{LogColors.PROCESS}Attempting trust impact analysis for {related_citizen_username} regarding message about {target_citizen_username} from {executed_by_username}.{LogColors.ENDC}")
                
                # related_citizen_data_package is already fetched and available
                # related_citizen_profile_for_kinos is also available
                
                model_for_related_citizen = _rh_get_kinos_model_for_citizen(related_citizen_profile_for_kinos.get("SocialClass"))
                
                analysis_prompt = (
                    f"You are {related_citizen_display_name}. You just received the following message from {executor_display_name} regarding {target_display_name}: '{cleaned_smear_message}'. "
                    f"Considering your personality, your relationship with both individuals ({executor_display_name} and {target_display_name}), and all information in your data package (provided in addSystem), "
                    f"how does this message impact your trust in {target_display_name}? "
                    f"Please respond ONLY with a JSON object in the format: {{\"trustChange\": <value>}}, where <value> is an integer between -25 (strong negative impact, e.g., you believe the smear) and +5 (slight positive impact or no negative impact, e.g., you dismiss the smear or it backfires on the sender)."
                )
                
                analysis_response_str = _call_kinos_analysis_api(
                    kinos_api_key,
                    related_citizen_username, # The Kin performing the analysis
                    analysis_prompt,
                    related_citizen_data_package, # Their own data package as context
                    model_for_related_citizen
                )
                
                trust_change_value = -5.0 # Default impact if analysis fails or provides invalid data

                if analysis_response_str:
                    try:
                        analysis_json = json.loads(analysis_response_str)
                        extracted_change = analysis_json.get("trustChange")
                        if isinstance(extracted_change, (int, float)):
                            trust_change_value = float(max(-25.0, min(5.0, extracted_change))) # Clamp value
                            log.info(f"{LogColors.PROCESS}Trust impact analysis for {related_citizen_username} on {target_citizen_username}: AI assessed change = {trust_change_value} (original from AI: {extracted_change}){LogColors.ENDC}")
                        else:
                            log.warning(f"{LogColors.WARNING}Trust impact analysis for {related_citizen_username}: 'trustChange' key missing or not a number in JSON response: {analysis_response_str}. Using default impact: {trust_change_value}{LogColors.ENDC}")
                    except json.JSONDecodeError:
                        log.warning(f"{LogColors.WARNING}Trust impact analysis for {related_citizen_username}: Failed to parse JSON response: '{analysis_response_str[:100]}...'. Using default impact: {trust_change_value}{LogColors.ENDC}")
                else:
                    log.warning(f"{LogColors.WARNING}Trust impact analysis for {related_citizen_username}: No response from KinOS analysis API. Using default impact: {trust_change_value}{LogColors.ENDC}")

                # Update trust score between related_citizen and target_citizen
                update_trust_score_for_activity(
                    tables,
                    related_citizen_username, # Citizen1 (whose trust is affected)
                    target_citizen_username,  # Citizen2 (the target of the smear)
                    trust_change_value,       # The impact amount
                    activity_type_for_notes=f"reputation_assault_trust_impact",
                    success=True, # The assessment itself was "successful" in terms of process
                    notes_detail=f"AI_assessed_impact_on_{related_citizen_username}_by_smear_from_{executed_by_username}_re_{target_citizen_username}. AI_raw_resp: {analysis_response_str[:50] if analysis_response_str else 'N/A'}",
                    activity_record_for_kinos=None # IMPORTANT: Pass None to prevent recursive dialogue
                )
                log.info(f"{LogColors.PROCESS}Trust score between {related_citizen_username} and {target_citizen_username} updated by {trust_change_value} based on AI analysis.{LogColors.ENDC}")
                # --- End Trust Impact Analysis ---
            else:
                log.warning(f"{LogColors.WARNING}Failed to store generated smear message to {related_citizen_username} for stratagem {stratagem_id}.{LogColors.ENDC}")
        else:
            log.warning(f"{LogColors.WARNING}Failed to generate smear message content for {related_citizen_username} (re: {target_citizen_username}) for stratagem {stratagem_id}.{LogColors.ENDC}")

    # 4. Damage relationship between executor and target (regardless of messages sent)
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

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
# Import for direct KinOS API calls
import requests

# Define the KinOS API call function at the module level
def _make_direct_kinos_channel_call(
    kin_username: str,
    channel_username: str,
    prompt: str,
    kinos_api_key: str,
    kinos_model_override: Optional[str] = None,
    add_system_data: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Makes a direct call to the KinOS API for a specific channel.
    Returns the response text or None if the call fails.
    """
    try:
        # Base URL for KinOS API
        kinos_api_url_base = "https://api.kinos-engine.ai/v2/blueprints/serenissima-ai/kins"
        
        # Construct the full URL for the channel messages endpoint
        url = f"{kinos_api_url_base}/{kin_username}/channels/{channel_username}/messages"
        
        # Prepare headers with API key
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {kinos_api_key}"
        }
        
        # Prepare payload
        payload = {
            "prompt": prompt,
            "model": kinos_model_override or "claude-3-7-sonnet-latest", # Default model if none specified
            "min_files": 0,
            "max_files": 0 
        }
        
        # Add system data if provided
        if add_system_data:
            # Create a serializable version of add_system_data
            serializable_system_data = {}
            for key, value in add_system_data.items():
                if hasattr(value, 'text'):  # If it's a requests.Response object
                    serializable_system_data[key] = value.text
                else:
                    serializable_system_data[key] = value
            
            payload["addSystem"] = serializable_system_data
        
        log.info(f"{LogColors.PROCESS}Making direct KinOS API call for {kin_username} to channel {channel_username} with model: {payload.get('model')}{LogColors.ENDC}")
        
        # Make the API call
        response = requests.post(url, headers=headers, json=payload, timeout=300)  # 5 minutes timeout for AI responses
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse response
        response_data = response.json()
        
        # Log response details for debugging
        log.info(f"{LogColors.PROCESS}KinOS API response status code: {response.status_code}{LogColors.ENDC}")
        log.info(f"{LogColors.PROCESS}KinOS API response data: {json.dumps(response_data, indent=2)}{LogColors.ENDC}")
        
        # Check for content in the response (new KinOS API format)
        if "content" in response_data:
            log.info(f"{LogColors.OKGREEN}Successfully received KinOS response for {kin_username} to channel {channel_username}{LogColors.ENDC}")
            return response_data["content"]
        # Check for older API format with success and response fields
        elif response_data.get("success") and "response" in response_data:
            log.info(f"{LogColors.OKGREEN}Successfully received KinOS response for {kin_username} to channel {channel_username} (legacy format){LogColors.ENDC}")
            return response_data["response"]
        else:
            log.error(f"{LogColors.FAIL}KinOS API call succeeded but returned error: {response_data.get('error', 'Unknown error')}{LogColors.ENDC}")
            return None
            
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}RequestException in KinOS API call: {e}{LogColors.ENDC}")
        return None
    except json.JSONDecodeError as e:
        log.error(f"{LogColors.FAIL}JSONDecodeError in KinOS API call: {e}. Response text: {response.text[:200] if 'response' in locals() and hasattr(response, 'text') else 'N/A'}{LogColors.ENDC}")
        return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Unexpected error in KinOS API call: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return None
from backend.engine.utils.relationship_helpers import (
    _rh_get_relationship_data, # Helper to get relationship details
    _rh_get_notifications_data_api, # Helper for context
    _rh_get_relevancies_data_api, # Helper for context
    _rh_get_problems_data_api, # Helper for context
    _get_kinos_api_key, # Helper for KinOS API key
    _store_message_via_api, # Helper to store message
    _rh_get_kinos_model_for_citizen # Helper to get model based on social class
)
# _call_kinos_analysis_api is no longer used here, trust impact is handled by conversation_helper

log = logging.getLogger(__name__)


# KINOS_API_URL_BASE = "https://api.kinos-engine.ai/v2/blueprints/serenissima-ai/kins" # Defined in relationship_helpers
NEXT_JS_BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')

def _get_related_citizens(tables: Dict[str, Any], target_username: str, limit: int = 50) -> List[str]:
    """
    Fetches usernames of citizens who have a relationship with the target_username,
    ordered by StrengthScore descending, up to a specified limit.
    """
    related_usernames_set: set[str] = set()
    
    # Utiliser l'API en première intention
    try:
        import requests
        api_url = f"{NEXT_JS_BASE_URL}/api/relationships?targetCitizen={target_username}"
        log.info(f"{LogColors.PROCESS}Fetching relationships via API: {api_url}{LogColors.ENDC}")
        response = requests.get(api_url, timeout=60)
        if response.ok:
            relationships_data = response.json()
            if relationships_data.get('success') and 'relationships' in relationships_data:
                log.info(f"{LogColors.OKGREEN}Successfully fetched {len(relationships_data['relationships'])} relationships via API{LogColors.ENDC}")
                # Extraire les usernames des citoyens liés
                for rel in relationships_data['relationships']:
                    other_citizen = None
                    if rel.get('citizen1') == target_username:
                        other_citizen = rel.get('citizen2')
                    elif rel.get('citizen2') == target_username:
                        other_citizen = rel.get('citizen1')
                    
                    if other_citizen and other_citizen != target_username:
                        related_usernames_set.add(other_citizen)
                        if len(related_usernames_set) >= limit:
                            break
                return list(related_usernames_set)
            else:
                log.warning(f"{LogColors.WARNING}API returned success=false or no relationships{LogColors.ENDC}")
        else:
            log.warning(f"{LogColors.WARNING}Failed to fetch relationships via API: {response.status_code}. Falling back to Airtable.{LogColors.ENDC}")
    except Exception as e_api:
        log.error(f"{LogColors.FAIL}Error fetching relationships via API: {e_api}. Falling back to Airtable.{LogColors.ENDC}")
    
    # Fallback: Utiliser Airtable si l'API échoue
    try:
        # Vérifier si 'relationships' est directement dans tables ou s'il faut l'accéder différemment
        relationships_table = None
        
        if 'relationships' in tables:
            relationships_table = tables['relationships']
        elif hasattr(tables, 'get') and callable(tables.get):
            # Si tables est un dictionnaire avec une méthode get()
            relationships_table = tables.get('relationships')
        
        if not relationships_table:
            log.error(f"{LogColors.FAIL}Table 'relationships' not found in tables dictionary. Available tables: {list(tables.keys()) if isinstance(tables, dict) else 'Not a dict'}{LogColors.ENDC}")
            return []
            
        escaped_target_username = _escape_airtable_value(target_username)
        formula = f"OR({{Citizen1}}='{escaped_target_username}', {{Citizen2}}='{escaped_target_username}')"
        
        # Fetch relationships, sorted by StrengthScore descending
        # Ensure StrengthScore is a number in Airtable for correct sorting.
        # Pyairtable handles missing fields by typically sorting them last.
        relationships = relationships_table.all(
            formula=formula,
            fields=['Citizen1', 'Citizen2', 'StrengthScore'], # StrengthScore needed for sorting
            sort=['-StrengthScore'], # Use string format for descending sort
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
    stratagem_notes = stratagem_fields.get('Notes', "")

    # Extract assaultAngle and kinosModelOverride from notes
    assault_angle_from_notes: Optional[str] = None
    kinos_model_override_from_notes: Optional[str] = None

    notes_lines = stratagem_notes.split('\n')
    remaining_notes_for_log = []
    for line in notes_lines:
        if line.startswith("Angle: "):
            assault_angle_from_notes = line.split("Angle: ", 1)[1].strip()
        elif line.startswith("KinosModelOverride: "):
            kinos_model_override_from_notes = line.split("KinosModelOverride: ", 1)[1].strip()
        else:
            remaining_notes_for_log.append(line)
    
    log_message_parts = [
        f"{LogColors.STRATAGEM_PROCESSOR}Processing 'reputation_assault' stratagem {stratagem_id} ",
        f"by {executed_by_username} against {target_citizen_username}."
    ]
    if assault_angle_from_notes:
        log_message_parts.append(f" Angle: '{assault_angle_from_notes}'.")
    if kinos_model_override_from_notes:
        log_message_parts.append(f" KinOS Model Override: '{kinos_model_override_from_notes}'.")
    
    log.info("".join(log_message_parts) + LogColors.ENDC)

    if not executed_by_username or not target_citizen_username:
        log.error(f"{LogColors.FAIL}Stratagem {stratagem_id} missing ExecutedBy or TargetCitizen. Cannot process.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'Missing ExecutedBy or TargetCitizen.'})
        return False

    kinos_api_key = _get_kinos_api_key()
    if not kinos_api_key:
        log.error(f"{LogColors.FAIL}KinOS API key not found. Cannot generate messages for stratagem {stratagem_id}.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'KinOS API key missing.'})
        return False

    # 1. Fetch ledgers for executor and target
    log.info(f"{LogColors.PROCESS}Fetching ledger for executor {executed_by_username}...{LogColors.ENDC}")
    executor_dp_response = requests.get(f"{NEXT_JS_BASE_URL}/api/get-ledger?citizenUsername={executed_by_username}", timeout=90)
    if not executor_dp_response.ok:
        log.error(f"{LogColors.FAIL}Failed to fetch ledger for executor {executed_by_username}. Status: {executor_dp_response.status_code}, Response: {executor_dp_response.text[:200]}{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f'Failed to fetch data for executor {executed_by_username}.'})
        return False
    
    executor_ledger = executor_dp_response

    executor_display_name = executed_by_username
    
    log.info(f"{LogColors.PROCESS}Fetching ledger for target {target_citizen_username}...{LogColors.ENDC}")
    target_dp_response = requests.get(f"{NEXT_JS_BASE_URL}/api/get-ledger?citizenUsername={target_citizen_username}", timeout=90)

    target_ledger = target_dp_response

    target_display_name = target_citizen_username

    # 2. Generate Core Attack Narrative (KinOS Call 1: Executor to Self)
    log.info(f"{LogColors.PROCESS}Generating core attack narrative for {executed_by_username} against {target_citizen_username}...{LogColors.ENDC}")
    add_system_for_narrative_gen = {
        "assault_angle_directive": assault_angle_from_notes or "any effective angle",
        "target_profile_and_data": target_ledger
    }
    prompt_for_narrative_gen = (
        f"You are {executor_display_name}. You are planning a reputation assault against {target_display_name}. "
        f"Your goal is to craft a compelling narrative or set of talking points that will damage their reputation. "
        f"Use the provided `assault_angle_directive` ('{assault_angle_from_notes or 'any effective angle'}') as the core theme. "
        f"You have access to the target's data (`target_profile_and_data`). "
        f"You can use factual information, misinterpretations, or even plausible fabrications to build your case. "
        f"Your output should be ONLY the core attack narrative/talking points you will use. Be strategic and persuasive. This text will be used by you in subsequent messages."
    )
    
    core_attack_narrative = _make_direct_kinos_channel_call(
        kin_username=executed_by_username,
        channel_username=target_citizen_username, # Self-chat
        prompt=prompt_for_narrative_gen,
        kinos_api_key=kinos_api_key,
        kinos_model_override="claude-3-7-sonnet-latest" or "local",
        add_system_data=add_system_for_narrative_gen
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
        f"target_citizen_username",
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

        log.info(f"{LogColors.PROCESS}Preparing to generate and send message to {related_citizen_username} about {target_citizen_username} (Stratagem {stratagem_id}).{LogColors.ENDC}")

        # Fetch related citizen's ledger
        related_citizen_dp_response = requests.get(f"{NEXT_JS_BASE_URL}/api/get-ledger?citizenUsername={related_citizen_username}", timeout=90)
        if not related_citizen_dp_response.ok:
            log.warning(f"{LogColors.WARNING}Failed to fetch ledger for related citizen {related_citizen_username}. Status: {related_citizen_dp_response.status_code}, Response: {related_citizen_dp_response.text[:200]}. Skipping message to them.{LogColors.ENDC}")
            continue
        
        try:
            related_citizen_ledger = related_citizen_dp_response.json()
            if not related_citizen_ledger:
                log.warning(f"{LogColors.WARNING}Empty ledger for related citizen {related_citizen_username}. Skipping message to them.{LogColors.ENDC}")
                continue
        except (json.JSONDecodeError, ValueError) as e_json:
            log.warning(f"{LogColors.WARNING}Failed to parse JSON ledger for related citizen {related_citizen_username}: {e_json}. Response text: {related_citizen_dp_response.text[:200]}. Skipping message to them.{LogColors.ENDC}")
            continue
        related_citizen_profile_for_kinos = related_citizen_ledger.get('citizen', {})
        if not related_citizen_profile_for_kinos: # Ensure it's a dict
            log.warning(f"{LogColors.WARNING}Related citizen profile missing in ledger for {related_citizen_username}. Proceeding with empty profile for this interaction.{LogColors.ENDC}")
            related_citizen_profile_for_kinos = {}
        related_citizen_display_name = related_citizen_profile_for_kinos.get('FirstName', related_citizen_username)
        
        # Get the appropriate KinOS model for the executor based on social class
        model_for_executor = _rh_get_kinos_model_for_citizen(tables, executed_by_username) or kinos_model_override_from_notes or "claude-3-7-sonnet-latest"
        
        # Au lieu de générer un message spécifique maintenant, nous allons préparer les données
        # qui seront transmises via addMessage pour que KinOS génère le message au moment de la livraison
        log.info(f"{LogColors.PROCESS}Préparation des données pour message futur de {executed_by_username} à {related_citizen_username}...{LogColors.ENDC}")
            
        # Nous utiliserons un message générique qui sera remplacé par KinOS au moment de la livraison
        cleaned_specific_message = f"Je dois vous parler de {target_display_name}..."
        log.info(f"{LogColors.PROCESS}Message générique préparé pour {related_citizen_username}, sera personnalisé par KinOS lors de la livraison{LogColors.ENDC}")

        # --- Create send_message activity directly using the send_message_creator ---
        if not api_base_url:
            log.error(f"{LogColors.FAIL}Python engine API base URL not provided. Cannot create send_message activity for stratagem {stratagem_id}.{LogColors.ENDC}")
            continue

        # Import the send_message_creator directly
        from backend.engine.activity_creators.send_message_creator import try_create as try_create_send_message
        
        # Get the executor's citizen record
        executor_citizen_record = get_citizen_record(tables, executed_by_username)
        if not executor_citizen_record:
            log.error(f"{LogColors.FAIL}Could not find citizen record for executor {executed_by_username}. Skipping message to {related_citizen_username}.{LogColors.ENDC}")
            continue
            
        # Prepare activity parameters similar to what the API would expect
        activity_details = {
            "receiverUsername": related_citizen_username,
            "content": cleaned_specific_message,
            "messageType": "stratagem_smear_delivery", # New type to distinguish
            "notes": { # Optional, but good for tracking
                "stratagemId": stratagem_id,
                "originalTarget": target_citizen_username, # This is the one being smeared
                "assaultAngle": assault_angle_from_notes or "N/A",
                "targetCitizenUsernameForTrustImpact": target_citizen_username # Pass the smeared target for trust impact
            },
            "addMessage": {
                "stratagemId": stratagem_id,
                "stratagemType": "reputation_assault",
                "originalTarget": target_citizen_username,
                "assaultAngle": assault_angle_from_notes or "N/A",
                "coreAttackNarrative": cleaned_core_attack_narrative,
                "executorUsername": executed_by_username,
                "targetDisplayName": target_display_name,
                "recipientUsername": related_citizen_username,
                "generateMessageOnDelivery": True,
                "relationshipWithTarget": _rh_get_relationship_data(tables, target_citizen_username, related_citizen_username),
                "relationshipWithRecipient": _rh_get_relationship_data(tables, executed_by_username, related_citizen_username),
                "customPrompt": (
                    f"[SYSTEM]You are {executed_by_username}, a citizen of Venice. "
                    f"Your objective is to damage the reputation of {target_display_name} in the eyes of {related_citizen_username}. "
                    f"You have a core attack narrative about {target_display_name} (see `additional_message_data.coreAttackNarrative` in addSystem). "
                    f"Using that narrative as a foundation, and considering all the contextual information in addSystem, "
                    f"craft a persuasive message to {related_citizen_username} that subtly damages {target_display_name}'s reputation. "
                    f"Your message should be conversational, persuasive, and tailored to your relationship with {related_citizen_username}. "
                    f"Focus on the assault angle: '{assault_angle_from_notes or 'any effective angle'}'. "
                    f"Your response should be direct speech TO {related_citizen_username}, in plain text in English.[/SYSTEM]\n\n"
                    f"{executed_by_username} (you) to {related_citizen_username} about {target_display_name}: "
                )
            }
        }
        
        # Get transport API URL from the base URL if not provided
        transport_api_url = f"{api_base_url}/api/transport" if api_base_url else None
        
        log.info(f"{LogColors.PROCESS}Directly calling send_message_creator.try_create for {executed_by_username} to send message to {related_citizen_username}{LogColors.ENDC}")
            
        try:
            # Call the send_message_creator directly
            created_activity = try_create_send_message(
                tables=tables,
                citizen_record=executor_citizen_record,
                details=activity_details,
                api_base_url=api_base_url,
                transport_api_url=transport_api_url
            )
            
            if created_activity:
                log.info(f"{LogColors.OKGREEN}Successfully created send_message activity directly for {executed_by_username} to {related_citizen_username}. Activity ID: {created_activity.get('id', 'N/A')}{LogColors.ENDC}")
                messages_sent_count += 1
            else:
                log.warning(f"{LogColors.WARNING}Failed to create send_message activity directly for {executed_by_username} to {related_citizen_username}.{LogColors.ENDC}")
        except Exception as e_direct_create:
            log.error(f"{LogColors.FAIL}Error directly creating send_message activity for {related_citizen_username}: {e_direct_create}{LogColors.ENDC}")
            import traceback
            log.error(traceback.format_exc())
        else:
            log.warning(f"{LogColors.WARNING}Failed to generate specific message content (self-chat) for {related_citizen_username} (re: {target_citizen_username}) for stratagem {stratagem_id}.{LogColors.ENDC}")

    # 4. Update stratagem status
    final_notes = f"Reputation assault executed. {messages_sent_count} 'send_message' activities initiated to relations of {target_citizen_username}."
    if not stratagem_fields.get('ExecutedAt'):
        tables['stratagems'].update(stratagem_record['id'], {'ExecutedAt': datetime.now(pytz.utc).isoformat(), 'Status': 'executed', 'Notes': final_notes})
    else:
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': final_notes})
    
    log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} (reputation_assault) marked as executed. {final_notes}{LogColors.ENDC}")
    return True

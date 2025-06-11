import os
import sys
import json
import logging
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import requests
from pyairtable import Table
from dotenv import load_dotenv

# Add project root to sys.path if this script is run directly or for broader imports
PROJECT_ROOT_CONV_HELPER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT_CONV_HELPER not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_CONV_HELPER)

try:
    from backend.engine.utils.activity_helpers import (
        LogColors, _escape_airtable_value, VENICE_TIMEZONE, get_citizen_record,
        get_relationship_trust_score, # Re-using this, though it only returns score. We need full record.
        clean_thought_content # Added import for clean_thought_content
    )
except ImportError:
    # Fallbacks if run in a context where backend.engine.utils is not directly available
    # This is primarily for robustness; ideally, imports should work.
    class LogColors: HEADER = OKBLUE = OKCYAN = OKGREEN = WARNING = FAIL = ENDC = BOLD = LIGHTBLUE = PINK = ""
    def _escape_airtable_value(value: Any) -> str: return str(value).replace("'", "\\'")
    import pytz
    VENICE_TIMEZONE = pytz.timezone('Europe/Rome')
    def get_citizen_record(tables, username): return None # Placeholder
    def get_relationship_trust_score(tables, u1, u2): return 0.0 # Placeholder

# Load environment variables from the project root .env file
dotenv_path = os.path.join(PROJECT_ROOT_CONV_HELPER, '.env')
load_dotenv(dotenv_path)

log = logging.getLogger(__name__)

# KinOS Configuration (should match Compagno.tsx and autonomouslyRun.py where applicable)
KINOS_API_CHANNEL_BASE_URL = 'https://api.kinos-engine.ai/v2'
KINOS_BLUEPRINT_ID = 'serenissima-ai' # From autonomouslyRun.py
DEFAULT_TIMEOUT_SECONDS = 300 # Increased timeout for KinOS calls to 5 minutes

# --- Helper Functions (adapted from autonomouslyRun.py and Compagno.tsx) ---

def get_kinos_model_for_social_class(username: Optional[str], social_class: Optional[str]) -> str:
    """Determines the KinOS model. Defaults to 'local' unless it's NLR."""
    if username == 'NLR': # Special case for NLR
        log.info(f"User '{username}' is NLR. Using KinOS model 'gemini-2.5-pro-preview-06-05'.")
        return 'gemini-2.5-pro-preview-06-05'
    
    # For all other users, default to 'local'
    log.info(f"User '{username}' (Social Class: {social_class}) is not NLR. Defaulting KinOS model to 'local'.")
    return 'local'

def make_api_get_request_helper(endpoint: str, api_base_url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Simplified helper to make GET requests to the game API."""
    url = f"{api_base_url}{endpoint}"
    try:
        log.debug(f"Making helper GET request to: {url} with params: {params}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error(f"Helper GET request to {url} failed: {e}")
    except json.JSONDecodeError as e_json:
        log.error(f"Failed to decode JSON from helper GET {url}: {e_json}")
    return None

def get_citizen_data_package(username: str, api_base_url: str) -> Optional[Dict]:
    """Fetches the full data package for a citizen."""
    log.info(f"Fetching data package for {username}...")
    response = make_api_get_request_helper(f"/api/get-data-package?citizenUsername={username}", api_base_url)
    if response and response.get("success"):
        return response.get("data")
    log.warning(f"Failed to fetch data package for {username}: {response.get('error') if response else 'No response'}")
    return None

def get_citizen_problems_list(username: str, api_base_url: str) -> List[Dict]:
    """Fetches active problems for a citizen."""
    log.info(f"Fetching problems for {username}...")
    response = make_api_get_request_helper(f"/api/problems?Citizen={username}&Status=active", api_base_url)
    if response and response.get("success") and isinstance(response.get("problems"), list):
        return response.get("problems")
    log.warning(f"Failed to fetch problems for {username}: {response.get('error') if response else 'No response'}")
    return []

def get_relationship_details(tables: Dict[str, Table], username1: str, username2: str) -> Optional[Dict]:
    """Fetches the full relationship record between two citizens."""
    if not username1 or not username2: return None
    user1_ordered, user2_ordered = sorted([username1, username2])
    formula = f"AND({{Citizen1}}='{_escape_airtable_value(user1_ordered)}', {{Citizen2}}='{_escape_airtable_value(user2_ordered)}')"
    try:
        relationships = tables['relationships'].all(formula=formula, max_records=1)
        if relationships:
            return relationships[0]['fields']
    except Exception as e:
        log.error(f"Error fetching relationship for {user1_ordered}-{user2_ordered}: {e}")
    return None

def get_conversation_history(tables: Dict[str, Table], channel_name: Any, limit: int = 5) -> List[Dict]: # Changed type hint for channel_name to Any for robustness check
    """Fetches the last few messages for a given channel."""
    # Ensure channel_name is definitely a string before use
    str_channel_name = str(channel_name)
    
    log.info(f"Fetching conversation history for channel {str_channel_name} (limit {limit})...")
    try:
        # Assuming 'Channel' field exists in MESSAGES table
        messages = tables['messages'].all(
            formula=f"{{Channel}}='{_escape_airtable_value(str_channel_name)}'",
            sort=['-CreatedAt'], # Get latest messages first
            max_records=limit
        )
        # Messages are fetched latest first, so reverse to get chronological order for the prompt
        return [msg['fields'] for msg in reversed(messages)]
    except Exception as e:
        log.error(f"Error fetching conversation history for channel {str_channel_name}: {e}")
        # Add specific logging if the error is the one reported
        if isinstance(e, AttributeError) and "'tuple' object has no attribute 'startswith'" in str(e):
            log.error(f"Type of original channel_name parameter was: {type(channel_name)}")
    return []

def persist_message(
    tables: Dict[str, Table],
    sender_username: str,
    receiver_username: str,
    content: str,
    message_type: str,
    channel_name: str,
    kinos_message_id: Optional[str] = None
) -> Optional[Dict]:
    """Persists a message to the Airtable MESSAGES table."""
    
    # Remove <think>...</think> tags from content and apply full cleaning for AI generated types
    cleaned_content_final = content # Default to original content

    if isinstance(content, str): # Ensure content is a string before regex
        # Step 1: Remove <think> tags
        cleaned_content_think_tags = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        if not cleaned_content_think_tags and content: # If cleaning resulted in empty string but original had content
            log.warning(f"Message content from {sender_username} to {receiver_username} (type: {message_type}) became empty after removing <think> tags. Original: '{content[:100]}...'")
        
        # Step 2: Apply full cleaning for AI generated types
        ai_generated_message_types = [
            "message_ai_augmented", 
            "encounter_reflection", 
            "conversation_opener", 
            "reaction_auto",
            "ai_initiative_reasoning" # Ajout du nouveau type pour le nettoyage
        ]
        if message_type in ai_generated_message_types:
            log.info(f"Nettoyage complet du contenu du message de type '{message_type}' de {sender_username} à {receiver_username}.")
            # clean_thought_content is imported at the top of the file
            fully_cleaned_content = clean_thought_content(tables, cleaned_content_think_tags)
            if fully_cleaned_content != cleaned_content_think_tags:
                log.info(f"Contenu après nettoyage <think> (extrait): '{cleaned_content_think_tags[:100]}...'")
                log.info(f"Contenu après nettoyage complet (extrait): '{fully_cleaned_content[:100]}...'")
            cleaned_content_final = fully_cleaned_content
        else:
            # For non-AI generated types (or types not explicitly listed), only <think> tag removal is applied
            cleaned_content_final = cleaned_content_think_tags
    # If content was not a string, cleaned_content_final remains as the original content

    payload = {
        "Sender": sender_username,
        "Receiver": receiver_username,
        "Content": cleaned_content_final, # Use fully cleaned content
        "Type": message_type,
        "Channel": channel_name,
        "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
        # "ReadAt" will be null initially for the receiver
    }
    if kinos_message_id: # If KinOS provides a message ID, store it
        payload["Notes"] = json.dumps({"kinos_message_id": kinos_message_id})

    try:
        log.info(f"Persisting message from {sender_username} to {receiver_username} in channel {channel_name}.")
        created_record = tables['messages'].create(payload)
        log.info(f"Message persisted with Airtable ID: {created_record['id']}")
        return created_record
    except Exception as e:
        log.error(f"Failed to persist message from {sender_username} to {receiver_username}: {e}")
    return None


def make_kinos_channel_call(
    kinos_api_key: str,
    speaker_username: str, # This is the 'kin_id' for the KinOS API call
    channel_name: str,
    prompt: str,
    add_system_data: Optional[Dict] = None,
    kinos_model_override: Optional[str] = None
) -> Optional[str]: # Returns the AI's message content string or None
    """Makes a call to a specific KinOS Engine citizen-to-citizen channel."""
    kinos_url = f"{KINOS_API_CHANNEL_BASE_URL}/blueprints/{KINOS_BLUEPRINT_ID}/kins/{speaker_username}/channels/{channel_name}/messages"
    headers = {"Authorization": f"Bearer {kinos_api_key}", "Content-Type": "application/json"}
    
    payload: Dict[str, Any] = {"content": prompt} # Changed "message" to "content" as per Compagno.tsx
    if add_system_data:
        try:
            payload["addSystem"] = json.dumps(add_system_data)
        except TypeError as te:
            log.error(f"Error serializing addSystem data for KinOS channel call: {te}. Sending without addSystem.")
    
    if kinos_model_override:
        payload["model"] = kinos_model_override
        log.info(f"Using KinOS model override '{kinos_model_override}' for channel call by {speaker_username}.")

    try:
        log.info(f"Sending request to KinOS channel {channel_name} for speaker {speaker_username}...")
        log.debug(f"KinOS Channel Prompt for {speaker_username} to {channel_name}: {prompt[:300]}...")
        if add_system_data:
            log.debug(f"KinOS Channel addSystem keys: {list(add_system_data.keys())}")

        response = requests.post(kinos_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        
        # KinOS channel API directly returns the AI's message in the response to POST,
        # or we might need to fetch history if it works like the main kin endpoint.
        # Compagno.tsx suggests the POST response itself contains the message.
        kinos_response_data = response.json()

        # Expected structure from Compagno.tsx: { "message_id": "...", "content": "...", "role": "assistant", ... }
        # or { "id": "...", "content": "...", ... }
        ai_message_content = kinos_response_data.get("content")
        
        if ai_message_content:
            log.info(f"Received KinOS response from channel {channel_name} for speaker {speaker_username}. Length: {len(ai_message_content)}")
            # Log full raw response at INFO level
            log.info(f"{LogColors.LIGHTBLUE}Full KinOS raw response content from channel call by {speaker_username} to {channel_name}:\n{ai_message_content}{LogColors.ENDC}")
            return ai_message_content
        else:
            log.warning(f"KinOS response from channel {channel_name} for {speaker_username} missing 'content'. Response: {kinos_response_data}")
            return None

    except requests.exceptions.RequestException as e:
        log.error(f"KinOS API channel request error for {speaker_username} to {channel_name}: {e}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            log.error(f"KinOS error response content: {e.response.text[:500]}")
    except Exception as e:
        log.error(f"Error in make_kinos_channel_call for {speaker_username} to {channel_name}: {e}", exc_info=True)
    return None

# --- Main Conversation Turn Generator ---

def generate_conversation_turn(
    tables: Dict[str, Table],
    kinos_api_key: str,
    speaker_username: str,
    listener_username: str, # For reflection, this is the citizen being observed; for opener, the one being spoken to
    api_base_url: str,
    kinos_model_override: Optional[str] = None,
    max_history_messages: int = 5,
    interaction_mode: str = "conversation" # "conversation", "reflection", or "conversation_opener"
) -> Optional[Dict]:
    """
    Generates one turn of a conversation, an internal reflection, or a conversation opener.
    Persists the generated message/reflection and returns its Airtable record.
    """
    if interaction_mode == "reflection":
        log.info(f"Generating internal reflection for {speaker_username} about {listener_username}.")
    elif interaction_mode == "conversation_opener":
        log.info(f"Generating conversation opener from {speaker_username} to {listener_username}.")
    else: # conversation
        log.info(f"Generating conversation turn: Speaker: {speaker_username}, Listener: {listener_username}")

    # 1. Get Speaker and Listener (observed/spoken-to citizen) profiles
    speaker_profile_record = get_citizen_record(tables, speaker_username)
    listener_profile_record = get_citizen_record(tables, listener_username)

    if not speaker_profile_record or not listener_profile_record:
        log.error("Could not find profile for speaker or listener.")
        return None
    
    speaker_profile = speaker_profile_record['fields']
    listener_profile = listener_profile_record['fields']
    
    speaker_social_class = speaker_profile.get('SocialClass')
    # speaker_current_point_id = speaker_profile.get('Point') # No longer primary way to determine location
    # listener_current_point_id = listener_profile.get('Point')

    shared_building_name: Optional[str] = None
    shared_building_id: Optional[str] = None
    location_description_for_prompt: str = "in the streets of Venice" # Default

    speaker_pos_str = speaker_profile.get('Position')
    listener_pos_str = listener_profile.get('Position')

    if speaker_pos_str and listener_pos_str:
        try:
            speaker_coords = json.loads(speaker_pos_str)
            listener_coords = json.loads(listener_pos_str)
            
            # Find building at speaker's coords
            from backend.engine.utils.activity_helpers import get_closest_building_to_position # Local import
            
            speaker_building_rec = get_closest_building_to_position(tables, speaker_coords, max_distance_meters=10)
            
            if speaker_building_rec:
                speaker_building_id = speaker_building_rec['fields'].get('BuildingId')
                # Now check if listener is also at this building_id
                listener_building_rec = get_closest_building_to_position(tables, listener_coords, max_distance_meters=10)
                
                if listener_building_rec and listener_building_rec['fields'].get('BuildingId') == speaker_building_id:
                    shared_building_id = speaker_building_id
                    shared_building_name = speaker_building_rec['fields'].get('Name', speaker_building_id) # Use speaker's building name
                    location_description_for_prompt = f"in {shared_building_name}"
                    log.info(f"Speaker and Listener are both in building: {shared_building_name} (ID: {shared_building_id})")
                else:
                    # Speaker is in a building, but listener is not in the same one (or not in any nearby)
                    speaker_only_building_name = speaker_building_rec['fields'].get('Name', speaker_building_id)
                    location_description_for_prompt = f"near {speaker_only_building_name}" # Or "in the streets of Venice" if preferred
                    log.info(f"Speaker is in {speaker_only_building_name}, Listener is elsewhere. Defaulting to 'near {speaker_only_building_name}'.")
            # If speaker_building_rec is None, they are not in/near a building, so default "in the streets" is fine.
            
        except Exception as e_shared_bldg:
            log.warning(f"Could not determine shared building due to error: {e_shared_bldg}. Defaulting location to 'in the streets of Venice'.")
            # location_description_for_prompt remains "in the streets of Venice"
    else:
        log.info("Speaker or Listener position string is missing. Defaulting location to 'in the streets of Venice'.")
        # location_description_for_prompt remains "in the streets of Venice"


    # 2. Determine KinOS channel name
    channel_name = "_".join(sorted([speaker_username, listener_username]))

    # 3. Fetch context data for addSystem
    add_system_payload = {
        "speaker_profile": {
            "username": speaker_profile.get("Username"),
            "firstName": speaker_profile.get("FirstName"),
            "lastName": speaker_profile.get("LastName"),
            "socialClass": speaker_profile.get("SocialClass")
        },
        "listener_profile": {
            "username": listener_profile.get("Username"),
            "firstName": listener_profile.get("FirstName"),
            "lastName": listener_profile.get("LastName"),
            "socialClass": listener_profile.get("SocialClass")
        },
        "speaker_data_package": get_citizen_data_package(speaker_username, api_base_url) or {},
        "speaker_problems": get_citizen_problems_list(speaker_username, api_base_url),
        "listener_problems": get_citizen_problems_list(listener_username, api_base_url),
        "relationship_details": get_relationship_details(tables, speaker_username, listener_username) or {},
        "conversation_history": get_conversation_history(tables, channel_name, limit=max_history_messages)
    }

    # 4. Construct KinOS prompt
    # location_description_for_prompt is now set above.
    location_context = f"You are both currently {location_description_for_prompt}. "

    if interaction_mode == "reflection":
        system_explanation = (
            f"[SYSTEM]You are {speaker_profile.get('FirstName', speaker_username)}, a {speaker_profile.get('SocialClass', 'citizen')} of Venice. "
            f"{location_context}You have noticed {listener_profile.get('FirstName', listener_username)} (Social Class: {listener_profile.get('SocialClass', 'unknown')}) is also here. "
            f"Review your knowledge in `addSystem` (your data package including `availableStratagems` and active stratagems, problems, your relationship with them, their problems, and any recent direct conversation history). "
            f"What are your internal thoughts or observations about their presence and this encounter? Consider any opportunities, risks, or social implications. Could a **Stratagem** be relevant here (either one you are running, one targeting you, or one you might propose)? "
            f"Your response should be your internal monologue or reflection in English, not direct speech to them. "
            f"Keep it concise and focused on potential gameplay impact or character development.[/SYSTEM]\n\n"
        )
        prompt = system_explanation + f"{speaker_profile.get('FirstName', speaker_username)}'s internal thoughts about {listener_profile.get('FirstName', listener_username)}: "
    elif interaction_mode == "conversation_opener":
        system_explanation = (
            f"[SYSTEM]You are {speaker_profile.get('FirstName', speaker_username)}, a {speaker_profile.get('SocialClass', 'citizen')} of Venice. "
            f"{location_context}You see {listener_profile.get('FirstName', listener_username)} (Social Class: {listener_profile.get('SocialClass', 'unknown')}) here. "
            f"Review your knowledge in `addSystem` (your data package including `availableStratagems` and active stratagems, problems, your relationship with them, their problems, and any recent direct conversation history). "
            f"What would you say to them to initiate or continue a conversation? Your opening could be related to a shared interest, a problem, an opportunity, or perhaps a **Stratagem** you wish to discuss or propose. "
            f"Your response should be direct speech TO {listener_profile.get('FirstName', listener_username)}, in English. "
            f"Keep it concise, in character, and relevant to your current situation or relationship.[/SYSTEM]\n\n"
        )
        # No conversation history for an opener
        prompt = system_explanation + f"{speaker_profile.get('FirstName', speaker_username)} (you) to {listener_profile.get('FirstName', listener_username)}: "
    else: # "conversation" mode (replying in an existing conversation)
        system_explanation = (
            f"[SYSTEM]You are {speaker_profile.get('FirstName', speaker_username)}, a {speaker_profile.get('SocialClass', 'citizen')} of Venice. "
            f"You are currently in conversation with {listener_profile.get('FirstName', listener_username)}. {location_context}"
            f"Review your knowledge in `addSystem` (your data package including `availableStratagems` and active stratagems, problems, relationship, listener's problems, and recent conversation history). "
            f"Answer/continue the conversation naturally in English, keeping your persona and objectives in mind. If strategic elements arise, remember that **Stratagems** are a key way to interact with the world. Your response should be direct speech.[/SYSTEM]\n\n"
        )
        
        prompt = system_explanation + f"{speaker_profile.get('FirstName', speaker_username)} (you): "

    # 5. Determine KinOS model
    effective_kinos_model = kinos_model_override or get_kinos_model_for_social_class(speaker_username, speaker_social_class)

    # --- NEW LOGIC for local model pre-processing ---
    final_add_system_data = add_system_payload # By default, use the full data package

    if effective_kinos_model == 'local':
        log.info(f"Local model detected for {speaker_username}. Performing attention pre-prompt step.")
        
        # A. Attention Call
        attention_channel_name = "attention"
        attention_prompt = (
            f"You are an AI assistant helping {speaker_username} prepare for a conversation with {listener_username}. "
            f"Based on the extensive context provided in `addSystem`, please perform the following two steps:\n\n"
            f"Step 1: Build a clear picture of the current situation. Describe the relationship, recent events, and any ongoing issues or goals for both individuals.\n\n"
            f"Step 2: Using the situation picture from Step 1 and your understanding of {speaker_username}'s personality, summarize the information and extract the most relevant specific pieces that should influence their next message. "
            "Focus on what is most important for them to remember or act upon in this specific interaction. Your final output should be this summary in English."
        )

        summarized_context = make_kinos_channel_call(
            kinos_api_key,
            speaker_username,
            attention_channel_name,
            attention_prompt,
            add_system_payload, # Use the full data package for the attention call
            'local' # Explicitly use local model for this step
        )

        if summarized_context:
            # Clean the summarized context before using it
            cleaned_summarized_context = clean_thought_content(tables, summarized_context)
            log.info(f"Successfully generated summarized context for {speaker_username}. Original length: {len(summarized_context)}, Cleaned length: {len(cleaned_summarized_context)}")
            log.debug(f"Original summarized context: {summarized_context}")
            log.debug(f"Cleaned summarized context: {cleaned_summarized_context}")
            
            # B. Prepare for Conversation Call with cleaned summarized context
            final_add_system_data = {
                "summary_of_relevant_context": cleaned_summarized_context,
                "original_context_available_on_request": "The full data package was summarized. You are now acting as the character based on this summary."
            }
        else:
            log.warning(f"Failed to generate summarized context for {speaker_username}. The conversation turn will be aborted for the local model.")
            return None # Abort the turn if summarization fails

    # 6. Call KinOS Engine (using final_add_system_data)
    ai_message_content = make_kinos_channel_call(
        kinos_api_key,
        speaker_username, # speaker_username is the kin_id
        channel_name,
        prompt, # The original prompt for the conversation
        final_add_system_data, # This is either the full package or the summary
        effective_kinos_model
    )

    if not ai_message_content:
        log.error(f"KinOS failed to generate a message for {speaker_username} to {listener_username}.")
        return None

    # 7. Persist message/reflection
    message_receiver = listener_username # Default for conversation and opener
    message_type_to_persist = "message_ai_augmented" # Default for conversation and opener
    
    if interaction_mode == "reflection":
        message_receiver = speaker_username # Reflection is "to self"
        message_type_to_persist = "encounter_reflection"
        log.info(f"Persisting reflection from {speaker_username} about {listener_username} (to self).")
    elif interaction_mode == "conversation_opener":
        # Receiver is listener_username, type is still message_ai_augmented or a new "opener" type
        message_type_to_persist = "conversation_opener" # Or keep as message_ai_augmented
        log.info(f"Persisting conversation opener from {speaker_username} to {listener_username}.")
    
    persisted_message_record = persist_message(
        tables,
        sender_username=speaker_username,
        receiver_username=message_receiver,
        content=ai_message_content,
        message_type=message_type_to_persist,
        channel_name=channel_name # Channel remains the pair for context, type differentiates
    )

    if persisted_message_record:
        if interaction_mode == "reflection":
            log.info(f"Successfully generated and persisted reflection from {speaker_username} about {listener_username}.")
        elif interaction_mode == "conversation_opener":
            log.info(f"Successfully generated and persisted conversation opener from {speaker_username} to {listener_username}.")
        else: # conversation
            log.info(f"Successfully generated and persisted conversation turn from {speaker_username}.")
        return persisted_message_record # Return the full Airtable record
    else:
        log.error(f"Failed to persist KinOS message from {speaker_username}.")
        return None


if __name__ == '__main__':
    # Example Usage (requires .env to be set up correctly)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log.info("Conversation Helper - Example Usage")

    kinos_key = os.getenv("KINOS_API_KEY")
    airtable_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base = os.getenv("AIRTABLE_BASE_ID")
    next_public_base_url = os.getenv("NEXT_PUBLIC_BASE_URL", "http://localhost:3000")

    if not all([kinos_key, airtable_key, airtable_base]):
        log.error("Missing KINOS_API_KEY, AIRTABLE_API_KEY, or AIRTABLE_BASE_ID in .env file.")
        sys.exit(1)

    try:
        api = requests.Session() # Dummy session for type hint, not used by pyairtable directly
        airtable_api_instance = Table(airtable_key, airtable_base, "MESSAGES", api=api).api # Get Api instance
        
        example_tables = {
            'citizens': airtable_api_instance.table(airtable_base, 'CITIZENS'),
            'messages': airtable_api_instance.table(airtable_base, 'MESSAGES'),
            'relationships': airtable_api_instance.table(airtable_base, 'RELATIONSHIPS'),
            'problems': airtable_api_instance.table(airtable_base, 'PROBLEMS'), # Assuming PROBLEMS table exists
        }
        log.info("Airtable tables initialized for example.")
    except Exception as e:
        log.error(f"Failed to initialize Airtable for example: {e}")
        sys.exit(1)

    # --- Define citizens for the conversation ---
    # Replace with actual usernames from your Airtable
    citizen1_test_username = "NLR"  # Example: The AI that will speak
    citizen2_test_username = "BasstheWhale" # Example: The AI that will listen this turn
    
    log.info(f"Attempting to generate conversation turn: {citizen1_test_username} (speaker) to {citizen2_test_username} (listener)")

    # Generate a turn
    new_message_record = generate_conversation_turn(
        tables=example_tables,
        kinos_api_key=kinos_key,
        speaker_username=citizen1_test_username,
        listener_username=citizen2_test_username,
        api_base_url=next_public_base_url,
        interaction_mode="conversation" # Explicitly "conversation" for this example
        # kinos_model_override="local" # Optional: force a model
    )

    if new_message_record:
        log.info(f"Conversation turn/reflection generated and saved. Message ID: {new_message_record.get('id')}")
        log.info(f"Content: {new_message_record.get('fields', {}).get('Content')}")
    else:
        log.error("Failed to generate conversation turn.")

    # Example for the other citizen to reply (swap speaker and listener)
    # log.info(f"\nAttempting to generate reply: {citizen2_test_username} (speaker) to {citizen1_test_username} (listener)")
    # reply_message_record = generate_conversation_turn(
    #     tables=example_tables,
    #     kinos_api_key=kinos_key,
    #     speaker_username=citizen2_test_username,
    #     listener_username=citizen1_test_username,
    #     api_base_url=next_public_base_url
    # )
    # if reply_message_record:
    #     log.info(f"Reply generated and saved. Message ID: {reply_message_record.get('id')}")
    #     log.info(f"Content: {reply_message_record.get('fields', {}).get('Content')}")
    # else:
    #     log.error("Failed to generate reply.")

    # Example for reflection
    # log.info(f"\nAttempting to generate reflection: {citizen1_test_username} about {citizen2_test_username}")
    # reflection_message_record = generate_conversation_turn(
    #     tables=example_tables,
    #     kinos_api_key=kinos_key,
    #     speaker_username=citizen1_test_username,
    #     listener_username=citizen2_test_username,
    #     api_base_url=next_public_base_url,
    #     interaction_mode="reflection"
    # )
    # if reflection_message_record:
    #     log.info(f"Reflection generated and saved. Message ID: {reflection_message_record.get('id')}")
    #     log.info(f"Content: {reflection_message_record.get('fields', {}).get('Content')}")
    # else:
    #     log.error("Failed to generate reflection.")

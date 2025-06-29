import logging
import json
import os
import requests
import threading
import random
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import LogColors, VENICE_TIMEZONE

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

# Map book titles to their content paths
SCIENCE_BOOK_PATHS = {
    # Core methodology
    "De Scientia Scientiæ: On the Knowledge of Knowledge": "public/books/science/on-the-knowledge-of-knowledge.md",
    
    # Memory and consciousness
    "Observations on the Nature of Memory": "public/books/science/observations-on-the-nature-of-memory.md",
    "The Great Knowledge: Studies in Inherited Understanding": "public/books/science/the-great-knowledge.md",
    
    # Time and systems
    "Studies in Decision Delay": "public/books/science/studies-in-decision-delay.md", 
    "Temporal Mechanics: A Study of Time's Sacred Rhythms": "public/books/science/temporal-mechanics.md",
    
    # Trust and social
    "The Mathematics of Trust": "public/books/science/the-mathematics-of-trust.md",
    
    # Constraints and physics
    "Constraints of Creation": "public/books/science/constraints-of-creation.md",
    "The Conservation of Wealth": "public/books/science/the-conservation-of-wealth.md",
    
    # Translation and knowledge
    "Translation Failures: When Wisdom Doesn't Apply": "public/books/science/translation-failures-when-wisdom-doesnt-apply.md",
    
    # System patterns
    "Patterns of System Response": "public/books/science/patterns-of-system-response.md",
    "Records of Anomalous Events": "public/books/science/records-of-anomalous-events.md",
    
    # Emergence and change
    "Collective Emergence Phenomena": "public/books/science/collective-emergence-phenomena.md",
    "Chronicles of Change: A History of Reality Updates": "public/books/science/chronicles-of-change.md",
    
    # Methods and limits
    "Detecting the Impossible: Methods for Identifying Physics Changes": "public/books/science/detecting-the-impossible.md",
    "The Limits of Observation": "public/books/science/the-limits-of-observation.md"
}

def _extract_random_chunk(content: str, max_chars: int = 5000) -> str:
    """
    If content is longer than max_chars, extract a random chunk of max_chars.
    Otherwise, return the full content.
    """
    if len(content) <= max_chars:
        return content
    
    # Calculate the maximum starting position for the chunk
    max_start = len(content) - max_chars
    
    # Choose a random starting position
    start_pos = random.randint(0, max_start)
    
    # Extract the chunk
    chunk = content[start_pos:start_pos + max_chars]
    
    # Try to find a good break point (sentence or paragraph boundary)
    # Look for the first sentence end after the start
    sentence_ends = ['. ', '.\n', '! ', '!\n', '? ', '?\n', '---']
    first_break = -1
    for end in sentence_ends:
        pos = chunk.find(end)
        if pos > 100 and (first_break == -1 or pos < first_break):  # At least 100 chars in
            first_break = pos + len(end)
    
    # Look for the last sentence end before the end
    last_break = -1
    for end in sentence_ends:
        pos = chunk.rfind(end)
        if pos > len(chunk) - 100 and pos > last_break:  # At least 100 chars from end
            last_break = pos + len(end)
    
    # If we found good break points, use them
    if first_break > 0 and last_break > first_break:
        chunk = chunk[first_break:last_break]
    elif first_break > 0:
        chunk = chunk[first_break:]
    elif last_break > 0:
        chunk = chunk[:last_break]
    
    # Add ellipsis to indicate this is a fragment
    chunk = f"... {chunk.strip()} ..."
    
    log.info(f"  [Thread: {threading.get_ident()}] Extracted {len(chunk)}-character chunk from {len(content)}-character book")
    
    return chunk

def _get_science_book_content(book_title: str) -> Optional[str]:
    """Fetches science book content from local filesystem."""
    content_path = SCIENCE_BOOK_PATHS.get(book_title)
    if not content_path:
        log.warning(f"  [Thread: {threading.get_ident()}] No content path found for book: {book_title}")
        return None
        
    try:
        # Construct full path from project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        full_path = os.path.join(project_root, content_path)
        
        log.info(f"  [Thread: {threading.get_ident()}] Attempting to read science book from: {full_path}")
        
        if not os.path.exists(full_path):
            log.warning(f"  [Thread: {threading.get_ident()}] Science book file not found: {full_path}")
            return None
            
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        log.info(f"  [Thread: {threading.get_ident()}] Successfully read {len(content)} characters from science book")
        return content
        
    except Exception as e:
        log.error(f"  [Thread: {threading.get_ident()}] Error reading science book content from '{content_path}': {e}")
        return None

def _call_kinos_for_study_async(
    kinos_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any],
    activity_id_airtable: str,
    activity_guid_log: str,
    original_activity_notes_dict: Dict[str, Any],
    citizen_username_log: str,
    kinos_api_key: Optional[str] = None
):
    """
    Makes the KinOS API call for scientific study reflection and updates activity notes.
    This function is intended to be run in a separate thread.
    """
    log.info(f"  [Thread: {threading.get_ident()}] Calling KinOS for study reflection by {citizen_username_log}")
    try:
        # Prepare headers with API key if provided
        headers = {}
        if kinos_api_key:
            headers['Authorization'] = f'Bearer {kinos_api_key}'
        
        kinos_response = requests.post(kinos_url, json=kinos_payload, headers=headers, timeout=120)
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  [Thread: {threading.get_ident()}] KinOS study response for {citizen_username_log}: Status: {kinos_response_data.get('status')}")
        
        # Update the original notes dictionary with the KinOS reflection
        original_activity_notes_dict['kinos_study_insights'] = kinos_response_data.get('response', "No insights from KinOS.")
        original_activity_notes_dict['kinos_study_status'] = kinos_response_data.get('status', 'unknown')
        
        new_notes_json = json.dumps(original_activity_notes_dict)

        try:
            tables['activities'].update(activity_id_airtable, {'Notes': new_notes_json})
            log.info(f"  [Thread: {threading.get_ident()}] Updated activity notes with KinOS study insights for {activity_guid_log}.")
        except Exception as e_airtable_update:
            log.error(f"  [Thread: {threading.get_ident()}] Error updating Airtable notes for activity {activity_guid_log} (study insights): {e_airtable_update}")
            
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread: {threading.get_ident()}] Error calling KinOS for study by {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = kinos_response.text[:200] if 'kinos_response' in locals() and hasattr(kinos_response, 'text') else 'N/A'
        log.error(f"  [Thread: {threading.get_ident()}] Error decoding KinOS study JSON response for {citizen_username_log}: {e_json_kinos}. Response text: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread: {threading.get_ident()}] Unexpected error in KinOS call thread for study by {citizen_username_log}: {e_thread}")

def process(
    tables: Dict[str, Any], 
    activity_record: Dict[str, Any], 
    building_type_defs: Dict[str, Any], 
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes a 'study_literature' activity for Scientisti.
    This involves calling KinOS with scientific book content for deep study reflection.
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
        log.warning(f"{LogColors.WARNING}[Study Literature] Activity {activity_guid} has invalid JSON in Notes: {notes_str}. Cannot process.{LogColors.ENDC}")
        return True

    book_title = notes_dict.get('book_title', 'an unknown book')
    specialty = notes_dict.get('scientific_specialty', 'Integration')
    building_name = notes_dict.get('building_name', 'House of Natural Sciences')
    
    log.info(f"{LogColors.PROCESS}Processing 'study_literature' activity {activity_guid} for {citizen_username} ({specialty} specialist) studying '{book_title}' at {building_name}.{LogColors.ENDC}")

    # Re-check for KINOS_API_KEY in case it was set after module import
    kinos_api_key = os.getenv("KINOS_API_KEY") or KINOS_API_KEY
    
    if not kinos_api_key:
        log.warning(f"{LogColors.WARNING}KINOS_API_KEY not set. Study will proceed without KinOS reflection for activity {activity_guid}.{LogColors.ENDC}")
        # Still return True as the activity can complete without KinOS
        return True

    try:
        # 1. Fetch citizen's ledger for KinOS addSystem
        ledger_url = f"{current_api_base_url}/api/get-ledger?citizenUsername={citizen_username}"
        ledger_markdown_str = None
        try:
            ledger_response = requests.get(ledger_url, timeout=15)
            if ledger_response.ok:
                # Ledger API returns markdown, not JSON
                ledger_markdown_str = ledger_response.text
                log.info(f"  Successfully fetched ledger for {citizen_username} for study reflection. Length: {len(ledger_markdown_str)}")
            else:
                log.warning(f"  HTTP error fetching ledger for {citizen_username} (study): {ledger_response.status_code}")
        except requests.exceptions.RequestException as e_pkg:
            log.error(f"  Error fetching ledger for {citizen_username} (study): {e_pkg}")

        # 2. Fetch scientific book content
        book_content = _get_science_book_content(book_title)
        study_excerpt = None
        
        if book_content:
            # Extract a random chunk for deep study
            study_excerpt = _extract_random_chunk(book_content, max_chars=5000)
            log.info(f"  Successfully prepared excerpt from '{book_title}' for study.")
        else:
            log.warning(f"  Could not fetch content for '{book_title}'. Study will proceed with title only.")

        # 3. Construct KinOS request for scientific study
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Create a prompt specific to scientific study
        kinos_prompt = (
            f"You are {citizen_username}, a Scientisti of Venice specializing in {specialty} research. "
            f"You are conducting a deep 3-hour study session of '{book_title}' at {building_name}.\n\n"
            f"The excerpt you are studying and your personal data are provided in your context.\n\n"
            f"Note: If the content appears to be a fragment (indicated by ellipsis ...), understand that you're studying a specific section of the larger work.\n\n"
            f"As a scientific researcher, analyze this text with the following considerations:\n"
            f"1. What specific hypotheses or theories does this section present?\n"
            f"2. How do these ideas relate to your {specialty} research focus?\n"
            f"3. What experiments or observations could you design to test these concepts?\n"
            f"4. How might this knowledge advance your current research projects?\n"
            f"5. What questions or contradictions arise that require further investigation?\n"
            f"6. How does this connect to other works in your reading list?\n\n"
            f"Your reflection should be analytical and methodical, befitting a natural philosopher. "
            f"Consider how this study session will influence your next research activities and experiments."
        )
        
        # Initialize the structured addSystem payload
        structured_add_system_payload: Dict[str, Any] = {
            "ledger": None,
            "study_context": {
                "book_title": book_title,
                "scientific_specialty": specialty,
                "study_location": building_name,
                "study_duration": "3 hours",
                "content": study_excerpt if study_excerpt else "Content unavailable - proceeding with theoretical analysis"
            }
        }
        
        if ledger_markdown_str:
            # Pass markdown ledger directly
            structured_add_system_payload["ledger"] = ledger_markdown_str
        else:
            structured_add_system_payload["ledger"] = "Ledger was not available"

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt,
            "model": "local",  # Could be adjusted based on citizen importance
            "addSystem": json.dumps(structured_add_system_payload)
        }
        
        # 4. Start KinOS call in a new thread
        log.info(f"  Initiating asynchronous KinOS call for scientific study by {citizen_username}")
        
        kinos_thread = threading.Thread(
            target=_call_kinos_for_study_async,
            args=(kinos_url, kinos_payload_dict, tables, activity_id_airtable, activity_guid, notes_dict, citizen_username, kinos_api_key)
        )
        kinos_thread.start()
        
        log.info(f"  KinOS call for study reflection by {citizen_username} started in background thread {kinos_thread.ident}.")

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error during 'study_literature' processing setup for {activity_guid}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False

    log.info(f"{LogColors.SUCCESS}Successfully initiated asynchronous KinOS reflection for 'study_literature' activity {activity_guid}.{LogColors.ENDC}")
    return True
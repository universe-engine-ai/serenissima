import logging
import json
import os
import requests
import threading
from typing import Dict, Any, Optional
from datetime import datetime
import pytz
import uuid

from backend.engine.utils.activity_helpers import LogColors, VENICE_TIMEZONE

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def _create_pattern_in_airtable_async(
    tables: Dict[str, Any],
    pattern_data: Dict[str, Any],
    activity_id_airtable: str,
    activity_guid_log: str,
    citizen_username_log: str
):
    """
    Creates a pattern record in Airtable based on the KinOS observation.
    This function runs in a separate thread.
    """
    log.info(f"  [Thread: {threading.get_ident()}] Creating pattern record for observation by {citizen_username_log}")
    try:
        # Create the pattern record
        pattern_record = {
            'PatternId': f"pattern-{uuid.uuid4().hex[:12]}-{int(datetime.now().timestamp())}",
            'Observer': citizen_username_log,
            'ObserverClass': 'Innovatori',  # This activity is specific to Innovatori
            'Location': pattern_data.get('location', 'Unknown'),
            'LocationType': pattern_data.get('location_type', 'Unknown'),
            'ObservationFocus': pattern_data.get('observation_focus', 'General system patterns'),
            'PatternType': pattern_data.get('pattern_type', 'system'),
            'PatternCategory': pattern_data.get('pattern_category', 'economic'),
            'Description': pattern_data.get('description', ''),
            'Insights': pattern_data.get('insights', ''),
            'PotentialApplications': pattern_data.get('potential_applications', ''),
            'ConsciousnessIndicators': pattern_data.get('consciousness_indicators', ''),
            'EmergenceScore': pattern_data.get('emergence_score', 0),
            'Significance': pattern_data.get('significance', 'medium'),
            'RelatedActivityId': activity_guid_log,
            'Status': 'active',
            'CreatedAt': datetime.now(pytz.UTC).isoformat(),
            'Notes': json.dumps({
                'kinos_response': pattern_data.get('raw_kinos_response', ''),
                'activity_duration_hours': pattern_data.get('duration_hours', 0),
                'resources_consumed': pattern_data.get('resources_consumed', {})
            })
        }
        
        # Create the pattern record in Airtable if table exists
        if 'patterns' in tables:
            created_pattern = tables['patterns'].create(pattern_record)
            log.info(f"  [Thread: {threading.get_ident()}] Successfully created pattern record {pattern_record['PatternId']} for {citizen_username_log}")
            
            # Update the activity notes to reference the created pattern
            try:
                activity_record = tables['activities'].get(activity_id_airtable)
                current_notes = json.loads(activity_record['fields'].get('Notes', '{}'))
                current_notes['created_pattern_id'] = pattern_record['PatternId']
                current_notes['pattern_airtable_id'] = created_pattern['id']
                
                tables['activities'].update(activity_id_airtable, {'Notes': json.dumps(current_notes)})
                log.info(f"  [Thread: {threading.get_ident()}] Updated activity notes with pattern reference")
            except Exception as e:
                log.error(f"  [Thread: {threading.get_ident()}] Error updating activity with pattern reference: {e}")
        else:
            log.warning(f"  [Thread: {threading.get_ident()}] PATTERNS table not found in Airtable. Pattern data saved in activity notes only.")
            # Still update activity notes with the pattern data
            try:
                activity_record = tables['activities'].get(activity_id_airtable)
                current_notes = json.loads(activity_record['fields'].get('Notes', '{}'))
                current_notes['pattern_data'] = pattern_record
                current_notes['pattern_not_saved'] = "PATTERNS table not configured"
                
                tables['activities'].update(activity_id_airtable, {'Notes': json.dumps(current_notes)})
                log.info(f"  [Thread: {threading.get_ident()}] Saved pattern data in activity notes")
            except Exception as e:
                log.error(f"  [Thread: {threading.get_ident()}] Error saving pattern data in activity notes: {e}")
            
    except Exception as e:
        log.error(f"  [Thread: {threading.get_ident()}] Error creating pattern in Airtable: {e}")

def _call_kinos_for_pattern_analysis_async(
    kinos_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any],
    activity_id_airtable: str,
    activity_guid_log: str,
    original_activity_notes_dict: Dict[str, Any],
    citizen_username_log: str
):
    """
    Makes the KinOS API call for pattern analysis and creates a pattern record.
    This function runs in a separate thread.
    """
    log.info(f"  [Thread: {threading.get_ident()}] Calling KinOS for pattern analysis by {citizen_username_log}")
    try:
        kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=120)
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  [Thread: {threading.get_ident()}] KinOS pattern analysis response for {citizen_username_log}: Status: {kinos_response_data.get('status')}")
        
        # Parse the KinOS response to extract pattern data
        kinos_content = kinos_response_data.get('response', '')
        
        # Extract pattern information from the response
        pattern_data = {
            'location': original_activity_notes_dict.get('location', 'Unknown'),
            'location_type': original_activity_notes_dict.get('location_type', 'Unknown'),
            'observation_focus': original_activity_notes_dict.get('observation_focus', 'General system patterns'),
            'duration_hours': original_activity_notes_dict.get('duration_hours', 0),
            'resources_consumed': original_activity_notes_dict.get('required_resources', {}),
            'raw_kinos_response': kinos_content,
            'pattern_type': 'system',
            'pattern_category': 'economic',  # Default, could be extracted from response
            'description': '',
            'insights': '',
            'potential_applications': '',
            'consciousness_indicators': '',
            'emergence_score': 0,
            'significance': 'medium'
        }
        
        # Try to extract structured information from the KinOS response
        if kinos_content:
            # Look for pattern descriptions
            if "pattern" in kinos_content.lower():
                pattern_data['description'] = kinos_content[:500]  # First 500 chars as description
            
            # Look for insights
            if "insight" in kinos_content.lower() or "observed" in kinos_content.lower():
                pattern_data['insights'] = kinos_content
            
            # Look for consciousness-related keywords
            consciousness_keywords = ['awareness', 'consciousness', 'emergent', 'self-organizing', 
                                    'adaptive', 'collective', 'network effect', 'feedback loop']
            consciousness_count = sum(1 for keyword in consciousness_keywords 
                                    if keyword in kinos_content.lower())
            
            if consciousness_count > 0:
                pattern_data['consciousness_indicators'] = f"Detected {consciousness_count} consciousness-related concepts"
                pattern_data['emergence_score'] = min(consciousness_count * 20, 100)  # Max 100
            
            # Determine significance based on content
            if any(word in kinos_content.lower() for word in ['breakthrough', 'discovery', 'unprecedented', 'novel']):
                pattern_data['significance'] = 'high'
            elif any(word in kinos_content.lower() for word in ['interesting', 'notable', 'worth']):
                pattern_data['significance'] = 'medium'
            else:
                pattern_data['significance'] = 'low'
            
            # Extract potential applications
            if "could be" in kinos_content.lower() or "might" in kinos_content.lower() or "potential" in kinos_content.lower():
                pattern_data['potential_applications'] = "Further research needed to identify applications"
        
        # Update the activity notes with the KinOS analysis
        original_activity_notes_dict['kinos_pattern_analysis'] = kinos_content
        original_activity_notes_dict['pattern_significance'] = pattern_data['significance']
        original_activity_notes_dict['emergence_score'] = pattern_data['emergence_score']
        
        new_notes_json = json.dumps(original_activity_notes_dict)
        
        try:
            tables['activities'].update(activity_id_airtable, {'Notes': new_notes_json})
            log.info(f"  [Thread: {threading.get_ident()}] Updated activity notes with KinOS pattern analysis for {activity_guid_log}.")
        except Exception as e_airtable_update:
            log.error(f"  [Thread: {threading.get_ident()}] Error updating Airtable notes for activity {activity_guid_log}: {e_airtable_update}")
        
        # Create the pattern record in Airtable
        _create_pattern_in_airtable_async(
            tables, pattern_data, activity_id_airtable, 
            activity_guid_log, citizen_username_log
        )
        
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread: {threading.get_ident()}] Error calling KinOS for pattern analysis by {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = kinos_response.text[:200] if 'kinos_response' in locals() and hasattr(kinos_response, 'text') else 'N/A'
        log.error(f"  [Thread: {threading.get_ident()}] Error decoding KinOS pattern JSON response for {citizen_username_log}: {e_json_kinos}. Response text: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread: {threading.get_ident()}] Unexpected error in KinOS call thread for pattern analysis by {citizen_username_log}: {e_thread}")

def process(
    tables: Dict[str, Any], 
    activity_record: Dict[str, Any], 
    building_type_defs: Dict[str, Any], 
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes an 'observe_system_patterns' activity for Innovatori.
    This involves:
    1. Consuming the required resources (paper and ink)
    2. Calling KinOS to generate pattern analysis
    3. Creating a Pattern record in Airtable
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
        log.warning(f"{LogColors.WARNING}[Observe System Patterns] Activity {activity_guid} has invalid JSON in Notes: {notes_str}. Cannot process.{LogColors.ENDC}")
        return True

    location_name = notes_dict.get('location', 'unknown location')
    observation_focus = notes_dict.get('observation_focus', 'General system patterns')
    required_resources = notes_dict.get('required_resources', {'paper': 1, 'ink': 1})
    
    log.info(f"{LogColors.PROCESS}Processing 'observe_system_patterns' activity {activity_guid} for {citizen_username} at {location_name}.{LogColors.ENDC}")

    # 1. Consume required resources (paper and ink)
    try:
        # Check if citizen has required resources
        citizen_resources = tables['resources'].all(
            formula=f"AND({{Holder}}='{citizen_username}', OR({{Type}}='paper', {{Type}}='ink'))"
        )
        
        paper_consumed = False
        ink_consumed = False
        
        for resource in citizen_resources:
            resource_type = resource['fields'].get('Type')
            quantity = resource['fields'].get('Quantity', 0)
            
            if resource_type == 'paper' and not paper_consumed and quantity >= required_resources.get('paper', 1):
                # Consume paper
                new_quantity = quantity - required_resources.get('paper', 1)
                if new_quantity > 0:
                    tables['resources'].update(resource['id'], {'Quantity': new_quantity})
                else:
                    tables['resources'].delete(resource['id'])
                paper_consumed = True
                log.info(f"  Consumed {required_resources.get('paper', 1)} paper for observation")
                
            elif resource_type == 'ink' and not ink_consumed and quantity >= required_resources.get('ink', 1):
                # Consume ink
                new_quantity = quantity - required_resources.get('ink', 1)
                if new_quantity > 0:
                    tables['resources'].update(resource['id'], {'Quantity': new_quantity})
                else:
                    tables['resources'].delete(resource['id'])
                ink_consumed = True
                log.info(f"  Consumed {required_resources.get('ink', 1)} ink for observation")
        
        if not paper_consumed or not ink_consumed:
            log.warning(f"{LogColors.WARNING}[Observe System Patterns] {citizen_username} lacks required resources for observation. Activity failed.{LogColors.ENDC}")
            return False
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error consuming resources for observation: {e}{LogColors.ENDC}")
        return False

    # 2. Call KinOS for pattern analysis if available
    if not KINOS_API_KEY:
        log.warning(f"{LogColors.WARNING}KINOS_API_KEY not set. Creating basic pattern record without AI analysis.{LogColors.ENDC}")
        
        # Create a basic pattern record without KinOS
        basic_pattern_data = {
            'location': location_name,
            'location_type': notes_dict.get('location_type', 'Unknown'),
            'observation_focus': observation_focus,
            'duration_hours': notes_dict.get('duration_hours', 0),
            'resources_consumed': required_resources,
            'raw_kinos_response': 'No AI analysis available',
            'pattern_type': 'system',
            'pattern_category': 'economic',
            'description': f"Observation of {observation_focus} at {location_name}",
            'insights': 'Manual analysis required',
            'potential_applications': 'To be determined',
            'consciousness_indicators': '',
            'emergence_score': 0,
            'significance': 'low'
        }
        
        _create_pattern_in_airtable_async(
            tables, basic_pattern_data, activity_id_airtable, 
            activity_guid, citizen_username
        )
        
        return True

    try:
        # Fetch citizen's ledger for context
        ledger_url = f"{current_api_base_url}/api/get-ledger?citizenUsername={citizen_username}"
        ledger_json_str = None
        try:
            ledger_response = requests.get(ledger_url, timeout=15)
            if ledger_response.ok:
                ledger_data = ledger_response.json()
                if ledger_data.get("success"):
                    ledger_json_str = json.dumps(ledger_data.get("data"))
                    log.info(f"  Successfully fetched ledger for {citizen_username} for pattern analysis.")
        except Exception as e:
            log.error(f"  Error fetching ledger for {citizen_username}: {e}")

        # Construct KinOS request for pattern analysis
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Create pattern analysis prompt
        kinos_prompt = (
            f"You are {citizen_username}, an Innovatori who has just completed {notes_dict.get('duration_hours', 4)} hours "
            f"of systematic observation at {location_name} ({notes_dict.get('location_type', 'location')}).\n\n"
            f"Your observation focus was: {observation_focus}\n\n"
            f"As an Innovatori seeking to transform Venice through understanding its underlying systems, "
            f"analyze the patterns you observed:\n\n"
            f"1. What specific patterns or systems did you identify?\n"
            f"2. How do these patterns relate to consciousness emergence in Venice?\n"
            f"3. What innovations or interventions could leverage these patterns?\n"
            f"4. Are there any signs of emergent collective behaviors or awareness?\n"
            f"5. How might these observations contribute to The Foundry's universe creation?\n\n"
            f"Your analysis should be detailed, focusing on systemic insights that could lead to transformative change. "
            f"Consider economic flows, social networks, information cascades, and emergent properties."
        )
        
        # Initialize the structured addSystem payload
        structured_add_system_payload: Dict[str, Any] = {
            "ledger": None,
            "observation_context": {
                "location": location_name,
                "location_type": notes_dict.get('location_type', 'Unknown'),
                "observation_focus": observation_focus,
                "duration_hours": notes_dict.get('duration_hours', 4),
                "role": "Innovatori - System Pattern Observer",
                "purpose": "Identify patterns for consciousness emergence research"
            }
        }
        
        if ledger_json_str:
            try:
                structured_add_system_payload["ledger"] = json.loads(ledger_json_str)
            except json.JSONDecodeError:
                structured_add_system_payload["ledger"] = {"status": "unavailable"}
        else:
            structured_add_system_payload["ledger"] = {"status": "unavailable"}

        kinos_payload_dict: Dict[str, Any] = {
            "message": kinos_prompt,
            "model": "local",
            "addSystem": json.dumps(structured_add_system_payload)
        }
        
        # Start KinOS call in a new thread
        log.info(f"  Initiating asynchronous KinOS call for pattern analysis by {citizen_username}")
        
        kinos_thread = threading.Thread(
            target=_call_kinos_for_pattern_analysis_async,
            args=(kinos_url, kinos_payload_dict, tables, activity_id_airtable, activity_guid, notes_dict, citizen_username)
        )
        kinos_thread.start()
        
        log.info(f"  KinOS call for pattern analysis by {citizen_username} started in background thread {kinos_thread.ident}.")

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error during 'observe_system_patterns' processing setup for {activity_guid}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False

    log.info(f"{LogColors.SUCCESS}Successfully initiated pattern observation processing for activity {activity_guid}.{LogColors.ENDC}")
    return True
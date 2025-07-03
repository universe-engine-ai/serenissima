import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

def process_goto_location_fn(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Any,
    resource_defs: Any,
    api_base_url: Optional[str] = None # Added api_base_url for signature consistency
) -> bool:
    """
    Process a goto_location activity.
    
    This is a generic travel activity processor that can be used as part of
    multi-activity chains. It checks the Details field for "activityType" and
    "nextStep" to determine if any special handling is needed.
    
    With the new approach of creating complete activity chains upfront,
    this processor no longer needs to create follow-up activities.
    """
    fields = activity_record.get('fields', {})
    citizen = fields.get('Citizen')
    notes_str = fields.get('Notes') # Changed 'Details' to 'Notes'
    
    activity_guid = fields.get('ActivityId', activity_record.get('id', 'UnknownID')) # Get a reliable ID for logging
    details_str = fields.get('Details') # Airtable field for structured JSON for goto_location
    notes_str = fields.get('Notes')     # Airtable field for simple text notes or fallback JSON

    parsed_structured_data: Optional[Dict[str, Any]] = None

    if details_str: # Prioritize 'Details' field for structured data
        try:
            potential_json_details = json.loads(details_str)
            if isinstance(potential_json_details, dict):
                parsed_structured_data = potential_json_details
                log.info(f"Activity {activity_guid}: Parsed 'Details' field as JSON for chaining information.")
            else:
                log.info(f"Activity {activity_guid}: 'Details' field parsed, but is not a dictionary (type: {type(potential_json_details)}). Content: '{details_str[:100]}...'")
        except json.JSONDecodeError:
            log.info(f"Activity {activity_guid}: 'Details' field is not valid JSON. Content: '{details_str[:100]}...'")
    
    if not parsed_structured_data and notes_str: # Fallback to 'Notes' if 'Details' didn't yield structured data
        try:
            potential_json_notes = json.loads(notes_str)
            if isinstance(potential_json_notes, dict):
                parsed_structured_data = potential_json_notes
                log.info(f"Activity {activity_guid}: Parsed 'Notes' field as JSON for chaining information (fallback).")
            else:
                # Notes parsed but not a dict, treat as informational
                log.info(f"Activity {activity_guid}: 'Notes' field parsed, but is not a dictionary (type: {type(potential_json_notes)}). Treating as informational text: '{notes_str[:100]}...'")
        except json.JSONDecodeError:
            # Notes is not JSON, treat as informational
            log.info(f"Activity {activity_guid}: 'Notes' field is not valid JSON. Treating as informational text: '{notes_str[:100]}...'")
    elif not details_str and not notes_str: # Neither field has content
        log.info(f"Activity {activity_guid}: No 'Details' or 'Notes' field found.")

    # Check for chaining information if any structured data was successfully parsed
    if parsed_structured_data:
        activity_type_from_data = parsed_structured_data.get("activityType")
        next_step_from_data = parsed_structured_data.get("nextStep")
        
        if activity_type_from_data and next_step_from_data:
            log.info(f"Activity {activity_guid} (goto_location) is part of a '{activity_type_from_data}' activity chain, next step: '{next_step_from_data}'.")
            log.info(f"The '{next_step_from_data}' activity should already be scheduled to start after this activity.")
        # else: The parsed JSON didn't contain chaining info.
    
    # Default: Mark as processed. The primary function of goto_location is movement,
    # which is considered complete when this processor runs.
    log.info(f"Processed goto_location activity {activity_guid} for citizen {citizen}.")
    return True

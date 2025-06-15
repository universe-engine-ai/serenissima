import logging
import json
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    clean_thought_content
)
from backend.engine.utils.thinking_helper import generate_daily_reflection

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    messagesing_type_defs: Dict[str, Any], # Not directly used here but part of signature
    resource_defs: Dict[str, Any],      # Not directly used here but part of signature
    api_base_url: Optional[str] = None
) -> bool:
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    
    # 'Notes' might contain details about the rest location (e.g., home, inn)
    # but for the reflection, we primarily need the citizen's context.
    notes_str = activity_fields.get('Notes') 
    activity_details = {}
    if notes_str:
        try:
            activity_details = json.loads(notes_str)
        except json.JSONDecodeError:
            log.warning(f"Could not parse Notes JSON for rest activity {activity_guid}: {notes_str}")
            # Continue, as notes are not critical for basic rest processing + KinOS reflection

    log.info(f"{LogColors.ACTIVITY}😴 Processing 'rest' activity: {activity_guid} for {citizen_username}. Triggering daily reflection.{LogColors.ENDC}")

    citizen_airtable_record = get_citizen_record(tables, citizen_username)
    if not citizen_airtable_record:
        log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found for rest activity {activity_guid}. Aborting KinOS reflection.{LogColors.ENDC}")
        # Still return True as the 'rest' activity itself is considered processed by time passing.
        return True 

    # Generate daily reflection using the thinking_helper
    generate_daily_reflection(tables, citizen_username, api_base_url)

    # The 'rest' activity itself is considered successful by its completion.
    # KinOS reflection is an add-on.
    return True

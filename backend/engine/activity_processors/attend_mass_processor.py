import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    VENICE_TIMEZONE,
    _escape_airtable_value
)
from backend.engine.utils.process_helper import (
    create_process,
    PROCESS_TYPE_MASS_REFLECTION,
    is_processes_table_available
)

log = logging.getLogger(__name__)

def process_attend_mass_fn(
    tables: Dict[str, Any], 
    activity_record: Dict[str, Any], 
    building_type_defs: Dict[str, Any], 
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes an 'attend_mass' activity.
    For now, this simply marks the activity as completed without any special effects.
    Future implementations may include:
    - Mood improvements
    - Influence gains
    - Social interactions with other attendees
    - Special events during religious holidays
    """
    activity_id = activity_record['id']
    activity_guid = activity_record['fields'].get('ActivityId', activity_id)
    citizen_username = activity_record['fields'].get('Citizen')
    
    notes_str = activity_record['fields'].get('Notes', '{}')
    try:
        notes_dict = json.loads(notes_str)
    except json.JSONDecodeError:
        log.warning(f"{LogColors.WARNING}[Attend Mass Proc] Activity {activity_guid} has invalid JSON in Notes: {notes_str}.{LogColors.ENDC}")
        notes_dict = {}
    
    church_name = notes_dict.get('church_name', 'church')
    church_type = notes_dict.get('church_type', 'church')
    church_id = notes_dict.get('church_id')
    
    log.info(f"{LogColors.PROCESS}⛪ Processing 'attend_mass' activity {activity_guid} for citizen {citizen_username} at {church_name}.{LogColors.ENDC}")
    
    # Get citizen record
    citizen_airtable_record = get_citizen_record(tables, citizen_username)
    if not citizen_airtable_record:
        log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found for activity {activity_guid}. Aborting.{LogColors.ENDC}")
        return False
    
    # Try to find today's sermon at this church
    sermon_content = None
    sermon_prepared_by = None
    
    today_start = datetime.now(VENICE_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_iso = today_start.isoformat()
    
    # Look for a sermon message from today at this church
    sermon_formula = (
        f"AND("
        f"{{Type}}='sermon', "
        f"{{Receiver}}='{_escape_airtable_value(church_name)}', "
        f"{{CreatedAt}}>='{today_start_iso}'"
        f")"
    )
    
    try:
        sermons = tables['messages'].all(formula=sermon_formula, max_records=1)
        if sermons:
            sermon_record = sermons[0]
            sermon_content = sermon_record['fields'].get('Content', '')
            sermon_prepared_by = sermon_record['fields'].get('Sender', '')
            
            # Try to get details from the sermon
            details_str = sermon_record['fields'].get('Details', '{}')
            try:
                sermon_details = json.loads(details_str)
                if not sermon_prepared_by:
                    sermon_prepared_by = sermon_details.get('prepared_by', '')
            except:
                pass
                
            log.info(f"{LogColors.OKGREEN}Found today's sermon at {church_name} prepared by {sermon_prepared_by}.{LogColors.ENDC}")
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching sermon: {e}{LogColors.ENDC}")
    
    # Future implementations can add:
    # - Mood boost based on church type (basilica > parish church > chapel)
    # - Social interactions with other citizens at the same church
    # - Influence gains for regular attendance
    
    log.info(f"{LogColors.OKGREEN}Activity 'attend_mass' {activity_guid} for {citizen_username} at {church_name} processed successfully. Creating process for reflection.{LogColors.ENDC}")
    
    # Create a process for mass reflection
    process_details = {
        "activity_id": activity_record['id'],
        "activity_guid": activity_guid,
        "activity_details": notes_dict,
        "church_id": church_id,
        "church_name": church_name,
        "church_type": church_type,
        "sermon_content": sermon_content,
        "sermon_prepared_by": sermon_prepared_by,
        "has_sermon": sermon_content is not None
    }
    
    # Check if 'processes' table exists before creating process
    if not is_processes_table_available(tables):
        log.error(f"{LogColors.FAIL}Cannot create mass reflection process for {citizen_username} - 'processes' table not available or is not properly initialized.{LogColors.ENDC}")
        log.info(f"{LogColors.WARNING}Attempting to reinitialize tables to get a working processes table...{LogColors.ENDC}")
        
        # Try to reinitialize the tables
        try:
            from backend.engine.utils.activity_helpers import get_tables
            new_tables = get_tables()
            if is_processes_table_available(new_tables):
                log.info(f"{LogColors.OKGREEN}Successfully reinitialized tables and found working 'processes' table. Attempting to create process with new tables.{LogColors.ENDC}")
                # Include api_base_url in process_details
                if api_base_url:
                    process_details["api_base_url"] = api_base_url
                
                process_record = create_process(
                    tables=new_tables,
                    process_type=PROCESS_TYPE_MASS_REFLECTION,
                    citizen_username=citizen_username,
                    priority=5,  # Medium priority
                    details=process_details
                )
                if process_record:
                    log.info(f"{LogColors.OKGREEN}Successfully created mass reflection process for {citizen_username} after table reinitialization.{LogColors.ENDC}")
                else:
                    log.warning(f"{LogColors.WARNING}Failed to create mass reflection process for {citizen_username} even after table reinitialization.{LogColors.ENDC}")
            else:
                log.error(f"{LogColors.FAIL}Failed to get working 'processes' table even after reinitialization. Process creation failed.{LogColors.ENDC}")
        except Exception as e_reinit:
            log.error(f"{LogColors.FAIL}Error reinitializing tables: {e_reinit}{LogColors.ENDC}")
    else:
        try:
            # Include api_base_url in process_details
            if api_base_url:
                process_details["api_base_url"] = api_base_url
            
            process_record = create_process(
                tables=tables,
                process_type=PROCESS_TYPE_MASS_REFLECTION,
                citizen_username=citizen_username,
                priority=5,  # Medium priority
                details=process_details
            )
            if process_record:
                log.info(f"{LogColors.OKGREEN}Successfully created mass reflection process for {citizen_username}.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Failed to create mass reflection process for {citizen_username}.{LogColors.ENDC}")
        except Exception as e:
            log.error(f"{LogColors.FAIL}Error creating mass reflection process for {citizen_username}: {e}{LogColors.ENDC}")
    
    return True
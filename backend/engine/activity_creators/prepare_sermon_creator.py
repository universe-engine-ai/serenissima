import logging
import json
import uuid
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_building_record,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser,
    _escape_airtable_value
)

log = logging.getLogger(__name__)

SERMON_PREPARATION_DURATION_HOURS = 2.0

def try_create_prepare_sermon_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    resource_defs: Dict[str, Any], 
    building_type_defs: Dict[str, Any], 
    now_venice_dt: datetime, 
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str, 
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'prepare_sermon' activity for Clero social class citizens.
    This activity is performed at their workplace (church).
    The citizen prepares the sermon of the day by consulting with divine inspiration.
    Returns the activity if created successfully.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_social_class = citizen_record['fields'].get('SocialClass', '')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    # Check if citizen is of Clero social class
    if citizen_social_class != 'Clero':
        log.info(f"{LogColors.WARNING}[Sermon] {citizen_name_log} is not of Clero social class ({citizen_social_class}). Cannot prepare sermon.{LogColors.ENDC}")
        return None
    
    # Get the citizen's workplace (should be a church)
    workplace_id = citizen_record['fields'].get('Work')
    if not workplace_id:
        log.warning(f"{LogColors.WARNING}[Sermon] {citizen_name_log} (Clero) has no workplace assigned. Cannot prepare sermon.{LogColors.ENDC}")
        return None
    
    # Get the workplace building record
    workplace_record = get_building_record(tables, workplace_id)
    if not workplace_record:
        log.warning(f"{LogColors.WARNING}[Sermon] Could not find workplace building {workplace_id} for {citizen_name_log}.{LogColors.ENDC}")
        return None
    
    workplace_name = workplace_record['fields'].get('Name', workplace_id)
    building_type = workplace_record['fields'].get('Type', '')
    
    # Check if the workplace is a religious building
    if building_type not in ['parish_church', 'chapel', 'st__mark_s_basilica']:
        log.warning(f"{LogColors.WARNING}[Sermon] {citizen_name_log}'s workplace {workplace_name} is not a religious building ({building_type}). Cannot prepare sermon here.{LogColors.ENDC}")
        return None
    
    # Check if a sermon has already been prepared today
    today_start = now_venice_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_iso = today_start.isoformat()
    
    # Check for existing sermon message from this citizen today
    sermon_formula = (
        f"AND("
        f"{{Sender}}='{_escape_airtable_value(citizen_username)}', "
        f"{{Type}}='sermon', "
        f"{{CreatedAt}}>='{today_start_iso}'"
        f")"
    )
    
    try:
        existing_sermons = tables['messages'].all(formula=sermon_formula, max_records=1)
        if existing_sermons:
            log.info(f"{LogColors.WARNING}[Sermon] {citizen_name_log} has already prepared a sermon today. Skipping.{LogColors.ENDC}")
            return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Sermon] Error checking for existing sermons: {e}{LogColors.ENDC}")
        # Continue anyway if check fails
    
    # Also check for recent prepare_sermon activities (completed or in progress today)
    activity_formula = (
        f"AND("
        f"{{Citizen}}='{_escape_airtable_value(citizen_username)}', "
        f"{{Type}}='prepare_sermon', "
        f"OR({{Status}}='completed', {{Status}}='in_progress'), "
        f"{{StartDate}}>='{today_start_iso}'"
        f")"
    )
    
    try:
        existing_activities = tables['activities'].all(formula=activity_formula, max_records=1)
        if existing_activities:
            log.info(f"{LogColors.WARNING}[Sermon] {citizen_name_log} has a prepare_sermon activity today. Skipping.{LogColors.ENDC}")
            return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Sermon] Error checking for existing activities: {e}{LogColors.ENDC}")
        # Continue anyway if check fails
    
    log.info(f"{LogColors.ACTIVITY}[Sermon] Creating sermon preparation activity for {citizen_name_log} at {workplace_name}.{LogColors.ENDC}")
    
    # The activity starts at the given time or now
    current_chain_time_iso = start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()
    
    # Create prepare_sermon activity
    sermon_start_dt = dateutil_parser.isoparse(current_chain_time_iso.replace("Z", "+00:00"))
    if sermon_start_dt.tzinfo is None:
        sermon_start_dt = pytz.utc.localize(sermon_start_dt)
    
    sermon_end_dt = sermon_start_dt + timedelta(hours=SERMON_PREPARATION_DURATION_HOURS)
    sermon_end_time_iso = sermon_end_dt.isoformat()
    
    activity_details = {
        "church_id": workplace_id,
        "church_name": workplace_name,
        "building_type": building_type,
        "duration_hours": SERMON_PREPARATION_DURATION_HOURS
    }
    
    prepare_sermon_activity = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="prepare_sermon",
        start_date_iso=current_chain_time_iso,
        end_date_iso=sermon_end_time_iso,
        from_building_id=workplace_id,  # At the church
        to_building_id=workplace_id,    # Stays at the church
        title=f"Preparing sermon at {workplace_name}",
        description=f"{citizen_name_log} is preparing today's sermon at {workplace_name}.",
        thought=f"I must seek divine guidance to prepare a meaningful sermon for today's congregation.",
        details_json=json.dumps(activity_details),
        priority_override=70  # High priority work activity
    )
    
    if not prepare_sermon_activity:
        log.error(f"{LogColors.FAIL}[Sermon] Failed to create 'prepare_sermon' activity for {citizen_name_log}.{LogColors.ENDC}")
        return None
    
    log.info(f"{LogColors.OKGREEN}[Sermon] Successfully created 'prepare_sermon' activity for {citizen_name_log} at {workplace_name}.{LogColors.ENDC}")
    return prepare_sermon_activity
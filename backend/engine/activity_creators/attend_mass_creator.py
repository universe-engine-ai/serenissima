import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters,
    get_path_between_points,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

ATTEND_MASS_DURATION_MINUTES = 45

def try_create_attend_mass_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    church_building_record: Dict[str, Any],
    now_utc_dt: datetime,
    transport_api_url: str,
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates an 'attend_mass' activity or a chain starting with 'goto_location'.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    church_building_id = church_building_record['fields'].get('BuildingId')
    church_name = church_building_record['fields'].get('Name', church_building_id)
    church_type = church_building_record['fields'].get('Type')
    church_position = _get_building_position_coords(church_building_record)

    if not church_position:
        log.warning(f"{LogColors.WARNING}[Attend Mass] {citizen_name_log}: Church '{church_name}' has no position.{LogColors.ENDC}")
        return None

    is_at_church = False
    if citizen_position:
        is_at_church = _calculate_distance_meters(citizen_position, church_position) < 20

    effective_start_time_dt = dateutil_parser.isoparse(start_time_utc_iso) if start_time_utc_iso else now_utc_dt
    if effective_start_time_dt.tzinfo is None:
        effective_start_time_dt = pytz.utc.localize(effective_start_time_dt)
        
    attend_mass_end_time_dt = effective_start_time_dt + timedelta(minutes=ATTEND_MASS_DURATION_MINUTES)
    attend_mass_end_time_iso = attend_mass_end_time_dt.isoformat()

    activity_title = f"Attend Mass at {church_name}"
    activity_description = f"{citizen_name_log} attends mass at {church_name}."
    activity_thought = f"I shall attend mass at {church_name} to pray and reflect."
    
    # Notes for the attend_mass activity
    attend_mass_notes = {
        "church_building_id": church_building_id,
        "church_name": church_name,
        "church_type": church_type,
        "duration_minutes": ATTEND_MASS_DURATION_MINUTES
    }

    if is_at_church:
        log.info(f"{LogColors.OKBLUE}[Attend Mass] {citizen_name_log} is at the church. Creating 'attend_mass' activity.{LogColors.ENDC}")
        return create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type="attend_mass",
            start_date_iso=start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat(),
            end_date_iso=attend_mass_end_time_iso,
            from_building_id=church_building_id,
            to_building_id=church_building_id,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(attend_mass_notes),
            priority_override=50  # Medium priority for leisure activities
        )
    else:
        # Need to travel to the church
        if not citizen_position or not church_position or not church_building_id:
            log.warning(f"{LogColors.WARNING}[Attend Mass] {citizen_name_log}: Missing position data for travel.{LogColors.ENDC}")
            return None

        log.info(f"{LogColors.OKBLUE}[Attend Mass] {citizen_name_log} needs to travel to {church_name}. Creating 'goto_location'.{LogColors.ENDC}")
        path_to_church = get_path_between_points(citizen_position, church_position, transport_api_url)
        if not (path_to_church and path_to_church.get('success')):
            log.warning(f"{LogColors.WARNING}[Attend Mass] {citizen_name_log}: Cannot find path to {church_name}.{LogColors.ENDC}")
            return None

        goto_notes_str = f"Going to {church_name} to attend mass."
        action_details_for_chaining = {
            "action_on_arrival": "attend_mass",
            "duration_minutes_on_arrival": ATTEND_MASS_DURATION_MINUTES,
            "original_target_building_id_on_arrival": church_building_id,
            "title_on_arrival": activity_title,
            "description_on_arrival": activity_description,
            "thought_on_arrival": activity_thought,
            "priority_on_arrival": 50,
            "notes_for_chained_activity": attend_mass_notes
        }
        
        goto_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            destination_building_id=church_building_id,
            path_data=path_to_church,
            current_time_utc=now_utc_dt,
            notes=goto_notes_str,
            details_payload=action_details_for_chaining,
            start_time_utc_iso=start_time_utc_iso
        )
        
        if goto_activity:
            log.info(f"{LogColors.OKGREEN}[Attend Mass] {citizen_name_log}: Created 'goto_location' to {church_name}. 'attend_mass' will be chained.{LogColors.ENDC}")
            return goto_activity
        else:
            log.warning(f"{LogColors.WARNING}[Attend Mass] {citizen_name_log}: Failed to create 'goto_location' to {church_name}.{LogColors.ENDC}")
            return None


def find_nearest_church(
    tables: Dict[str, Any],
    citizen_position: Dict[str, float]
) -> Optional[Dict[str, Any]]:
    """
    Find the nearest church (parish_church, chapel, or st__mark_s_basilica) to the citizen.
    """
    # Get all churches
    church_types = ['parish_church', 'chapel', 'st__mark_s_basilica']
    church_type_filter = " OR ".join([f"{{Type}} = '{church_type}'" for church_type in church_types])
    formula = f"AND(OR({church_type_filter}), {{Status}} = 'active')"
    
    try:
        churches = tables['buildings'].all(formula=formula)
    except Exception as e:
        log.error(f"Error fetching churches: {e}")
        return None
    
    if not churches:
        log.warning("No churches found in the city")
        return None
    
    # Find the nearest church
    nearest_church = None
    min_distance = float('inf')
    
    for church in churches:
        church_position = _get_building_position_coords(church)
        if not church_position:
            continue
            
        distance = _calculate_distance_meters(citizen_position, church_position)
        if distance < min_distance:
            min_distance = distance
            nearest_church = church
    
    if nearest_church:
        church_name = nearest_church['fields'].get('Name', 'Unknown Church')
        log.info(f"Found nearest church: {church_name} at {min_distance:.0f} meters")
    
    return nearest_church
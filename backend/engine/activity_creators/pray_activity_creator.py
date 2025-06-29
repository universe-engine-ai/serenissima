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
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

PRAY_DURATION_MINUTES = 20

def try_create_pray_activity(
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
    Creates a 'pray' activity chain.
    1. Find the nearest church (parish_church, chapel, or st__mark_s_basilica).
    2. If not at the church, create 'goto_location' to the church.
    3. Create 'pray' activity at the church.
    Returns the first activity in the chain.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_social_class = citizen_record['fields'].get('SocialClass', 'Popolani')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Pray] {citizen_name_log} has no position. Cannot create 'pray' activity.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.ACTIVITY}[Pray] Attempting to create pray activity for {citizen_name_log} ({citizen_social_class}).{LogColors.ENDC}")

    # Find the nearest church
    nearest_church = find_nearest_church(tables, citizen_position)
    if not nearest_church:
        log.info(f"{LogColors.OKBLUE}[Pray] {citizen_name_log}: No church found nearby.{LogColors.ENDC}")
        return None

    church_custom_id = nearest_church['fields'].get('BuildingId')
    church_pos = _get_building_position_coords(nearest_church)
    church_name_display = nearest_church['fields'].get('Name', church_custom_id)
    church_type = nearest_church['fields'].get('Type')

    if not church_custom_id or not church_pos:
        log.warning(f"{LogColors.WARNING}[Pray] {citizen_name_log}: Target church ({church_name_display}) is invalid. Cannot create activity.{LogColors.ENDC}")
        return None

    is_at_church = _calculate_distance_meters(citizen_position, church_pos) < 20

    activity_chain = []
    current_chain_time_iso = start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()

    if not is_at_church:
        goto_activity_params = {
            "targetBuildingId": church_custom_id,
            "notes": f"Going to {church_name_display} to pray."
        }

        goto_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            activity_params=goto_activity_params,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url,
        )
        if not goto_activity:
            log.warning(f"{LogColors.WARNING}[Pray] {citizen_name_log}: Failed to create 'goto_location' to {church_name_display}.{LogColors.ENDC}")
            return None
        activity_chain.append(goto_activity)
        current_chain_time_iso = goto_activity['fields']['EndDate']

    # Create pray activity
    pray_start_dt = dateutil_parser.isoparse(current_chain_time_iso.replace("Z", "+00:00"))
    if pray_start_dt.tzinfo is None:
        pray_start_dt = pytz.utc.localize(pray_start_dt)
    
    pray_end_dt = pray_start_dt + timedelta(minutes=PRAY_DURATION_MINUTES)
    pray_end_time_iso = pray_end_dt.isoformat()

    activity_details_for_notes = {
        "church_building_id": church_custom_id,
        "church_name": church_name_display,
        "church_type": church_type,
        "duration_minutes": PRAY_DURATION_MINUTES
    }

    pray_activity = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="pray",
        start_date_iso=current_chain_time_iso,
        end_date_iso=pray_end_time_iso,
        from_building_id=church_custom_id, # At the church
        to_building_id=church_custom_id,   # Stays at the church
        title=f"Pray at {church_name_display}",
        description=f"{citizen_name_log} prays at {church_name_display}.",
        thought=f"I shall pray at {church_name_display} for guidance and peace.",
        details_json=json.dumps(activity_details_for_notes),
        priority_override=45 # Leisure activity priority
    )

    if not pray_activity:
        log.error(f"{LogColors.FAIL}[Pray] {citizen_name_log}: Failed to create 'pray' activity.{LogColors.ENDC}")
        if activity_chain: # If goto was created, try to delete it
            try: tables['activities'].delete(activity_chain[0]['id'])
            except: pass
        return None
    
    activity_chain.append(pray_activity)

    log.info(f"{LogColors.OKGREEN}[Pray] {citizen_name_log}: 'pray' activity chain created. First activity: {activity_chain[0]['fields']['Type']}.{LogColors.ENDC}")
    return activity_chain[0]


def find_nearest_church(
    tables: Dict[str, Any],
    citizen_position: Dict[str, float]
) -> Optional[Dict[str, Any]]:
    """
    Find the nearest church (parish_church, chapel, or st__mark_s_basilica) to the citizen.
    """
    # Get all religious buildings that are constructed
    formula = f"AND({{Category}} = 'religious', {{IsConstructed}} = TRUE())"
    
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
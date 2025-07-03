import logging
import json
from datetime import datetime, timedelta
import pytz
import random
from typing import Dict, Optional, Any

from backend.engine.utils.activity_helpers import (
    LogColors,
    create_activity_record,
    get_path_between_points,
    _calculate_distance_meters,
    VENICE_TIMEZONE,
    dateutil_parser
)
from .goto_position_activity_creator import try_create as try_create_goto_position_activity

log = logging.getLogger(__name__)

OBSERVE_PHENOMENA_DURATION_MINUTES = 120  # 2 hours

# Observation locations around Venice
OBSERVATION_SITES = [
    {
        "id": "grand_canal_tides",
        "name": "Grand Canal Tide Observation Point",
        "position": {"x": 45.4385, "y": 12.3358},
        "phenomena": "tidal patterns and water flow dynamics"
    },
    {
        "id": "rialto_bridge_structure",
        "name": "Rialto Bridge",
        "position": {"x": 45.4380, "y": 12.3359},
        "phenomena": "architectural stress patterns and crowd dynamics"
    },
    {
        "id": "lagoon_edge",
        "name": "Lagoon Edge Observatory",
        "position": {"x": 45.4450, "y": 12.3450},
        "phenomena": "lagoon ecosystem and bird migration patterns"
    },
    {
        "id": "san_marco_campanile",
        "name": "St. Mark's Campanile",
        "position": {"x": 45.4340, "y": 12.3388},
        "phenomena": "weather patterns and atmospheric conditions"
    },
    {
        "id": "arsenale_shipyard",
        "name": "Arsenale Shipyard",
        "position": {"x": 45.4350, "y": 12.3530},
        "phenomena": "material degradation and marine engineering"
    }
]

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    now_utc_dt: datetime,
    transport_api_url: str,
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates an 'observe_phenomena' activity for Scientisti to observe natural phenomena.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Observe Phenomena] {citizen_name_log} has no position.{LogColors.ENDC}")
        return None
    
    # Select a random observation site
    site = random.choice(OBSERVATION_SITES)
    
    # Check distance to site
    distance = _calculate_distance_meters(citizen_position, site['position'])
    is_at_site = distance < 50  # Within 50 meters
    
    effective_start_time_dt = dateutil_parser.isoparse(start_time_utc_iso) if start_time_utc_iso else now_utc_dt
    if effective_start_time_dt.tzinfo is None:
        effective_start_time_dt = pytz.utc.localize(effective_start_time_dt)
    
    observe_end_time_dt = effective_start_time_dt + timedelta(minutes=OBSERVE_PHENOMENA_DURATION_MINUTES)
    observe_end_time_iso = observe_end_time_dt.isoformat()
    
    activity_title = f"Observe {site['phenomena']}"
    activity_description = f"{citizen_name_log} observes {site['phenomena']} at {site['name']}."
    activity_thought = f"I must carefully document the {site['phenomena']} for my research."
    
    # Notes for the observation activity
    observation_notes = {
        "site_id": site['id'],
        "site_name": site['name'],
        "phenomena": site['phenomena'],
        "observation_duration_minutes": OBSERVE_PHENOMENA_DURATION_MINUTES
    }
    
    if is_at_site:
        log.info(f"{LogColors.OKBLUE}[Observe Phenomena] {citizen_name_log} is at {site['name']}. Creating observation activity.{LogColors.ENDC}")
        return create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type="observe_phenomena",
            start_date_iso=start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat(),
            end_date_iso=observe_end_time_iso,
            from_building_id=None,  # Outdoor observation
            to_building_id=None,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(observation_notes),
            priority_override=55
        )
    else:
        # Need to travel to observation site
        log.info(f"{LogColors.OKBLUE}[Observe Phenomena] {citizen_name_log} needs to travel to {site['name']}. Creating 'goto_position' activity.{LogColors.ENDC}")
        
        goto_notes_str = f"Going to {site['name']} to observe {site['phenomena']}."
        action_details_for_chaining = {
            "action_on_arrival": "observe_phenomena",
            "duration_minutes_on_arrival": OBSERVE_PHENOMENA_DURATION_MINUTES,
            "title_on_arrival": activity_title,
            "description_on_arrival": activity_description,
            "thought_on_arrival": activity_thought,
            "priority_on_arrival": 55,
            "notes_for_chained_activity": observation_notes
        }
        
        # Create goto_position activity
        goto_activity = try_create_goto_position_activity(
            tables=tables,
            citizen_record=citizen_record,
            destination_position=site['position'],
            destination_name=site['name'],
            citizen_position=citizen_position,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            notes=goto_notes_str,
            details_payload=action_details_for_chaining,
            start_time_utc_iso=start_time_utc_iso
        )
        
        if goto_activity:
            log.info(f"{LogColors.OKGREEN}[Observe Phenomena] {citizen_name_log}: 'goto_position' activity created to {site['name']}. Observation will be chained.{LogColors.ENDC}")
            return goto_activity
        else:
            log.warning(f"{LogColors.WARNING}[Observe Phenomena] {citizen_name_log}: Failed to create 'goto_position' to {site['name']}.{LogColors.ENDC}")
            return None
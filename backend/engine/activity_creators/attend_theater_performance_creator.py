import logging
import json
import uuid
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_closest_building_of_type,
    _get_building_position_coords,
    _calculate_distance_meters,
    get_path_between_points,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

THEATER_PERFORMANCE_DURATION_HOURS = 1.0

# Prices and influence based on social class
THEATER_COSTS = {
    "Facchini": 100,
    "Popolani": 200,
    "Cittadini": 500,
    "Nobili": 1000,
    "Forestieri": 700,
    "Artisti": 300 # Assuming Artisti might get a slight discount or have their own rate
}
THEATER_INFLUENCE_GAIN = {
    "Facchini": 1,
    "Popolani": 2,
    "Cittadini": 5,
    "Nobili": 10,
    "Forestieri": 7,
    "Artisti": 4 # Assuming Artisti gain moderate influence
}

DEFAULT_THEATER_COST = 200
DEFAULT_THEATER_INFLUENCE = 2

def try_create_attend_theater_performance_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    resource_defs: Dict[str, Any], # Added
    building_type_defs: Dict[str, Any], # Added
    now_venice_dt: datetime, # Added
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str, # Added
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates an 'attend_theater_performance' activity chain.
    1. Find the nearest 'theater' building.
    2. If not at the theater, create 'goto_location' to the theater.
    3. Create 'attend_theater_performance' activity at the theater.
    Returns the first activity in the chain.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_social_class = citizen_record['fields'].get('SocialClass', 'Popolani')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Théâtre] {citizen_name_log} n'a pas de position. Impossible de créer 'attend_theater_performance'.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.ACTIVITY}[Théâtre] Tentative de création d'activité pour {citizen_name_log} ({citizen_social_class}).{LogColors.ENDC}")

    theater_record = get_closest_building_of_type(tables, citizen_position, "theater")
    if not theater_record:
        log.info(f"{LogColors.OKBLUE}[Théâtre] {citizen_name_log}: Aucun théâtre trouvé à proximité.{LogColors.ENDC}")
        return None

    theater_custom_id = theater_record['fields'].get('BuildingId')
    theater_pos = _get_building_position_coords(theater_record)
    theater_name_display = theater_record['fields'].get('Name', theater_custom_id)

    if not theater_custom_id or not theater_pos:
        log.warning(f"{LogColors.WARNING}[Théâtre] {citizen_name_log}: Théâtre cible ({theater_name_display}) invalide. Impossible de créer l'activité.{LogColors.ENDC}")
        return None

    is_at_theater = _calculate_distance_meters(citizen_position, theater_pos) < 20

    cost = THEATER_COSTS.get(citizen_social_class, DEFAULT_THEATER_COST)
    influence_gain = THEATER_INFLUENCE_GAIN.get(citizen_social_class, DEFAULT_THEATER_INFLUENCE)

    activity_chain = []
    current_chain_time_iso = start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()

    if not is_at_theater:
        # path_to_theater is no longer needed here, goto_location_activity_creator handles pathfinding.
        
        goto_activity_params = {
            "targetBuildingId": theater_custom_id,
            "notes": f"Se rendant à {theater_name_display} pour assister à une représentation."
            # "fromBuildingId" could be added if starting from a specific building is desired,
            # otherwise current citizen position is used by goto_location_activity_creator.
        }

        goto_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            activity_params=goto_activity_params, # Pass parameters here
            resource_defs=resource_defs, # Pass through
            building_type_defs=building_type_defs, # Pass through
            now_venice_dt=now_venice_dt, # Pass through
            now_utc_dt=now_utc_dt, # Pass through
            transport_api_url=transport_api_url, # Pass through
            api_base_url=api_base_url, # Pass through
            # start_time_utc_iso is handled by the creator if needed for chaining,
            # but for the first goto, it's effectively current_chain_time_iso
        )
        if not goto_activity:
            log.warning(f"{LogColors.WARNING}[Théâtre] {citizen_name_log}: Échec de la création de 'goto_location' vers {theater_name_display}.{LogColors.ENDC}")
            return None
        activity_chain.append(goto_activity)
        current_chain_time_iso = goto_activity['fields']['EndDate']

    # Create attend_theater_performance activity
    performance_start_dt = dateutil_parser.isoparse(current_chain_time_iso.replace("Z", "+00:00"))
    if performance_start_dt.tzinfo is None:
        performance_start_dt = pytz.utc.localize(performance_start_dt)
    
    performance_end_dt = performance_start_dt + timedelta(hours=THEATER_PERFORMANCE_DURATION_HOURS)
    performance_end_time_iso = performance_end_dt.isoformat()

    activity_details_for_notes = {
        "theater_id": theater_custom_id,
        "theater_name": theater_name_display,
        "cost_expected": cost, # Store expected cost at creation time
        "influence_gain_expected": influence_gain, # Store expected influence at creation time
        "duration_hours": THEATER_PERFORMANCE_DURATION_HOURS
    }

    attend_performance_activity = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="attend_theater_performance",
        start_date_iso=current_chain_time_iso,
        end_date_iso=performance_end_time_iso,
        from_building_id=theater_custom_id,
        to_building_id=theater_custom_id,
        title=f"Assister à une représentation à {theater_name_display}",
        description=f"{citizen_name_log} assiste à une représentation au théâtre {theater_name_display}.",
        thought=f"Une soirée au théâtre ! J'espère que la pièce à {theater_name_display} sera divertissante.",
        details_json=json.dumps(activity_details_for_notes), # Utiliser details_json pour le JSON structuré
        priority_override=50 # Leisure activity priority
    )

    if not attend_performance_activity:
        log.error(f"{LogColors.FAIL}[Théâtre] {citizen_name_log}: Échec de la création de l'activité 'attend_theater_performance'.{LogColors.ENDC}")
        if activity_chain: # If goto was created, try to delete it
            try: tables['activities'].delete(activity_chain[0]['id'])
            except: pass
        return None
    
    activity_chain.append(attend_performance_activity)

    log.info(f"{LogColors.OKGREEN}[Théâtre] {citizen_name_log}: Chaîne d'activités 'aller au théâtre' créée. Première activité: {activity_chain[0]['fields']['Type']}.{LogColors.ENDC}")
    return activity_chain[0]

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
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

PUBLIC_BATH_DURATION_HOURS = 1.0

# Costs are primarily handled by the processor, but can be stored in notes for reference
PUBLIC_BATH_COSTS = {
    "Facchini": 25, "Popolani": 25, "Cittadini": 40,
    "Nobili": 100, "Forestieri": 40, "Artisti": 30
}
DEFAULT_PUBLIC_BATH_COST = 25
PUBLIC_BATH_INFLUENCE_GAIN = 5 # Influence gain is handled by processor

def try_create_use_public_bath_activity(
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
    Creates a 'use_public_bath' activity chain.
    1. Find the nearest 'public_bath' building.
    2. If not at the bath, create 'goto_location' to the bath.
    3. Create 'use_public_bath' activity at the bath.
    Returns the first activity in the chain.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_social_class = citizen_record['fields'].get('SocialClass', 'Popolani')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Bain Public] {citizen_name_log} n'a pas de position. Impossible de créer 'use_public_bath'.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.ACTIVITY}[Bain Public] Tentative de création d'activité pour {citizen_name_log} ({citizen_social_class}).{LogColors.ENDC}")

    public_bath_record = get_closest_building_of_type(tables, citizen_position, "public_bath")
    if not public_bath_record:
        log.info(f"{LogColors.OKBLUE}[Bain Public] {citizen_name_log}: Aucun bain public trouvé à proximité.{LogColors.ENDC}")
        return None

    public_bath_custom_id = public_bath_record['fields'].get('BuildingId')
    public_bath_pos = _get_building_position_coords(public_bath_record)
    public_bath_name_display = public_bath_record['fields'].get('Name', public_bath_custom_id)

    if not public_bath_custom_id or not public_bath_pos:
        log.warning(f"{LogColors.WARNING}[Bain Public] {citizen_name_log}: Bain public cible ({public_bath_name_display}) invalide. Impossible de créer l'activité.{LogColors.ENDC}")
        return None

    is_at_bath = _calculate_distance_meters(citizen_position, public_bath_pos) < 20

    cost_expected = PUBLIC_BATH_COSTS.get(citizen_social_class, DEFAULT_PUBLIC_BATH_COST)
    
    # Check affordability before creating travel activity
    current_ducats = float(citizen_record['fields'].get('Ducats', 0.0))
    if current_ducats < cost_expected:
        log.warning(f"{LogColors.WARNING}[Bain Public] {citizen_name_log} n'a pas assez de Ducats ({current_ducats:.2f}) pour le bain public (coût estimé: {cost_expected:.2f}). Abandon.{LogColors.ENDC}")
        return None

    activity_chain = []
    current_chain_time_iso = start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()

    if not is_at_bath:
        goto_activity_params = {
            "targetBuildingId": public_bath_custom_id,
            "notes": f"Se rendant à {public_bath_name_display} pour prendre un bain."
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
            log.warning(f"{LogColors.WARNING}[Bain Public] {citizen_name_log}: Échec de la création de 'goto_location' vers {public_bath_name_display}.{LogColors.ENDC}")
            return None
        activity_chain.append(goto_activity)
        current_chain_time_iso = goto_activity['fields']['EndDate']

    # Create use_public_bath activity
    bath_start_dt = dateutil_parser.isoparse(current_chain_time_iso.replace("Z", "+00:00"))
    if bath_start_dt.tzinfo is None:
        bath_start_dt = pytz.utc.localize(bath_start_dt)
    
    bath_end_dt = bath_start_dt + timedelta(hours=PUBLIC_BATH_DURATION_HOURS)
    bath_end_time_iso = bath_end_dt.isoformat()

    activity_details_for_notes = {
        "public_bath_id": public_bath_custom_id,
        "public_bath_name": public_bath_name_display,
        "cost_expected": cost_expected,
        "influence_gain_expected": PUBLIC_BATH_INFLUENCE_GAIN,
        "duration_hours": PUBLIC_BATH_DURATION_HOURS
    }

    use_bath_activity = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="use_public_bath",
        start_date_iso=current_chain_time_iso,
        end_date_iso=bath_end_time_iso,
        from_building_id=public_bath_custom_id, # At the bath
        to_building_id=public_bath_custom_id,   # Stays at the bath
        title=f"Prendre un bain à {public_bath_name_display}",
        description=f"{citizen_name_log} prend un bain et socialise à {public_bath_name_display}.",
        thought=f"Un bon bain chaud à {public_bath_name_display} sera relaxant. Peut-être y verrai-je des connaissances.",
        details_json=json.dumps(activity_details_for_notes),
        priority_override=45 # Leisure activity, slightly higher than general shopping
    )

    if not use_bath_activity:
        log.error(f"{LogColors.FAIL}[Bain Public] {citizen_name_log}: Échec de la création de l'activité 'use_public_bath'.{LogColors.ENDC}")
        if activity_chain: # If goto was created, try to delete it
            try: tables['activities'].delete(activity_chain[0]['id'])
            except: pass
        return None
    
    activity_chain.append(use_bath_activity)

    log.info(f"{LogColors.OKGREEN}[Bain Public] {citizen_name_log}: Chaîne d'activités 'utiliser bain public' créée. Première activité: {activity_chain[0]['fields']['Type']}.{LogColors.ENDC}")
    return activity_chain[0]

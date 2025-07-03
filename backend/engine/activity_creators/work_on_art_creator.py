import logging
import json
from datetime import datetime, timedelta
import pytz # Keep pytz for timezone operations
from typing import Dict, Optional, Any, List # Added List

from pyairtable import Table # Import Table for type hinting

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_home,
    get_closest_building_of_type,
    _get_building_position_coords,
    _calculate_distance_meters,
    # get_path_between_points, # No longer called directly here
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser # For robust date parsing
)
# Import directly from the specific module to avoid circular import
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

WORK_ON_ART_DURATION_HOURS = 1.0

def try_create_work_on_art_activity(
    tables: Dict[str, Table],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str, # New parameter
    start_time_utc_iso: Optional[str] = None # For chaining
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'work_on_art' activity for an Artisti citizen.
    The citizen will go to their home or the nearest art_gallery.
    If travel is needed, a 'goto_location' activity is created first.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_airtable_id = citizen_record['id'] # Not directly used by create_activity_record but good to have
    citizen_custom_id = citizen_record['fields'].get('CitizenId') # Used by create_activity_record
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Artiste Travail] {citizen_name_log} n'a pas de position. Impossible de créer 'work_on_art'.{LogColors.ENDC}")
        return None

    target_location_record: Optional[Dict[str, Any]] = None
    target_location_type: Optional[str] = None
    
    art_gallery_record = get_closest_building_of_type(tables, citizen_position, "art_gallery")
    
    if art_gallery_record:
        target_location_record = art_gallery_record
        target_location_type = "art_gallery"
    else:
        home_record = get_citizen_home(tables, citizen_username)
        if home_record:
            target_location_record = home_record
            target_location_type = "home"
        else:
            log.warning(f"{LogColors.WARNING}[Artiste Travail] {citizen_name_log} n'a ni académie d'art proche ni domicile. Impossible de créer 'work_on_art'.{LogColors.ENDC}")
            return None

    target_location_custom_id = target_location_record['fields'].get('BuildingId')
    target_location_pos = _get_building_position_coords(target_location_record)
    target_location_name_display = target_location_record['fields'].get('Name', target_location_custom_id)

    if not target_location_custom_id or not target_location_pos:
        log.warning(f"{LogColors.WARNING}[Artiste Travail] {citizen_name_log}: Lieu cible ({target_location_type}) invalide. Impossible de créer 'work_on_art'.{LogColors.ENDC}")
        return None

    is_at_target_location = _calculate_distance_meters(citizen_position, target_location_pos) < 20

    # Determine start and end times for work_on_art
    # If travel is needed, work_on_art_start_time will be after travel.
    # If no travel, it starts based on start_time_utc_iso or now_utc_dt.
    
    work_art_start_time_iso: str
    
    # Activity chain will be built here
    activities_created: List[Dict[str, Any]] = []

    activity_title = f"Travailler sur une œuvre d'art à {target_location_name_display}"
    activity_description = f"{citizen_name_log} se consacre à son art à {target_location_name_display}."
    activity_thought = f"Je vais passer {WORK_ON_ART_DURATION_HOURS} heure(s) à travailler sur mon art ici, à {target_location_name_display}."

    if is_at_target_location:
        log.info(f"{LogColors.OKBLUE}[Artiste Travail] {citizen_name_log} est déjà à {target_location_name_display}. Création de 'work_on_art'.{LogColors.ENDC}")
        work_art_start_time_iso = start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()
    else:
        log.info(f"{LogColors.OKBLUE}[Artiste Travail] {citizen_name_log} doit se rendre à {target_location_name_display}. Création de 'goto_location' d'abord.{LogColors.ENDC}")
        # path_to_target is no longer calculated here; goto_location_activity_creator will handle it.

        goto_notes = f"Se rendant à {target_location_name_display} pour travailler sur son art."
        
        # Prepare parameters for try_create_goto_location_activity
        activity_params_for_goto = {
            'targetBuildingId': target_location_custom_id,
            'notes': goto_notes,
            # 'fromBuildingId' can be omitted; goto_location_creator will use citizen's current position.
            # 'details' can be omitted if no specific chained activity data is needed beyond notes.
            'start_time_utc_iso': start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()
        }
        
        now_venice_dt = now_utc_dt.astimezone(VENICE_TIMEZONE)

        # Create goto_location activity
        goto_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            activity_params=activity_params_for_goto,
            resource_defs={},  # Not used by goto_location
            building_type_defs={},  # Not used by goto_location
            now_venice_dt=now_venice_dt,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url
        )
        
        if not goto_activity:
            log.warning(f"{LogColors.WARNING}[Artiste Travail] {citizen_name_log}: Échec de la création de 'goto_location' vers {target_location_name_display}.{LogColors.ENDC}")
            return None
        
        activities_created.append(goto_activity)
        # The work_on_art activity will start after the goto_location activity ends.
        work_art_start_time_iso = goto_activity['fields']['EndDate']

    # Calculate end time for work_on_art based on its determined start time
    work_art_start_dt = dateutil_parser.isoparse(work_art_start_time_iso.replace("Z", "+00:00"))
    if work_art_start_dt.tzinfo is None:
        work_art_start_dt = pytz.utc.localize(work_art_start_dt)
    work_art_end_time_dt = work_art_start_dt + timedelta(hours=WORK_ON_ART_DURATION_HOURS)
    work_art_end_time_iso = work_art_end_time_dt.isoformat()

    # Create work_on_art activity
    work_art_activity = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="work_on_art",
        start_date_iso=work_art_start_time_iso,
        end_date_iso=work_art_end_time_iso,
        from_building_id=target_location_custom_id,
        to_building_id=target_location_custom_id,
        title=activity_title,
        description=activity_description,
        thought=activity_thought,
        priority_override=35 
    )

    if not work_art_activity:
        log.error(f"{LogColors.FAIL}[Artiste Travail] {citizen_name_log}: Échec de la création de l'activité 'work_on_art'.{LogColors.ENDC}")
        # If goto was created but work_on_art failed, we might need to delete the goto activity.
        # For now, return None, indicating overall failure.
        if activities_created: # If goto was created
            try: tables['activities'].delete(activities_created[0]['id'])
            except: pass # Ignore error during cleanup
        return None
    
    activities_created.append(work_art_activity)
    
    if activities_created:
        log.info(f"{LogColors.OKGREEN}[Artiste Travail] {citizen_name_log}: Chaîne d'activités créée. Première activité: {activities_created[0]['fields']['Type']}.{LogColors.ENDC}")
        return activities_created[0] # Return the first activity of the chain
    else:
        # This case should ideally not be reached if logic is correct (e.g. direct work_on_art should always create one)
        log.error(f"{LogColors.FAIL}[Artiste Travail] {citizen_name_log}: Aucune activité créée pour work_on_art.{LogColors.ENDC}")
        return None

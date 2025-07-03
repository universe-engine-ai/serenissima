import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters, # Added import
    get_path_between_points,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

READ_BOOK_DURATION_MINUTES = 20

def try_create_read_book_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    book_resource_record: Dict[str, Any], # The specific book resource record
    now_utc_dt: datetime,
    transport_api_url: str,
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'read_book' activity or a chain starting with 'goto_location'.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    book_attributes_str = book_resource_record['fields'].get('Attributes')
    book_title = "a book"
    if book_attributes_str:
        try:
            book_attrs = json.loads(book_attributes_str)
            book_title = book_attrs.get('title', book_title)
        except json.JSONDecodeError:
            pass # Use default title

    book_asset_type = book_resource_record['fields'].get('AssetType')
    book_asset_id = book_resource_record['fields'].get('Asset') # BuildingId or Citizen Username

    target_location_custom_id: Optional[str] = None
    target_location_pos: Optional[Dict[str, float]] = None
    target_location_name_display: str = "their current location"

    is_at_book_location = False

    if book_asset_type == 'citizen' and book_asset_id == citizen_username:
        # Book is on the citizen, can read anywhere (or at current position)
        is_at_book_location = True
        target_location_custom_id = citizen_custom_id # Representing the citizen themselves as location
        target_location_pos = citizen_position
        target_location_name_display = "their current location"
        log.info(f"{LogColors.OKBLUE}[Lire Livre] {citizen_name_log} a le livre '{book_title}' sur lui/elle.{LogColors.ENDC}")
    elif book_asset_type == 'building':
        target_location_custom_id = book_asset_id
        book_building_record = get_building_record(tables, target_location_custom_id)
        if not book_building_record:
            log.warning(f"{LogColors.WARNING}[Lire Livre] {citizen_name_log}: Bâtiment du livre '{target_location_custom_id}' non trouvé.{LogColors.ENDC}")
            return None
        target_location_pos = _get_building_position_coords(book_building_record)
        target_location_name_display = book_building_record['fields'].get('Name', target_location_custom_id)
        if not target_location_pos:
            log.warning(f"{LogColors.WARNING}[Lire Livre] {citizen_name_log}: Bâtiment du livre '{target_location_name_display}' n'a pas de position.{LogColors.ENDC}")
            return None
        if citizen_position:
            is_at_book_location = _calculate_distance_meters(citizen_position, target_location_pos) < 20
        log.info(f"{LogColors.OKBLUE}[Lire Livre] {citizen_name_log}: Le livre '{book_title}' est à {target_location_name_display}. Est sur place: {is_at_book_location}.{LogColors.ENDC}")
    else:
        log.warning(f"{LogColors.WARNING}[Lire Livre] {citizen_name_log}: Type d'asset de livre inconnu '{book_asset_type}' ou ID d'asset '{book_asset_id}'.{LogColors.ENDC}")
        return None

    effective_start_time_for_read_dt = dateutil_parser.isoparse(start_time_utc_iso) if start_time_utc_iso else now_utc_dt
    if effective_start_time_for_read_dt.tzinfo is None:
        effective_start_time_for_read_dt = pytz.utc.localize(effective_start_time_for_read_dt)
        
    read_book_end_time_dt = effective_start_time_for_read_dt + timedelta(minutes=READ_BOOK_DURATION_MINUTES)
    read_book_end_time_iso = read_book_end_time_dt.isoformat()

    activity_title = f"Lire '{book_title}'"
    activity_description = f"{citizen_name_log} lit '{book_title}' à {target_location_name_display}."
    activity_thought = f"Je vais prendre un moment pour lire '{book_title}'."
    
    # Notes for the read_book activity itself
    # Parse book attributes to get both kinos_path and content_path
    book_attrs = {}
    if book_attributes_str:
        try:
            if isinstance(book_attributes_str, dict):
                book_attrs = book_attributes_str
            else:
                book_attrs = json.loads(book_attributes_str)
        except json.JSONDecodeError:
            pass
    
    read_book_notes = {
        "book_resource_id": book_resource_record['fields'].get('ResourceId'),
        "book_title": book_title,
        "location_type": book_asset_type,
        "location_id": book_asset_id
    }
    
    # Add kinos_path if it exists
    if book_attrs.get('kinos_path'):
        read_book_notes["book_kinos_path"] = book_attrs['kinos_path']
    
    # Add content_path if it exists (for local books like distributed manuscripts)
    if book_attrs.get('content_path'):
        read_book_notes["content_path"] = book_attrs['content_path']
    
    # Add local_path if it exists (for books from public/books directory)
    if book_attrs.get('local_path'):
        read_book_notes["book_local_path"] = book_attrs['local_path']


    if is_at_book_location:
        log.info(f"{LogColors.OKBLUE}[Lire Livre] {citizen_name_log} est à l'emplacement du livre. Création de 'read_book'.{LogColors.ENDC}")
        return create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type="read_book",
            start_date_iso=start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat(),
            end_date_iso=read_book_end_time_iso,
            from_building_id=target_location_custom_id if book_asset_type == 'building' else None,
            to_building_id=target_location_custom_id if book_asset_type == 'building' else None,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(read_book_notes),
            priority_override=55 
        )
    else:
        # Need to travel to the book's location (if it's a building)
        if not citizen_position or not target_location_pos or not target_location_custom_id:
             log.warning(f"{LogColors.WARNING}[Lire Livre] {citizen_name_log}: Données de position manquantes pour le déplacement.{LogColors.ENDC}")
             return None

        log.info(f"{LogColors.OKBLUE}[Lire Livre] {citizen_name_log} doit se rendre à {target_location_name_display}. Création de 'goto_location'.{LogColors.ENDC}")
        path_to_target = get_path_between_points(citizen_position, target_location_pos, transport_api_url)
        if not (path_to_target and path_to_target.get('success')):
            log.warning(f"{LogColors.WARNING}[Lire Livre] {citizen_name_log}: Impossible de trouver un chemin vers {target_location_name_display}.{LogColors.ENDC}")
            return None

        goto_notes_str = f"Se rendant à {target_location_name_display} pour lire '{book_title}'."
        action_details_for_chaining = {
            "action_on_arrival": "read_book",
            "duration_minutes_on_arrival": READ_BOOK_DURATION_MINUTES,
            "original_target_building_id_on_arrival": target_location_custom_id, # The building where the book is
            "title_on_arrival": activity_title,
            "description_on_arrival": activity_description,
            "thought_on_arrival": activity_thought,
            "priority_on_arrival": 55,
            "notes_for_chained_activity": read_book_notes # Pass notes for the read_book activity
        }
        
        goto_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            destination_building_id=target_location_custom_id,
            path_data=path_to_target,
            current_time_utc=now_utc_dt,
            notes=goto_notes_str,
            details_payload=action_details_for_chaining,
            start_time_utc_iso=start_time_utc_iso # This is for the goto_location itself
        )
        
        if goto_activity:
            log.info(f"{LogColors.OKGREEN}[Lire Livre] {citizen_name_log}: Activité 'goto_location' créée vers {target_location_name_display}. 'read_book' sera chaînée.{LogColors.ENDC}")
            return goto_activity
        else:
            log.warning(f"{LogColors.WARNING}[Lire Livre] {citizen_name_log}: Échec de la création de 'goto_location' vers {target_location_name_display}.{LogColors.ENDC}")
            return None

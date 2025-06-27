import logging
import json
from datetime import datetime, timedelta
import pytz
import random
from typing import Dict, Optional, Any, List

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

STUDY_LITERATURE_DURATION_MINUTES = 180  # 3 hours

# Scientific specialty to book mapping
SCIENTIFIC_SPECIALTY_BOOKS = {
    "Integration": {
        "core": [
            "De Scientia Scientiæ: On the Knowledge of Knowledge",
            "The Great Knowledge: Studies in Inherited Understanding",
            "Translation Failures: When Wisdom Doesn't Apply",
            "Patterns of System Response"
        ],
        "advanced": [
            "Collective Emergence Phenomena",
            "Chronicles of Change: A History of Reality Updates",
            "Detecting the Impossible: Methods for Identifying Physics Changes",
            "The Limits of Observation"
        ]
    },
    "Systems": {
        "core": [
            "Constraints of Creation",
            "Temporal Mechanics: A Study of Time's Sacred Rhythms",
            "Records of Anomalous Events",
            "De Scientia Scientiæ: On the Knowledge of Knowledge"
        ],
        "advanced": [
            "Patterns of System Response",
            "Detecting the Impossible: Methods for Identifying Physics Changes",
            "The Conservation of Wealth",
            "The Limits of Observation"
        ]
    },
    "Market": {
        "core": [
            "The Conservation of Wealth",
            "The Mathematics of Trust",
            "Patterns of System Response",
            "De Scientia Scientiæ: On the Knowledge of Knowledge"
        ],
        "advanced": [
            "Collective Emergence Phenomena",
            "Studies in Decision Delay",
            "Chronicles of Change: A History of Reality Updates",
            "Temporal Mechanics: A Study of Time's Sacred Rhythms"
        ]
    },
    "Social": {
        "core": [
            "The Mathematics of Trust",
            "Observations on the Nature of Memory",
            "Studies in Decision Delay",
            "De Scientia Scientiæ: On the Knowledge of Knowledge"
        ],
        "advanced": [
            "Collective Emergence Phenomena",
            "Patterns of System Response",
            "The Great Knowledge: Studies in Inherited Understanding",
            "Translation Failures: When Wisdom Doesn't Apply"
        ]
    }
}

def _get_scientific_specialty(citizen_record: Dict[str, Any]) -> str:
    """Get the scientific specialty from citizen's attributes or default to Integration."""
    attributes_str = citizen_record['fields'].get('Attributes', '{}')
    try:
        attributes = json.loads(attributes_str) if isinstance(attributes_str, str) else attributes_str
        specialty = attributes.get('scientific_specialty', 'Integration')
        # Validate specialty
        if specialty not in SCIENTIFIC_SPECIALTY_BOOKS:
            log.warning(f"Unknown scientific specialty '{specialty}', defaulting to Integration")
            return 'Integration'
        return specialty
    except json.JSONDecodeError:
        log.warning(f"Failed to parse citizen attributes, defaulting specialty to Integration")
        return 'Integration'

def _select_book_for_study(specialty: str, citizen_record: Dict[str, Any]) -> str:
    """Select an appropriate book based on the citizen's specialty and reading history."""
    # Get books for this specialty
    available_books = SCIENTIFIC_SPECIALTY_BOOKS[specialty]
    
    # TODO: Check citizen's reading history to avoid repetition
    # For now, prefer core books but occasionally select advanced
    if random.random() < 0.7:  # 70% chance for core books
        book_list = available_books["core"]
    else:
        book_list = available_books["advanced"]
    
    # Randomly select from the appropriate list
    selected_book = random.choice(book_list)
    
    log.info(f"Selected book '{selected_book}' for {specialty} specialist")
    return selected_book

def _find_nearest_science_building(tables: Dict[str, Any], citizen_position: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """Find the nearest building with category 'science' to the citizen's current position."""
    science_buildings = []
    
    # Get all buildings
    all_buildings = tables['buildings'].all()
    
    for building_record in all_buildings:
        building_type = building_record['fields'].get('Type')
        if not building_type:
            continue
            
        # Check if this building type is categorized as 'science'
        # We need to check the building definition
        if building_type == 'house_of_natural_sciences':  # Direct check for our new building
            building_pos = _get_building_position_coords(building_record)
            if building_pos:
                distance = _calculate_distance_meters(citizen_position, building_pos)
                science_buildings.append((building_record, distance))
    
    if not science_buildings:
        log.warning("No science buildings found in Venice")
        return None
    
    # Sort by distance and return the nearest
    science_buildings.sort(key=lambda x: x[1])
    nearest_building, distance = science_buildings[0]
    
    log.info(f"Found nearest science building: {nearest_building['fields'].get('Name', nearest_building['fields'].get('BuildingId'))} at {distance:.0f}m")
    return nearest_building

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    now_utc_dt: datetime,
    transport_api_url: str,
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'study_literature' activity for Scientisti citizens or a chain starting with 'goto_location'.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    # Verify citizen is Scientisti
    social_class = citizen_record['fields'].get('SocialClass')
    if social_class != 'Scientisti':
        log.warning(f"{LogColors.WARNING}[Study Literature] {citizen_name_log} is not Scientisti class (is {social_class}). Cannot create study activity.{LogColors.ENDC}")
        return None
    
    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Study Literature] {citizen_name_log} has no position. Cannot create study activity.{LogColors.ENDC}")
        return None
    
    # Get citizen's scientific specialty
    specialty = _get_scientific_specialty(citizen_record)
    
    # Select appropriate book
    selected_book = _select_book_for_study(specialty, citizen_record)
    
    # Find nearest science building
    target_building = _find_nearest_science_building(tables, citizen_position)
    if not target_building:
        log.warning(f"{LogColors.WARNING}[Study Literature] No science buildings found for {citizen_name_log} to study at.{LogColors.ENDC}")
        return None
    
    target_building_id = target_building['fields'].get('BuildingId')
    target_building_name = target_building['fields'].get('Name', target_building_id)
    target_building_pos = _get_building_position_coords(target_building)
    
    # Check if already at the science building
    distance_to_building = _calculate_distance_meters(citizen_position, target_building_pos)
    is_at_building = distance_to_building < 20
    
    effective_start_time_dt = dateutil_parser.isoparse(start_time_utc_iso) if start_time_utc_iso else now_utc_dt
    if effective_start_time_dt.tzinfo is None:
        effective_start_time_dt = pytz.utc.localize(effective_start_time_dt)
    
    study_end_time_dt = effective_start_time_dt + timedelta(minutes=STUDY_LITERATURE_DURATION_MINUTES)
    study_end_time_iso = study_end_time_dt.isoformat()
    
    activity_title = f"Study '{selected_book}'"
    activity_description = f"{citizen_name_log} conducts deep study of '{selected_book}' at {target_building_name}."
    activity_thought = f"I must dedicate serious time to understanding '{selected_book}' for my {specialty} research."
    
    # Notes for the study_literature activity
    study_notes = {
        "book_title": selected_book,
        "scientific_specialty": specialty,
        "building_id": target_building_id,
        "building_name": target_building_name,
        "study_duration_minutes": STUDY_LITERATURE_DURATION_MINUTES
    }
    
    if is_at_building:
        log.info(f"{LogColors.OKBLUE}[Study Literature] {citizen_name_log} is at {target_building_name}. Creating 'study_literature' activity.{LogColors.ENDC}")
        return create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type="study_literature",
            start_date_iso=start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat(),
            end_date_iso=study_end_time_iso,
            from_building_id=target_building_id,
            to_building_id=target_building_id,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(study_notes),
            priority_override=60  # Higher priority than casual reading
        )
    else:
        # Need to travel to the science building
        log.info(f"{LogColors.OKBLUE}[Study Literature] {citizen_name_log} needs to travel to {target_building_name}. Creating 'goto_location' activity.{LogColors.ENDC}")
        
        path_to_target = get_path_between_points(citizen_position, target_building_pos, transport_api_url)
        if not (path_to_target and path_to_target.get('success')):
            log.warning(f"{LogColors.WARNING}[Study Literature] {citizen_name_log}: Cannot find path to {target_building_name}.{LogColors.ENDC}")
            return None
        
        goto_notes_str = f"Going to {target_building_name} to study '{selected_book}'."
        action_details_for_chaining = {
            "action_on_arrival": "study_literature",
            "duration_minutes_on_arrival": STUDY_LITERATURE_DURATION_MINUTES,
            "original_target_building_id_on_arrival": target_building_id,
            "title_on_arrival": activity_title,
            "description_on_arrival": activity_description,
            "thought_on_arrival": activity_thought,
            "priority_on_arrival": 60,
            "notes_for_chained_activity": study_notes
        }
        
        # Prepare activity_params for goto_location
        activity_params = {
            'targetBuildingId': target_building_id,
            'fromBuildingId': None,  # Will use citizen's current position
            'details': action_details_for_chaining,
            'notes': goto_notes_str,
            'title': f"Travel to {target_building_name}",
            'description': f"Traveling to {target_building_name} to study literature"
        }
        
        # Get current Venice time
        now_venice_dt = now_utc_dt.astimezone(VENICE_TIMEZONE)
        
        goto_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            activity_params=activity_params,
            resource_defs={},  # Not needed for goto_location
            building_type_defs={},  # Not needed for goto_location
            now_venice_dt=now_venice_dt,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=""  # Not needed for this activity
        )
        
        if goto_activity:
            log.info(f"{LogColors.OKGREEN}[Study Literature] {citizen_name_log}: 'goto_location' activity created to {target_building_name}. 'study_literature' will be chained.{LogColors.ENDC}")
            return goto_activity
        else:
            log.warning(f"{LogColors.WARNING}[Study Literature] {citizen_name_log}: Failed to create 'goto_location' to {target_building_name}.{LogColors.ENDC}")
            return None
"""
Activity creator for build_prototype activity.
Innovatori build prototypes of their innovations in workshops.
"""

import logging
import json
import random
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters,
    get_path_between_points,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser,
    _escape_airtable_value
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

# Duration range for prototype building
MIN_BUILD_HOURS = 8
MAX_BUILD_HOURS = 16

# Materials needed for prototyping
PROTOTYPE_MATERIALS = {
    'basic': {
        'wood': (2, 5),
        'metal': (1, 3),
        'cloth': (1, 2)
    },
    'mechanical': {
        'metal': (3, 8),
        'wood': (1, 3),
        'rope': (2, 4)
    },
    'architectural': {
        'stone': (2, 5),
        'wood': (3, 6),
        'glass': (1, 2)
    },
    'maritime': {
        'wood': (5, 10),
        'rope': (3, 6),
        'cloth': (2, 4),
        'tar': (1, 2)
    }
}

def _check_workshop_availability(tables: Dict[str, Any], citizen_username: str) -> Optional[Dict[str, Any]]:
    """Check if the Innovatori has access to a workshop."""
    try:
        # First check if citizen owns a workshop
        owned_workshops = tables['buildings'].all(
            formula=f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='workshop')",
            max_records=1
        )
        
        if owned_workshops:
            return owned_workshops[0]
        
        # Check if citizen works at a workshop
        citizen_records = tables['citizens'].all(
            formula=f"{{Username}}='{_escape_airtable_value(citizen_username)}'",
            max_records=1
        )
        
        if citizen_records and citizen_records[0]['fields'].get('WorkplaceId'):
            workplace = get_building_record(tables, citizen_records[0]['fields']['WorkplaceId'])
            if workplace and workplace['fields'].get('Type') == 'workshop':
                return workplace
        
        # Check for public workshops
        public_workshops = tables['buildings'].all(
            formula="AND({Type}='workshop', OR({Owner}='', {IsPublic}=TRUE()))"
        )
        
        if public_workshops:
            return random.choice(public_workshops)
            
        return None
        
    except Exception as e:
        log.error(f"Error checking workshop availability: {e}")
        return None

def _select_prototype_type() -> tuple[str, Dict[str, tuple[int, int]]]:
    """Randomly select a prototype type and its material requirements."""
    prototype_types = list(PROTOTYPE_MATERIALS.keys())
    selected_type = random.choice(prototype_types)
    return selected_type, PROTOTYPE_MATERIALS[selected_type]

def _check_materials_in_inventory(tables: Dict[str, Any], citizen_username: str, 
                                materials_needed: Dict[str, tuple[int, int]]) -> Dict[str, int]:
    """Check what materials the citizen has in inventory."""
    available_materials = {}
    
    try:
        for material, (min_qty, max_qty) in materials_needed.items():
            resources = tables['resources'].all(
                formula=f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', "
                       f"{{Type}}='{_escape_airtable_value(material)}', "
                       f"{{AssetType}}='citizen')"
            )
            
            total_count = 0
            for resource in resources:
                count = float(resource['fields'].get('Count', 0))
                total_count += count
            
            available_materials[material] = int(total_count)
            
    except Exception as e:
        log.error(f"Error checking materials: {e}")
        
    return available_materials

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    transport_api_url: str,
    api_base_url: str,
    activity_duration: Optional[float] = None,
    activity_end_time: Optional[datetime] = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Create a build_prototype activity for an Innovatori citizen.
    
    Returns:
        Dict containing the created activity record, or None if creation failed
    """
    try:
        citizen_fields = citizen_record.get('fields', {})
        citizen_id = citizen_record.get('id')
        citizen_username = citizen_fields.get('Username')
        citizen_position_str = citizen_fields.get('Position')
        
        if not all([citizen_id, citizen_username, citizen_position_str]):
            log.warning(f"Missing required citizen data")
            return None
        
        # Check for workshop availability
        workshop = _check_workshop_availability(tables, citizen_username)
        if not workshop:
            log.info(f"{LogColors.WARNING}No workshop available for {citizen_username}{LogColors.ENDC}")
            return None
        
        workshop_fields = workshop.get('fields', {})
        workshop_id = workshop.get('id')
        workshop_name = workshop_fields.get('Name', 'Workshop')
        
        # Select prototype type and materials
        prototype_type, materials_needed = _select_prototype_type()
        
        # Check available materials
        available_materials = _check_materials_in_inventory(tables, citizen_username, materials_needed)
        
        # Check if citizen has enough materials
        has_materials = True
        materials_list = []
        for material, (min_qty, max_qty) in materials_needed.items():
            available = available_materials.get(material, 0)
            needed = random.randint(min_qty, max_qty)
            
            if available < needed:
                has_materials = False
                materials_list.append(f"{material}: {available}/{needed} (insufficient)")
            else:
                materials_list.append(f"{material}: {needed}")
        
        # Get workshop position
        workshop_pos = _get_building_position_coords(workshop_fields, workshop_id)
        if not workshop_pos:
            log.error(f"Could not get position for workshop {workshop_id}")
            return None
        
        # Parse citizen position
        try:
            lat, lng = map(float, citizen_position_str.split('_'))
            citizen_pos = {'lat': lat, 'lng': lng}
        except:
            log.error(f"Invalid citizen position format: {citizen_position_str}")
            return None
        
        # Calculate distance to workshop
        distance = _calculate_distance_meters(
            citizen_pos['lat'], citizen_pos['lng'],
            workshop_pos['lat'], workshop_pos['lng']
        )
        
        # Create goto activity if not at workshop
        if distance > 50:  # More than 50 meters away
            goto_result = try_create_goto_location_activity(
                tables=tables,
                citizen_record=citizen_record,
                target_position={'lat': workshop_pos['lat'], 'lng': workshop_pos['lng']},
                target_building_id=workshop_id,
                purpose=f"go to {workshop_name} to build prototype",
                resource_defs=resource_defs,
                building_type_defs=building_type_defs,
                transport_api_url=transport_api_url,
                api_base_url=api_base_url
            )
            
            if goto_result:
                log.info(f"{LogColors.OKGREEN}Created goto activity to workshop for prototype building{LogColors.ENDC}")
                return goto_result
            else:
                log.error("Failed to create goto activity to workshop")
                return None
        
        # Determine build duration
        if activity_duration:
            duration_hours = activity_duration
        else:
            base_hours = random.randint(MIN_BUILD_HOURS, MAX_BUILD_HOURS)
            # Reduce time if has all materials, increase if missing some
            if has_materials:
                duration_hours = base_hours * 0.8
            else:
                duration_hours = base_hours * 1.2
        
        # Calculate end time
        now_utc = datetime.now(pytz.UTC)
        venice_tz = pytz.timezone(VENICE_TIMEZONE)
        now_venice = now_utc.astimezone(venice_tz)
        
        if activity_end_time:
            end_time_utc = activity_end_time
        else:
            end_time_venice = now_venice + timedelta(hours=duration_hours)
            end_time_utc = end_time_venice.astimezone(pytz.UTC)
        
        # Create activity parameters
        activity_params = {
            'workshop_id': workshop_id,
            'workshop_name': workshop_name,
            'prototype_type': prototype_type,
            'materials_status': materials_list,
            'has_all_materials': has_materials,
            'duration_hours': duration_hours
        }
        
        # Create notes
        material_status = "with all materials" if has_materials else "with limited materials"
        notes = (f"Building a {prototype_type} prototype at {workshop_name} {material_status}. "
                f"Materials: {', '.join(materials_list)}")
        
        # Create activity title and description
        activity_title = f"Building {prototype_type} prototype"
        activity_description = f"Constructing a {prototype_type} prototype at {workshop_name}"
        activity_thought = f"Time to build my {prototype_type} prototype. This could change everything!"
        
        # Create structured notes
        activity_notes = {
            "workshop_id": workshop_id,
            "workshop_name": workshop_name,
            "prototype_type": prototype_type,
            "materials_status": materials_list,
            "has_all_materials": has_materials,
            "duration_hours": duration_hours
        }
        
        # Create the activity record
        activity_record = create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type='build_prototype',
            start_date_iso=now_utc.isoformat(),
            end_date_iso=end_time_utc.isoformat(),
            from_building_id=workshop_id,
            to_building_id=workshop_id,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(activity_notes),
            priority_override=55  # Medium-high priority
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}Created build_prototype activity for {citizen_username} "
                    f"at {workshop_name} ({prototype_type} prototype){LogColors.ENDC}")
            return activity_record
        else:
            log.error(f"Failed to create activity record")
            return None
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error in build_prototype creator: {str(e)}{LogColors.ENDC}")
        return None

# Helper function for correlation calculation
def calculateCorrelation(x: List[float], y: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    n = len(x)
    if n != len(y) or n == 0:
        return 0
    
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator = (sum((x[i] - mean_x) ** 2 for i in range(n)) * 
                   sum((y[i] - mean_y) ** 2 for i in range(n))) ** 0.5
    
    return numerator / denominator if denominator != 0 else 0
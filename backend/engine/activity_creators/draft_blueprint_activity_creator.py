"""
Activity creator for draft_blueprint activity.
Innovatori draft blueprints and formal documentation for their innovations.
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

# Duration range for blueprint drafting
MIN_DRAFT_HOURS = 6
MAX_DRAFT_HOURS = 12

# Blueprint types and their requirements
BLUEPRINT_TYPES = {
    'economic_system': {
        'name': 'Economic System Blueprint',
        'requires_research': True,
        'complexity': 'high',
        'materials': ['paper', 'ink']
    },
    'social_innovation': {
        'name': 'Social Innovation Blueprint', 
        'requires_research': True,
        'complexity': 'medium',
        'materials': ['paper', 'ink']
    },
    'infrastructure': {
        'name': 'Infrastructure Blueprint',
        'requires_research': False,
        'complexity': 'high',
        'materials': ['paper', 'ink', 'measuring_tools']
    },
    'process_improvement': {
        'name': 'Process Improvement Blueprint',
        'requires_research': False,
        'complexity': 'low',
        'materials': ['paper', 'ink']
    },
    'governance_reform': {
        'name': 'Governance Reform Blueprint',
        'requires_research': True,
        'complexity': 'very_high',
        'materials': ['paper', 'ink', 'seal']
    }
}

def _check_study_availability(tables: Dict[str, Any], citizen_username: str) -> Optional[Dict[str, Any]]:
    """Check if the Innovatori has access to a study or library for drafting."""
    try:
        # First check if citizen owns a study
        owned_studies = tables['buildings'].all(
            formula=f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', "
                   f"OR({{Type}}='private_study', {{Type}}='library'))",
            max_records=1
        )
        
        if owned_studies:
            return owned_studies[0]
        
        # Check for public libraries
        public_libraries = tables['buildings'].all(
            formula="AND({Type}='library', OR({Owner}='', {IsPublic}=TRUE()))"
        )
        
        if public_libraries:
            return random.choice(public_libraries)
        
        # Check for guild halls (Innovatori guild would have drafting space)
        guild_halls = tables['buildings'].all(
            formula="AND({Type}='guild_hall', {Status}='active')"
        )
        
        if guild_halls:
            return random.choice(guild_halls)
            
        return None
        
    except Exception as e:
        log.error(f"Error checking study availability: {e}")
        return None

def _select_blueprint_type(has_research_data: bool = False) -> tuple[str, Dict[str, Any]]:
    """Select a blueprint type based on context."""
    # Filter by research requirement if specified
    if has_research_data:
        valid_types = {k: v for k, v in BLUEPRINT_TYPES.items() if v['requires_research']}
    else:
        valid_types = BLUEPRINT_TYPES
    
    # Weight selection by complexity (simpler = more likely)
    weights = {
        'low': 4,
        'medium': 3,
        'high': 2,
        'very_high': 1
    }
    
    weighted_choices = []
    for type_key, type_info in valid_types.items():
        weight = weights.get(type_info['complexity'], 1)
        weighted_choices.extend([type_key] * weight)
    
    selected_type = random.choice(weighted_choices)
    return selected_type, BLUEPRINT_TYPES[selected_type]

def _check_materials_available(tables: Dict[str, Any], citizen_username: str,
                             required_materials: List[str]) -> Dict[str, bool]:
    """Check which required materials are available."""
    material_status = {}
    
    try:
        for material in required_materials:
            # Special handling for common materials
            if material in ['paper', 'ink']:
                # Assume these are always available at a study/library
                material_status[material] = True
            else:
                # Check inventory for special materials
                resources = tables['resources'].all(
                    formula=f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', "
                           f"{{Type}}='{_escape_airtable_value(material)}', "
                           f"{{AssetType}}='citizen')",
                    max_records=1
                )
                material_status[material] = len(resources) > 0
                
    except Exception as e:
        log.error(f"Error checking materials: {e}")
        # Default to assuming basic materials are available
        for material in required_materials:
            material_status[material] = material in ['paper', 'ink']
            
    return material_status

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
    Create a draft_blueprint activity for an Innovatori citizen.
    
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
        
        # Check for study/library availability
        study_location = _check_study_availability(tables, citizen_username)
        if not study_location:
            log.info(f"{LogColors.WARNING}No study or library available for {citizen_username}{LogColors.ENDC}")
            return None
        
        study_fields = study_location.get('fields', {})
        study_id = study_location.get('id')
        study_name = study_fields.get('Name', 'Study')
        study_type = study_fields.get('Type', 'study')
        
        # Check if citizen has recent research data (from completed activities)
        has_research = False
        try:
            recent_research_formula = (
                f"AND({{CitizenId}}='{citizen_id}', {{Status}}='completed', "
                f"OR({{Type}}='research_investigation', {{Type}}='test_innovation', "
                f"{{Type}}='observe_system_patterns'), "
                f"DATETIME_DIFF(NOW(), {{EndTime}}, 'days') < 7)"
            )
            recent_research = tables['activities'].all(
                formula=recent_research_formula,
                max_records=1
            )
            has_research = len(recent_research) > 0
        except:
            pass
        
        # Select blueprint type
        blueprint_type, blueprint_info = _select_blueprint_type(has_research)
        
        # Check materials
        material_status = _check_materials_available(
            tables, citizen_username, blueprint_info['materials']
        )
        has_all_materials = all(material_status.values())
        
        # Get study position
        study_pos = _get_building_position_coords(study_fields, study_id)
        if not study_pos:
            log.error(f"Could not get position for study {study_id}")
            return None
        
        # Parse citizen position
        try:
            lat, lng = map(float, citizen_position_str.split('_'))
            citizen_pos = {'lat': lat, 'lng': lng}
        except:
            log.error(f"Invalid citizen position format: {citizen_position_str}")
            return None
        
        # Calculate distance to study
        distance = _calculate_distance_meters(
            citizen_pos['lat'], citizen_pos['lng'],
            study_pos['lat'], study_pos['lng']
        )
        
        # Create goto activity if not at study
        if distance > 50:  # More than 50 meters away
            goto_result = try_create_goto_location_activity(
                tables=tables,
                citizen_record=citizen_record,
                target_position={'lat': study_pos['lat'], 'lng': study_pos['lng']},
                target_building_id=study_id,
                purpose=f"go to {study_name} to draft blueprint",
                resource_defs=resource_defs,
                building_type_defs=building_type_defs,
                transport_api_url=transport_api_url,
                api_base_url=api_base_url
            )
            
            if goto_result:
                log.info(f"{LogColors.OKGREEN}Created goto activity to study for blueprint drafting{LogColors.ENDC}")
                return goto_result
            else:
                log.error("Failed to create goto activity to study")
                return None
        
        # Determine drafting duration
        if activity_duration:
            duration_hours = activity_duration
        else:
            base_hours = random.randint(MIN_DRAFT_HOURS, MAX_DRAFT_HOURS)
            
            # Adjust based on complexity
            complexity_multipliers = {
                'low': 0.7,
                'medium': 1.0,
                'high': 1.3,
                'very_high': 1.6
            }
            multiplier = complexity_multipliers.get(blueprint_info['complexity'], 1.0)
            
            # Reduce time if has research data
            if has_research and blueprint_info['requires_research']:
                multiplier *= 0.8
                
            duration_hours = base_hours * multiplier
        
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
            'study_id': study_id,
            'study_name': study_name,
            'study_type': study_type,
            'blueprint_type': blueprint_type,
            'blueprint_name': blueprint_info['name'],
            'complexity': blueprint_info['complexity'],
            'has_research_data': has_research,
            'has_all_materials': has_all_materials,
            'material_status': material_status,
            'duration_hours': duration_hours
        }
        
        # Create notes
        research_note = "with research data" if has_research else "without prior research"
        materials_note = "with all materials" if has_all_materials else "with limited materials"
        notes = (f"Drafting {blueprint_info['name']} at {study_name} {research_note} {materials_note}. "
                f"Complexity: {blueprint_info['complexity']}")
        
        # Create activity title and description
        activity_title = f"Drafting {blueprint_info['name']}"
        activity_description = f"Creating formal documentation for {blueprint_type} innovation at {study_name}"
        activity_thought = f"Time to formalize my ideas into a blueprint. This {blueprint_info['name']} could transform Venice!"
        
        # Create structured notes  
        activity_notes = {
            "study_id": study_id,
            "study_name": study_name,
            "study_type": study_type,
            "blueprint_type": blueprint_type,
            "blueprint_name": blueprint_info['name'],
            "complexity": blueprint_info['complexity'],
            "has_research_data": has_research,
            "has_all_materials": has_all_materials,
            "material_status": material_status,
            "duration_hours": duration_hours
        }
        
        # Create the activity record
        activity_record = create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type='draft_blueprint',
            start_date_iso=now_utc.isoformat(),
            end_date_iso=end_time_utc.isoformat(),
            from_building_id=study_id,
            to_building_id=study_id,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(activity_notes),
            priority_override=45  # Medium priority
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}Created draft_blueprint activity for {citizen_username} "
                    f"at {study_name} ({blueprint_info['name']}){LogColors.ENDC}")
            return activity_record
        else:
            log.error(f"Failed to create activity record")
            return None
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error in draft_blueprint creator: {str(e)}{LogColors.ENDC}")
        return None
"""
Activity creator for observe_system_patterns activity.
Innovatori observe economic patterns at busy locations to gather insights.
"""

import logging
import json
import os
import requests
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

# Duration range for observation activities
MIN_OBSERVATION_HOURS = 4
MAX_OBSERVATION_HOURS = 6

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

# Building types that are good for observation
OBSERVATION_BUILDING_TYPES = [
    'market',
    'dock', 
    'guild_hall',
    'public_square',
    'rialto_bridge'  # Major economic hub
]

def _check_innovatori_resources(tables: Dict[str, Any], citizen_username: str) -> bool:
    """Check if the Innovatori has required resources (paper and ink)."""
    try:
        # Get citizen's inventory
        resources = tables['resources'].all(
            formula=f"AND({{Holder}}='{citizen_username}', OR({{Type}}='paper', {{Type}}='ink'))"
        )
        
        has_paper = False
        has_ink = False
        
        for resource in resources:
            resource_type = resource['fields'].get('Type')
            quantity = resource['fields'].get('Quantity', 0)
            
            if resource_type == 'paper' and quantity >= 1:
                has_paper = True
            elif resource_type == 'ink' and quantity >= 1:
                has_ink = True
        
        if not has_paper or not has_ink:
            log.info(f"Innovatori {citizen_username} lacks required resources - Paper: {has_paper}, Ink: {has_ink}")
            return False
            
        return True
        
    except Exception as e:
        log.error(f"Error checking Innovatori resources: {e}")
        return False

def _find_best_observation_location(
    tables: Dict[str, Any], 
    citizen_position: Dict[str, float],
    citizen_username: str
) -> Optional[Dict[str, Any]]:
    """Find the best location for observing system patterns."""
    
    observation_locations = []
    
    # Get all buildings
    all_buildings = tables['buildings'].all()
    
    for building_record in all_buildings:
        building_type = building_record['fields'].get('Type')
        if building_type not in OBSERVATION_BUILDING_TYPES:
            continue
            
        building_pos = _get_building_position_coords(building_record)
        if not building_pos:
            continue
            
        distance = _calculate_distance_meters(citizen_position, building_pos)
        
        # Score locations based on type and distance
        score = 0
        if building_type == 'market':
            score = 100  # Markets are best for economic patterns
        elif building_type == 'dock':
            score = 90   # Docks show trade patterns
        elif building_type == 'guild_hall':
            score = 80   # Guild halls show professional patterns
        elif building_type == 'public_square':
            score = 70   # Public squares show social patterns
        elif building_type == 'rialto_bridge':
            score = 110  # Rialto is the economic heart
            
        # Reduce score based on distance (up to 50 points)
        distance_penalty = min(50, distance / 100)  # 1 point per 100m
        score -= distance_penalty
        
        # Check for recent activity at this location
        recent_activities = tables['activities'].all(
            formula=f"AND({{Citizen}}='{citizen_username}', {{Type}}='observe_system_patterns', {{Status}}='completed')",
            max_records=10
        )
        
        # Reduce score if we've been here recently
        for activity in recent_activities:
            if activity['fields'].get('TargetBuildingId') == building_record['id']:
                created_at = activity['fields'].get('CreatedAt')
                if created_at:
                    try:
                        activity_time = dateutil_parser.parse(created_at)
                        hours_ago = (datetime.now(pytz.UTC) - activity_time).total_seconds() / 3600
                        if hours_ago < 24:  # Within last day
                            score -= 30  # Significant penalty for recent visit
                    except:
                        pass
        
        observation_locations.append((building_record, distance, score))
    
    if not observation_locations:
        log.warning("No suitable observation locations found")
        return None
    
    # Sort by score (highest first) and select from top 3
    observation_locations.sort(key=lambda x: x[2], reverse=True)
    top_locations = observation_locations[:3]
    
    # Weighted random selection from top locations
    selected = random.choice(top_locations)
    building, distance, score = selected
    
    log.info(f"Selected observation location: {building['fields'].get('Name', building['fields'].get('BuildingId'))} "
             f"(Type: {building['fields'].get('Type')}, Distance: {distance:.0f}m, Score: {score:.1f})")
    
    return building

def _ask_citizen_observation_focus(
    citizen_username: str,
    citizen_name: str,
    location_name: str,
    location_type: str,
    api_base_url: Optional[str] = None,
    kinos_model: str = 'local'
) -> Optional[str]:
    """
    Ask the citizen via KinOS what patterns they want to observe at this location.
    Returns their observation focus as a string or None if KinOS is unavailable.
    """
    if not KINOS_API_KEY:
        return None
    
    try:
        # Fetch citizen's recent activities for context
        ledger_markdown_str = None
        if api_base_url:
            ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={citizen_username}"
            try:
                ledger_response = requests.get(ledger_url, timeout=15)
                if ledger_response.ok:
                    ledger_markdown_str = ledger_response.text
                    log.info(f"  Successfully fetched ledger for {citizen_username}. Length: {len(ledger_markdown_str)}")
            except Exception as e:
                log.warning(f"  Could not fetch ledger for observation planning: {e}")
        
        # Construct KinOS request
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt = (
            f"You are {citizen_name}, an Innovatori about to observe system patterns at {location_name} (a {location_type}). "
            f"As a change-maker and system designer, you seek to understand the underlying mechanics that govern Venice.\n\n"
            f"Based on your recent experiences and your role as an Innovatori, what specific patterns or systems "
            f"will you focus on observing at this location?\n\n"
            f"Examples of observation focuses:\n"
            f"- 'Economic flow patterns during peak trading hours'\n"
            f"- 'Social network formation among merchant classes'\n"
            f"- 'Resource distribution inefficiencies in the supply chain'\n"
            f"- 'Trust network dynamics in guild interactions'\n\n"
            f"What patterns will you observe and document today?"
        )
        
        # Initialize the structured addSystem payload
        structured_add_system_payload: Dict[str, Any] = {
            "context": "observation_planning",
            "role": "You are an Innovatori studying systems to create transformative changes",
            "location": location_name,
            "location_type": location_type
        }
        
        if ledger_markdown_str:
            structured_add_system_payload["ledger"] = ledger_markdown_str
        
        kinos_payload = {
            "message": kinos_prompt,
            "model": kinos_model,
            "addSystem": json.dumps(structured_add_system_payload)
        }
        
        # Make synchronous KinOS call
        log.info(f"  Asking {citizen_name} what patterns they want to observe...")
        kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=30)
        kinos_response.raise_for_status()
        
        kinos_data = kinos_response.json()
        observation_focus = kinos_data.get('response', '').strip()
        
        if observation_focus:
            log.info(f"{LogColors.OKGREEN}[Observe Patterns] {citizen_name} will observe: {observation_focus[:100]}...{LogColors.ENDC}")
            return observation_focus
        else:
            log.warning(f"  Received empty response from KinOS")
            return None
        
    except Exception as e:
        log.error(f"  Error asking citizen for observation focus: {e}")
        return None

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    transport_api_url: str,
    api_base_url: str,
    activity_duration: Optional[float] = None,
    activity_end_time: Optional[datetime] = None,
    kinos_model: str = 'local',
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Try to create an observe_system_patterns activity for an Innovatori.
    
    Args:
        tables: Database tables
        citizen_record: The citizen record
        resource_defs: Resource definitions
        building_type_defs: Building type definitions
        transport_api_url: Transport API URL
        api_base_url: Base API URL
        activity_duration: Optional duration in hours
        activity_end_time: Optional specific end time
        **kwargs: Additional parameters
        
    Returns:
        Created activity record or None
    """
    
    citizen_username = citizen_record['fields'].get('Username')
    citizen_id = citizen_record['fields'].get('CitizenId')
    citizen_airtable_id = citizen_record['id']
    
    # Verify this is an Innovatori
    social_class = citizen_record['fields'].get('SocialClass')
    if social_class != 'Innovatori':
        log.warning(f"Citizen {citizen_username} is not an Innovatori (class: {social_class})")
        return None
    
    # Check required resources
    if not _check_innovatori_resources(tables, citizen_username):
        log.info(f"Innovatori {citizen_username} lacks required observation resources")
        return None
    
    # Get citizen position
    position_str = citizen_record['fields'].get('Position')
    if not position_str:
        log.warning(f"No position for citizen {citizen_username}")
        return None
        
    try:
        citizen_position = json.loads(position_str)
    except json.JSONDecodeError:
        log.error(f"Invalid position format for citizen {citizen_username}")
        return None
    
    # Find best observation location
    target_building = _find_best_observation_location(tables, citizen_position, citizen_username)
    if not target_building:
        log.warning(f"No suitable observation location found for {citizen_username}")
        return None
    
    building_position = _get_building_position_coords(target_building)
    if not building_position:
        log.error(f"No position for building {target_building['id']}")
        return None
    
    # Calculate distance and check if we need to go there first
    distance = _calculate_distance_meters(citizen_position, building_position)
    
    if distance > 50:  # More than 50 meters away
        log.info(f"Creating goto activity first - citizen is {distance:.0f}m from observation location")
        
        # Create a goto activity
        goto_result = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url,
            target_building_id=target_building['id'],
            purpose="observe_system_patterns"
        )
        
        if goto_result:
            log.info(f"Created goto activity for {citizen_username} to reach observation location")
            return goto_result
        else:
            log.error(f"Failed to create goto activity for observation")
            return None
    
    # We're at the location, create the observation activity
    now_utc = datetime.now(pytz.UTC)
    
    # Determine duration
    if activity_duration:
        duration_hours = activity_duration
    else:
        duration_hours = random.randint(MIN_OBSERVATION_HOURS, MAX_OBSERVATION_HOURS)
    
    if activity_end_time:
        end_time = activity_end_time
    else:
        end_time = now_utc + timedelta(hours=duration_hours)
    
    # Get path (even though we're already there, for consistency)
    path_result = get_path_between_points(
        transport_api_url,
        citizen_position['lat'],
        citizen_position['lng'],
        building_position['lat'],
        building_position['lng']
    )
    
    if not path_result or not path_result.get('success'):
        log.warning("Failed to get path, using direct route")
        path_data = json.dumps([citizen_position, building_position])
    else:
        path_data = json.dumps(path_result['data']['path_points'])
    
    # Get citizen's name for KinOS
    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip()
    if not citizen_name:
        citizen_name = citizen_username
    
    # Ask citizen what they want to observe via KinOS
    building_name = target_building['fields'].get('Name', 'Observation Location')
    building_type = target_building['fields'].get('Type')
    observation_focus = _ask_citizen_observation_focus(
        citizen_username, citizen_name, building_name, building_type,
        api_base_url, kinos_model
    )
    
    # Create activity parameters
    purpose = kwargs.get('purpose', 'observe_patterns')
    
    activity_params = {
        'targetBuildingId': target_building['id'],
        'targetBuildingName': building_name,
        'targetBuildingType': building_type,
        'purpose': purpose,
        'observationType': 'system_patterns',
        'specialty': 'innovation',
        'duration_hours': duration_hours,
        'observationFocus': observation_focus or 'General system patterns',
        'requiredResources': {
            'paper': 1,
            'ink': 1
        }
    }
    
    # Create activity title and description
    activity_title = f"Observing System Patterns at {building_name}"
    activity_description = f"Conducting systematic observation at {building_name} ({building_type}) to identify patterns for innovation"
    
    # Create thought based on KinOS response
    if observation_focus:
        activity_thought = f"I need to observe: {observation_focus[:150]}..."
    else:
        activity_thought = f"Time to observe the patterns at {building_name}. What innovations might emerge from today's observations?"
    
    # Create notes for the activity
    activity_notes = {
        "location": building_name,
        "location_type": building_type,
        "observation_focus": observation_focus or "General system patterns",
        "duration_hours": duration_hours,
        "required_resources": activity_params['requiredResources']
    }
    
    # Create the activity
    activity_record = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type='observe_system_patterns',
        start_date_iso=now_utc.isoformat(),
        end_date_iso=end_time.isoformat(),
        from_building_id=target_building['id'],
        to_building_id=target_building['id'],
        path_json=path_data,
        title=activity_title,
        description=activity_description,
        thought=activity_thought,
        notes=json.dumps(activity_notes),
        priority_override=50  # Medium-high priority for innovation work
    )
    
    if activity_record:
        log.info(f"{LogColors.OKGREEN}Created observe_system_patterns activity for {citizen_username} "
                 f"at {activity_params['targetBuildingName']} for {duration_hours} hours{LogColors.ENDC}")
        return activity_record
    else:
        log.error(f"Failed to create observe_system_patterns activity record")
        return None
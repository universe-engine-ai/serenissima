"""
Activity creator for test_innovation activity.
Innovatori test their innovations in the field with other citizens.
"""

import logging
import json
import os
import requests
import random
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any, List, Tuple

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

# Duration range for innovation testing
MIN_TEST_HOURS = 4
MAX_TEST_HOURS = 8

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

# Test location types
TEST_LOCATIONS = [
    ('marketplace', 'Market District', ['merchant', 'trader']),
    ('docks', 'Harbor Area', ['sailor', 'porter']),  
    ('piazza', 'Public Square', ['all']),
    ('workshop_district', 'Workshop Quarter', ['artisan', 'builder']),
    ('residential', 'Residential Area', ['all'])
]

def _find_test_participants(tables: Dict[str, Any], location_type: str, 
                          target_classes: List[str], citizen_username: str,
                          max_participants: int = 5) -> List[Dict[str, Any]]:
    """Find citizens who could participate in testing."""
    participants = []
    
    try:
        # Build formula based on target classes
        if 'all' in target_classes:
            formula = f"AND({{Username}}!='{_escape_airtable_value(citizen_username)}', {{Status}}='active')"
        else:
            class_conditions = [f"{{SocialClass}}='{cls}'" for cls in target_classes]
            class_formula = f"OR({','.join(class_conditions)})"
            formula = f"AND({{Username}}!='{_escape_airtable_value(citizen_username)}', {{Status}}='active', {class_formula})"
        
        potential_participants = tables['citizens'].all(
            formula=formula,
            max_records=max_participants * 2  # Get more to allow filtering
        )
        
        # Randomly select participants
        if potential_participants:
            selected = random.sample(
                potential_participants, 
                min(len(potential_participants), max_participants)
            )
            participants = selected
            
    except Exception as e:
        log.error(f"Error finding test participants: {e}")
        
    return participants

def _select_test_location(citizen_position: Dict[float, float]) -> Tuple[str, str, List[str]]:
    """Select a location type for testing based on innovation type."""
    # For now, randomly select a test location
    # In future, could be based on innovation type
    return random.choice(TEST_LOCATIONS)

def _find_nearest_test_venue(tables: Dict[str, Any], location_type: str,
                           citizen_position: Dict[float, float]) -> Optional[Dict[str, Any]]:
    """Find the nearest building suitable for testing."""
    try:
        # Map location types to building types
        building_types_map = {
            'marketplace': ['market', 'trading_post'],
            'docks': ['public_dock', 'warehouse'],
            'piazza': ['town_hall', 'guild_hall'],
            'workshop_district': ['workshop', 'small_warehouse'],
            'residential': ['apartment_building', 'villa']
        }
        
        building_types = building_types_map.get(location_type, [])
        if not building_types:
            return None
            
        # Build formula for building types
        type_conditions = [f"{{Type}}='{bt}'" for bt in building_types]
        type_formula = f"OR({','.join(type_conditions)})"
        formula = f"AND({type_formula}, {{Status}}='active')"
        
        buildings = tables['buildings'].all(formula=formula)
        if not buildings:
            return None
            
        # Find closest building
        closest_building = None
        min_distance = float('inf')
        
        for building in buildings:
            building_pos = _get_building_position_coords(building['fields'], building['id'])
            if building_pos:
                distance = _calculate_distance_meters(
                    citizen_position['lat'], citizen_position['lng'],
                    building_pos['lat'], building_pos['lng']
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_building = building
                    
        return closest_building
        
    except Exception as e:
        log.error(f"Error finding test venue: {e}")
        return None

def _ask_citizen_testing_approach(
    citizen_username: str,
    citizen_name: str,
    location_name: str,
    participant_count: int,
    api_base_url: Optional[str] = None,
    kinos_model: str = 'local'
) -> Optional[str]:
    """
    Ask the citizen via KinOS how they want to test their innovation.
    Returns their testing approach as a string or None if KinOS is unavailable.
    """
    if not KINOS_API_KEY:
        return None
    
    try:
        # Construct KinOS request
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt = (
            f"You are {citizen_name}, an Innovatori about to test your innovation at {location_name} "
            f"with {participant_count} citizens.\n\n"
            f"Based on your recent prototype work and observations, how will you approach this test? "
            f"What specific aspects of your innovation will you focus on demonstrating? "
            f"What feedback are you hoping to gather?\n\n"
            f"Describe your testing approach in 1-2 sentences."
        )
        
        # Initialize the structured addSystem payload
        structured_add_system_payload: Dict[str, Any] = {
            "context": "innovation_testing",
            "role": "You are an Innovatori testing your transformative innovation",
            "location": location_name,
            "participants": participant_count
        }
        
        kinos_payload = {
            "message": kinos_prompt,
            "model": kinos_model,
            "addSystem": json.dumps(structured_add_system_payload)
        }
        
        # Make synchronous KinOS call
        log.info(f"  Asking {citizen_name} about their testing approach...")
        kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=30)
        kinos_response.raise_for_status()
        
        kinos_data = kinos_response.json()
        testing_approach = kinos_data.get('response', '').strip()
        
        if testing_approach:
            log.info(f"{LogColors.OKGREEN}[Test Innovation] {citizen_name}'s approach: {testing_approach[:100]}...{LogColors.ENDC}")
            return testing_approach
        else:
            log.warning(f"  Received empty response from KinOS")
            return None
        
    except Exception as e:
        log.error(f"  Error asking citizen for testing approach: {e}")
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
    Create a test_innovation activity for an Innovatori citizen.
    
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
        
        # Parse citizen position
        try:
            lat, lng = map(float, citizen_position_str.split('_'))
            citizen_pos = {'lat': lat, 'lng': lng}
        except:
            log.error(f"Invalid citizen position format: {citizen_position_str}")
            return None
        
        # Select test location type
        location_type, location_name, target_classes = _select_test_location(citizen_pos)
        
        # Find test venue
        test_venue = _find_nearest_test_venue(tables, location_type, citizen_pos)
        if not test_venue:
            log.info(f"{LogColors.WARNING}No suitable test venue found for {location_type}{LogColors.ENDC}")
            return None
            
        venue_fields = test_venue.get('fields', {})
        venue_id = test_venue.get('id')
        venue_name = venue_fields.get('Name', location_name)
        
        # Get venue position
        venue_pos = _get_building_position_coords(venue_fields, venue_id)
        if not venue_pos:
            log.error(f"Could not get position for venue {venue_id}")
            return None
        
        # Calculate distance to venue
        distance = _calculate_distance_meters(
            citizen_pos['lat'], citizen_pos['lng'],
            venue_pos['lat'], venue_pos['lng']
        )
        
        # Create goto activity if not at venue
        if distance > 50:  # More than 50 meters away
            goto_result = try_create_goto_location_activity(
                tables=tables,
                citizen_record=citizen_record,
                target_position={'lat': venue_pos['lat'], 'lng': venue_pos['lng']},
                target_building_id=venue_id,
                purpose=f"go to {venue_name} to test innovation",
                resource_defs=resource_defs,
                building_type_defs=building_type_defs,
                transport_api_url=transport_api_url,
                api_base_url=api_base_url
            )
            
            if goto_result:
                log.info(f"{LogColors.OKGREEN}Created goto activity to test venue{LogColors.ENDC}")
                return goto_result
            else:
                log.error("Failed to create goto activity to test venue")
                return None
        
        # Find test participants
        participants = _find_test_participants(
            tables, location_type, target_classes, citizen_username
        )
        
        participant_names = []
        participant_ids = []
        for participant in participants:
            p_fields = participant.get('fields', {})
            p_name = f"{p_fields.get('FirstName', '')} {p_fields.get('LastName', '')}".strip()
            if not p_name:
                p_name = p_fields.get('Username', 'Unknown')
            participant_names.append(p_name)
            participant_ids.append(participant.get('id'))
        
        # Determine test duration
        if activity_duration:
            duration_hours = activity_duration
        else:
            base_hours = random.randint(MIN_TEST_HOURS, MAX_TEST_HOURS)
            # More participants = longer testing
            duration_hours = base_hours + (len(participants) * 0.5)
        
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
            'venue_id': venue_id,
            'venue_name': venue_name,
            'location_type': location_type,
            'participant_count': len(participants),
            'participant_ids': participant_ids,
            'participant_names': participant_names,
            'duration_hours': duration_hours
        }
        
        # Create notes
        participant_str = f"{len(participants)} citizens" if participants else "no participants"
        notes = (f"Testing innovation at {venue_name} ({location_name}) with {participant_str}. "
                f"Participants: {', '.join(participant_names[:3])}")
        if len(participant_names) > 3:
            notes += f" and {len(participant_names) - 3} others"
        
        # Get citizen's name for KinOS
        citizen_name = f"{citizen_fields.get('FirstName', '')} {citizen_fields.get('LastName', '')}".strip()
        if not citizen_name:
            citizen_name = citizen_username
        
        # Ask citizen about their testing approach via KinOS
        testing_approach = _ask_citizen_testing_approach(
            citizen_username, citizen_name, venue_name, len(participants),
            api_base_url, kinos_model
        )
        
        # Create activity title and description
        activity_title = f"Testing Innovation at {venue_name}"
        activity_description = f"Field testing innovation with {len(participants)} citizens at {venue_name}"
        
        # Create thought based on KinOS response
        if testing_approach:
            activity_thought = testing_approach
        else:
            activity_thought = f"Let's see how people respond to my innovation. Their feedback will be invaluable."
        
        # Create structured notes
        activity_notes = {
            "venue_id": venue_id,
            "venue_name": venue_name,
            "venue_type": venue_type,
            "location_type": location_type,
            "participant_count": len(participants),
            "participant_ids": participant_ids,
            "participant_names": participant_names[:5],  # Limit to first 5 names
            "testing_approach": testing_approach or "Standard field testing",
            "duration_hours": duration_hours
        }
        
        # Create the activity record
        activity_record = create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type='test_innovation',
            start_date_iso=now_utc.isoformat(),
            end_date_iso=end_time_utc.isoformat(),
            from_building_id=venue_id,
            to_building_id=venue_id,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(activity_notes),
            priority_override=60  # High priority for testing
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}Created test_innovation activity for {citizen_username} "
                    f"at {venue_name} with {len(participants)} participants{LogColors.ENDC}")
            return activity_record
        else:
            log.error(f"Failed to create activity record")
            return None
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error in test_innovation creator: {str(e)}{LogColors.ENDC}")
        return None
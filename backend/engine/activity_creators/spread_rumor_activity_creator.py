"""
Activity Creator for 'spread_rumor'.

This activity allows a citizen to spread a rumor about another citizen.
The citizen will go to a location where other citizens are present and initiate
conversations to spread the rumor.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import pytz

from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    get_path_between_points,
    _get_building_position_coords,
    calculate_haversine_distance_meters,
    get_citizen_record
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    activity_params: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    now_venice_dt: Any,
    now_utc_dt: Any,
    transport_api_url: str,
    api_base_url: str
) -> bool:
    """
    Tries to create a 'spread_rumor' activity.

    Expected activity_params:
    - targetCitizen (str): The username of the citizen being gossiped about.
    - gossipContent (str): The content of the rumor/gossip.
    - locationId (str, optional): The ID of a specific building to spread the rumor at.
    - locationCoords (dict, optional): The coordinates where to spread the rumor if no locationId.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_airtable_id = citizen_record['id']
    
    # Check if parameters are directly in activity_params or in a nested 'notes' JSON string
    target_citizen = activity_params.get('targetCitizen')
    gossip_content = activity_params.get('gossipContent')
    location_id = activity_params.get('locationId')
    location_coords_raw = activity_params.get('locationCoords')
    position = activity_params.get('position')  # Direct position parameter
    
    # If parameters are in notes JSON string, extract them
    notes_str = activity_params.get('notes')
    if notes_str and not (target_citizen and gossip_content):
        try:
            if isinstance(notes_str, str):
                notes_data = json.loads(notes_str)
                target_citizen = target_citizen or notes_data.get('targetCitizen')
                gossip_content = gossip_content or notes_data.get('gossipContent')
                location_coords_raw = location_coords_raw or notes_data.get('locationCoords')
            elif isinstance(notes_str, dict):
                # Already a dictionary
                target_citizen = target_citizen or notes_str.get('targetCitizen')
                gossip_content = gossip_content or notes_str.get('gossipContent')
                location_coords_raw = location_coords_raw or notes_str.get('locationCoords')
        except json.JSONDecodeError as e:
            log.warning(f"Could not parse notes JSON for spread_rumor: {e}")
    
    # If position is provided directly but not locationCoords, use position
    if not location_coords_raw and position:
        location_coords_raw = position
    
    # Validate required parameters
    if not citizen_username:
        log.error(f"{LogColors.FAIL}Missing citizen_username for spread_rumor. Params: {activity_params}{LogColors.ENDC}")
        return False
    
    # target_citizen est optionnel - la rumeur peut être générale
    # gossip_content est optionnel - KinOS générera le contenu
    if not target_citizen:
        log.info(f"{LogColors.OKBLUE}Target citizen not provided for {citizen_username}. Rumor will be general.{LogColors.ENDC}")
    if not gossip_content:
        log.info(f"{LogColors.OKBLUE}Gossip content not provided for {citizen_username}. KinOS will generate content.{LogColors.ENDC}")
    
    log.info(f"{LogColors.OKBLUE}Creating spread_rumor activity for {citizen_username} targeting {target_citizen} with coordinates: {location_coords_raw}{LogColors.ENDC}")
    
    # Validate target citizen exists only if specified
    if target_citizen:
        target_citizen_record = get_citizen_record(tables, target_citizen)
        if not target_citizen_record:
            log.error(f"{LogColors.FAIL}Target citizen {target_citizen} not found for spread_rumor by {citizen_username}.{LogColors.ENDC}")
            return False
    
    # Get citizen's current position
    citizen_position_str = citizen_record['fields'].get('Position')
    citizen_position = None
    try:
        if citizen_position_str:
            citizen_position = json.loads(citizen_position_str)
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error parsing citizen position for {citizen_username}: {e}{LogColors.ENDC}")
        return False
    
    if not citizen_position:
        log.error(f"{LogColors.FAIL}Citizen {citizen_username} has no position. Cannot create spread_rumor activity.{LogColors.ENDC}")
        return False
    
    # Determine target location
    target_location_coords = None
    target_building_record = None
    path_data = None
    
    # If location_id is provided, use that building
    if location_id:
        # Find the building record
        building_formula = f"{{BuildingId}}='{_escape_airtable_value(location_id)}'"
        building_records = tables['buildings'].all(formula=building_formula)
        
        if building_records:
            target_building_record = building_records[0]
            target_location_coords = _get_building_position_coords(target_building_record)
            
            if not target_location_coords:
                log.error(f"{LogColors.FAIL}Building {location_id} has no position coordinates. Cannot create spread_rumor activity.{LogColors.ENDC}")
                return False
        else:
            log.error(f"{LogColors.FAIL}Building {location_id} not found. Cannot create spread_rumor activity.{LogColors.ENDC}")
            return False
    
    # If no location_id but location_coords provided, use those coordinates
    elif location_coords_raw:
        try:
            if isinstance(location_coords_raw, str):
                target_location_coords = json.loads(location_coords_raw)
            else:
                target_location_coords = location_coords_raw
                
            if not (isinstance(target_location_coords, dict) and 
                    'lat' in target_location_coords and 
                    'lng' in target_location_coords):
                log.error(f"{LogColors.FAIL}Invalid location coordinates format for spread_rumor by {citizen_username}: {location_coords_raw}{LogColors.ENDC}")
                return False
        except Exception as e:
            log.error(f"{LogColors.FAIL}Error parsing location coordinates for spread_rumor by {citizen_username}: {e}{LogColors.ENDC}")
            return False
    
    # If neither location_id nor location_coords provided, find a populated public place
    else:
        # Find a public place with citizens (tavern, inn, market, etc.)
        public_places_types = ["tavern", "inn", "market_stall", "public_square", "theater"]
        public_places = []
        
        for place_type in public_places_types:
            formula = f"{{Type}}='{place_type}'"
            places = tables['buildings'].all(formula=formula)
            public_places.extend(places)
        
        if not public_places:
            log.error(f"{LogColors.FAIL}No suitable public places found for spread_rumor by {citizen_username}.{LogColors.ENDC}")
            return False
        
        # Find the closest public place
        closest_place = None
        min_distance = float('inf')
        
        for place in public_places:
            place_coords = _get_building_position_coords(place)
            if place_coords:
                distance = calculate_haversine_distance_meters(
                    citizen_position['lat'], citizen_position['lng'],
                    place_coords['lat'], place_coords['lng']
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_place = place
                    target_location_coords = place_coords
        
        if closest_place:
            target_building_record = closest_place
        else:
            log.error(f"{LogColors.FAIL}Could not find a suitable public place with valid coordinates for spread_rumor by {citizen_username}.{LogColors.ENDC}")
            return False
    
    # Calculate path to target location if not already there
    is_at_target_location = False
    if target_location_coords:
        distance_to_target = calculate_haversine_distance_meters(
            citizen_position['lat'], citizen_position['lng'],
            target_location_coords['lat'], target_location_coords['lng']
        )
        
        is_at_target_location = distance_to_target < 20  # Consider "at location" if within 20 meters
        
        if not is_at_target_location:
            path_data = get_path_between_points(citizen_position, target_location_coords, transport_api_url)
            
            if not path_data or not path_data.get('success'):
                log.error(f"{LogColors.FAIL}Failed to find path to target location for spread_rumor by {citizen_username}.{LogColors.ENDC}")
                return False
    
    # Prepare activity details
    activity_details = {
        "targetCitizen": target_citizen,
        "gossipContent": gossip_content,
        "locationCoords": json.dumps(target_location_coords)
    }
    
    if target_building_record:
        building_id = target_building_record['fields'].get('BuildingId')
        building_name = target_building_record['fields'].get('Name', 'Unknown Building')
        building_type = target_building_record['fields'].get('Type', 'Unknown Type')
        
        activity_details["locationBuildingId"] = building_id
        activity_details["locationBuildingName"] = building_name
        activity_details["locationBuildingType"] = building_type
    
    # Create the activity
    activity_id = f"spread-rumor-{uuid.uuid4().hex[:8]}"
    
    activity_fields = {
        "ActivityId": activity_id,
        "Type": "spread_rumor",
        "Citizen": citizen_username,
        "Status": "created",
        "CreatedAt": now_utc_dt.isoformat(),
        "StartDate": now_utc_dt.isoformat(),
        "EndDate": (now_utc_dt + timedelta(minutes=30)).isoformat(),  # Rumor spreading takes 30 minutes
        "Notes": json.dumps(activity_details),
        "Title": f"Spreading rumors about {target_citizen}",
        "Description": f"Spreading gossip about {target_citizen} at a public place."
    }
    
    if target_building_record:
        building_id = target_building_record['fields'].get('BuildingId')
        activity_fields["ToBuilding"] = building_id
    
    try:
        created_activity = tables['activities'].create(activity_fields)
        log.info(f"{LogColors.OKGREEN}Created spread_rumor activity {activity_id} for {citizen_username} targeting {target_citizen}.{LogColors.ENDC}")
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to create spread_rumor activity for {citizen_username}: {e}{LogColors.ENDC}")
        return False

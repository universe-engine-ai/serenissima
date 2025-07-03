import json
import uuid
import logging
import os # Added import
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union # Added List, Union
from backend.engine.utils.activity_helpers import (
    _escape_airtable_value, 
    VENICE_TIMEZONE,
    find_path_between_buildings_or_coords, # Corrected import
    get_building_record,
    _get_building_position_coords, # Added for _get_building_position
    _calculate_distance_meters # Added for _calculate_distance
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    activity_type_param: str, 
    details: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    now_venice_dt: datetime,
    now_utc_dt_param: datetime, 
    transport_api_url_param: str,
    api_base_url_param: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Create the complete manage_logistics_service_contract activity chain at once:
    1. A goto_location activity for travel to the client's building (to assess logistics needs)
    2. An assess_logistics_needs activity at the client's building
    3. A goto_location activity for travel to the porter guild hall
    4. A register_logistics_service_contract activity that will execute after arrival
    
    This approach creates the complete activity chain upfront.
    """
    # Extract required parameters
    contract_id = details.get('contractId')  # Optional for new contracts
    resource_type = details.get('resourceType')  # Optional for general logistics
    service_fee_per_unit = details.get('serviceFeePerUnit')
    client_building_id = details.get('clientBuildingId')
    target_guild_hall_id = details.get('targetGuildHallId')  # porter_guild_hall
    
    # Validate required parameters
    if not (service_fee_per_unit is not None and client_building_id and target_guild_hall_id):
        log.error(f"Missing required details for manage_logistics_service_contract: serviceFeePerUnit, clientBuildingId, or targetGuildHallId")
        return None

    citizen_username = citizen_record['fields'].get('Username')
    ts = int(datetime.now(VENICE_TIMEZONE).timestamp())
    
    # Get building records for path calculation
    client_building_record = get_building_record(tables, client_building_id)
    guild_hall_record = get_building_record(tables, target_guild_hall_id)
    
    if not client_building_record or not guild_hall_record:
        log.error(f"Could not find building records for {client_building_id} or {target_guild_hall_id}")
        return None
    
    # Get current citizen position to determine first path
    citizen_position_str = citizen_record['fields'].get('Position')
    current_position = None
    if citizen_position_str:
        try:
            current_position = json.loads(citizen_position_str)
        except json.JSONDecodeError:
            log.error(f"Could not parse citizen position: {citizen_position_str}")
            return None
    
    # Determine if we need to go to client building first or if citizen is already there
    citizen_at_client_building = False
    if current_position:
        client_position = _get_building_position(client_building_record)
        if client_position:
            # Simple check if positions are close enough (within ~10 meters)
            distance = _calculate_distance(current_position, client_position)
            citizen_at_client_building = distance < 10
    
    # Create activity IDs
    assess_activity_id = f"assess_logistics_needs_{citizen_username}_{ts}"
    goto_guild_hall_activity_id = f"goto_guild_hall_{citizen_username}_{ts}"
    register_activity_id = f"register_logistics_service_{citizen_username}_{ts}"
    
    now_utc = now_utc_dt_param # Use passed now_utc
    
    # Calculate activity times
    # The main conditional logic: if travel to client is NOT needed (i.e., citizen IS at client building)
    # vs. if travel TO client IS needed.
    if citizen_at_client_building: 
        # Citizen is ALREADY at the client building.
        chain_created_at = now_utc.isoformat()
        assess_start_date = chain_created_at # Assess starts immediately
        assess_end_date_dt = datetime.fromisoformat(assess_start_date.replace('Z', '+00:00')) + timedelta(minutes=15)
        assess_end_date = assess_end_date_dt.isoformat()
        goto_guild_hall_start_date = assess_end_date # Travel to guild hall starts after assessment
    else:
        # Citizen is NOT at the client building. Travel to client is needed first.
        path_to_client = find_path_between_buildings_or_coords(tables, current_position, client_building_record, api_base_url_param, transport_api_url_param)
        if not path_to_client or not path_to_client.get('path'):
            log.error(f"Could not find path to client building {client_building_id}")
            return None
        
        chain_created_at = now_utc.isoformat() # Timestamp for the creation of this chain
        goto_client_start_date = chain_created_at
        
        # Calculate travel duration to client building
        client_duration_seconds = path_to_client.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min
        goto_client_end_date_dt = datetime.fromisoformat(goto_client_start_date.replace('Z', '+00:00')) + timedelta(seconds=client_duration_seconds)
        goto_client_end_date = goto_client_end_date_dt.isoformat()

        assess_start_date = goto_client_end_date # Assess starts after travel
        assess_end_date_dt = goto_client_end_date_dt + timedelta(minutes=15) # 15 min to assess needs
        assess_end_date = assess_end_date_dt.isoformat()
        
        goto_guild_hall_start_date = assess_end_date # Travel to guild hall starts after assessment
    
    # Calculate path from client building to guild hall
    path_to_guild_hall = find_path_between_buildings_or_coords(tables, client_building_record, guild_hall_record, api_base_url_param, transport_api_url_param)
    if not path_to_guild_hall or not path_to_guild_hall.get('path'):
        log.error(f"Could not find path from client building {client_building_id} to guild hall {target_guild_hall_id}")
        return None
    
    # Calculate guild hall travel duration
    guild_hall_duration_seconds = path_to_guild_hall.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min
    goto_guild_hall_end_date_dt = datetime.fromisoformat(goto_guild_hall_start_date.replace('Z', '+00:00')) + timedelta(seconds=guild_hall_duration_seconds)
    goto_guild_hall_end_date = goto_guild_hall_end_date_dt.isoformat()
    
    # Calculate registration activity times (15 minutes after arrival at guild hall)
    register_start_date = goto_guild_hall_end_date # Starts when travel ends
    register_end_date_dt = goto_guild_hall_end_date_dt + timedelta(minutes=15)
    register_end_date = register_end_date_dt.isoformat()
    
    # Prepare activity payloads
    activities_to_create = []
    
    # 1. Create goto_client_building activity (if needed)
    if not citizen_at_client_building:
        goto_client_payload = {
            "ActivityId": f"goto_client_{citizen_username}_{ts}",
            "Type": "goto_location",
            "Citizen": citizen_username,
            "FromBuilding": None,  # Starting from current position
            "ToBuilding": client_building_id,
            "Path": json.dumps(path_to_client.get('path', [])),
            "Notes": json.dumps({ # Changed Details to Notes
                "resourceType": resource_type,
                "activityType": "manage_logistics_service_contract",
                "nextStep": "assess_logistics_needs"
            }),
            "Status": "created",
            "Title": f"Traveling to assess logistics needs",
            "Description": f"Traveling to {client_building_record['fields'].get('Name', client_building_id)} to assess logistics service needs",
            # "Notes": f"First step of manage_logistics_service_contract process. Will be followed by needs assessment.", # This descriptive note is covered by Description. The JSON Notes above is needed by the processor.
            "CreatedAt": chain_created_at,
            "StartDate": goto_client_start_date, # This was assess_start_date, should be goto_client_start_date
            "EndDate": goto_client_end_date,     # This was assess_end_date, should be goto_client_end_date
            "Priority": 20
        }
        activities_to_create.append(goto_client_payload)
    
    # 2. Create assess_logistics_needs activity (short duration at client building)
    assess_needs_payload = {
        "ActivityId": assess_activity_id,
        "Type": "assess_logistics_needs",
        "Citizen": citizen_username,
        "FromBuilding": client_building_id,
        "ToBuilding": client_building_id,  # Same location
        "Notes": json.dumps({ # Changed Details to Notes
            "resourceType": resource_type,
            "serviceFeePerUnit": service_fee_per_unit,
            "contractId": contract_id,
            "activityType": "manage_logistics_service_contract",
            "nextStep": "goto_guild_hall"
        }),
        "Status": "created",
        "Title": f"Assessing logistics service needs",
        "Description": f"Evaluating logistics requirements at {client_building_record['fields'].get('Name', client_building_id)}",
        # "Notes": f"{'Modifying' if contract_id else 'Creating new'} logistics service contract", # This descriptive note is covered by Description. The JSON Notes above is needed by the processor.
        "CreatedAt": chain_created_at,
        "StartDate": assess_start_date, # Correct: starts when travel ends or immediately
        "EndDate": assess_end_date,     # Correct: ends after 15 mins
        "Priority": 20
    }
    activities_to_create.append(assess_needs_payload)
    
    # 3. Create goto_guild_hall activity
    goto_guild_hall_payload = {
        "ActivityId": goto_guild_hall_activity_id,
        "Type": "goto_location",
        "Citizen": citizen_username,
        "FromBuilding": client_building_id,
        "ToBuilding": target_guild_hall_id,
        "Path": json.dumps(path_to_guild_hall.get('path', [])),
        "Notes": json.dumps({ # Changed Details to Notes
            "resourceType": resource_type,
            "serviceFeePerUnit": service_fee_per_unit,
            "contractId": contract_id,
            "clientBuildingId": client_building_id,
            "activityType": "manage_logistics_service_contract",
            "nextStep": "register_logistics_service_contract"
        }),
        "Status": "created",
        "Title": f"Traveling to {'modify' if contract_id else 'register'} logistics service contract",
        "Description": f"Traveling to {guild_hall_record['fields'].get('Name', target_guild_hall_id)} to {'modify' if contract_id else 'register'} logistics service contract",
        # "Notes": f"Second step of manage_logistics_service_contract process. Will be followed by contract registration.", # This descriptive note is covered by Description. The JSON Notes above is needed by the processor.
        "CreatedAt": chain_created_at,
        "StartDate": goto_guild_hall_start_date, # Correct: starts when assessment ends
        "EndDate": goto_guild_hall_end_date,
        "Priority": 20
    }
    activities_to_create.append(goto_guild_hall_payload)
    
    # 4. Create register_logistics_service_contract activity
    register_payload = {
        "ActivityId": register_activity_id,
        "Type": "register_logistics_service_contract",
        "Citizen": citizen_username,
        "FromBuilding": target_guild_hall_id,
        "ToBuilding": target_guild_hall_id,  # Same location
        "Notes": json.dumps({ # Changed Details to Notes
            "resourceType": resource_type,
            "serviceFeePerUnit": service_fee_per_unit,
            "contractId": contract_id,
            "clientBuildingId": client_building_id
        }),
        "Status": "created",
        "Title": f"{'Modifying' if contract_id else 'Registering'} logistics service contract",
        "Description": f"{'Modifying' if contract_id else 'Registering'} logistics service contract for {client_building_record['fields'].get('Name', client_building_id)}",
        # "Notes": f"Final step of manage_logistics_service_contract process. Will create/update logistics_service_request contract.", # This descriptive note is covered by Description. The JSON Notes above is needed by the processor.
        "CreatedAt": chain_created_at,
        "StartDate": register_start_date, # Correct: starts when travel to guild hall ends
        "EndDate": register_end_date,
        "Priority": 20
    }
    activities_to_create.append(register_payload)

    # The creator should now return the list of payloads, and the dispatcher will handle creation.
    log.info(f"Prepared manage_logistics_service_contract activity chain for citizen {citizen_username}:")
    for idx, activity_payload_log in enumerate(activities_to_create, 1):
        log.info(f"  {idx}. {activity_payload_log['Type']} activity payload {activity_payload_log['ActivityId']} prepared.")
    return activities_to_create

def _get_building_position(building_record):
    """Extract position from building record."""
    position_str = building_record['fields'].get('Position')
    if position_str:
        try:
            return json.loads(position_str)
        except json.JSONDecodeError:
            return None
    return None

def _calculate_distance(pos1, pos2):
    """Calculate simple Euclidean distance between two positions."""
    if not (pos1 and pos2 and 'lat' in pos1 and 'lng' in pos1 and 'lat' in pos2 and 'lng' in pos2):
        return float('inf')
    
    # Simple approximation for small distances
    lat_diff = (pos1['lat'] - pos2['lat']) * 111000  # ~111km per degree of latitude
    lng_diff = (pos1['lng'] - pos2['lng']) * 111000 * 0.85  # Approximate at mid-latitudes
    return (lat_diff**2 + lng_diff**2)**0.5  # Euclidean distance in meters

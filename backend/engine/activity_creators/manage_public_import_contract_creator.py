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
    get_closest_building_of_type, 
    _get_building_position_coords 
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
    Create the complete manage_public_import_contract activity chain at once:
    1. A goto_location activity for travel to the customs house or broker's office
    2. A register_public_import_agreement activity that will execute after arrival
    
    This approach creates the complete activity chain upfront for a public import offer.
    """
    # Extract required parameters
    contract_id = details.get('contractId')  # Optional for new contracts
    resource_type = details.get('resourceType')
    price_per_resource = details.get('pricePerResource')
    target_amount = details.get('targetAmount')
    target_office_building_id = details.get('targetOfficeBuildingId')  # customs_house or broker_s_office
    
    # Validate required parameters
    if not (resource_type and price_per_resource is not None and target_amount is not None and
            target_office_building_id):
        log.error(f"Missing required details for manage_public_import_contract: resourceType, pricePerResource, targetAmount, or targetOfficeBuildingId")
        return None

    citizen_username = citizen_record['fields'].get('Username')
    ts = int(datetime.now(VENICE_TIMEZONE).timestamp())
    
    # Get building record for path calculation
    office_building_record = get_building_record(tables, target_office_building_id)
    
    if not office_building_record:
        log.error(f"Could not find building record for {target_office_building_id}")
        return None
    
    # Get current citizen position to determine path
    citizen_position_str = citizen_record['fields'].get('Position')
    current_position = None
    if citizen_position_str:
        try:
            current_position = json.loads(citizen_position_str)
        except json.JSONDecodeError:
            log.error(f"Could not parse citizen position: {citizen_position_str}")
            return None
    
    # Create activity IDs
    goto_office_activity_id = f"goto_office_{_escape_airtable_value(resource_type)}_{citizen_username}_{ts}"
    register_activity_id = f"register_public_import_{_escape_airtable_value(resource_type)}_{citizen_username}_{ts}"
    
    now_utc = now_utc_dt_param # Use passed now_utc
    
    # Calculate activity times for path to office
    # Assuming API_BASE_URL and TRANSPORT_API_URL are available in this scope or passed in.
    # For now, let's assume they are passed in `details` or globally accessible.
    # This creator might need its signature updated if they are not.
    # For consistency with other updated creators, let's assume api_base_url and transport_api_url are available.
    # If this script is called by citizen_general_activities.dispatch_specific_activity_request,
    # those should be passed to its `try_create` function.
    # The current `try_create` signature for this file is:
    # def try_create(tables: Dict[str, Any], citizen_record: Dict[str, Any], details: Dict[str, Any]) -> bool:
    # It needs to be updated to accept api_base_url and transport_api_url.
    # For now, I will make the call assuming they are available.
    # This will likely require a follow-up to adjust the function signature.
    
    # Placeholder for api_base_url and transport_api_url - these need to be passed to this function
    # For the purpose of this change, I'll assume they are available.
    # This will require a signature change for this creator.
    # api_base_url = details.get("api_base_url", os.getenv("API_BASE_URL", "http://localhost:3000")) # Now passed as api_base_url_param
    # transport_api_url = details.get("transport_api_url", os.getenv("TRANSPORT_API_URL")) # Now passed as transport_api_url_param

    path_to_office = find_path_between_buildings_or_coords(tables, current_position, office_building_record, api_base_url_param, transport_api_url_param)
    if not path_to_office or not path_to_office.get('path'):
        log.error(f"Could not find path to office building {target_office_building_id}")
        return None
    
    # Set start times
    chain_created_at = now_utc.isoformat() # Timestamp for the creation of this chain
    goto_office_start_date = chain_created_at
    
    # Calculate office travel duration
    office_duration_seconds = path_to_office.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min
    goto_office_end_date_dt = datetime.fromisoformat(goto_office_start_date.replace('Z', '+00:00')) + timedelta(seconds=office_duration_seconds)
    goto_office_end_date = goto_office_end_date_dt.isoformat()
    
    # Calculate registration activity times (15 minutes after arrival at office)
    register_start_date = goto_office_end_date # Starts when travel ends
    register_end_date_dt = goto_office_end_date_dt + timedelta(minutes=15)
    register_end_date = register_end_date_dt.isoformat()
    
    # Prepare activity payloads
    activities_to_create = []
    
    # Create goto_office activity (direct from current position)
    goto_office_payload = {
        "ActivityId": goto_office_activity_id,
        "Type": "goto_location",
        "Citizen": citizen_username,
        "FromBuilding": None,  # Starting from current position
        "ToBuilding": target_office_building_id,
        "Path": json.dumps(path_to_office.get('path', [])),
        "Notes": json.dumps({ # Changed Details to Notes
            "resourceType": resource_type,
            "targetAmount": target_amount,
            "pricePerResource": price_per_resource,
            "contractId": contract_id,
            "activityType": "manage_public_import_contract",
            "nextStep": "register_public_import_agreement"
        }),
        "Status": "created",
        "Title": f"Traveling to {'modify' if contract_id else 'register'} public import offer",
        "Description": f"Traveling to {office_building_record['fields'].get('Name', target_office_building_id)} to {'modify' if contract_id else 'register'} public import offer for {target_amount} {resource_type}",
        # "Notes": f"First step of manage_public_import_contract process. Will be followed by contract registration.", # This descriptive note is covered by Description. The JSON Notes above is needed by the processor.
        "CreatedAt": chain_created_at,
        "StartDate": goto_office_start_date,
        "EndDate": goto_office_end_date,
        "Priority": 20
    }
    activities_to_create.append(goto_office_payload)
    
    # Create register_public_import_agreement activity
    register_payload = {
        "ActivityId": register_activity_id,
        "Type": "register_public_import_agreement",
        "Citizen": citizen_username,
        "FromBuilding": target_office_building_id,
        "ToBuilding": target_office_building_id,  # Same location
        "Notes": json.dumps({ # Changed Details to Notes
            "resourceType": resource_type,
            "targetAmount": target_amount,
            "pricePerResource": price_per_resource,
            "contractId": contract_id
        }),
        "Status": "created",
        "Title": f"{'Modifying' if contract_id else 'Registering'} public import offer for {resource_type}",
        "Description": f"{'Modifying' if contract_id else 'Registering'} public import offer for {target_amount} {resource_type} at {price_per_resource} Ducats each",
        # "Notes": f"Final step of manage_public_import_contract process. Will create/update public import contract.", # This descriptive note is covered by Description. The JSON Notes above is needed by the processor.
        "CreatedAt": chain_created_at,
        "StartDate": register_start_date,
        "EndDate": register_end_date,
        "Priority": 20
    }
    activities_to_create.append(register_payload)

    # The creator should now return the list of payloads, and the dispatcher will handle creation.
    log.info(f"Prepared manage_public_import_contract activity chain for citizen {citizen_username}:")
    for idx, activity_payload_log in enumerate(activities_to_create, 1):
        log.info(f"  {idx}. {activity_payload_log['Type']} activity payload {activity_payload_log['ActivityId']} prepared.")
    return activities_to_create

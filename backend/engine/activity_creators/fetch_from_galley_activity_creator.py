"""
Creator for 'fetch_from_galley' activities.
"""
import logging
import datetime
import time
import json
import uuid
import pytz 
from typing import Dict, Optional, Any

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_airtable_id: str,
    citizen_custom_id: str,
    citizen_username: str,
    galley_airtable_id: str = None,
    galley_custom_id: str = None,
    original_contract_custom_id: str = None,
    resource_id_to_fetch: str = None,
    amount_to_fetch: float = None,
    path_data_to_galley: Dict = None,
    current_time_utc: datetime.datetime = None,
    resource_defs: Dict[str, Any] = None,
    buyer_destination_building_record: Dict[str, Any] = None,
    api_base_url: str = None,
    transport_api_url: str = None,
    start_time_utc_iso: Optional[str] = None,
    # Add parameters to support direct API calls
    activity_params: Dict[str, Any] = None
) -> Optional[Dict]:
    """
    Creates a chain of activities for fetching resources from a galley and delivering them:
    1. goto_location (to galley)
    2. pickup_from_galley (at galley)
    3. goto_location (to buyer's destination)
    4. deliver_resource_to_buyer (at destination)
    Returns the first activity in the chain (goto_location to galley).
    """
    # Handle direct API calls with activity_params
    if activity_params:
        # Extract parameters from activity_params
        from_building_id = activity_params.get("fromBuildingId")
        to_building_id = activity_params.get("toBuildingId")
        contract_id = activity_params.get("contractId")
        resource_type = activity_params.get("resourceType")
        amount = activity_params.get("amount", 10.0)  # Default to 10 if not specified
        
        # Override parameters with values from activity_params
        if from_building_id:
            galley_custom_id = from_building_id
        if contract_id:
            original_contract_custom_id = contract_id
        if resource_type:
            resource_id_to_fetch = resource_type
        if amount:
            amount_to_fetch = float(amount)
            
        # Get galley record if not provided
        if galley_custom_id and not galley_airtable_id:
            try:
                galley_records = tables['buildings'].all(formula=f"{{BuildingId}}='{galley_custom_id}'", max_records=1)
                if galley_records:
                    galley_airtable_id = galley_records[0]['id']
            except Exception as e:
                log.error(f"Error fetching galley record for {galley_custom_id}: {e}")
                
        # Get buyer destination building record if not provided
        if to_building_id and not buyer_destination_building_record:
            try:
                destination_records = tables['buildings'].all(formula=f"{{BuildingId}}='{to_building_id}'", max_records=1)
                if destination_records:
                    buyer_destination_building_record = destination_records[0]
            except Exception as e:
                log.error(f"Error fetching destination building record for {to_building_id}: {e}")
                return None
    
    if not galley_custom_id or not resource_id_to_fetch or not amount_to_fetch or not buyer_destination_building_record:
        log.error(f"Missing required parameters for fetch_from_galley activity creation")
        return None
        
    log.info(f"Attempting to create 'fetch_from_galley' chain for {citizen_username} to galley {galley_custom_id} for contract {original_contract_custom_id}, delivering to {buyer_destination_building_record['fields'].get('BuildingId')}")

    # --- Activity 1: Go to Galley ---
    goto_galley_start_time_iso: str
    goto_galley_end_time_iso: str

    if start_time_utc_iso: # If an explicit start time for the whole chain is given
        goto_galley_start_time_iso = start_time_utc_iso
        if path_data_to_galley and path_data_to_galley.get('timing', {}).get('durationSeconds') is not None:
            start_dt_obj = datetime.datetime.fromisoformat(goto_galley_start_time_iso.replace("Z", "+00:00"))
            if start_dt_obj.tzinfo is None: start_dt_obj = pytz.UTC.localize(start_dt_obj)
            duration_seconds = path_data_to_galley['timing']['durationSeconds']
            goto_galley_end_time_iso = (start_dt_obj + datetime.timedelta(seconds=duration_seconds)).isoformat()
        else: # Default duration
            start_dt_obj = datetime.datetime.fromisoformat(goto_galley_start_time_iso.replace("Z", "+00:00"))
            if start_dt_obj.tzinfo is None: start_dt_obj = pytz.UTC.localize(start_dt_obj)
            goto_galley_end_time_iso = (start_dt_obj + datetime.timedelta(minutes=30)).isoformat() # Default 30 mins travel
    elif path_data_to_galley and path_data_to_galley.get('timing', {}).get('startDate') and path_data_to_galley.get('timing', {}).get('endDate'):
        goto_galley_start_time_iso = path_data_to_galley['timing']['startDate']
        goto_galley_end_time_iso = path_data_to_galley['timing']['endDate']
    else: # Fallback to current_time_utc and default duration
        goto_galley_start_time_iso = current_time_utc.isoformat()
        goto_galley_end_time_iso = (current_time_utc + datetime.timedelta(minutes=30)).isoformat()

    goto_galley_activity_id = f"goto_galley_{citizen_custom_id}_{uuid.uuid4().hex[:8]}"
    pickup_details_for_goto = {
        "action_on_arrival": "pickup_from_galley",
        "resource_id": resource_id_to_fetch,
        "amount": amount_to_fetch,
        "original_contract_id": original_contract_custom_id,
        "galley_id": galley_custom_id, # For the pickup processor
        "final_destination_building_id": buyer_destination_building_record['fields'].get('BuildingId')
    }
    goto_galley_payload = {
        "ActivityId": goto_galley_activity_id,
        "Type": "goto_location",
        "Citizen": citizen_username,
        "ToBuilding": galley_custom_id,
        "Path": json.dumps(path_data_to_galley.get('path', []) if path_data_to_galley else []),
        "Transporter": path_data_to_galley.get('transporter') if path_data_to_galley else None,
        "StartDate": goto_galley_start_time_iso,
        "EndDate": goto_galley_end_time_iso,
        "Status": "created",
        "Priority": 10, # High priority
        # "Notes" field will now store the JSON details for chaining.
        # The descriptive note can be part of the JSON or logged separately if needed.
        # For now, prioritizing the structured data for chaining.
        "Notes": json.dumps(pickup_details_for_goto) # Store details for chaining
    }
    try:
        created_goto_galley_activity = tables['activities'].create(goto_galley_payload)
        log.info(f"Created 'goto_location' (to galley) activity: {created_goto_galley_activity['id']}")
    except Exception as e:
        log.error(f"Failed to create 'goto_location' (to galley) activity for {citizen_username}: {e}")
        return None

    # --- Activity 2: Pickup from Galley ---
    pickup_start_time_iso = goto_galley_end_time_iso
    pickup_duration_minutes = 15 # Fixed time for pickup
    pickup_end_time_dt = datetime.datetime.fromisoformat(pickup_start_time_iso.replace("Z", "+00:00"))
    if pickup_end_time_dt.tzinfo is None: pickup_end_time_dt = pytz.UTC.localize(pickup_end_time_dt)
    pickup_end_time_iso = (pickup_end_time_dt + datetime.timedelta(minutes=pickup_duration_minutes)).isoformat()

    pickup_activity_id = f"pickup_galley_{citizen_custom_id}_{uuid.uuid4().hex[:8]}"
    delivery_details_for_pickup = {
        "action_on_completion": "goto_buyer_destination", # Instruction for processor if needed, or for clarity
        "resource_id": resource_id_to_fetch, # Carried over
        "amount": amount_to_fetch, # Carried over
        "final_destination_building_id": buyer_destination_building_record['fields'].get('BuildingId')
    }
    pickup_payload = {
        "ActivityId": pickup_activity_id,
        "Type": "pickup_from_galley", # New activity type
        "Citizen": citizen_username,
        "FromBuilding": galley_custom_id,
        "ContractId": original_contract_custom_id,
        "Resources": json.dumps([{"ResourceId": resource_id_to_fetch, "Amount": amount_to_fetch}]),
        "StartDate": pickup_start_time_iso,
        "EndDate": pickup_end_time_iso,
        "Status": "created",
        "Priority": 10,
        # "Notes" field will now store the JSON details for chaining.
        "Notes": json.dumps(delivery_details_for_pickup)
    }
    try:
        tables['activities'].create(pickup_payload)
        log.info(f"Created 'pickup_from_galley' activity: {pickup_activity_id}")
    except Exception as e:
        log.error(f"Failed to create 'pickup_from_galley' activity for {citizen_username}: {e}")
        # If this fails, the chain is broken. Consider cleanup or error handling.
        return created_goto_galley_activity # Return first activity even if subsequent ones fail for now

    # --- Activity 3: Go to Buyer's Destination ---
    from backend.engine.utils.activity_helpers import find_path_between_buildings_or_coords, _get_building_position_coords
    
    galley_pos = _get_building_position_coords(tables['buildings'].all(formula=f"{{BuildingId}}='{galley_custom_id}'", max_records=1)[0])
    buyer_dest_pos = _get_building_position_coords(buyer_destination_building_record)
    buyer_dest_id = buyer_destination_building_record['fields'].get('BuildingId')

    path_to_destination_data = None
    if galley_pos and buyer_dest_pos:
        path_to_destination_data = find_path_between_buildings_or_coords(tables, galley_pos, buyer_dest_pos, api_base_url, transport_api_url)
    
    goto_dest_start_time_iso = pickup_end_time_iso
    goto_dest_end_time_iso: str

    if path_to_destination_data and path_to_destination_data.get('success') and path_to_destination_data.get('timing', {}).get('durationSeconds') is not None:
        start_dt_obj = datetime.datetime.fromisoformat(goto_dest_start_time_iso.replace("Z", "+00:00"))
        if start_dt_obj.tzinfo is None: start_dt_obj = pytz.UTC.localize(start_dt_obj)
        duration_seconds = path_to_destination_data['timing']['durationSeconds']
        goto_dest_end_time_iso = (start_dt_obj + datetime.timedelta(seconds=duration_seconds)).isoformat()
    else:
        log.warning(f"Pathfinding from galley {galley_custom_id} to destination {buyer_dest_id} failed or no duration. Defaulting travel time.")
        start_dt_obj = datetime.datetime.fromisoformat(goto_dest_start_time_iso.replace("Z", "+00:00"))
        if start_dt_obj.tzinfo is None: start_dt_obj = pytz.UTC.localize(start_dt_obj)
        goto_dest_end_time_iso = (start_dt_obj + datetime.timedelta(minutes=30)).isoformat() # Default 30 mins

    goto_dest_activity_id = f"goto_dest_{citizen_custom_id}_{uuid.uuid4().hex[:8]}"
    final_delivery_details_for_goto = {
        "action_on_arrival": "deliver_resource_to_buyer",
        "resource_id": resource_id_to_fetch,
        "amount": amount_to_fetch,
        "target_building_id_on_arrival": buyer_dest_id
    }
    goto_dest_payload = {
        "ActivityId": goto_dest_activity_id,
        "Type": "goto_location",
        "Citizen": citizen_username,
        "FromBuilding": galley_custom_id, # Starting from galley
        "ToBuilding": buyer_dest_id,
        "Path": json.dumps(path_to_destination_data.get('path', []) if path_to_destination_data else []),
        "Transporter": path_to_destination_data.get('transporter') if path_to_destination_data else None,
        "StartDate": goto_dest_start_time_iso,
        "EndDate": goto_dest_end_time_iso,
        "Status": "created",
        "Priority": 10,
        # "Notes" field will now store the JSON details for chaining.
        "Notes": json.dumps(final_delivery_details_for_goto)
    }
    try:
        tables['activities'].create(goto_dest_payload)
        log.info(f"Created 'goto_location' (to buyer destination) activity: {goto_dest_activity_id}")
    except Exception as e:
        log.error(f"Failed to create 'goto_location' (to buyer destination) activity for {citizen_username}: {e}")
        return created_goto_galley_activity

    # --- Activity 4: Deliver Resource to Buyer Building ---
    delivery_start_time_iso = goto_dest_end_time_iso
    delivery_duration_minutes = 10 # Fixed time for delivery
    delivery_end_time_dt = datetime.datetime.fromisoformat(delivery_start_time_iso.replace("Z", "+00:00"))
    if delivery_end_time_dt.tzinfo is None: delivery_end_time_dt = pytz.UTC.localize(delivery_end_time_dt)
    delivery_end_time_iso = (delivery_end_time_dt + datetime.timedelta(minutes=delivery_duration_minutes)).isoformat()

    delivery_activity_id = f"deliver_buyer_{citizen_custom_id}_{uuid.uuid4().hex[:8]}"
    delivery_payload = {
        "ActivityId": delivery_activity_id,
        "Type": "deliver_resource_to_buyer", # New activity type
        "Citizen": citizen_username,
        "ToBuilding": buyer_dest_id, # Delivering to this building
        "Resources": json.dumps([{"ResourceId": resource_id_to_fetch, "Amount": amount_to_fetch}]),
        "ContractId": original_contract_custom_id, # Link back to original import contract
        "StartDate": delivery_start_time_iso,
        "EndDate": delivery_end_time_iso,
        "Status": "created",
        "Priority": 10,
        "Notes": f"Livre {amount_to_fetch:.2f} de {resource_id_to_fetch} à {buyer_dest_id}."
    }
    try:
        tables['activities'].create(delivery_payload)
        log.info(f"Created 'deliver_resource_to_buyer' activity: {delivery_activity_id}")
    except Exception as e:
        log.error(f"Failed to create 'deliver_resource_to_buyer' activity for {citizen_username}: {e}")
        return created_goto_galley_activity

    return created_goto_galley_activity # Return the first activity of the chain

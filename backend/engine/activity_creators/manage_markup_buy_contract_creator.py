import logging
from typing import Dict, List, Any, Optional

# Import LogColors from activity_helpers
from backend.engine.utils.activity_helpers import LogColors # This line was already present in the user's provided file, but the error suggests it might not have been effective or was missing in the deployed version. Let's ensure it's correctly placed.

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any], 
    citizen_record: Dict[str, Any], 
    activity_type: str, 
    activity_parameters: Dict[str, Any],
    resource_defs: Dict, # Added based on similar contract creators
    building_type_defs: Dict, # Added based on similar contract creators
    now_venice_dt: Any, # datetime
    now_utc_dt: Any, # datetime
    transport_api_url: str,
    api_base_url: str
) -> List[Dict[str, Any]]:
    """
    Creates activities for a citizen to create or update a markup buy contract.
    This involves travel to a market, then creating/updating the contract.
    """
    activities_created = []
    citizen_username = citizen_record['fields'].get('Username')
    
    contract_id_to_update = activity_parameters.get('contractId') # Optional: for updating existing contract
    resource_type = activity_parameters.get('resourceType')
    target_amount = activity_parameters.get('targetAmount')
    max_price_per_resource = activity_parameters.get('maxPricePerResource')
    buyer_building_id = activity_parameters.get('buyerBuildingId') # Where the goods should be delivered
    user_specified_market_id = activity_parameters.get('targetMarketBuildingId')

    if not resource_type or target_amount is None or max_price_per_resource is None or not buyer_building_id:
        log.error(f"{LogColors.FAIL}Missing required parameters for manage_markup_buy_contract for {citizen_username}. Params: {activity_parameters}{LogColors.ENDC}")
        return []

    log.info(f"{LogColors.ACTIVITY}Attempting to create 'manage_markup_buy_contract' chain for {citizen_username} for {resource_type}.{LogColors.ENDC}")

    # Imports moved up for clarity
    import json
    import uuid
    from datetime import timedelta
    from backend.engine.utils.activity_helpers import (
        find_path_between_buildings_or_coords, 
        get_closest_building_of_type, get_building_record,
        _get_building_position_coords, 
        clean_thought_content
    )

    # Fetch buyer building record first, as it's essential
    buyer_building_record = get_building_record(tables, buyer_building_id)
    if not buyer_building_record:
        log.error(f"{LogColors.FAIL}Buyer building {buyer_building_id} not found for {citizen_username}. Cannot create contract.{LogColors.ENDC}")
        return []

    # Imports
    import json
    import uuid
    from datetime import timedelta
    from backend.engine.utils.activity_helpers import (
        find_path_between_buildings_or_coords, 
        get_closest_building_of_type, get_building_record,
        _get_building_position_coords, # Added import
        clean_thought_content # Import the cleaning function
    )

    # 1. Determine citizen's current location
    citizen_position_str = citizen_record['fields'].get('Position')
    log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Citizen {citizen_username} Position string from Airtable: '{citizen_position_str}'{LogColors.ENDC}")
    from_location_data = None
    if citizen_position_str:
        try:
            pos_data = json.loads(citizen_position_str)
            if 'lat' in pos_data and 'lng' in pos_data: from_location_data = {"lat": pos_data['lat'], "lng": pos_data['lng']}
            elif 'building_id' in pos_data: from_location_data = {"building_id": pos_data['building_id']}
            log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Parsed pos_data: {pos_data}, derived from_location_data: {from_location_data}{LogColors.ENDC}")
        except json.JSONDecodeError:
            if isinstance(citizen_position_str, str) and citizen_position_str.startswith("bld_"): # Assuming "bld_" is a typo for a building ID prefix
                 from_location_data = {"building_id": citizen_position_str}
                 log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Position string looks like building_id: {citizen_position_str}. Using as from_location_data.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}[MarkupBuyCreator] Citizen {citizen_username} Position string '{citizen_position_str}' is not valid JSON and not a recognized building_id pattern.{LogColors.ENDC}")
    
    if not from_location_data:
        log.warning(f"{LogColors.WARNING}[MarkupBuyCreator] Citizen {citizen_username} has no valid current location data (from_location_data is None). Cannot create manage_markup_buy_contract.{LogColors.ENDC}")
        return []

    actual_from_coords: Optional[Dict[str, float]] = None
    if from_location_data:
        if 'lat' in from_location_data and 'lng' in from_location_data:
            actual_from_coords = from_location_data
        elif 'building_id' in from_location_data:
            start_building_id = from_location_data['building_id']
            log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Resolving coordinates for start_building_id: '{start_building_id}'{LogColors.ENDC}")
            # Ensure start_building_id is a string if it came from a list/tuple
            if isinstance(start_building_id, (list, tuple)) and start_building_id:
                start_building_id = start_building_id[0]
            
            if isinstance(start_building_id, str):
                start_building_rec = get_building_record(tables, start_building_id)
                if start_building_rec:
                    actual_from_coords = _get_building_position_coords(start_building_rec)
                    log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Resolved actual_from_coords: {actual_from_coords} for building {start_building_id}{LogColors.ENDC}")
                else: # Failed to get building record
                    log.warning(f"{LogColors.WARNING}[MarkupBuyCreator] Could not find building record for start_building_id '{start_building_id}' for {citizen_username}.{LogColors.ENDC}")
                    return [] # Cannot proceed without start coordinates
                if not actual_from_coords: # Failed to get coords from building_id
                    log.warning(f"{LogColors.WARNING}[MarkupBuyCreator] Could not resolve coordinates for starting building_id '{start_building_id}' for {citizen_username}.{LogColors.ENDC}")
                    return []
            else:
                log.warning(f"{LogColors.WARNING}[MarkupBuyCreator] Invalid building_id type in from_location_data for {citizen_username}: {start_building_id}.{LogColors.ENDC}")
                return []
    
    if not actual_from_coords:
        log.warning(f"{LogColors.WARNING}[MarkupBuyCreator] Citizen {citizen_username} has no valid resolved current coordinates (actual_from_coords is None). Cannot create manage_markup_buy_contract.{LogColors.ENDC}")
        return []
    log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Citizen {citizen_username} actual_from_coords for pathfinding: {actual_from_coords}{LogColors.ENDC}")

    # 2. Determine the target market building
    # Simplified: Contract finalization always occurs at the buyer's building.
    target_market_record = buyer_building_record
    target_market_building_id = buyer_building_id
    log.info(f"{LogColors.ACTIVITY}Contract finalization for {citizen_username} will occur at buyer's building: {buyer_building_id}.{LogColors.ENDC}")

    # 3. Create goto_location activity
    # Use actual_from_coords as the starting point for pathfinding
    log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Pathfinding for {citizen_username}: From {actual_from_coords} to target market (buyer building) {target_market_building_id}.{LogColors.ENDC}")
    path_data = find_path_between_buildings_or_coords(tables, actual_from_coords, {"building_id": target_market_building_id}, api_base_url, transport_api_url)
    current_end_time_utc = now_utc_dt

    if path_data and path_data.get("path"):
        log.info(f"{LogColors.ACTIVITY}[MarkupBuyCreator] Path found for {citizen_username} to {target_market_building_id}. Path details: {json.dumps(path_data)[:200]}...{LogColors.ENDC}")
        path_json = json.dumps(path_data["path"])
        travel_duration_minutes = path_data.get("duration_minutes", 30)
        
        goto_activity_id = str(uuid.uuid4())
        goto_start_time_utc = now_utc_dt
        goto_end_time_utc = goto_start_time_utc + timedelta(minutes=travel_duration_minutes)
        current_end_time_utc = goto_end_time_utc

        goto_activity_notes_payload = {
            "activityType": "manage_markup_buy_contract", # Overall endeavor
            "nextStep": "finalize_manage_markup_buy_contract", # What happens after this goto
            "contractIdToManage": activity_parameters.get("contractId_to_create_if_new"), # Pass this ID
            "resourceType": resource_type,
            "targetAmount": target_amount,
            "maxPricePerResource": max_price_per_resource,
            "buyerBuildingId": buyer_building_id,
            "targetMarketBuildingId": target_market_building_id,
            # Pass through details needed by the finalize step for contract creation/update
            "sellerBuildingId_for_contract": activity_parameters.get("sellerBuildingId"),
            "sellerUsername_for_contract": activity_parameters.get("sellerUsername"),
            "title_for_contract": activity_parameters.get("title"),
            "description_for_contract": activity_parameters.get("description"),
            "notes_for_contract_field": activity_parameters.get("notes") # This is the dict for the contract's Notes field
        }
        # Removed: if contract_id_to_update: goto_activity_notes_payload["contractIdToUpdate"] = contract_id_to_update

        goto_title = f"Travel to {target_market_record['fields'].get('Name', target_market_building_id)}"
        goto_description = f"{citizen_username} is traveling to manage a markup buy contract."
        goto_thought = f"I need to visit the market at {target_market_record['fields'].get('Name', target_market_building_id)} to place my buy order."

        goto_activity = {
            "ActivityId": goto_activity_id, "Citizen": citizen_username, "Type": "goto_location", "Status": "created",
            "StartDate": goto_start_time_utc.isoformat(), "EndDate": goto_end_time_utc.isoformat(),
            "ToBuilding": target_market_building_id, "Path": path_json,
            "TransportMode": path_data.get("transport_mode", "walk"),
            "Title": clean_thought_content(tables, goto_title),
            "Description": clean_thought_content(tables, goto_description),
            "Thought": clean_thought_content(tables, goto_thought),
            "Notes": json.dumps(goto_activity_notes_payload), # Notes (JSON string) are not cleaned by default by clean_thought_content
            "Priority": 20
            # "CreatedAt" and "UpdatedAt" will be set by the dispatcher
        }
        activities_created.append(goto_activity)
        log.info(f"{LogColors.ACTIVITY}Created goto_location activity {goto_activity_id} for {citizen_username}. Duration: {travel_duration_minutes} mins.{LogColors.ENDC}")
    else:
        log.warning(f"{LogColors.WARNING}No path found for {citizen_username} to {target_market_building_id}. Finalize activity will start immediately.{LogColors.ENDC}")

    # 4. Create finalize_manage_markup_buy_contract activity
    finalize_activity_id = str(uuid.uuid4())
    finalize_duration_minutes = 15 
    finalize_start_time_utc = current_end_time_utc
    finalize_end_time_utc = finalize_start_time_utc + timedelta(minutes=finalize_duration_minutes)

    finalize_activity_details = {
        "contractIdToManage": activity_parameters.get("contractId_to_create_if_new"), # Pass this ID
        "resourceType": resource_type,
        "targetAmount": target_amount,
        "maxPricePerResource": max_price_per_resource,
        "buyerBuildingId": buyer_building_id,
        "buyerUsername": citizen_username, # This is the activity performer
        # Pass through details needed for contract creation/update
        "sellerBuildingId_for_contract": activity_parameters.get("sellerBuildingId"),
        "sellerUsername_for_contract": activity_parameters.get("sellerUsername"),
        "title_for_contract": activity_parameters.get("title"),
        "description_for_contract": activity_parameters.get("description"),
        "notes_for_contract_field": activity_parameters.get("notes") # This is the dict for the contract's Notes field
    }
    # Removed: if contract_id_to_update: finalize_activity_details["contractIdToUpdate"] = contract_id_to_update

    finalize_title = f"Manage Markup Buy Contract for {resource_type}"
    finalize_description = f"{citizen_username} is finalizing a markup buy contract for {target_amount} of {resource_type} at a max price of {max_price_per_resource} each."
    finalize_thought = "Let's make this buy order official."

    finalize_activity = {
        "ActivityId": finalize_activity_id, "Citizen": citizen_username, "Type": "finalize_manage_markup_buy_contract", "Status": "created",
        "StartDate": finalize_start_time_utc.isoformat(), "EndDate": finalize_end_time_utc.isoformat(),
        "FromBuilding": target_market_building_id, 
        "Notes": json.dumps(finalize_activity_details), # Notes (JSON string) are not cleaned by default
        "Title": clean_thought_content(tables, finalize_title),
        "Description": clean_thought_content(tables, finalize_description),
        "Thought": clean_thought_content(tables, finalize_thought),
        "Priority": 20
        # "CreatedAt" and "UpdatedAt" will be set by the dispatcher
    }
    activities_created.append(finalize_activity)
    log.info(f"{LogColors.ACTIVITY}Created finalize_manage_markup_buy_contract activity {finalize_activity_id} for {citizen_username}.{LogColors.ENDC}")

    return activities_created

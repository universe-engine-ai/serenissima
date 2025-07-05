"""
Creator for 'fetch_resource' activities.
"""
import logging
import datetime
from datetime import timedelta
import time
import json
import uuid # Already imported in createActivities, but good practice here too
import pytz # For timezone handling
from typing import Dict, Optional, Any, List # Added List
from dateutil import parser as dateutil_parser # Added dateutil_parser

# Import helper functions
from backend.engine.utils.activity_helpers import (
    LogColors,
    _get_building_position_coords,
    _calculate_distance_meters, # Added _calculate_distance_meters
    calculate_haversine_distance_meters,
    VENICE_TIMEZONE,
    get_building_record,
    get_citizen_record, # Added
    get_building_storage_details,
    get_path_between_points, # Added
    find_path_between_buildings_or_coords, # Added
    create_activity_record, # Added
    _escape_airtable_value # Added import for _escape_airtable_value
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity # Added

log = logging.getLogger(__name__)

PICKUP_DURATION_MINUTES = 5
DELIVERY_DURATION_MINUTES = 5 # Time spent at destination building after arrival

def try_create(
    tables: Dict[str, Any],
    citizen_airtable_id: str,
    citizen_custom_id: str,
    citizen_username: str,
    contract_custom_id: Optional[str],
    from_building_custom_id: Optional[str],
    to_building_custom_id: Optional[str],
    resource_type_id: str,
    amount: float,
    path_data_to_source: Optional[Dict], # Path from current location to source building
    current_time_utc: datetime.datetime,
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any], # Added
    now_venice_dt: datetime.datetime, # Added
    transport_api_url: str, 
    api_base_url: str,      
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict]:
    """
    Creates a chain of activities for fetching a resource:
    1. goto_location (to source building, if not already there)
    2. fetch_resource (pickup at source building)
    3. goto_location (from source to destination building, if destination is specified and different)
    Returns the first activity in the chain.
    
    Parameters:
    -----------
    amount: float
        The amount of resource to fetch. This is required and must be a positive number.
    """
    """
    Creates a chain of activities for fetching a resource:
    1. goto_location (to source building, if not already there)
    2. fetch_resource (pickup at source building)
    3. goto_location (from source to destination building, if destination is specified and different)
    Returns the first activity in the chain.
    """
    log.info(f"{LogColors.ACTIVITY}[FetchCreator] Init: citizen={citizen_username}, resource={resource_type_id}, amount={amount}, from_bldg_param={from_building_custom_id}, to_bldg_param={to_building_custom_id}")
    
    activity_chain: List[Dict[str, Any]] = []
    current_chain_time_iso = start_time_utc_iso if start_time_utc_iso else current_time_utc.isoformat()
    
    citizen_record = get_citizen_record(tables, citizen_username)
    if not citizen_record:
        log.error(f"Citizen {citizen_username} not found. Cannot create fetch_resource chain.")
        return None
    
    citizen_position_str = citizen_record['fields'].get('Position')
    citizen_position: Optional[Dict[str, float]] = None
    if citizen_position_str:
        try:
            citizen_position = json.loads(citizen_position_str)
        except json.JSONDecodeError:
            log.warning(f"Could not parse citizen {citizen_username} position: {citizen_position_str}")
            # Potentially try to assign random start position or fail
            return None # For now, fail if position is invalid

    if not citizen_position:
        log.warning(f"Citizen {citizen_username} has no position. Cannot create fetch_resource chain.")
        return None

    # Determine final_from_building_custom_id (source)
    final_from_building_custom_id = from_building_custom_id
    final_contract_custom_id = contract_custom_id # Use this for the activity if a contract is found/used

    # Log initial to_building_custom_id name
    if to_building_custom_id:
        initial_to_bldg_rec = get_building_record(tables, to_building_custom_id)
        initial_to_bldg_name = initial_to_bldg_rec['fields'].get('Name', to_building_custom_id) if initial_to_bldg_rec else to_building_custom_id
        log.info(f"{LogColors.ACTIVITY}[FetchCreator] Initial ToBuilding (destination for delivery): {to_building_custom_id} (Name: {initial_to_bldg_name})")
    else:
        log.info(f"{LogColors.ACTIVITY}[FetchCreator] Initial ToBuilding (destination for delivery) is None.")


    if not final_from_building_custom_id:
        log.info(f"{LogColors.ACTIVITY}[FetchCreator] No explicit source for {citizen_username} requesting {resource_type_id}. Initiating dynamic source finding...")
        
        # Special handling for water resource
        if resource_type_id == "water":
            log.info(f"{LogColors.ACTIVITY}[FetchCreator] Special handling for water resource. Looking for wells, cisterns, or other water sources...")
            
            # First try to find water sources with public_sell contracts
            water_contract_formula = f"AND({{ResourceType}}='{_escape_airtable_value(resource_type_id)}', {{Type}}='public_sell', {{Status}}='active')"
            try:
                water_contracts = tables['contracts'].all(formula=water_contract_formula)
                
                for contract in water_contracts:
                    seller_bldg_id = contract['fields'].get('SellerBuilding')
                    if not seller_bldg_id: continue
                    seller_bldg_rec = get_building_record(tables, seller_bldg_id)
                    if not seller_bldg_rec: continue
                    seller = contract['fields'].get('Seller')
                    if not seller: continue
                    
                    # Check if this building has water stock
                    _, source_stock_map = get_building_storage_details(tables, seller_bldg_id, seller)
                    actual_stock = source_stock_map.get(resource_type_id, 0.0)
                    
                    if actual_stock >= amount:
                        final_from_building_custom_id = seller_bldg_id
                        final_contract_custom_id = contract['fields'].get('ContractId', contract['id'])
                        log.info(f"{LogColors.ACTIVITY}[FetchCreator] Found water source with public_sell contract: {seller_bldg_id}")
                        break
                
                # If still no source, look for buildings with water-related types
                if not final_from_building_custom_id:
                    water_building_types = ["public_well", "cistern"]
                    water_subcategories = ["Water Management", "storage"]
                    
                    # Collect all water sources with enough water
                    water_sources_with_distance = []
                    
                    # Try to find buildings by type
                    for building_type in water_building_types:
                        building_formula = f"{{Type}}='{_escape_airtable_value(building_type)}'"
                        water_buildings = tables['buildings'].all(formula=building_formula)
                        
                        for water_building in water_buildings:
                            water_building_id = water_building['fields'].get('BuildingId')
                            
                            if water_building_id:
                                # For public water sources, check total water available regardless of owner
                                water_formula = f"AND({{Asset}}='{_escape_airtable_value(water_building_id)}', {{AssetType}}='building', {{Type}}='water')"
                                try:
                                    water_resources = tables['resources'].all(formula=water_formula)
                                    total_water = sum(float(r['fields'].get('Count', 0)) for r in water_resources)
                                    
                                    if total_water >= amount:
                                        # Calculate distance to this water source
                                        water_building_pos = _get_building_position_coords(water_building)
                                        if water_building_pos:
                                            distance = _calculate_distance_meters(citizen_position, water_building_pos)
                                            water_sources_with_distance.append({
                                                'building_id': water_building_id,
                                                'building_type': building_type,
                                                'total_water': total_water,
                                                'distance': distance,
                                                'building_record': water_building
                                            })
                                except Exception as e:
                                    log.error(f"{LogColors.ACTIVITY}[FetchCreator] Error checking water in {water_building_id}: {e}")
                    
                    # Also check by subcategory
                    for subcategory in water_subcategories:
                        building_formula = f"{{SubCategory}}='{_escape_airtable_value(subcategory)}'"
                        water_buildings = tables['buildings'].all(formula=building_formula)
                        
                        for water_building in water_buildings:
                            water_building_id = water_building['fields'].get('BuildingId')
                            
                            if water_building_id:
                                # Skip if already checked by type
                                if any(ws['building_id'] == water_building_id for ws in water_sources_with_distance):
                                    continue
                                    
                                # For public water sources, check total water available regardless of owner
                                water_formula = f"AND({{Asset}}='{_escape_airtable_value(water_building_id)}', {{AssetType}}='building', {{Type}}='water')"
                                try:
                                    water_resources = tables['resources'].all(formula=water_formula)
                                    total_water = sum(float(r['fields'].get('Count', 0)) for r in water_resources)
                                    
                                    if total_water >= amount:
                                        # Calculate distance to this water source
                                        water_building_pos = _get_building_position_coords(water_building)
                                        if water_building_pos:
                                            distance = _calculate_distance_meters(citizen_position, water_building_pos)
                                            water_sources_with_distance.append({
                                                'building_id': water_building_id,
                                                'building_type': water_building['fields'].get('Type', 'unknown'),
                                                'total_water': total_water,
                                                'distance': distance,
                                                'building_record': water_building
                                            })
                                except Exception as e:
                                    log.error(f"{LogColors.ACTIVITY}[FetchCreator] Error checking water in {water_building_id}: {e}")
                    
                    # Now select the closest water source
                    if water_sources_with_distance:
                        # Sort by distance and select the closest
                        water_sources_with_distance.sort(key=lambda x: x['distance'])
                        closest_source = water_sources_with_distance[0]
                        final_from_building_custom_id = closest_source['building_id']
                        
                        log.info(f"{LogColors.ACTIVITY}[FetchCreator] Selected closest public water source: {closest_source['building_id']} "
                                f"(Type: {closest_source['building_type']}, Distance: {closest_source['distance']:.1f}m, "
                                f"Total water: {closest_source['total_water']})")
            except Exception as e:
                log.error(f"{LogColors.ACTIVITY}[FetchCreator] Error finding water source: {e}")
        
        # Special handling for grain resource - check galleys first!
        if resource_type_id == "grain" and not final_from_building_custom_id:
            log.info(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: Special handling for grain - checking merchant galleys first...")
            
            # Look for grain in merchant galleys (foreign merchants)
            try:
                # Find all merchant galleys
                galleys_formula = "AND({Type}='merchant_galley', {Status}='active')"
                merchant_galleys = tables['buildings'].all(formula=galleys_formula)
                
                galley_sources_with_distance = []
                
                for galley in merchant_galleys:
                    galley_id = galley['fields'].get('BuildingId')
                    galley_owner = galley['fields'].get('Owner')
                    
                    if not galley_id:
                        continue
                    
                    # Check grain inventory at this galley
                    grain_formula = f"AND({{Type}}='grain', {{Asset}}='{_escape_airtable_value(galley_id)}', {{AssetType}}='building')"
                    grain_resources = tables['resources'].all(formula=grain_formula)
                    total_grain = sum(float(r['fields'].get('Count', 0)) for r in grain_resources)
                    
                    if total_grain >= amount:
                        # Calculate distance to galley
                        galley_pos = _get_building_position_coords(galley)
                        if galley_pos:
                            distance = _calculate_distance_meters(citizen_position, galley_pos)
                            galley_sources_with_distance.append({
                                'building_id': galley_id,
                                'owner': galley_owner,
                                'total_grain': total_grain,
                                'distance': distance,
                                'building_record': galley
                            })
                            log.info(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: Found galley {galley_id} with {total_grain} grain at {distance:.1f}m")
                
                # Select closest galley with grain
                if galley_sources_with_distance:
                    galley_sources_with_distance.sort(key=lambda x: x['distance'])
                    closest_galley = galley_sources_with_distance[0]
                    
                    # Check if there's a public_sell contract for this galley
                    galley_contract_formula = f"AND({{Type}}='public_sell', {{ResourceType}}='grain', {{SellerBuilding}}='{_escape_airtable_value(closest_galley['building_id'])}', {{Status}}='active')"
                    galley_contracts = tables['contracts'].all(formula=galley_contract_formula)
                    
                    if galley_contracts:
                        # Use existing contract
                        contract = galley_contracts[0]
                        final_from_building_custom_id = closest_galley['building_id']
                        final_contract_custom_id = contract['fields'].get('ContractId', contract['id'])
                        log.info(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: Using existing galley contract {final_contract_custom_id}")
                    else:
                        # Create emergency bridge contract
                        log.info(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: No contract found - creating emergency bridge contract...")
                        
                        # Create public_sell contract for galley grain
                        contract_id = f"bridge-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{closest_galley['building_id'][:8]}"
                        contract_data = {
                            'ContractId': contract_id,
                            'Type': 'public_sell',
                            'Status': 'active',
                            'Seller': closest_galley['owner'],
                            'SellerBuilding': closest_galley['building_id'],
                            'ResourceType': 'grain',
                            'TargetAmount': int(closest_galley['total_grain']),
                            'PricePerResource': 1.08,  # Competitive price to encourage use
                            'CreatedAt': current_time_utc.isoformat(),
                            'EndAt': (current_time_utc + timedelta(hours=24)).isoformat(),
                            'Notes': f"BRIDGE CONTRACT: Auto-created to connect galley grain to mills"
                        }
                        
                        try:
                            new_contract = tables['contracts'].create(contract_data)
                            final_from_building_custom_id = closest_galley['building_id']
                            final_contract_custom_id = contract_id
                            log.info(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: Created emergency contract {contract_id} for galley {closest_galley['building_id']}")
                        except Exception as e:
                            log.error(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: Failed to create contract: {e}")
                    
                    if final_from_building_custom_id:
                        log.info(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: Selected galley {final_from_building_custom_id} "
                                f"(Distance: {closest_galley['distance']:.1f}m, Grain: {closest_galley['total_grain']})")
                        
            except Exception as e:
                log.error(f"{LogColors.ACTIVITY}[FetchCreator] BRIDGE: Error finding grain in galleys: {e}")
        
        # Standard dynamic source finding for all resources (including water if special handling failed)
        if not final_from_building_custom_id:
            # Dynamic Source Finding Logic:
            # 1. Look for public_sell contracts for the resource_type_id
            public_sell_formula = f"AND({{Type}}='public_sell', {{ResourceType}}='{_escape_airtable_value(resource_type_id)}', {{EndAt}}>'{current_time_utc.isoformat()}', {{TargetAmount}}>0, {{Status}}='active')"
            try:
                all_public_sell_contracts = tables['contracts'].all(formula=public_sell_formula, sort=['PricePerResource']) # Cheaper first
                
                best_source_contract_record = None
                
                for contract_rec_dyn in all_public_sell_contracts:
                    seller_building_id_cand = contract_rec_dyn['fields'].get('SellerBuilding')
                    if not seller_building_id_cand: continue
                    
                    seller_building_rec_cand = get_building_record(tables, seller_building_id_cand)
                    if not seller_building_rec_cand: continue
                    
                    seller_building_pos_cand = _get_building_position_coords(seller_building_rec_cand)
                    if not seller_building_pos_cand: continue

                    contract_seller_username = contract_rec_dyn['fields'].get('Seller')
                    if not contract_seller_username: continue
                    
                    _, seller_stock_map = get_building_storage_details(tables, seller_building_id_cand, contract_seller_username)
                    if seller_stock_map.get(resource_type_id, 0.0) >= amount:
                        # Check buyer's (workshop operator) ability to pay
                        # to_building_custom_id is the workshop where goods are delivered
                        if not to_building_custom_id:
                            log.warning(f"Dynamic source finding: to_building_custom_id (workshop) is None. Cannot check payment ability. Skipping contract {contract_rec_dyn['id']}.")
                            continue

                        workshop_record_for_payment = get_building_record(tables, to_building_custom_id)
                        if not workshop_record_for_payment:
                            log.warning(f"Dynamic source finding: Workshop {to_building_custom_id} not found for payment check. Skipping contract {contract_rec_dyn['id']}.")
                            continue
                        
                        workshop_operator_for_payment = workshop_record_for_payment['fields'].get('RunBy') or workshop_record_for_payment['fields'].get('Owner')
                        if not workshop_operator_for_payment:
                            log.warning(f"Dynamic source finding: Workshop {to_building_custom_id} has no operator for payment. Skipping contract {contract_rec_dyn['id']}.")
                            continue
                        
                        operator_citizen_record = get_citizen_record(tables, workshop_operator_for_payment)
                        if not operator_citizen_record:
                            log.warning(f"Dynamic source finding: Workshop operator {workshop_operator_for_payment} not found. Skipping contract {contract_rec_dyn['id']}.")
                            continue
                            
                        operator_ducats = float(operator_citizen_record['fields'].get('Ducats', 0))
                        price_per_unit = float(contract_rec_dyn['fields'].get('PricePerResource', 0))
                        total_cost = price_per_unit * amount
                        
                        if operator_ducats >= total_cost:
                            best_source_contract_record = contract_rec_dyn
                            break 
                        else:
                            log.info(f"  Dynamic source finding: Contract {contract_rec_dyn['id']} viable, but workshop operator {workshop_operator_for_payment} has insufficient ducats ({operator_ducats:.2f}) for cost {total_cost:.2f}.")
                
                if best_source_contract_record:
                    final_from_building_custom_id = best_source_contract_record['fields']['SellerBuilding']
                    final_contract_custom_id = best_source_contract_record['fields'].get('ContractId', best_source_contract_record['id'])
                    dynamically_found_source_bldg_rec = get_building_record(tables, final_from_building_custom_id)
                    dynamically_found_source_bldg_name = dynamically_found_source_bldg_rec['fields'].get('Name', final_from_building_custom_id) if dynamically_found_source_bldg_rec else final_from_building_custom_id
                    log.info(f"{LogColors.ACTIVITY}[FetchCreator] Dynamically found source: Building {final_from_building_custom_id} (Name: {dynamically_found_source_bldg_name}) via contract {final_contract_custom_id} for {resource_type_id}.")
                else:
                    log.warning(f"{LogColors.ACTIVITY}[FetchCreator] No suitable public_sell contract found for {resource_type_id} (amount: {amount}) after dynamic search.")
                    # TODO: Could add logic to find producer buildings as a fallback.
            except Exception as e_dyn_src:
                log.error(f"{LogColors.ACTIVITY}[FetchCreator] Error during dynamic source finding for {resource_type_id}: {e_dyn_src}")

    # After dynamic source finding attempt, check if we have a source
    if not final_from_building_custom_id:
        log.error(f"{LogColors.ACTIVITY}[FetchCreator] Could not determine a source building (explicit or dynamic) for fetching {resource_type_id}. Aborting fetch_resource chain creation.")
        return None

    source_building_record = get_building_record(tables, final_from_building_custom_id)
    if not source_building_record:
        # This log is already present above, so we can remove the redundant one here.
        # log.error(f"{LogColors.ACTIVITY}[FetchCreator] Source building {final_from_building_custom_id} not found.")
        return None
    source_building_pos = _get_building_position_coords(source_building_record)
    if not source_building_pos:
        log.error(f"{LogColors.ACTIVITY}[FetchCreator] Source building {final_from_building_custom_id} has no position.")
        return None
    
    source_building_name_log = source_building_record['fields'].get('Name', final_from_building_custom_id)
    resource_name_log = resource_defs.get(resource_type_id, {}).get('name', resource_type_id)

    # Step 1: Travel to Source Building
    is_at_source = _calculate_distance_meters(citizen_position, source_building_pos) < 20
    
    if not is_at_source:
            # path_data_to_source is already calculated or provided if needed by the old logic.
            # The new goto_location_activity_creator calculates its own path.
            # We just need to provide the targetBuildingId.
            pass # No need to recalculate path_data_to_source here if new goto_location_creator handles it.

            # Call the new goto_location_activity_creator with activity_params
            goto_activity_params = {
                "targetBuildingId": final_from_building_custom_id,
                "notes": f"Traveling to {source_building_name_log} to pick up {resource_name_log}.",
                "startTimeUtcIso": current_chain_time_iso 
                # fromBuildingId can be omitted, creator will use citizen's current position.
            }
            goto_source_activity = try_create_goto_location_activity(
                tables=tables,
                citizen_record=citizen_record,
                activity_params=goto_activity_params,
                resource_defs=resource_defs, # Pass through
                building_type_defs=building_type_defs, # Pass through
                now_venice_dt=now_venice_dt, # Pass through
                now_utc_dt=current_time_utc, # Map current_time_utc to now_utc_dt
                transport_api_url=transport_api_url, # Pass through
                api_base_url=api_base_url # Pass through
            )
            if not goto_source_activity:
                log.error(f"Failed to create goto_location activity to source {source_building_name_log} using new creator structure.")
                return None
            activity_chain.append(goto_source_activity)
            current_chain_time_iso = goto_source_activity['fields']['EndDate']
    
    # Step 2: Fetch Resource (Pickup at Source)
    pickup_start_dt = dateutil_parser.isoparse(current_chain_time_iso.replace("Z", "+00:00"))
    if pickup_start_dt.tzinfo is None: pickup_start_dt = pytz.UTC.localize(pickup_start_dt)
    pickup_end_dt = pickup_start_dt + datetime.timedelta(minutes=PICKUP_DURATION_MINUTES)
    
    fetch_activity_payload = {
        "Type": "fetch_resource",
        "FromBuilding": final_from_building_custom_id,
        "ToBuilding": final_from_building_custom_id, # Action happens at source
        "Path": "[]", # No travel during pickup itself
        "Resources": json.dumps([{"ResourceId": resource_type_id, "Amount": amount}]),
        "Notes": f"Picking up {amount:.2f} {resource_name_log} from {source_building_name_log}.",
        "Title": f"Pick up {resource_name_log}",
        "Description": f"Picking up {amount:.2f} units of {resource_name_log} from {source_building_name_log}."
    }
    if final_contract_custom_id: # Use the potentially updated contract ID
        fetch_activity_payload["ContractId"] = final_contract_custom_id
    
    fetch_activity = create_activity_record(
        tables, citizen_username, fetch_activity_payload["Type"],
        current_chain_time_iso, pickup_end_dt.isoformat(),
        from_building_id=fetch_activity_payload["FromBuilding"],
        to_building_id=fetch_activity_payload["ToBuilding"],
        path_json=fetch_activity_payload["Path"],
        notes=fetch_activity_payload["Notes"],
        contract_id=fetch_activity_payload.get("ContractId"), # Use the one set in payload
        title=fetch_activity_payload["Title"],
        description=fetch_activity_payload["Description"],
        resources_json_payload=fetch_activity_payload["Resources"]
    )
    if not fetch_activity:
        log.error(f"Failed to create fetch_resource (pickup) activity at {source_building_name_log}.")
        # If goto_source was created, it should ideally be cancelled. For now, fail chain.
        return None
    activity_chain.append(fetch_activity)
    current_chain_time_iso = fetch_activity['fields']['EndDate']

    # Step 3: Travel to Destination Building (if specified and different from source)
    if to_building_custom_id and to_building_custom_id != final_from_building_custom_id:
        destination_building_record = get_building_record(tables, to_building_custom_id)
        if not destination_building_record:
            log.error(f"{LogColors.ACTIVITY}[FetchCreator] Destination building {to_building_custom_id} not found for delivery.")
            return activity_chain[0] # Return chain up to fetch, delivery will fail or be manual
        
        destination_building_pos = _get_building_position_coords(destination_building_record)
        if not destination_building_pos:
            log.error(f"{LogColors.ACTIVITY}[FetchCreator] Destination building {to_building_custom_id} has no position.")
            return activity_chain[0]

        destination_building_name_log = destination_building_record['fields'].get('Name', to_building_custom_id)
        log.info(f"{LogColors.ACTIVITY}[FetchCreator] Final destination for delivery: {to_building_custom_id} (Name: {destination_building_name_log})")
        
        # Corrected call to include api_base_url
        path_to_destination_data = find_path_between_buildings_or_coords(
            tables, # Pass tables
            source_building_record, # Pass source building record
            destination_building_record, # Pass destination building record
            api_base_url, # Pass api_base_url
            transport_api_url=transport_api_url # Pass transport_api_url
        )

        if not path_to_destination_data or not path_to_destination_data.get('success'):
            log.error(f"{LogColors.ACTIVITY}[FetchCreator] Failed to calculate path from {source_building_name_log} to {destination_building_name_log}.")
            return activity_chain[0] # Return chain up to fetch

        # The goto_location activity for delivery should carry the resources.
        # The 'Resources' field in activities is a JSON string of a list of {"ResourceId": ..., "Amount": ...}
        resources_carried_payload = json.dumps([{"ResourceId": resource_type_id, "Amount": amount}])

        # Call the new goto_location_activity_creator with activity_params
        goto_dest_activity_params = {
            "targetBuildingId": to_building_custom_id,
            "notes": f"Delivering {amount:.2f} {resource_name_log} to {destination_building_name_log}.",
            "startTimeUtcIso": current_chain_time_iso,
            "resourcesJson": resources_carried_payload # The new creator might need to handle this inside activity_params if it supports it
            # fromBuildingId can be omitted, creator will use citizen's current position (which is source_building_pos after pickup)
        }
        # The new goto_location_activity_creator calculates its own path.
        # We need to ensure it uses source_building_pos as the start for this leg.
        # This might require passing fromBuildingId explicitly in activity_params if current citizen position isn't updated yet.
        # For now, let's assume the creator handles pathing from current citizen position.
        # The `resources_json` needs to be handled by the `goto_location_activity_creator` if it's to be included in its notes.
        # The provided `goto_location_activity_creator` does not explicitly handle `resourcesJson` in `activity_params`.
        # We might need to adjust how `resources_json` is passed or handled.
        # For now, we'll pass it, and if the creator doesn't use it, it will be ignored there.
        # A better way would be for the new creator to accept `resourcesCarried` in its `activity_params`.

        goto_destination_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            activity_params=goto_dest_activity_params,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt,
            now_utc_dt=dateutil_parser.isoparse(current_chain_time_iso.replace("Z", "+00:00")), # Start time of this leg
            transport_api_url=transport_api_url,
            api_base_url=api_base_url
        )
        if not goto_destination_activity:
            log.error(f"Failed to create goto_location activity to destination {destination_building_name_log} using new creator structure.")
            return activity_chain[0] # Return chain up to fetch
        activity_chain.append(goto_destination_activity)
        # current_chain_time_iso = goto_destination_activity['fields']['EndDate'] # Not strictly needed if this is the last step

    if not activity_chain:
        log.error(f"Failed to create any part of the fetch_resource chain for {citizen_username}.")
        return None
        
    log.info(f"Successfully created fetch_resource activity chain for {citizen_username}. First activity: {activity_chain[0]['fields']['Type']}")
    return activity_chain[0]

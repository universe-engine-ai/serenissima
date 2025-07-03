import json
import uuid
import logging
import time # Import time for performance measurement
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from backend.engine.utils.activity_helpers import (
    _escape_airtable_value, 
    VENICE_TIMEZONE,
    find_path_between_buildings_or_coords, # Changed from find_path_between_buildings
    get_building_record,
    get_citizen_record,
    get_closest_building_of_type, # Added import
    _get_building_position_coords, # Added import
    calculate_haversine_distance_meters, # Added import
    clean_thought_content # Added import
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    activity_type_param: str, # Added - though not directly used if creator is specific
    details: Dict[str, Any],  # This is activity_parameters from dispatcher
    resource_defs: Dict[str, Any], # Added
    building_type_defs: Dict[str, Any], # Added
    now_venice_dt: datetime, # Added
    now_utc_dt_param: datetime, # Added - renamed to avoid conflict with internal now_utc
    transport_api_url: str, # Added
    api_base_url: str # Added
) -> Optional[List[Dict[str, Any]]]: # Return type changed to Optional[List[Dict]]
    """
    Create the complete manage_public_sell_contract activity chain:
    1. A goto_location activity for travel to the seller's building to prepare goods
    2. A prepare_goods_for_sale activity at the seller's building
    3. A goto_location activity for travel to the market
    4. A register_public_sell_offer activity to finalize the contract creation/modification
    
    This approach creates the complete activity chain upfront.
    """
    # Extract required parameters
    contract_id = details.get('contractId')  # Optional, only if modifying existing contract
    resource_type = details.get('resourceType')
    price_per_resource = details.get('pricePerResource')
    target_amount = details.get('targetAmount')
    seller_building_id = details.get('sellerBuildingId')
    target_market_building_id = details.get('targetMarketBuildingId')
    
    # Validate required parameters (targetMarketBuildingId is now optional here, will be determined if not provided)
    if not (resource_type and price_per_resource is not None and target_amount is not None and
            seller_building_id):
        log.error(f"Missing required details for manage_public_sell_contract: resourceType, pricePerResource, targetAmount, or sellerBuildingId")
        return None

    citizen_username = citizen_record['fields'].get('Username')
    # Use the passed now_venice_dt for timestamp consistency
    ts = int(now_venice_dt.timestamp())
    
    # Get current citizen position to determine first path
    citizen_position_str = citizen_record['fields'].get('Position')
    current_position = None
    if citizen_position_str:
        try:
            current_position = json.loads(citizen_position_str)
        except json.JSONDecodeError:
            log.error(f"Could not parse citizen position: {citizen_position_str}")
            return None # Changed to None
    
    # Get building records for path calculation
    start_time_fetch_buildings = time.perf_counter()
    seller_building_record = get_building_record(tables, seller_building_id)
    # market_building_record will be determined later
    end_time_fetch_buildings = time.perf_counter()
    log.info(f"Time to fetch seller building record: {end_time_fetch_buildings - start_time_fetch_buildings:.4f} seconds")

    if not seller_building_record:
        log.error(f"Could not find seller building record for ID: {seller_building_id}")
        return None
    
    # Verify citizen is owner or operator of seller building
    seller_owner = seller_building_record['fields'].get('Owner')
    seller_operator = seller_building_record['fields'].get('RunBy')
    
    if citizen_username != seller_owner and citizen_username != seller_operator:
        log.error(f"Citizen {citizen_username} is neither owner nor operator of building {seller_building_id}")
        return None # Changed to None

    # Determine the target market building
    target_market_record: Optional[Dict[str, Any]] = None # Initialize
    # target_market_building_id was already extracted from details (or is None) at the start of the function
    
    if target_market_building_id: # User specified a market
        log.info(f"User specified target market: {target_market_building_id}")
        target_market_record = get_building_record(tables, target_market_building_id)
        if not target_market_record:
            log.error(f"Specified target market building {target_market_building_id} not found.")
            return None
    else: # Find the closest suitable market
        log.info(f"No target market specified. Finding closest market to seller building {seller_building_id}.")
        seller_building_pos = _get_building_position_coords(seller_building_record)
        if not seller_building_pos:
            log.error(f"Seller building {seller_building_id} has no position. Cannot find closest market.")
            return None

        market_types_to_check = ["market_stall", "merceria", "weighing_station"]
        closest_market_overall: Optional[Dict[str, Any]] = None
        min_distance_to_market = float('inf')
        
        market_formula_parts = [f"{{Type}}='{_escape_airtable_value(mt)}'" for mt in market_types_to_check]
        market_formula = f"OR({', '.join(market_formula_parts)})"
        all_potential_markets = tables['buildings'].all(formula=market_formula)

        if not all_potential_markets:
            log.warning(f"No buildings found of types: {', '.join(market_types_to_check)}.")
            log.error(f"No suitable market (stall, merceria, weighing_station) found near seller building {seller_building_id}.")
            return None
        else:
            for potential_market in all_potential_markets:
                market_pos = _get_building_position_coords(potential_market)
                if market_pos:
                    distance = calculate_haversine_distance_meters(seller_building_pos['lat'], seller_building_pos['lng'], market_pos['lat'], market_pos['lng'])
                    if distance < min_distance_to_market:
                        min_distance_to_market = distance
                        closest_market_overall = potential_market
        
        if closest_market_overall:
            target_market_record = closest_market_overall
            # Update target_market_building_id with the ID of the found market
            target_market_building_id = target_market_record['fields'].get('BuildingId') 
            log.info(f"Closest market found: {target_market_record['fields'].get('Name', target_market_building_id)} (Type: {target_market_record['fields'].get('Type')}) at {min_distance_to_market:.2f}m.")
        else:
            log.error(f"No suitable market (stall, merceria, weighing_station) found near seller building {seller_building_id}.")
            return None

    # Final check for target_market_building_id and target_market_record
    if not target_market_building_id: 
        log.error(f"Could not determine a valid targetMarketBuildingId for contract by {citizen_username} after all checks.")
        return None
    if not target_market_record: # Should be set if target_market_building_id is set
        log.error(f"Internal error: target_market_building_id is '{target_market_building_id}' but target_market_record is None.")
        return None
        
    # Create activity IDs
    goto_seller_activity_id = f"goto_seller_for_contract_{citizen_username}_{ts}"
    prepare_goods_activity_id = f"prepare_goods_for_sale_{citizen_username}_{ts}"
    goto_market_activity_id = f"goto_market_for_contract_{citizen_username}_{ts}"
    register_offer_activity_id = f"register_public_sell_offer_{citizen_username}_{ts}"
    
    # Use the passed now_utc_dt_param
    now_utc = now_utc_dt_param 
    
    # Calculate path to seller building
    # Pass api_base_url to find_path_between_buildings_or_coords
    start_time_path_seller = time.perf_counter()
    path_to_seller = find_path_between_buildings_or_coords(tables, current_position, seller_building_record, api_base_url, transport_api_url)
    end_time_path_seller = time.perf_counter()
    log.info(f"Time for path_to_seller: {end_time_path_seller - start_time_path_seller:.4f} seconds")

    if not path_to_seller or not path_to_seller.get('path'):
        log.error(f"Could not find path to seller building {seller_building_id}")
        return None # Changed to None
    
    # Calculate seller travel duration
    seller_duration_seconds = path_to_seller.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min
    goto_seller_start_date = now_utc.isoformat() # Start immediately
    goto_seller_end_date = (now_utc + timedelta(seconds=seller_duration_seconds)).isoformat()
    
    # Calculate preparation activity times (15 minutes)
    prepare_goods_start_date = goto_seller_end_date
    prepare_goods_end_date = (datetime.fromisoformat(goto_seller_end_date.replace('Z', '+00:00')) + timedelta(minutes=15)).isoformat()
    
    # Calculate path from seller to market
    # Pass api_base_url to find_path_between_buildings_or_coords
    start_time_path_market = time.perf_counter()
    # Use target_market_record which is determined by the logic above (user-specified or closest)
    path_to_market = find_path_between_buildings_or_coords(tables, seller_building_record, target_market_record, api_base_url, transport_api_url)
    end_time_path_market = time.perf_counter()
    log.info(f"Time for path_to_market: {end_time_path_market - start_time_path_market:.4f} seconds")

    if not path_to_market or not path_to_market.get('path'):
        log.error(f"Could not find path from seller building {seller_building_id} to market {target_market_building_id}")
        return None # Changed to None
    
    # Calculate market travel duration
    market_duration_seconds = path_to_market.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min
    goto_market_start_date = prepare_goods_end_date
    goto_market_end_date = (datetime.fromisoformat(goto_market_start_date.replace('Z', '+00:00')) + 
                           timedelta(seconds=market_duration_seconds)).isoformat()
    
    # Calculate registration activity times (15 minutes)
    register_offer_start_date = goto_market_end_date
    register_offer_end_date = (datetime.fromisoformat(goto_market_end_date.replace('Z', '+00:00')) + timedelta(minutes=15)).isoformat()
    
    # Prepare activity payloads
    activities_to_create = []
    
    # 1. Create goto_seller activity
    goto_seller_payload = {
        "ActivityId": goto_seller_activity_id,
        "Type": "goto_location",
        "Citizen": citizen_username,
        "FromBuilding": None,  # Starting from current position
        "ToBuilding": seller_building_id,
        "Path": json.dumps(path_to_seller.get('path', [])),
        "Notes": json.dumps({ # Changed Details to Notes
            "contractId": contract_id,
            "resourceType": resource_type,
            "pricePerResource": price_per_resource,
            "targetAmount": target_amount,
            "sellerBuildingId": seller_building_id,
            "targetMarketBuildingId": target_market_building_id,
            "activityType": "manage_public_sell_contract",
            "nextStep": "prepare_goods_for_sale"
        }),
        "Status": "created",
        "Title": f"Traveling to prepare goods for sale",
        "Description": f"Traveling to {seller_building_record['fields'].get('Name', seller_building_id)} to prepare goods for public sale. This is the first step of the manage_public_sell_contract process and will be followed by goods preparation.",
        # JSON "Notes" is already set above and should not be overwritten by descriptive text.
        "CreatedAt": goto_seller_start_date,
        "StartDate": goto_seller_start_date,
        "EndDate": goto_seller_end_date,
        "Priority": 20  # Medium-high priority for economic activities
    }
    activities_to_create.append(goto_seller_payload)
    
    # 2. Create prepare_goods_for_sale activity
    prepare_goods_payload = {
        "ActivityId": prepare_goods_activity_id,
        "Type": "prepare_goods_for_sale",
        "Citizen": citizen_username,
        "FromBuilding": seller_building_id,
        "ToBuilding": seller_building_id,  # Same location
        "Notes": json.dumps({ # Changed Details to Notes
            "contractId": contract_id,
            "resourceType": resource_type,
            "pricePerResource": price_per_resource,
            "targetAmount": target_amount,
            "sellerBuildingId": seller_building_id,
            "targetMarketBuildingId": target_market_building_id,
            "activityType": "manage_public_sell_contract",
            "nextStep": "goto_market"
        }),
        "Status": "created",
        "Title": f"Preparing {resource_type} for public sale",
        "Description": f"Preparing {target_amount} units of {resource_type} for public sale at {price_per_resource} Ducats each. This is the second step of the manage_public_sell_contract process and will be followed by travel to market.",
        # "Notes" field containing the JSON details is now the only one.
        "CreatedAt": goto_seller_start_date,
        "StartDate": prepare_goods_start_date,
        "EndDate": prepare_goods_end_date,
        "Priority": 20
    }
    activities_to_create.append(prepare_goods_payload)
    
    # 3. Create goto_market activity
    goto_market_payload = {
        "ActivityId": goto_market_activity_id,
        "Type": "goto_location",
        "Citizen": citizen_username,
        "FromBuilding": seller_building_id,
        "ToBuilding": target_market_record['fields'].get('BuildingId'), # Use resolved market ID
        "Path": json.dumps(path_to_market.get('path', [])),
        "Notes": json.dumps({ # Changed Details to Notes
            "contractId": contract_id,
            "resourceType": resource_type,
            "pricePerResource": price_per_resource,
            "targetAmount": target_amount,
            "sellerBuildingId": seller_building_id,
            "targetMarketBuildingId": target_market_record['fields'].get('BuildingId'), # Use resolved market ID in notes too for consistency
            "activityType": "manage_public_sell_contract",
            "nextStep": "register_public_sell_offer"
        }),
        "Status": "created",
        "Title": f"Traveling to {target_market_record['fields'].get('Name', target_market_record['fields'].get('BuildingId'))} to register sale offer", # Use resolved market name
        "Description": f"Traveling to {target_market_record['fields'].get('Name', target_market_record['fields'].get('BuildingId'))} to register public sale offer. This is the third step of the manage_public_sell_contract process and will be followed by offer registration.", # Use resolved market name
        # JSON "Notes" is already set above and should not be overwritten by descriptive text.
        "CreatedAt": goto_seller_start_date,
        "StartDate": goto_market_start_date,
        "EndDate": goto_market_end_date,
        "Priority": 20
    }
    activities_to_create.append(goto_market_payload)
    
    # 4. Create register_public_sell_offer activity
    register_offer_payload = {
        "ActivityId": register_offer_activity_id,
        "Type": "register_public_sell_offer",
        "Citizen": citizen_username,
        "FromBuilding": target_market_record['fields'].get('BuildingId'), # Use resolved market ID
        "ToBuilding": target_market_record['fields'].get('BuildingId'),  # Same location, use resolved market ID
        "Notes": json.dumps({ # Changed Details to Notes
            "contractId": contract_id,
            "resourceType": resource_type,
            "pricePerResource": price_per_resource,
            "targetAmount": target_amount,
            "sellerBuildingId": seller_building_id,
            "targetMarketBuildingId": target_market_building_id
        }),
        "Status": "created",
        "Title": f"Registering public sale offer for {resource_type}",
        "Description": f"Registering offer to sell {target_amount} units of {resource_type} at {price_per_resource} Ducats each. This is the final step of the manage_public_sell_contract process and will create or update the public_sell contract.",
        # JSON "Notes" is already set above and should not be overwritten by descriptive text.
        "CreatedAt": goto_seller_start_date,
        "StartDate": register_offer_start_date,
        "EndDate": register_offer_end_date,
        "Priority": 20
    }
    activities_to_create.append(register_offer_payload)

    # The creator should now return the list of payloads, and the dispatcher will handle creation.
    log.info(f"Prepared manage_public_sell_contract activity chain for citizen {citizen_username}:")
    for idx, activity_payload_log in enumerate(activities_to_create, 1):
        log.info(f"  {idx}. {activity_payload_log['Type']} activity payload {activity_payload_log['ActivityId']} prepared.")
    return activities_to_create # Return the list of payloads

    # The try-except block for Airtable creation is removed as creation is deferred to the dispatcher.
    # Any errors during payload preparation (like pathfinding) are already handled and return None.

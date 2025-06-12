import logging
import json
from datetime import datetime, timedelta
import time
import requests # Should be used by helpers, not directly here unless for specific API calls not in helpers
import pytz
import uuid
import re
import random # For _fetch_and_assign_random_starting_position if it were here and for weighted leisure
from collections import defaultdict
from typing import Dict, List, Optional, Any, Tuple, Union # Added Tuple and Union
from pyairtable import Table
from dateutil import parser as dateutil_parser # Import for parsing dates

# Import helpers from the utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    _has_recent_failed_activity_for_contract,
    _get_building_position_coords,
    _calculate_distance_meters,
    is_nighttime as is_nighttime_helper, # General nighttime, less used now
    is_rest_time_for_class,
    is_work_time, # Updated from is_work_time_for_class
    is_leisure_time_for_class,
    SOCIAL_CLASS_SCHEDULES, # Import the schedule dictionary
    # BUILDING_TYPE_WORK_SCHEDULES, # No longer needed here, specialWorkHours come from building_type_defs
    get_path_between_points,
    get_citizen_current_load,
    get_citizen_effective_carry_capacity,
    CITIZEN_CARRY_CAPACITY, # Import constant for carry capacity
    get_relationship_trust_score,
    get_closest_food_provider, # Import the new function
    get_closest_building_of_type, # Import for finding specific building types like "inn"
    get_citizen_inventory_details, # New import
    get_citizen_workplace,
    get_citizen_home,
    get_building_type_info, # Will use this from helpers
    get_building_resources, # Will use this from helpers
    can_produce_output,     # Will use this from helpers
    find_path_between_buildings, # Will use this from helpers
    get_citizen_contracts,  # Will use this from helpers
    # get_idle_citizens, # Not used by process_citizen_activity directly
    _fetch_and_assign_random_starting_position, # Already using from helpers
    get_building_storage_details, # Added import
    VENICE_TIMEZONE, # Import VENICE_TIMEZONE
    FOOD_RESOURCE_TYPES_FOR_EATING, # Import from activity_helpers
    clean_thought_content # Import the missing function
)

# Import activity creators
from backend.engine.activity_creators import (
    try_create_stay_activity,
    try_create_goto_work_activity,
    try_create_goto_home_activity,
    try_create_travel_to_inn_activity,
    try_create_idle_activity,
    try_create_production_activity,
    try_create_resource_fetching_activity,
    try_create_eat_from_inventory_activity,
    try_create_eat_at_home_activity,
    try_create_eat_at_tavern_activity,
    try_create_secure_warehouse_activity,
    try_create_check_business_status_activity, # Import new creator
    # Import new storage activity creators
    try_create_deliver_to_storage_activity,
    try_create_initiate_building_project_activity, # Import new creator for building projects
    try_create_fetch_from_storage_activity,
    try_create_fishing_activity, # Import new creator
    try_create_manage_public_dock_activity, # Import new creator
    try_create_work_on_art_activity, # Import new creator for Artisti
    try_create_read_book_activity, # Import new creator for reading books
    try_create_attend_theater_performance_activity, # New theater activity
    try_create_drink_at_inn_activity, # New drink at inn activity
    try_create_use_public_bath_activity, # New public bath activity
    try_create_deposit_inventory_orchestrator, # New orchestrator for depositing inventory
    try_create_construct_building_activity, # Added for occupant construction
    # try_create_fetch_from_galley_activity is not used by process_citizen_activity
)
from backend.engine.activity_creators.send_message_creator import try_create as try_create_send_message_chain # Import for send_message
from backend.engine.activity_creators.manage_public_storage_offer_creator import try_create as try_create_manage_public_storage_offer_chain

# Import the specific processor function

# Import the specific processor function
from backend.engine.activity_processors import process_goto_work as process_goto_work_fn
from backend.engine.logic.porter_activities import process_porter_activity # Added import
from backend.engine.logic.forestieri_activities import (
    process_forestieri_night_activity,
    process_forestieri_daytime_activity,
    process_forestieri_departure_check # Import new function
)
from backend.engine.logic.construction_logic import handle_construction_worker_activity # Import new handler

# Import get_building_record and get_citizen_record from activity_helpers
from backend.engine.utils.activity_helpers import get_building_record, get_citizen_record

log = logging.getLogger(__name__)

# Module-level constants
IDLE_ACTIVITY_DURATION_HOURS = 1
SOCIAL_CLASS_VALUE = {"Nobili": 4, "Cittadini": 3, "Popolani": 2, "Facchini": 1, "Forestieri": 2}
THEATER_COSTS = {
    "Facchini": 100, "Popolani": 200, "Cittadini": 500,
    "Nobili": 1000, "Forestieri": 700, "Artisti": 300
}
DEFAULT_THEATER_COST = 200
DRINKABLE_RESOURCE_TYPES = ["wine", "spiced_wine"] # Added constant
TAVERN_MEAL_COST_ESTIMATE = 10  # Ducats
FOOD_SHOPPING_COST_ESTIMATE = 15 # Ducats, for 1-2 units of basic food
# FOOD_RESOURCE_TYPES_FOR_EATING is now in activity_helpers
NIGHT_END_HOUR_FOR_STAY = 6
STORAGE_FULL_THRESHOLD = 0.80

# Module-level helper functions for logging display names
def _get_bldg_display_name_module(tables: Dict[str, Table], bldg_record: Optional[Dict], default_id: Optional[str] = None) -> str:
    if bldg_record and bldg_record.get('fields'):
        name = bldg_record['fields'].get('Name')
        b_id = bldg_record['fields'].get('BuildingId', bldg_record.get('id', 'Unknown ID'))
        b_type = bldg_record['fields'].get('Type', 'Unknown Type')
        if name:
            return f"'{name}' ({b_type}, ID: {b_id})"
        return f"{b_type} (ID: {b_id})"
    if default_id:
        b_rec = get_building_record(tables, default_id)
        if b_rec:
            return _get_bldg_display_name_module(tables, b_rec)
        return f"Building (ID: {default_id})"
    return "an unknown building"

def _get_res_display_name_module(res_id: str, resource_definitions_dict: Dict) -> str:
    return resource_definitions_dict.get(res_id, {}).get('name', res_id)

# --- Helper for Water Graph Data ---
_water_graph_cache: Optional[Dict] = None
_water_graph_last_fetch_time: Optional[datetime] = None
_WATER_GRAPH_CACHE_TTL_SECONDS = 300 # Cache for 5 minutes

def _get_water_graph_data(api_base_url: str) -> Optional[Dict]:
    """Fetches water graph data from the API, with caching."""
    global _water_graph_cache, _water_graph_last_fetch_time
    
    now = datetime.now(pytz.UTC)
    if _water_graph_cache and _water_graph_last_fetch_time and \
       (now - _water_graph_last_fetch_time).total_seconds() < _WATER_GRAPH_CACHE_TTL_SECONDS:
        log.info("Using cached water graph data.")
        return _water_graph_cache

    try:
        url = f"{api_base_url}/api/get-water-graph" # Assuming this endpoint exists
        log.info(f"Fetching water graph data from API: {url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and isinstance(data.get("waterGraph"), dict):
            _water_graph_cache = data["waterGraph"]
            _water_graph_last_fetch_time = now
            log.info(f"Successfully fetched and cached water graph data. Found {len(_water_graph_cache.get('waterPoints', []))} water points.")
            return _water_graph_cache
        log.error(f"API error fetching water graph: {data.get('error', 'Unknown error')}")
        return None
    except Exception as e:
        log.error(f"Exception fetching water graph data: {e}")
        return None

def _find_closest_fishable_water_point(
    citizen_position: Dict[str, float], 
    api_base_url: str,
    transport_api_url: str
) -> Tuple[Optional[str], Optional[Dict[str, float]], Optional[Dict]]:
    """Finds the closest water point with hasFish=true and returns its ID, position, and path data."""
    water_graph = _get_water_graph_data(api_base_url)
    if not water_graph or not water_graph.get("waterPoints"):
        log.warning("No water graph data or water points available for fishing.")
        return None, None, None

    fishable_points = [wp for wp in water_graph["waterPoints"] if wp.get("hasFish")]
    if not fishable_points:
        log.info("No water points with fish found.")
        return None, None, None

    closest_point_record = None
    min_distance = float('inf')

    for point_data in fishable_points:
        # Correctly access nested position data
        position_field = point_data.get("position")
        if not position_field or not isinstance(position_field, dict):
            log.warning(f"Water point {point_data.get('id', 'Unknown ID')} missing or invalid 'position' field. Skipping.")
            continue
            
        try:
            point_lat = float(position_field.get("lat", 0.0))
            point_lng = float(position_field.get("lng", 0.0))
        except (ValueError, TypeError):
            log.warning(f"Water point {point_data.get('id', 'Unknown ID')} has invalid lat/lng in position field: {position_field}. Skipping.")
            continue

        point_pos = {"lat": point_lat, "lng": point_lng}
        # Check for (0,0) might not be necessary if API guarantees valid coords for fishable points,
        # but as a safeguard if 0,0 is an invalid location:
        if point_lat == 0.0 and point_lng == 0.0: 
            log.debug(f"Water point {point_data.get('id', 'Unknown ID')} has coordinates (0,0). Skipping if this is considered invalid.")
            # Depending on game logic, (0,0) might be a valid sea point or an error indicator.
            # If it's an error, 'continue' here. For now, assume it could be valid.
            # continue 

        distance = _calculate_distance_meters(citizen_position, point_pos)
        if distance < min_distance:
            min_distance = distance
            closest_point_record = point_data
    
    if closest_point_record:
        # Correctly access nested position data for the chosen point
        closest_point_position_field = closest_point_record.get("position")
        if not closest_point_position_field or not isinstance(closest_point_position_field, dict):
            log.error(f"Selected closest fishable point {closest_point_record.get('id', 'Unknown ID')} has invalid position data. Cannot proceed.")
            return None, None, None
        
        try:
            closest_lat = float(closest_point_position_field.get("lat"))
            closest_lng = float(closest_point_position_field.get("lng"))
        except (ValueError, TypeError, AttributeError): # AttributeError if .get() returns non-dict
            log.error(f"Selected closest fishable point {closest_point_record.get('id', 'Unknown ID')} has invalid lat/lng in position: {closest_point_position_field}. Cannot proceed.")
            return None, None, None

        closest_point_id = closest_point_record.get("id", f"wp_{closest_lat}_{closest_lng}")
        closest_point_pos = {"lat": closest_lat, "lng": closest_lng}
        
        path_to_point = get_path_between_points(citizen_position, closest_point_pos, transport_api_url)
        if path_to_point and path_to_point.get("success"):
            log.info(f"Closest fishable water point: {closest_point_id} at {min_distance:.2f}m.")
            return closest_point_id, closest_point_pos, path_to_point
        else:
            log.warning(f"Found closest fishable point {closest_point_id}, but pathfinding failed.")
            return None, None, None
            
    log.info("Could not find a suitable (reachable) fishable water point.")
    return None, None, None

# --- Activity Handler Functions ---

def _handle_emergency_fishing(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str # Added social_class
) -> Optional[Dict]:
    """Prio 4: Handles emergency fishing if citizen is Facchini, starving, and it's not rest time."""
    if citizen_social_class != "Facchini": # Only Facchini do emergency fishing for now
        return None
    if is_rest_time_for_class(citizen_social_class, now_venice_dt): # No fishing during rest
        return None

    ate_at_str = citizen_record['fields'].get('AteAt')
    is_starving = True # Assume starving if no AteAt or very old
    if ate_at_str:
        try:
            ate_at_dt = dateutil_parser.isoparse(ate_at_str.replace('Z', '+00:00'))
            if ate_at_dt.tzinfo is None: ate_at_dt = pytz.UTC.localize(ate_at_dt)
            if (now_utc_dt - ate_at_dt) <= timedelta(hours=24): # More than 24 hours
                is_starving = False
        except ValueError: pass # Invalid date format, assume starving
    
    if not is_starving:
        return None

    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Pêche Urgence] {citizen_name} n'a pas de position. Impossible de pêcher.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.OKCYAN}[Pêche Urgence] {citizen_name} est affamé(e) et vit dans un fisherman_s_cottage. Recherche d'un lieu de pêche.{LogColors.ENDC}")
    
    target_wp_id, target_wp_pos, path_data = _find_closest_fishable_water_point(citizen_position, api_base_url, transport_api_url)

    if target_wp_id and path_data:
        activity_record = try_create_fishing_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            target_wp_id, path_data, now_utc_dt, activity_type="emergency_fishing"
        )
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Pêche Urgence] {citizen_name}: Activité 'emergency_fishing' créée vers {target_wp_id}.{LogColors.ENDC}")
            return activity_record
    return None

def _handle_leave_venice(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str # Added social_class
) -> bool:
    """Prio 1: Handles Forestieri departure."""
    if citizen_social_class != "Forestieri":
        return None # Changed from False

    # Forestieri departure logic might be complex, involving duration of stay, objectives, etc.
    # For now, let's assume a simplified condition or delegate to a specific Forestieri handler.
    # This handler is high priority, so it should be relatively certain.
    # The existing process_forestieri_departure_check can be used here.
    # It requires: tables, citizen_record, citizen_position, now_utc_dt, transport_api_url, IDLE_ACTIVITY_DURATION_HOURS
    if not process_forestieri_departure_check(tables, citizen_record, citizen_position, now_utc_dt, transport_api_url, IDLE_ACTIVITY_DURATION_HOURS):
        return None # Changed from False

    log.info(f"{LogColors.OKCYAN}[Départ] Forestiero {citizen_name}: Conditions de départ remplies.{LogColors.ENDC}")

    # Find nearest public_dock as exit point
    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Départ] Citoyen {citizen_name}: Pas de position pour trouver un quai de départ.{LogColors.ENDC}")
        return None # Changed from False

    public_docks = tables['buildings'].all(formula="{Type}='public_dock'")
    if not public_docks:
        log.warning(f"{LogColors.WARNING}[Départ] Citoyen {citizen_name}: Aucun quai public trouvé pour le départ.{LogColors.ENDC}")
        return None # Changed from False

    closest_dock_record = None
    min_dist_to_dock = float('inf')
    for dock in public_docks:
        dock_pos = _get_building_position_coords(dock)
        if dock_pos:
            dist = _calculate_distance_meters(citizen_position, dock_pos)
            if dist < min_dist_to_dock:
                min_dist_to_dock = dist
                closest_dock_record = dock
    
    if not closest_dock_record:
        log.warning(f"{LogColors.WARNING}[Départ] Citoyen {citizen_name}: Aucun quai public avec position valide trouvé.{LogColors.ENDC}")
        return None # Changed from False

    exit_point_custom_id = closest_dock_record['fields'].get('BuildingId')
    exit_point_pos = _get_building_position_coords(closest_dock_record)
    exit_point_name_display = _get_bldg_display_name_module(tables, closest_dock_record)

    if not exit_point_custom_id or not exit_point_pos:
        log.warning(f"{LogColors.WARNING}[Départ] Citoyen {citizen_name}: Quai de départ {exit_point_name_display} n'a pas d'ID ou de position.{LogColors.ENDC}")
        return None # Changed from False

    path_to_exit_data = get_path_between_points(citizen_position, exit_point_pos, transport_api_url)
    if not (path_to_exit_data and path_to_exit_data.get('success')):
        log.warning(f"{LogColors.WARNING}[Départ] Citoyen {citizen_name}: Impossible de trouver un chemin vers le quai de départ {exit_point_name_display}.{LogColors.ENDC}")
        return None # Changed from False
    
    # For now, assume no galley to delete for simplicity. This can be added later.
    from backend.engine.activity_creators.leave_venice_activity_creator import try_create as try_create_leave_venice_activity
    activity_record = try_create_leave_venice_activity( # Capture record
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        exit_point_custom_id, path_to_exit_data, None, now_utc_dt
    )
    if activity_record:
        log.info(f"{LogColors.OKGREEN}[Départ] Citoyen {citizen_name}: Activité 'leave_venice' créée via {exit_point_name_display}.{LogColors.ENDC}")
    return activity_record # Return record or None


def _handle_eat_from_inventory(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str 
) -> Optional[Dict]:
    """Prio 2: Handles eating from inventory if hungry and it's leisure time or a meal break."""
    # Removed: if not citizen_record['is_hungry']: return None
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt): # Still check for leisure time
        return None

    log.info(f"{LogColors.OKCYAN}[Manger - Inventaire] Citoyen {citizen_name} ({citizen_social_class}): En période de loisirs. Vérification de l'inventaire.{LogColors.ENDC}")
    for food_type_id in FOOD_RESOURCE_TYPES_FOR_EATING:
        food_name = _get_res_display_name_module(food_type_id, resource_defs)
        formula = (f"AND({{AssetType}}='citizen', {{Asset}}='{_escape_airtable_value(citizen_username)}', "
                   f"{{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='{_escape_airtable_value(food_type_id)}')")
        try:
            inventory_food = tables['resources'].all(formula=formula, max_records=1)
            if inventory_food and float(inventory_food[0]['fields'].get('Count', 0)) >= 1.0:
                # Pass now_utc_dt as current_time_utc, and None for start_time_utc_iso for immediate start
                activity_record = try_create_eat_from_inventory_activity(
                    tables, citizen_custom_id, citizen_username, citizen_airtable_id, 
                    food_type_id, 1.0, 
                    current_time_utc=now_utc_dt, 
                    resource_defs=resource_defs,
                    start_time_utc_iso=None # Explicitly None for immediate start
                )
                if activity_record:
                    log.info(f"{LogColors.OKGREEN}[Faim] Citoyen {citizen_name}: Activité 'eat_from_inventory' créée pour '{food_name}'.{LogColors.ENDC}")
                    return activity_record
        except Exception as e_inv_food:
            log.error(f"{LogColors.FAIL}[Faim] Citoyen {citizen_name}: Erreur vérification inventaire pour '{food_name}': {e_inv_food}{LogColors.ENDC}")
    return None

def _handle_eat_at_home_or_goto(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str 
) -> Optional[Dict]:
    """Prio 3: Handles eating at home or going home to eat if hungry and it's leisure time."""
    # Removed: if not citizen_record['is_hungry']: return None
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt): # Still check for leisure time
        return None

    home_record = get_citizen_home(tables, citizen_username)
    if not home_record: return None

    log.info(f"{LogColors.OKCYAN}[Manger - Maison] Citoyen {citizen_name} ({citizen_social_class}): En période de loisirs. Vérification domicile.{LogColors.ENDC}")
    home_name_display = _get_bldg_display_name_module(tables, home_record)
    home_position = _get_building_position_coords(home_record)
    home_building_id = home_record['fields'].get('BuildingId', home_record['id'])
    
    is_at_home = (citizen_position and home_position and _calculate_distance_meters(citizen_position, home_position) < 20)

    # food_resource_types = ["bread", "fish", "preserved_fish"] # Replaced by constant
    food_type_at_home_id = None
    food_at_home_name = "nourriture inconnue"
    for food_type_id in FOOD_RESOURCE_TYPES_FOR_EATING:
        formula_home = (f"AND({{AssetType}}='building', {{Asset}}='{_escape_airtable_value(home_building_id)}', "
                        f"{{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='{_escape_airtable_value(food_type_id)}')")
        try:
            home_food = tables['resources'].all(formula=formula_home, max_records=1)
            if home_food and float(home_food[0]['fields'].get('Count', 0)) >= 1.0:
                food_type_at_home_id = food_type_id
                food_at_home_name = _get_res_display_name_module(food_type_id, resource_defs)
                break
        except Exception as e_home_food:
            log.error(f"{LogColors.FAIL}[Faim] Citoyen {citizen_name}: Erreur vérification nourriture à {home_name_display}: {e_home_food}{LogColors.ENDC}")

    if not food_type_at_home_id: return None # No food at home

    if is_at_home:
        # Create eat_at_home directly
        eat_activity = try_create_eat_at_home_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            home_building_id, food_type_at_home_id, 1.0,
            current_time_utc=now_utc_dt, resource_defs=resource_defs,
            start_time_utc_iso=None # Immediate start
        )
        if eat_activity:
            log.info(f"{LogColors.OKGREEN}[Faim] Citoyen {citizen_name}: Activité 'eat_at_home' créée pour manger '{food_at_home_name}' à {home_name_display}.{LogColors.ENDC}")
        return eat_activity
    else:
        # Create goto_home, then chain eat_at_home
        if not citizen_position or not home_position: return None # Cannot pathfind
        
        path_to_home = get_path_between_points(citizen_position, home_position, transport_api_url)
        if not (path_to_home and path_to_home.get('success')): return None # Pathfinding failed

        goto_home_activity = try_create_goto_home_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            home_building_id, path_to_home, current_time_utc=now_utc_dt
            # start_time_utc_iso is None for immediate start of travel
        )
        if goto_home_activity:
            log.info(f"{LogColors.OKGREEN}[Faim] Citoyen {citizen_name}: Activité 'goto_home' créée vers {home_name_display} pour manger.{LogColors.ENDC}")
            # Chain eat_at_home activity
            next_start_time_iso = goto_home_activity['fields']['EndDate']
            eat_activity_chained = try_create_eat_at_home_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                home_building_id, food_type_at_home_id, 1.0,
                current_time_utc=now_utc_dt, # current_time_utc is for fallback if start_time_utc_iso is None
                resource_defs=resource_defs,
                start_time_utc_iso=next_start_time_iso
            )
            if eat_activity_chained:
                log.info(f"{LogColors.OKGREEN}[Faim] Citoyen {citizen_name}: Activité 'eat_at_home' chaînée après 'goto_home', début à {next_start_time_iso}.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}[Faim] Citoyen {citizen_name}: Échec de la création de 'eat_at_home' chaînée après 'goto_home'.{LogColors.ENDC}")
            return goto_home_activity # Return the first activity of the chain
        return None # Failed to create goto_home

def _handle_eat_at_tavern_or_goto(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str 
) -> Optional[Dict]:
    """Prio 6: Handles eating at tavern or going to tavern to eat if hungry and it's leisure time."""
    # Removed: if not citizen_record['is_hungry']: return None
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt): # Still check for leisure time
        return None
    if not citizen_position: return None

    citizen_ducats = float(citizen_record['fields'].get('Ducats', 0))
    # Keep a very basic ducat check, actual affordability checked against API response
    if citizen_ducats < 1: # Must have at least 1 ducat to consider buying food
        log.info(f"{LogColors.OKBLUE}[Faim - Externe] Citoyen {citizen_name} a moins de 1 Ducat. Ne peut pas acheter à manger.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.OKCYAN}[Faim - Externe] Citoyen {citizen_name} ({citizen_social_class}): Affamé et en période de loisirs. Appel API /get-eating-options.{LogColors.ENDC}")

    eating_options_response = None
    try:
        response = requests.get(f"{api_base_url}/api/get-eating-options?citizenUsername={citizen_username}", timeout=60) # Increased timeout to 60 seconds
        response.raise_for_status()
        eating_options_response = response.json()
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}Erreur appel API /get-eating-options pour {citizen_username}: {e}{LogColors.ENDC}")
        return None
    except json.JSONDecodeError as e:
        log.error(f"{LogColors.FAIL}Erreur décodage JSON de /get-eating-options pour {citizen_username}: {e}. Réponse: {response.text if response else 'N/A'}{LogColors.ENDC}")
        return None

    if not eating_options_response or not eating_options_response.get('success'):
        log.warning(f"{LogColors.WARNING}API /get-eating-options n'a pas retourné de succès pour {citizen_username}. Réponse: {eating_options_response}{LogColors.ENDC}")
        return None

    available_options = eating_options_response.get('options', [])
    log.info(f"{LogColors.OKBLUE}[Faim - Externe] Citoyen {citizen_name} ({citizen_social_class}): API /get-eating-options returned {len(available_options)} options. Ducats: {citizen_ducats:.2f}.{LogColors.ENDC}")
    if available_options:
        for i, opt_log in enumerate(available_options):
            log.debug(f"  Option {i+1}: Source: {opt_log.get('source')}, Resource: {opt_log.get('resourceType')}, Price: {opt_log.get('price')}, Building: {opt_log.get('buildingName')}")

    chosen_option = None
    if available_options: # Only loop if there are options
        for option in available_options:
            source = option.get('source')
            price_str = option.get('price') # Price might be null/undefined or a string
            
            if source in ['tavern', 'retail_food_shop']:
                if price_str is not None:
                    try:
                        price = float(price_str)
                        if citizen_ducats >= price:
                            chosen_option = option
                            log.info(f"{LogColors.OKGREEN}[Faim - Externe] Citoyen {citizen_name}: Option abordable trouvée: {option.get('resourceType')} à {option.get('buildingName')} pour {price:.2f} Ducats.{LogColors.ENDC}")
                            break # Take the first affordable tavern/shop option
                        # else: log.debug(f"  Option {option.get('resourceType')} at {option.get('buildingName')} price {price:.2f} is not affordable (Ducats: {citizen_ducats:.2f}).")
                    except ValueError:
                        log.warning(f"{LogColors.WARNING}[Faim - Externe] Option {option.get('resourceType')} at {option.get('buildingName')} has invalid price '{price_str}'. Skipping.{LogColors.ENDC}")
                # else: log.debug(f"  Option {option.get('resourceType')} at {option.get('buildingName')} has no price. Skipping.")
            # else: log.debug(f"  Option source '{source}' is not tavern or retail_food_shop. Skipping.")

    if not chosen_option:
        if not available_options:
            log.info(f"{LogColors.OKBLUE}[Faim - Externe] Citoyen {citizen_name}: Aucune option de repas externe retournée par l'API /get-eating-options.{LogColors.ENDC}")
        else:
            log.info(f"{LogColors.OKBLUE}[Faim - Externe] Citoyen {citizen_name}: Aucune option de repas externe abordable ou valide trouvée parmi les {len(available_options)} options de l'API (Ducats: {citizen_ducats:.2f}).{LogColors.ENDC}")
        return None

    provider_custom_id = chosen_option.get('buildingId')
    provider_name_display = chosen_option.get('buildingName', provider_custom_id)
    resource_to_eat = chosen_option.get('resourceType')
    price_of_meal = float(chosen_option.get('price', 0))

    if not provider_custom_id or not resource_to_eat:
        log.warning(f"{LogColors.WARNING}[Faim - Externe] Option API invalide pour {citizen_name}: buildingId ou resourceType manquant. Option: {chosen_option}{LogColors.ENDC}")
        return None

    provider_record = get_building_record(tables, provider_custom_id)
    if not provider_record:
        log.warning(f"{LogColors.WARNING}[Faim - Externe] Bâtiment fournisseur {provider_custom_id} non trouvé pour {citizen_name}.{LogColors.ENDC}")
        return None
    
    provider_pos = _get_building_position_coords(provider_record)
    if not provider_pos:
        log.warning(f"{LogColors.WARNING}[Faim - Externe] Bâtiment fournisseur {provider_custom_id} n'a pas de position pour {citizen_name}.{LogColors.ENDC}")
        return None

    is_at_provider = _calculate_distance_meters(citizen_position, provider_pos) < 20
    
    eat_activity_details = {
        "is_retail_purchase": chosen_option.get('source') == 'retail_food_shop',
        "food_resource_id": resource_to_eat,
        "price": price_of_meal,
        "original_contract_id": chosen_option.get('contractId') # API provides this
    }

    if is_at_provider:
        eat_activity = try_create_eat_at_tavern_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id, 
            provider_custom_id, current_time_utc=now_utc_dt, resource_defs=resource_defs,
            start_time_utc_iso=None, # Immediate start
            details_payload=eat_activity_details
        )
        if eat_activity:
            log.info(f"{LogColors.OKGREEN}[Faim - Externe] Citoyen {citizen_name}: Activité 'eat_at_provider' créée à {provider_name_display} pour {resource_to_eat}.{LogColors.ENDC}")
        return eat_activity
    else:
        # Pathfinding will be handled by the goto_location_activity_creator.
        # We still need provider_pos to check if already at provider (done above).
        # The check for citizen_position is also done above.

        # Use the generic goto_location_activity_creator for chaining
        from backend.engine.activity_creators.goto_location_activity_creator import try_create as try_create_goto_location_activity
        
        activity_params_for_goto = {
            "targetBuildingId": provider_custom_id,
            "details": {  # This was previously details_payload
                "action_on_arrival": "eat_at_tavern",
                "eat_details_on_arrival": eat_activity_details,
                "target_building_id_on_arrival": provider_custom_id
            }
            # Optional: "fromBuildingId", "notes", "title", "description"
        }

        goto_provider_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            activity_params=activity_params_for_goto,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url
        )
        if goto_provider_activity:
            log.info(f"{LogColors.OKGREEN}[Faim - Externe] Citoyen {citizen_name}: Activité 'goto_location' créée vers {provider_name_display} pour manger {resource_to_eat}.{LogColors.ENDC}")
            # The eat_at_tavern activity will be chained by the goto_location processor based on details_payload
            return goto_provider_activity
        return None

def _handle_deposit_inventory_at_work(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str_val: Optional[str],
    citizen_social_class: str # Added social_class
) -> bool:
    """Prio 10: Handles depositing full inventory at work if it's work time or just before/after."""
    workplace_record_for_deposit = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    workplace_type_str_for_deposit = workplace_record_for_deposit['fields'].get('Type') if workplace_record_for_deposit else None
    workplace_def_for_deposit = building_type_defs.get(workplace_type_str_for_deposit) if workplace_type_str_for_deposit else None

    # Allow depositing even slightly outside work hours if inventory is full.
    if not (is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=workplace_def_for_deposit) or \
            is_leisure_time_for_class(citizen_social_class, now_venice_dt)): # Allow during leisure too if near work
        # More precise: check if current time is "close" to work time.
        # For now, allowing during leisure is a simple proxy.
        pass # Let it proceed if inventory is full, even if not strictly work time.

    current_load = get_citizen_current_load(tables, citizen_username)
    citizen_max_capacity = get_citizen_effective_carry_capacity(citizen_record)
    if current_load <= (citizen_max_capacity * 0.7): return False

    log.info(f"{LogColors.OKCYAN}[Inventaire Plein] Citoyen {citizen_name} ({citizen_social_class}): Inventaire >70% plein. Vérification lieu de travail.{LogColors.ENDC}")
    workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    if not workplace_record: return False

    workplace_name_display = _get_bldg_display_name_module(tables, workplace_record)
    workplace_pos = _get_building_position_coords(workplace_record)
    workplace_custom_id_val = workplace_record['fields'].get('BuildingId', workplace_record['id'])
    if not citizen_position or not workplace_pos: return False

    is_at_workplace = _calculate_distance_meters(citizen_position, workplace_pos) < 20
    if not is_at_workplace:
        path_to_work = get_path_between_points(citizen_position, workplace_pos, transport_api_url)
        if path_to_work and path_to_work.get('success'):
            if try_create_goto_work_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                workplace_custom_id_val, path_to_work,
                get_citizen_home(tables, citizen_username), resource_defs, False, citizen_position_str_val, now_utc_dt
            ):
                log.info(f"{LogColors.OKGREEN}[Inventaire Plein] Citoyen {citizen_name}: Activité 'goto_work' créée vers {workplace_name_display} pour dépôt.{LogColors.ENDC}")
                return True
    else: # Is at workplace
        mock_activity_record = {'id': f"mock_deposit_{citizen_airtable_id}", 'fields': {'ActivityId': f"mock_deposit_{uuid.uuid4()}", 'Citizen': citizen_username, 'ToBuilding': workplace_custom_id_val}}
        # Call process_goto_work_fn to attempt the deposit.
        # This function itself doesn't create a new activity record in Airtable.
        # It performs an action (deposit) based on the mock activity.
        deposit_successful = process_goto_work_fn(tables, mock_activity_record, building_type_defs, resource_defs)
        
        if deposit_successful:
            log.info(f"{LogColors.OKGREEN}[Inventaire Plein] Citoyen {citizen_name}: Dépôt direct à {workplace_name_display} réussi (ou rien à déposer).{LogColors.ENDC}")
        else:
            log.warning(f"{LogColors.WARNING}[Inventaire Plein] Citoyen {citizen_name}: Tentative de dépôt direct à {workplace_name_display} échouée (ex: pas d'espace).{LogColors.ENDC}")
            
        # Regardless of deposit success/failure, this handler did not create a *new* activity record.
        # Return False to allow other handlers (e.g., production, idle) to be evaluated for this citizen.
        return False
    # If we created a goto_work activity (because not at workplace), the return True from that path is correct.
    # If we reach here, it means no goto_work activity was created (e.g. pathfinding failed or already at work but deposit logic returned False from above).
    return False

def _handle_check_business_status(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str, # Added social_class
    check_only: bool = False
) -> Union[Optional[Dict], bool]:
    """Prio 65: Handles checking business status if manager and not checked recently, during work/leisure time."""
    # For checking business status, the specific work hours of the business itself are most relevant.
    # However, the citizen might also do this during their general leisure time.
    # We need the business_type_def to check its specific hours.
    # This check is a bit broad; it will be refined if a specific business is found.
    
    # Initial check: if it's general leisure for the citizen, allow.
    # If not, then we'll need to check specific business work hours later.
    is_general_leisure = is_leisure_time_for_class(citizen_social_class, now_venice_dt)
    
    # If not general leisure, we can't proceed without knowing the business type yet.
    # The is_work_time check will be done per business later.
    # For now, if it's not leisure, and we don't know the business yet, we can't definitively say "no".
    # Let's assume if it's NOT leisure, it MUST be work time for *some* business they run.
    # This part of the logic might need refinement if a citizen runs multiple businesses with different hours.

    try:
        businesses_run_by_citizen = tables['buildings'].all(
            formula=f"AND({{RunBy}}='{_escape_airtable_value(citizen_username)}', {{Category}}='business')"
        )
    except Exception as e_fetch_biz:
        log.error(f"{LogColors.FAIL}[Vérif. Business] Erreur récupération des entreprises pour {citizen_name}: {e_fetch_biz}{LogColors.ENDC}")
        return False

    if not businesses_run_by_citizen:
        return False if check_only else None

    business_needing_check = None
    business_to_check_type_def = None

    for business_check_loop in businesses_run_by_citizen:
        business_type_str_loop = business_check_loop['fields'].get('Type')
        business_def_loop = building_type_defs.get(business_type_str_loop) if business_type_str_loop else None
        
        # Check if it's work time for this specific business OR general leisure for the citizen
        can_check_this_business_now = is_general_leisure or \
                                   is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=business_def_loop)

        if not can_check_this_business_now:
            # log.debug(f"Not check time for business {business_check_loop['fields'].get('Name', business_check_loop['id'])} based on its type/class schedule.")
            continue # Skip this business if not the right time to check it

        checked_at_str_check = business_check_loop['fields'].get('CheckedAt')
        needs_check_due_to_time = False
        if not checked_at_str_check:
            needs_check_due_to_time = True
        else:
            try:
                checked_at_dt_check = datetime.fromisoformat(checked_at_str_check.replace("Z", "+00:00"))
                if checked_at_dt_check.tzinfo is None: checked_at_dt_check = pytz.UTC.localize(checked_at_dt_check)
                if (now_utc_dt - checked_at_dt_check) >= timedelta(hours=23):
                    needs_check_due_to_time = True
            except ValueError: # Invalid date string
                needs_check_due_to_time = True
        
        if needs_check_due_to_time:
            business_needing_check = business_check_loop
            business_to_check_type_def = business_def_loop # Store its definition
            break 
    
    if not business_needing_check:
        return False if check_only else None # No business needs checking at this time

    # If we found a business needing check, re-verify if it's appropriate time using its specific definition
    # This is a bit redundant if is_general_leisure was true, but ensures correctness if it wasn't.
    if not (is_general_leisure or is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=business_to_check_type_def)):
        # log.debug(f"Final time check failed for selected business {business_needing_check['fields'].get('Name')}. Not leisure or specific work time.")
        return False if check_only else None


    if check_only:
        # Check if pathing is possible if not at the business
        if not citizen_position: return False
        business_pos_check = _get_building_position_coords(business_needing_check)
        if not business_pos_check: return False
        if _calculate_distance_meters(citizen_position, business_pos_check) > 20:
            path_check = get_path_between_points(citizen_position, business_pos_check, transport_api_url)
            return bool(path_check and path_check.get('success'))
        return True # At business or path possible

    # Actual creation logic
    business_custom_id = business_needing_check['fields'].get('BuildingId')
    business_name_display = _get_bldg_display_name_module(tables, business_needing_check)
    log.info(f"{LogColors.OKCYAN}[Vérif. Business] {business_name_display} (géré par {citizen_name}) nécessite une vérification.{LogColors.ENDC}")
    
    path_to_business = None
    if not citizen_position: return None
    business_pos = _get_building_position_coords(business_needing_check)
    if not business_pos: return None

    if _calculate_distance_meters(citizen_position, business_pos) > 20:
        path_to_business = get_path_between_points(citizen_position, business_pos, transport_api_url)
        if not (path_to_business and path_to_business.get('success')):
            log.warning(f"{LogColors.WARNING}[Vérif. Business] Impossible de trouver un chemin vers {business_name_display} pour {citizen_name}.{LogColors.ENDC}")
            return None
    
    activity_record = try_create_check_business_status_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        business_custom_id, path_to_business, now_utc_dt
    )
    if activity_record:
        log.info(f"{LogColors.OKGREEN}[Vérif. Business] Activité 'check_business_status' créée pour {citizen_name} vers {business_name_display}.{LogColors.ENDC}")
    return activity_record


def _handle_night_shelter(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str 
) -> Optional[Dict]:
    """Prio 15: Handles finding night shelter (home or inn) if it's rest time."""
    if not is_rest_time_for_class(citizen_social_class, now_venice_dt):
        return None
    if not citizen_position: return None

    log.info(f"{LogColors.OKCYAN}[Repos] Citoyen {citizen_name} ({citizen_social_class}): Période de repos. Évaluation abri.{LogColors.ENDC}")
    is_forestieri = citizen_social_class == "Forestieri"

    # Calculate end time for rest based on class schedule
    # Get the 'rest' periods for the citizen's social class
    schedule = SOCIAL_CLASS_SCHEDULES.get(citizen_social_class, {})
    rest_periods = schedule.get("rest", [])
    if not rest_periods:
        log.error(f"No rest periods defined for {citizen_social_class}. Cannot calculate rest end time.")
        # Fallback to a generic 6 AM end time if schedule is missing, though this shouldn't happen.
        venice_now_for_rest_fallback = now_utc_dt.astimezone(VENICE_TIMEZONE)
        if venice_now_for_rest_fallback.hour < NIGHT_END_HOUR_FOR_STAY:
             end_time_venice_rest = venice_now_for_rest_fallback.replace(hour=NIGHT_END_HOUR_FOR_STAY, minute=0, second=0, microsecond=0)
        else:
             end_time_venice_rest = (venice_now_for_rest_fallback + timedelta(days=1)).replace(hour=NIGHT_END_HOUR_FOR_STAY, minute=0, second=0, microsecond=0)
    else:
        # Determine the end of the current or upcoming rest period
        # This logic assumes rest periods are sorted and handles overnight.
        # For simplicity, find the next rest end hour after current time.
        current_hour_venice = now_venice_dt.hour
        end_hour_of_current_rest_period = -1

        for start_h, end_h in rest_periods:
            if start_h <= end_h: # Same day
                if start_h <= current_hour_venice < end_h:
                    end_hour_of_current_rest_period = end_h
                    break
            else: # Overnight
                if current_hour_venice >= start_h: # Currently in the first part of overnight rest
                    end_hour_of_current_rest_period = end_h # End hour is on the next day
                    break
                elif current_hour_venice < end_h: # Currently in the second part of overnight rest
                    end_hour_of_current_rest_period = end_h
                    break
        
        if end_hour_of_current_rest_period == -1: # Should not happen if is_rest_time_for_class was true
            log.warning(f"Could not determine current rest period end for {citizen_name}. Defaulting end time.")
            end_time_venice_rest = (now_venice_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0) # Default 1h rest
        else:
            # If the end_hour is for "next day" (e.g. rest is 22-06, current is 23, end_hour is 6)
            # or if current_hour is already past the start of a period that ends on the same day.
            target_date = now_venice_dt
            # If current hour is in an overnight period that started "yesterday" (e.g. current 01:00, period 22-06)
            # OR if current hour is in a period that started today and ends "tomorrow" (e.g. current 23:00, period 22-06)
            # and the end_hour_of_current_rest_period is less than current_hour_venice (meaning it's next day's hour)
            # This logic needs to be robust for all cases.
            # Simpler: if end_hour < current_hour (and it's an overnight block), it's next day.
            # Or if it's a normal block, it's same day.
            
            # Find the specific (start, end) block we are in or about to be in.
            chosen_rest_block_end_hour = -1
            is_overnight_block_ending_next_day = False # Correctly indicates if the chosen block itself is overnight

            for start_h, end_h in rest_periods:
                current_block_is_overnight = (start_h > end_h)
                if not current_block_is_overnight: # Same day block
                    if start_h <= current_hour_venice < end_h:
                        chosen_rest_block_end_hour = end_h
                        is_overnight_block_ending_next_day = False # This chosen block is not overnight
                        break
                else: # Overnight block (e.g. 22 to 06)
                    if current_hour_venice >= start_h: # e.g. current 23:00, in block 22-06
                        chosen_rest_block_end_hour = end_h
                        is_overnight_block_ending_next_day = True # This chosen block is overnight
                        break
                    elif current_hour_venice < end_h: # e.g. current 01:00, in block 22-06 (started prev day)
                        chosen_rest_block_end_hour = end_h
                        is_overnight_block_ending_next_day = True # This chosen block is overnight
                        break
            
            if chosen_rest_block_end_hour != -1:
                # Handle end_hour being 24 (midnight of the next day)
                actual_end_hour_for_replace = chosen_rest_block_end_hour
                add_day_for_midnight_24 = False
                if chosen_rest_block_end_hour == 24:
                    actual_end_hour_for_replace = 0
                    add_day_for_midnight_24 = True

                end_time_venice_rest = now_venice_dt.replace(hour=actual_end_hour_for_replace, minute=0, second=0, microsecond=0)
                
                if add_day_for_midnight_24:
                    end_time_venice_rest += timedelta(days=1)
                # For overnight blocks like (22, 6), if current time is 23:00, chosen_rest_block_end_hour is 6.
                # actual_end_hour_for_replace is 6. is_overnight_block_ending_next_day is True.
                # 6 <= 23 is true, so we add a day.
                elif is_overnight_block_ending_next_day and actual_end_hour_for_replace <= current_hour_venice:
                    end_time_venice_rest += timedelta(days=1)
                # If current time is already past the calculated end time for today (e.g. current 07:00, end_hour 06:00 from a 22-06 block)
                # this means we are past the rest period. This case should ideally be caught by is_rest_time_for_class.
                # However, if is_rest_time_for_class was true, and we are here, it means we are *in* a rest period.
            else: # Fallback, should not be reached if is_rest_time_for_class is accurate
                log.error(f"Logic error determining rest end time for {citizen_name}. Defaulting.")
                end_time_venice_rest = (now_venice_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    stay_end_time_utc_iso = end_time_venice_rest.astimezone(pytz.UTC).isoformat()

    if not is_forestieri: # Resident logic
        home_record = get_citizen_home(tables, citizen_username)
        if not home_record: # Homeless resident
            log.info(f"{LogColors.WARNING}[Repos] Citoyen {citizen_name} ({citizen_social_class}): Sans domicile. Recherche d'une auberge.{LogColors.ENDC}")
        else: # Resident with a home
            home_name_display = _get_bldg_display_name_module(tables, home_record)
            home_pos = _get_building_position_coords(home_record)
            home_custom_id_val = home_record['fields'].get('BuildingId', home_record['id'])
            if not home_pos or not home_custom_id_val: return None

            if _calculate_distance_meters(citizen_position, home_pos) < 20: # Is at home
                stay_activity = try_create_stay_activity(
                    tables, citizen_custom_id, citizen_username, citizen_airtable_id, 
                    home_custom_id_val, "home", stay_end_time_utc_iso, now_utc_dt, start_time_utc_iso=None
                )
                if stay_activity:
                    log.info(f"{LogColors.OKGREEN}[Repos] Citoyen {citizen_name} ({citizen_social_class}): Activité 'rest' (maison) créée à {home_name_display}.{LogColors.ENDC}")
                return stay_activity
            else: # Not at home, go home then rest
                path_to_home = get_path_between_points(citizen_position, home_pos, transport_api_url)
                if not (path_to_home and path_to_home.get('success')): return None
                
                goto_home_activity = try_create_goto_home_activity(
                    tables, citizen_custom_id, citizen_username, citizen_airtable_id, 
                    home_custom_id_val, path_to_home, now_utc_dt # start_time_utc_iso is None for goto_home
                )
                if goto_home_activity:
                    log.info(f"{LogColors.OKGREEN}[Repos] Citoyen {citizen_name} ({citizen_social_class}): Activité 'goto_home' créée vers {home_name_display}.{LogColors.ENDC}")
                    next_start_time_iso = goto_home_activity['fields']['EndDate']
                    stay_activity_chained = try_create_stay_activity(
                        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                        home_custom_id_val, "home", stay_end_time_utc_iso, now_utc_dt, 
                        start_time_utc_iso=next_start_time_iso
                    )
                    if stay_activity_chained:
                        log.info(f"{LogColors.OKGREEN}[Repos] Citoyen {citizen_name}: Activité 'rest' (maison) chaînée après 'goto_home', début à {next_start_time_iso}.{LogColors.ENDC}")
                    else:
                        log.warning(f"{LogColors.WARNING}[Repos] Citoyen {citizen_name}: Échec de la création de 'rest' (maison) chaînée.{LogColors.ENDC}")
                    return goto_home_activity # Return first activity of chain
                return None # Failed to create goto_home
            return None # Failed to rest or go home for resident with home

    # Forestieri or Homeless Resident logic (Inn)
    log.info(f"{LogColors.OKCYAN}[Repos] Citoyen {citizen_name} ({citizen_social_class} - {'Forestieri' if is_forestieri else 'Résident sans abri'}): Recherche d'une auberge.{LogColors.ENDC}")
    closest_inn_record = get_closest_building_of_type(tables, citizen_position, "inn")
    if not closest_inn_record: return None

    inn_name_display = _get_bldg_display_name_module(tables, closest_inn_record)
    inn_pos = _get_building_position_coords(closest_inn_record)
    inn_custom_id_val = closest_inn_record['fields'].get('BuildingId', closest_inn_record['id'])
    if not inn_pos or not inn_custom_id_val: return None

    if _calculate_distance_meters(citizen_position, inn_pos) < 20: # Is at inn
        stay_activity_inn = try_create_stay_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id, 
            inn_custom_id_val, "inn", stay_end_time_utc_iso, now_utc_dt, start_time_utc_iso=None
        )
        if stay_activity_inn:
            log.info(f"{LogColors.OKGREEN}[Nuit] Citoyen {citizen_name}: Activité 'rest' (auberge) créée à {inn_name_display}.{LogColors.ENDC}")
        return stay_activity_inn
    else: # Not at inn, go to inn then rest
        path_to_inn = get_path_between_points(citizen_position, inn_pos, transport_api_url)
        if not (path_to_inn and path_to_inn.get('success')): return None
        
        goto_inn_activity = try_create_travel_to_inn_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id, 
            inn_custom_id_val, path_to_inn, now_utc_dt # start_time_utc_iso is None for travel_to_inn
        )
        if goto_inn_activity:
            log.info(f"{LogColors.OKGREEN}[Nuit] Citoyen {citizen_name}: Activité 'travel_to_inn' créée vers {inn_name_display}.{LogColors.ENDC}")
            next_start_time_iso = goto_inn_activity['fields']['EndDate']
            stay_activity_inn_chained = try_create_stay_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                inn_custom_id_val, "inn", stay_end_time_utc_iso, now_utc_dt,
                start_time_utc_iso=next_start_time_iso
            )
            if stay_activity_inn_chained:
                log.info(f"{LogColors.OKGREEN}[Nuit] Citoyen {citizen_name}: Activité 'rest' (auberge) chaînée après 'travel_to_inn', début à {next_start_time_iso}.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}[Nuit] Citoyen {citizen_name}: Échec de la création de 'rest' (auberge) chaînée.{LogColors.ENDC}")
            return goto_inn_activity # Return first activity of chain
        return None # Failed to create travel_to_inn
    return None

def _handle_shop_for_food_at_retail(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str # Added social_class
) -> Optional[Dict]:
    """Prio 20 (was 5): Handles shopping for food at retail_food if hungry, has home, and it's leisure time."""
    # This is now a lower priority than general work/production, happens during leisure.
    if not citizen_record['is_hungry']: return None
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    if not citizen_position: return None

    home_record = get_citizen_home(tables, citizen_username)
    # For shopping, having a home is not strictly necessary if they can store in inventory,
    # but the current logic delivers to home. We can adjust this if needed.
    # For now, let's keep the home requirement for this specific handler.
    if not home_record:
        log.info(f"{LogColors.OKBLUE}[Achat Nourriture Détail] Citoyen {citizen_name} ({citizen_social_class}): Sans domicile. Cette logique d'achat livre à domicile.{LogColors.ENDC}")
        return None
    
    home_custom_id = home_record['fields'].get('BuildingId')
    if not home_custom_id: return None # Should not happen if home_record is valid

    citizen_ducats = float(citizen_record['fields'].get('Ducats', 0))
    if citizen_ducats < FOOD_SHOPPING_COST_ESTIMATE: # Estimate for 1-2 units of food
        log.info(f"{LogColors.OKBLUE}[Achat Nourriture] Citoyen {citizen_name}: Pas assez de Ducats ({citizen_ducats:.2f}) pour acheter de la nourriture (Estimation: {FOOD_SHOPPING_COST_ESTIMATE}).{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.OKCYAN}[Achat Nourriture] Citoyen {citizen_name}: Affamé, a un domicile et des Ducats. Recherche de magasins d'alimentation.{LogColors.ENDC}")

    # citizen_social_class is already a parameter
    citizen_tier = SOCIAL_CLASS_VALUE.get(citizen_social_class, 1) # Default to tier 1

    try:
        retail_food_buildings = tables['buildings'].all(formula="AND({SubCategory}='retail_food', {IsConstructed}=TRUE())")
    except Exception as e_fetch_shops:
        log.error(f"{LogColors.FAIL}[Achat Nourriture] Erreur récupération des magasins 'retail_food': {e_fetch_shops}{LogColors.ENDC}")
        return None

    if not retail_food_buildings:
        log.info(f"{LogColors.OKBLUE}[Achat Nourriture] Aucun magasin 'retail_food' trouvé.{LogColors.ENDC}")
        return None

    best_deal_info = None 
    best_tier_priority_score = float('inf') # Lower is better for tier priority (0 is perfect match)
    best_secondary_score = -float('inf')    # Higher is better for price * distance

    for shop_rec in retail_food_buildings:
        shop_pos = _get_building_position_coords(shop_rec)
        shop_custom_id_val = shop_rec['fields'].get('BuildingId')
        shop_custom_id: Optional[str] = None # Renommé pour éviter confusion avec la variable finale

        temp_val_for_id = shop_custom_id_val
        # Tentative de dérouler une potentielle structure imbriquée (liste/tuple dans liste/tuple)
        if isinstance(temp_val_for_id, (list, tuple)):
            if temp_val_for_id: # Si la liste/tuple externe n'est pas vide
                temp_val_for_id = temp_val_for_id[0] # Prendre le premier élément
            else:
                log.warning(f"{LogColors.WARNING}[Achat Nourriture] BuildingId (externe) pour le magasin {shop_rec.get('id', 'Unknown ID')} est une liste/tuple vide. Ignoré.{LogColors.ENDC}")
                continue
        
        # Vérifier à nouveau si l'élément interne est une liste/tuple
        if isinstance(temp_val_for_id, (list, tuple)):
            if temp_val_for_id: # Si la liste/tuple interne n'est pas vide
                temp_val_for_id = temp_val_for_id[0] # Prendre le premier élément de la structure interne
            else:
                log.warning(f"{LogColors.WARNING}[Achat Nourriture] BuildingId (interne) pour le magasin {shop_rec.get('id', 'Unknown ID')} est une liste/tuple vide. Ignoré.{LogColors.ENDC}")
                continue
        
        # À ce stade, temp_val_for_id devrait être la valeur ID brute ou None
        if temp_val_for_id is not None:
            shop_custom_id = str(temp_val_for_id) # Convertir en chaîne
        else:
            log.warning(f"{LogColors.WARNING}[Achat Nourriture] BuildingId pour le magasin {shop_rec.get('id', 'Unknown ID')} est None ou est devenu None après traitement. Ignoré.{LogColors.ENDC}")
            continue

        # Vérification finale après traitement de shop_custom_id
        if not shop_pos or not shop_custom_id:
            log.warning(f"{LogColors.WARNING}[Achat Nourriture] Position ou ID de magasin invalide après traitement pour {shop_rec.get('id', 'Unknown ID')}. shop_custom_id: {shop_custom_id}. Ignoré.{LogColors.ENDC}")
            continue

        distance_to_shop = _calculate_distance_meters(citizen_position, shop_pos)
        if distance_to_shop == float('inf'): continue

        # Simplified Airtable query: fetch all contracts for the shop
        # The shop_custom_id is already validated as a string.
        # Use SEARCH and ARRAYJOIN for SellerBuilding to handle cases where it might be a list/tuple in Airtable.
        formula_shop_contracts = f"SEARCH('${_escape_airtable_value(shop_custom_id)}', ARRAYJOIN({{SellerBuilding}}))"
        
        try:
            all_shop_contracts = tables['contracts'].all(formula=formula_shop_contracts)
        except Exception as e_fetch_all_shop_contracts:
            log.error(f"{LogColors.FAIL}[Achat Nourriture] Erreur récupération des contrats pour le magasin {shop_custom_id}: {e_fetch_all_shop_contracts}{LogColors.ENDC}")
            continue # Try next shop

        for food_type_id in FOOD_RESOURCE_TYPES_FOR_EATING:
            candidate_contracts_for_food_type = []
            for contract_rec in all_shop_contracts:
                fields = contract_rec.get('fields', {})
                
                # Python-side filtering
                if fields.get('Type') != 'public_sell': continue
                if fields.get('ResourceType') != food_type_id: continue
                if float(fields.get('TargetAmount', 0)) <= 0: continue

                created_at_str = fields.get('CreatedAt')
                end_at_str = fields.get('EndAt')
                if not created_at_str or not end_at_str: continue

                try:
                    created_at_dt = dateutil_parser.isoparse(created_at_str)
                    end_at_dt = dateutil_parser.isoparse(end_at_str)
                    if created_at_dt.tzinfo is None: created_at_dt = pytz.utc.localize(created_at_dt)
                    if end_at_dt.tzinfo is None: end_at_dt = pytz.utc.localize(end_at_dt)

                    if not (created_at_dt <= now_utc_dt <= end_at_dt):
                        continue # Contract not active
                except Exception as e_date_parse:
                    log.warning(f"Could not parse dates for contract {fields.get('ContractId', 'N/A')}: {e_date_parse}")
                    continue
                
                candidate_contracts_for_food_type.append(contract_rec)

            if not candidate_contracts_for_food_type:
                continue

            # Sort candidates by price (ascending)
            candidate_contracts_for_food_type.sort(key=lambda c: float(c.get('fields', {}).get('PricePerResource', float('inf'))))
            
            if candidate_contracts_for_food_type:
                best_contract_for_this_food_at_shop = candidate_contracts_for_food_type[0]
                price = float(best_contract_for_this_food_at_shop.get('fields', {}).get('PricePerResource', float('inf')))
                if price == float('inf'): continue

                resource_tier_from_def = resource_defs.get(food_type_id, {}).get('tier')
                try:
                    resource_tier = int(resource_tier_from_def) if resource_tier_from_def is not None else 99
                except ValueError:
                    resource_tier = 99
                
                current_tier_priority = abs(resource_tier - citizen_tier)
                current_secondary_score = price * distance_to_shop if distance_to_shop != float('inf') else -float('inf')

                is_better_deal = False
                if current_tier_priority < best_tier_priority_score:
                    is_better_deal = True
                elif current_tier_priority == best_tier_priority_score:
                    if current_secondary_score > best_secondary_score:
                        is_better_deal = True
                
                if is_better_deal:
                    path_to_shop = get_path_between_points(citizen_position, shop_pos, transport_api_url)
                    if path_to_shop and path_to_shop.get('success'):
                        best_tier_priority_score = current_tier_priority
                        best_secondary_score = current_secondary_score
                        best_deal_info = {
                            "contract_rec": best_contract_for_this_food_at_shop, "shop_rec": shop_rec, 
                            "food_type_id": food_type_id, "price": price, 
                            "path_to_shop": path_to_shop,
                            "tier_priority_debug": current_tier_priority, 
                            "secondary_score_debug": current_secondary_score 
                        }
    
    if best_deal_info:
        shop_display_name = _get_bldg_display_name_module(tables, best_deal_info["shop_rec"])
        shop_custom_id_for_activity = best_deal_info["shop_rec"]['fields'].get('BuildingId')
        food_display_name = _get_res_display_name_module(best_deal_info["food_type_id"], resource_defs)
        price_for_this_meal = best_deal_info['price']

        log.info(f"{LogColors.OKBLUE}[Achat Nourriture] Meilleure offre trouvée: {food_display_name} à {shop_display_name} pour {price_for_this_meal:.2f} Ducats (Priorité Tier: {best_deal_info['tier_priority_debug']}, Score Sec: {best_deal_info['secondary_score_debug']:.2f}).{LogColors.ENDC}")

        if citizen_ducats < price_for_this_meal: # Check against the actual price of the chosen food
            log.info(f"{LogColors.WARNING}[Achat Nourriture] Pas assez de Ducats ({citizen_ducats:.2f}) pour acheter {food_display_name} à {price_for_this_meal:.2f} Ducats.{LogColors.ENDC}")
            return None
        
        # Determine if citizen is at the shop
        is_at_shop = False
        if citizen_position and best_deal_info["shop_rec"]:
            shop_pos_for_check = _get_building_position_coords(best_deal_info["shop_rec"])
            if shop_pos_for_check and _calculate_distance_meters(citizen_position, shop_pos_for_check) < 20:
                is_at_shop = True
        
        if is_at_shop:
            log.info(f"{LogColors.OKBLUE}[Achat Nourriture] Citoyen {citizen_name} est déjà à {shop_display_name}. Création de l'activité 'eat_at_tavern'.{LogColors.ENDC}")
            # Prepare details for the eat_at_tavern activity
            activity_details = {
                "is_retail_purchase": True,
                "food_resource_id": best_deal_info["food_type_id"],
                "price": price_for_this_meal,
                "original_contract_id": best_deal_info["contract_rec"]['fields'].get('ContractId', best_deal_info["contract_rec"]['id'])
            }
            eat_activity_at_shop = try_create_eat_at_tavern_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id, 
                shop_custom_id_for_activity, # Use shop ID as tavern ID
                now_utc_dt, resource_defs,
                details_payload=activity_details # Pass the details
            )
            if eat_activity_at_shop:
                # No specific log here, creator handles it. Return the activity record.
                return eat_activity_at_shop # Return the created activity record or None
        else:
            log.info(f"{LogColors.OKBLUE}[Achat Nourriture] Citoyen {citizen_name} n'est pas à {shop_display_name}. Création de l'activité 'travel_to_inn'.{LogColors.ENDC}")
            # Path to shop is in best_deal_info["path_to_shop"]
            # The travel_to_inn creator is generic enough for any destination.
            # The subsequent 'eat_at_tavern' activity will handle the purchase logic.
            # We need to ensure the 'eat_at_tavern' activity knows this is a retail purchase.
            # This can be done by adding details to the 'goto_location' (travel_to_inn) activity,
            # which are then passed to the chained 'eat_at_tavern' activity.
            
            # For now, the existing travel_to_inn and eat_at_tavern creators are used.
            # The eat_at_tavern processor will need to be aware of retail purchases if different logic applies.
            # The current eat_at_tavern creator doesn't take specific food item details, it assumes a generic meal.
            # This might need adjustment if we want them to buy a *specific* item from the shop.
            # For now, let's assume they go to the shop and the 'eat_at_tavern' activity implies buying *something* there.

            goto_activity = try_create_travel_to_inn_activity( # This creates a 'goto_location'
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                shop_custom_id_for_activity, 
                best_deal_info["path_to_shop"], 
                now_utc_dt
            )
            if goto_activity:
                log.info(f"{LogColors.OKGREEN}[Achat Nourriture] Citoyen {citizen_name}: Activité 'goto_location' (vers magasin {shop_display_name}) créée pour acheter et manger {food_display_name}.{LogColors.ENDC}")
                # Chain the 'eat_at_tavern' activity to occur upon arrival
                next_start_time_iso = goto_activity['fields']['EndDate']
                eat_activity_details = {
                    "is_retail_purchase": True,
                    "food_resource_id": best_deal_info["food_type_id"],
                    "price": price_for_this_meal,
                    "original_contract_id": best_deal_info["contract_rec"]['fields'].get('ContractId', best_deal_info["contract_rec"]['id'])
                }
                chained_eat_activity = try_create_eat_at_tavern_activity(
                    tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                    shop_custom_id_for_activity, # Target building is the shop
                    now_utc_dt, resource_defs,
                    start_time_utc_iso=next_start_time_iso,
                    details_payload=eat_activity_details # Pass purchase details
                )
                if chained_eat_activity:
                    log.info(f"{LogColors.OKGREEN}[Achat Nourriture] Activité 'eat_at_provider' (eat_at_tavern) chaînée pour {food_display_name} à {shop_display_name}, début à {next_start_time_iso}.{LogColors.ENDC}")
                else:
                    log.warning(f"{LogColors.WARNING}[Achat Nourriture] Échec de la création de 'eat_at_provider' (eat_at_tavern) chaînée.{LogColors.ENDC}")
                return goto_activity # Return the first activity of the chain (goto_activity)
    else:
        log.info(f"{LogColors.OKBLUE}[Achat Nourriture] Aucune offre de nourriture appropriée trouvée pour {citizen_name} selon les critères de priorité.{LogColors.ENDC}")
        
    return None

def _handle_fishing(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str # Added social_class
) -> Optional[Dict]:
    """Prio 32: Handles regular fishing if citizen is Facchini, it's work time, and they are a fisherman."""
    if citizen_social_class != "Facchini":
        return None
    # Fishing is a generic Facchini task, not tied to a specific building type's hours, so use class schedule.
    if not is_work_time(citizen_social_class, now_venice_dt): # Pass no workplace_type
        return None
        
    home_record = get_citizen_home(tables, citizen_username) # Fishermen live in fisherman's cottages
    if not (home_record and home_record['fields'].get('Type') == 'fisherman_s_cottage'):
        return None # Not a fisherman (based on home type)

    # Check if they have a formal "Workplace" record. If so, they should do that job.
    # This fishing is for those Facchini in fisherman's cottages without other assigned work.
    workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    if workplace_record:
        return None # Has other work

    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Pêche Régulière] {citizen_name} n'a pas de position. Impossible de pêcher.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.OKCYAN}[Pêche Régulière] {citizen_name} (Facchini pêcheur sans autre travail) en période de travail. Recherche lieu de pêche.{LogColors.ENDC}")
    
    target_wp_id, target_wp_pos, path_data = _find_closest_fishable_water_point(citizen_position, api_base_url, transport_api_url)

    if target_wp_id and path_data:
        activity_record = try_create_fishing_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            target_wp_id, path_data, now_utc_dt, activity_type="fishing"
        )
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Pêche] {citizen_name}: Activité 'fishing' créée vers {target_wp_id}.{LogColors.ENDC}")
            return activity_record
    else:
        log.info(f"{LogColors.OKBLUE}[Pêche] {citizen_name}: Aucun lieu de pêche accessible trouvé.{LogColors.ENDC}")
        
    return None

def _handle_work_on_art(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str,
    check_only: bool = False
) -> Union[Optional[Dict], bool]:
    """Prio 35: Handles Artisti working on their art if it's work/leisure time."""
    if citizen_social_class != "Artisti":
        return False if check_only else None

    if not (is_work_time(citizen_social_class, now_venice_dt) or \
            is_leisure_time_for_class(citizen_social_class, now_venice_dt)):
        return False if check_only else None

    if not citizen_position: # Required for location checks
        return False if check_only else None

    # Logic to find target location (home or art_gallery)
    target_location_record: Optional[Dict[str, Any]] = None
    art_gallery_record = get_closest_building_of_type(tables, citizen_position, "art_gallery")
    if art_gallery_record:
        target_location_record = art_gallery_record
    else:
        home_record = get_citizen_home(tables, citizen_username)
        if home_record:
            target_location_record = home_record
        else:
            return False if check_only else None # No suitable location

    if not target_location_record: # Should be caught above, but defensive
        return False if check_only else None

    target_location_pos = _get_building_position_coords(target_location_record)
    if not target_location_pos:
        return False if check_only else None

    is_at_target_location = _calculate_distance_meters(citizen_position, target_location_pos) < 20

    if check_only:
        if is_at_target_location:
            return True # Can create work_on_art directly
        else: # Needs travel
            # Simulate path check without creating activity
            path_to_target = get_path_between_points(citizen_position, target_location_pos, transport_api_url)
            return bool(path_to_target and path_to_target.get('success'))

    # Actual creation logic (delegated to the creator function)
    log.info(f"{LogColors.OKCYAN}[Artiste Travail] {citizen_name} (Artisti) en période de travail/loisir. Tentative de création d'activité 'work_on_art'.{LogColors.ENDC}")
    activity_record = try_create_work_on_art_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=citizen_position,
        now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url,
        start_time_utc_iso=None
    )

    if activity_record:
        log.info(f"{LogColors.OKGREEN}[Artiste Travail] {citizen_name}: Activité 'work_on_art' (ou chaîne goto_location->work_on_art) créée.{LogColors.ENDC}")
    else:
        log.info(f"{LogColors.OKBLUE}[Artiste Travail] {citizen_name}: Impossible de créer une activité 'work_on_art'.{LogColors.ENDC}")
        
    return activity_record

def _handle_attend_theater_performance(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str,
    check_only: bool = False
) -> Union[Optional[Dict], bool]:
    """Prio 45: Handles going to the theater if it's leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return False if check_only else None
    
    if not citizen_position: # Required for location checks
        return False if check_only else None

    # Check if citizen can afford it (rough check, processor does final check)
    cost = THEATER_COSTS.get(citizen_social_class, DEFAULT_THEATER_COST)
    if float(citizen_record['fields'].get('Ducats', 0.0)) < cost:
        return False if check_only else None

    # Check if a theater exists and is reachable
    theater_record = get_closest_building_of_type(tables, citizen_position, "theater")
    if not theater_record:
        return False if check_only else None
    
    theater_pos = _get_building_position_coords(theater_record)
    if not theater_pos:
        return False if check_only else None

    if check_only:
        if _calculate_distance_meters(citizen_position, theater_pos) < 20:
            return True # Can create attend_theater_performance directly
        else: # Needs travel
            path_to_theater = get_path_between_points(citizen_position, theater_pos, transport_api_url)
            return bool(path_to_theater and path_to_theater.get('success'))

    # Actual creation logic
    log.info(f"{LogColors.OKCYAN}[Théâtre] {citizen_name} ({citizen_social_class}) en période de loisirs. Tentative de création d'activité 'attend_theater_performance'.{LogColors.ENDC}")
    activity_chain_start = try_create_attend_theater_performance_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=citizen_position,
        resource_defs=resource_defs, # Added
        building_type_defs=building_type_defs, # Added
        now_venice_dt=now_venice_dt, # Added
        now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url,
        api_base_url=api_base_url, # Added
        start_time_utc_iso=None # Immediate start for the chain
    )
    if activity_chain_start:
        log.info(f"{LogColors.OKGREEN}[Théâtre] {citizen_name}: Chaîne d'activités 'aller au théâtre' créée.{LogColors.ENDC}")
    else:
        log.info(f"{LogColors.OKBLUE}[Théâtre] {citizen_name}: Impossible de créer une chaîne d'activités 'aller au théâtre'.{LogColors.ENDC}")
    return activity_chain_start

def _handle_drink_at_inn(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str,
    check_only: bool = False
) -> Union[Optional[Dict], bool]:
    """Prio 40: Handles going to an inn to drink if it's leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return False if check_only else None
    
    if not citizen_position: return False if check_only else None

    # Check if citizen can afford a drink (rough estimate, processor does final check)
    # Assume a drink costs at least 5-10 ducats.
    if float(citizen_record['fields'].get('Ducats', 0.0)) < 5.0:
        return False if check_only else None

    # Check if any inn sells wine/spiced_wine and has stock
    potential_inns = tables['buildings'].all(formula="{Type}='inn'")
    valid_inn_found = False
    for inn_candidate_record_check in potential_inns:
        inn_candidate_id_check = inn_candidate_record_check['fields'].get('BuildingId')
        if not inn_candidate_id_check: continue
        for drink_type_check in DRINKABLE_RESOURCE_TYPES: # DRINKABLE_RESOURCE_TYPES from creator
            contract_formula_check = (
                f"AND({{Type}}='public_sell', {{SellerBuilding}}='{_escape_airtable_value(inn_candidate_id_check)}', "
                f"{{ResourceType}}='{_escape_airtable_value(drink_type_check)}', {{TargetAmount}}>0, "
                f"{{EndAt}}>'{now_utc_dt.isoformat()}', {{CreatedAt}}<='{now_utc_dt.isoformat()}' )"
            )
            try:
                contracts_check = tables['contracts'].all(formula=contract_formula_check, max_records=1)
                if contracts_check:
                    inn_operator_check = inn_candidate_record_check['fields'].get('RunBy') or inn_candidate_record_check['fields'].get('Owner')
                    if inn_operator_check:
                        from backend.engine.utils.activity_helpers import get_source_building_resource_stock # Local import
                        stock_check = get_source_building_resource_stock(tables, inn_candidate_id_check, drink_type_check, inn_operator_check)
                        if stock_check >= 1.0:
                            valid_inn_found = True; break
            except Exception: pass # Ignore errors during check_only
        if valid_inn_found: break
    
    if not valid_inn_found:
        return False if check_only else None

    if check_only: return True # If an inn with drinks exists, assume it's possible

    # Actual creation logic
    log.info(f"{LogColors.OKCYAN}[Boire Auberge] {citizen_name} ({citizen_social_class}) en période de loisirs. Tentative de création d'activité 'drink_at_inn'.{LogColors.ENDC}")
    activity_chain_start = try_create_drink_at_inn_activity(
        tables=tables, citizen_record=citizen_record, citizen_position=citizen_position,
        resource_defs=resource_defs, building_type_defs=building_type_defs,
        now_venice_dt=now_venice_dt, now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url, api_base_url=api_base_url,
        start_time_utc_iso=None
    )
    if activity_chain_start:
        log.info(f"{LogColors.OKGREEN}[Boire Auberge] {citizen_name}: Chaîne d'activités 'boire à l'auberge' créée.{LogColors.ENDC}")
    else:
        log.info(f"{LogColors.OKBLUE}[Boire Auberge] {citizen_name}: Impossible de créer une chaîne d'activités 'boire à l'auberge'.{LogColors.ENDC}")
    return activity_chain_start

def _handle_use_public_bath(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str,
    check_only: bool = False
) -> Union[Optional[Dict], bool]:
    """Prio 42: Handles going to a public bath if it's leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return False if check_only else None
    
    if not citizen_position: return False if check_only else None

    # Check if citizen can afford it (rough estimate, processor does final check)
    cost_map = { "Facchini": 25, "Popolani": 25, "Cittadini": 40, "Nobili": 100, "Forestieri": 40, "Artisti": 30 }
    default_cost = 25
    cost = cost_map.get(citizen_social_class, default_cost)
    if float(citizen_record['fields'].get('Ducats', 0.0)) < cost:
        return False if check_only else None

    # Check if a public_bath exists and is reachable
    bath_record = get_closest_building_of_type(tables, citizen_position, "public_bath")
    if not bath_record:
        return False if check_only else None
    
    bath_pos = _get_building_position_coords(bath_record)
    if not bath_pos:
        return False if check_only else None

    if check_only:
        if _calculate_distance_meters(citizen_position, bath_pos) < 20:
            return True # Can create use_public_bath directly
        else: # Needs travel
            path_to_bath = get_path_between_points(citizen_position, bath_pos, transport_api_url)
            return bool(path_to_bath and path_to_bath.get('success'))

    # Actual creation logic
    log.info(f"{LogColors.OKCYAN}[Bain Public] {citizen_name} ({citizen_social_class}) en période de loisirs. Tentative de création d'activité 'use_public_bath'.{LogColors.ENDC}")
    activity_chain_start = try_create_use_public_bath_activity(
        tables=tables, citizen_record=citizen_record, citizen_position=citizen_position,
        resource_defs=resource_defs, building_type_defs=building_type_defs,
        now_venice_dt=now_venice_dt, now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url, api_base_url=api_base_url,
        start_time_utc_iso=None
    )
    if activity_chain_start:
        log.info(f"{LogColors.OKGREEN}[Bain Public] {citizen_name}: Chaîne d'activités 'utiliser bain public' créée.{LogColors.ENDC}")
    else:
        log.info(f"{LogColors.OKBLUE}[Bain Public] {citizen_name}: Impossible de créer une chaîne d'activités 'utiliser bain public'.{LogColors.ENDC}")
    return activity_chain_start

# --- Placeholder for new handler functions ---

def _handle_construction_tasks(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str # Added social_class
) -> bool:
    """Prio 30: Handles construction related tasks if it's work time."""
    workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    if not workplace_record or workplace_record['fields'].get('SubCategory') != 'construction':
        return False
    
    workplace_type_str = workplace_record['fields'].get('Type') # e.g., "construction_workshop"
    workplace_def = building_type_defs.get(workplace_type_str) if workplace_type_str else None
    if not is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=workplace_def):
        return False

    workplace_pos = _get_building_position_coords(workplace_record)
    if not citizen_position or not workplace_pos or _calculate_distance_meters(citizen_position, workplace_pos) > 20:
        log.info(f"{LogColors.OKBLUE}[Construction] Citoyen {citizen_name} ({citizen_social_class}) n'est pas à son atelier. Pas de tâche de construction.{LogColors.ENDC}")
        return False
    
    log.info(f"{LogColors.OKCYAN}[Construction] Citoyen {citizen_name} ({citizen_social_class}) est à son atelier. Délégation à handle_construction_worker_activity.{LogColors.ENDC}")
    # handle_construction_worker_activity expects the citizen record and workplace record.
    # It also needs building_type_defs, resource_defs, time, and api_urls.
    if handle_construction_worker_activity(
        tables, citizen_record, workplace_record,
        building_type_defs, resource_defs, 
        now_venice_dt, now_utc_dt, 
        transport_api_url, api_base_url
    ):
        log.info(f"{LogColors.OKGREEN}[Construction] Citoyen {citizen_name}: Tâche de construction créée/gérée.{LogColors.ENDC}")
        return True
    return False

def _handle_production_and_general_work_tasks(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str_val: Optional[str],
    citizen_social_class: str 
) -> Optional[Dict]:
    """
    Prio 31: Handles production, restocking for general workplaces if it's work time.
    Phases à implémenter :
    1. Production directe : créer et retourner l’activité production si possible.
    2. Réapprovisionnement : si ressources manquantes, créer une activité de fetch (storage_fetch ou fetch_resource),
       puis chaîner la production en lui passant son EndDate à start_time_utc_iso.
    3. Livraison surplus : si stockage plein et contrat storage_query, créer deliver_to_storage et retourner l’activité.
    """
    workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    if not workplace_record:
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Pas de lieu de travail trouvé. Sortie.{LogColors.ENDC}")
        return None

    workplace_type_str = workplace_record['fields'].get('Type')
    workplace_def = building_type_defs.get(workplace_type_str) if workplace_type_str else None

    if not is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=workplace_def):
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Pas l'heure de travail pour la classe '{citizen_social_class}' au lieu '{workplace_type_str}'. Sortie.{LogColors.ENDC}")
        return None
        
    # Nobili specific check: if they are at a workplace, it must have specialWorkHours,
    # otherwise their class schedule (all leisure) applies, and they wouldn't "work" there.
    if citizen_social_class == "Nobili" and (not workplace_def or not workplace_def.get("specialWorkHours")):
         log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Nobili à '{workplace_type_str}' qui n'a pas d'horaires spéciaux. Pas de travail basé sur classe. Sortie.{LogColors.ENDC}")
         return None

    workplace_category = workplace_record['fields'].get('Category', '').lower()
    workplace_subcategory = workplace_record['fields'].get('SubCategory', '').lower()
    workplace_type = workplace_record['fields'].get('Type', '')
    workplace_custom_id = workplace_record['fields'].get('BuildingId')
    workplace_operator = workplace_record['fields'].get('RunBy') or workplace_record['fields'].get('Owner')


    # This handler is for general business/production, not construction or porter guilds
    if workplace_category != 'business' or workplace_subcategory in ['construction', 'porter_guild_hall', 'storage']:
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Lieu de travail '{workplace_type}' (Cat: {workplace_category}, SubCat: {workplace_subcategory}) n'est pas une entreprise de production/générale éligible. Sortie.{LogColors.ENDC}")
        return None
    
    if not citizen_position:
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Position du citoyen inconnue. Sortie.{LogColors.ENDC}")
        return None 
    workplace_pos = _get_building_position_coords(workplace_record)
    if not workplace_pos:
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Position du lieu de travail '{workplace_custom_id}' inconnue. Sortie.{LogColors.ENDC}")
        return None
    if _calculate_distance_meters(citizen_position, workplace_pos) > 20:
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: N'est pas à son lieu de travail '{workplace_custom_id}'. La gestion du déplacement est gérée ailleurs. Sortie.{LogColors.ENDC}")
        # If not at workplace, this handler won't create a goto_work. That's handled by _handle_general_goto_work.
        return None 

    log.info(f"{LogColors.OKCYAN}[Travail Général] Citoyen {citizen_name} à {workplace_custom_id} ({workplace_type}). Évaluation des tâches.{LogColors.ENDC}")

    building_type_def = get_building_type_info(workplace_type, building_type_defs)
    if not building_type_def or 'productionInformation' not in building_type_def:
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Pas d'information de production pour le type de bâtiment '{workplace_type}'. Impossible de produire ou réapprovisionner. Sortie.{LogColors.ENDC}")
        return None
    
    prod_info = building_type_def['productionInformation']
    recipes = prod_info.get('Arti', []) if isinstance(prod_info, dict) else []
    # Correction: 'sells' est à l'intérieur de prod_info (productionInformation)
    sellable_items_defined = prod_info.get('sells', []) if isinstance(prod_info, dict) else []

    if not recipes and not sellable_items_defined:
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Aucune recette ('Arti') ni article à vendre ('sells') défini pour '{workplace_type}' dans productionInformation. Sortie.{LogColors.ENDC}")
        return None
    
    if not recipes and sellable_items_defined: # Pas de recettes, mais des articles à vendre
        log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Aucune recette ('Arti') pour '{workplace_type}', mais des articles à vendre existent. Évaluation du réapprovisionnement pour la vente.{LogColors.ENDC}")
    
    storage_capacity = float(prod_info.get('storageCapacity', 0))
    
    first_fetch_activity: Optional[Dict] = None # Initialize here

    # 1. Try to produce
    if recipes:
        current_workplace_stock_map = get_building_resources(tables, workplace_custom_id) # Fetches {res_id: count}
        for recipe_idx, recipe_def in enumerate(recipes):
            if not isinstance(recipe_def, dict): continue # Skip if recipe_def is not a dict
            
            can_produce_this_recipe = True
            if not recipe_def.get('inputs'): # Recipe with no inputs (e.g. research)
                 pass # can_produce_this_recipe remains true
            else:
                for input_res, input_qty_needed in recipe_def.get('inputs', {}).items():
                    if current_workplace_stock_map.get(input_res, 0.0) < float(input_qty_needed):
                        can_produce_this_recipe = False; break
            
            if can_produce_this_recipe:
                log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Tous les inputs pour la recette {recipe_idx} de '{workplace_type}' sont disponibles en stock.")
                # Check output space
                output_total_volume = sum(float(qty) for qty in recipe_def.get('outputs', {}).values())
                current_total_stock_volume = sum(current_workplace_stock_map.values())
                # Approximate available space check
                if storage_capacity == 0 or (storage_capacity - current_total_stock_volume + sum(float(qty) for qty in recipe_def.get('inputs', {}).values())) >= output_total_volume:
                    # Create production activity with immediate start
                    production_activity = try_create_production_activity(
                        tables, citizen_airtable_id, citizen_custom_id, citizen_username, 
                        workplace_custom_id, recipe_def, now_utc_dt, start_time_utc_iso=None
                    )
                    if production_activity:
                        log.info(f"{LogColors.OKGREEN}[Travail Général] Citoyen {citizen_name} a commencé la production à {workplace_custom_id}.{LogColors.ENDC}")
                        return production_activity # Return the created activity
                else:
                    log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Pas assez d'espace de stockage à {workplace_custom_id} pour la sortie de la recette {recipe_idx}.")
            # else: # can_produce_this_recipe is False, inputs are missing, proceed to restocking logic below.
            #    log.info(f"{LogColors.PROCESS}[Prod/Général] {citizen_name}: Inputs manquants pour la recette {recipe_idx} de '{workplace_type}'. Tentative de réapprovisionnement.")


    # 2. Try to restock inputs for production
    if recipes:
        current_workplace_stock_map_for_restock = get_building_resources(tables, workplace_custom_id)
        all_missing_inputs_for_arti = [] # Stores dicts: {"resource_id", "needed_for_recipe", "currently_in_stock", "recipe_def", "deficit"}

        for recipe_idx, recipe_def in enumerate(recipes):
            if not isinstance(recipe_def, dict): continue
            inputs_for_this_recipe = recipe_def.get('inputs', {})
            if not inputs_for_this_recipe: continue

            for input_res_id, input_qty_needed_val in inputs_for_this_recipe.items():
                input_qty_needed = float(input_qty_needed_val)
                current_stock_of_input = current_workplace_stock_map_for_restock.get(input_res_id, 0.0)
                if current_stock_of_input < input_qty_needed:
                    all_missing_inputs_for_arti.append({
                        "resource_id": input_res_id,
                        "needed_for_recipe": input_qty_needed,
                        "currently_in_stock": current_stock_of_input,
                        "recipe_def": recipe_def,
                        "deficit": input_qty_needed - current_stock_of_input
                    })
        
        if all_missing_inputs_for_arti:
            # Prioritize: resource with the lowest stock percentage relative to its need for a recipe
            all_missing_inputs_for_arti.sort(key=lambda x: (x["currently_in_stock"] / x["needed_for_recipe"]) if x["needed_for_recipe"] > 0 else float('inf'))

            log.info(f"{LogColors.PROCESS}[Prod/Général - Arti Restock] {citizen_name}: Missing inputs identified. Prioritized list (first is highest prio):")
            for i, item in enumerate(all_missing_inputs_for_arti[:3]): # Log top 3
                outputs_str = list(item['recipe_def'].get('outputs',{}).keys())
                log.info(f"  {i+1}. Res: {item['resource_id']}, Stock: {item['currently_in_stock']:.2f}/{item['needed_for_recipe']:.2f} (Deficit: {item['deficit']:.2f}) for recipe producing {outputs_str}")

            for missing_input_info in all_missing_inputs_for_arti:
                input_res_id_to_fetch = missing_input_info["resource_id"]
                # amount_to_fetch_for_recipe is the deficit for *this specific recipe's input need*
                amount_to_fetch_for_recipe = missing_input_info["deficit"] 
                recipe_def_to_chain = missing_input_info["recipe_def"]
                res_name_display = _get_res_display_name_module(input_res_id_to_fetch, resource_defs)
                
                outputs_to_chain_str = list(recipe_def_to_chain.get('outputs',{}).keys())
                log.info(f"{LogColors.OKBLUE}  [Réappro. Arti Prioritaire] {workplace_custom_id} a besoin de {amount_to_fetch_for_recipe:.2f} de {res_name_display} (pour recette {outputs_to_chain_str}).{LogColors.ENDC}")

                # Initialize first_fetch_activity for this iteration
                first_fetch_activity_for_this_input: Optional[Dict] = None

                # Prio 1: Fetch from dedicated storage contract (storage_query)
                log.info(f"    [Réappro. Arti Prio 1] Recherche de contrat 'storage_query' pour {res_name_display} (Opérateur: {workplace_operator}, Atelier: {workplace_custom_id}).")
                storage_query_contracts = tables['contracts'].all(
                    formula=f"AND({{Type}}='storage_query', {{Buyer}}='{_escape_airtable_value(workplace_operator)}', {{BuyerBuilding}}='{_escape_airtable_value(workplace_custom_id)}', {{ResourceType}}='{_escape_airtable_value(input_res_id_to_fetch)}', {{Status}}='active', IS_BEFORE(NOW(), {{EndAt}}))"
                )
                if storage_query_contracts:
                    sq_contract = storage_query_contracts[0]
                    storage_facility_id = sq_contract['fields'].get('SellerBuilding')
                    sq_contract_id_log = sq_contract['fields'].get('ContractId', sq_contract['id'])
                    if storage_facility_id:
                        storage_facility_record = get_building_record(tables, storage_facility_id)
                        if storage_facility_record:
                            facility_name_log = _get_bldg_display_name_module(tables, storage_facility_record)
                            _, facility_stock_map = get_building_storage_details(tables, storage_facility_id, workplace_operator)
                            actual_stored_amount = float(facility_stock_map.get(input_res_id_to_fetch, 0.0))
                            # Use amount_to_fetch_for_recipe (deficit for this recipe)
                            amount_to_fetch_from_storage = min(amount_to_fetch_for_recipe, actual_stored_amount)
                            amount_to_fetch_from_storage = float(f"{amount_to_fetch_from_storage:.4f}")
                            if amount_to_fetch_from_storage >= 0.1:
                                storage_facility_pos = _get_building_position_coords(storage_facility_record)
                                if citizen_position and storage_facility_pos:
                                    path_to_storage = get_path_between_points(citizen_position, storage_facility_pos, transport_api_url)
                                    if path_to_storage and path_to_storage.get('success'):
                                        goto_notes = f"Aller à {facility_name_log} pour chercher {amount_to_fetch_from_storage:.2f} {res_name_display} pour l'atelier {workplace_custom_id}."
                                        fetch_details = {"action_on_arrival": "fetch_from_storage", "original_workplace_id": workplace_custom_id, "storage_query_contract_id": sq_contract_id_log, "resources_to_fetch": [{"ResourceId": input_res_id_to_fetch, "Amount": amount_to_fetch_from_storage}]}
                                        first_fetch_activity_for_this_input = try_create_goto_work_activity(tables, citizen_custom_id, citizen_username, citizen_airtable_id, storage_facility_id, path_to_storage, None, resource_defs, False, citizen_position_str_val, now_utc_dt, custom_notes=goto_notes, activity_type="goto_building_for_storage_fetch", details_payload=fetch_details, start_time_utc_iso=None)
                                        if first_fetch_activity_for_this_input: log.info(f"      [Travail Général - Arti] Activité 'goto_building_for_storage_fetch' créée vers {facility_name_log}.")
                
                # Prio 2: Fetch via recurrent contract
                if not first_fetch_activity_for_this_input:
                    log.info(f"    [Réappro. Arti Prio 2] Recherche de contrat 'recurrent' pour {res_name_display}.")
                    recurrent_contracts = get_citizen_contracts(tables, workplace_operator)
                    for contract_rec in recurrent_contracts:
                        if contract_rec['fields'].get('ResourceType') == input_res_id_to_fetch and contract_rec['fields'].get('BuyerBuilding') == workplace_custom_id:
                            from_bldg_id_rec = contract_rec['fields'].get('SellerBuilding')
                            if not from_bldg_id_rec: continue
                            from_bldg_rec_rec = get_building_record(tables, from_bldg_id_rec)
                            if not from_bldg_rec_rec: continue
                            amount_rec_contract = float(contract_rec['fields'].get('TargetAmount', 0) or 0)
                            amount_to_fetch_rec = min(amount_to_fetch_for_recipe, amount_rec_contract) # Use deficit
                            seller_rec = contract_rec['fields'].get('Seller')
                            if not seller_rec: continue
                            _, source_stock_rec_map = get_building_storage_details(tables, from_bldg_id_rec, seller_rec)
                            actual_stock_at_source_rec = source_stock_rec_map.get(input_res_id_to_fetch, 0.0)
                            if actual_stock_at_source_rec >= amount_to_fetch_rec and amount_to_fetch_rec > 0.01:
                                contract_custom_id_rec_str = contract_rec['fields'].get('ContractId', contract_rec['id'])
                                if _has_recent_failed_activity_for_contract(tables, 'fetch_resource', contract_custom_id_rec_str): continue
                                seller_bldg_pos_rec = _get_building_position_coords(from_bldg_rec_rec)
                                if citizen_position and seller_bldg_pos_rec:
                                    path_src_rec = get_path_between_points(citizen_position, seller_bldg_pos_rec, transport_api_url)
                                    if path_src_rec and path_src_rec.get('success'):
                                        first_fetch_activity_for_this_input = try_create_resource_fetching_activity(tables, citizen_airtable_id, citizen_custom_id, citizen_username, contract_custom_id_rec_str, from_bldg_id_rec, workplace_custom_id, input_res_id_to_fetch, amount_to_fetch_rec, path_src_rec, now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url, start_time_utc_iso=None)
                                        if first_fetch_activity_for_this_input: log.info(f"      [Travail Général - Arti] Activité 'fetch_resource' (recurrent) créée."); break 
                    if first_fetch_activity_for_this_input: break # Break from recurrent contracts loop

                # Prio 3: Buy from public sell contract
                if not first_fetch_activity_for_this_input:
                    log.info(f"    [Réappro. Arti Prio 3] Recherche de contrat 'public_sell' pour {res_name_display}.")
                    public_sell_formula = f"AND({{Type}}='public_sell', {{ResourceType}}='{_escape_airtable_value(input_res_id_to_fetch)}', {{EndAt}}>'{now_utc_dt.isoformat()}', {{TargetAmount}}>0)"
                    all_public_sell_for_res = tables['contracts'].all(formula=public_sell_formula, sort=['PricePerResource'])
                    for contract_ps in all_public_sell_for_res:
                        seller_bldg_id_ps = contract_ps['fields'].get('SellerBuilding')
                        if not seller_bldg_id_ps: continue
                        seller_bldg_rec_ps = get_building_record(tables, seller_bldg_id_ps)
                        if not seller_bldg_rec_ps: continue
                        price_ps = float(contract_ps['fields'].get('PricePerResource', 0))
                        available_ps = float(contract_ps['fields'].get('TargetAmount', 0))
                        seller_ps = contract_ps['fields'].get('Seller')
                        if not seller_ps: continue
                        buyer_rec_ps = get_citizen_record(tables, workplace_operator)
                        if not buyer_rec_ps: continue
                        ducats_ps = float(buyer_rec_ps['fields'].get('Ducats', 0))
                        max_affordable_ps = (ducats_ps / price_ps) if price_ps > 0 else float('inf')
                        amount_to_buy_ps = min(amount_to_fetch_for_recipe, available_ps, max_affordable_ps) # Use deficit
                        amount_to_buy_ps = float(f"{amount_to_buy_ps:.4f}")
                        if amount_to_buy_ps >= 0.0001:
                            _, source_stock_ps_map = get_building_storage_details(tables, seller_bldg_id_ps, seller_ps)
                            actual_stock_at_source = source_stock_ps_map.get(input_res_id_to_fetch, 0.0)
                            if actual_stock_at_source >= amount_to_buy_ps:
                                contract_custom_id_ps_str = contract_ps['fields'].get('ContractId', contract_ps['id'])
                                if _has_recent_failed_activity_for_contract(tables, 'fetch_resource', contract_custom_id_ps_str): continue
                                seller_bldg_pos_ps = _get_building_position_coords(seller_bldg_rec_ps)
                                if citizen_position and seller_bldg_pos_ps:
                                    path_seller_ps = get_path_between_points(citizen_position, seller_bldg_pos_ps, transport_api_url)
                                    if path_seller_ps and path_seller_ps.get('success'):
                                        first_fetch_activity_for_this_input = try_create_resource_fetching_activity(tables, citizen_airtable_id, citizen_custom_id, citizen_username, contract_custom_id_ps_str, seller_bldg_id_ps, workplace_custom_id, input_res_id_to_fetch, amount_to_buy_ps, path_seller_ps, now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url, start_time_utc_iso=None)
                                        if first_fetch_activity_for_this_input: log.info(f"      [Travail Général - Arti] Activité 'fetch_resource' (public_sell) créée."); break
                    if first_fetch_activity_for_this_input: break # Break from public_sell contracts loop
                
                # Prio 4: Generic fetch_resource (fallback)
                if not first_fetch_activity_for_this_input:
                    log.info(f"    [Réappro. Arti Prio 4] Tentative de récupération générique pour {res_name_display}.")
                    # Use amount_to_fetch_for_recipe (deficit)
                    fetch_amount_generic = min(amount_to_fetch_for_recipe, get_citizen_effective_carry_capacity(citizen_record) - get_citizen_current_load(tables, citizen_username))
                    if fetch_amount_generic >= 0.1:
                        first_fetch_activity_for_this_input = try_create_resource_fetching_activity(tables, citizen_airtable_id, citizen_custom_id, citizen_username, None, None, workplace_custom_id, input_res_id_to_fetch, fetch_amount_generic, None, now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url, start_time_utc_iso=None)
                        if first_fetch_activity_for_this_input: log.info(f"      [Travail Général - Arti] Activité 'fetch_resource' (générique) créée.")
                
                # If a fetch activity was created for this input, chain production and return
                if first_fetch_activity_for_this_input:
                    log.info(f"  [Travail Général - Arti] Une activité de récupération ({first_fetch_activity_for_this_input['fields'].get('Type')}, ID: {first_fetch_activity_for_this_input['fields'].get('ActivityId')}) a été créée pour {input_res_id_to_fetch}.")
                    next_start_time_iso = first_fetch_activity_for_this_input['fields']['EndDate']
                    chained_production = try_create_production_activity(
                        tables, citizen_airtable_id, citizen_custom_id, citizen_username,
                        workplace_custom_id, recipe_def_to_chain, now_utc_dt,
                        start_time_utc_iso=next_start_time_iso
                    )
                    if chained_production:
                        log.info(f"{LogColors.OKGREEN}[Travail Général] Production chaînée après récupération de {res_name_display}, début à {next_start_time_iso}.{LogColors.ENDC}")
                    else:
                        log.warning(f"{LogColors.WARNING}[Travail Général] Échec de la création de production chaînée après récupération de {res_name_display}.{LogColors.ENDC}")
                    return first_fetch_activity_for_this_input # Return the first activity of the chain

            # If loop completes, no fetch activity was created for any missing input.
            log.info(f"{LogColors.PROCESS}[Prod/Général - Arti Restock] {citizen_name}: Aucune activité de récupération n'a pu être créée pour les inputs manquants des recettes Arti.{LogColors.ENDC}")
            # Fall through to sellable items restocking or storage delivery

    # NOUVEAU BLOC : Si aucune activité liée aux Arti n'a été créée, essayer de réapprovisionner les articles listés dans 'sells'
    # This assumes the Arti block returns if it creates an activity.
    if sellable_items_defined: 
        log.info(f"{LogColors.PROCESS}[Prod/Général - Vente] {citizen_name}: Évaluation du réapprovisionnement des articles à vendre pour '{workplace_custom_id}'.{LogColors.ENDC}")
        current_workplace_stock_map_for_sells_restock = get_building_resources(tables, workplace_custom_id)
        
        missing_sellable_items = [] # Stores dicts: {"item_id", "desired_stock", "current_stock", "deficit"}

        for item_to_sell_id in sellable_items_defined:
            desired_stock_for_sale = float(building_type_def.get('targetSellStock', {}).get(item_to_sell_id, 10.0))
            current_stock_of_sellable = current_workplace_stock_map_for_sells_restock.get(item_to_sell_id, 0.0)

            if current_stock_of_sellable < desired_stock_for_sale:
                missing_sellable_items.append({
                    "item_id": item_to_sell_id,
                    "desired_stock": desired_stock_for_sale,
                    "current_stock": current_stock_of_sellable,
                    "deficit": desired_stock_for_sale - current_stock_of_sellable
                })
        
        if missing_sellable_items:
            # Prioritize: item with the lowest stock percentage relative to its desired stock
            missing_sellable_items.sort(key=lambda x: (x["current_stock"] / x["desired_stock"]) if x["desired_stock"] > 0 else float('inf'))

            log.info(f"{LogColors.PROCESS}[Prod/Général - Vente Restock] {citizen_name}: Articles à vendre manquants identifiés. Liste priorisée (premier = plus haute prio):")
            for i, item_info in enumerate(missing_sellable_items[:3]): # Log top 3
                 log.info(f"  {i+1}. Item: {item_info['item_id']}, Stock: {item_info['current_stock']:.2f}/{item_info['desired_stock']:.2f} (Déficit: {item_info['deficit']:.2f})")

            for item_to_restock_info in missing_sellable_items:
                item_to_sell_id_fetch = item_to_restock_info["item_id"]
                needed_amount_for_sale_fetch = item_to_restock_info["deficit"]
                res_name_display_sell = _get_res_display_name_module(item_to_sell_id_fetch, resource_defs)
                
                log.info(f"{LogColors.OKBLUE}  [Réappro. Vente Prioritaire] {workplace_custom_id} a besoin de {needed_amount_for_sale_fetch:.2f} de {res_name_display_sell} pour la vente.{LogColors.ENDC}")

                first_fetch_activity_for_this_sellable: Optional[Dict] = None

                # Prio 1: Fetch from dedicated storage contract (storage_query)
                log.info(f"    [Réappro. Vente - Prio 1] Recherche de contrat 'storage_query' pour {res_name_display_sell}.")
                storage_query_contracts_sell = tables['contracts'].all(
                    formula=f"AND({{Type}}='storage_query', {{Buyer}}='{_escape_airtable_value(workplace_operator)}', {{BuyerBuilding}}='{_escape_airtable_value(workplace_custom_id)}', {{ResourceType}}='{_escape_airtable_value(item_to_sell_id_fetch)}', {{Status}}='active', IS_BEFORE(NOW(), {{EndAt}}))"
                )
                if storage_query_contracts_sell:
                    sq_contract_sell = storage_query_contracts_sell[0]
                    storage_facility_id_sell = sq_contract_sell['fields'].get('SellerBuilding')
                    sq_contract_id_log_sell = sq_contract_sell['fields'].get('ContractId', sq_contract_sell['id'])
                    if storage_facility_id_sell:
                        storage_facility_record_sell = get_building_record(tables, storage_facility_id_sell)
                        if storage_facility_record_sell:
                            facility_name_log_sell = _get_bldg_display_name_module(tables, storage_facility_record_sell)
                            _, facility_stock_map_sell = get_building_storage_details(tables, storage_facility_id_sell, workplace_operator)
                            actual_stored_amount_sell = float(facility_stock_map_sell.get(item_to_sell_id_fetch, 0.0))
                            amount_to_fetch_sell = min(needed_amount_for_sale_fetch, actual_stored_amount_sell)
                            amount_to_fetch_sell = float(f"{amount_to_fetch_sell:.4f}")
                            if amount_to_fetch_sell >= 0.1:
                                storage_facility_pos_sell = _get_building_position_coords(storage_facility_record_sell)
                                if citizen_position and storage_facility_pos_sell:
                                    path_to_storage_sell = get_path_between_points(citizen_position, storage_facility_pos_sell, transport_api_url)
                                    if path_to_storage_sell and path_to_storage_sell.get('success'):
                                        goto_notes_sell = f"Aller à {facility_name_log_sell} pour chercher {amount_to_fetch_sell:.2f} {res_name_display_sell} pour {workplace_custom_id} (vente)."
                                        fetch_details_sell = { "action_on_arrival": "fetch_from_storage", "original_workplace_id": workplace_custom_id, "storage_query_contract_id": sq_contract_id_log_sell, "resources_to_fetch": [{"ResourceId": item_to_sell_id_fetch, "Amount": amount_to_fetch_sell}] }
                                        first_fetch_activity_for_this_sellable = try_create_goto_work_activity( tables, citizen_custom_id, citizen_username, citizen_airtable_id, storage_facility_id_sell, path_to_storage_sell, None, resource_defs, False, citizen_position_str_val, now_utc_dt, custom_notes=goto_notes_sell, activity_type="goto_building_for_storage_fetch", details_payload=fetch_details_sell, start_time_utc_iso=None )
                                        if first_fetch_activity_for_this_sellable: log.info(f"      [Réappro. Vente] Activité 'goto_building_for_storage_fetch' créée vers {facility_name_log_sell}.")
                
                # Prio 2: Fetch via recurrent contract
                if not first_fetch_activity_for_this_sellable:
                    log.info(f"    [Réappro. Vente - Prio 2] Recherche de contrat 'recurrent' pour {res_name_display_sell}...")
                    recurrent_contracts_sell = get_citizen_contracts(tables, workplace_operator)
                    for contract_rec_sell in recurrent_contracts_sell:
                        if contract_rec_sell['fields'].get('ResourceType') == item_to_sell_id_fetch and contract_rec_sell['fields'].get('BuyerBuilding') == workplace_custom_id:
                            from_bldg_id_rec_sell = contract_rec_sell['fields'].get('SellerBuilding')
                            if not from_bldg_id_rec_sell: continue
                            from_bldg_rec_rec_sell = get_building_record(tables, from_bldg_id_rec_sell)
                            if not from_bldg_rec_rec_sell: continue
                            amount_rec_contract_sell = float(contract_rec_sell['fields'].get('TargetAmount', 0) or 0)
                            amount_to_fetch_rec_sell = min(needed_amount_for_sale_fetch, amount_rec_contract_sell)
                            seller_rec_sell = contract_rec_sell['fields'].get('Seller')
                            if not seller_rec_sell: continue
                            _, source_stock_rec_map_sell = get_building_storage_details(tables, from_bldg_id_rec_sell, seller_rec_sell)
                            actual_stock_at_source_rec_sell = source_stock_rec_map_sell.get(item_to_sell_id_fetch, 0.0)
                            if actual_stock_at_source_rec_sell >= amount_to_fetch_rec_sell and amount_to_fetch_rec_sell > 0.01:
                                contract_custom_id_rec_str_sell = contract_rec_sell['fields'].get('ContractId', contract_rec_sell['id'])
                                if _has_recent_failed_activity_for_contract(tables, 'fetch_resource', contract_custom_id_rec_str_sell): continue
                                path_src_rec_sell = get_path_between_points(citizen_position, _get_building_position_coords(from_bldg_rec_rec_sell), transport_api_url)
                                if path_src_rec_sell and path_src_rec_sell.get('success'):
                                    first_fetch_activity_for_this_sellable = try_create_resource_fetching_activity( tables, citizen_airtable_id, citizen_custom_id, citizen_username, contract_custom_id_rec_str_sell, from_bldg_id_rec_sell, workplace_custom_id, item_to_sell_id_fetch, amount_to_fetch_rec_sell, path_src_rec_sell, now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url, start_time_utc_iso=None )
                                    if first_fetch_activity_for_this_sellable: log.info(f"      [Réappro. Vente] Activité 'fetch_resource' (recurrent) créée."); break
                    if first_fetch_activity_for_this_sellable: break

                # Prio 3: Buy from public sell contract (via building's own markup_buy contract)
                if not first_fetch_activity_for_this_sellable:
                    log.info(f"    [Réappro. Vente - Prio 3] Recherche de contrat 'markup_buy' de {workplace_custom_id} pour {res_name_display_sell}...")
                    markup_buy_formula_sell = f"AND({{Type}}='markup_buy', {{BuyerBuilding}}='{_escape_airtable_value(workplace_custom_id)}', {{ResourceType}}='{_escape_airtable_value(item_to_sell_id_fetch)}', {{EndAt}}>'{now_utc_dt.isoformat()}', {{TargetAmount}}>0, {{Status}}='active')"
                    all_markup_buy_for_sell_item = tables['contracts'].all(formula=markup_buy_formula_sell, sort=['PricePerResource'])
                    for contract_mb_sell in all_markup_buy_for_sell_item:
                        seller_bldg_id_mb_sell = contract_mb_sell['fields'].get('SellerBuilding')
                        seller_username_mb_sell = contract_mb_sell['fields'].get('Seller')
                        if seller_bldg_id_mb_sell and seller_username_mb_sell: 
                            seller_bldg_rec_mb_sell = get_building_record(tables, seller_bldg_id_mb_sell)
                            if seller_bldg_rec_mb_sell:
                                _, source_stock_mb_sell_map = get_building_storage_details(tables, seller_bldg_id_mb_sell, seller_username_mb_sell)
                                actual_stock_at_source_mb_sell = source_stock_mb_sell_map.get(item_to_sell_id_fetch, 0.0)
                                if actual_stock_at_source_mb_sell >= needed_amount_for_sale_fetch:
                                    contract_custom_id_mb_sell_str = contract_mb_sell['fields'].get('ContractId', contract_mb_sell['id'])
                                    if _has_recent_failed_activity_for_contract(tables, 'fetch_resource', contract_custom_id_mb_sell_str): continue
                                    path_seller_mb_sell = get_path_between_points(citizen_position, _get_building_position_coords(seller_bldg_rec_mb_sell), transport_api_url)
                                    if path_seller_mb_sell and path_seller_mb_sell.get('success'):
                                        first_fetch_activity_for_this_sellable = try_create_resource_fetching_activity( tables, citizen_airtable_id, citizen_custom_id, citizen_username, contract_custom_id_mb_sell_str, seller_bldg_id_mb_sell, workplace_custom_id, item_to_sell_id_fetch, needed_amount_for_sale_fetch, path_seller_mb_sell, now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url, start_time_utc_iso=None )
                                        if first_fetch_activity_for_this_sellable: log.info(f"      [Réappro. Vente] Activité 'fetch_resource' (markup_buy spécifique) créée."); break
                        else: # Public markup_buy by the stall
                            contract_custom_id_mb_sell_str = contract_mb_sell['fields'].get('ContractId', contract_mb_sell['id'])
                            if _has_recent_failed_activity_for_contract(tables, 'fetch_resource', contract_custom_id_mb_sell_str): continue
                            first_fetch_activity_for_this_sellable = try_create_resource_fetching_activity( tables, citizen_airtable_id, citizen_custom_id, citizen_username, contract_custom_id_mb_sell_str, None, workplace_custom_id, item_to_sell_id_fetch, needed_amount_for_sale_fetch, None, now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url, start_time_utc_iso=None )
                            if first_fetch_activity_for_this_sellable: log.info(f"      [Réappro. Vente] Activité 'fetch_resource' (markup_buy public) créée."); break
                    if first_fetch_activity_for_this_sellable: break

                # Prio 4: Generic fetch_resource (fallback)
                if not first_fetch_activity_for_this_sellable:
                    log.info(f"    [Réappro. Vente - Prio 4] Tentative de récupération générique pour {res_name_display_sell}...")
                    fetch_amount_generic_sell = min(needed_amount_for_sale_fetch, get_citizen_effective_carry_capacity(citizen_record) - get_citizen_current_load(tables, citizen_username))
                    if fetch_amount_generic_sell >= 0.1:
                        first_fetch_activity_for_this_sellable = try_create_resource_fetching_activity(
                            tables, citizen_airtable_id, citizen_custom_id, citizen_username, None, None, workplace_custom_id,
                            item_to_sell_id_fetch, fetch_amount_generic_sell,
                            None, now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url, start_time_utc_iso=None
                        )
                        if first_fetch_activity_for_this_sellable: log.info(f"      [Réappro. Vente] Activité 'fetch_resource' (générique) créée.")
                
                if first_fetch_activity_for_this_sellable:
                    log.info(f"  [Travail Général - Vente] Une activité de récupération ({first_fetch_activity_for_this_sellable['fields'].get('Type')}, ID: {first_fetch_activity_for_this_sellable['fields'].get('ActivityId')}) a été créée pour réapprovisionner {item_to_sell_id_fetch}.")
                    return first_fetch_activity_for_this_sellable # Return the created activity

            log.info(f"{LogColors.PROCESS}[Prod/Général - Vente Restock] {citizen_name}: Aucune activité de récupération n'a pu être créée pour les articles à vendre manquants.{LogColors.ENDC}")

    # 3. Try to deliver excess output to storage (This logic remains unchanged and is fine here)
    current_workplace_total_load, current_workplace_stock_map_for_delivery = get_building_storage_details(tables, workplace_custom_id, workplace_operator)
    if storage_capacity > 0 and (current_workplace_total_load / storage_capacity) > STORAGE_FULL_THRESHOLD:
        log.info(f"{LogColors.OKCYAN}[Travail Général] {workplace_custom_id} est >{STORAGE_FULL_THRESHOLD*100:.0f}% plein. Vérification des contrats de stockage.{LogColors.ENDC}")
        for res_id_to_deliver, amount_at_workplace in current_workplace_stock_map_for_delivery.items():
            if amount_at_workplace <= 0.1: continue
            storage_query_contracts = tables['contracts'].all(
                formula=f"AND({{Type}}='storage_query', {{Buyer}}='{_escape_airtable_value(workplace_operator)}', {{BuyerBuilding}}='{_escape_airtable_value(workplace_custom_id)}', {{ResourceType}}='{_escape_airtable_value(res_id_to_deliver)}', {{Status}}='active', IS_BEFORE(NOW(), {{EndAt}}))"
            )
            if storage_query_contracts:
                sq_contract = storage_query_contracts[0]
                storage_facility_id = sq_contract['fields'].get('SellerBuilding')
                if storage_facility_id:
                    storage_facility_record = get_building_record(tables, storage_facility_id)
                    if storage_facility_record:
                        _, facility_stock_map = get_building_storage_details(tables, storage_facility_id, workplace_operator)
                        current_stored_in_facility = facility_stock_map.get(res_id_to_deliver, 0.0)
                        contracted_capacity = float(sq_contract['fields'].get('TargetAmount', 0))
                        remaining_facility_capacity_for_contract = contracted_capacity - current_stored_in_facility
                        if remaining_facility_capacity_for_contract > 0.1:
                            amount_to_deliver = min(amount_at_workplace * 0.5, 
                                                    get_citizen_effective_carry_capacity(citizen_record) - get_citizen_current_load(tables, citizen_username),
                                                    remaining_facility_capacity_for_contract)
                            amount_to_deliver = float(f"{amount_to_deliver:.4f}")
                            if amount_to_deliver >= 0.1:
                                storage_facility_pos = _get_building_position_coords(storage_facility_record)
                                if citizen_position and storage_facility_pos:
                                    path_to_storage = get_path_between_points(citizen_position, storage_facility_pos, transport_api_url)
                                    if path_to_storage and path_to_storage.get('success'):
                                        deliver_activity = try_create_deliver_to_storage_activity(
                                            tables, citizen_record, workplace_record, storage_facility_record,
                                            [{"ResourceId": res_id_to_deliver, "Amount": amount_to_deliver}],
                                            sq_contract['fields'].get('ContractId', sq_contract['id']),
                                            path_to_storage, now_utc_dt, start_time_utc_iso=None # Immediate start for delivery
                                        )
                                        if deliver_activity:
                                            log.info(f"{LogColors.OKGREEN}[Travail Général] Citoyen {citizen_name} va livrer {amount_to_deliver:.2f} de {res_id_to_deliver} à l'entrepôt {storage_facility_id}.{LogColors.ENDC}")
                                            return deliver_activity # Return the delivery activity
    return None # No activity created by this handler this cycle


def _handle_forestieri_daytime_tasks(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str # Added social_class
) -> bool:
    """Prio 40: Handles Forestieri specific activities (work/leisure) based on their schedule."""
    if citizen_social_class != "Forestieri":
        return False
    
    workplace_record_forestieri = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    workplace_type_str_forestieri = workplace_record_forestieri['fields'].get('Type') if workplace_record_forestieri else None
    workplace_def_forestieri = building_type_defs.get(workplace_type_str_forestieri) if workplace_type_str_forestieri else None

    if is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=workplace_def_forestieri):
        # Forestieri "work" could be specific tasks or managing their affairs.
        # For now, let's assume if they have a workplace, they go there.
        # Otherwise, they might engage in trade-related leisure or specific Forestieri tasks.
        # This part can be expanded with specific Forestieri work logic.
        # If they have a workplace record (e.g. a rented stall or office):
        workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
        if workplace_record:
            if not citizen_position: return False
            workplace_pos = _get_building_position_coords(workplace_record)
            if not workplace_pos: return False
            if _calculate_distance_meters(citizen_position, workplace_pos) > 20: # Not at workplace
                 # Create goto_work for Forestieri to their specific workplace
                path_to_work = get_path_between_points(citizen_position, workplace_pos, transport_api_url)
                if path_to_work and path_to_work.get('success'):
                    workplace_custom_id_val = workplace_record['fields'].get('BuildingId')
                    if try_create_goto_work_activity(tables, citizen_custom_id, citizen_username, citizen_airtable_id, workplace_custom_id_val, path_to_work, None, resource_defs, False, citizen_position_str, now_utc_dt):
                        log.info(f"{LogColors.OKGREEN}[Forestieri Travail] Forestiero {citizen_name} va à son lieu de travail {workplace_custom_id_val}.{LogColors.ENDC}")
                        return True
            else: # At workplace
                # Placeholder for Forestieri-specific work/production at their workplace
                log.info(f"{LogColors.OKBLUE}[Forestieri Travail] Forestiero {citizen_name} est à son lieu de travail. Logique de travail spécifique à implémenter.{LogColors.ENDC}")
                # Could try production if applicable, or a specific "manage_trade" activity.
                # For now, if at workplace during work time, let it fall through to idle if no specific task.
                pass # Fall through to allow other non-work leisure if no specific work task here
        # If no workplace, they engage in leisure during their "work" hours.
        # Fall through to general leisure logic.

    if is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        log.info(f"{LogColors.OKCYAN}[Forestieri Loisirs] Forestiero {citizen_name}: Période de loisirs. Évaluation des tâches.{LogColors.ENDC}")
        if process_forestieri_daytime_activity( # This function handles general Forestieri leisure
            tables, citizen_record, citizen_position, now_utc_dt, resource_defs, building_type_defs, transport_api_url, IDLE_ACTIVITY_DURATION_HOURS
        ):
            return True
    return False


def _handle_shopping_tasks(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str_val: Optional[str],
    citizen_social_class: str # Added social_class
) -> Optional[Dict]:
    """Prio 50: Handles personal shopping tasks if it's leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    # Nobili have a lot of leisure time, shopping is a key activity for them.
    # Other classes also shop during their leisure.

    current_load = get_citizen_current_load(tables, citizen_username)
    max_capacity = get_citizen_effective_carry_capacity(citizen_record)
    if current_load >= max_capacity * 0.9:
        return None 
    
    home_record = get_citizen_home(tables, citizen_username)
    # Forestieri might shop even without a permanent "home" record in Venice, goods go to inventory.
    # Homeless citizens can also shop, goods go to their inventory.
    # if not home_record and citizen_social_class != "Forestieri":
    #      log.info(f"{LogColors.OKBLUE}[Shopping] Citoyen {citizen_name} ({citizen_social_class}): Pas de domicile, ne peut pas faire d'achats (sauf Forestieri).{LogColors.ENDC}")
    #      return False

    log.info(f"{LogColors.OKCYAN}[Achat Nourriture] Citoyen {citizen_name}: Affamé et a des Ducats. Recherche de magasins d'alimentation. Domicile: {'Oui' if home_record else 'Non'}.{LogColors.ENDC}")
    
    # citizen_social_class is now a parameter
    citizen_max_tier_access = SOCIAL_CLASS_VALUE.get(citizen_social_class, 1)
    citizen_ducats = float(citizen_record['fields'].get('Ducats', 0))
    remaining_capacity = max_capacity - current_load

    # Simplified: find any public_sell contract for a resource the citizen can afford and carry, within their tier.
    shoppable_resources_ids = [res_id for res_id, res_data in resource_defs.items() 
                               if int(res_data.get('tier', 0) or 0) <= citizen_max_tier_access and int(res_data.get('tier', 0) or 0) > 0]
    if not shoppable_resources_ids: return False

    # Randomly pick a resource type to shop for to add variety
    random.shuffle(shoppable_resources_ids)

    for res_id_to_buy in shoppable_resources_ids:
        active_sell_contracts_formula = f"AND({{Type}}='public_sell', {{ResourceType}}='{_escape_airtable_value(res_id_to_buy)}', {{EndAt}}>'{now_utc_dt.isoformat()}', {{TargetAmount}}>0)"
        try:
            sell_contracts = tables['contracts'].all(formula=active_sell_contracts_formula, sort=[('PricePerResource', 'asc')]) # Cheaper first
            if not sell_contracts: continue

            for contract_rec in sell_contracts:
                seller_building_id = contract_rec['fields'].get('SellerBuilding')
                if not seller_building_id: continue
                
                seller_building_rec = get_building_record(tables, seller_building_id)
                if not seller_building_rec: continue

                price_per_unit = float(contract_rec['fields'].get('PricePerResource', 0))
                contract_amount_available = float(contract_rec['fields'].get('TargetAmount', 0))
                if price_per_unit <= 0: continue

                max_affordable = citizen_ducats / price_per_unit
                amount_to_buy = min(remaining_capacity, contract_amount_available, max_affordable, 5.0) # Buy up to 5 units
                amount_to_buy = float(f"{amount_to_buy:.4f}")

                if amount_to_buy >= 0.1:
                    if not citizen_position: continue # Need citizen position for path
                    seller_pos = _get_building_position_coords(seller_building_rec)
                    if not seller_pos: continue

                    path_to_seller = get_path_between_points(citizen_position, seller_pos, transport_api_url)
                    if path_to_seller and path_to_seller.get('success'):
                        home_custom_id_for_delivery = home_record['fields'].get('BuildingId')
                        contract_custom_id_for_sell = contract_rec['fields'].get('ContractId', contract_rec['id'])
                        # If homeless, home_custom_id_for_delivery will be None.
                        # The fetch_resource activity will handle this by putting items in inventory,
                        # and the processor will correctly assign ownership to the citizen.
                        created_activity = try_create_resource_fetching_activity(
                            tables, citizen_airtable_id, citizen_custom_id, citizen_username,
                            contract_custom_id_for_sell, seller_building_id, 
                            home_custom_id_for_delivery, # This can be None for homeless
                            res_id_to_buy, amount_to_buy, 
                            path_to_seller, # path_data_to_source
                            now_utc_dt, resource_defs,
                            building_type_defs, now_venice_dt, transport_api_url, api_base_url
                        )
                        if created_activity:
                            log.info(f"{LogColors.OKGREEN}[Shopping] Citoyen {citizen_name}: Activité d'achat créée pour {res_id_to_buy}. Destination: {home_custom_id_for_delivery or 'Inventaire'}.{LogColors.ENDC}")
                            return created_activity # Return the activity record
            # If no suitable contract found for this resource_type, loop to next resource_type
        except Exception as e_shop:
            log.error(f"Erreur pendant le shopping pour {res_id_to_buy}: {e_shop}")
            continue # Try next resource
    return None


def _handle_porter_tasks(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str # Added social_class
) -> bool:
    """Prio 60: Handles Porter tasks if it's work time and they are at Guild Hall."""
    # Porters work at a 'porter_guild_hall'. Check work time for this specific building type.
    # We need to know if the citizen *is* a porter at a guild hall first.
    # This handler is called if the citizen is at their guild_hall.
    # So, we can assume workplace_type is 'porter_guild_hall' if this handler is reached appropriately.
    # The check for being at the guild hall is done before calling process_porter_activity.
    # For the time check here, we need the workplace_type if they have one.
    
    workplace_record_porter = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    workplace_type_str_porter = None
    workplace_def_porter = None
    is_porter_at_guild_hall = False

    if workplace_record_porter and workplace_record_porter['fields'].get('Type') == 'porter_guild_hall':
        workplace_type_str_porter = 'porter_guild_hall'
        workplace_def_porter = building_type_defs.get(workplace_type_str_porter)
        # Check if citizen is physically at the guild hall
        guild_hall_pos = _get_building_position_coords(workplace_record_porter)
        if citizen_position and guild_hall_pos and _calculate_distance_meters(citizen_position, guild_hall_pos) < 20:
            is_porter_at_guild_hall = True

    if not is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=workplace_def_porter):
        return False
    
    if not is_porter_at_guild_hall: # If not at guild hall, this handler shouldn't proceed.
        return False

    # The original logic for getting porter_guild_hall_operated can remain,
    # as process_porter_activity uses it.
    porter_guild_hall_operated = workplace_record_porter # Since we've established they work at one.
    try:
        # Assuming RunBy is the correct field for operator
        buildings_run_by_citizen = tables['buildings'].all(formula=f"AND({{RunBy}}='{_escape_airtable_value(citizen_username)}', {{Type}}='porter_guild_hall')")
        if buildings_run_by_citizen:
            porter_guild_hall_operated = buildings_run_by_citizen[0]
    except Exception as e_fetch_porter_hall:
        log.error(f"Erreur vérification si {citizen_username} opère un Porter Guild Hall: {e_fetch_porter_hall}")
        return False
        
    if not porter_guild_hall_operated: return False # Not a porter or doesn't operate a guild hall

    guild_hall_pos = _get_building_position_coords(porter_guild_hall_operated)
    if not citizen_position or not guild_hall_pos or _calculate_distance_meters(citizen_position, guild_hall_pos) > 20:
        return False # Not at their guild hall

    log.info(f"{LogColors.OKCYAN}[Porteur] Citoyen {citizen_name} est à son Porter Guild Hall. Délégation à process_porter_activity.{LogColors.ENDC}")
    # process_porter_activity needs now_venice_dt
    if process_porter_activity(
        tables, citizen_record, porter_guild_hall_operated, resource_defs, building_type_defs,
        now_venice_dt, transport_api_url, api_base_url
    ):
        return True # Activity created by porter logic
    return False

def _handle_professional_construction_work( # Renamed from _handle_construction_tasks
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]: # Changed return type to Optional[Dict] to match other handlers
    """Prio 30: Handles construction related tasks if it's work time and citizen is a professional builder."""
    workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    if not workplace_record:
        return None # No workplace

    workplace_type_str = workplace_record['fields'].get('Type')
    workplace_def = building_type_defs.get(workplace_type_str) if workplace_type_str else None
    # Check if it's a construction workshop
    if workplace_type_str not in ["masons_lodge", "master_builders_workshop"]:
        return None # Not a construction workshop

    if not is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=workplace_def):
        return None # Not work time

    workplace_pos = _get_building_position_coords(workplace_record)
    if not citizen_position or not workplace_pos or _calculate_distance_meters(citizen_position, workplace_pos) > 20:
        log.info(f"{LogColors.OKBLUE}[Construction Pro] Citoyen {citizen_name} ({citizen_social_class}) n'est pas à son atelier {workplace_type_str}. Pas de tâche de construction pro.{LogColors.ENDC}")
        return None # Not at workplace
    
    log.info(f"{LogColors.OKCYAN}[Construction Pro] Citoyen {citizen_name} ({citizen_social_class}) est à son atelier {workplace_type_str}. Délégation à handle_construction_worker_activity.{LogColors.ENDC}")
    
    # handle_construction_worker_activity returns a boolean. We need to adapt if we want to return the activity record.
    # For now, let's assume if it returns True, an activity was created, but we don't have the record itself here.
    # This is a slight deviation from other handlers that return the record.
    # To fix this, handle_construction_worker_activity would need to be refactored to return the activity record.
    # For now, we'll return a placeholder dict if True, or None if False.
    if handle_construction_worker_activity(
        tables, citizen_record, workplace_record,
        building_type_defs, resource_defs, 
        now_venice_dt, now_utc_dt, 
        transport_api_url, api_base_url
    ):
        log.info(f"{LogColors.OKGREEN}[Construction Pro] Citoyen {citizen_name}: Tâche de construction professionnelle créée/gérée.{LogColors.ENDC}")
        # We don't have the actual activity record here, so we can't return it directly.
        # This is a limitation of the current handle_construction_worker_activity signature.
        # Returning a dummy dict to signify success for now.
        return {"id": "placeholder_professional_construction_activity", "fields": {"Type": "professional_construction_task_managed"}}
    return None


def _handle_occupant_self_construction(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str_val: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 32: Handles occupant self-construction if they are AI, at an unconstructed site they occupy, and materials are present."""
    if not citizen_record['fields'].get('IsAI'): # Only AI occupants for now
        return None

    # Find if the citizen is an occupant of any unconstructed building
    # This requires fetching buildings where Occupant is citizen_username and ConstructionMinutesRemaining > 0
    try:
        occupied_unconstructed_sites_formula = f"AND({{Occupant}}='{_escape_airtable_value(citizen_username)}', {{ConstructionMinutesRemaining}} > 0)"
        occupied_sites = tables['buildings'].all(formula=occupied_unconstructed_sites_formula, max_records=1)
        if not occupied_sites:
            return None # Not an occupant of an unconstructed site
        
        site_record = occupied_sites[0]
        site_id = site_record['fields'].get('BuildingId', site_record['id'])
        site_type_str = site_record['fields'].get('Type')

        log.info(f"{LogColors.OKCYAN}[Auto-Construction] {citizen_name} est occupant du site {site_id} (Type: {site_type_str}). Évaluation.{LogColors.ENDC}")

        # Check if occupant already has a relevant construction/goto activity for this site
        existing_activity_formula = f"AND({{Citizen}}='{_escape_airtable_value(citizen_username)}', {{ToBuilding}}='{_escape_airtable_value(site_id)}', OR({{Type}}='construct_building', {{Type}}='goto_construction_site', {{Type}}='goto_location'), NOT(OR({{Status}}='processed', {{Status}}='failed', {{Status}}='error')))"
        if tables['activities'].all(formula=existing_activity_formula, max_records=1):
            log.info(f"  {citizen_name} a déjà une activité de construction/déplacement pour {site_id}. Saut.")
            return None # Already has a task

        site_building_def = building_type_defs.get(site_type_str)
        if not site_building_def:
            log.error(f"  Définition de bâtiment non trouvée pour {site_type_str} (site {site_id}). Saut.")
            return None

        construction_costs_from_def = site_building_def.get('constructionCosts', {})
        required_materials_for_site = {k: v for k, v in construction_costs_from_def.items() if k != 'ducats'}
        
        site_owner_username = site_record['fields'].get('Owner')
        if not site_owner_username:
            log.warning(f"  Site {site_id} n'a pas de propriétaire. Impossible de déterminer la propriété des matériaux. Saut.")
            return None
            
        _, site_inventory_map = get_building_storage_details(tables, site_id, site_owner_username)
        
        all_materials_on_site = True
        if not required_materials_for_site:
            log.info(f"  Site {site_id}: Aucun matériau listé. Supposons que tout est sur site.")
        else:
            for material, needed_qty_from_def in required_materials_for_site.items():
                needed_qty = float(needed_qty_from_def)
                on_site_qty = float(site_inventory_map.get(material, 0.0))
                if on_site_qty < needed_qty:
                    all_materials_on_site = False
                    log.info(f"  Site {site_id} manque de {material} (Besoin: {needed_qty}, A: {on_site_qty}).")
                    break
        
        if all_materials_on_site:
            log.info(f"  Tous matériaux présents sur {site_id} pour {citizen_name}.")
            construction_minutes_remaining_site = float(site_record['fields'].get('ConstructionMinutesRemaining', 0))
            if construction_minutes_remaining_site > 0:
                if not citizen_position: # Should have been handled by caller, but double check
                    log.warning(f"  {citizen_name} n'a pas de position. Saut.")
                    return None

                site_position = _get_building_position_coords(site_record)
                if not site_position:
                    log.warning(f"  Site {site_id} n'a pas de position. Saut.")
                    return None

                path_to_site_for_occupant = None
                if _calculate_distance_meters(citizen_position, site_position) > 20:
                    log.info(f"  {citizen_name} n'est pas sur le site {site_id}. Recherche de chemin...")
                    path_to_site_for_occupant = get_path_between_points(citizen_position, site_position, transport_api_url)
                    if not (path_to_site_for_occupant and path_to_site_for_occupant.get('success')):
                        log.warning(f"  Recherche de chemin vers {site_id} échouée pour {citizen_name}. Saut.")
                        return None
                
                work_duration_occupant = 60 
                # try_create_construct_building_activity returns the activity record or None
                created_activity = try_create_construct_building_activity(
                    tables, citizen_record, site_record,
                    work_duration_occupant, contract_id=None, # No formal contract for self-construction
                    path_data=path_to_site_for_occupant,
                    current_time_utc=now_utc_dt
                )
                if created_activity:
                    log.info(f"{LogColors.OKGREEN}  Activité 'construct_building' créée pour {citizen_name} sur {site_id}.{LogColors.ENDC}")
                return created_activity # Return record or None
            else:
                log.info(f"  Site {site_id} déjà construit. {citizen_name} ne construira pas.")
        else:
            log.info(f"  Site {site_id} n'a pas tous les matériaux pour que {citizen_name} construise.")
            # Future: Could create a "fetch_missing_materials_for_own_site" activity here.
            
    except Exception as e_occ_constr:
        log.error(f"{LogColors.FAIL}Erreur dans _handle_occupant_self_construction pour {citizen_name}: {e_occ_constr}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
    return None


def _handle_deposit_full_inventory(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Prio 10: Handles depositing inventory if it's full.
    This orchestrator will create a chain of activities to deposit items at appropriate locations.
    """
    current_load = get_citizen_current_load(tables, citizen_username)
    citizen_max_capacity = get_citizen_effective_carry_capacity(citizen_record)

    # Trigger if inventory is, for example, > 70% full
    # Or if specific items should always be deposited (e.g., finished goods after production)
    # For now, a simple capacity check.
    if current_load <= (citizen_max_capacity * 0.7):
        return None # Inventory not full enough

    if not citizen_position: # Orchestrator needs current position
        log.warning(f"{LogColors.WARNING}[Dépôt Inventaire Complet] {citizen_name} n'a pas de position. Impossible de planifier le dépôt.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.OKCYAN}[Dépôt Inventaire Complet] {citizen_name} ({citizen_social_class}): Inventaire >70% plein. Tentative d'orchestration du dépôt.{LogColors.ENDC}")

    # Call the orchestrator creator
    # It needs: tables, citizen_record, citizen_position, resource_defs, building_type_defs, now_utc_dt, transport_api_url, api_base_url
    # start_time_utc_iso can be None for immediate start of the chain.
    first_activity_in_chain = try_create_deposit_inventory_orchestrator(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=citizen_position,
        resource_defs=resource_defs,
        building_type_defs=building_type_defs,
        now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url,
        api_base_url=api_base_url,
        start_time_utc_iso=None 
    )

    if first_activity_in_chain:
        log.info(f"{LogColors.OKGREEN}[Dépôt Inventaire Complet] {citizen_name}: Chaîne d'activités de dépôt créée. Première activité: {first_activity_in_chain['fields'].get('Type', 'N/A')}.{LogColors.ENDC}")
    else:
        log.info(f"{LogColors.OKBLUE}[Dépôt Inventaire Complet] {citizen_name}: Aucune chaîne d'activités de dépôt n'a pu être créée (ex: inventaire vide après tout, pas de lieux valides).{LogColors.ENDC}")
        
    return first_activity_in_chain


def _handle_read_book(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str,
    check_only: bool = False
) -> Union[Optional[Dict], bool]:
    """Prio 55: Handles reading a book if citizen owns one and it's leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return False if check_only else None

    # Check for book ownership
    owned_books_formula = f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='books', {{Count}} >= 1)"
    try:
        owned_books = tables['resources'].all(formula=owned_books_formula, max_records=1) # Just need to know if any exist
        if not owned_books:
            return False if check_only else None
    except Exception as e_fetch_books_check:
        log.error(f"{LogColors.FAIL}[Lire Livre - Check] Erreur lors de la vérification des livres pour {citizen_name}: {e_fetch_books_check}{LogColors.ENDC}")
        return False if check_only else None
        
    if check_only:
        # If we reach here, they own a book and it's leisure time.
        # The actual location check (inventory vs. home vs. other building) is complex
        # and handled by try_create_read_book_activity. For check_only, we assume
        # if they own a book, they can find a way to read it (e.g., it's in inventory or home).
        # A more precise check_only would need to replicate parts of try_create_read_book_activity's location logic.
        return True

    log.info(f"{LogColors.OKCYAN}[Lire Livre] {citizen_name} ({citizen_social_class}) en période de loisirs. Recherche d'un livre à lire.{LogColors.ENDC}")

    # Find any book owned by the citizen (either in inventory or in a building they own/operate)
    # For simplicity, let's first check inventory, then home.
    # A more complex version could check any building they own/operate.

    owned_books_formula = f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='books', {{Count}} >= 1)"
    try:
        owned_books = tables['resources'].all(formula=owned_books_formula)
        if not owned_books:
            log.info(f"{LogColors.OKBLUE}[Lire Livre] {citizen_name} ne possède aucun livre.{LogColors.ENDC}")
            return None
        
        # Select a book at random from the ones they own
        # To make it more interesting, we could prioritize unread books if we tracked that.
        # For now, any owned book.
        book_to_read_record = random.choice(owned_books)
        
        book_title_for_log = book_to_read_record['fields'].get('Name', 'un livre')
        book_asset_type = book_to_read_record['fields'].get('AssetType')
        book_asset_id = book_to_read_record['fields'].get('Asset')
        log.info(f"{LogColors.OKBLUE}[Lire Livre] {citizen_name} a choisi de lire '{book_title_for_log}' (Asset: {book_asset_type} {book_asset_id}).{LogColors.ENDC}")

        # The try_create_read_book_activity will handle pathing if needed
        activity_record = try_create_read_book_activity(
            tables=tables,
            citizen_record=citizen_record,
            citizen_position=citizen_position,
            book_resource_record=book_to_read_record,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            start_time_utc_iso=None # Immediate start
        )

        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Lire Livre] {citizen_name}: Activité 'read_book' (ou chaîne goto_location->read_book) créée.{LogColors.ENDC}")
        else:
            log.info(f"{LogColors.OKBLUE}[Lire Livre] {citizen_name}: Impossible de créer une activité 'read_book'.{LogColors.ENDC}")
            
        return activity_record

    except Exception as e_fetch_books:
        log.error(f"{LogColors.FAIL}[Lire Livre] Erreur lors de la recherche de livres pour {citizen_name}: {e_fetch_books}{LogColors.ENDC}")
        return None

def _handle_manage_public_dock(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str,
    check_only: bool = False
) -> Union[Optional[Dict], bool]:
    """Prio 66: Handles managing a public dock if the citizen runs one and it needs attention."""
    if not (is_work_time(citizen_social_class, now_venice_dt) or is_leisure_time_for_class(citizen_social_class, now_venice_dt)):
        return False if check_only else None

    try:
        docks_run_by_citizen = tables['buildings'].all(
            formula=f"AND({{RunBy}}='{_escape_airtable_value(citizen_username)}', {{Type}}='public_dock')"
        )
    except Exception as e_fetch_docks:
        log.error(f"{LogColors.FAIL}[Gestion Quai Public] Erreur récupération des quais pour {citizen_name}: {e_fetch_docks}{LogColors.ENDC}")
        return None

    if not docks_run_by_citizen:
        return False if check_only else None

    dock_needing_management = None
    for dock_check in docks_run_by_citizen:
        checked_at_str_check = dock_check['fields'].get('CheckedAt')
        if not checked_at_str_check:
            dock_needing_management = dock_check; break
        try:
            checked_at_dt_check = datetime.fromisoformat(checked_at_str_check.replace("Z", "+00:00"))
            if checked_at_dt_check.tzinfo is None: checked_at_dt_check = pytz.UTC.localize(checked_at_dt_check)
            if (now_utc_dt - checked_at_dt_check) >= timedelta(hours=12):
                dock_needing_management = dock_check; break
        except ValueError:
            dock_needing_management = dock_check; break
            
    if not dock_needing_management:
        return False if check_only else None

    if check_only:
        if not citizen_position: return False
        dock_pos_check = _get_building_position_coords(dock_needing_management)
        if not dock_pos_check: return False
        if _calculate_distance_meters(citizen_position, dock_pos_check) > 20:
            path_check = get_path_between_points(citizen_position, dock_pos_check, transport_api_url)
            return bool(path_check and path_check.get('success'))
        return True

    # Actual creation logic
    dock_custom_id_val = dock_needing_management['fields'].get('BuildingId')
    dock_name_display = _get_bldg_display_name_module(tables, dock_needing_management)
    MANAGEMENT_DURATION_HOURS = 2.0
    log.info(f"{LogColors.OKCYAN}[Gestion Quai Public] {dock_name_display} (géré par {citizen_name}) nécessite une gestion.{LogColors.ENDC}")

    if not citizen_position: return None
    dock_pos = _get_building_position_coords(dock_needing_management)
    if not dock_pos: return None

    if _calculate_distance_meters(citizen_position, dock_pos) > 20:
        path_to_dock = get_path_between_points(citizen_position, dock_pos, transport_api_url)
        if not (path_to_dock and path_to_dock.get('success')):
            log.warning(f"{LogColors.WARNING}[Gestion Quai Public] Impossible de trouver un chemin vers {dock_name_display} pour {citizen_name}.{LogColors.ENDC}")
            return None
        
        goto_notes = f"Se rendant à {dock_name_display} pour gérer les opérations."
        action_details = {
            "action_on_arrival": "manage_public_dock",
            "duration_hours_on_arrival": MANAGEMENT_DURATION_HOURS,
            "target_dock_id_on_arrival": dock_custom_id_val
        }
        from backend.engine.activity_creators.goto_location_activity_creator import try_create as try_create_goto_location_activity
        goto_activity = try_create_goto_location_activity(
            tables=tables, citizen_record=citizen_record, destination_building_id=dock_custom_id_val,
            path_data=path_to_dock, notes=goto_notes, # current_time_utc removed
            details_payload=action_details, start_time_utc_iso=None # Assuming None implies immediate start handled by creator
        )
        if goto_activity:
            log.info(f"{LogColors.OKGREEN}[Gestion Quai Public] Activité 'goto_location' créée pour {citizen_name} vers {dock_name_display}.{LogColors.ENDC}")
        return goto_activity
    else: # Already at the dock
        manage_activity = try_create_manage_public_dock_activity(
            tables=tables, citizen_record=citizen_record, public_dock_record=dock_needing_management,
            duration_hours=MANAGEMENT_DURATION_HOURS, current_time_utc=now_utc_dt, start_time_utc_iso=None
        )
        if manage_activity:
            log.info(f"{LogColors.OKGREEN}[Gestion Quai Public] Activité 'manage_public_dock' créée directement pour {citizen_name} à {dock_name_display}.{LogColors.ENDC}")
        return manage_activity

# Nouvelle fonction pour la sélection pondérée des loisirs
def _try_process_weighted_leisure_activities(
    tables: Dict[str, Table], citizen_record: Dict, is_night_dummy: bool, resource_defs: Dict, building_type_defs: Dict, # is_night_dummy is unused placeholder
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str_val: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Tries to select and process a leisure activity based on weighted random choice."""

    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None # Not leisure time

    log.info(f"{LogColors.OKCYAN}[Loisirs Pondérés] Citoyen {citizen_name} ({citizen_social_class}): Évaluation des options de loisirs.{LogColors.ENDC}")

    leisure_candidates = [
        # (handler_function, priority_value, description_for_log)
        (_handle_work_on_art, 35, "Travailler sur une œuvre d'art (Artisti)"),
        (_handle_drink_at_inn, 40, "Boire un verre à l'auberge"), 
        (_handle_use_public_bath, 42, "Utiliser un bain public"), # Nouvelle activité de loisir
        (_handle_attend_theater_performance, 45, "Aller au théâtre"), 
        (_handle_read_book, 55, "Lire un livre"),
        (_handle_check_business_status, 65, "Vérifier le statut de l'entreprise"), 
        (_handle_manage_public_dock, 66, "Gérer un quai public"), 
        # _handle_shopping_tasks est pour l'instant géré séparément
    ]

    eligible_options: List[Tuple[Any, float]] = [] # List of (handler_function, weight)

    # Prepare arguments for calling the handlers, matching the main handler_args_tuple structure
    # The 'is_night' argument (second one) is a dummy placeholder as it's not used by these leisure handlers directly
    # but is part of the standard tuple structure they expect from their definition.
    # The actual check_only flag is the last argument.
    
    # Args for check_only=True
    handler_args_for_check = (
        tables, citizen_record, False, resource_defs, building_type_defs, # False is for the dummy is_night
        now_venice_dt, now_utc_dt, transport_api_url, api_base_url,
        citizen_position, citizen_custom_id, citizen_username, citizen_airtable_id, citizen_name, citizen_position_str_val,
        citizen_social_class, True # check_only=True is the last argument
    )
    
    # Args for check_only=False (actual creation)
    handler_args_for_creation = (
        tables, citizen_record, False, resource_defs, building_type_defs, # False is for the dummy is_night
        now_venice_dt, now_utc_dt, transport_api_url, api_base_url,
        citizen_position, citizen_custom_id, citizen_username, citizen_airtable_id, citizen_name, citizen_position_str_val,
        citizen_social_class, False # check_only=False is the last argument
    )

    for handler_func, priority_val, desc_log in leisure_candidates:
        try:
            can_execute = handler_func(*handler_args_for_check)
            if can_execute:
                weight = 100.0 - priority_val # Higher priority = lower number = higher weight
                if weight <= 0: weight = 1.0 # Ensure positive weight
                eligible_options.append((handler_func, weight))
                log.debug(f"  Option loisir éligible: {desc_log} (Poids: {weight})")
        except Exception as e_check:
            log.error(f"Erreur lors de la vérification de l'option loisir '{desc_log}': {e_check}")

    if not eligible_options:
        log.info(f"{LogColors.OKBLUE}[Loisirs Pondérés] {citizen_name}: Aucune option de loisir éligible trouvée après vérification.{LogColors.ENDC}")
        return None

    # Sélectionner une activité
    handlers_to_choose_from = [opt[0] for opt in eligible_options]
    weights = [opt[1] for opt in eligible_options]
    
    selected_handler_list = random.choices(handlers_to_choose_from, weights=weights, k=1)
    if not selected_handler_list: # Should not happen if eligible_options was not empty
        return None
        
    selected_handler = selected_handler_list[0]
    
    # Trouver la description pour le log
    selected_desc_log = "Activité de loisir inconnue"
    for h_func, _, desc_l in leisure_candidates:
        if h_func == selected_handler:
            selected_desc_log = desc_l
            break
            
    log.info(f"{LogColors.OKGREEN}[Loisirs Pondérés] {citizen_name}: Sélectionné '{selected_desc_log}' pour exécution.{LogColors.ENDC}")
    
    # Exécuter le handler sélectionné
    try:
        activity_created = selected_handler(*handler_args_for_creation)
        if isinstance(activity_created, dict) and activity_created.get('id'): # Check if it's an activity record
            return activity_created
        # If it returned bool (e.g. from an older handler not fully updated for this pattern) or None
        log.warning(f"Le handler de loisir sélectionné '{selected_desc_log}' n'a pas retourné un enregistrement d'activité valide.")
        return None
    except Exception as e_create:
        log.error(f"Erreur lors de la création de l'activité de loisir sélectionnée '{selected_desc_log}': {e_create}")
        return None


def _handle_general_goto_work(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str_val: Optional[str],
    citizen_social_class: str 
) -> Optional[Dict]:
    """Prio 70: Handles general goto_work if it's work time, citizen has a workplace and is not there."""
    workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    if not workplace_record: return None

    workplace_type_str = workplace_record['fields'].get('Type')
    workplace_def = building_type_defs.get(workplace_type_str) if workplace_type_str else None

    if not is_work_time(citizen_social_class, now_venice_dt, workplace_type_definition=workplace_def):
        return None

    if citizen_social_class == "Nobili" and (not workplace_def or not workplace_def.get("specialWorkHours")):
        return None

    if not citizen_position: return None
    workplace_pos = _get_building_position_coords(workplace_record)
    if not workplace_pos: return None 

    if _calculate_distance_meters(citizen_position, workplace_pos) < 20:
        return None # Already at workplace

    log.info(f"{LogColors.OKCYAN}[Aller au Travail] Citoyen {citizen_name} ({citizen_social_class}) n'est pas à son lieu de travail. Création goto_work.{LogColors.ENDC}")
    path_to_work = get_path_between_points(citizen_position, workplace_pos, transport_api_url)
    if path_to_work and path_to_work.get('success'):
        workplace_custom_id_val = workplace_record['fields'].get('BuildingId')
        home_record = get_citizen_home(tables, citizen_username) 
        is_at_home_val = False 
        if home_record and citizen_position:
            home_pos = _get_building_position_coords(home_record)
            if home_pos: is_at_home_val = _calculate_distance_meters(citizen_position, home_pos) < 20
        
        # Create goto_work activity, no chaining from this handler.
        # start_time_utc_iso is None for immediate start.
        activity_record = try_create_goto_work_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            workplace_custom_id_val, path_to_work, home_record, resource_defs,
            is_at_home_val, citizen_position_str_val, now_utc_dt, start_time_utc_iso=None
        )
        return activity_record 
    return None 

# --- Dispatcher for Specific Activity Requests ---
def dispatch_specific_activity_request(
    tables: Dict[str, Table],
    citizen_record_full: Dict, # Full Airtable record for the citizen
    activity_type: str,
    activity_parameters: Optional[Dict[str, Any]],
    resource_defs: Dict,
    building_type_defs: Dict,
    transport_api_url: str,
    api_base_url: str
) -> Dict[str, Any]: # Return type remains Dict, but content will change slightly
    # Get current time in UTC and Venice timezone
    now_utc_dt = datetime.now(pytz.UTC)
    now_venice_dt = now_utc_dt.astimezone(VENICE_TIMEZONE)
    
    log.info(f"{LogColors.ACTIVITY}Dispatch: Entered dispatch_specific_activity_request for citizen {citizen_record_full.get('fields', {}).get('Username', 'UnknownCitizen')} - ActivityType: {activity_type}, Params: {activity_parameters}{LogColors.ENDC}")

    """
    Attempts to create a specific activity for a citizen based on activity_type and parameters.
    This will now orchestrate chains of activities if necessary.
    Returns a dictionary with success status, message, and optionally the first activity of a chain.
    """
    # Extract common citizen details
    original_activity_type = activity_type # Keep original for logging if redirected
    citizen_custom_id = citizen_record_full['fields'].get('CitizenId')
    citizen_username = citizen_record_full['fields'].get('Username')
    citizen_airtable_id = citizen_record_full['id']
    citizen_name = f"{citizen_record_full['fields'].get('FirstName', '')} {citizen_record_full['fields'].get('LastName', '')}".strip() or citizen_username
    citizen_social_class = citizen_record_full['fields'].get('SocialClass', 'Facchini')
    
    citizen_position_str = citizen_record_full['fields'].get('Position')
    citizen_position: Optional[Dict[str, float]] = None
    try:
        if citizen_position_str: citizen_position = json.loads(citizen_position_str)
    except Exception: pass

    if not citizen_position: # Fallback if position is missing or invalid
        log.warning(f"Citizen {citizen_username} has no valid position. Attempting to assign random for specific activity.")
        citizen_position = _fetch_and_assign_random_starting_position(tables, citizen_record_full, api_base_url)
        if citizen_position:
            citizen_position_str = json.dumps(citizen_position)
        else:
            return {"success": False, "message": "Citizen has no position and failed to assign one.", "activity": None, "reason": "missing_position"}

    # Prepare is_hungry state for eat handlers
    is_hungry = False
    ate_at_str = citizen_record_full['fields'].get('AteAt')
    if ate_at_str:
        try:
            ate_at_dt = dateutil_parser.isoparse(ate_at_str.replace('Z', '+00:00'))
            if ate_at_dt.tzinfo is None: ate_at_dt = pytz.UTC.localize(ate_at_dt)
            if (now_utc_dt - ate_at_dt) > timedelta(hours=12): is_hungry = True
        except ValueError: is_hungry = True 
    else: is_hungry = True
    citizen_record_full['is_hungry'] = is_hungry # Modify a copy if concerned about side effects, or pass as arg

    # Common arguments for handler functions
    handler_args = (
        tables, citizen_record_full, False, resource_defs, building_type_defs, # False for deprecated is_night
        now_venice_dt, now_utc_dt, transport_api_url, api_base_url,
        citizen_position, citizen_custom_id, citizen_username, citizen_airtable_id, 
        citizen_name, citizen_position_str, citizen_social_class
    )
    
    first_activity_of_chain: Optional[Dict] = None # Will store the first activity created
    strategy_applied = "default_order" # For logging/messaging
    params = activity_parameters or {}

    # Check if 'params' (which is activity_parameters from the API call)
    # contains a nested "activityParameters" field. If so, use that inner dict.
    # This handles cases where the full request body might have been passed.
    if isinstance(params, dict) and "activityParameters" in params and isinstance(params["activityParameters"], dict):
        log.info(f"{LogColors.ACTIVITY}Dispatch: Detected nested 'activityParameters'. Using inner dictionary for activity type '{activity_type}'.{LogColors.ENDC}")
        params = params["activityParameters"]
    elif isinstance(params, dict) and "activityDetails" in params and isinstance(params["activityDetails"], dict):
        # Fallback for an older key name that might have been used by KinOS or API
        log.info(f"{LogColors.ACTIVITY}Dispatch: Detected nested 'activityDetails'. Using inner dictionary for activity type '{activity_type}'.{LogColors.ENDC}")
        params = params["activityDetails"]
    
    # Ensure params is a dict after potential reassignment, defaulting to empty if not.
    params = params if isinstance(params, dict) else {}


    # --- Handle specific activity_type requests ---
    # Each block should set first_activity_of_chain if successful.

    # Redirect make_offer_for_land to bid_on_land
    if activity_type == "make_offer_for_land":
        log.info(f"Redirecting activityType 'make_offer_for_land' to 'bid_on_land' for citizen {citizen_username}.")
        activity_type = "bid_on_land"

    if activity_type == "goto_work":
        log.info(f"Dispatching to try_create_goto_work_activity for {citizen_name} with params: {params}")
        to_building_id_param = params.get("toBuildingId")
        path_data_param = params.get("pathData") # This should be the path from current location to to_building_id

        if not to_building_id_param or not path_data_param:
            return {"success": False, "message": "Missing toBuildingId or pathData for goto_work.", "activity": None, "reason": "missing_goto_work_parameters"}

        home_record_param = get_citizen_home(tables, citizen_username) # Fetch home record
        is_at_home_param = False
        if home_record_param and citizen_position:
            home_pos = _get_building_position_coords(home_record_param)
            if home_pos:
                is_at_home_param = _calculate_distance_meters(citizen_position, home_pos) < 20
        
        first_activity_of_chain = try_create_goto_work_activity(
            tables=tables,
            citizen_custom_id=citizen_custom_id,
            citizen_username=citizen_username,
            citizen_airtable_id=citizen_airtable_id,
            to_building_id=to_building_id_param,
            path_data=path_data_param,
            home_record=home_record_param,
            resource_defs=resource_defs, # Passed to dispatch_specific_activity_request
            is_at_home=is_at_home_param,
            citizen_position_str=citizen_position_str,
            current_time_utc=now_utc_dt,
            start_time_utc_iso=params.get("startTimeUtcIso"), # Allow explicit start time
            custom_notes=params.get("customNotes"),
            activity_type="goto_work", # Explicitly set
            details_payload=params.get("detailsPayload")
        )
        if first_activity_of_chain and isinstance(first_activity_of_chain, dict) and 'fields' in first_activity_of_chain:
            return {"success": True, "message": f"Goto_work endeavor initiated for {citizen_name}. Activity: {first_activity_of_chain['fields'].get('Type', 'N/A')}.", "activity": first_activity_of_chain['fields']}
        else:
            log.warning(f"try_create_goto_work_activity did not return a valid activity record for {citizen_name}. Returned: {first_activity_of_chain}")
            return {"success": False, "message": f"Could not initiate 'goto_work' endeavor for {citizen_name}.", "activity": None, "reason": "goto_work_creation_failed"}

    elif activity_type == "eat_from_inventory":
        log.info(f"Dispatching to _handle_eat_from_inventory for {citizen_name}.")
        # Removed: if not is_hungry: check
        first_activity_of_chain = _handle_eat_from_inventory(*handler_args)
        if first_activity_of_chain:
            return {"success": True, "message": f"Eating from inventory endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields']['Type']}.", "activity": first_activity_of_chain['fields']}
        else:
            return {"success": False, "message": f"Could not initiate eating from inventory for {citizen_name}.", "activity": None, "reason": "no_food_in_inventory_or_error"}

    elif activity_type == "eat_at_home":
        log.info(f"Dispatching to _handle_eat_at_home_or_goto for {citizen_name}.")
        # Removed: if not is_hungry: check
        first_activity_of_chain = _handle_eat_at_home_or_goto(*handler_args)
        if first_activity_of_chain:
            return {"success": True, "message": f"Eating at home endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields']['Type']}.", "activity": first_activity_of_chain['fields']}
        else:
            return {"success": False, "message": f"Could not initiate eating at home for {citizen_name}.", "activity": None, "reason": "no_food_at_home_or_path_issue"}

    elif activity_type == "eat_at_tavern":
        log.info(f"Dispatching to _handle_eat_at_tavern_or_goto for {citizen_name}.")
        # Removed: if not is_hungry: check
        first_activity_of_chain = _handle_eat_at_tavern_or_goto(*handler_args)
        if first_activity_of_chain:
            return {"success": True, "message": f"Eating at tavern endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields']['Type']}.", "activity": first_activity_of_chain['fields']}
        else:
            return {"success": False, "message": f"Could not initiate eating at tavern for {citizen_name}.", "activity": None, "reason": "no_tavern_found_or_funds_issue"}
            
    elif activity_type == "eat": # Generic "eat" with strategy
        strategy = params.get("strategy", "default_order")
        strategy_applied = strategy

        # Removed: if not is_hungry: check

        if strategy == "inventory":
            first_activity_of_chain = _handle_eat_from_inventory(*handler_args)
        elif strategy == "home":
            first_activity_of_chain = _handle_eat_at_home_or_goto(*handler_args)
        elif strategy == "tavern":
            first_activity_of_chain = _handle_eat_at_tavern_or_goto(*handler_args)
        else: # Default order if no specific strategy or unknown
            first_activity_of_chain = _handle_eat_from_inventory(*handler_args)
            if not first_activity_of_chain:
                first_activity_of_chain = _handle_eat_at_home_or_goto(*handler_args)
            if not first_activity_of_chain:
                first_activity_of_chain = _handle_eat_at_tavern_or_goto(*handler_args)
        
        if first_activity_of_chain:
            return {"success": True, "message": f"Eating endeavor initiated for {citizen_name} (strategy: {strategy_applied}). First activity: {first_activity_of_chain['fields']['Type']}.", "activity": first_activity_of_chain['fields']}
        else:
            return {"success": False, "message": f"Could not initiate eating endeavor for {citizen_name} (strategy: {strategy_applied}).", "activity": None, "reason": "no_eating_option_found"}

    elif activity_type == "leave_venice":
        # _handle_leave_venice should already create the necessary chain (e.g., goto_dock then leave_venice)
        # and return the first activity of that chain.
        first_activity_of_chain = _handle_leave_venice(*handler_args)
        if first_activity_of_chain:
            return {"success": True, "message": f"Leave Venice endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields']['Type']}.", "activity": first_activity_of_chain['fields']}
        else:
            return {"success": False, "message": f"Could not initiate 'leave_venice' endeavor for {citizen_name}.", "activity": None, "reason": "conditions_not_met_or_pathfinding_failed"}

    elif activity_type == "seek_shelter": # Example for a new high-level endeavor
        # _handle_night_shelter creates chains (e.g. goto_home then rest)
        first_activity_of_chain = _handle_night_shelter(*handler_args)
        if first_activity_of_chain:
            return {"success": True, "message": f"Seek shelter endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields']['Type']}.", "activity": first_activity_of_chain['fields']}
        else:
            return {"success": False, "message": f"Could not find or initiate shelter endeavor for {citizen_name}.", "activity": None, "reason": "no_shelter_option_found"}

    elif activity_type == "fetch_resource":
        log.info(f"Dispatching to resource_fetching_activity_creator for {citizen_name} with params: {activity_parameters}")
        # Parameters for try_create_resource_fetching_activity:
        # tables, citizen_airtable_id, citizen_custom_id, citizen_username,
        # contract_custom_id, from_building_custom_id, to_building_custom_id,
        # resource_type_id, amount, path_data, current_time_utc, resource_defs, start_time_utc_iso
        
        # Extract parameters from activity_parameters
        contract_id_param = params.get("contractId") # This is the custom ContractId string
        from_building_id_param = params.get("fromBuildingId")
        to_building_id_param = params.get("toBuildingId") # Can be None
        
        log.info(f"{LogColors.ACTIVITY}Dispatch (fetch_resource): Current params for {citizen_name}: {json.dumps(params)}{LogColors.ENDC}")
        
        resource_type_id_param = params.get("resourceTypeId") or params.get("resourceType") # Accept resourceType as fallback
        amount_param_raw = params.get("amount")

        log.info(f"{LogColors.ACTIVITY}Dispatch (fetch_resource): Extracted resource_type_id_param: {resource_type_id_param}, amount_param_raw: {amount_param_raw}{LogColors.ENDC}")

        amount_param = 0.0
        if amount_param_raw is not None:
            try:
                amount_param = float(amount_param_raw)
            except ValueError:
                log.error(f"{LogColors.FAIL}Dispatch (fetch_resource): Invalid amount '{amount_param_raw}' for {citizen_name}. Defaulting to 0.0.{LogColors.ENDC}")
                # This will likely cause the "missing parameters" error below, which is correct.
        
        # Path data is tricky here. If the AI requests a fetch_resource, it implies the citizen
        # might need to travel to the from_building first.
        # The resource_fetching_activity_creator expects path_data from current location to from_building.
        # For orchestrated creation, we might need to calculate this path here if not provided.
        # For now, assume path_data might be None or provided if AI is smart.
        # If path_data is None, the creator might assume citizen is already at from_building or handle it.
        # Let's assume for now that if AI calls this, it's for an immediate fetch from a known location,
        # or the creator handles finding the source if from_building_id_param is None.

        path_data_param = params.get("pathData") # Optional: AI might provide pre-calculated path

        if not resource_type_id_param or amount_param <= 0:
            return {"success": False, "message": "Missing resourceTypeId or invalid amount for fetch_resource.", "activity": None, "reason": "missing_fetch_parameters"}

        # The resource_fetching_activity_creator.try_create function is imported as try_create_resource_fetching_activity
        first_activity_of_chain = try_create_resource_fetching_activity(
            tables=tables,
            citizen_airtable_id=citizen_airtable_id,
            citizen_custom_id=citizen_custom_id,
            citizen_username=citizen_username,
            contract_custom_id=contract_id_param,
            from_building_custom_id=from_building_id_param,
            to_building_custom_id=to_building_id_param,
            resource_type_id=resource_type_id_param,
            amount=amount_param,
            path_data_to_source=path_data_param, # Corrected argument name
            current_time_utc=now_utc_dt,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs, # Added missing argument
            now_venice_dt=now_venice_dt,           # Added missing argument
            transport_api_url=transport_api_url,   # Added missing argument
            api_base_url=api_base_url,             # Added missing argument
            start_time_utc_iso=params.get("startTimeUtcIso") # Allow explicit start time
        )
        if first_activity_of_chain and isinstance(first_activity_of_chain, dict) and 'fields' in first_activity_of_chain:
            return {"success": True, "message": f"Fetch resource endeavor initiated for {citizen_name}. Activity: {first_activity_of_chain['fields'].get('Type', 'N/A')}.", "activity": first_activity_of_chain['fields']}
        else:
            log.warning(f"resource_fetching_activity_creator did not return a valid activity record for {citizen_name}. Returned: {first_activity_of_chain}")
            return {"success": False, "message": f"Could not initiate 'fetch_resource' endeavor for {citizen_name}.", "activity": None, "reason": "fetch_resource_creation_failed"}
            
    # TODO: Add more handlers for other high-level activityTypes like "work_at_business", "shop_for_item", etc.
    # These would involve:
    # 1. Checking prerequisites (e.g., has workplace, has money).
    # 2. Determining if travel is needed.
    # 3. Calling appropriate activity creators in sequence.
    # Example: "work_at_business"
    # elif activity_type == "work_at_business":
    #     workplace_rec = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    #     if not workplace_rec:
    #         return {"success": False, "message": f"{citizen_name} has no workplace.", "activity": None, "reason": "no_workplace"}
    #     
    #     workplace_pos = _get_building_position_coords(workplace_rec)
    #     is_at_work = citizen_position and workplace_pos and _calculate_distance_meters(citizen_position, workplace_pos) < 20
    #
    #     if is_at_work:
    #         # Directly try to create a production/work task
    #         # This might call a sub-handler like _handle_production_and_general_work_tasks
    #         # which itself needs to return the first activity of a potential chain.
    #         first_activity_of_chain = _handle_production_and_general_work_tasks(*handler_args) # Assuming it's adapted
    #     else:
    #         # Create goto_work, then chain production/work
    #         path_to_work = get_path_between_points(citizen_position, workplace_pos, transport_api_url)
    #         if path_to_work and path_to_work.get('success'):
    #             first_activity_of_chain = try_create_goto_work_activity(...) # Create goto_work
    #             if first_activity_of_chain:
    #                 # Chain the actual work activity (e.g., production)
    #                 # next_work_start_time = first_activity_of_chain['fields']['EndDate']
    #                 # Call try_create_production_activity with start_time_utc_iso = next_work_start_time
    #                 pass # Placeholder for chaining logic
    #     # ... return based on first_activity_of_chain ...

    elif activity_type == "initiate_building_project":
        log.info(f"Dispatching to initiate_building_project_creator for {citizen_name} with params: {activity_parameters}")
        # The initiate_building_project_creator.try_create might return an Airtable record directly,
        # OR a dict like {'success': True, 'activity_fields': {...}}
        creator_response = try_create_initiate_building_project_activity(
            tables,
            citizen_record_full,
            activity_parameters if activity_parameters is not None else {},
            resource_defs,
            building_type_defs,
            now_venice_dt,
            now_utc_dt,
            transport_api_url,
            api_base_url
        )

        activity_fields_to_return = None
        # Default success message, might be overridden by creator's message
        success_message = f"Initiate building project endeavor initiated for {citizen_name}."

        if creator_response and isinstance(creator_response, dict):
            if 'fields' in creator_response: # Case 1: Creator returned an Airtable record {id: ..., fields: ...}
                activity_fields_to_return = creator_response['fields']
                # Append activity type to message if available
                success_message = f"Initiate building project endeavor initiated for {citizen_name}. First activity: {activity_fields_to_return.get('Type', 'N/A')}."
            elif creator_response.get('success') is True and 'activity_fields' in creator_response and isinstance(creator_response['activity_fields'], dict):
                # Case 2: Creator returned {'success': True, 'activity_fields': {...}}
                activity_fields_to_return = creator_response['activity_fields']
                success_message = creator_response.get('message', success_message)
                # Ensure the message reflects the actual activity type if available and not already in creator's message
                activity_type_from_fields = activity_fields_to_return.get('Type', 'N/A')
                if activity_type_from_fields not in success_message: # Avoid duplicating if creator message already has it
                    success_message += f" First activity: {activity_type_from_fields}."
            elif creator_response.get('success') is True and 'activity' in creator_response and isinstance(creator_response['activity'], dict):
                # Case 3: Creator returned {'success': True, 'activity': {...activity_fields...}}
                activity_fields_to_return = creator_response['activity']
                success_message = creator_response.get('message', success_message)
                activity_type_from_fields = activity_fields_to_return.get('Type', 'N/A')
                if activity_type_from_fields not in success_message:
                    success_message += f" First activity: {activity_type_from_fields}."


        if activity_fields_to_return:
            return {"success": True, "message": success_message, "activity": activity_fields_to_return}
        else:
            log.warning(f"initiate_building_project_creator did not return a valid activity record or expected success structure for {citizen_name}. Returned: {creator_response}")
            failure_message = f"Could not initiate 'initiate_building_project' endeavor for {citizen_name}."
            reason = "initiate_building_project_creation_failed_or_invalid_response"
            # If creator returned a dict with success=False and a message/reason, use that
            if isinstance(creator_response, dict) and creator_response.get('success') is False:
                failure_message = creator_response.get('message', failure_message)
                reason = creator_response.get('reason', reason)
            return {"success": False, "message": failure_message, "activity": None, "reason": reason}

    elif activity_type == "send_message":
        log.info(f"Dispatching to send_message_creator for {citizen_name} with params: {activity_parameters}")
        # The send_message_creator.try_create expects `tables`, `citizen_record`, and `details` (which are activityParameters)
        # It will now return the first activity record of the chain, or None.
        first_activity_of_chain = try_create_send_message_chain(
            tables,
            citizen_record_full,
            activity_parameters if activity_parameters is not None else {}, # Ensure details is a dict
            api_base_url,       # Pass api_base_url
            transport_api_url   # Pass transport_api_url
        )
        if first_activity_of_chain and isinstance(first_activity_of_chain, dict) and 'fields' in first_activity_of_chain:
            return {"success": True, "message": f"Send message endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields'].get('Type', 'N/A')}.", "activity": first_activity_of_chain['fields']}
        else:
            log.warning(f"send_message_creator did not return a valid activity record for {citizen_name}. Returned: {first_activity_of_chain}")
            return {"success": False, "message": f"Could not initiate 'send_message' endeavor for {citizen_name}.", "activity": None, "reason": "send_message_creation_failed"}

    elif activity_type == "manage_public_storage_offer":
        log.info(f"Dispatching to manage_public_storage_offer_creator for {citizen_name} with params: {activity_parameters}")
        first_activity_of_chain = try_create_manage_public_storage_offer_chain(
            tables, citizen_record_full, activity_parameters or {},
            resource_defs, building_type_defs,
            now_venice_dt, now_utc_dt,
            transport_api_url, api_base_url
        )
        if first_activity_of_chain and isinstance(first_activity_of_chain, dict) and 'fields' in first_activity_of_chain:
            return {"success": True, "message": f"Manage public storage offer endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields'].get('Type', 'N/A')}.", "activity": first_activity_of_chain['fields']}
        else:
            log.warning(f"manage_public_storage_offer_creator did not return a valid activity record for {citizen_name}. Returned: {first_activity_of_chain}")
            return {"success": False, "message": f"Could not initiate 'manage_public_storage_offer' endeavor for {citizen_name}.", "activity": None, "reason": "manage_public_storage_offer_creation_failed"}

    elif activity_type == "bid_on_land":
        log.info(f"Dispatching to make_offer_for_land_creator (aliased for bid_on_land) for {citizen_name} (original type: {original_activity_type}) with params: {activity_parameters}")
        # Use make_offer_for_land_creator as bid_on_land_activity_creator was removed and functionality merged.
        from backend.engine.activity_creators.make_offer_for_land_creator import try_create as try_create_bid_on_land_chain
        # The try_create function from make_offer_for_land_creator will be used.
        activities_to_create_payloads = try_create_bid_on_land_chain(
            tables,
            citizen_record_full,
            activity_type, # Pass the actual activity_type
            activity_parameters if activity_parameters is not None else {},
            now_venice_dt, # Pass now_venice_dt
            now_utc_dt,    # Pass now_utc_dt
            transport_api_url, # Pass transport_api_url
            api_base_url       # Pass api_base_url
        )
        
        created_airtable_records = []
        if activities_to_create_payloads and isinstance(activities_to_create_payloads, list):
            log.info(f"{LogColors.ACTIVITY}Dispatch: Received {len(activities_to_create_payloads)} activity payloads from creator for {original_activity_type}. Attempting Airtable creation...{LogColors.ENDC}")
            for activity_payload in activities_to_create_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    # Ensure essential fields are present if not set by creator
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload:
                         activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload:
                         activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload:
                         activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    # UpdatedAt is handled by Airtable, remove if present
                    if 'UpdatedAt' in activity_payload:
                        del activity_payload['UpdatedAt']

                    # Nettoyer les champs textuels avant la création
                    if 'Title' in activity_payload and isinstance(activity_payload['Title'], str):
                        activity_payload['Title'] = clean_thought_content(tables, activity_payload['Title'])
                    if 'Description' in activity_payload and isinstance(activity_payload['Description'], str):
                        activity_payload['Description'] = clean_thought_content(tables, activity_payload['Description'])
                    if 'Thought' in activity_payload and isinstance(activity_payload['Thought'], str):
                        activity_payload['Thought'] = clean_thought_content(tables, activity_payload['Thought'])
                    if 'Notes' in activity_payload and isinstance(activity_payload['Notes'], str): # Ne nettoyer que si c'est une chaîne simple
                        activity_payload['Notes'] = clean_thought_content(tables, activity_payload['Notes'])
                        
                    log.info(f"{LogColors.ACTIVITY}Dispatch: Attempting to create activity in Airtable. Payload for '{activity_payload.get('Type', 'unknown')}': {json.dumps(activity_payload, indent=2)}{LogColors.ENDC}")
                    created_record = tables['activities'].create(activity_payload)
                    log.info(f"{LogColors.SUCCESS}Dispatch: Airtable API response for create: {json.dumps(created_record, indent=2)}{LogColors.ENDC}")

                    if created_record and 'id' in created_record and created_record['id']:
                        airtable_record_id = created_record['id']
                        log.info(f"{LogColors.ACTIVITY}Dispatch: Airtable 'create' call for {activity_payload.get('Type', 'unknown')} for {citizen_username} returned record ID: {airtable_record_id}. Attempting diagnostic fetch...{LogColors.ENDC}")
                        # Diagnostic: Immediately try to fetch the created record
                        try:
                            time.sleep(0.5) # Brief pause for eventual consistency, though usually not needed for direct create/get
                            fetched_record_check = tables['activities'].get(airtable_record_id)
                            if fetched_record_check:
                                log.info(f"{LogColors.OKGREEN}Dispatch: Diagnostic fetch successful for Airtable ID {airtable_record_id}. Record exists.{LogColors.ENDC}")
                                log.info(f"{LogColors.OKGREEN}Dispatch: Fetched record content: {json.dumps(fetched_record_check, indent=2)}{LogColors.ENDC}")
                                created_airtable_records.append(created_record) # Use original created_record
                                log.info(f"{LogColors.SUCCESS}Dispatch: Successfully processed payload for activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}. Airtable Record ID: {airtable_record_id}{LogColors.ENDC}")
                            else:
                                # This case is highly problematic: create reported success with ID, but get failed.
                                log.error(f"{LogColors.FAIL}Dispatch: DIAGNOSTIC FAILURE. Airtable 'create' reported success with ID {airtable_record_id}, but immediate 'get' request FAILED to find it. Activity NOT considered successfully created for this chain.{LogColors.ENDC}")
                                # DO NOT append to created_airtable_records if diagnostic fetch fails.
                                # This will cause the API to return an error if this was the only activity or all failed.
                        except Exception as e_diag_fetch:
                            log.error(f"{LogColors.FAIL}Dispatch: DIAGNOSTIC EXCEPTION during fetch of {airtable_record_id}: {e_diag_fetch}. Activity NOT considered successfully created for this chain due to fetch exception.{LogColors.ENDC}")
                            # DO NOT append to created_airtable_records if diagnostic fetch has an exception.
                    else:
                        log.error(f"{LogColors.FAIL}Dispatch: Airtable 'create' call for {activity_payload.get('Type', 'unknown')} for {citizen_username} did NOT return a valid record with an ID. Response: {json.dumps(created_record, indent=2)}{LogColors.ENDC}")
                        # This path implies a problem; the activity might not have been truly created.
                        # The existing logic will lead to a failure response if created_airtable_records remains empty.

                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    import traceback
                    log.error(traceback.format_exc())
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
        
        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Bid on land endeavor (originally {original_activity_type}) initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"{LogColors.WARNING}Activity creator for '{original_activity_type}' did not return any activities to create for {citizen_name}.{LogColors.ENDC}")
            return {"success": False, "message": f"Could not initiate '{original_activity_type}' endeavor for {citizen_name}.", "activity": None, "reason": f"{original_activity_type}_creation_failed_no_payloads"}

    elif activity_type == "buy_listed_land":
        log.info(f"Dispatching to buy_listed_land_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.buy_listed_land_creator import try_create as try_create_buy_listed_land_activity
        
        activities_chain = try_create_buy_listed_land_activity(
            tables,
            citizen_record_full,
            activity_type,
            activity_parameters if activity_parameters is not None else {},
            now_venice_dt,
            now_utc_dt,
            transport_api_url,
            api_base_url
        )
        
        created_airtable_records = []
        if activities_chain and isinstance(activities_chain, list): # Renamed activities_to_create_payloads to activities_chain to match existing code
            for activity_payload in activities_chain:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    # Ensure essential fields are present if not set by creator
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload:
                         activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload:
                         activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload:
                         activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: # Ensure UpdatedAt is not sent
                        del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
        
        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Buy listed land endeavor (originally {original_activity_type}) initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"{LogColors.WARNING}Activity creator for '{original_activity_type}' did not return any activities to create for {citizen_name}. Returned: {activities_chain}{LogColors.ENDC}")
            return {"success": False, "message": f"Could not initiate '{original_activity_type}' endeavor for {citizen_name}.", "activity": None, "reason": f"{original_activity_type}_creation_failed_no_payloads"}

    elif activity_type == "list_land_for_sale":
        log.info(f"Dispatching to list_land_for_sale_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.list_land_for_sale_creator import try_create as try_create_list_land_for_sale_activity
        
        activities_to_create_payloads = try_create_list_land_for_sale_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, 
            now_venice_dt, now_utc_dt, 
            transport_api_url, api_base_url
        )
        
        created_airtable_records = []
        if activities_to_create_payloads and isinstance(activities_to_create_payloads, list):
            for activity_payload in activities_to_create_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    # Ensure essential fields are present if not set by creator
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload:
                         activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload:
                         activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload:
                         activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: # Ensure UpdatedAt is not sent
                        del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
        
        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"List land for sale endeavor (originally {original_activity_type}) initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"{LogColors.WARNING}Activity creator for '{original_activity_type}' did not return any activities to create for {citizen_name}. Returned: {activities_to_create_payloads}{LogColors.ENDC}")
            return {"success": False, "message": f"Could not initiate '{original_activity_type}' endeavor for {citizen_name}.", "activity": None, "reason": f"{original_activity_type}_creation_failed_no_payloads"}

    elif activity_type == "accept_land_offer":
        log.info(f"Dispatching to accept_land_offer_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.accept_land_offer_creator import try_create as try_create_accept_land_offer_activity
        activities_chain = try_create_accept_land_offer_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Accept land offer endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"accept_land_offer_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'accept_land_offer'.", "activity": None, "reason": "accept_land_offer_creation_failed"}

    elif activity_type == "cancel_land_listing":
        log.info(f"Dispatching to cancel_land_listing_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.cancel_land_listing_creator import try_create as try_create_cancel_land_listing_activity
        activities_chain = try_create_cancel_land_listing_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Cancel land listing endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"cancel_land_listing_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'cancel_land_listing'.", "activity": None, "reason": "cancel_land_listing_creation_failed"}

    elif activity_type == "cancel_land_offer":
        log.info(f"Dispatching to cancel_land_offer_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.cancel_land_offer_creator import try_create as try_create_cancel_land_offer_activity
        
        activities_to_create_payloads = try_create_cancel_land_offer_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, 
            now_venice_dt, now_utc_dt, 
            transport_api_url, api_base_url
        )
        
        created_airtable_records = []
        if activities_to_create_payloads and isinstance(activities_to_create_payloads, list):
            for activity_payload in activities_to_create_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    # Ensure essential fields are present if not set by creator
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload:
                         activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload:
                         activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload:
                         activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: # Ensure UpdatedAt is not sent
                        del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
        
        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Cancel land offer endeavor (originally {original_activity_type}) initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"{LogColors.WARNING}Activity creator for '{original_activity_type}' did not return any activities to create for {citizen_name}.{LogColors.ENDC}")
            return {"success": False, "message": f"Could not initiate '{original_activity_type}' endeavor for {citizen_name}.", "activity": None, "reason": f"{original_activity_type}_creation_failed_no_payloads"}

    elif activity_type == "adjust_land_lease_price":
        log.info(f"Dispatching to adjust_land_lease_price_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.adjust_land_lease_price_creator import try_create as try_create_adjust_land_lease_price_activity
        activities_chain = try_create_adjust_land_lease_price_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Adjust land lease price endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"adjust_land_lease_price_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'adjust_land_lease_price'.", "activity": None, "reason": "adjust_land_lease_price_creation_failed"}
            
    elif activity_type == "adjust_building_rent_price":
        log.info(f"Dispatching to adjust_building_rent_price_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.adjust_building_rent_price_creator import try_create as try_create_adjust_building_rent_price_activity
        activities_chain = try_create_adjust_building_rent_price_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Adjust building rent price endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"adjust_building_rent_price_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'adjust_building_rent_price'.", "activity": None, "reason": "adjust_building_rent_price_creation_failed"}

    elif activity_type == "adjust_building_lease_price":
        log.info(f"Dispatching to adjust_building_lease_price_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.adjust_building_lease_price_creator import try_create as try_create_adjust_building_lease_price_activity
        activities_chain = try_create_adjust_building_lease_price_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Adjust building lease price endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"adjust_building_lease_price_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'adjust_building_lease_price'.", "activity": None, "reason": "adjust_building_lease_price_creation_failed"}

    elif activity_type == "bid_on_building":
        log.info(f"Dispatching to bid_on_building_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.bid_on_building_activity_creator import try_create as try_create_bid_on_building_activity
        activities_chain = try_create_bid_on_building_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Bid on building endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"bid_on_building_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'bid_on_building'.", "activity": None, "reason": "bid_on_building_creation_failed"}

    elif activity_type == "manage_public_sell_contract":
        log.info(f"Dispatching to manage_public_sell_contract_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.manage_public_sell_contract_creator import try_create as try_create_manage_public_sell_contract_activity
        
        activity_payloads = try_create_manage_public_sell_contract_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, resource_defs, building_type_defs, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )

        if not activity_payloads: # Creator returns None or empty list on failure/no action
            log.warning(f"manage_public_sell_contract_creator for {citizen_name} returned no activity payloads.")
            return {"success": False, "message": "No public sell contract activities were generated by the creator.", "activity": None, "reason": "no_activities_generated_by_creator"}

        created_airtable_records = []
        for activity_payload in activity_payloads:
            if not isinstance(activity_payload, dict):
                log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
            try:
                if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                     activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                if 'Citizen' not in activity_payload: activity_payload['Citizen'] = citizen_username
                if 'Status' not in activity_payload: activity_payload['Status'] = 'created'
                if 'CreatedAt' not in activity_payload: activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                if 'UpdatedAt' in activity_payload: del activity_payload['UpdatedAt']

                created_record = tables['activities'].create(activity_payload)
                created_airtable_records.append(created_record)
                log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
            except Exception as e:
                log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
        
        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Manage public sell contract endeavor initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else: # Should be caught by "if not activity_payloads" earlier
            log.warning(f"manage_public_sell_contract_creator for {citizen_name} returned an empty list of payloads after processing.")
            return {"success": False, "message": "Could not initiate 'manage_public_sell_contract'.", "activity": None, "reason": "manage_public_sell_contract_creation_failed_empty_payloads"}

    elif activity_type == "manage_import_contract":
        log.info(f"Dispatching to manage_import_contract_creator for {citizen_name} with params: {json.dumps(activity_parameters, indent=2) if activity_parameters else 'None'}") # Log params more clearly
        # The check "if not activity_parameters:" is removed.
        # We will pass "activity_parameters or {}" to the creator,
        # letting the creator handle validation of specific fields.

        from backend.engine.activity_creators.manage_import_contract_creator import try_create as try_create_manage_import_contract_activity
        
        # Call the creator function
        # Pass "activity_parameters or {}" to ensure the creator receives a dict.
        activities_chain_or_error = try_create_manage_import_contract_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, resource_defs, building_type_defs, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )

        # Handle the response from the creator
        if isinstance(activities_chain_or_error, dict) and not activities_chain_or_error.get("success", True):
            # Error dictionary returned by the creator
            log.warning(f"manage_import_contract_creator for {citizen_name} failed: {activities_chain_or_error.get('message')}")
            return {
                "success": False,
                "message": activities_chain_or_error.get("message", "Could not initiate 'manage_import_contract' due to creator error."),
                "activity": None,
                "reason": activities_chain_or_error.get("reason", "manage_import_contract_creation_failed_from_creator")
            }
        elif isinstance(activities_chain_or_error, list):
            activity_payloads = activities_chain_or_error
            if not activity_payloads:
                log.warning(f"manage_import_contract_creator for {citizen_name} returned no activity payloads.")
                return {"success": False, "message": "No import contract activities were generated by the creator.", "activity": None, "reason": "no_activities_generated_by_creator"}

            created_airtable_records = []
            for activity_payload in activity_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload: activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload: activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload: activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
            
            if created_airtable_records:
                first_created_activity_fields = created_airtable_records[0]['fields']
                message = f"Manage import contract endeavor initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
                return {"success": True, "message": message, "activity": first_created_activity_fields}
            else: # Should be caught by "if not activity_payloads" earlier
                log.warning(f"manage_import_contract_creator for {citizen_name} returned an empty list of payloads after processing.")
                return {"success": False, "message": "Could not initiate 'manage_import_contract'.", "activity": None, "reason": "manage_import_contract_creation_failed_empty_payloads"}
        else: # Unexpected return type from creator
            log.error(f"manage_import_contract_creator for {citizen_name} returned unexpected data type: {type(activities_chain_or_error)}. Expected list or error dict.")
            return {"success": False, "message": "Internal error: Unexpected response from import contract creator.", "activity": None, "reason": "unexpected_creator_response"}

    elif activity_type == "manage_public_import_contract":
        log.info(f"Dispatching to manage_public_import_contract_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.manage_public_import_contract_creator import try_create as try_create_manage_public_import_contract_activity
        
        activities_chain_or_error = try_create_manage_import_contract_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, resource_defs, building_type_defs, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )

        if isinstance(activities_chain_or_error, dict) and not activities_chain_or_error.get("success", True):
            # Error dictionary returned by the creator
            log.warning(f"manage_import_contract_creator for {citizen_name} failed: {activities_chain_or_error.get('message')}")
            return {
                "success": False,
                "message": activities_chain_or_error.get("message", "Could not initiate 'manage_import_contract' due to creator error."),
                "activity": None,
                "reason": activities_chain_or_error.get("reason", "manage_import_contract_creation_failed_from_creator")
            }
        elif isinstance(activities_chain_or_error, list):
            activity_payloads = activities_chain_or_error
            if not activity_payloads:
                log.warning(f"manage_import_contract_creator for {citizen_name} returned no activity payloads.")
                return {"success": False, "message": "No import contract activities were generated by the creator.", "activity": None, "reason": "no_activities_generated_by_creator"}

            created_airtable_records = []
            for activity_payload in activity_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload: activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload: activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload: activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
            
            if created_airtable_records:
                first_created_activity_fields = created_airtable_records[0]['fields']
                message = f"Manage import contract endeavor initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
                return {"success": True, "message": message, "activity": first_created_activity_fields}
            else: # Should be caught by "if not activity_payloads" earlier
                log.warning(f"manage_import_contract_creator for {citizen_name} returned an empty list of payloads after processing.")
                return {"success": False, "message": "Could not initiate 'manage_import_contract'.", "activity": None, "reason": "manage_import_contract_creation_failed_empty_payloads"}
        else: # Unexpected return type from creator
            log.error(f"manage_import_contract_creator for {citizen_name} returned unexpected data type: {type(activities_chain_or_error)}. Expected list or error dict.")
            return {"success": False, "message": "Internal error: Unexpected response from import contract creator.", "activity": None, "reason": "unexpected_creator_response"}

    elif activity_type == "manage_public_import_contract":
        log.info(f"Dispatching to manage_public_import_contract_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.manage_public_import_contract_creator import try_create as try_create_manage_public_import_contract_activity
        
        activity_payloads = try_create_manage_public_import_contract_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, resource_defs, building_type_defs, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )
        
        created_airtable_records = []
        if activity_payloads and isinstance(activity_payloads, list):
            for activity_payload in activity_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload: activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload: activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload: activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
        
        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Manage public import contract endeavor initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"manage_public_import_contract_creator for {citizen_name} returned no activity payloads or failed to create them. Payloads: {activity_payloads}")
            return {"success": False, "message": "Could not initiate 'manage_public_import_contract'.", "activity": None, "reason": "manage_public_import_contract_creation_failed_no_payloads_or_creation_error"}

    elif activity_type == "manage_logistics_service_contract":
        log.info(f"Dispatching to manage_logistics_service_contract_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.manage_logistics_service_contract_creator import try_create as try_create_manage_logistics_service_contract_activity
        
        activity_payloads = try_create_manage_logistics_service_contract_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, resource_defs, building_type_defs, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )
        
        created_airtable_records = []
        if activity_payloads and isinstance(activity_payloads, list):
            for activity_payload in activity_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload: activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload: activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload: activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}

        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Manage logistics service contract endeavor initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"manage_logistics_service_contract_creator for {citizen_name} returned no activity payloads or failed to create them. Payloads: {activity_payloads}")
            return {"success": False, "message": "Could not initiate 'manage_logistics_service_contract'.", "activity": None, "reason": "manage_logistics_service_contract_creation_failed_no_payloads_or_creation_error"}

    elif activity_type == "adjust_business_wages":
        log.info(f"Dispatching to adjust_business_wages_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.adjust_business_wages_creator import try_create as try_create_adjust_business_wages_activity
        activities_chain = try_create_adjust_business_wages_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Adjust business wages endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"adjust_business_wages_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'adjust_business_wages'.", "activity": None, "reason": "adjust_business_wages_creation_failed"}

    elif activity_type == "change_business_manager":
        log.info(f"Dispatching to change_business_manager_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.change_business_manager_creator import try_create as try_create_change_business_manager_activity
        
        # The creator's try_create now returns a boolean indicating success of creating the chain.
        # The activities are created directly in Airtable by the creator.
        # We need to fetch the first activity of the chain if successful.
        
        creation_successful = try_create_change_business_manager_activity(
            tables, 
            citizen_record_full, 
            activity_type, 
            activity_parameters or {}, 
            now_venice_dt, 
            now_utc_dt, 
            transport_api_url, 
            api_base_url
        )
        
        if creation_successful:
            # If successful, we need to find the first activity created to return its fields.
            # The first activity is likely a 'goto_location' to the business.
            # We can search for it based on citizen, type, and recent CreatedAt.
            # This is a bit indirect but necessary if the creator doesn't return the record.
            time_buffer_seconds = 5 # Look for activities created in the last 5 seconds
            search_start_time_iso = (now_utc_dt - timedelta(seconds=time_buffer_seconds)).isoformat()
            
            first_activity_formula = f"AND({{Citizen}}='{_escape_airtable_value(citizen_username)}', {{Type}}='goto_location', {{CreatedAt}} >= '{search_start_time_iso}')"
            # Add more specific details to formula if possible, e.g., part of ActivityId or Notes
            # For now, sort by CreatedAt descending and take the first one.
            
            try:
                potential_first_activities = tables['activities'].all(formula=first_activity_formula, sort=['-CreatedAt'], max_records=1)
                if potential_first_activities:
                    first_activity_fields = potential_first_activities[0]['fields']
                    return {"success": True, "message": f"Change business manager endeavor initiated. First activity: {first_activity_fields.get('Type', 'N/A')}.", "activity": first_activity_fields}
                else:
                    # This case means the creator reported success but we couldn't find the activity.
                    log.warning(f"change_business_manager_creator reported success for {citizen_name}, but could not retrieve the first activity of the chain.")
                    return {"success": True, "message": "Change business manager endeavor reported as initiated, but first activity details could not be retrieved.", "activity": None} # Success true, but no activity data
            except Exception as e_fetch_first:
                log.error(f"Error fetching first activity for change_business_manager chain for {citizen_name}: {e_fetch_first}")
                return {"success": True, "message": "Change business manager endeavor reported as initiated, but failed to retrieve first activity details due to error.", "activity": None}
        else:
            log.warning(f"change_business_manager_creator reported failure for {citizen_name}.")
            return {"success": False, "message": "Could not initiate 'change_business_manager'. Creator reported failure.", "activity": None, "reason": "change_business_manager_creation_failed_by_creator"}

    elif activity_type == "request_loan":
        log.info(f"Dispatching to request_loan_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.request_loan_creator import try_create as try_create_request_loan_activity
        activities_chain = try_create_request_loan_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Request loan endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"request_loan_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'request_loan'.", "activity": None, "reason": "request_loan_creation_failed"}

    elif activity_type == "offer_loan":
        log.info(f"Dispatching to offer_loan_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.offer_loan_creator import try_create as try_create_offer_loan_activity
        activities_chain = try_create_offer_loan_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Offer loan endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"offer_loan_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'offer_loan'.", "activity": None, "reason": "offer_loan_creation_failed"}

    elif activity_type == "manage_guild_membership":
        log.info(f"Dispatching to manage_guild_membership_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.manage_guild_membership_creator import try_create as try_create_manage_guild_membership_activity
        activities_chain = try_create_manage_guild_membership_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Manage guild membership endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"manage_guild_membership_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'manage_guild_membership'.", "activity": None, "reason": "manage_guild_membership_creation_failed"}

    elif activity_type == "buy_available_land":
        log.info(f"Dispatching to buy_available_land_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.buy_available_land_creator import try_create as try_create_buy_available_land_activity
        activities_chain = try_create_buy_available_land_activity(
            tables, citizen_record_full, activity_type, activity_parameters or {}, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Buy available land endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"buy_available_land_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'buy_available_land'.", "activity": None, "reason": "buy_available_land_creation_failed"}

    elif activity_type == "respond_to_building_bid":
        log.info(f"Dispatching to respond_to_building_bid_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.respond_to_building_bid_creator import try_create as try_create_respond_to_building_bid_activity
        activities_chain = try_create_respond_to_building_bid_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Respond to building bid endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"respond_to_building_bid_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'respond_to_building_bid'.", "activity": None, "reason": "respond_to_building_bid_creation_failed"}

    elif activity_type == "withdraw_building_bid":
        log.info(f"Dispatching to withdraw_building_bid_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.withdraw_building_bid_creator import try_create as try_create_withdraw_building_bid_activity
        activities_chain = try_create_withdraw_building_bid_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Withdraw building bid endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"withdraw_building_bid_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'withdraw_building_bid'.", "activity": None, "reason": "withdraw_building_bid_creation_failed"}

    elif activity_type == "manage_markup_buy_contract":
        log.info(f"Dispatching to manage_markup_buy_contract_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.manage_markup_buy_contract_creator import try_create as try_create_manage_markup_buy_contract_activity
        
        activity_payloads = try_create_manage_markup_buy_contract_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, resource_defs, building_type_defs, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )
        
        created_airtable_records = []
        if activity_payloads and isinstance(activity_payloads, list):
            for activity_payload in activity_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload: activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload: activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload: activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: del activity_payload['UpdatedAt']
                    
                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}
        
        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Manage markup buy contract endeavor initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"manage_markup_buy_contract_creator for {citizen_name} returned no activity payloads or failed to create them. Payloads: {activity_payloads}")
            return {"success": False, "message": "Could not initiate 'manage_markup_buy_contract'.", "activity": None, "reason": "manage_markup_buy_contract_creation_failed_no_payloads_or_creation_error"}

    elif activity_type == "manage_storage_query_contract":
        log.info(f"Dispatching to manage_storage_query_contract_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.manage_storage_query_contract_creator import try_create as try_create_manage_storage_query_contract_activity
        
        activity_payloads = try_create_manage_storage_query_contract_activity(
            tables, citizen_record_full, activity_type, 
            activity_parameters or {}, resource_defs, building_type_defs, 
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url
        )
        
        created_airtable_records = []
        if activity_payloads and isinstance(activity_payloads, list):
            for activity_payload in activity_payloads:
                if not isinstance(activity_payload, dict):
                    log.error(f"{LogColors.FAIL}Creator for {activity_type} returned non-dict item in list: {activity_payload}{LogColors.ENDC}")
                    return {"success": False, "message": f"Internal error: activity creator for {original_activity_type} returned invalid payload.", "activity": None, "reason": "invalid_creator_payload"}
                try:
                    if 'ActivityId' not in activity_payload or not activity_payload['ActivityId']:
                         activity_payload['ActivityId'] = f"{activity_payload.get('Type', 'unknown').lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
                    if 'Citizen' not in activity_payload: activity_payload['Citizen'] = citizen_username
                    if 'Status' not in activity_payload: activity_payload['Status'] = 'created'
                    if 'CreatedAt' not in activity_payload: activity_payload['CreatedAt'] = now_utc_dt.isoformat()
                    if 'UpdatedAt' in activity_payload: del activity_payload['UpdatedAt']

                    created_record = tables['activities'].create(activity_payload)
                    created_airtable_records.append(created_record)
                    log.info(f"{LogColors.SUCCESS}Successfully created activity {created_record['fields'].get('ActivityId')} of type {created_record['fields'].get('Type')} for {citizen_username}.{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create activity in Airtable for {citizen_username}. Payload: {json.dumps(activity_payload, indent=2)}. Error: {e}{LogColors.ENDC}")
                    return {"success": False, "message": f"Error creating activity chain for {original_activity_type}: {e}", "activity": None, "reason": "airtable_creation_error"}

        if created_airtable_records:
            first_created_activity_fields = created_airtable_records[0]['fields']
            message = f"Manage storage query contract endeavor initiated for {citizen_name}. First activity: {first_created_activity_fields.get('Type', 'N/A')}."
            return {"success": True, "message": message, "activity": first_created_activity_fields}
        else:
            log.warning(f"manage_storage_query_contract_creator for {citizen_name} returned no activity payloads or failed to create them. Payloads: {activity_payloads}")
            return {"success": False, "message": "Could not initiate 'manage_storage_query_contract'.", "activity": None, "reason": "manage_storage_query_contract_creation_failed_no_payloads_or_creation_error"}

    elif activity_type == "update_citizen_profile":
        log.info(f"Dispatching to update_citizen_profile_creator for {citizen_name} with params: {activity_parameters}")
        from backend.engine.activity_creators.update_citizen_profile_creator import try_create as try_create_update_citizen_profile_activity
        activities_chain = try_create_update_citizen_profile_activity(tables, citizen_record_full, activity_type, activity_parameters or {}, now_venice_dt, now_utc_dt, transport_api_url, api_base_url)
        first_activity_of_chain_fields = activities_chain[0] if activities_chain else None
        if first_activity_of_chain_fields and isinstance(first_activity_of_chain_fields, dict) and 'ActivityId' in first_activity_of_chain_fields:
            return {"success": True, "message": f"Update citizen profile endeavor initiated. First activity: {first_activity_of_chain_fields.get('Type', 'N/A')}.", "activity": first_activity_of_chain_fields}
        else:
            log.warning(f"update_citizen_profile_creator did not return valid activity. Returned: {activities_chain}")
            return {"success": False, "message": "Could not initiate 'update_citizen_profile'.", "activity": None, "reason": "update_citizen_profile_creation_failed"}

    elif activity_type == "attend_theater_performance":
        log.info(f"Dispatching to attend_theater_performance_creator for {citizen_name} with params: {activity_parameters}")
        # The creator expects citizen_record, citizen_position, resource_defs, building_type_defs, now_venice_dt, now_utc_dt, transport_api_url, api_base_url, start_time_utc_iso
        first_activity_of_chain = try_create_attend_theater_performance_activity(
            tables=tables,
            citizen_record=citizen_record_full,
            citizen_position=citizen_position,
            resource_defs=resource_defs, # Pass through
            building_type_defs=building_type_defs, # Pass through
            now_venice_dt=now_venice_dt, # Pass through
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url, # Pass through
            start_time_utc_iso=params.get("startTimeUtcIso")
        )
        if first_activity_of_chain and isinstance(first_activity_of_chain, dict) and 'fields' in first_activity_of_chain:
            return {"success": True, "message": f"Attend theater performance endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields'].get('Type', 'N/A')}.", "activity": first_activity_of_chain['fields']}
        else:
            log.warning(f"attend_theater_performance_creator did not return a valid activity record for {citizen_name}. Returned: {first_activity_of_chain}")
            return {"success": False, "message": f"Could not initiate 'attend_theater_performance' endeavor for {citizen_name}.", "activity": None, "reason": "attend_theater_performance_creation_failed"}

    elif activity_type == "drink_at_inn":
        log.info(f"Dispatching to drink_at_inn_activity_creator for {citizen_name} with params: {activity_parameters}")
        first_activity_of_chain = try_create_drink_at_inn_activity(
            tables=tables, citizen_record=citizen_record_full, citizen_position=citizen_position,
            resource_defs=resource_defs, building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt, now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url, api_base_url=api_base_url,
            start_time_utc_iso=params.get("startTimeUtcIso")
        )
        if first_activity_of_chain and isinstance(first_activity_of_chain, dict) and 'fields' in first_activity_of_chain:
            return {"success": True, "message": f"Drink at inn endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields'].get('Type', 'N/A')}.", "activity": first_activity_of_chain['fields']}
        else:
            log.warning(f"drink_at_inn_activity_creator did not return a valid activity record for {citizen_name}. Returned: {first_activity_of_chain}")
            return {"success": False, "message": f"Could not initiate 'drink_at_inn' endeavor for {citizen_name}.", "activity": None, "reason": "drink_at_inn_creation_failed"}

    elif activity_type == "use_public_bath":
        log.info(f"Dispatching to use_public_bath_creator for {citizen_name} with params: {activity_parameters}")
        first_activity_of_chain = try_create_use_public_bath_activity(
            tables=tables, citizen_record=citizen_record_full, citizen_position=citizen_position,
            resource_defs=resource_defs, building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt, now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url, api_base_url=api_base_url,
            start_time_utc_iso=params.get("startTimeUtcIso")
        )
        if first_activity_of_chain and isinstance(first_activity_of_chain, dict) and 'fields' in first_activity_of_chain:
            return {"success": True, "message": f"Use public bath endeavor initiated for {citizen_name}. First activity: {first_activity_of_chain['fields'].get('Type', 'N/A')}.", "activity": first_activity_of_chain['fields']}
        else:
            log.warning(f"use_public_bath_creator did not return a valid activity record for {citizen_name}. Returned: {first_activity_of_chain}")
            return {"success": False, "message": f"Could not initiate 'use_public_bath' endeavor for {citizen_name}.", "activity": None, "reason": "use_public_bath_creation_failed"}
    
    # Add other activity_type handlers here as needed, for example:
    # elif activity_type == "manage_public_sell_contract":
    #     # Import and call its specific creator function
    #     # from backend.engine.activity_creators.manage_public_sell_contract_creator import try_create as try_create_manage_public_sell_chain
    #     # first_activity_of_chain = try_create_manage_public_sell_chain(...)
    #     # ... handle response ...
    #     pass

    else: # Fallback for unsupported or not-yet-implemented high-level types
        supported_orchestrated_types = [
            'goto_work', # Added goto_work
            'eat', 'eat_from_inventory', 'eat_at_home', 'eat_at_tavern', 
            'leave_venice', 'seek_shelter', 'fetch_resource', 
            'initiate_building_project', 
            'send_message', 'manage_public_storage_offer', 'bid_on_land',
            'buy_listed_land', 'buy_available_land', 
            'list_land_for_sale', 'accept_land_offer', 'cancel_land_listing', 'cancel_land_offer',
            'adjust_land_lease_price', 'adjust_building_rent_price', 'adjust_building_lease_price',
            'bid_on_building', 'manage_public_sell_contract', 'manage_import_contract',
            'manage_public_import_contract', 'manage_logistics_service_contract',
            'adjust_business_wages', 'change_business_manager', 'request_loan', 'offer_loan',
            'manage_guild_membership',
            'respond_to_building_bid', 'withdraw_building_bid', 
            'manage_markup_buy_contract', 'manage_storage_query_contract', 
            'update_citizen_profile',
            'attend_theater_performance', 
            'drink_at_inn', 
            'use_public_bath' # Added new activity type
            # Add other explicitly handled types here as they are implemented in this dispatcher
        ]
        # Use original_activity_type in the error message if it was redirected
        error_activity_type_display = original_activity_type if original_activity_type != activity_type else activity_type
        
        error_message = (f"Activity type '{error_activity_type_display}' is not supported for orchestrated creation by the Python engine yet. "
                         f"Supported types are: {', '.join(supported_orchestrated_types)}.")
        if original_activity_type != activity_type:
            error_message += f" (Note: '{original_activity_type}' was redirected to '{activity_type}' which is also currently unhandled or failed). "

        return {"success": False, "message": error_message, "activity": None, "reason": "unsupported_orchestrated_activity_type"}


# --- Main Activity Processing Function ---

def process_citizen_activity(
    tables: Dict[str, Table],
    citizen_record: Dict,
    # is_night: bool, # This will be determined internally based on class schedule
    resource_defs: Dict,
    building_type_defs: Dict,
    now_venice_dt: datetime,
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str
) -> Optional[Dict]:
    """Process activity creation for a single citizen based on prioritized handlers."""
    
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_username = citizen_record['fields'].get('Username')
    citizen_airtable_id = citizen_record['id']
    
    if not citizen_custom_id: log.error(f"Missing CitizenId: {citizen_airtable_id}"); return None # Return None
    if not citizen_username: citizen_username = citizen_custom_id # Fallback

    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    citizen_social_class = citizen_record['fields'].get('SocialClass', 'Facchini') # Default if not set
    log.info(f"{LogColors.HEADER}Processing Citizen: {citizen_name} (ID: {citizen_custom_id}, User: {citizen_username}, Class: {citizen_social_class}){LogColors.ENDC}")

    citizen_position_str = citizen_record['fields'].get('Position')
    citizen_position: Optional[Dict[str, float]] = None
    try:
        if citizen_position_str: citizen_position = json.loads(citizen_position_str)
        if not citizen_position:
            point_str = citizen_record['fields'].get('Point')
            if point_str and isinstance(point_str, str):
                parts = point_str.split('_')
                if len(parts) >= 3: citizen_position = {"lat": float(parts[1]), "lng": float(parts[2])}
    except Exception: pass # Ignore parsing errors, will be handled

    if not citizen_position:
        log.info(f"{LogColors.OKBLUE}Citizen {citizen_custom_id} has no position. Assigning random.{LogColors.ENDC}")
        citizen_position = _fetch_and_assign_random_starting_position(tables, citizen_record, api_base_url)
        if citizen_position: 
            citizen_position_str = json.dumps(citizen_position)
        else: # Failed to assign random position
            log.warning(f"{LogColors.WARNING}Failed to assign random position for {citizen_name}. Cannot proceed with activity creation.{LogColors.ENDC}")
            # Create an immediate idle activity if position assignment fails critically
            idle_end_time_iso_critical = (now_utc_dt + timedelta(hours=IDLE_ACTIVITY_DURATION_HOURS)).isoformat()
            return try_create_idle_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                end_date_iso=idle_end_time_iso_critical,
                reason_message="Critical: Failed to determine or assign citizen position.",
                current_time_utc=now_utc_dt, start_time_utc_iso=None
            )

    # Determine hunger state once
    is_hungry = False
    ate_at_str = citizen_record['fields'].get('AteAt')
    if ate_at_str:
        try:
            ate_at_dt = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
            if ate_at_dt.tzinfo is None: ate_at_dt = pytz.UTC.localize(ate_at_dt)
            if (now_utc_dt - ate_at_dt) > timedelta(hours=12): is_hungry = True
        except ValueError: is_hungry = True 
    else: is_hungry = True
    citizen_record['is_hungry'] = is_hungry # Add to record for handlers

    # Define activity handlers in order of priority
    handler_args_tuple = (
        tables, citizen_record, False, resource_defs, building_type_defs,
        now_venice_dt, now_utc_dt, transport_api_url, api_base_url,
        citizen_position, citizen_custom_id, citizen_username, citizen_airtable_id, citizen_name, citizen_position_str,
        citizen_social_class
    )

    # Handlers that are always evaluated sequentially first (critical needs)
    critical_handlers = [
        (1, _handle_leave_venice, "Départ de Venise (Forestieri)"),
        (2, _handle_eat_from_inventory, "Manger depuis l'inventaire (si faim et loisir/pause)"),
        (3, _handle_eat_at_home_or_goto, "Manger à la maison / Aller à la maison (si faim et loisir/pause)"),
        (4, _handle_emergency_fishing, "Pêche d'urgence (Facchini affamé, pas en repos)"),
        (5, _handle_shop_for_food_at_retail, "Acheter nourriture au détail (si faim, loisir)"),
        (6, _handle_eat_at_tavern_or_goto, "Manger à la taverne / Aller à la taverne (si faim et loisir/pause)"),
        (10, _handle_deposit_full_inventory, "Déposer l'inventaire plein"), 
        (15, _handle_night_shelter, "Abri nocturne / Repos (selon horaire de classe)"),
        # (20, _handle_deposit_inventory_at_work, "Déposer inventaire plein au travail (si proche du travail)"), # Remplacé par _handle_deposit_full_inventory
    ]

    for priority, handler_func, description in critical_handlers:
        log.info(f"{LogColors.OKBLUE}[Prio Critique/Besoin: {priority}] {citizen_name} ({citizen_social_class}): Évaluation '{description}'...{LogColors.ENDC}")
        try:
            # These handlers do not use check_only, they are evaluated directly
            created_activity_record = handler_func(*handler_args_tuple)
            if created_activity_record:
                activity_id = created_activity_record['fields'].get('ActivityId', created_activity_record['id']) if isinstance(created_activity_record, dict) else "unknown"
                log.info(f"{LogColors.OKGREEN}{citizen_name} ({citizen_social_class}): Activité/chaîne créée par '{description}'. Première activité: {activity_id}{LogColors.ENDC}")
                return created_activity_record
        except Exception as e_handler:
            log.error(f"{LogColors.FAIL}{citizen_name} ({citizen_social_class}): ERREUR dans handler critique '{description}': {e_handler}{LogColors.ENDC}", exc_info=True)

    # If no critical activity, try weighted leisure activities if it's leisure time
    if is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        weighted_leisure_activity = _try_process_weighted_leisure_activities(*handler_args_tuple)
        if weighted_leisure_activity:
            activity_id = weighted_leisure_activity['fields'].get('ActivityId', weighted_leisure_activity['id'])
            log.info(f"{LogColors.OKGREEN}{citizen_name} ({citizen_social_class}): Activité de loisir pondérée créée. Première activité: {activity_id}{LogColors.ENDC}")
            return weighted_leisure_activity
        else: # No weighted leisure activity chosen, try sequential shopping as a fallback leisure
            log.info(f"{LogColors.OKBLUE}{citizen_name} ({citizen_social_class}): Pas d'activité de loisir pondérée. Essai shopping séquentiel.{LogColors.ENDC}")
            shopping_activity = _handle_shopping_tasks(*handler_args_tuple) # Prio 50
            if shopping_activity:
                 activity_id = shopping_activity['fields'].get('ActivityId', shopping_activity['id'])
                 log.info(f"{LogColors.OKGREEN}{citizen_name} ({citizen_social_class}): Activité de shopping créée. Première activité: {activity_id}{LogColors.ENDC}")
                 return shopping_activity


    # If not leisure time or no leisure activity created, proceed to work-related and other sequential handlers
    # This list now excludes the leisure activities handled by _try_process_weighted_leisure_activities
    # and _handle_shopping_tasks if it was tried above.
    sequential_main_handlers = [
        # Work-related tasks (check work time inside handlers)
        (30, _handle_construction_tasks, "Tâches de construction"),
        (31, _handle_production_and_general_work_tasks, "Production et tâches générales"),
        (32, _handle_fishing, "Pêche régulière (Facchini pêcheur)"),
        # Forestieri specific activities (daytime)
        (40, _handle_forestieri_daytime_tasks, "Tâches spécifiques Forestieri (jour)"),
        # Porter tasks
        (60, _handle_porter_tasks, "Tâches de porteur (au Guild Hall)"),
        # General goto_work if not at workplace during work hours
        (70, _handle_general_goto_work, "Aller au travail (général)"),
    ]
    
    # Add leisure activities not covered by weighted selection if they were missed and it's still leisure time
    # For now, _handle_shopping_tasks was the main one. If others are added, they could go here.

    for priority, handler_func, description in sequential_main_handlers:
        log.info(f"{LogColors.OKBLUE}[Prio Séquentiel: {priority}] {citizen_name} ({citizen_social_class}): Évaluation '{description}'...{LogColors.ENDC}")
        try:
            created_activity_record = handler_func(*handler_args_tuple)
            if created_activity_record:
                activity_id = created_activity_record['fields'].get('ActivityId', created_activity_record['id']) if isinstance(created_activity_record, dict) else "unknown"
                log.info(f"{LogColors.OKGREEN}{citizen_name} ({citizen_social_class}): Activité/chaîne créée par '{description}'. Première activité: {activity_id}{LogColors.ENDC}")
                return created_activity_record
        except Exception as e_handler:
            log.error(f"{LogColors.FAIL}{citizen_name} ({citizen_social_class}): ERREUR dans handler séquentiel '{description}': {e_handler}{LogColors.ENDC}", exc_info=True)

    # Fallback logic if no activity was created
    log.info(f"{LogColors.OKBLUE}{citizen_name} ({citizen_social_class}): Aucune activité spécifique. Évaluation fallback (repos ou oisiveté).{LogColors.ENDC}")
    # Try rest via _handle_night_shelter as a final fallback if appropriate
    if is_rest_time_for_class(citizen_social_class, now_venice_dt): # Check if it's actually rest time
        fallback_rest_activity = _handle_night_shelter(*handler_args_tuple)
        if fallback_rest_activity:
            log.info(f"{LogColors.OKGREEN}Fallback pour {citizen_name}: Activité 'rest' (ou chaîne) créée par _handle_night_shelter.{LogColors.ENDC}")
            return fallback_rest_activity
    
    log.info(f"{LogColors.OKBLUE}Fallback final pour {citizen_name}: Création d'une activité 'idle'.{LogColors.ENDC}")
    idle_end_time_iso = (now_utc_dt + timedelta(hours=IDLE_ACTIVITY_DURATION_HOURS)).isoformat()
    return try_create_idle_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        end_date_iso=idle_end_time_iso,
        reason_message="No specific tasks available after evaluating all priorities, or fallback rest attempt failed.",
        current_time_utc=now_utc_dt, start_time_utc_iso=None
    )

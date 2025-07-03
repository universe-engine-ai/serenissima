import logging
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

from pyairtable import Table
import requests # For fetching water graph and land details

from backend.engine.utils.activity_helpers import (
    LogColors,
    VENICE_TIMEZONE,
    get_citizen_record,
    get_land_record, # Used if we don't fetch land center via API
    _calculate_distance_meters,
    create_activity_record,
    find_path_between_buildings_or_coords # For pathing to coordinates
)
from backend.engine.utils.notification_helpers import create_notification

log = logging.getLogger(__name__)

# Night time definition (consistent with citizen_general_activities.py)
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6
HIGH_PRIORITY_GOTO = 20
AMBUSH_PRIORITY = 15

# Cache for water graph to avoid refetching on every processor run within a short time
_water_graph_cache: Optional[Dict] = None
_water_graph_last_fetch_time: Optional[datetime] = None
_WATER_GRAPH_CACHE_TTL_SECONDS = 300 # Cache for 5 minutes

def _get_seeded_random_generator(stratagem_id: str) -> random.Random:
    """Creates a seeded random number generator based on date and stratagem ID."""
    current_time_venice = datetime.now(VENICE_TIMEZONE)
    # Seed changes daily, and also if it's AM or PM part of the day (effectively changes at midday)
    day_part = "AM" if current_time_venice.hour < 12 else "PM"
    seed_string = f"{current_time_venice.strftime('%Y-%m-%d')}-{day_part}-{stratagem_id}"
    return random.Random(seed_string)

def _fetch_water_graph(api_base_url: str) -> Optional[Dict]:
    """Fetches and caches the water graph data."""
    global _water_graph_cache, _water_graph_last_fetch_time
    
    now = datetime.now(timezone.utc)
    if _water_graph_cache and _water_graph_last_fetch_time and \
       (now - _water_graph_last_fetch_time).total_seconds() < _WATER_GRAPH_CACHE_TTL_SECONDS:
        log.info(f"{LogColors.INFO}Using cached water graph data for canal mugging.{LogColors.ENDC}")
        return _water_graph_cache

    try:
        url = f"{api_base_url}/api/get-water-graph"
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}Fetching water graph from {url} for canal mugging.{LogColors.ENDC}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and isinstance(data.get("waterGraph"), dict):
            _water_graph_cache = data["waterGraph"]
            _water_graph_last_fetch_time = now
            log.info(f"{LogColors.STRATAGEM_PROCESSOR}Successfully fetched and cached water graph data.{LogColors.ENDC}")
            return _water_graph_cache
        log.error(f"{LogColors.FAIL}API error fetching water graph for canal mugging: {data.get('error', 'Unknown error')}{LogColors.ENDC}")
        return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Exception fetching water graph for canal mugging: {e}{LogColors.ENDC}")
        return None

def _get_land_center_coords(target_land_id_custom: str, api_base_url: str, tables: Dict[str, Table]) -> Optional[Dict[str, float]]:
    """Fetches land details from API to get center coordinates."""
    try:
        # Try fetching from /api/lands/{land_id} first as it might be enriched
        url_specific_land = f"{api_base_url}/api/lands/{target_land_id_custom}"
        response = requests.get(url_specific_land, timeout=10)
        if response.ok:
            land_data_api = response.json()
            if land_data_api.get("success") and isinstance(land_data_api.get("land"), dict) and land_data_api["land"].get("center"):
                log.info(f"{LogColors.STRATAGEM_PROCESSOR}Found land center via /api/lands/{target_land_id_custom}: {land_data_api['land']['center']}{LogColors.ENDC}")
                return land_data_api["land"]["center"]
        
        # Fallback: get full polygon data and find the land
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}Could not get center from /api/lands/{target_land_id_custom}. Fetching all polygons as fallback.{LogColors.ENDC}")
        polygons_url = f"{api_base_url}/api/get-polygons"
        poly_response = requests.get(polygons_url, timeout=15)
        poly_response.raise_for_status()
        poly_data = poly_response.json()
        if poly_data.get("success") and isinstance(poly_data.get("polygons"), list):
            for polygon in poly_data["polygons"]:
                if polygon.get("polygonId") == target_land_id_custom and polygon.get("center"):
                    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Found land center via /api/get-polygons for {target_land_id_custom}: {polygon['center']}{LogColors.ENDC}")
                    return polygon["center"]
        
        log.warning(f"{LogColors.WARNING}Could not find center coordinates for land {target_land_id_custom} via API.{LogColors.ENDC}")
        return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching land center for {target_land_id_custom}: {e}{LogColors.ENDC}")
        return None


def process(
    tables: Dict[str, Table], 
    stratagem_record: Dict[str, Any], 
    resource_defs: Dict[str, Any], 
    building_type_defs: Dict[str, Any], 
    api_base_url: str
) -> bool:
    """
    Processes the 'canal_mugging' stratagem.
    Determines a mugging location, and if it's nighttime, creates activities
    to go to the location and then perform the ambush.
    """
    stratagem_guid = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    executor_username = stratagem_record['fields'].get('ExecutedBy')
    
    # Parse stratagem details from Notes
    notes_str = stratagem_record['fields'].get('Notes', '{}')
    try:
        stratagem_details_from_notes = json.loads(notes_str)
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Could not parse JSON from stratagem Notes for {stratagem_guid}. Notes: {notes_str}{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f"{notes_str}\nError: Failed to parse stratagem details from Notes."})
        return False

    variant = stratagem_record['fields'].get('Variant') or stratagem_details_from_notes.get('variant', 'Standard')
    # durationDays is used by creator to set ExpiresAt. Processor checks ExpiresAt.
    target_land_id_custom = stratagem_details_from_notes.get('targetLandId_param') # Custom LandId

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing Canal Mugging Stratagem {stratagem_guid} for {executor_username}. Variant: {variant}, TargetLand: {target_land_id_custom or 'Opportunistic'}{LogColors.ENDC}")

    executor_record = get_citizen_record(tables, executor_username)
    if not executor_record:
        log.error(f"{LogColors.FAIL}Executor {executor_username} not found for stratagem {stratagem_guid}. Failing stratagem.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f"{notes_str}\nError: Executor citizen not found."})
        return False
    
    current_citizen_pos_str = executor_record['fields'].get('Position')
    current_citizen_pos: Optional[Dict[str, float]] = None
    if current_citizen_pos_str:
        try:
            current_citizen_pos = json.loads(current_citizen_pos_str)
        except json.JSONDecodeError:
            log.warning(f"{LogColors.WARNING}Could not parse current position for {executor_username}. Stratagem may fail if travel is needed.{LogColors.ENDC}")

    # 1. Determine Mugging Location
    water_graph = _fetch_water_graph(api_base_url)
    if not water_graph or not water_graph.get("waterPoints"):
        log.warning(f"{LogColors.WARNING}No water graph data available for stratagem {stratagem_guid}. Cannot determine mugging location.{LogColors.ENDC}")
        return True # Keep active, maybe data will be available later

    seeded_rng = _get_seeded_random_generator(stratagem_guid)
    selected_mugging_water_point: Optional[Dict[str, Any]] = None

    if target_land_id_custom:
        land_center_coords = _get_land_center_coords(target_land_id_custom, api_base_url, tables)
        if land_center_coords:
            water_points_with_dist = []
            for wp in water_graph["waterPoints"]:
                wp_pos = wp.get("position")
                if wp_pos and isinstance(wp_pos, dict) and 'lat' in wp_pos and 'lng' in wp_pos:
                    dist = _calculate_distance_meters(land_center_coords, wp_pos)
                    if dist != float('inf'):
                        water_points_with_dist.append((wp, dist))
            
            water_points_with_dist.sort(key=lambda x: x[1])
            closest_5_water_points = [item[0] for item in water_points_with_dist[:5]]
            if closest_5_water_points:
                selected_mugging_water_point = seeded_rng.choice(closest_5_water_points)
                log.info(f"{LogColors.STRATAGEM_PROCESSOR}Selected mugging water point near {target_land_id_custom}: {selected_mugging_water_point.get('id') if selected_mugging_water_point else 'None'}{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}No water points found near land {target_land_id_custom} for stratagem {stratagem_guid}. Falling back to opportunistic.{LogColors.ENDC}")
        else:
            log.warning(f"{LogColors.WARNING}Could not get center for land {target_land_id_custom}. Falling back to opportunistic for stratagem {stratagem_guid}.{LogColors.ENDC}")

    if not selected_mugging_water_point: # Opportunistic or fallback
        if water_graph["waterPoints"]:
            selected_mugging_water_point = seeded_rng.choice(water_graph["waterPoints"])
            log.info(f"{LogColors.STRATAGEM_PROCESSOR}Selected opportunistic mugging water point: {selected_mugging_water_point.get('id') if selected_mugging_water_point else 'None'} for stratagem {stratagem_guid}.{LogColors.ENDC}")
        else:
            log.error(f"{LogColors.FAIL}No water points in graph for opportunistic selection for stratagem {stratagem_guid}.{LogColors.ENDC}")
            return True # Keep active

    if not selected_mugging_water_point or not selected_mugging_water_point.get("position"):
        log.error(f"{LogColors.FAIL}Failed to select a valid mugging water point for stratagem {stratagem_guid}.{LogColors.ENDC}")
        return True

    mugging_coords = selected_mugging_water_point["position"]
    mugging_wp_id = selected_mugging_water_point.get("id", f"wp_{mugging_coords['lat']}_{mugging_coords['lng']}")

    # 2. Check Night Time
    now_venice_dt = datetime.now(VENICE_TIMEZONE)
    now_utc_dt = datetime.now(timezone.utc)
    current_hour_venice = now_venice_dt.hour
    is_night = current_hour_venice >= NIGHT_START_HOUR or current_hour_venice < NIGHT_END_HOUR

    if not is_night:
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}Stratagem {stratagem_guid}: Not nighttime ({current_hour_venice}h Venice). No action.{LogColors.ENDC}")
        return True # Keep active

    # Check for existing relevant activities
    activity_search_notes = f"stratagem_id: {stratagem_guid}, target_wp_id: {mugging_wp_id}"
    existing_goto_formula = f"AND({{Citizen}}='{executor_username}', {{Type}}='goto_location', {{Status}}='active', FIND('{activity_search_notes}', {{Notes}}))"
    existing_ambush_formula = f"AND({{Citizen}}='{executor_username}', {{Type}}='canal_mugging_ambush', {{Status}}='active', FIND('{activity_search_notes}', {{Notes}}))"
    
    if tables['activities'].all(formula=existing_goto_formula, max_records=1) or \
       tables['activities'].all(formula=existing_ambush_formula, max_records=1):
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}Stratagem {stratagem_guid}: Citizen {executor_username} already has an active goto or ambush activity for this target. Skipping.{LogColors.ENDC}")
        return True

    # 3. Create Activities
    if not current_citizen_pos:
        log.warning(f"{LogColors.WARNING}Stratagem {stratagem_guid}: Executor {executor_username} has no current position. Cannot create travel activity.{LogColors.ENDC}")
        return True # Keep active, maybe position will be set later

    distance_to_mugging_spot = _calculate_distance_meters(current_citizen_pos, mugging_coords)

    if distance_to_mugging_spot > 20: # Threshold to consider "at location"
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}Stratagem {stratagem_guid}: {executor_username} is not at mugging spot {mugging_wp_id}. Creating goto_location.{LogColors.ENDC}")
        
        path_data = find_path_between_buildings_or_coords(
            tables, current_citizen_pos, mugging_coords, api_base_url
        )
        if not path_data or not path_data.get("success"):
            log.warning(f"{LogColors.WARNING}Stratagem {stratagem_guid}: Could not find path for {executor_username} to mugging spot {mugging_wp_id}.{LogColors.ENDC}")
            return True # Keep active, pathing might work later

        goto_notes = {
            "purpose": "Proceed to ambush point for canal mugging",
            "stratagem_id": stratagem_guid,
            "target_wp_id": mugging_wp_id,
            "target_coordinates": mugging_coords,
            "variant": variant
        }
        create_activity_record(
            tables, executor_username, "goto_location",
            start_date_iso=now_utc_dt.isoformat(),
            end_date_iso=(now_utc_dt + timedelta(seconds=path_data.get('timing', {}).get('durationSeconds', 1800))).isoformat(),
            to_building_id=target_land_id_custom or mugging_wp_id, # Use land ID if available, else wp_id
            path_json=json.dumps(path_data.get("path", [])),
            details_json=json.dumps(goto_notes), # Store structured details
            priority_override=HIGH_PRIORITY_GOTO,
            title=f"Travel to Ambush Point ({variant})"
        )
    else: # At location
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}Stratagem {stratagem_guid}: {executor_username} is at mugging spot {mugging_wp_id}. Creating canal_mugging_ambush.{LogColors.ENDC}")
        
        end_of_night_venice: datetime
        if current_hour_venice >= NIGHT_START_HOUR:
            end_of_night_venice = now_venice_dt.replace(hour=NIGHT_END_HOUR, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else: # current_hour_venice < NIGHT_END_HOUR
            end_of_night_venice = now_venice_dt.replace(hour=NIGHT_END_HOUR, minute=0, second=0, microsecond=0)
        
        end_of_night_utc_iso = end_of_night_venice.astimezone(timezone.utc).isoformat()

        ambush_notes = {
            "stratagem_id": stratagem_guid,
            "target_wp_id": mugging_wp_id,
            "mugging_coordinates": mugging_coords,
            "variant": variant,
            "original_target_land_id": target_land_id_custom
        }
        create_activity_record(
            tables, executor_username, "canal_mugging_ambush",
            start_date_iso=now_utc_dt.isoformat(),
            end_date_iso=end_of_night_utc_iso,
            from_building_id=target_land_id_custom or mugging_wp_id, # Location context
            to_building_id=target_land_id_custom or mugging_wp_id,   # Location context
            details_json=json.dumps(ambush_notes),
            priority_override=AMBUSH_PRIORITY,
            title=f"Ambush ({variant}) at {mugging_wp_id}"
        )

    return True # Stratagem remains active

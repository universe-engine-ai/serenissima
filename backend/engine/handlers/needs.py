# backend/engine/handlers/needs.py

"""
Contains activity handlers related to a citizen's fundamental survival needs,
such as eating, finding shelter, and acquiring food.
"""

import logging
import requests
import pytz
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from pyairtable import Table
from dateutil import parser as dateutil_parser

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers from the central utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    _calculate_distance_meters,
    is_rest_time_for_class,
    is_leisure_time_for_class,
    get_path_between_points,
    get_citizen_home,
    get_building_record,
    get_closest_building_of_type,
    _get_bldg_display_name_module,
    _get_res_display_name_module,
    _get_building_position_coords,
    _find_closest_fishable_water_point,
    find_closest_fishable_water_point,
    VENICE_TIMEZONE,
    FOOD_RESOURCE_TYPES_FOR_EATING,
    SOCIAL_CLASS_SCHEDULES,
    get_citizen_current_load,
    get_citizen_effective_carry_capacity
)

# Import constants
from backend.engine.config.constants import IDLE_ACTIVITY_DURATION_HOURS

# Define module-level constants (from citizen_general_activities.py)
SOCIAL_CLASS_VALUE = {"Nobili": 4, "Cittadini": 3, "Popolani": 2, "Facchini": 1, "Forestieri": 2}
FOOD_SHOPPING_COST_ESTIMATE = 15 # Ducats, for 1-2 units of basic food
NIGHT_END_HOUR_FOR_STAY = 6

# Import specific activity creators needed by these handlers
from backend.engine.activity_creators import (
    try_create_stay_activity,
    try_create_goto_home_activity,
    try_create_travel_to_inn_activity,
    try_create_fishing_activity,
    try_create_eat_from_inventory_activity,
    try_create_eat_at_home_activity,
    try_create_eat_at_tavern_activity,
    try_create_goto_location_activity,
    try_create_leave_venice_activity
)

# Import for goto_location activity creator
from backend.engine.activity_creators.goto_location_activity_creator import try_create as try_create_goto_location_activity

# Import process_forestieri_departure_check for leave venice handler
from backend.engine.logic.forestieri_activities import process_forestieri_departure_check

# Import emergency hunger check
from backend.arsenale.fix_hunger_crisis import is_severely_hungry

log = logging.getLogger(__name__)


# ==============================================================================
# EATING HANDLERS
# ==============================================================================

def _handle_eat_from_inventory(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 2: Handles eating from inventory if hungry and it's leisure time OR EMERGENCY."""
    if not citizen_record['is_hungry']: return None
    
    # EMERGENCY: Allow eating if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions.{LogColors.ENDC}")

    log.info(f"{LogColors.OKCYAN}[Eat-Inv] {citizen_name}: Leisure time & hungry. Checking inventory.{LogColors.ENDC}")
    
    # First, collect all available food items in inventory
    available_foods = []
    for food_type_id in FOOD_RESOURCE_TYPES_FOR_EATING:
        food_name = _get_res_display_name_module(food_type_id, resource_defs)
        formula = (f"AND({{AssetType}}='citizen', {{Asset}}='{_escape_airtable_value(citizen_username)}', "
                   f"{{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='{_escape_airtable_value(food_type_id)}')")
        try:
            inventory_food = tables['resources'].all(formula=formula, max_records=1)
            if inventory_food and float(inventory_food[0]['fields'].get('Count', 0)) >= 1.0:
                available_foods.append({
                    'food_type_id': food_type_id,
                    'food_name': food_name,
                    'count': float(inventory_food[0]['fields'].get('Count', 0))
                })
                log.info(f"{LogColors.OKBLUE}[Eat-Inv] {citizen_name}: Found {inventory_food[0]['fields'].get('Count', 0)} {food_name} in inventory.{LogColors.ENDC}")
        except Exception as e:
            log.error(f"{LogColors.FAIL}[Eat-Inv] {citizen_name}: Error checking inventory for '{food_name}': {e}{LogColors.ENDC}")
    
    if not available_foods:
        log.info(f"{LogColors.WARNING}[Eat-Inv] {citizen_name}: No food found in inventory.{LogColors.ENDC}")
        return None
    
    # Try to create eat activity for the first available food type
    # Note: In future, could prioritize by food tier or other criteria
    for food_item in available_foods:
        activity_record = try_create_eat_from_inventory_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            food_item['food_type_id'], 1.0, now_utc_dt, resource_defs)
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Eat-Inv] {citizen_name}: Creating 'eat_from_inventory' for '{food_item['food_name']}' (has {food_item['count']} units).{LogColors.ENDC}")
            return activity_record
        else:
            log.warning(f"{LogColors.WARNING}[Eat-Inv] {citizen_name}: Failed to create eat activity for '{food_item['food_name']}', trying next food type.{LogColors.ENDC}")
    
    log.error(f"{LogColors.FAIL}[Eat-Inv] {citizen_name}: Failed to create eat activity for any available food type.{LogColors.ENDC}")
    return None

def _handle_eat_at_home_or_goto(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 3: Handles eating at home or going home to eat if hungry and it's leisure time OR EMERGENCY."""
    if not citizen_record['is_hungry']: return None
    
    # EMERGENCY: Allow eating if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions.{LogColors.ENDC}")

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
    """Prio 6: Handles eating at tavern or going to tavern to eat if hungry and it's leisure time OR EMERGENCY."""
    # EMERGENCY: Allow eating if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions.{LogColors.ENDC}")
    if not citizen_position: return None

    citizen_ducats = float(citizen_record['fields'].get('Ducats', 0))
    # Keep a very basic ducat check, actual affordability checked against API response
    if citizen_ducats < 1: # Must have at least 1 ducat to consider buying food
        log.info(f"{LogColors.OKBLUE}[Faim - Externe] Citoyen {citizen_name} a moins de 1 Ducat. Ne peut pas acheter à manger.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.OKCYAN}[Faim - Externe] Citoyen {citizen_name} ({citizen_social_class}): Affamé et en période de loisirs. Appel API /get-eating-options.{LogColors.ENDC}")

    eating_options_response = None
    response = None
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

# ==============================================================================
# FOOD ACQUISITION HANDLERS
# ==============================================================================

def _handle_emergency_fishing(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
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

def _handle_shop_for_food_at_retail(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 20 (was 5): Handles shopping for food at retail_food if hungry, has home, and it's leisure time OR EMERGENCY."""
    # This is now a lower priority than general work/production, happens during leisure.
    if not citizen_record['is_hungry']: return None
    
    # EMERGENCY: Allow shopping if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions for food shopping.{LogColors.ENDC}")
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

# ==============================================================================
# SHELTER / REST HANDLER
# ==============================================================================

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
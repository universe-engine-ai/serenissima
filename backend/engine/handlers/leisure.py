# backend/engine/handlers/leisure.py

"""
Contains activity handlers related to a citizen's leisure time,
entertainment, social activities during free time, and cultural pursuits.
"""

import logging
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from pyairtable import Table

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers from the central utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    _calculate_distance_meters,
    is_leisure_time_for_class,
    get_citizen_home,
    get_building_record,
    get_closest_building_of_type,
    _get_bldg_display_name_module,
    _get_res_display_name_module,
    VENICE_TIMEZONE,
    SOCIAL_CLASS_SCHEDULES
)

# Import specific activity creators needed by these handlers
from backend.engine.activity_creators import (
    try_create_read_book_activity,
    try_create_attend_theater_performance_activity,
    try_create_drink_at_inn_activity,
    try_create_use_public_bath_activity,
    try_create_work_on_art_activity,
    try_create_goto_location_activity,
    try_create_attend_mass_activity,
    find_nearest_church,
    try_create_pray_activity
)

# Import social activity creators
from backend.engine.activity_creators.spread_rumor_activity_creator import try_create as try_create_spread_rumor_activity
from backend.engine.activity_creators import try_create_send_message_activity as try_create_send_message_chain

# Import governance handler
from backend.engine.handlers.governance import _handle_governance_participation
# Import KinOS-enhanced governance handler (will use this if KinOS is configured)
try:
    from backend.engine.handlers.governance_kinos import _handle_governance_participation_kinos
    KINOS_GOVERNANCE_AVAILABLE = True
except ImportError:
    KINOS_GOVERNANCE_AVAILABLE = False

log = logging.getLogger(__name__)


# ==============================================================================
# LEISURE ACTIVITY HANDLERS
# ==============================================================================

def _handle_attend_mass(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Handles attending mass at the nearest church during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Mass] {citizen_name}: No position available.{LogColors.ENDC}")
        return None
    
    log.info(f"{LogColors.OKCYAN}[Mass] {citizen_name}: Looking for a church to attend mass.{LogColors.ENDC}")
    
    # Find the nearest church
    nearest_church = find_nearest_church(tables, citizen_position)
    if not nearest_church:
        log.info(f"{LogColors.WARNING}[Mass] {citizen_name}: No church found nearby.{LogColors.ENDC}")
        return None
    
    # Create attend mass activity
    activity_record = try_create_attend_mass_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=citizen_position,
        church_building_record=nearest_church,
        now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url
    )
    
    if activity_record:
        church_name = nearest_church['fields'].get('Name', 'church')
        log.info(f"{LogColors.OKGREEN}[Mass] {citizen_name}: Creating 'attend_mass' activity at {church_name}.{LogColors.ENDC}")
    
    return activity_record

def _handle_pray(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Handles praying at a church during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Pray] {citizen_name}: No position available.{LogColors.ENDC}")
        return None
    
    log.info(f"{LogColors.OKCYAN}[Pray] {citizen_name}: Looking for a quiet place to pray.{LogColors.ENDC}")
    
    # Create pray activity
    activity_record = try_create_pray_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=citizen_position,
        resource_defs=resource_defs,
        building_type_defs=building_type_defs,
        now_venice_dt=now_venice_dt,
        now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url,
        api_base_url=api_base_url
    )
    
    if activity_record:
        log.info(f"{LogColors.OKGREEN}[Pray] {citizen_name}: Creating 'pray' activity.{LogColors.ENDC}")
    
    return activity_record

def _handle_work_on_art(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 25: Handles working on art for Artisti during leisure time."""
    if citizen_social_class != "Artisti": return None
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Art] {citizen_name}: Artisti checking for art creation opportunity.{LogColors.ENDC}")
    
    # Check if already working on art
    current_artwork_formula = f"AND({{Artist}}='{_escape_airtable_value(citizen_username)}', {{Finished}}=FALSE())"
    current_artworks = tables['artworks'].all(formula=current_artwork_formula, max_records=1)
    
    if current_artworks:
        log.info(f"{LogColors.WARNING}[Art] {citizen_name}: Already working on an artwork.{LogColors.ENDC}")
        return None
    
    activity_record = try_create_work_on_art_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        now_utc_dt
    )
    if activity_record:
        log.info(f"{LogColors.OKGREEN}[Art] {citizen_name}: Creating 'work_on_art' activity.{LogColors.ENDC}")
    return activity_record

def _handle_attend_theater_performance(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio L2: Handles attending theater performances during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Theater] {citizen_name}: Checking for theater performances.{LogColors.ENDC}")
    
    # Get theaters with active performances
    theater_type = building_type_defs.get('theater')
    if not theater_type:
        return None
    
    theater_formula = "AND({Type}='theater', {Status}='active', {CurrentRepresentation}!='')"
    active_theaters = tables['buildings'].all(formula=theater_formula)
    
    if not active_theaters:
        log.info(f"{LogColors.WARNING}[Theater] {citizen_name}: No active theater performances.{LogColors.ENDC}")
        return None
    
    # Check wallet balance
    citizen_ducats = float(citizen_record.get('ducats', 0))
    ticket_cost = 20
    
    if citizen_ducats < ticket_cost:
        log.info(f"{LogColors.WARNING}[Theater] {citizen_name}: Cannot afford theater ticket ({ticket_cost} ducats).{LogColors.ENDC}")
        return None
    
    # Find closest theater
    if not citizen_position:
        log.info(f"{LogColors.WARNING}[Theater] {citizen_name}: No position, cannot find theater.{LogColors.ENDC}")
        return None
    
    closest_theater = get_closest_building_of_type(
        tables, citizen_position, 'theater', 
        transport_api_url, building_type_defs,
        extra_filter="{CurrentRepresentation}!=''"
    )
    
    if not closest_theater:
        return None
    
    activity_record = try_create_attend_theater_performance_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        closest_theater['id'], now_utc_dt
    )
    
    if activity_record:
        theater_name = _get_bldg_display_name_module(closest_theater, building_type_defs)
        log.info(f"{LogColors.OKGREEN}[Theater] {citizen_name}: Creating 'attend_theater_performance' at {theater_name}.{LogColors.ENDC}")
    
    return activity_record

def _handle_drink_at_inn(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio L3: Handles drinking at inn during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Drink] {citizen_name}: Checking for inn drinking opportunity.{LogColors.ENDC}")
    
    # Check if recently drank at inn (prevent drinking loops)
    recent_drinking_formula = (f"AND({{CitizenId}}='{citizen_airtable_id}', "
                              f"{{Type}}='drink_at_inn', "
                              f"{{Status}}='processed', "
                              f"DATETIME_DIFF(NOW(), {{EndDate}}, 'hours') < 3)")
    
    try:
        recent_drinks = tables['activities'].all(formula=recent_drinking_formula, max_records=1)
        if recent_drinks:
            log.info(f"{LogColors.WARNING}[Drink] {citizen_name}: Recently drank at inn. Taking a break from drinking.{LogColors.ENDC}")
            return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Drink] {citizen_name}: Error checking recent drinks: {e}{LogColors.ENDC}")
    
    # Check wallet balance
    citizen_ducats = float(citizen_record.get('ducats', 0))
    drink_cost = 10
    
    if citizen_ducats < drink_cost:
        log.info(f"{LogColors.WARNING}[Drink] {citizen_name}: Cannot afford drinks ({drink_cost} ducats).{LogColors.ENDC}")
        return None
    
    # Find closest inn that isn't overcrowded
    if not citizen_position:
        log.info(f"{LogColors.WARNING}[Drink] {citizen_name}: No position, cannot find inn.{LogColors.ENDC}")
        return None
    
    # Get all inns
    all_inns = tables['buildings'].all(formula="{Type}='inn'")
    valid_inns = []
    
    for inn in all_inns:
        inn_position_str = inn['fields'].get('Position', '')
        if inn_position_str:
            # Check capacity
            citizens_at_inn_formula = f"{{Position}}='{_escape_airtable_value(inn_position_str)}'"
            try:
                citizens_at_inn = tables['citizens'].all(formula=citizens_at_inn_formula)
                if len(citizens_at_inn) < 10:
                    valid_inns.append(inn)
                else:
                    log.info(f"{LogColors.WARNING}[Drink] {inn['fields'].get('Name', 'Inn')} is at capacity (10 citizens).{LogColors.ENDC}")
            except:
                valid_inns.append(inn)  # Include if we can't check
    
    if not valid_inns:
        log.info(f"{LogColors.WARNING}[Drink] {citizen_name}: All inns are at capacity.{LogColors.ENDC}")
        return None
    
    # Find closest valid inn
    closest_inn = None
    min_distance = float('inf')
    for inn in valid_inns:
        inn_pos = _get_building_position_coords(inn)
        if inn_pos:
            distance = _calculate_distance_meters(citizen_position, inn_pos)
            if distance < min_distance:
                min_distance = distance
                closest_inn = inn
    
    if not closest_inn:
        return None
    
    activity_record = try_create_drink_at_inn_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=citizen_position,
        resource_defs=resource_defs,
        building_type_defs=building_type_defs,
        now_venice_dt=now_venice_dt,
        now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url,
        api_base_url=api_base_url
    )
    
    if activity_record:
        inn_name = _get_bldg_display_name_module(closest_inn, building_type_defs)
        log.info(f"{LogColors.OKGREEN}[Drink] {citizen_name}: Creating 'drink_at_inn' at {inn_name}.{LogColors.ENDC}")
    
    return activity_record

def _handle_use_public_bath(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio L4: Handles using public bath during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Bath] {citizen_name}: Checking for public bath usage.{LogColors.ENDC}")
    
    # Check wallet balance
    citizen_ducats = float(citizen_record.get('ducats', 0))
    bath_cost = 5
    
    if citizen_ducats < bath_cost:
        log.info(f"{LogColors.WARNING}[Bath] {citizen_name}: Cannot afford public bath ({bath_cost} ducats).{LogColors.ENDC}")
        return None
    
    # Find closest public bath
    if not citizen_position:
        log.info(f"{LogColors.WARNING}[Bath] {citizen_name}: No position, cannot find bath.{LogColors.ENDC}")
        return None
    
    closest_bath = get_closest_building_of_type(
        tables, citizen_position, 'public_bath', 
        transport_api_url, building_type_defs
    )
    
    if not closest_bath:
        return None
    
    activity_record = try_create_use_public_bath_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        closest_bath['id'], now_utc_dt
    )
    
    if activity_record:
        bath_name = _get_bldg_display_name_module(closest_bath, building_type_defs)
        log.info(f"{LogColors.OKGREEN}[Bath] {citizen_name}: Creating 'use_public_bath' at {bath_name}.{LogColors.ENDC}")
    
    return activity_record

def _handle_read_book(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio L5: Handles reading books during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Read] {citizen_name}: Checking for book reading opportunity.{LogColors.ENDC}")
    
    # Check inventory for books
    books_formula = (f"AND({{AssetType}}='citizen', {{Asset}}='{_escape_airtable_value(citizen_username)}', "
                     f"{{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='books')")
    
    try:
        books_in_inventory = tables['resources'].all(formula=books_formula, max_records=1)
        if not books_in_inventory or float(books_in_inventory[0]['fields'].get('Count', 0)) < 1.0:
            log.info(f"{LogColors.WARNING}[Read] {citizen_name}: No books in inventory.{LogColors.ENDC}")
            return None
        
        activity_record = try_create_read_book_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            now_utc_dt
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Read] {citizen_name}: Creating 'read_book' activity.{LogColors.ENDC}")
        
        return activity_record
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Read] {citizen_name}: Error checking books: {e}{LogColors.ENDC}")
        return None

def _handle_shopping_tasks(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 50: Handles general shopping tasks during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Shop] {citizen_name}: Evaluating shopping opportunities.{LogColors.ENDC}")
    
    # Check wallet balance
    citizen_ducats = float(citizen_record.get('ducats', 0))
    if citizen_ducats < 50:
        log.info(f"{LogColors.WARNING}[Shop] {citizen_name}: Insufficient funds for shopping.{LogColors.ENDC}")
        return None
    
    if not citizen_position:
        return None
    
    # Priority shopping list
    shopping_priorities = [
        ('books', 100, ['printing_house', 'market_stall']),
        ('candles', 50, ['market_stall', 'merceria']),
        ('olive_oil', 30, ['market_stall', 'oil_press']),
        ('wine', 40, ['inn', 'wine_cellar']),
    ]
    
    for resource_type, max_cost, shop_types in shopping_priorities:
        # Check if already have the resource
        inv_formula = (f"AND({{AssetType}}='citizen', {{Asset}}='{_escape_airtable_value(citizen_username)}', "
                       f"{{Owner}}='{_escape_airtable_value(citizen_username)}', {{Type}}='{resource_type}')")
        
        try:
            existing_resource = tables['resources'].all(formula=inv_formula, max_records=1)
            if existing_resource and float(existing_resource[0]['fields'].get('Count', 0)) >= 1.0:
                continue
            
            # Find shop selling this resource
            for shop_type in shop_types:
                shop = get_closest_building_of_type(
                    tables, citizen_position, shop_type,
                    transport_api_url, building_type_defs
                )
                
                if shop:
                    # Check if shop has stock
                    stock_formula = (f"AND({{AssetType}}='building', {{Asset}}='{shop['fields']['CustomId']}', "
                                     f"{{Type}}='{resource_type}', {{Count}}>0)")
                    shop_stock = tables['resources'].all(formula=stock_formula, max_records=1)
                    
                    if shop_stock:
                        # Create shopping activity
                        activity_record = try_create_goto_location_activity(
                            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                            shop['fields']['CustomId'], 'shop', now_utc_dt
                        )
                        
                        if activity_record:
                            shop_name = _get_bldg_display_name_module(shop, building_type_defs)
                            log.info(f"{LogColors.OKGREEN}[Shop] {citizen_name}: Going to {shop_name} to buy {resource_type}.{LogColors.ENDC}")
                            return activity_record
                        
        except Exception as e:
            log.error(f"{LogColors.FAIL}[Shop] {citizen_name}: Error checking {resource_type}: {e}{LogColors.ENDC}")
            continue
    
    return None

# ==============================================================================
# LEISURE ACTIVITY SELECTION SYSTEM
# ==============================================================================

def _try_process_weighted_leisure_activities(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Processes weighted leisure activities during leisure time.
    Returns the first successfully created activity, or None if none are chosen or created.
    """
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKBLUE}[Leisure] {citizen_name}: Processing weighted leisure activities.{LogColors.ENDC}")
    
    # Define leisure activities with their weights and check_only functions
    # Higher weight = more likely to be chosen
    # Base weights that can be modified by social class
    base_weights = {
        "Work on Art (Artisti)": 20,
        "Attend Theater": 15,
        "Drink at Inn": 25,
        "Use Public Bath": 10,
        "Read Book": 15,
        "Attend Mass": 20,
        "Pray": 15,
        "Send Message": 10,
        "Spread Rumor": 5,
        "Participate in Governance": 8,  # Base weight for governance activities
    }
    
    # Modify weights based on social class
    # Renaissance Venice social classes: Nobili, Clero, Cittadini, Artisti, Popolani, Facchini, Scientisti
    class_weight_modifiers = {
        "Nobili": {  # Nobility - cultured, wealthy, politically active
            "Attend Theater": 35,
            "Read Book": 30,
            "Drink at Inn": 15,  # More refined social drinking
            "Use Public Bath": 5,  # Would have private baths
            "Work on Art (Artisti)": 0,  # Would commission, not create
            "Pray": 10,
            "Attend Mass": 15,
            "Send Message": 20,  # Political correspondence
            "Spread Rumor": 15,  # Political intrigue
            "Participate in Governance": 25,  # High political engagement
        },
        "Clero": {  # Clergy - religious, educated, moral
            "Pray": 45,  # Significantly higher chance for clergy
            "Attend Mass": 35,  # Also higher for mass
            "Read Book": 25,  # Religious texts and education
            "Attend Theater": 5,  # Less worldly entertainment
            "Drink at Inn": 5,  # Much lower chance for drinking
            "Use Public Bath": 8,
            "Work on Art (Artisti)": 0,
            "Send Message": 15,
            "Spread Rumor": 2,  # Gossip is unseemly
            "Participate in Governance": 10,  # Moderate, moral guidance role
        },
        "Cittadini": {  # Citizens - educated, bureaucratic, business-oriented
            "Read Book": 20,
            "Attend Theater": 20,
            "Drink at Inn": 25,  # Business and social meetings
            "Use Public Bath": 10,
            "Work on Art (Artisti)": 0,
            "Pray": 15,
            "Attend Mass": 20,
            "Send Message": 20,  # Business and civic correspondence
            "Spread Rumor": 15,  # Market and civic gossip
            "Participate in Governance": 20,  # High civic engagement
        },
        "Artisti": {  # Artists - creative, bohemian
            "Work on Art (Artisti)": 40,  # Primary activity
            "Attend Theater": 25,  # Appreciate performances
            "Drink at Inn": 30,  # Bohemian lifestyle
            "Read Book": 15,
            "Use Public Bath": 10,
            "Pray": 8,
            "Attend Mass": 10,
            "Send Message": 10,
            "Spread Rumor": 15,
            "Participate in Governance": 12,  # Moderate, cultural issues
        },
        "Popolani": {  # Common workers - practical, social
            "Drink at Inn": 30,
            "Attend Theater": 10,  # Occasional treat
            "Read Book": 5,  # Lower literacy
            "Use Public Bath": 20,
            "Work on Art (Artisti)": 0,
            "Pray": 15,
            "Attend Mass": 25,
            "Send Message": 5,  # Less writing
            "Spread Rumor": 25,  # Neighborhood gossip
            "Participate in Governance": 6,  # Low but present when desperate
        },
        "Facchini": {  # Laborers - hardworking, simple pleasures
            "Drink at Inn": 40,  # Main leisure activity
            "Attend Theater": 5,  # Rare and expensive
            "Read Book": 2,  # Very low literacy
            "Use Public Bath": 25,  # Important for hygiene
            "Work on Art (Artisti)": 0,
            "Pray": 10,
            "Attend Mass": 20,
            "Send Message": 2,  # Rarely write
            "Spread Rumor": 30,  # Street gossip
            "Participate in Governance": 4,  # Rarely engage unless desperate
        },
        "Scientisti": {  # Scientists - intellectual, studious
            "Read Book": 40,  # Primary leisure activity
            "Attend Theater": 15,  # Some cultural interest
            "Drink at Inn": 10,  # Occasional social drinking
            "Use Public Bath": 10,
            "Work on Art (Artisti)": 0,
            "Pray": 20,  # Balance of faith and reason
            "Attend Mass": 20,
            "Send Message": 15,  # Academic correspondence
            "Spread Rumor": 5,  # Less interested in gossip
            "Participate in Governance": 15,  # Engaged for progress issues
        }
    }
    
    # Apply class-specific modifiers if they exist
    weights = base_weights.copy()
    if citizen_social_class in class_weight_modifiers:
        for activity, new_weight in class_weight_modifiers[citizen_social_class].items():
            if activity in weights:
                weights[activity] = new_weight
    
    leisure_activities = [
        # (weight, handler_func, description, check_only)
        (weights["Work on Art (Artisti)"], _handle_work_on_art, "Work on Art (Artisti)", True),
        (weights["Attend Theater"], _handle_attend_theater_performance, "Attend Theater", True),
        (weights["Drink at Inn"], _handle_drink_at_inn, "Drink at Inn", True),
        (weights["Use Public Bath"], _handle_use_public_bath, "Use Public Bath", True),
        (weights["Read Book"], _handle_read_book, "Read Book", True),
        (weights["Attend Mass"], _handle_attend_mass, "Attend Mass", True),
        (weights["Pray"], _handle_pray, "Pray", True),
        (weights["Send Message"], _handle_send_leisure_message, "Send Message", True),
        (weights["Spread Rumor"], _handle_spread_rumor, "Spread Rumor", True),
    ]
    
    # Use KinOS-enhanced governance if available and configured
    governance_handler = _handle_governance_participation
    if KINOS_GOVERNANCE_AVAILABLE and os.getenv("KINOS_API_KEY"):
        governance_handler = _handle_governance_participation_kinos
        log.debug(f"[Leisure] Using KinOS-enhanced governance for {citizen_name}")
    
    leisure_activities.append(
        (weights["Participate in Governance"], governance_handler, "Participate in Governance", True)
    )
    
    # Filter activities based on check_only evaluation
    available_activities = []
    total_weight = 0
    
    for weight, handler_func, description, use_check_only in leisure_activities:
        # For check_only handlers, we need to implement the check logic
        # For now, we'll add all activities and let the actual handler decide
        available_activities.append((weight, handler_func, description))
        total_weight += weight
    
    if not available_activities:
        log.info(f"{LogColors.WARNING}[Leisure] {citizen_name}: No leisure activities available.{LogColors.ENDC}")
        return None
    
    # Weighted random selection
    rand_value = random.uniform(0, total_weight)
    cumulative_weight = 0
    
    for weight, handler_func, description in available_activities:
        cumulative_weight += weight
        if rand_value <= cumulative_weight:
            log.info(f"{LogColors.OKBLUE}[Leisure] {citizen_name}: Selected '{description}' for leisure activity.{LogColors.ENDC}")
            try:
                activity_record = handler_func(
                    tables, citizen_record, is_night, resource_defs, building_type_defs,
                    now_venice_dt, now_utc_dt, transport_api_url, api_base_url,
                    citizen_position, citizen_custom_id, citizen_username, citizen_airtable_id, 
                    citizen_name, citizen_position_str, citizen_social_class
                )
                if activity_record:
                    return activity_record
                else:
                    log.info(f"{LogColors.WARNING}[Leisure] {citizen_name}: '{description}' returned no activity.{LogColors.ENDC}")
            except Exception as e:
                log.error(f"{LogColors.FAIL}[Leisure] {citizen_name}: Error in '{description}': {e}{LogColors.ENDC}")
            break
    
    return None

# ==============================================================================
# SOCIAL INTERACTION HANDLERS
# ==============================================================================

def _handle_send_leisure_message(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio L6: Handles sending messages during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Message] {citizen_name}: Checking for message sending opportunity.{LogColors.ENDC}")
    
    # Check if recently sent a message
    recent_activity_formula = (f"AND({{CitizenId}}='{citizen_airtable_id}', "
                               f"{{Type}}='send_message', "
                               f"{{Status}}='processed', "
                               f"DATETIME_DIFF(NOW(), {{EndDate}}, 'hours') < 24)")
    
    try:
        recent_messages = tables['activities'].all(formula=recent_activity_formula, max_records=1)
        if recent_messages:
            log.info(f"{LogColors.WARNING}[Message] {citizen_name}: Recently sent a message.{LogColors.ENDC}")
            return None
        
        # Get relationships to potentially message
        relationships_formula = f"OR({{Citizen1}}='{citizen_username}', {{Citizen2}}='{citizen_username}')"
        relationships = tables['relationships'].all(formula=relationships_formula)
        
        if not relationships:
            return None
        
        # Filter for strong relationships
        strong_relationships = [
            r for r in relationships 
            if float(r['fields'].get('Strength', 0)) > 0.5
        ]
        
        if not strong_relationships:
            return None
        
        # Pick a random relationship
        import random
        relationship = random.choice(strong_relationships)
        
        # Determine recipient
        if relationship['fields']['Citizen1'] == citizen_username:
            recipient = relationship['fields']['Citizen2']
        else:
            recipient = relationship['fields']['Citizen1']
        
        activity_record = try_create_send_message_chain(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            recipient, 'social', now_utc_dt
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Message] {citizen_name}: Creating 'send_message' to {recipient}.{LogColors.ENDC}")
        
        return activity_record
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Message] {citizen_name}: Error checking messages: {e}{LogColors.ENDC}")
        return None

def _handle_spread_rumor(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio L7: Handles spreading rumors during leisure time."""
    if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Rumor] {citizen_name}: Checking for rumor spreading opportunity.{LogColors.ENDC}")
    
    if not citizen_position:
        return None
    
    # Check if recently spread a rumor
    recent_rumor_formula = (f"AND({{CitizenId}}='{citizen_airtable_id}', "
                            f"{{Type}}='spread_rumor', "
                            f"DATETIME_DIFF(NOW(), {{Created}}, 'hours') < 48)")
    
    try:
        recent_rumors = tables['activities'].all(formula=recent_rumor_formula, max_records=1)
        if recent_rumors:
            log.info(f"{LogColors.WARNING}[Rumor] {citizen_name}: Recently spread a rumor.{LogColors.ENDC}")
            return None
        
        # Find nearby citizens
        all_citizens = tables['citizens'].all(formula="{IsActive}=TRUE()")
        nearby_citizens = []
        
        for other_citizen in all_citizens:
            if other_citizen['fields']['username'] == citizen_username:
                continue
            
            other_pos = other_citizen['fields'].get('Position')
            if not other_pos:
                continue
            
            try:
                other_x = float(other_pos.split(',')[0])
                other_y = float(other_pos.split(',')[1])
                distance = _calculate_distance_meters(
                    (citizen_position['x'], citizen_position['y']),
                    (other_x, other_y)
                )
                
                if distance < 50:  # Within 50 meters
                    nearby_citizens.append(other_citizen['fields']['username'])
                    
            except Exception:
                continue
        
        if not nearby_citizens:
            log.info(f"{LogColors.WARNING}[Rumor] {citizen_name}: No nearby citizens for rumors.{LogColors.ENDC}")
            return None
        
        # Create rumor activity
        activity_record = try_create_spread_rumor_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            'market_gossip', nearby_citizens, now_utc_dt
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Rumor] {citizen_name}: Creating 'spread_rumor' activity.{LogColors.ENDC}")
        
        return activity_record
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Rumor] {citizen_name}: Error spreading rumor: {e}{LogColors.ENDC}")
        return None
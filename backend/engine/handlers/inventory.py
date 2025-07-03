# backend/engine/handlers/inventory.py

"""
Contains activity handlers related to inventory management,
including depositing items, storage management, and resource handling.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Optional, Any, List, Tuple
from pyairtable import Table

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers from the central utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    get_citizen_current_load,
    get_citizen_effective_carry_capacity,
    get_citizen_home,
    get_citizen_workplace,
    get_building_record,
    _calculate_distance_meters,
    _get_bldg_display_name_module,
    VENICE_TIMEZONE
)

# Import specific activity creators needed by these handlers
from backend.engine.activity_creators import (
    try_create_deposit_inventory_orchestrator,
    try_create_manage_public_storage_offer_activity
)

log = logging.getLogger(__name__)


# ==============================================================================
# INVENTORY MANAGEMENT HANDLERS
# ==============================================================================

def _handle_deposit_full_inventory(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Handles depositing inventory when carrying capacity is near full.
    This can happen at any time and takes priority over many other activities.
    """
    # Check current load
    current_load = get_citizen_current_load(tables, citizen_username)
    carry_capacity = get_citizen_effective_carry_capacity(citizen_record)
    
    # Use configurable thresholds
    storage_threshold = const.STORAGE_FULL_THRESHOLD  # e.g., 0.8
    min_load = const.MINIMUM_LOAD_FOR_DEPOSIT  # e.g., 5.0
    
    if current_load < min_load:
        return None
    
    if current_load / carry_capacity < storage_threshold:
        return None
    
    log.info(f"{LogColors.OKCYAN}[Deposit] {citizen_name}: Inventory near full ({current_load:.1f}/{carry_capacity:.1f}). Need to deposit.{LogColors.ENDC}")
    
    # Try to create deposit orchestrator activity
    activity_chain = try_create_deposit_inventory_orchestrator(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=citizen_position,
        resource_defs=resource_defs,
        building_type_defs=building_type_defs,
        now_utc_dt=now_utc_dt,
        transport_api_url=transport_api_url,
        api_base_url=api_base_url
    )
    
    if activity_chain:
        log.info(f"{LogColors.OKGREEN}[Deposit] {citizen_name}: Created deposit inventory orchestrator chain.{LogColors.ENDC}")
        return activity_chain
    
    return None

def _handle_deposit_inventory_at_work(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    DEPRECATED: This handler has been replaced by _handle_deposit_full_inventory
    which uses the new deposit orchestrator system.
    """
    log.warning(f"{LogColors.WARNING}[Deposit] _handle_deposit_inventory_at_work is deprecated. Use _handle_deposit_full_inventory.{LogColors.ENDC}")
    return None

def _handle_manage_public_storage_offer(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Handles managing public storage offers for citizens who run warehouses.
    This creates or updates storage contracts based on warehouse capacity.
    """
    # Check if citizen runs any warehouses
    run_buildings_formula = f"{{RunBy}}='{_escape_airtable_value(citizen_username)}'"
    try:
        run_buildings = tables['buildings'].all(formula=run_buildings_formula)
        warehouses = [b for b in run_buildings if b['fields'].get('Category') == 'storage']
        
        if not warehouses:
            return None
            
        log.info(f"{LogColors.OKCYAN}[Storage] {citizen_name}: Runs {len(warehouses)} warehouse(s). Checking storage contracts.{LogColors.ENDC}")
        
        # Try to create manage storage offer chain
        activity_chain = try_create_manage_public_storage_offer_activity(
            tables=tables,
            citizen_id=citizen_custom_id,
            citizen_username=citizen_username,
            citizen_airtable_id=citizen_airtable_id,
            warehouses=warehouses,
            now_utc_dt=now_utc_dt,
            resource_defs=resource_defs
        )
        
        if activity_chain:
            log.info(f"{LogColors.OKGREEN}[Storage] {citizen_name}: Created manage storage offer chain.{LogColors.ENDC}")
            return activity_chain
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Storage] {citizen_name}: Error checking warehouses: {e}{LogColors.ENDC}")
    
    return None

# ==============================================================================
# HELPER FUNCTIONS FOR INVENTORY CALCULATIONS
# ==============================================================================

def calculate_optimal_deposit_location(
    tables: Dict[str, Table], 
    citizen_username: str,
    citizen_position: Dict[str, float],
    building_type_defs: Dict
) -> Optional[Dict]:
    """
    Calculates the optimal location to deposit inventory based on:
    - Distance from current position
    - Available storage capacity
    - Building ownership/access rights
    """
    potential_locations = []
    
    # Check home
    home = get_citizen_home(tables, citizen_username)
    if home and home['fields'].get('StorageCapacity', 0) > 0:
        home_pos = json.loads(home['fields'].get('Position', '{}'))
        if home_pos:
            distance = _calculate_distance_meters(citizen_position, home_pos)
            potential_locations.append({
                'building': home,
                'type': 'home',
                'distance': distance,
                'priority': 1  # Highest priority
            })
    
    # Check workplace
    workplace = get_citizen_workplace(tables, citizen_username)
    if workplace and workplace['fields'].get('StorageCapacity', 0) > 0:
        work_pos = json.loads(workplace['fields'].get('Position', '{}'))
        if work_pos:
            distance = _calculate_distance_meters(citizen_position, work_pos)
            potential_locations.append({
                'building': workplace,
                'type': 'workplace',
                'distance': distance,
                'priority': 2
            })
    
    # Check owned warehouses
    owned_formula = f"AND({{Owner}}='{_escape_airtable_value(citizen_username)}', {{Category}}='storage')"
    try:
        owned_warehouses = tables['buildings'].all(formula=owned_formula)
        for warehouse in owned_warehouses:
            wh_pos = json.loads(warehouse['fields'].get('Position', '{}'))
            if wh_pos:
                distance = _calculate_distance_meters(citizen_position, wh_pos)
                potential_locations.append({
                    'building': warehouse,
                    'type': 'owned_warehouse',
                    'distance': distance,
                    'priority': 3
                })
    except Exception as e:
        log.error(f"Error finding owned warehouses: {e}")
    
    # Sort by priority first, then by distance
    if potential_locations:
        potential_locations.sort(key=lambda x: (x['priority'], x['distance']))
        return potential_locations[0]['building']
    
    return None
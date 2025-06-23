# backend/engine/handlers/management.py

"""
Contains activity handlers related to business and building management,
including checking business status, managing contracts, and administrative tasks.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from pyairtable import Table

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers from the central utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    is_work_time,
    get_citizen_workplace,
    get_building_record,
    _get_bldg_display_name_module,
    VENICE_TIMEZONE
)

# Import specific activity creators
from backend.engine.activity_creators import (
    try_create_check_business_status_activity,
    try_create_initiate_building_project_activity,
    try_create_secure_warehouse_activity,
    try_create_goto_work_activity
)

from backend.engine.activity_creators.manage_public_storage_offer_creator import try_create as try_create_manage_public_storage_offer_chain

log = logging.getLogger(__name__)


# ==============================================================================
# BUSINESS MANAGEMENT HANDLERS
# ==============================================================================

def _handle_check_business_status(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Handles checking business status for business owners/managers.
    This includes reviewing finances, inventory, and making management decisions.
    """
    # Check if citizen runs any businesses
    run_buildings_formula = f"{{RunBy}}='{_escape_airtable_value(citizen_username)}'"
    
    try:
        run_buildings = tables['buildings'].all(formula=run_buildings_formula)
        businesses = [b for b in run_buildings if b['fields'].get('Category') == 'business']
        
        if not businesses:
            return None
        
        # Check when last status check was done
        last_check = citizen_record['fields'].get('LastBusinessCheck')
        if last_check:
            try:
                last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                if (now_utc_dt - last_check_dt) < timedelta(hours=const.BUSINESS_CHECK_INTERVAL_HOURS):
                    return None
            except Exception:
                pass
        
        log.info(f"{LogColors.OKCYAN}[Business] {citizen_name}: Runs {len(businesses)} business(es). Time to check status.{LogColors.ENDC}")
        
        # Create check business status activity
        for business in businesses[:1]:  # Check one business at a time
            activity = try_create_check_business_status_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                business['fields']['BuildingId'], now_utc_dt
            )
            
            if activity:
                log.info(f"{LogColors.OKGREEN}[Business] {citizen_name}: Created check business status activity.{LogColors.ENDC}")
                # Update last check time
                tables['citizens'].update(citizen_airtable_id, {'LastBusinessCheck': now_utc_dt.isoformat()})
                return activity
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Business] {citizen_name}: Error checking businesses: {e}{LogColors.ENDC}")
    
    return None

def _handle_initiate_building_project(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Handles initiating new building projects for landowners with sufficient resources.
    """
    # Only landowners can initiate building projects
    owned_lands_formula = f"{{Owner}}='{_escape_airtable_value(citizen_username)}'"
    
    try:
        owned_lands = tables['lands'].all(formula=owned_lands_formula)
        if not owned_lands:
            return None
        
        # Check if citizen has sufficient wealth for construction
        ducats = citizen_record['fields'].get('Ducats', 0)
        if ducats < const.MIN_CONSTRUCTION_BUDGET:
            return None
        
        # Find lands with available building points
        for land in owned_lands:
            available_points = _get_available_building_points(tables, land)
            if available_points > 0:
                log.info(f"{LogColors.OKCYAN}[Building] {citizen_name}: Has land with {available_points} available points.{LogColors.ENDC}")
                
                # Create initiate building project activity
                activity = try_create_initiate_building_project_activity(
                    tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                    land['fields']['PolygonId'], now_utc_dt, building_type_defs
                )
                
                if activity:
                    log.info(f"{LogColors.OKGREEN}[Building] {citizen_name}: Created initiate building project activity.{LogColors.ENDC}")
                    return activity
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Building] {citizen_name}: Error checking building opportunities: {e}{LogColors.ENDC}")
    
    return None

def _handle_secure_warehouse(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Handles securing warehouse space for citizens who need storage.
    """
    # Check if citizen needs warehouse space
    current_storage_needs = _calculate_storage_needs(tables, citizen_username)
    if current_storage_needs <= 0:
        return None
    
    # Check if already has sufficient warehouse contracts
    existing_storage = _get_existing_storage_capacity(tables, citizen_username)
    if existing_storage >= current_storage_needs:
        return None
    
    log.info(f"{LogColors.OKCYAN}[Warehouse] {citizen_name}: Needs {current_storage_needs:.0f} storage, has {existing_storage:.0f}.{LogColors.ENDC}")
    
    # Find available warehouses
    available_warehouses = _find_available_warehouses(tables, citizen_position)
    if not available_warehouses:
        log.info(f"{LogColors.WARNING}[Warehouse] {citizen_name}: No available warehouses found.{LogColors.ENDC}")
        return None
    
    # Create secure warehouse activity
    for warehouse in available_warehouses[:1]:  # Try one at a time
        activity = try_create_secure_warehouse_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            warehouse['fields']['BuildingId'], current_storage_needs, now_utc_dt
        )
        
        if activity:
            log.info(f"{LogColors.OKGREEN}[Warehouse] {citizen_name}: Created secure warehouse activity.{LogColors.ENDC}")
            return activity
    
    return None

# ==============================================================================
# NAVIGATION AND GENERAL WORK HANDLERS
# ==============================================================================

def _handle_general_goto_work(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 70: Handles going to work if it's work time and not at workplace."""
    if not is_work_time(citizen_social_class, now_venice_dt):
        return None
    
    # Get workplace
    workplace = get_citizen_workplace(tables, citizen_username)
    if not workplace:
        return None
    
    workplace_pos = json.loads(workplace['fields'].get('Position', '{}'))
    if not workplace_pos or not citizen_position:
        return None
    
    # Check if already at workplace
    distance = _calculate_distance_meters(citizen_position, workplace_pos)
    if distance < const.AT_LOCATION_THRESHOLD:
        return None
    
    workplace_name = _get_bldg_display_name_module(workplace['fields'], building_type_defs)
    log.info(f"{LogColors.OKCYAN}[GoWork] {citizen_name}: Not at workplace ({workplace_name}). Distance: {distance:.0f}m{LogColors.ENDC}")
    
    # Create goto work activity
    activity = try_create_goto_work_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        workplace['fields']['BuildingId'], now_utc_dt
    )
    
    if activity:
        log.info(f"{LogColors.OKGREEN}[GoWork] {citizen_name}: Created goto work activity.{LogColors.ENDC}")
        return activity
    
    return None

def _handle_manage_public_storage_offer(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 82: Handles managing public storage offers for warehouse owners."""
    # Check if citizen runs any warehouses
    warehouse_formula = f"AND({{Type}}='small_warehouse', {{RunBy}}='{_escape_airtable_value(citizen_username)}')"
    
    try:
        warehouses = tables['buildings'].all(formula=warehouse_formula)
        if not warehouses:
            return None
        
        for warehouse in warehouses:
            warehouse_id = warehouse['fields']['BuildingId']
            
            # Check if warehouse already has active storage offer
            offer_formula = f"AND({{Type}}='public_storage_offer', {{BuildingId}}='{warehouse_id}', {{Status}}='active')"
            existing_offers = tables['contracts'].all(formula=offer_formula, max_records=1)
            
            if not existing_offers:
                log.info(f"{LogColors.OKCYAN}[Storage] {citizen_name}: Warehouse needs public storage offer.{LogColors.ENDC}")
                
                # Create manage storage offer activity
                activity = try_create_manage_public_storage_offer_chain(
                    tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                    warehouse_id, now_utc_dt
                )
                
                if activity:
                    warehouse_name = _get_bldg_display_name_module(warehouse, building_type_defs)
                    log.info(f"{LogColors.OKGREEN}[Storage] {citizen_name}: Creating manage storage offer for {warehouse_name}.{LogColors.ENDC}")
                    return activity
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Storage] {citizen_name}: Error managing storage offers: {e}{LogColors.ENDC}")
    
    return None

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _get_available_building_points(tables: Dict[str, Table], land: Dict) -> int:
    """Calculate available building points on a piece of land."""
    try:
        total_points = land['fields'].get('BuildingPoints', 0)
        land_id = land['fields'].get('PolygonId')
        
        # Get existing buildings on this land
        buildings_formula = f"{{LandPolygonId}}='{_escape_airtable_value(land_id)}'"
        existing_buildings = tables['buildings'].all(formula=buildings_formula)
        
        used_points = sum(b['fields'].get('BuildingSize', 1) for b in existing_buildings)
        return max(0, total_points - used_points)
        
    except Exception as e:
        log.error(f"Error calculating building points: {e}")
        return 0

def _calculate_storage_needs(tables: Dict[str, Table], citizen_username: str) -> float:
    """Calculate how much storage a citizen needs based on their business operations."""
    try:
        # Check businesses run by citizen
        run_formula = f"{{RunBy}}='{_escape_airtable_value(citizen_username)}'"
        businesses = tables['buildings'].all(formula=run_formula)
        
        total_needs = 0.0
        for business in businesses:
            # Estimate based on business type and size
            business_type = business['fields'].get('Type', '')
            if business_type in ['merchant_s_house', 'spice_merchant_shop', 'textile_import_house']:
                total_needs += 100.0  # Large storage needs
            elif business_type in ['bakery', 'butcher_shop', 'vegetable_market']:
                total_needs += 50.0   # Medium storage needs
            else:
                total_needs += 25.0   # Small storage needs
        
        return total_needs
        
    except Exception as e:
        log.error(f"Error calculating storage needs: {e}")
        return 0.0

def _get_existing_storage_capacity(tables: Dict[str, Table], citizen_username: str) -> float:
    """Get total storage capacity from existing contracts."""
    try:
        # Check storage contracts
        formula = f"AND({{Type}}='storage_rental', {{Supplier}}='{_escape_airtable_value(citizen_username)}', {{Status}}='active')"
        contracts = tables['contracts'].all(formula=formula)
        
        total_capacity = 0.0
        for contract in contracts:
            total_capacity += float(contract['fields'].get('StorageCapacity', 0))
        
        return total_capacity
        
    except Exception as e:
        log.error(f"Error getting storage capacity: {e}")
        return 0.0

def _find_available_warehouses(tables: Dict[str, Table], citizen_position: Optional[Dict]) -> List[Dict]:
    """Find warehouses with available capacity."""
    try:
        # Get all warehouses
        warehouse_formula = "{{Type}}='small_warehouse'"
        warehouses = tables['buildings'].all(formula=warehouse_formula)
        
        available = []
        for warehouse in warehouses:
            # Check if has public storage offer
            offer_formula = f"AND({{Type}}='public_storage_offer', {{BuildingId}}='{warehouse['fields']['BuildingId']}', {{Status}}='active')"
            offers = tables['contracts'].all(formula=offer_formula, max_records=1)
            
            if offers and offers[0]['fields'].get('AvailableCapacity', 0) > 0:
                available.append(warehouse)
        
        # Sort by distance if position available
        if citizen_position and available:
            for wh in available:
                wh_pos = json.loads(wh['fields'].get('Position', '{}'))
                if wh_pos:
                    wh['distance'] = _calculate_distance_meters(citizen_position, wh_pos)
                else:
                    wh['distance'] = float('inf')
            
            available.sort(key=lambda x: x.get('distance', float('inf')))
        
        return available
        
    except Exception as e:
        log.error(f"Error finding warehouses: {e}")
        return []
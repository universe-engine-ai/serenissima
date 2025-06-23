# backend/engine/handlers/work.py

"""
Contains activity handlers related to a citizen's work, professional duties,
production tasks, construction contracts, and other forms of labor.
"""

import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple, List
from pyairtable import Table
from dateutil import parser as dateutil_parser

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers from the central utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    _calculate_distance_meters,
    is_work_time,
    get_citizen_current_load,
    get_citizen_effective_carry_capacity,
    get_path_between_points,
    get_closest_building_of_type,
    get_building_record,
    get_citizen_home,
    _get_bldg_display_name_module,
    _get_res_display_name_module,
    _get_building_position_coords,
    find_closest_fishable_water_point,
    VENICE_TIMEZONE
)

# Import specific activity creators needed by these handlers
from backend.engine.activity_creators import (
    try_create_deliver_to_storage_activity,
    try_create_fetch_from_storage_activity,
    try_create_production_activity,
    try_create_construction_activity,
    try_create_fishing_activity,
    try_create_porter_guild_task_activity,
    try_create_goto_work_activity,
    try_create_deposit_inventory_orchestrator_activity
)

# Import logic helpers
from backend.engine.logic.construction_logic import check_building_construction_contract
from backend.engine.logic.porter_activities import find_porter_task

log = logging.getLogger(__name__)


# ==============================================================================
# INTERNAL HELPER FUNCTIONS
# ==============================================================================

def __has_recent_failed_activity_for_contract(
    tables: Dict[str, Any],
    citizen_airtable_id: str,
    contract_id: str
) -> bool:
    """
    Checks if the citizen has a recently failed activity for a specific contract.
    This helper is internal to the work module to avoid cluttering global helpers.
    """
    try:
        recent_activity_formula = (
            f"AND({{CitizenId}}='{citizen_airtable_id}', "
            f"{{Contract}}='{_escape_airtable_value(contract_id)}', "
            f"{{Status}}='failed', "
            f"DATETIME_DIFF(NOW(), {{Created}}, 'hours') < 24)"
        )
        recent_failures = tables['activities'].all(formula=recent_activity_formula, max_records=1)
        return len(recent_failures) > 0
    except Exception as e:
        log.error(f"Error checking recent failures: {e}")
        return False

# ==============================================================================
# INVENTORY & LOGISTICS HANDLERS
# ==============================================================================

def _handle_deposit_full_inventory(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 10: Handles depositing a full inventory into a warehouse or home."""
    current_load = get_citizen_current_load(tables, citizen_username)
    carry_capacity = get_citizen_effective_carry_capacity(tables, citizen_username)
    
    if current_load < (carry_capacity * const.STORAGE_FULL_THRESHOLD):
        return None
    
    if current_load < const.MINIMUM_LOAD_FOR_DEPOSIT:
        return None
    
    log.info(f"{LogColors.OKCYAN}[Deposit] {citizen_name}: Full inventory ({current_load:.1f}/{carry_capacity:.1f}). Need to deposit.{LogColors.ENDC}")
    
    # First priority: owned storage buildings
    owned_storage_formula = (f"AND({{Type}}='small_warehouse', {{Status}}='active', "
                             f"{{Occupant}}='{_escape_airtable_value(citizen_username)}')")
    
    try:
        owned_storages = tables['buildings'].all(formula=owned_storage_formula)
        if owned_storages:
            storage_building = owned_storages[0]
            activity_record = try_create_deposit_inventory_orchestrator_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                storage_building['id'], storage_building['fields']['CustomId'], now_utc_dt
            )
            if activity_record:
                bldg_name = _get_bldg_display_name_module(storage_building, building_type_defs)
                log.info(f"{LogColors.OKGREEN}[Deposit] {citizen_name}: Creating 'deposit_inventory_orchestrator' to {bldg_name}.{LogColors.ENDC}")
                return activity_record
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Deposit] {citizen_name}: Error checking owned storage: {e}{LogColors.ENDC}")
    
    # Second priority: home storage
    home_building = get_citizen_home(tables, citizen_username)
    if home_building:
        activity_record = try_create_deposit_inventory_orchestrator_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            home_building['id'], home_building['fields']['CustomId'], now_utc_dt
        )
        if activity_record:
            home_name = _get_bldg_display_name_module(home_building, building_type_defs)
            log.info(f"{LogColors.OKGREEN}[Deposit] {citizen_name}: Creating 'deposit_inventory_orchestrator' to home {home_name}.{LogColors.ENDC}")
            return activity_record
    
    # Third priority: public storage with active offers
    public_storage_formula = "AND({Type}='small_warehouse', {Status}='active', {StorageOffersActive}=TRUE())"
    
    try:
        public_storages = tables['buildings'].all(formula=public_storage_formula)
        if public_storages and citizen_position:
            # Find closest
            closest_storage = None
            min_distance = float('inf')
            
            for storage in public_storages:
                storage_pos = _get_building_position_coords(storage)
                if storage_pos:
                    distance = _calculate_distance_meters(
                        (citizen_position['x'], citizen_position['y']),
                        (storage_pos['x'], storage_pos['y'])
                    )
                    if distance < min_distance:
                        min_distance = distance
                        closest_storage = storage
            
            if closest_storage:
                activity_record = try_create_deposit_inventory_orchestrator_activity(
                    tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                    closest_storage['id'], closest_storage['fields']['CustomId'], now_utc_dt
                )
                if activity_record:
                    storage_name = _get_bldg_display_name_module(closest_storage, building_type_defs)
                    log.info(f"{LogColors.OKGREEN}[Deposit] {citizen_name}: Creating 'deposit_inventory_orchestrator' to public {storage_name}.{LogColors.ENDC}")
                    return activity_record
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Deposit] {citizen_name}: Error finding public storage: {e}{LogColors.ENDC}")
    
    return None

# ==============================================================================
# PRODUCTION & PROFESSIONAL WORK HANDLERS
# ==============================================================================

def _handle_production_and_general_work_tasks(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 31: Handles production and general work tasks if it's work time."""
    if not is_work_time(citizen_social_class, now_venice_dt): return None
    
    log.info(f"{LogColors.OKCYAN}[Work] {citizen_name}: Checking for production/work tasks.{LogColors.ENDC}")
    
    # Check if citizen has a workplace
    workplace_str = citizen_record['fields'].get('WorkplaceId')
    if not workplace_str:
        return None
    
    # Get workplace building
    workplace_building = get_building_record(tables, workplace_str)
    if not workplace_building:
        log.warning(f"{LogColors.WARNING}[Work] {citizen_name}: Workplace {workplace_str} not found.{LogColors.ENDC}")
        return None
    
    workplace_type = workplace_building['fields'].get('Type')
    workplace_name = _get_bldg_display_name_module(workplace_building, building_type_defs)
    
    # Check if citizen is at workplace
    if citizen_position:
        workplace_pos = _get_building_position_coords(workplace_building)
        if workplace_pos:
            distance = _calculate_distance_meters(
                (citizen_position['x'], citizen_position['y']),
                (workplace_pos['x'], workplace_pos['y'])
            )
            
            if distance > const.AT_LOCATION_THRESHOLD:
                log.info(f"{LogColors.WARNING}[Work] {citizen_name}: Not at workplace {workplace_name} ({distance:.1f}m away).{LogColors.ENDC}")
                return None
    
    # Check building type def for production capability
    building_def = building_type_defs.get(workplace_type, {})
    recipes = building_def.get('Recipes', [])
    
    if not recipes:
        log.info(f"{LogColors.WARNING}[Work] {citizen_name}: Workplace {workplace_name} has no recipes.{LogColors.ENDC}")
        return None
    
    # Try to create production activity
    activity_record = try_create_production_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        workplace_building['id'], workplace_str, now_utc_dt
    )
    
    if activity_record:
        log.info(f"{LogColors.OKGREEN}[Work] {citizen_name}: Creating 'production' activity at {workplace_name}.{LogColors.ENDC}")
        return activity_record
    
    return None

def _handle_professional_construction_work(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 30: Handles finding and executing professional construction contracts."""
    if not is_work_time(citizen_social_class, now_venice_dt): return None
    
    # Check if citizen is a professional builder
    workplace_str = citizen_record['fields'].get('WorkplaceId')
    if not workplace_str:
        return None
    
    workplace_building = get_building_record(tables, workplace_str)
    if not workplace_building:
        return None
    
    workplace_type = workplace_building['fields'].get('Type')
    if workplace_type not in ['masons_lodge', 'master_builders_workshop']:
        return None
    
    log.info(f"{LogColors.OKCYAN}[Construction] {citizen_name}: Professional builder checking for contracts.{LogColors.ENDC}")
    
    if not citizen_position:
        return None
    
    # Find construction contracts within radius
    construction_formula = ("AND({Type}='construction_service', {Status}='active', "
                            "{TargetBuildingId}!='', {Worker}='')")
    
    try:
        available_contracts = tables['contracts'].all(formula=construction_formula)
        if not available_contracts:
            log.info(f"{LogColors.WARNING}[Construction] {citizen_name}: No available construction contracts.{LogColors.ENDC}")
            return None
        
        # Filter by distance and recent failures
        valid_contracts = []
        for contract in available_contracts:
            contract_id = contract['fields']['ContractId']
            
            # Check for recent failures
            if __has_recent_failed_activity_for_contract(tables, citizen_airtable_id, contract_id):
                continue
            
            # Check distance
            target_building_id = contract['fields'].get('TargetBuildingId')
            if target_building_id:
                target_building = get_building_record(tables, target_building_id)
                if target_building:
                    target_pos = _get_building_position_coords(target_building)
                    if target_pos:
                        distance = _calculate_distance_meters(
                            (citizen_position['x'], citizen_position['y']),
                            (target_pos['x'], target_pos['y'])
                        )
                        if distance <= const.CONSTRUCTION_CONTRACT_SEARCH_RADIUS_METERS:
                            valid_contracts.append((contract, distance))
        
        if not valid_contracts:
            return None
        
        # Sort by distance and take closest
        valid_contracts.sort(key=lambda x: x[1])
        chosen_contract, distance = valid_contracts[0]
        
        contract_id = chosen_contract['fields']['ContractId']
        target_building_id = chosen_contract['fields']['TargetBuildingId']
        
        # Create construction activity
        activity_record = try_create_construction_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            contract_id, target_building_id, now_utc_dt
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Construction] {citizen_name}: Creating 'deliver_construction_materials' for contract {contract_id}.{LogColors.ENDC}")
            return activity_record
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Construction] {citizen_name}: Error finding contracts: {e}{LogColors.ENDC}")
    
    return None

def _handle_occupant_self_construction(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 33: Handles self-construction on a citizen's own building project."""
    if not is_work_time(citizen_social_class, now_venice_dt): return None
    
    log.info(f"{LogColors.OKCYAN}[Self-Build] {citizen_name}: Checking for self-construction opportunities.{LogColors.ENDC}")
    
    # Check for building projects where citizen is the occupant
    project_formula = (f"AND({{Occupant}}='{_escape_airtable_value(citizen_username)}', "
                       f"{{Status}}='under_construction', {{SelfBuild}}=TRUE())")
    
    try:
        building_projects = tables['buildings'].all(formula=project_formula)
        if not building_projects:
            return None
        
        for project in building_projects:
            building_id = project['fields']['CustomId']
            building_name = _get_bldg_display_name_module(project, building_type_defs)
            
            # Check construction contract
            contract_info = check_building_construction_contract(
                tables, building_id, building_type_defs
            )
            
            if not contract_info or not contract_info.get('needs_work'):
                continue
            
            # Create self-construction activity
            activity_record = try_create_construction_activity(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                contract_info['contract_id'], building_id, now_utc_dt,
                is_self_build=True
            )
            
            if activity_record:
                log.info(f"{LogColors.OKGREEN}[Self-Build] {citizen_name}: Creating 'occupant_self_construction' for {building_name}.{LogColors.ENDC}")
                return activity_record
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Self-Build] {citizen_name}: Error checking projects: {e}{LogColors.ENDC}")
    
    return None


def _handle_porter_tasks(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 60: Handles finding and executing tasks from the Porter's Guild."""
    if not is_work_time(citizen_social_class, now_venice_dt): return None
    
    # Check if citizen is a porter guild member
    guild_formula = (f"AND({{GuildId}}='{const.PORTER_GUILD_ID}', "
                     f"{{Member}}='{_escape_airtable_value(citizen_username)}')")
    
    try:
        guild_membership = tables['guild_members'].all(formula=guild_formula, max_records=1)
        if not guild_membership:
            return None
        
        log.info(f"{LogColors.OKCYAN}[Porter] {citizen_name}: Porter guild member checking for tasks.{LogColors.ENDC}")
        
        if not citizen_position:
            return None
        
        # Find porter task
        task_info = find_porter_task(
            tables, citizen_username, citizen_position,
            const.PORTER_TASK_SEARCH_RADIUS, resource_defs
        )
        
        if not task_info:
            log.info(f"{LogColors.WARNING}[Porter] {citizen_name}: No porter tasks available.{LogColors.ENDC}")
            return None
        
        # Create porter task activity
        activity_record = try_create_porter_guild_task_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            task_info['contract_id'], task_info['pickup_location'],
            task_info['delivery_location'], task_info['resource_type'],
            task_info['quantity'], now_utc_dt
        )
        
        if activity_record:
            resource_name = _get_res_display_name_module(task_info['resource_type'], resource_defs)
            log.info(f"{LogColors.OKGREEN}[Porter] {citizen_name}: Creating porter task to transport {task_info['quantity']} {resource_name}.{LogColors.ENDC}")
            return activity_record
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Porter] {citizen_name}: Error finding tasks: {e}{LogColors.ENDC}")
    
    return None

def _handle_fishing(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 32: Handles professional fishing if it's work time."""
    if not is_work_time(citizen_social_class, now_venice_dt): return None
    
    # Check if citizen works at a fisherman's cottage
    workplace_str = citizen_record['fields'].get('WorkplaceId')
    if not workplace_str:
        return None
    
    workplace_building = get_building_record(tables, workplace_str)
    if not workplace_building:
        return None
    
    if workplace_building['fields'].get('Type') != 'fisherman_s_cottage':
        return None
    
    log.info(f"{LogColors.OKCYAN}[Fishing] {citizen_name}: Professional fisher checking for fishing opportunity.{LogColors.ENDC}")
    
    if not citizen_position:
        return None
    
    # Find fishable water point
    water_point_info = find_closest_fishable_water_point(
        transport_api_url, citizen_position, max_distance=500
    )
    
    if not water_point_info:
        log.warning(f"{LogColors.WARNING}[Fishing] {citizen_name}: No fishable water nearby.{LogColors.ENDC}")
        return None
    
    # Create fishing activity
    activity_record = try_create_fishing_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        water_point_info['point_id'], now_utc_dt,
        is_professional=True
    )
    
    if activity_record:
        log.info(f"{LogColors.OKGREEN}[Fishing] {citizen_name}: Creating professional 'fishing' activity at {water_point_info['point_id']}.{LogColors.ENDC}")
        return activity_record
    
    return None
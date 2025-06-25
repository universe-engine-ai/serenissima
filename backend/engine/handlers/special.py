# backend/engine/handlers/special.py

"""
Contains activity handlers for special citizen classes and unique activities,
including Forestieri, Artisti, and other class-specific behaviors.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pyairtable import Table

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers from the central utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    is_work_time,
    is_leisure_time_for_class,
    get_citizen_home,
    VENICE_TIMEZONE
)

# Import specific activity creators
from backend.engine.activity_creators import (
    try_create_leave_venice_activity,
    try_create_manage_public_dock_activity,
    try_create_work_on_art_activity,
    try_create_prepare_sermon_activity
)

# Import specialized activity processors
from backend.engine.logic.forestieri_activities import (
    process_forestieri_night_activity,
    process_forestieri_daytime_activity,
    process_forestieri_departure_check
)

log = logging.getLogger(__name__)


# ==============================================================================
# FORESTIERI-SPECIFIC HANDLERS
# ==============================================================================

def _handle_leave_venice(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 1: Handles Forestieri leaving Venice when conditions are met."""
    if citizen_social_class != "Forestieri":
        return None
    
    log.info(f"{LogColors.OKCYAN}[Forestieri-Leave] {citizen_name}: Checking departure conditions.{LogColors.ENDC}")
    
    # Check departure conditions using the forestieri processor
    should_leave = process_forestieri_departure_check(
        tables, citizen_record, now_venice_dt, now_utc_dt
    )
    
    if should_leave:
        log.info(f"{LogColors.OKGREEN}[Forestieri-Leave] {citizen_name}: Departure conditions met. Creating leave activity.{LogColors.ENDC}")
        
        # Create leave Venice activity
        activity = try_create_leave_venice_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            now_utc_dt
        )
        
        if activity:
            log.info(f"{LogColors.OKGREEN}[Forestieri-Leave] {citizen_name}: Created leave Venice activity.{LogColors.ENDC}")
            return activity
    
    return None

def _handle_forestieri_daytime_tasks(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Prio 40: Handles Forestieri-specific daytime activities."""
    if citizen_social_class != "Forestieri":
        return None
    
    # Forestieri work differently - they don't follow normal work schedules
    # They trade, explore, and conduct business during the day
    
    log.info(f"{LogColors.OKCYAN}[Forestieri-Day] {citizen_name}: Processing daytime activities.{LogColors.ENDC}")
    
    # Use the specialized forestieri processor
    activity = process_forestieri_daytime_activity(
        tables, citizen_record, resource_defs, building_type_defs,
        now_venice_dt, now_utc_dt, transport_api_url, api_base_url
    )
    
    if activity:
        log.info(f"{LogColors.OKGREEN}[Forestieri-Day] {citizen_name}: Created daytime activity.{LogColors.ENDC}")
        return activity
    
    return None

def _handle_forestieri_night_shelter(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Handles Forestieri-specific night shelter needs."""
    if citizen_social_class != "Forestieri":
        return None
    
    # Forestieri always need to find inn shelter at night
    log.info(f"{LogColors.OKCYAN}[Forestieri-Night] {citizen_name}: Processing night shelter needs.{LogColors.ENDC}")
    
    # Use the specialized forestieri processor
    activity = process_forestieri_night_activity(
        tables, citizen_record, resource_defs, building_type_defs,
        now_venice_dt, now_utc_dt, transport_api_url, api_base_url
    )
    
    if activity:
        log.info(f"{LogColors.OKGREEN}[Forestieri-Night] {citizen_name}: Created night shelter activity.{LogColors.ENDC}")
        return activity
    
    return None

# ==============================================================================
# ARTISTI-SPECIFIC HANDLERS
# ==============================================================================

def _handle_artisti_work_on_art(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Special handler for Artisti creating art.
    Unlike the leisure version, this can happen during work time for professional artists.
    """
    if citizen_social_class != "Artisti":
        return None
    
    # Artisti can work on art during work time OR leisure time
    current_hour = now_venice_dt.hour
    is_appropriate_time = is_work_time(citizen_social_class, now_venice_dt) or is_leisure_time_for_class(citizen_social_class, now_venice_dt)
    
    if not is_appropriate_time:
        return None
    
    log.info(f"{LogColors.OKCYAN}[Artisti-Art] {citizen_name}: Professional artist checking for art creation.{LogColors.ENDC}")
    
    # Check if has art studio or appropriate workspace
    workspace = _get_artisti_workspace(tables, citizen_username)
    if not workspace:
        log.info(f"{LogColors.WARNING}[Artisti-Art] {citizen_name}: No suitable workspace for art creation.{LogColors.ENDC}")
        return None
    
    # Create work on art activity
    activity = try_create_work_on_art_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        now_utc_dt, workspace_id=workspace['fields'].get('BuildingId')
    )
    
    if activity:
        log.info(f"{LogColors.OKGREEN}[Artisti-Art] {citizen_name}: Created professional art work activity.{LogColors.ENDC}")
        return activity
    
    return None

# ==============================================================================
# CLERO-SPECIFIC HANDLERS
# ==============================================================================

def _handle_clero_prepare_sermon(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Special handler for Clero preparing sermons during work hours.
    This happens at their assigned church workplace.
    """
    if citizen_social_class != "Clero":
        return None
    
    # Check if it's work time for Clero
    if not is_work_time(citizen_social_class, now_venice_dt):
        return None
    
    log.info(f"{LogColors.OKCYAN}[Clero-Sermon] {citizen_name}: Clergy member checking for sermon preparation.{LogColors.ENDC}")
    
    # Check if the citizen is at their workplace (church)
    workplace_str = citizen_record['fields'].get('WorkplaceId')
    if not workplace_str:
        log.info(f"{LogColors.WARNING}[Clero-Sermon] {citizen_name}: No workplace assigned.{LogColors.ENDC}")
        return None
    
    # For prepare_sermon, the citizen should already be at their workplace
    # The activity creator will verify this
    
    # Create prepare sermon activity
    activity = try_create_prepare_sermon_activity(
        tables, citizen_record, citizen_position,
        resource_defs, building_type_defs,
        now_venice_dt, now_utc_dt,
        transport_api_url, api_base_url
    )
    
    if activity:
        log.info(f"{LogColors.OKGREEN}[Clero-Sermon] {citizen_name}: Created prepare sermon activity.{LogColors.ENDC}")
        return activity
    
    return None

# ==============================================================================
# PUBLIC SERVICE HANDLERS
# ==============================================================================

def _handle_manage_public_dock(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Handles managing public docks for citizens who run them.
    This includes collecting fees and maintaining dock operations.
    """
    # Check if citizen runs a public dock
    run_buildings_formula = f"AND({{RunBy}}='{_escape_airtable_value(citizen_username)}', {{Type}}='public_dock')"
    
    try:
        docks = tables['buildings'].all(formula=run_buildings_formula)
        if not docks:
            return None
        
        dock = docks[0]  # Handle first dock
        dock_name = dock['fields'].get('Name', 'public dock')
        
        log.info(f"{LogColors.OKCYAN}[Dock] {citizen_name}: Manages {dock_name}. Creating management activity.{LogColors.ENDC}")
        
        # Create manage dock activity
        activity = try_create_manage_public_dock_activity(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            dock['fields']['BuildingId'], now_utc_dt
        )
        
        if activity:
            log.info(f"{LogColors.OKGREEN}[Dock] {citizen_name}: Created manage public dock activity.{LogColors.ENDC}")
            return activity
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Dock] {citizen_name}: Error checking dock management: {e}{LogColors.ENDC}")
    
    return None

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _get_artisti_workspace(tables: Dict[str, Table], citizen_username: str) -> Optional[Dict]:
    """Find suitable workspace for an artist (studio, workshop, or home with space)."""
    try:
        # Check for art gallery or bottega ownership/management
        formula = f"AND(OR({{Owner}}='{_escape_airtable_value(citizen_username)}', {{RunBy}}='{_escape_airtable_value(citizen_username)}'), OR({{Type}}='art_gallery', {{Type}}='bottega'))"
        art_spaces = tables['buildings'].all(formula=formula, max_records=1)
        
        if art_spaces:
            return art_spaces[0]
        
        # Check if home can serve as workspace
        home = get_citizen_home(tables, citizen_username)
        if home:
            # Nobili and wealthy Cittadini homes can serve as art studios
            home_type = home['fields'].get('Type', '')
            if home_type in ['nobili_palazzo', 'grand_canal_palace', 'merchant_s_house']:
                return home
        
        return None
        
    except Exception as e:
        log.error(f"Error finding artist workspace: {e}")
        return None
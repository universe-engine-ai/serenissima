# backend/engine/handlers/orchestrator.py

"""
Main orchestrator for citizen activity processing.
This replaces the monolithic process_citizen_activity function by coordinating
calls to specialized handlers in a clean, maintainable way.
"""

import logging
import json
import pytz
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple, List, Callable
from pyairtable import Table

# Import helpers
from backend.engine.utils.activity_helpers import (
    LogColors,
    _fetch_and_assign_random_starting_position,
    is_rest_time_for_class,
    is_leisure_time_for_class,
    is_work_time,
    VENICE_TIMEZONE
)

# Import constants
from backend.engine.config.constants import IDLE_ACTIVITY_DURATION_HOURS

# Import all handlers
from backend.engine.handlers.needs import (
    _handle_eat_from_inventory,
    _handle_eat_at_home_or_goto,
    _handle_eat_at_tavern_or_goto,
    _handle_emergency_fishing,
    _handle_shop_for_food_at_retail,
    _handle_night_shelter
)

from backend.engine.handlers.work import (
    _handle_production_and_general_work_tasks,
    _handle_professional_construction_work,
    _handle_occupant_self_construction,
    _handle_porter_tasks,
    _handle_fishing,
    _handle_deposit_full_inventory
)

from backend.engine.handlers.leisure import (
    _handle_work_on_art,
    _handle_attend_theater_performance,
    _handle_drink_at_inn,
    _handle_use_public_bath,
    _handle_read_book,
    _handle_shopping_tasks,
    _try_process_weighted_leisure_activities
)

from backend.engine.handlers.social import (
    _handle_send_message,
    _handle_spread_rumor
)

from backend.engine.handlers.inventory import (
    _handle_deposit_full_inventory as _handle_deposit_inventory,
    _handle_manage_public_storage_offer
)

from backend.engine.handlers.management import (
    _handle_check_business_status,
    _handle_initiate_building_project,
    _handle_secure_warehouse,
    _handle_general_goto_work
)

from backend.engine.handlers.special import (
    _handle_leave_venice,
    _handle_forestieri_daytime_tasks,
    _handle_forestieri_night_shelter,
    _handle_artisti_work_on_art,
    _handle_manage_public_dock
)

# Import activity creators for fallback
from backend.engine.activity_creators import try_create_idle_activity

log = logging.getLogger(__name__)


# Type alias for handler functions
HandlerFunc = Callable[..., Optional[Dict]]


class CitizenActivityOrchestrator:
    """
    Orchestrates citizen activity processing by coordinating specialized handlers.
    Each handler is responsible for a specific type of activity and announces itself.
    """
    
    def __init__(self):
        """Initialize the orchestrator with handler configurations."""
        # Define handler groups with priorities
        self.critical_handlers: List[Tuple[int, HandlerFunc, str]] = [
            (1, _handle_leave_venice, "Leave Venice (Forestieri)"),
            (2, _handle_eat_from_inventory, "Eat from Inventory"),
            (3, _handle_eat_at_home_or_goto, "Eat at Home"),
            (4, _handle_emergency_fishing, "Emergency Fishing"),
            (5, _handle_shop_for_food_at_retail, "Shop for Food"),
            (6, _handle_eat_at_tavern_or_goto, "Eat at Tavern"),
            (10, _handle_deposit_inventory, "Deposit Full Inventory"),
            (15, _handle_night_shelter, "Night Shelter/Rest"),
        ]
        
        self.work_handlers: List[Tuple[int, HandlerFunc, str]] = [
            (20, _handle_check_business_status, "Check Business Status"),
            (25, _handle_artisti_work_on_art, "Artisti Work on Art"),
            (30, _handle_professional_construction_work, "Professional Construction"),
            (31, _handle_production_and_general_work_tasks, "Production & General Work"),
            (32, _handle_fishing, "Professional Fishing"),
            (33, _handle_occupant_self_construction, "Self Construction"),
            (35, _handle_manage_public_dock, "Manage Public Dock"),
            (40, _handle_forestieri_daytime_tasks, "Forestieri Daytime Tasks"),
            (60, _handle_porter_tasks, "Porter Guild Tasks"),
            (70, _handle_general_goto_work, "Go to Work"),
        ]
        
        self.management_handlers: List[Tuple[int, HandlerFunc, str]] = [
            (80, _handle_initiate_building_project, "Initiate Building Project"),
            (81, _handle_secure_warehouse, "Secure Warehouse"),
            (82, _handle_manage_public_storage_offer, "Manage Storage Offers"),
        ]
        
        # Leisure handlers are processed differently (weighted random)
        self.leisure_handler = _try_process_weighted_leisure_activities
        
    def process_citizen_activity(
        self,
        tables: Dict[str, Table],
        citizen_record: Dict,
        resource_defs: Dict,
        building_type_defs: Dict,
        now_venice_dt: datetime,
        now_utc_dt: datetime,
        transport_api_url: str,
        api_base_url: str
    ) -> Optional[Dict]:
        """
        Main entry point for processing a citizen's activity.
        Coordinates handlers in priority order and returns the first successful activity.
        """
        # Extract citizen information
        citizen_custom_id = citizen_record['fields'].get('CitizenId')
        citizen_username = citizen_record['fields'].get('Username')
        citizen_airtable_id = citizen_record['id']
        
        if not citizen_custom_id:
            log.error(f"Missing CitizenId: {citizen_airtable_id}")
            return None
        
        if not citizen_username:
            citizen_username = citizen_custom_id  # Fallback
        
        citizen_name = self._get_citizen_name(citizen_record)
        citizen_social_class = citizen_record['fields'].get('SocialClass', 'Facchini')
        
        log.info(f"{LogColors.HEADER}=== PROCESSING CITIZEN: {citizen_name} ==={LogColors.ENDC}")
        log.info(f"{LogColors.OKBLUE}ID: {citizen_custom_id} | Username: {citizen_username} | Class: {citizen_social_class}{LogColors.ENDC}")
        
        # Get citizen position
        citizen_position = self._get_citizen_position(tables, citizen_record, api_base_url)
        if not citizen_position:
            log.warning(f"{LogColors.WARNING}No position for {citizen_name}. Creating idle activity.{LogColors.ENDC}")
            return self._create_fallback_idle(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                now_utc_dt, "Failed to determine citizen position"
            )
        
        citizen_position_str = json.dumps(citizen_position)
        
        # Determine citizen state
        citizen_record['is_hungry'] = self._is_citizen_hungry(citizen_record, now_utc_dt)
        
        # Prepare handler arguments
        handler_args = (
            tables, citizen_record, False, resource_defs, building_type_defs,
            now_venice_dt, now_utc_dt, transport_api_url, api_base_url,
            citizen_position, citizen_custom_id, citizen_username, citizen_airtable_id,
            citizen_name, citizen_position_str, citizen_social_class
        )
        
        # Process critical needs first
        log.info(f"{LogColors.HEADER}--- Checking Critical Needs ---{LogColors.ENDC}")
        activity = self._process_handler_group(self.critical_handlers, handler_args, "Critical")
        if activity:
            return activity
        
        # Check if it's leisure time
        if is_leisure_time_for_class(citizen_social_class, now_venice_dt):
            log.info(f"{LogColors.HEADER}--- Leisure Time Activities ---{LogColors.ENDC}")
            activity = self.leisure_handler(*handler_args)
            if activity:
                return activity
            
            # Try shopping as fallback leisure
            activity = _handle_shopping_tasks(*handler_args)
            if activity:
                return activity
        
        # Process work activities if work time
        if is_work_time(citizen_social_class, now_venice_dt):
            log.info(f"{LogColors.HEADER}--- Work Time Activities ---{LogColors.ENDC}")
            activity = self._process_handler_group(self.work_handlers, handler_args, "Work")
            if activity:
                return activity
        
        # Process management activities
        log.info(f"{LogColors.HEADER}--- Management Activities ---{LogColors.ENDC}")
        activity = self._process_handler_group(self.management_handlers, handler_args, "Management")
        if activity:
            return activity
        
        # Fallback activities
        log.info(f"{LogColors.HEADER}--- Fallback Activities ---{LogColors.ENDC}")
        
        # Try rest if it's rest time
        if is_rest_time_for_class(citizen_social_class, now_venice_dt):
            log.info(f"{LogColors.OKBLUE}Attempting fallback rest activity{LogColors.ENDC}")
            activity = _handle_night_shelter(*handler_args)
            if activity:
                return activity
        
        # Try depositing inventory
        log.info(f"{LogColors.OKBLUE}Attempting fallback inventory deposit{LogColors.ENDC}")
        activity = _handle_deposit_inventory(*handler_args)
        if activity:
            return activity
        
        # Final fallback: idle
        log.info(f"{LogColors.WARNING}No activities available. Creating idle activity.{LogColors.ENDC}")
        return self._create_fallback_idle(
            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
            now_utc_dt, "No activities available after checking all handlers"
        )
    
    def _process_handler_group(
        self,
        handlers: List[Tuple[int, HandlerFunc, str]],
        handler_args: Tuple,
        group_name: str
    ) -> Optional[Dict]:
        """Process a group of handlers in priority order."""
        for priority, handler_func, description in handlers:
            log.info(f"{LogColors.OKBLUE}[{group_name}-P{priority}] Checking: {description}{LogColors.ENDC}")
            
            try:
                activity = handler_func(*handler_args)
                if activity:
                    activity_id = self._get_activity_id(activity)
                    log.info(f"{LogColors.OKGREEN}✓ Created: {description} (Activity: {activity_id}){LogColors.ENDC}")
                    return activity
                else:
                    log.info(f"{LogColors.OKCYAN}  ↳ Not applicable or no activity needed{LogColors.ENDC}")
            
            except Exception as e:
                log.error(f"{LogColors.FAIL}✗ ERROR in {description}: {e}{LogColors.ENDC}", exc_info=True)
        
        return None
    
    def _get_citizen_name(self, citizen_record: Dict) -> str:
        """Extract citizen display name."""
        first_name = citizen_record['fields'].get('FirstName', '')
        last_name = citizen_record['fields'].get('LastName', '')
        username = citizen_record['fields'].get('Username', citizen_record['fields'].get('CitizenId', 'Unknown'))
        
        full_name = f"{first_name} {last_name}".strip()
        return full_name if full_name else username
    
    def _get_citizen_position(
        self,
        tables: Dict[str, Table],
        citizen_record: Dict,
        api_base_url: str
    ) -> Optional[Dict[str, float]]:
        """Get or assign citizen position."""
        position_str = citizen_record['fields'].get('Position')
        
        try:
            if position_str:
                return json.loads(position_str)
            
            # Try to parse from Point field
            point_str = citizen_record['fields'].get('Point')
            if point_str and isinstance(point_str, str):
                parts = point_str.split('_')
                if len(parts) >= 3:
                    return {"lat": float(parts[1]), "lng": float(parts[2])}
        
        except Exception:
            pass
        
        # Assign random position
        log.info(f"{LogColors.OKBLUE}Assigning random position{LogColors.ENDC}")
        return _fetch_and_assign_random_starting_position(tables, citizen_record, api_base_url)
    
    def _is_citizen_hungry(self, citizen_record: Dict, now_utc_dt: datetime) -> bool:
        """Determine if citizen is hungry based on last meal time."""
        ate_at_str = citizen_record['fields'].get('AteAt')
        if not ate_at_str:
            return True
        
        try:
            ate_at_dt = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
            if ate_at_dt.tzinfo is None:
                ate_at_dt = pytz.UTC.localize(ate_at_dt)
            
            hours_since_meal = (now_utc_dt - ate_at_dt).total_seconds() / 3600
            return hours_since_meal > 12
        
        except Exception:
            return True
    
    def _get_activity_id(self, activity: Dict) -> str:
        """Extract activity ID from activity record."""
        if isinstance(activity, dict) and 'fields' in activity:
            return activity['fields'].get('ActivityId', activity.get('id', 'unknown'))
        return "unknown"
    
    def _create_fallback_idle(
        self,
        tables: Dict[str, Table],
        citizen_id: str,
        citizen_username: str,
        citizen_airtable_id: str,
        now_utc_dt: datetime,
        reason: str
    ) -> Dict:
        """Create a fallback idle activity."""
        idle_end_time = (now_utc_dt + timedelta(hours=IDLE_ACTIVITY_DURATION_HOURS)).isoformat()
        
        return try_create_idle_activity(
            tables, citizen_id, citizen_username, citizen_airtable_id,
            end_date_iso=idle_end_time,
            reason_message=reason,
            current_time_utc=now_utc_dt,
            start_time_utc_iso=None
        )


# Create singleton instance
orchestrator = CitizenActivityOrchestrator()


def process_citizen_activity(
    tables: Dict[str, Table],
    citizen_record: Dict,
    resource_defs: Dict,
    building_type_defs: Dict,
    now_venice_dt: datetime,
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str
) -> Optional[Dict]:
    """
    Main entry point maintaining the same interface as the original function.
    Delegates to the orchestrator for actual processing.
    """
    return orchestrator.process_citizen_activity(
        tables, citizen_record, resource_defs, building_type_defs,
        now_venice_dt, now_utc_dt, transport_api_url, api_base_url
    )
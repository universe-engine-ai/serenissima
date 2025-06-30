# backend/engine/main_engine.py

"""
The central decision-making engine for citizen AI in La Serenissima.

This module contains the primary orchestration logic for citizen activities.
It determines what a citizen should do in a given tick by evaluating a series of
specialized handlers in a predefined priority order. It also includes the dispatcher
for handling direct, API-driven activity requests.

This file is the refactored core of the original citizen_general_activities.py.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
import pytz

# Import refactored constants
from backend.engine.config import constants as const

# Import core utilities and helpers needed for orchestration
from backend.engine.utils.activity_helpers import (
    LogColors,
    is_rest_time_for_class,
    VENICE_TIMEZONE
)

# Import activity creators used directly by the dispatcher or fallback logic
from backend.engine.activity_creators import (
    try_create_idle_activity,
    try_create_send_message_activity as try_create_send_message_chain,
    try_create_initiate_building_project_activity,
    try_create_talk_publicly_activity,
    try_create_send_diplomatic_email_activity,
    # ... import other creators used by the dispatcher below
)

# ==============================================================================
# IMPORT SPECIALIZED HANDLERS
# These modules now contain the implementations of the _handle_... functions.
# ==============================================================================
from backend.engine.handlers import needs as needs_handlers
from backend.engine.handlers import work as work_handlers
from backend.engine.handlers import leisure as leisure_handlers
from backend.engine.handlers import management as management_handlers
from backend.engine.handlers import special as special_handlers

log = logging.getLogger(__name__)

# ==============================================================================
# API-DRIVEN ACTIVITY DISPATCHER
# ==============================================================================

def dispatch_specific_activity_request(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    activity_type: str,
    activity_parameters: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    transport_api_url: str,
    api_base_url: str
) -> Dict[str, Any]:
    """
    Handles direct requests to create a specific activity for a citizen.

    This function acts as a router, calling the appropriate activity creation
    logic based on the 'activity_type' provided.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_airtable_id = citizen_record['id']
    
    # Extract current UTC time
    now_utc_dt = datetime.now(timezone.utc)
    now_venice_dt = now_utc_dt.astimezone(VENICE_TIMEZONE)
    
    try:
        if activity_type == "send_message":
            # Extract parameters
            recipient = activity_parameters.get('recipient')
            message_type = activity_parameters.get('messageType', 'general')
            content = activity_parameters.get('content', '')
            
            if not recipient:
                return {"success": False, "message": "Recipient is required for send_message activity", "activity": None, "reason": "missing_recipient"}
            
            # Create the send message activity
            activity_record = try_create_send_message_chain(
                tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                recipient, message_type, now_utc_dt
            )
            
            if activity_record:
                return {"success": True, "message": f"Created send_message activity to {recipient}", "activity": activity_record, "reason": None}
            else:
                return {"success": False, "message": f"Failed to create send_message activity to {recipient}", "activity": None, "reason": "creation_failed"}
        
        elif activity_type == "initiate_building_project":
            # Create the initiate building project activity
            # The smart wrapper will detect the signature and call the appropriate function
            result = try_create_initiate_building_project_activity(
                tables, citizen_record, activity_parameters,
                resource_defs, building_type_defs,
                now_venice_dt, now_utc_dt,
                transport_api_url, api_base_url
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": result.get("message", "Created initiate_building_project activity chain"),
                    "activity": result.get("activity_fields"),
                    "reason": None
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "Failed to create initiate_building_project activity"),
                    "activity": None,
                    "reason": result.get("reason", "creation_failed")
                }
        
        elif activity_type == "talk_publicly":
            # Extract parameters for public announcement
            message = activity_parameters.get('message', '').strip()
            message_type = activity_parameters.get('messageType', 'announcement')
            target_audience = activity_parameters.get('targetAudience')
            
            if not message:
                return {"success": False, "message": "Message content is required for talk_publicly activity", "activity": None, "reason": "missing_message"}
            
            # Create the talk_publicly activity
            activity_record = try_create_talk_publicly_activity(
                tables, citizen_record, activity_parameters,
                api_base_url, transport_api_url
            )
            
            if activity_record:
                return {"success": True, "message": f"Created talk_publicly activity", "activity": activity_record, "reason": None}
            else:
                return {"success": False, "message": f"Failed to create talk_publicly activity", "activity": None, "reason": "creation_failed"}
        
        elif activity_type == "send_diplomatic_email":
            # Extract parameters for diplomatic email
            description = activity_parameters.get('description', '{}')
            
            # Only diplomatic_virtuoso can send diplomatic emails
            if citizen_record['fields'].get('Username') != 'diplomatic_virtuoso':
                return {"success": False, "message": "Only diplomatic_virtuoso can send diplomatic emails", "activity": None, "reason": "unauthorized"}
            
            # Create the send_diplomatic_email activity
            activity_record = try_create_send_diplomatic_email_activity(
                tables, citizen_record, activity_parameters,
                api_base_url, transport_api_url
            )
            
            if activity_record:
                return {"success": True, "message": f"Created send_diplomatic_email activity", "activity": activity_record, "reason": None}
            else:
                return {"success": False, "message": f"Failed to create send_diplomatic_email activity", "activity": None, "reason": "creation_failed"}
        
        # Add more activity types here as needed
        # elif activity_type == "bid_on_land":
        #     return try_create_bid_on_land_chain(...)
        # ... etc.
        
        else:
            log.warning(f"Dispatcher received an unknown activity type: {activity_type}")
            return {"success": False, "message": f"Activity type '{activity_type}' is not supported.", "activity": None, "reason": "unknown_activity_type"}
            
    except Exception as e:
        log.error(f"Error in dispatch_specific_activity_request for {citizen_username}, type {activity_type}: {e}", exc_info=True)
        return {"success": False, "message": f"Error creating activity: {str(e)}", "activity": None, "reason": "internal_error"}


# ==============================================================================
# AUTONOMOUS AI DECISION ENGINE
# ==============================================================================

def process_citizen_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    now_utc_dt: datetime,
    is_night: bool,
    api_base_url: str,
    hf_api_token: str
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the decision-making process for a single citizen's activity.

    This function calls a sequence of prioritized handler functions. Each handler
    checks if a specific condition is met (e.g., citizen is hungry, it's time
    to work) and, if so, returns an activity record. The first handler to
    return a valid activity wins.

    If no handler generates an activity, a fallback idle activity is created.
    """
    citizen_name = citizen_record.get('fields', {}).get('Username', 'UnknownCitizen')

    # Block new activities if the citizen is already engaged in a blocking activity
    if citizen_record.get('fields', {}).get('IsEngagedInBlockingActivity'):
        log.info(f"{LogColors.WARNING}Citizen {citizen_name} is engaged in a blocking activity. Skipping new activity creation.{LogColors.ENDC}")
        return None

    # This tuple packages all necessary arguments for the handlers.
    handler_args_tuple = (
        tables, citizen_record, is_night, now_utc_dt, api_base_url, hf_api_token
    )

    # --- Handler Priority Chain ---
    # The core logic is now just a clean sequence of calls to imported handlers.
    # The order of these calls defines the citizen's priorities.

    handler_chain = [
        # CRITICAL: Needs and Survival
        (special_handlers._handle_leave_venice, "Check if Forestieri should leave Venice"),
        (needs_handlers._handle_eat_from_inventory, "Check for eating from inventory"),
        (needs_handlers._handle_eat_at_home_or_goto, "Check for eating at home"),
        (needs_handlers._handle_eat_at_tavern_or_goto, "Check for eating at a tavern"),

        # HIGH: Business, Work, and Shelter
        (management_handlers._handle_check_business_status, "Check business status"),
        (needs_handlers._handle_night_shelter, "Check for night shelter"),
        (work_handlers._handle_deposit_full_inventory, "Check for depositing full inventory"),
        (work_handlers._handle_production_and_general_work_tasks, "Check for production/general work"),
        (work_handlers._handle_professional_construction_work, "Check for professional construction work"),
        
        # MEDIUM: Personal Construction, Logistics, Special Roles
        (work_handlers._handle_occupant_self_construction, "Check for self-construction"),
        (management_handlers._handle_manage_public_dock, "Check for managing public dock"),
        (special_handlers._handle_forestieri_daytime_tasks, "Check for Forestieri daytime tasks"),

        # LOW: Leisure and Personal Errands
        (leisure_handlers._handle_shopping_tasks, "Check for shopping tasks"),
        (leisure_handlers._handle_attend_theater_performance, "Check for attending theater"),
        (leisure_handlers._handle_drink_at_inn, "Check for drinking at an inn"),
        (leisure_handlers._handle_use_public_bath, "Check for using public baths"),
        (leisure_handlers._handle_read_book, "Check for reading a book"),
        (work_handlers._handle_porter_tasks, "Check for porter tasks"),
        (leisure_handlers._handle_send_leisure_message, "Check for sending leisure message"),
        (leisure_handlers._handle_spread_rumor, "Check for spreading rumor"),
        
        # FALLBACK: Last resort before being idle
        (needs_handlers._handle_emergency_fishing, "Check for emergency fishing")
    ]

    for handler_func, description in handler_chain:
        log.info(f"{LogColors.OKBLUE}Citizen {citizen_name}: {description}{LogColors.ENDC}")
        activity_record = handler_func(*handler_args_tuple)
        if activity_record:
            log.info(f"{LogColors.OKGREEN}Citizen {citizen_name}: Activity created by {handler_func.__name__}.{LogColors.ENDC}")
            return activity_record

    # --- Final Fallback to Idle ---
    log.info(f"{LogColors.WARNING}Citizen {citizen_name}: No specific activity determined. Creating idle activity.{LogColors.ENDC}")
    idle_end_time_iso = (now_utc_dt + timedelta(hours=const.IDLE_ACTIVITY_DURATION_HOURS)).isoformat()
    return try_create_idle_activity(
        tables,
        citizen_record.get('fields').get('CustomId'),
        citizen_name,
        citizen_record.get('id'),
        idle_end_time_iso
    )
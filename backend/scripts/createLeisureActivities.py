#!/usr/bin/env python3
"""
Force Create Leisure Activities Script for La Serenissima.

This script iterates through citizens in Venice (or a specific citizen)
and forces the creation of a leisure activity, bypassing normal time
and occupation checks.
"""

import os
import sys
import logging
import argparse
import json
import random
from datetime import datetime
import pytz
from typing import Optional, Dict, List, Tuple, Any

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

from backend.engine.utils.activity_helpers import (
    LogColors, VENICE_TIMEZONE, _escape_airtable_value,
    get_resource_types_from_api, get_building_types_from_api,
    get_citizen_record, log_header, _get_building_position_coords,
    _fetch_and_assign_random_starting_position,
    SOCIAL_CLASS_SCHEDULES # Import schedule dictionary
)
# Import specific leisure activity handlers from leisure handler module
from backend.engine.handlers.leisure import (
    _handle_attend_theater_performance,
    _handle_drink_at_inn,
    _handle_work_on_art,
    _handle_read_book
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("createLeisureActivities")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
TRANSPORT_API_URL = os.getenv("TRANSPORT_API_URL", f"{API_BASE_URL}/api/transport")

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initializes connection to Airtable."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    if not api_key or not base_id:
        log.error(f"{LogColors.FAIL}Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID.{LogColors.ENDC}")
        return None
    try:
        api = Api(api_key.strip())
        tables = {
            'citizens': api.table(base_id.strip(), 'CITIZENS'),
            'buildings': api.table(base_id.strip(), 'BUILDINGS'),
            'activities': api.table(base_id.strip(), 'ACTIVITIES'),
            'resources': api.table(base_id.strip(), 'RESOURCES'), # Needed by some handlers
            'contracts': api.table(base_id.strip(), 'CONTRACTS'), # Needed by some handlers
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection initialized successfully.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def create_leisure_activities(dry_run: bool = False, target_citizen_username: Optional[str] = None, forced_activity_type: Optional[str] = None):
    """Main function to force leisure activities."""
    log_header_msg = f"Force Create Leisure Activities (dry_run={dry_run}"
    if target_citizen_username:
        log_header_msg += f", citizen={target_citizen_username}"
    if forced_activity_type:
        log_header_msg += f", activity_type={forced_activity_type}"
    log_header_msg += ")"
    log_header(log_header_msg, LogColors.HEADER)

    tables = initialize_airtable()
    if not tables: return

    # Get current real times, these might be used for logging or other non-handler purposes
    current_real_venice_dt = datetime.now(VENICE_TIMEZONE)
    current_real_utc_dt = current_real_venice_dt.astimezone(pytz.UTC)
    
    resource_defs = get_resource_types_from_api(API_BASE_URL)
    building_type_defs = get_building_types_from_api(API_BASE_URL)

    if not resource_defs or not building_type_defs:
        log.error(f"{LogColors.FAIL}Failed to load resource or building definitions. Exiting.{LogColors.ENDC}")
        return

    citizens_to_process = []
    if target_citizen_username:
        citizen_rec = get_citizen_record(tables, target_citizen_username)
        if citizen_rec and citizen_rec['fields'].get('InVenice'):
            citizens_to_process.append(citizen_rec)
        elif citizen_rec:
            log.warning(f"{LogColors.WARNING}Target citizen {target_citizen_username} is not in Venice. Skipping.{LogColors.ENDC}")
        else:
            log.error(f"{LogColors.FAIL}Target citizen {target_citizen_username} not found.{LogColors.ENDC}")
            return
    else:
        try:
            all_in_venice_citizens = tables['citizens'].all(formula="{InVenice}=1")
            citizens_to_process.extend(all_in_venice_citizens)
            log.info(f"Found {len(citizens_to_process)} citizens in Venice.")
        except Exception as e_fetch_all:
            log.error(f"{LogColors.FAIL}Error fetching all citizens in Venice: {e_fetch_all}{LogColors.ENDC}")
            return
            
    if not citizens_to_process:
        log.info("No citizens in Venice to process.")
        return

    activities_created_count = 0
    
    # (handler_function, priority_value, description_for_log, type_string_for_arg)
    # Priority values are used for weighting if not forcing a type.
    # Note: Lower priority value = higher weight (100 - priority)
    base_priority_values = {
        "attend_theater_performance": 45,
        "drink_at_inn": 40,
        "work_on_art": 35,
        "read_book": 55,
    }
    
    # Class-specific priority modifiers (lower value = higher priority)
    # Note: createLeisureActivities doesn't include pray/attend_mass handlers
    class_priority_modifiers = {
        "Nobili": {
            "attend_theater_performance": 25,  # Higher priority for nobility
            "read_book": 35,
            "drink_at_inn": 55,  # Lower priority for public drinking
        },
        "Clero": {
            "read_book": 35,  # Higher priority for reading
            "attend_theater_performance": 70,  # Lower priority for entertainment
            "drink_at_inn": 80,  # Much lower priority for drinking
        },
        "Cittadini": {
            "read_book": 40,
            "attend_theater_performance": 40,
            "drink_at_inn": 35,  # Business and social meetings
        },
        "Artisti": {
            "work_on_art": 20,  # Highest priority for art
            "attend_theater_performance": 35,
            "drink_at_inn": 35,
        },
        "Popolani": {
            "drink_at_inn": 35,
            "attend_theater_performance": 60,  # Lower priority
            "read_book": 75,  # Much lower priority
        },
        "Facchini": {
            "drink_at_inn": 30,  # Highest priority
            "attend_theater_performance": 75,  # Very low priority
            "read_book": 85,  # Extremely low priority
        },
        "Scientisti": {
            "read_book": 25,  # Highest priority for reading
            "attend_theater_performance": 50,
            "drink_at_inn": 60,  # Lower priority
            "work_on_art": 70,  # Not their primary focus
        }
    }
    
    for citizen_record_full in citizens_to_process:
        citizen_custom_id = citizen_record_full['fields'].get('CitizenId')
        citizen_username = citizen_record_full['fields'].get('Username')
        citizen_airtable_id = citizen_record_full['id']
        citizen_name = f"{citizen_record_full['fields'].get('FirstName', '')} {citizen_record_full['fields'].get('LastName', '')}".strip() or citizen_username
        citizen_social_class = citizen_record_full['fields'].get('SocialClass', 'Facchini')
        
        log.info(f"\nProcessing citizen: {citizen_name} (Class: {citizen_social_class})")
        
        # Apply class-specific modifiers for this citizen
        priority_values = base_priority_values.copy()
        if citizen_social_class in class_priority_modifiers:
            for activity, new_priority in class_priority_modifiers[citizen_social_class].items():
                if activity in priority_values:
                    priority_values[activity] = new_priority
        
        leisure_activity_handlers_config = {
            "attend_theater_performance": (_handle_attend_theater_performance, priority_values["attend_theater_performance"], "Aller au théâtre"),
            "drink_at_inn": (_handle_drink_at_inn, priority_values["drink_at_inn"], "Boire un verre à l'auberge"),
            "work_on_art": (_handle_work_on_art, priority_values["work_on_art"], "Travailler sur une œuvre d'art (Artisti)"),
            "read_book": (_handle_read_book, priority_values["read_book"], "Lire un livre"),
        }
        leisure_candidates_for_weighted_selection = [
            (func, prio, desc) for type_str, (func, prio, desc) in leisure_activity_handlers_config.items()
        ]

        # Determine a simulated leisure time for this citizen
        # This time will be passed to the handlers to bypass their internal time checks.
        schedule = SOCIAL_CLASS_SCHEDULES.get(citizen_social_class, {})
        leisure_periods = schedule.get("leisure", [])
        simulated_leisure_hour = 19 # Default: 7 PM, a common leisure hour
        if leisure_periods:
            # Use the start of the first defined leisure period for this class
            # Ensure it's not an overnight period start that might be confusing if we take middle
            simulated_leisure_hour = leisure_periods[0][0] 
            if simulated_leisure_hour == 0 and len(leisure_periods[0]) > 1 and leisure_periods[0][1] > 0: # e.g. (0,8) for Nobili
                 pass # 00:00 is fine as a start
            elif leisure_periods[0][0] > leisure_periods[0][1] and leisure_periods[0][0] >= 20 : # Overnight like (22,2)
                 simulated_leisure_hour = leisure_periods[0][0] # Start of the overnight period
            # For other cases, the first start hour is usually fine.
        
        # Use current_real_venice_dt's date, but replace the hour for simulation
        simulated_venice_dt_for_handler = current_real_venice_dt.replace(hour=simulated_leisure_hour, minute=0, second=0, microsecond=0)
        simulated_utc_dt_for_handler = simulated_venice_dt_for_handler.astimezone(pytz.UTC)
        log.info(f"Simulating time for {citizen_name} as {simulated_venice_dt_for_handler.strftime('%Y-%m-%d %H:%M:%S %Z%z')} (UTC: {simulated_utc_dt_for_handler.isoformat()}) for handler calls.")

        citizen_position_str_val = citizen_record_full['fields'].get('Position')
        citizen_position: Optional[Dict[str, float]] = None
        try:
            if citizen_position_str_val: citizen_position = json.loads(citizen_position_str_val)
        except Exception: pass

        if not citizen_position:
            citizen_position = _fetch_and_assign_random_starting_position(tables, citizen_record_full, API_BASE_URL)
            if citizen_position:
                citizen_position_str_val = json.dumps(citizen_position)
            else:
                log.warning(f"Could not assign position to {citizen_name}. Skipping.")
                continue
        
        # Base arguments for handlers, using SIMULATED time to bypass handler's internal time checks
        # The 'False' is for the 'is_night_dummy' argument in the handlers' signature.
        base_handler_args_simulated_time = (
            tables, citizen_record_full, False, resource_defs, building_type_defs,
            simulated_venice_dt_for_handler, simulated_utc_dt_for_handler, # Use simulated times
            TRANSPORT_API_URL, API_BASE_URL,
            citizen_position, citizen_custom_id, citizen_username, citizen_airtable_id, citizen_name, citizen_position_str_val,
            citizen_social_class
        )
        # These args will be used for both check_only=True and check_only=False calls
        handler_args_for_creation = base_handler_args_simulated_time + (False,) # check_only=False
        handler_args_for_check = base_handler_args_simulated_time + (True,)   # check_only=True

        activity_created_for_citizen = False
        selected_handler_desc = "N/A"

        if forced_activity_type:
            if forced_activity_type in leisure_activity_handlers_config:
                handler_func, _, desc = leisure_activity_handlers_config[forced_activity_type]
                selected_handler_desc = desc
                log.info(f"Forcing leisure activity '{desc}' for {citizen_name}.")
                if dry_run:
                    log.info(f"[DRY RUN] Would attempt to create '{desc}' for {citizen_name}.")
                    activities_created_count += 1
                    activity_created_for_citizen = True
                else:
                    created_activity = handler_func(*handler_args_for_creation)
                    if created_activity:
                        activities_created_count += 1
                        activity_created_for_citizen = True
            else:
                log.warning(f"Forced activity type '{forced_activity_type}' is not a known leisure activity. Skipping for {citizen_name}.")
        else:
            eligible_options: List[Tuple[Any, float, str]] = []
            for handler_func_check, priority_val_check, desc_log_check in leisure_candidates_for_weighted_selection:
                try:
                    can_execute = handler_func_check(*handler_args_for_check)
                    if can_execute:
                        weight = 100.0 - priority_val_check 
                        if weight <= 0: weight = 1.0
                        eligible_options.append((handler_func_check, weight, desc_log_check))
                        log.info(f"  Activity '{desc_log_check}' is ELIGIBLE for {citizen_name}.")
                    else:
                        log.info(f"  Activity '{desc_log_check}' is NOT ELIGIBLE for {citizen_name} (handler check returned False).")
                except Exception as e_check_leisure:
                    log.error(f"  Error checking eligibility for '{desc_log_check}' for {citizen_name}: {e_check_leisure}")
            
            if eligible_options:
                handlers_to_choose_from = [opt[0] for opt in eligible_options]
                weights = [opt[1] for opt in eligible_options]
                descriptions_for_log = [opt[2] for opt in eligible_options]

                chosen_indices = random.choices(range(len(handlers_to_choose_from)), weights=weights, k=1)
                if chosen_indices:
                    chosen_handler_index = chosen_indices[0]
                    selected_handler_func = handlers_to_choose_from[chosen_handler_index]
                    selected_handler_desc = descriptions_for_log[chosen_handler_index]

                    log.info(f"Selected leisure activity '{selected_handler_desc}' for {citizen_name} by weighted choice.")
                    if dry_run:
                        log.info(f"[DRY RUN] Would attempt to create '{selected_handler_desc}' for {citizen_name}.")
                        activities_created_count += 1
                        activity_created_for_citizen = True
                    else:
                        created_activity = selected_handler_func(*handler_args_for_creation)
                        if created_activity:
                            activities_created_count += 1
                            activity_created_for_citizen = True
            else:
                log.info(f"No eligible leisure activities found for {citizen_name} after checking.")

        if activity_created_for_citizen:
            log.info(f"Leisure activity ('{selected_handler_desc}') {'simulated' if dry_run else 'creation attempted/succeeded'} for {citizen_name}.")
        else:
            log.info(f"No leisure activity created for {citizen_name}.")
            
    log_header(f"Force Create Leisure Activities Finished. Activities Triggered/Simulated: {activities_created_count}", LogColors.HEADER)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Force creation of leisure activities for citizens in Venice.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the process without making changes.")
    parser.add_argument("--citizen", type=str, help="Process a specific citizen by username.")
    parser.add_argument("--activity-type", type=str, choices=["attend_theater_performance", "drink_at_inn", "work_on_art", "read_book"], help="Force a specific type of leisure activity.")
    
    args = parser.parse_args()

    create_leisure_activities(dry_run=args.dry_run, target_citizen_username=args.citizen, forced_activity_type=args.activity_type)

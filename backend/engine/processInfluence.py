#!/usr/bin/env python3
"""
Process Influence Script for La Serenissima.

This script:
1. Fetches all building type definitions from the API.
2. Identifies building types that have a "dailyInfluence" value.
3. For each such building type:
    a. Fetches all existing buildings of that type.
    b. For each building, identifies its owner.
    c. If an owner exists (and is not the state):
        i. Retrieves the owner's citizen record.
        ii. Adds the "dailyInfluence" value to the citizen's "Influence" field.
        iii. Creates a notification for the owner about this influence gain.
"""

import os
import sys
import json
import traceback
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Any
import requests
from dotenv import load_dotenv
from pyairtable import Api, Table
import argparse
import logging

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("process_influence")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")

# Import shared utilities from activity_helpers
try:
    from backend.engine.utils.activity_helpers import (
        LogColors, 
        log_header, 
        _escape_airtable_value,
        VENICE_TIMEZONE,
        get_building_types_from_api, # Use the helper
        get_citizen_record, # Use the helper
        get_venice_time_now # Import for current Venice time
    )
except ImportError:
    class LogColors: HEADER=OKBLUE=OKCYAN=OKGREEN=WARNING=FAIL=ENDC=BOLD=LIGHTBLUE=""
    def log_header(msg, color=None): print(f"--- {msg} ---")
    def _escape_airtable_value(val): return str(val).replace("'", "\\'")
    VENICE_TIMEZONE = pytz.timezone('Europe/Rome')
    def get_building_types_from_api(base_url=None): return {}
    def get_citizen_record(tables, username): return None
    def get_venice_time_now(): return datetime.now(VENICE_TIMEZONE) # Fallback
    log.error("Failed to import from backend.engine.utils.activity_helpers. Using fallback definitions.")

# --- Helper Functions ---

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initialize connection to Airtable."""
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")

    if not airtable_api_key or not airtable_base_id:
        log.error(f"{LogColors.FAIL}Error: Airtable credentials not found in environment variables.{LogColors.ENDC}")
        return None

    try:
        api = Api(airtable_api_key)
        tables = {
            "buildings": api.table(airtable_base_id, "BUILDINGS"),
            "citizens": api.table(airtable_base_id, "CITIZENS"),
            "notifications": api.table(airtable_base_id, "NOTIFICATIONS"),
            "stratagems": api.table(airtable_base_id, "STRATAGEMS") # Ajout de la table STRATAGEMS
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection initialized successfully.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

# --- Main Processing Logic ---

def process_daily_influence(dry_run: bool = False, building_type_filter: Optional[str] = None):
    log_header_message = f"Process Daily Influence (dry_run={dry_run})"
    if building_type_filter:
        log_header_message += f" for Building Type: {building_type_filter}"
    log_header(log_header_message, LogColors.HEADER)

    tables = initialize_airtable()
    if not tables:
        return

    building_type_defs = get_building_types_from_api(API_BASE_URL)
    if not building_type_defs:
        log.error(f"{LogColors.FAIL}Failed to get building type definitions. Aborting.{LogColors.ENDC}")
        return
    
    influence_granting_building_types: Dict[str, float] = {}
    for type_name, type_def in building_type_defs.items():
        daily_influence = type_def.get("dailyInfluence")
        if daily_influence is not None:
            try:
                influence_value = float(daily_influence)
                if influence_value > 0:
                    influence_granting_building_types[type_name] = influence_value
                    log.info(f"Building type '{type_name}' grants {influence_value} daily influence.")
            except ValueError:
                log.warning(f"Invalid non-numeric dailyInfluence value '{daily_influence}' for building type '{type_name}'. Skipping.")

    if not influence_granting_building_types:
        log.info("No building types found with a 'dailyInfluence' value. Nothing to process.")
        return

    for building_type, influence_to_grant in influence_granting_building_types.items():
        if building_type_filter and building_type != building_type_filter:
            log.info(f"Skipping building type '{building_type}' due to filter.")
            continue

        log.info(f"{LogColors.OKBLUE}--- Processing buildings of type: {building_type} (Influence: {influence_to_grant}) ---{LogColors.ENDC}")
        
        formula = f"{{Type}}='{_escape_airtable_value(building_type)}'"
        
        try:
            buildings_of_this_type = tables["buildings"].all(formula=formula)
            if not buildings_of_this_type:
                log.info(f"No buildings of type '{building_type}' found.")
                continue

            for building_record in buildings_of_this_type:
                building_name_log = building_record['fields'].get('Name', building_record['fields'].get('BuildingId', building_record['id']))
                owner_username = building_record['fields'].get('Owner')

                if not owner_username:
                    log.info(f"  Building {building_name_log} has no owner. Skipping influence grant.")
                    continue
                
                # Removed the condition that skips ConsiglioDeiDieci for influence grant.
                # Now, ConsiglioDeiDieci will also be processed for influence.

                log.info(f"  Processing {building_type}: {building_name_log} (Owner: {owner_username})")

                owner_citizen_record = get_citizen_record(tables, owner_username)
                if not owner_citizen_record:
                    log.warning(f"{LogColors.WARNING}    Owner citizen {owner_username} not found for building {building_name_log}. Cannot grant influence.{LogColors.ENDC}")
                    continue

                # Check LastActiveAt for human citizens
                is_ai = owner_citizen_record['fields'].get('IsAI', False)
                if not is_ai:
                    last_active_at_str = owner_citizen_record['fields'].get('LastActiveAt')
                    if last_active_at_str:
                        try:
                            # Ensure LastActiveAt is timezone-aware (assume UTC if not specified, then convert to Venice time)
                            last_active_at_dt = pytz.utc.localize(datetime.fromisoformat(last_active_at_str.replace("Z", ""))).astimezone(VENICE_TIMEZONE)
                            
                            # Calculate the beginning of the previous day in Venice time
                            now_venice = get_venice_time_now()
                            start_of_today_venice = now_venice.replace(hour=0, minute=0, second=0, microsecond=0)
                            start_of_previous_day_venice = start_of_today_venice - timedelta(days=1)

                            if last_active_at_dt < start_of_previous_day_venice:
                                log.info(f"    Skipping influence for human citizen {owner_username} (building {building_name_log}). LastActiveAt ({last_active_at_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}) is before {start_of_previous_day_venice.strftime('%Y-%m-%d %H:%M:%S %Z')}.")
                                continue
                            else:
                                log.info(f"    Processing influence for human citizen {owner_username} (building {building_name_log}). LastActiveAt ({last_active_at_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}) is recent enough.")
                        except ValueError as e_date:
                            log.warning(f"{LogColors.WARNING}    Could not parse LastActiveAt ('{last_active_at_str}') for human citizen {owner_username}. Error: {e_date}. Processing influence as fallback.{LogColors.ENDC}")
                    else:
                        log.warning(f"{LogColors.WARNING}    Human citizen {owner_username} (building {building_name_log}) has no LastActiveAt. Processing influence as fallback.{LogColors.ENDC}")
                
                owner_airtable_id = owner_citizen_record['id']
                current_influence = float(owner_citizen_record['fields'].get('Influence', 0.0))
                new_influence = current_influence + influence_to_grant

                log.info(f"    Granting {influence_to_grant} influence to {owner_username}. Current: {current_influence}, New: {new_influence}")

                if not dry_run:
                    try:
                        tables["citizens"].update(owner_airtable_id, {"Influence": new_influence})
                        
                        # Create notification for the owner
                        notification_content = f"Vous avez gagné {influence_to_grant} point(s) d'influence pour la possession de {building_name_log} ({building_type})."
                        notification_details = {
                            "event_type": "daily_building_influence_gain",
                            "building_id": building_record['fields'].get('BuildingId'),
                            "building_name": building_name_log,
                            "building_type": building_type,
                            "influence_gained": influence_to_grant,
                            "new_total_influence": new_influence
                        }
                        tables['notifications'].create({
                            "Type": "daily_influence_reward",
                            "Content": notification_content,
                            "Details": json.dumps(notification_details),
                            "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                            "Citizen": owner_username 
                        })
                        log.info(f"    Notification de gain d'influence créée pour {owner_username}.")
                    except Exception as e_update:
                        log.error(f"{LogColors.FAIL}    Failed to update influence or create notification for {owner_username}: {e_update}{LogColors.ENDC}")
                else:
                    log.info(f"    [DRY RUN] Would update influence for {owner_username} to {new_influence} and create notification.")

        except Exception as e:
            log.error(f"{LogColors.FAIL}Error processing buildings of type '{building_type}': {e}{LogColors.ENDC}")
            traceback.print_exc()

    log.info(f"{LogColors.OKGREEN}Daily influence processing finished.{LogColors.ENDC}")

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process daily influence from buildings.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, performs a dry run and does not save changes to Airtable."
    )
    parser.add_argument(
        "--buildingType",
        type=str,
        default=None,
        help="Optional: Process only a single building type."
    )
    args = parser.parse_args()

    process_daily_influence(dry_run=args.dry_run, building_type_filter=args.buildingType)

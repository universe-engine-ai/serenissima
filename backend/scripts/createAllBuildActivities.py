#!/usr/bin/env python3
"""
Create All Build Activities Script for La Serenissima.

This script identifies AI citizens operating construction buildings (masons_lodge, 
master_builders_workshop) and triggers their construction-related activity logic.
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime, timezone
import pytz # Pour VENICE_TIMEZONE
from typing import Optional, Dict # Ajout de l'importation

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

from backend.engine.utils.activity_helpers import (
    LogColors, VENICE_TIMEZONE, _escape_airtable_value,
    get_resource_types_from_api, get_building_types_from_api,
    get_citizen_record, get_building_record, log_header,
    get_building_storage_details, _calculate_distance_meters, get_path_between_points, # Added imports
    _get_building_position_coords # Ensure this is also imported if not already implicitly
)
from backend.engine.logic.construction_logic import handle_construction_worker_activity
from backend.engine.activity_creators import try_create_construct_building_activity # Added import

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("createAllBuildActivities")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Constants
TRANSPORT_API_URL = os.getenv("TRANSPORT_API_URL", "http://localhost:3000/api/transport")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")

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
            'activities': api.table(base_id.strip(), 'ACTIVITIES'), # Needed by handle_construction_worker_activity
            'contracts': api.table(base_id.strip(), 'CONTRACTS'),   # Needed by handle_construction_worker_activity
            'resources': api.table(base_id.strip(), 'RESOURCES'),   # Needed by handle_construction_worker_activity
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection initialized successfully.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def create_all_build_activities(dry_run: bool = False):
    """Main function to iterate through construction buildings and trigger operator logic."""
    log_header_msg = f"Create All Build Activities Process (dry_run={dry_run})"
    log_header(log_header_msg, LogColors.HEADER)

    tables = initialize_airtable()
    if not tables: return

    now_venice_dt = datetime.now(VENICE_TIMEZONE)
    now_utc_dt = now_venice_dt.astimezone(timezone.utc)
    
    resource_defs = get_resource_types_from_api(API_BASE_URL)
    building_type_defs = get_building_types_from_api(API_BASE_URL)

    if not resource_defs or not building_type_defs:
        log.error(f"{LogColors.FAIL}Failed to load resource or building definitions. Exiting.{LogColors.ENDC}")
        return

    construction_building_types = ["masons_lodge", "master_builders_workshop"]
    type_conditions = [f"{{Type}}='{_escape_airtable_value(bt)}'" for bt in construction_building_types]
    formula = f"OR({', '.join(type_conditions)})"
    
    log.info(f"Fetching construction buildings with formula: {formula}")
    try:
        construction_buildings = tables['buildings'].all(formula=formula)
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching construction buildings: {e}{LogColors.ENDC}")
        return

    log.info(f"Found {len(construction_buildings)} construction buildings to evaluate.")
    
    activities_triggered_count = 0

    for workplace_record in construction_buildings:
        workplace_id = workplace_record['fields'].get('BuildingId', workplace_record['id'])
        workplace_type = workplace_record['fields'].get('Type')
        operator_username = workplace_record['fields'].get('RunBy')

        if not operator_username:
            log.info(f"{LogColors.OKBLUE}Construction building {workplace_id} (Type: {workplace_type}) has no operator (RunBy). Skipping.{LogColors.ENDC}")
            continue

        log.info(f"{LogColors.OKCYAN}Processing construction building {workplace_id} (Type: {workplace_type}), Operator: {operator_username}{LogColors.ENDC}")

        citizen_record = get_citizen_record(tables, operator_username)
        if not citizen_record:
            log.warning(f"  Operator {operator_username} for building {workplace_id} not found. Skipping.")
            continue
        
        if not citizen_record['fields'].get('IsAI'):
            log.info(f"  Operator {operator_username} for building {workplace_id} is not an AI. Skipping.")
            continue
        
        if not citizen_record['fields'].get('InVenice'):
            log.info(f"  Operator {operator_username} for building {workplace_id} is not in Venice. Skipping.")
            continue

        log.info(f"  AI Operator {operator_username} found for {workplace_id}. Attempting to trigger construction logic.")
        
        if dry_run:
            log.info(f"  [DRY RUN] Would call handle_construction_worker_activity for {operator_username} at {workplace_id}.")
            # Simulate a potential activity trigger for counting purposes in dry run
            activities_triggered_count +=1 
        else:
            try:
                activity_created = handle_construction_worker_activity(
                    tables=tables,
                    citizen_record=citizen_record,
                    workplace_record=workplace_record,
                    building_type_defs=building_type_defs,
                    resource_defs=resource_defs,
                    now_venice_dt=now_venice_dt,
                    now_utc_dt=now_utc_dt,
                    transport_api_url=TRANSPORT_API_URL,
                    api_base_url=API_BASE_URL
                )
                if activity_created:
                    log.info(f"  {LogColors.OKGREEN}Construction logic triggered an activity for {operator_username} at {workplace_id}.{LogColors.ENDC}")
                    activities_triggered_count += 1
                else:
                    log.info(f"  {LogColors.OKBLUE}Construction logic for {operator_username} at {workplace_id} did not result in a new activity at this time.{LogColors.ENDC}")
            except Exception as e_handler:
                log.error(f"  {LogColors.FAIL}Error calling handle_construction_worker_activity for {operator_username} at {workplace_id}: {e_handler}{LogColors.ENDC}")
                import traceback
                log.error(traceback.format_exc())

    # --- Deuxième passe: Occupants des sites non construits ---
    log.info(f"\n{LogColors.HEADER}--- Processing Occupants of Unconstructed Sites for Direct Construction ---{LogColors.ENDC}")
    unconstructed_buildings_formula = "{ConstructionMinutesRemaining} > 0"
    try:
        all_unconstructed_sites = tables['buildings'].all(formula=unconstructed_buildings_formula)
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching unconstructed buildings: {e}{LogColors.ENDC}")
        all_unconstructed_sites = []

    log.info(f"Found {len(all_unconstructed_sites)} unconstructed building sites to evaluate for occupant participation.")

    for site_record in all_unconstructed_sites:
        site_id = site_record['fields'].get('BuildingId', site_record['id'])
        site_type_str = site_record['fields'].get('Type')
        occupant_username = site_record['fields'].get('Occupant')

        if not occupant_username:
            continue

        occupant_citizen_record = get_citizen_record(tables, occupant_username)
        if not (occupant_citizen_record and occupant_citizen_record['fields'].get('IsAI') and occupant_citizen_record['fields'].get('InVenice')):
            continue

        # Check if occupant already has a relevant construction/goto activity for this site
        existing_activity_formula = f"AND({{Citizen}}='{_escape_airtable_value(occupant_username)}', {{ToBuilding}}='{_escape_airtable_value(site_id)}', OR({{Type}}='construct_building', {{Type}}='goto_construction_site', {{Type}}='goto_location'), NOT(OR({{Status}}='processed', {{Status}}='failed', {{Status}}='error')))"
        try:
            if tables['activities'].all(formula=existing_activity_formula, max_records=1):
                log.info(f"Occupant {occupant_username} of site {site_id} already has a relevant construction/goto activity. Skipping.")
                continue
        except Exception as e_check_act:
            log.error(f"Error checking existing activities for {occupant_username} at {site_id}: {e_check_act}. Skipping.")
            continue
            
        log.info(f"Evaluating occupant {occupant_username} of site {site_id} (Type: {site_type_str}) for direct construction.")

        site_building_def = building_type_defs.get(site_type_str)
        if not site_building_def:
            log.error(f"Could not get building definition for site type {site_type_str}. Skipping occupant construction for {site_id}.")
            continue

        construction_costs_from_def = site_building_def.get('constructionCosts', {})
        required_materials_for_project = {}
        for k, v_raw in construction_costs_from_def.items():
            if k == 'ducats':
                continue
            try:
                if isinstance(v_raw, (int, float)):
                    val_float = float(v_raw)
                elif isinstance(v_raw, str):
                    val_float = float(v_raw)
                else:
                    log.warning(f"Material {k} for site {site_id} has unexpected value type {type(v_raw)}: {v_raw}. Skipping.")
                    continue
                required_materials_for_project[k] = val_float
            except ValueError:
                log.warning(f"Could not convert value '{v_raw}' to float for material '{k}' for site {site_id}. Skipping.")
        
        site_owner_username = site_record['fields'].get('Owner')
        if not site_owner_username:
            log.warning(f"Site {site_id} has no Owner. Cannot determine material ownership for occupant construction. Skipping.")
            continue
            
        _, site_inventory_map = get_building_storage_details(tables, site_id, site_owner_username)
        log.debug(f"Site {site_id} (Owner: {site_owner_username}) inventory: {site_inventory_map}. Required for project: {required_materials_for_project}")

        construction_minutes_remaining_site = float(site_record['fields'].get('ConstructionMinutesRemaining', 0))
        if construction_minutes_remaining_site <= 0:
            log.info(f"Site {site_id} construction already complete. Occupant {occupant_username} will not construct.")
            continue

        # Calculate max permissible work duration based on available materials at the site
        max_permissible_work_minutes_for_occupant = construction_minutes_remaining_site
        total_construction_time_for_building = float(site_building_def.get('constructionMinutes', 0))

        if total_construction_time_for_building <= 0:
            log.warning(f"Building type {site_type_str} for site {site_id} has invalid total_construction_time ({total_construction_time_for_building}). Using default of 120 minutes for material calculation.")
            total_construction_time_for_building = 120.0 # Default construction time
        
        can_occupant_do_any_work = True
        if not required_materials_for_project:
            log.info(f"Site {site_id}: No materials listed in definition. Occupant {occupant_username} can construct for full duration.")
        else:
            for material, needed_qty_total_for_project in required_materials_for_project.items():
                on_site_qty = float(site_inventory_map.get(material, 0.0))
                if on_site_qty <= 0.001 and needed_qty_total_for_project > 0:
                    can_occupant_do_any_work = False
                    log.info(f"Site {site_id} is completely missing required material {material} for occupant {occupant_username}.")
                    break
                if needed_qty_total_for_project > 0: # Avoid division by zero
                    minutes_this_material_supports = (on_site_qty / needed_qty_total_for_project) * total_construction_time_for_building
                    max_permissible_work_minutes_for_occupant = min(max_permissible_work_minutes_for_occupant, minutes_this_material_supports)
        
        if not can_occupant_do_any_work:
            log.info(f"Site {site_id} does not have essential materials for occupant {occupant_username} to construct.")
            continue
        
        if max_permissible_work_minutes_for_occupant < 1: # Needs at least 1 minute of work possible
            log.info(f"Site {site_id} has insufficient materials for occupant {occupant_username} to perform meaningful work ({max_permissible_work_minutes_for_occupant:.2f} mins possible).")
            continue

        log.info(f"Site {site_id} has materials for occupant {occupant_username} to construct for up to {max_permissible_work_minutes_for_occupant:.2f} minutes.")
        
        # Determine actual work duration for this activity
        work_duration_occupant = min(60, int(max_permissible_work_minutes_for_occupant)) # Max 60 mins, or less if limited by materials/remaining time
        
        if work_duration_occupant > 0:
            occupant_position_str = occupant_citizen_record['fields'].get('Position')
            occupant_position = json.loads(occupant_position_str) if occupant_position_str else None
            site_position = _get_building_position_coords(site_record)

            if not occupant_position or not site_position:
                log.warning(f"Missing occupant or site position for {occupant_username} at {site_id}. Skipping construction task.")
                continue

            path_to_site_for_occupant = None
            if _calculate_distance_meters(occupant_position, site_position) > 20:
                log.info(f"Occupant {occupant_username} is not at site {site_id}. Pathfinding...")
                path_to_site_for_occupant = get_path_between_points(occupant_position, site_position, TRANSPORT_API_URL)
                if not (path_to_site_for_occupant and path_to_site_for_occupant.get('success')):
                    log.warning(f"Pathfinding to site {site_id} failed for occupant {occupant_username}. Skipping construction task.")
                    continue
            
            # work_duration_occupant is already calculated above
            if dry_run:
                log.info(f"[DRY RUN] Would call try_create_construct_building_activity for occupant {occupant_username} at site {site_id} for {work_duration_occupant} minutes.")
                activities_triggered_count += 1
            else:
                if try_create_construct_building_activity(
                    tables, occupant_citizen_record, site_record,
                    work_duration_occupant, 
                    contract_custom_id_or_airtable_id=None, # No formal contract for self-construction
                    path_data=path_to_site_for_occupant,
                    current_time_utc=now_utc_dt
                ):
                    log.info(f"{LogColors.OKGREEN}Created 'construct_building' activity for occupant {occupant_username} at site {site_id} for {work_duration_occupant} minutes.{LogColors.ENDC}")
                    activities_triggered_count += 1
                else:
                    log.error(f"{LogColors.FAIL}Failed to create 'construct_building' activity for occupant {occupant_username} at site {site_id}.{LogColors.ENDC}")
        else: # This else corresponds to if work_duration_occupant <= 0
            log.info(f"Site {site_id} does not have sufficient materials for occupant {occupant_username} to construct at this time (permissible work: {max_permissible_work_minutes_for_occupant:.2f} mins).")


    log_header(f"Create All Build Activities Process Finished. Activities Triggered/Simulated: {activities_triggered_count}", LogColors.HEADER)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Force creation of build activities for construction buildings.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the process without making changes.")
    args = parser.parse_args()

    create_all_build_activities(dry_run=args.dry_run)

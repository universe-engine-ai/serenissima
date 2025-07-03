#!/usr/bin/env python3
"""
Script to accelerate the construction of a specific building by repeatedly
calling createActivities.py and processAllActivitiesNow.py for the relevant citizen.
"""

import os
import sys
import subprocess
import logging
import argparse
import time
import json
from typing import Optional, Dict, Any, List # Added List

# Add project root to sys.path for consistent imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

try:
    from backend.engine.utils.activity_helpers import LogColors, get_building_record, _escape_airtable_value
    from dateutil import parser as dateutil_parser # Added import
except ImportError:
    class LogColors: #type: ignore
        HEADER = OKBLUE = OKGREEN = WARNING = FAIL = ENDC = BOLD = ''
    def get_building_record(tables: Dict[str, Table], building_id_input: str) -> Optional[Dict[str, Any]]: #type: ignore
        # Minimal fallback if imports fail during standalone execution (should not happen in normal use)
        log.error("Failed to import get_building_record from activity_helpers.")
        try:
            # Attempt direct fetch, assuming building_id_input is the custom BuildingId
            # To avoid potential parsing issues with nested quotes and escapes in f-strings:
            escaped_building_id = building_id_input.replace("'", "\\'")
            formula = f"{{BuildingId}} = '{escaped_building_id}'"
            records = tables['buildings'].all(formula=formula, max_records=1)
            return records[0] if records else None
        except Exception as e:
            log.error(f"Fallback get_building_record failed: {e}")
            return None
    def _escape_airtable_value(value: Any) -> str: #type: ignore
        if isinstance(value, str):
            return value.replace("'", "\\'")
        return str(value)
    # Fallback for dateutil_parser if activity_helpers fails to import it (less likely)
    try:
        from dateutil import parser as dateutil_parser #type: ignore
    except ImportError:
        print("ERROR: Failed to import dateutil.parser. Date parsing for activities will fail.") # Changed log.error to print
        dateutil_parser = None #type: ignore


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("buildFast")

# Load environment variables from .env file
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initializes and returns a dictionary of Airtable Table objects."""
    api_key_env = os.environ.get('AIRTABLE_API_KEY')
    base_id_env = os.environ.get('AIRTABLE_BASE_ID')

    api_key = api_key_env.strip() if api_key_env else None
    base_id = base_id_env.strip() if base_id_env else None

    if not api_key or not base_id:
        log.error(f"{LogColors.FAIL}Airtable API Key or Base ID not configured.{LogColors.ENDC}")
        return None
    try:
        # Using requests session from pyairtable's Api default
        api = Api(api_key)
        tables = {
            'buildings': api.table(base_id, 'BUILDINGS'),
            'activities': api.table(base_id, 'ACTIVITIES'), # Needed to check last activity status
            'contracts': api.table(base_id, 'CONTRACTS'), # Added contracts table
        }
        # Test connection
        tables['buildings'].all(max_records=1)
        tables['contracts'].all(max_records=1) # Test contracts table connection
        log.info(f"{LogColors.OKGREEN}Airtable connection successful.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def get_activities_for_citizen(tables: Dict[str, Table], citizen_username: str) -> List[Dict]:
    """
    Fetches 'created' or 'in_progress' activities for a specific citizen,
    sorted by StartDate, excluding 'rest' and 'idle'.
    """
    formula_parts = [
        f"{{Citizen}} = '{_escape_airtable_value(citizen_username)}'",
        "OR({Status}='created', {Status}='in_progress')",
        "NOT({Type}='rest')",
        "NOT({Type}='idle')"
    ]
    formula = "AND(" + ", ".join(formula_parts) + ")"
    log.info(f"Fetching activities for citizen '{citizen_username}' with formula: {formula}")
    try:
        all_citizen_activities = tables['activities'].all(formula=formula, fields=['ActivityId', 'StartDate', 'Type', 'Citizen', 'Status'])
        
        valid_activities = []
        if dateutil_parser: # Check if parser was imported
            for activity_record in all_citizen_activities:
                start_date_str = activity_record['fields'].get('StartDate')
                if start_date_str:
                    try:
                        activity_record['fields']['_ParsedStartDate'] = dateutil_parser.isoparse(start_date_str)
                        valid_activities.append(activity_record)
                    except ValueError:
                        log.warning(f"Could not parse StartDate '{start_date_str}' for activity {activity_record.get('id')}. Skipping.")
                else:
                    log.warning(f"Activity {activity_record.get('id')} missing StartDate. Skipping.")
            
            valid_activities.sort(key=lambda x: x['fields']['_ParsedStartDate'])
        else: # Fallback if dateutil_parser is not available
            log.error("dateutil.parser not available, cannot sort activities by date. Processing order may be incorrect.")
            valid_activities = all_citizen_activities # Return unsorted
        
        log.info(f"{LogColors.OKBLUE}Found {len(valid_activities)} activities for citizen '{citizen_username}'.{LogColors.ENDC}")
        return valid_activities
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching activities for citizen '{citizen_username}': {e}{LogColors.ENDC}")
        return []

def run_script(script_path: str, citizen_username: Optional[str] = None, activity_id_param: Optional[str] = None) -> bool:
    """Runs a given script with specific arguments based on the script type."""
    command = ["python", script_path]
    script_name = os.path.basename(script_path)
    log_context = ""

    if script_name == "createActivities.py":
        if citizen_username:
            command.extend(["--citizen", citizen_username])
            log_context = f"for citizen '{citizen_username}'"
        # No --activityId for createActivities.py
    elif script_name == "processAllActivitiesNow.py":
        if activity_id_param:
            command.extend(["--activityId", activity_id_param])
            log_context = f"for activityId '{activity_id_param}'"
        # No --citizen for processAllActivitiesNow.py as it processes based on its internal query or --activityId
    else: # Fallback for other potential scripts
        if citizen_username: command.extend(["--citizen", citizen_username])
        if activity_id_param: command.extend(["--activityId", activity_id_param])
        log_context = f"with citizen='{citizen_username}', activityId='{activity_id_param}'"
    
    log.info(f"{LogColors.OKBLUE}Running {script_name} {log_context}... Command: {' '.join(command)}{LogColors.ENDC}")
    try:
        # Stream output directly
        process = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr, text=True)
        process.communicate() # Wait for the process to complete
        
        if process.returncode == 0:
            log.info(f"{LogColors.OKGREEN}{script_name} {log_context} completed successfully.{LogColors.ENDC}")
            return True
        else:
            log.error(f"{LogColors.FAIL}{script_name} {log_context} failed with exit code {process.returncode}.{LogColors.ENDC}")
            return False
    except FileNotFoundError:
        log.error(f"{LogColors.FAIL}Error: The script at '{script_path}' was not found.{LogColors.ENDC}")
        return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}An exception occurred while running {script_name} {log_context}: {e}{LogColors.ENDC}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Accelerate building construction.")
    parser.add_argument("--buildingId", required=True, help="The custom BuildingId of the building to construct.")
    parser.add_argument("--maxIterations", type=int, default=100, help="Maximum number of iterations.")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds between cycles.")
    args = parser.parse_args()

    log.info(f"{LogColors.HEADER}--- Starting BuildFast for BuildingId: {args.buildingId} ---{LogColors.ENDC}")

    tables = initialize_airtable()
    if not tables:
        log.error(f"{LogColors.FAIL}Exiting due to Airtable initialization failure.{LogColors.ENDC}")
        return

    # Paths to the scripts
    create_activities_path = os.path.join(PROJECT_ROOT, 'backend', 'engine', 'createActivities.py')
    process_all_activities_path = os.path.join(PROJECT_ROOT, 'backend', 'scripts', 'processAllActivitiesNow.py')

    # Get initial building state
    building_record = get_building_record(tables, args.buildingId)
    if not building_record:
        log.error(f"{LogColors.FAIL}Building with ID '{args.buildingId}' not found.{LogColors.ENDC}")
        return

    if building_record['fields'].get('IsConstructed'):
        log.info(f"{LogColors.OKGREEN}Building '{args.buildingId}' is already constructed.{LogColors.ENDC}")
        return

    # Determine the relevant citizen
    relevant_citizen_username: Optional[str] = None

    # Attempt to find a builder via contract
    try:
        # Assuming BuyerBuilding links to the building being constructed.
        # Or Asset might be used. Let's check for BuyerBuilding first as it's more specific.
        # Status should be active (e.g., 'pending_materials', 'in_progress', or simply not 'completed' or 'failed')
        contract_formula = f"AND({{Type}}='construction_project', {{BuyerBuilding}}='{_escape_airtable_value(args.buildingId)}', NOT(OR({{Status}}='completed', {{Status}}='failed', {{Status}}='cancelled')))"
        log.info(f"Searching for construction contract with formula: {contract_formula}")
        construction_contracts = tables['contracts'].all(formula=contract_formula, max_records=1)

        if construction_contracts:
            contract = construction_contracts[0]
            log.info(f"Found active construction contract: {contract['fields'].get('ContractId', contract['id'])}")
            workshop_building_id = contract['fields'].get('SellerBuilding')
            if workshop_building_id:
                log.info(f"Builder's workshop ID from contract: {workshop_building_id}")
                workshop_record = get_building_record(tables, workshop_building_id)
                if workshop_record:
                    relevant_citizen_username = workshop_record['fields'].get('Occupant')
                    if relevant_citizen_username:
                        log.info(f"Using Occupant of workshop '{workshop_building_id}': {relevant_citizen_username}")
                    else:
                        relevant_citizen_username = workshop_record['fields'].get('RunBy')
                        if relevant_citizen_username:
                            log.info(f"Workshop '{workshop_building_id}' has no Occupant, using RunBy: {relevant_citizen_username}")
                        else:
                            log.warning(f"{LogColors.WARNING}Workshop '{workshop_building_id}' has no Occupant or RunBy.{LogColors.ENDC}")
                else:
                    log.warning(f"{LogColors.WARNING}Could not fetch workshop building record for ID: {workshop_building_id}{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Construction contract {contract['id']} found, but no SellerBuilding specified.{LogColors.ENDC}")
        else:
            log.info(f"No active construction contract found for building '{args.buildingId}'. Assuming self-construction or direct owner involvement.")
    except Exception as e_contract:
        log.error(f"{LogColors.FAIL}Error while searching for construction contract: {e_contract}{LogColors.ENDC}")

    # If no builder found via contract, fall back to owner of the building being constructed
    if not relevant_citizen_username:
        log.info("Falling back to Owner of the target building for construction.")
        relevant_citizen_username = building_record['fields'].get('Owner')
        if relevant_citizen_username:
            log.info(f"Using Owner of target building '{args.buildingId}': {relevant_citizen_username}")
        else:
            # As a last resort, check RunBy of the target building, though less likely for unconstructed.
            relevant_citizen_username = building_record['fields'].get('RunBy')
            if relevant_citizen_username:
                log.info(f"Target building '{args.buildingId}' has no Owner, using RunBy: {relevant_citizen_username}")


    if not relevant_citizen_username:
        log.error(f"{LogColors.FAIL}Could not determine a relevant citizen for building '{args.buildingId}'. Searched contract, then Owner/RunBy of target building.{LogColors.ENDC}")
        return

    log.info(f"Targeting citizen '{relevant_citizen_username}' for construction of '{args.buildingId}'.")

    building_completed_flag = False
    for i in range(args.maxIterations):
        log.info(f"{LogColors.HEADER}--- Iteration {i + 1}/{args.maxIterations} for building {args.buildingId} ---{LogColors.ENDC}")
        iteration_failed_flag = False

        # 1. Call createActivities.py for the relevant_citizen_username
        log.info(f"Calling createActivities.py for {relevant_citizen_username}...")
        if not run_script(create_activities_path, citizen_username=relevant_citizen_username):
            log.error(f"{LogColors.FAIL}createActivities.py failed. Stopping BuildFast.{LogColors.ENDC}")
            iteration_failed_flag = True
        
        if iteration_failed_flag: break

        # 2. Fetch all 'created' or 'in_progress' activities for the relevant_citizen_username, sorted by StartDate
        activities_to_process_this_iteration = get_activities_for_citizen(tables, relevant_citizen_username)

        if not activities_to_process_this_iteration:
            log.info(f"No pending activities found for {relevant_citizen_username} after createActivities. Checking building status.")
        else:
            log.info(f"Found {len(activities_to_process_this_iteration)} activities for {relevant_citizen_username} to process this iteration.")
            for activity_record in activities_to_process_this_iteration:
                activity_id_custom = activity_record['fields'].get('ActivityId')
                activity_type_log = activity_record['fields'].get('Type', 'N/A')
                if not activity_id_custom:
                    log.warning(f"Activity {activity_record['id']} missing ActivityId. Skipping.")
                    continue

                log.info(f"Calling processAllActivitiesNow.py for activityId: {activity_id_custom} (Type: {activity_type_log})...")
                if not run_script(process_all_activities_path, activity_id_param=activity_id_custom):
                    log.error(f"{LogColors.FAIL}processAllActivitiesNow.py failed for activityId {activity_id_custom}. Stopping BuildFast.{LogColors.ENDC}")
                    iteration_failed_flag = True
                    break 
                
                # Check building status after each activity is processed
                current_building_record_inner = get_building_record(tables, args.buildingId)
                if not current_building_record_inner:
                    log.error(f"{LogColors.FAIL}Building '{args.buildingId}' could not be refetched. Stopping BuildFast.{LogColors.ENDC}")
                    iteration_failed_flag = True; break
                if current_building_record_inner['fields'].get('IsConstructed'):
                    log.info(f"{LogColors.OKGREEN}Building '{args.buildingId}' successfully constructed after processing ActivityId {activity_id_custom}!{LogColors.ENDC}")
                    building_completed_flag = True; break
                
                construction_minutes_remaining_inner = current_building_record_inner['fields'].get('ConstructionMinutesRemaining', 0)
                log.info(f"Building '{args.buildingId}' after ActivityId {activity_id_custom}: IsConstructed={current_building_record_inner['fields'].get('IsConstructed')}, MinutesRemaining={construction_minutes_remaining_inner}")


            if iteration_failed_flag or building_completed_flag: break 

        # 3. Final check for this iteration (if not already broken out)
        if not building_completed_flag: # Only check if not already marked as completed
            current_building_record_outer = get_building_record(tables, args.buildingId)
            if not current_building_record_outer:
                log.error(f"{LogColors.FAIL}Building '{args.buildingId}' could not be refetched at end of iteration. Stopping BuildFast.{LogColors.ENDC}")
                break
            if current_building_record_outer['fields'].get('IsConstructed'):
                log.info(f"{LogColors.OKGREEN}Building '{args.buildingId}' successfully constructed at end of iteration!{LogColors.ENDC}")
                building_completed_flag = True
            else:
                construction_minutes_remaining_outer = current_building_record_outer['fields'].get('ConstructionMinutesRemaining', 0)
                log.info(f"Building '{args.buildingId}' status at end of iteration: IsConstructed={current_building_record_outer['fields'].get('IsConstructed')}, MinutesRemaining={construction_minutes_remaining_outer}")


        if building_completed_flag: break 

        if i < args.maxIterations - 1:
            log.info(f"Waiting {args.delay} seconds before next iteration...")
            time.sleep(args.delay)
        elif i == args.maxIterations -1 and not building_completed_flag: # Max iterations reached and not completed
             log.warning(f"{LogColors.WARNING}Max iterations ({args.maxIterations}) reached. Building '{args.buildingId}' may not be fully constructed.{LogColors.ENDC}")


    log.info(f"{LogColors.HEADER}--- BuildFast for BuildingId: {args.buildingId} Finished ---{LogColors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("BuildFast script interrupted by user.")
        sys.exit(1)
    except Exception as e:
        log.error(f"An unexpected error occurred in BuildFast: {e}", exc_info=True)
        sys.exit(1)

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
from typing import Optional, Dict, Any

# Add project root to sys.path for consistent imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

try:
    from backend.engine.utils.activity_helpers import LogColors, get_building_record, _escape_airtable_value
except ImportError:
    class LogColors:
        HEADER = OKBLUE = OKGREEN = WARNING = FAIL = ENDC = BOLD = ''
    def get_building_record(tables: Dict[str, Table], building_id_input: str) -> Optional[Dict[str, Any]]:
        # Minimal fallback if imports fail during standalone execution (should not happen in normal use)
        log.error("Failed to import get_building_record from activity_helpers.")
        try:
            # Attempt direct fetch, assuming building_id_input is the custom BuildingId
            formula = f"{{BuildingId}} = '{building_id_input.replace(\"'\", \"\\'\")}'"
            records = tables['buildings'].all(formula=formula, max_records=1)
            return records[0] if records else None
        except Exception as e:
            log.error(f"Fallback get_building_record failed: {e}")
            return None
    def _escape_airtable_value(value: Any) -> str:
        if isinstance(value, str):
            return value.replace("'", "\\'")
        return str(value)


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
        }
        # Test connection
        tables['buildings'].all(max_records=1)
        log.info(f"{LogColors.OKGREEN}Airtable connection successful.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def run_script(script_path: str, citizen_username: Optional[str] = None, activity_id: Optional[str] = None) -> bool:
    """Runs a given script with optional citizen or activityId argument."""
    command = ["python", script_path]
    if citizen_username:
        command.extend(["--citizen", citizen_username])
    if activity_id: # Should not be used by processAllActivitiesNow when --citizen is used
        command.extend(["--ActivityId", activity_id])

    script_name = os.path.basename(script_path)
    log.info(f"{LogColors.OKBLUE}Running {script_name} for citizen '{citizen_username}'... Command: {' '.join(command)}{LogColors.ENDC}")
    try:
        # Stream output directly
        process = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr)
        process.communicate() # Wait for the process to complete
        
        if process.returncode == 0:
            log.info(f"{LogColors.OKGREEN}{script_name} completed successfully for citizen '{citizen_username}'.{LogColors.ENDC}")
            return True
        else:
            log.error(f"{LogColors.FAIL}{script_name} failed for citizen '{citizen_username}' with exit code {process.returncode}.{LogColors.ENDC}")
            return False
    except FileNotFoundError:
        log.error(f"{LogColors.FAIL}Error: The script at '{script_path}' was not found.{LogColors.ENDC}")
        return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}An exception occurred while running {script_name} for '{citizen_username}': {e}{LogColors.ENDC}")
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
    relevant_citizen_username = building_record['fields'].get('RunBy')
    if not relevant_citizen_username:
        relevant_citizen_username = building_record['fields'].get('Owner')

    if not relevant_citizen_username:
        log.error(f"{LogColors.FAIL}Could not determine a relevant citizen (RunBy or Owner) for building '{args.buildingId}'.{LogColors.ENDC}")
        return

    log.info(f"Targeting citizen '{relevant_citizen_username}' for construction of '{args.buildingId}'.")

    for i in range(args.maxIterations):
        log.info(f"{LogColors.HEADER}--- Iteration {i + 1}/{args.maxIterations} for building {args.buildingId} ---{LogColors.ENDC}")

        # 1. Call createActivities.py
        log.info(f"Calling createActivities.py for {relevant_citizen_username}...")
        if not run_script(create_activities_path, citizen_username=relevant_citizen_username):
            log.error(f"{LogColors.FAIL}createActivities.py failed. Stopping BuildFast.{LogColors.ENDC}")
            break
        
        log.info(f"Waiting {args.delay} seconds...")
        time.sleep(args.delay)

        # 2. Call processAllActivitiesNow.py
        log.info(f"Calling processAllActivitiesNow.py for {relevant_citizen_username}...")
        if not run_script(process_all_activities_path, citizen_username=relevant_citizen_username):
            log.error(f"{LogColors.FAIL}processAllActivitiesNow.py failed. Stopping BuildFast.{LogColors.ENDC}")
            break
        
        # 3. Check building status
        current_building_record = get_building_record(tables, args.buildingId)
        if not current_building_record:
            log.error(f"{LogColors.FAIL}Building '{args.buildingId}' could not be refetched. Stopping BuildFast.{LogColors.ENDC}")
            break

        if current_building_record['fields'].get('IsConstructed'):
            log.info(f"{LogColors.OKGREEN}Building '{args.buildingId}' successfully constructed!{LogColors.ENDC}")
            break
        
        construction_minutes_remaining = current_building_record['fields'].get('ConstructionMinutesRemaining', 0)
        log.info(f"Building '{args.buildingId}' status: IsConstructed={current_building_record['fields'].get('IsConstructed')}, MinutesRemaining={construction_minutes_remaining}")

        # Optional: Check last activity status for the citizen if needed for finer-grained error detection
        # This would involve querying the ACTIVITIES table for the latest activity by this citizen related to this building.

        if i < args.maxIterations - 1:
            log.info(f"Waiting {args.delay} seconds before next iteration...")
            time.sleep(args.delay)
    else:
        if i == args.maxIterations -1 : # Check if loop finished due to maxIterations
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

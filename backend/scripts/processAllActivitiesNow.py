#!/usr/bin/env python3
"""
Script to process all 'created' or 'in_progress' activities sequentially by StartDate.
It calls the main processActivities.py script for each activity.
"""

import os
import sys
import subprocess
import logging
import argparse
import concurrent.futures # Added for threading
from datetime import datetime
from typing import List, Dict, Optional, Any

# Add project root to sys.path for consistent imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv
from dateutil import parser as dateutil_parser
import requests # Added for custom session

# Import utility from backend.engine.utils (assuming LogColors might be useful)
try:
    from backend.engine.utils.activity_helpers import LogColors, _escape_airtable_value
except ImportError:
    # Fallback if utils are not directly importable or for simpler logging
    class LogColors:
        HEADER = OKBLUE = OKGREEN = WARNING = FAIL = ENDC = BOLD = '' # No colors
    def _escape_airtable_value(value: Any) -> str:
        if isinstance(value, str):
            return value.replace("'", "\\'")
        return str(value)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("processAllActivitiesNow")

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
        custom_session = requests.Session() 
        custom_session.trust_env = False    
        custom_session.headers.update({"Authorization": f"Bearer {api_key}"})

        from urllib3.util.retry import Retry # Ensure Retry is imported
        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        api = Api(api_key, retry_strategy=retry_strategy)
        api.session = custom_session

        tables = {
            'activities': api.table(base_id, 'ACTIVITIES'),
        }
        # Test connection by trying to fetch schema for one table (or a dummy fetch)
        tables['activities'].all(max_records=1) 
        log.info(f"{LogColors.OKGREEN}Airtable connection successful.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def get_activities_to_process(tables: Dict[str, Table], activity_type_filter: Optional[str] = None, specific_activity_id: Optional[str] = None) -> List[Dict]:
    """
    Fetches activities to process.
    If specific_activity_id is provided, fetches only that activity.
    Otherwise, fetches 'created' or 'in_progress' activities, sorted by StartDate, 
    optionally filtered by type, excluding 'rest' and 'idle'.
    """
    if specific_activity_id:
        formula = f"{{ActivityId}} = '{_escape_airtable_value(specific_activity_id)}'"
        log.info(f"Fetching specific activity with formula: {formula}")
    else:
        base_formula_parts = [
            "OR({Status}='created', {Status}='in_progress')",
            "NOT({Type}='rest')",
            "NOT({Type}='idle')"
        ]
        if activity_type_filter:
            base_formula_parts.append(f"{{Type}}='{_escape_airtable_value(activity_type_filter)}'")
        
        formula = "AND(" + ", ".join(base_formula_parts) + ")"
        log.info(f"Fetching activities with formula: {formula}")
    try:
        all_matching_activities = tables['activities'].all(formula=formula, fields=['ActivityId', 'StartDate', 'Type', 'Citizen', 'Status'])
        
        # Filter out activities without a valid StartDate and parse dates
        valid_activities = []
        for activity_record in all_matching_activities:
            start_date_str = activity_record['fields'].get('StartDate')
            if start_date_str:
                try:
                    activity_record['fields']['_ParsedStartDate'] = dateutil_parser.isoparse(start_date_str)
                    valid_activities.append(activity_record)
                except ValueError:
                    log.warning(f"Could not parse StartDate '{start_date_str}' for activity {activity_record.get('id')}. Skipping.")
            else:
                log.warning(f"Activity {activity_record.get('id')} missing StartDate. Skipping.")
        
        # Sort by parsed StartDate
        valid_activities.sort(key=lambda x: x['fields']['_ParsedStartDate'])
        
        log.info(f"{LogColors.OKBLUE}Found {len(valid_activities)} activities to process, sorted by StartDate.{LogColors.ENDC}")
        return valid_activities
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching activities: {e}{LogColors.ENDC}")
        return []

def run_process_activities_script(activity_id: str, process_activities_script_path: str):
    """Runs the processActivities.py script for a given activityId and streams its output."""
    # Check if file exists before trying to run it
    if not os.path.exists(process_activities_script_path):
        log.error(f"{LogColors.FAIL}Error: processActivities.py not found at: {process_activities_script_path}{LogColors.ENDC}")
        return False
    
    # Use python3 explicitly
    command = ["python3", process_activities_script_path, "--activityId", activity_id]
    log.info(f"{LogColors.HEADER}Executing: {' '.join(command)}{LogColors.ENDC}")

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Redirect stderr to stdout
            text=True,
            bufsize=1, # Line buffered
            universal_newlines=True # Ensure text mode for stdout
        )

        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                # Print line by line to stream output
                # The [processActivities] prefix helps distinguish logs
                print(f"[processActivities] {line.strip()}", flush=True)
            process.stdout.close()
        
        return_code = process.wait()

        if return_code == 0:
            log.info(f"{LogColors.OKGREEN}Successfully processed activity {activity_id}.{LogColors.ENDC}")
        else:
            log.error(f"{LogColors.FAIL}Error processing activity {activity_id}. processActivities.py exited with code {return_code}.{LogColors.ENDC}")
        return return_code == 0
    except FileNotFoundError:
        log.error(f"{LogColors.FAIL}Error: The script at '{process_activities_script_path}' was not found.{LogColors.ENDC}")
        return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}An exception occurred while running processActivities.py for {activity_id}: {e}{LogColors.ENDC}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Process activities sequentially or in parallel.")
    parser.add_argument("--activityType", type=str, help="Process only activities of this specific type.")
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="Number of threads to use for parallel processing. Default is 1 (sequential)."
    )
    # --hour argument is removed from here
    parser.add_argument(
        "--activityId",
        type=str,
        help="Process a specific activity by its custom ActivityId, bypassing normal selection criteria."
    )
    args = parser.parse_args()

    num_threads = args.threads
    if num_threads < 1:
        log.warning(f"{LogColors.WARNING}Number of threads must be at least 1. Defaulting to 1.{LogColors.ENDC}")
        num_threads = 1

    header_info = f"--- Starting Process All Activities Now script (Threads: {num_threads}) ---"
    if args.activityType:
        header_info = f"--- Starting Process All Activities Now script (Filtering for Type: {args.activityType}, Threads: {num_threads}) ---"
    if args.activityId: # Add activityId to header if present
        header_info = f"--- Starting Process All Activities Now script (ActivityId: {args.activityId}, Threads: {num_threads}) ---"
    log.info(f"{LogColors.HEADER}{header_info}{LogColors.ENDC}")
    
    tables = initialize_airtable()
    if not tables:
        log.error(f"{LogColors.FAIL}Exiting due to Airtable initialization failure.{LogColors.ENDC}")
        return

    activities = get_activities_to_process(tables, activity_type_filter=args.activityType, specific_activity_id=args.activityId)
    if not activities:
        filter_message = ""
        if args.activityId:
            filter_message = f" with ActivityId '{args.activityId}'"
        elif args.activityType:
            filter_message = f" of type '{args.activityType}'"
        log.info(f"{LogColors.OKBLUE}No activities found to process{filter_message}.{LogColors.ENDC}")
        return

    # Construct the path to processActivities.py relative to this script's project root
    # This script is in backend/scripts/
    # processActivities.py is in backend/engine/
    process_activities_script_path = os.path.join(PROJECT_ROOT, 'backend', 'engine', 'processActivities.py')
    
    # Debug: Check if file exists
    if not os.path.exists(process_activities_script_path):
        log.error(f"processActivities.py not found at: {process_activities_script_path}")
        log.info(f"PROJECT_ROOT is: {PROJECT_ROOT}")
        log.info(f"Current working directory: {os.getcwd()}")
        # Try alternative path
        alt_path = os.path.join(os.path.dirname(__file__), '..', 'engine', 'processActivities.py')
        alt_path = os.path.abspath(alt_path)
        if os.path.exists(alt_path):
            log.info(f"Found processActivities.py at alternative path: {alt_path}")
            process_activities_script_path = alt_path
        else:
            log.error(f"Also not found at alternative path: {alt_path}")
    
    log.info(f"Path to processActivities.py: {process_activities_script_path}")


    total_activities = len(activities)
    processed_successfully = 0
    processed_with_errors = 0

    if num_threads > 1 and not args.activityId: # Parallel processing only if not targeting a specific activityId
        log.info(f"{LogColors.OKBLUE}Starting parallel processing with {num_threads} threads.{LogColors.ENDC}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_activity_id = {
                executor.submit(run_process_activities_script, activity_record['fields'].get('ActivityId'), process_activities_script_path): activity_record['fields'].get('ActivityId')
                for activity_record in activities if activity_record['fields'].get('ActivityId')
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_activity_id)):
                activity_id_custom = future_to_activity_id[future]
                # Find the original activity_record for logging details (optional, but good for context)
                original_activity_record = next((act for act in activities if act['fields'].get('ActivityId') == activity_id_custom), None)
                activity_type_log = original_activity_record['fields'].get('Type', 'N/A') if original_activity_record else 'N/A'
                citizen_username_log = original_activity_record['fields'].get('Citizen', 'N/A') if original_activity_record else 'N/A'

                log.info(f"{LogColors.HEADER}Completed processing for activity {activity_id_custom} (Type: {activity_type_log}, Citizen: {citizen_username_log}) (Job {i+1}/{total_activities}){LogColors.ENDC}")
                try:
                    success = future.result()
                    if success:
                        processed_successfully += 1
                    else:
                        processed_with_errors += 1
                except Exception as exc:
                    log.error(f"{LogColors.FAIL}Activity {activity_id_custom} generated an exception in the thread: {exc}{LogColors.ENDC}")
                    processed_with_errors += 1
    else:
        log.info(f"{LogColors.OKBLUE}Starting sequential processing.{LogColors.ENDC}")
        for i, activity_record in enumerate(activities):
            activity_id_custom = activity_record['fields'].get('ActivityId')
            activity_type = activity_record['fields'].get('Type', 'N/A')
            citizen_username = activity_record['fields'].get('Citizen', 'N/A')
            status = activity_record['fields'].get('Status', 'N/A')
            start_date_iso = activity_record['fields'].get('_ParsedStartDate').isoformat() if '_ParsedStartDate' in activity_record['fields'] else 'N/A'

            if not activity_id_custom:
                log.warning(f"{LogColors.WARNING}Activity record {activity_record.get('id')} is missing 'ActivityId' field. Skipping.{LogColors.ENDC}")
                processed_with_errors +=1
                continue
            
            log.info(f"{LogColors.HEADER}Processing activity {i+1}/{total_activities}: {activity_id_custom} (Type: {activity_type}, Citizen: {citizen_username}, Status: {status}, Start: {start_date_iso}){LogColors.ENDC}")
            
            success = run_process_activities_script(activity_id_custom, process_activities_script_path)
            if success:
                processed_successfully += 1
            else:
                processed_with_errors += 1

    log.info(f"{LogColors.HEADER}--- Process All Activities Now script finished ---{LogColors.ENDC}")
    log.info(f"Total activities considered: {total_activities}")
    log.info(f"{LogColors.OKGREEN}Successfully processed: {processed_successfully}{LogColors.ENDC}")
    if processed_with_errors > 0:
        log.info(f"{LogColors.FAIL}Processed with errors/skipped: {processed_with_errors}{LogColors.ENDC}")

if __name__ == "__main__":
    # Argument parsing is now handled at the beginning of main()
    main()

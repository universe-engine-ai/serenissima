#!/usr/bin/env python3
import os
import sys
import logging
import json
import requests
import argparse
import subprocess
from typing import Optional

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Import LogColors from the canonical location
from backend.engine.utils.activity_helpers import LogColors

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("attempt_to_solve_problem")

# Constants
API_BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')

def attempt_to_solve_problem(building_id: str, resource_type: str, dry_run: bool = False, kinos_model: str = "local"):
    """
    Calls pinpoint-problem API and then triggers autonomouslyRun.py for the target citizen.
    """
    log.info(f"{LogColors.HEADER}--- Attempting to solve problem for Building: {building_id}, Resource: {resource_type} (Model: {kinos_model}) ---{LogColors.ENDC}")

    # 1. Call pinpoint-problem API
    pinpoint_url = f"{API_BASE_URL}/api/pinpoint-problem?buildingId={building_id}&resourceType={resource_type}"
    log.info(f"{LogColors.OKBLUE}Calling pinpoint-problem API: {pinpoint_url}{LogColors.ENDC}")

    try:
        response = requests.get(pinpoint_url, timeout=30)
        response.raise_for_status()
        pinpoint_data = response.json()
        log.info(f"{LogColors.OKGREEN}pinpoint-problem API response: {json.dumps(pinpoint_data, indent=2)}{LogColors.ENDC}")

    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}Error calling pinpoint-problem API: {e}{LogColors.ENDC}")
        return
    except json.JSONDecodeError as e:
        log.error(f"{LogColors.FAIL}Error decoding JSON response from pinpoint-problem API: {e}. Response text: {response.text[:200] if hasattr(response, 'text') else 'N/A'}{LogColors.ENDC}")
        return

    # 2. Analyze response and call autonomouslyRun.py
    if pinpoint_data.get("success") and pinpoint_data.get("problem_identified"):
        problem_details = pinpoint_data.get("problemDetails", {})
        target_citizen = problem_details.get("citizenToNotify")
        # Use the description from problemDetails as the primary message
        problem_message = problem_details.get("description", pinpoint_data.get("message")) 
        problem_issue_code = pinpoint_data.get("issue") # This is the short code like NO_MARKUP_BUY_CONTRACT

        if not target_citizen:
            log.warning(f"{LogColors.WARNING}Problem identified ({problem_issue_code}), but no 'citizenToNotify' in 'problemDetails' provided by pinpoint-problem API. Cannot trigger autonomous run.{LogColors.ENDC}")
            log.warning(f"Full problem details: {json.dumps(problem_details, indent=2)}")
            return

        if not problem_message:
            log.warning(f"{LogColors.WARNING}Problem identified ({problem_issue_code}) for citizen {target_citizen}, but no problem message/description provided. Triggering autonomous run without specific problem context in --addMessage.{LogColors.ENDC}")
            problem_message = f"A problem of type '{problem_issue_code}' was identified at building {building_id} regarding resource {resource_type}, but no further details were provided by the pinpointing system."
        
        # Add solutions to the problem message if available
        solutions = problem_details.get("solutions")
        if solutions:
            problem_message += f"\n\nSuggested Solutions:\n{solutions}"

        log.info(f"{LogColors.OKCYAN}Problem identified: {problem_issue_code}. Target citizen: {target_citizen}. Problem message for AI: {problem_message}{LogColors.ENDC}")

        autonomously_run_script_path = os.path.join(os.path.dirname(__file__), 'autonomouslyRun.py')
        
        command = [
            sys.executable,
            autonomously_run_script_path,
            "--citizen", target_citizen,
            "--addMessage", problem_message,
            "--unguided", # Default to unguided mode for problem solving
            "--model", kinos_model # Use specified or default model
        ]
        if dry_run:
            command.append("--dry-run")

        log.info(f"{LogColors.OKBLUE}Executing autonomouslyRun.py with command: {' '.join(command)}{LogColors.ENDC}")

        if dry_run:
            log.info(f"{LogColors.WARNING}[DRY RUN] Would execute the above command.{LogColors.ENDC}")
        else:
            try:
                # Start the subprocess
                # Use bufsize=1 for line buffering, text=True (or universal_newlines=True) for text mode
                process = subprocess.Popen(
                    command, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    encoding='utf-8', 
                    errors='replace', # Add error handling for decoding
                    bufsize=1
                )

                # Stream stdout
                if process.stdout:
                    log.info(f"{LogColors.OKCYAN}--- autonomouslyRun.py STDOUT for {target_citizen} ---{LogColors.ENDC}")
                    for line in iter(process.stdout.readline, ''):
                        sys.stdout.write(line) # Write directly to allow colors from subprocess
                        sys.stdout.flush()
                    process.stdout.close()
                
                # Stream stderr
                if process.stderr:
                    log.info(f"{LogColors.WARNING}--- autonomouslyRun.py STDERR for {target_citizen} ---{LogColors.ENDC}")
                    for line in iter(process.stderr.readline, ''):
                        sys.stderr.write(line) # Write directly to allow colors from subprocess
                        sys.stderr.flush()
                    process.stderr.close()

                process.wait() # Wait for the process to complete

                if process.returncode == 0:
                    log.info(f"{LogColors.OKGREEN}autonomouslyRun.py executed successfully for {target_citizen} (Return Code: {process.returncode}).{LogColors.ENDC}")
                else:
                    log.error(f"{LogColors.FAIL}autonomouslyRun.py failed for {target_citizen} with return code {process.returncode}.{LogColors.ENDC}")

            except FileNotFoundError:
                log.error(f"{LogColors.FAIL}Error: autonomouslyRun.py script not found at {autonomously_run_script_path}{LogColors.ENDC}")
            except Exception as e_subproc:
                log.error(f"{LogColors.FAIL}Error executing autonomouslyRun.py: {e_subproc}{LogColors.ENDC}")

    elif pinpoint_data.get("success") and not pinpoint_data.get("problem_identified"):
        log.info(f"{LogColors.OKGREEN}pinpoint-problem API reported no problem identified for building {building_id}, resource {resource_type}.{LogColors.ENDC}")
        log.info(f"Message: {pinpoint_data.get('message')}")
    else:
        log.error(f"{LogColors.FAIL}pinpoint-problem API call was not successful or did not identify a problem. Response: {pinpoint_data}{LogColors.ENDC}")

    log.info(f"{LogColors.HEADER}--- Finished attempt to solve problem for Building: {building_id}, Resource: {resource_type} ---{LogColors.ENDC}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Attempt to solve a resource availability problem by triggering an AI citizen's autonomous run.")
    parser.add_argument("--buildingId", required=True, help="The BuildingId where the resource problem exists.")
    parser.add_argument("--resourceType", required=True, help="The type of resource that is unavailable.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the process without executing autonomouslyRun.py.")
    parser.add_argument(
        "--model",
        type=str,
        default="local",
        help="Specify a KinOS model override for autonomouslyRun.py (e.g., 'local', 'gemini-2.5-flash-preview-05-20'). Default: local."
    )
    args = parser.parse_args()

    attempt_to_solve_problem(args.buildingId, args.resourceType, args.dry_run, args.model)

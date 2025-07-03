#!/usr/bin/env python3
import os
import sys
import logging
import json
import requests
import argparse
from datetime import datetime, timedelta # Added timedelta
import pytz # Keep pytz for timezone operations
from typing import Any, Dict, Optional # Added Dict, Optional
import subprocess # Ajout pour exécuter un script externe

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
from pyairtable import Api as AirtableApi, Table as AirtableTable
from backend.engine.utils.activity_helpers import LogColors, _escape_airtable_value, VENICE_TIMEZONE
from backend.engine.activity_creators.work_on_art_creator import try_create_work_on_art_activity

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("artist_work_script")

# KinOS constants
# Always use the production KinOS API URL
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")

def initialize_airtable() -> dict[str, AirtableTable] | None:
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not api_key or not base_id:
        log.error(f"{LogColors.FAIL}Airtable credentials missing.{LogColors.ENDC}")
        return None
    
    try:
        api = AirtableApi(api_key)
        tables = {
            'citizens': api.table(base_id, 'CITIZENS'),
            'activities': api.table(base_id, 'ACTIVITIES'), # For potential future use
            'buildings': api.table(base_id, 'BUILDINGS') # Added BUILDINGS table
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection successful.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def trigger_artist_work(target_artist_username: str | None = None, additional_message: str | None = None, kinos_model_override: str | None = None):
    """
    Fetches Artisti citizens and triggers their 'work_on_art' KinOS interaction.
    An optional additional message can be appended to the KinOS prompt.
    """
    log.info(f"{LogColors.HEADER}--- Starting Artist Work Trigger Script ---{LogColors.ENDC}")
    
    tables = initialize_airtable()
    if not tables:
        return

    artists_to_process = []
    try:
        if target_artist_username:
            formula = f"{{Username}} = '{_escape_airtable_value(target_artist_username)}'"
            artist_record = tables['citizens'].all(formula=formula, max_records=1)
            if artist_record and artist_record[0]['fields'].get('SocialClass') == "Artisti":
                artists_to_process = artist_record
            elif artist_record:
                log.warning(f"{LogColors.WARNING}Citizen {target_artist_username} is not an Artisti. Skipping.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Artist {target_artist_username} not found.{LogColors.ENDC}")
        else:
            formula = "{SocialClass} = 'Artisti'"
            artists_to_process = tables['citizens'].all(formula=formula)
        
        if not artists_to_process:
            log.info(f"{LogColors.OKBLUE}No Artisti found to process.{LogColors.ENDC}")
            return

        log.info(f"{LogColors.OKBLUE}Found {len(artists_to_process)} Artisti to process.{LogColors.ENDC}")

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching Artisti: {e}{LogColors.ENDC}")
        return

    for artist_record in artists_to_process:
        citizen_username = artist_record['fields'].get('Username')
        citizen_name_log = f"{artist_record['fields'].get('FirstName', '')} {artist_record['fields'].get('LastName', '')}".strip() or citizen_username
        citizen_position_str = artist_record['fields'].get('Position')
        citizen_position_coords: Optional[Dict[str, float]] = None

        if citizen_position_str:
            try:
                citizen_position_coords = json.loads(citizen_position_str)
                if not isinstance(citizen_position_coords, dict) or \
                   not all(key in citizen_position_coords for key in ['lat', 'lng']):
                    log.warning(f"  Parsed position for {citizen_name_log} is not a valid dict with lat/lng. Position: {citizen_position_coords}")
                    citizen_position_coords = None
            except json.JSONDecodeError:
                log.warning(f"  Could not parse position JSON for {citizen_name_log}: {citizen_position_str}")
                citizen_position_coords = None
        else:
            log.warning(f"  Position field is empty for {citizen_name_log}.")

        log.info(f"\n{LogColors.OKCYAN}Processing artist: {citizen_name_log} (Username: {citizen_username}){LogColors.ENDC}")
        log.info(f"  Fetched Position: {citizen_position_str} -> Parsed: {citizen_position_coords}")

        # --- Existing KinOS Interaction for Art Session Description ---
        log.info(f"{LogColors.BOLD}--- Starting KinOS Interaction for Art Session Description ---{LogColors.ENDC}")
        # 1. Fetch citizen's ledger for KinOS addSystem
        ledger_url = f"{API_BASE_URL}/api/get-ledger?citizenUsername={citizen_username}" # Defaults to Markdown format
        ledger_markdown_str = None # Changed variable name for clarity
        log.info(f"  Fetching ledger (Markdown) from: {ledger_url}")
        try:
            ledger_response = requests.get(ledger_url, timeout=20)
            ledger_response.raise_for_status()
            # The response is now expected to be Markdown text
            ledger_markdown_str = ledger_response.text
            log.info(f"  Successfully fetched Markdown ledger for {citizen_username} (length: {len(ledger_markdown_str)}).")
        except requests.exceptions.RequestException as e_pkg:
            log.error(f"  Error fetching Markdown ledger for {citizen_username}: {e_pkg}")
            # Continue without ledger if it fails, KinOS might still work with just the prompt.

        # 2. Construct KinOS /build request
        kinos_build_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/build"
        
        kinos_message = (
            "You are an Artista in Venice, using a digital system (Aider, via KinOS) to manage your creative projects. It's time to dedicate an hour to your artistic endeavors. "
            "You have complete autonomy to decide what to work on. This system allows you to **create new files, edit existing ones, and organize your work in directories.**\n\n"
            "All your project files MUST be managed within the `AI-memories/art/` directory. "
            "Use your current situation, recent events, inspirations, and available resources (detailed in the `addSystem` data which includes your full citizen profile, properties, contracts, relationships, problems, etc.) "
            "to guide your work. After your session, briefly describe what file operations you performed and the creative progress you made."
        )

        if additional_message:
            kinos_message += f"\n\n--- Additional Instructions ---\n{additional_message}"
            log.info(f"  Appended additional message to KinOS prompt for {citizen_username}.")
        
        kinos_payload: dict[str, Any] = {
            "message": kinos_message
        }
        if kinos_model_override:
            kinos_payload["model"] = kinos_model_override
            log.info(f"  Using KinOS model override: {kinos_model_override}")
        else:
            kinos_payload["model"] = "local"
            log.info(f"  Using default KinOS model: local")

        if ledger_markdown_str: # Use the new variable name
            kinos_payload["addSystem"] = ledger_markdown_str
        
        log.info(f"  Calling KinOS /build endpoint for {citizen_username} at {kinos_build_url}")
        log.info(f"  KinOS payload for {citizen_username}: {json.dumps(kinos_payload, indent=2)}") # Log the payload

        # 3. Make synchronous KinOS call
        try:
            kinos_response = requests.post(kinos_build_url, json=kinos_payload, timeout=180) # Increased timeout for build
            kinos_response.raise_for_status() 
            
            kinos_response_data = kinos_response.json()
            log.info(f"  KinOS /build response status for {citizen_username}: {kinos_response_data.get('status')}")
            
            kinos_actual_response_content = kinos_response_data.get('response', "No response content from KinOS.")
            
            print(f"\n--- KinOS Response for {citizen_name_log} ({citizen_username}) ---")
            # Ensure the content is a string before encoding
            response_str_to_print = str(kinos_actual_response_content)
            sys.stdout.buffer.write(response_str_to_print.encode('utf-8', errors='replace') + b'\n')
            sys.stdout.flush()
            print(f"--- End KinOS Response for {citizen_name_log} ---\n")
            
            if kinos_response_data.get('status') != 'completed':
                log.warning(f"  KinOS /build did not complete successfully for {citizen_username}. Full response data: {kinos_response_data}")

        except requests.exceptions.Timeout:
            log.error(f"  Timeout calling KinOS /build for {citizen_username}.")
            print(f"\n--- KinOS Call for {citizen_name_log} ({citizen_username}) TIMED OUT ---")
        except requests.exceptions.RequestException as e_kinos:
            log.error(f"  Error calling KinOS /build for {citizen_username}: {e_kinos}")
            if hasattr(e_kinos, 'response') and e_kinos.response is not None:
                log.error(f"  KinOS error response content: {e_kinos.response.text[:500]}")
                print(f"\n--- KinOS Call for {citizen_name_log} ({citizen_username}) FAILED ---")
                print(f"Error: {e_kinos}")
                print(f"Response: {e_kinos.response.text[:500]}")
                print(f"--- End KinOS Failure ---")
        except json.JSONDecodeError as e_json_kinos:
            log.error(f"  Error decoding KinOS /build JSON response for {citizen_username}: {e_json_kinos}. Response text: {kinos_response.text[:200] if 'kinos_response' in locals() and hasattr(kinos_response, 'text') else 'N/A'}")
            print(f"\n--- KinOS Call for {citizen_name_log} ({citizen_username}) FAILED (JSON Decode Error) ---")
            print(f"Response Text (first 200 chars): {kinos_response.text[:200] if 'kinos_response' in locals() and hasattr(kinos_response, 'text') else 'N/A'}")
            print(f"--- End KinOS Failure ---")
        log.info(f"{LogColors.BOLD}--- Finished KinOS Interaction for Art Session Description ---{LogColors.ENDC}")

        # --- ADDING 'work_on_art' ACTIVITY CREATION ---
        log.info(f"\n{LogColors.BOLD}--- Attempting to Create 'work_on_art' Activity in Airtable for {citizen_name_log} ---{LogColors.ENDC}")
        if citizen_position_coords and artist_record['fields'].get('CitizenId'): # CitizenId is also needed by the creator
            now_utc_dt = datetime.now(pytz.utc)
            transport_api_url = os.getenv("TRANSPORT_API_URL", "http://localhost:3000/api/transport")
            
            log.info(f"  Calling try_create_work_on_art_activity for {citizen_name_log}...")
            log.info(f"  Parameters: citizen_username='{citizen_username}', citizen_position={citizen_position_coords}, transport_api_url='{transport_api_url}'")

            # Ensure the full artist_record (which is a dict with 'id' and 'fields') is passed
            created_activity_chain_start = try_create_work_on_art_activity(
                tables=tables,
                citizen_record=artist_record,
                citizen_position=citizen_position_coords,
                now_utc_dt=now_utc_dt,
                transport_api_url=transport_api_url,
                api_base_url=API_BASE_URL # Pass API_BASE_URL
            )

            if created_activity_chain_start:
                activity_type = created_activity_chain_start['fields'].get('Type')
                activity_type = created_activity_chain_start['fields'].get('Type')
                activity_id_guid = created_activity_chain_start['fields'].get('ActivityId') # GUID personnalisé
                airtable_record_id = created_activity_chain_start['id'] # ID d'enregistrement Airtable

                log.info(f"{LogColors.OKGREEN}  Successfully created activity chain starting with '{activity_type}' (GUID: {activity_id_guid}, Airtable ID: {airtable_record_id}) for {citizen_name_log}.{LogColors.ENDC}")
                print(f"  Created activity details: {json.dumps(created_activity_chain_start['fields'], indent=2, default=str)}")

                if activity_id_guid:
                    log.info(f"{LogColors.BOLD}--- Attempting to process created activity {activity_id_guid} immediately ---{LogColors.ENDC}")
                    try:
                        # Construire le chemin relatif vers le script processAllActivitiesnow.py
                        process_script_path = os.path.join(PROJECT_ROOT, 'backend', 'scripts', 'processAllActivitiesnow.py')
                        command = [
                            sys.executable, # Utiliser l'interpréteur Python actuel
                            process_script_path,
                            '--activityId', activity_id_guid
                        ]
                        log.info(f"  Executing command: {' '.join(command)}")
                        
                        # Exécuter le script et streamer la sortie
                        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
                        
                        if process.stdout:
                            for line in iter(process.stdout.readline, ''):
                                print(f"  [ProcessActivitiesNow] {line.strip()}")
                            process.stdout.close()
                        
                        return_code = process.wait()
                        if return_code == 0:
                            log.info(f"{LogColors.OKGREEN}  Successfully processed activity {activity_id_guid}.{LogColors.ENDC}")
                        else:
                            log.error(f"{LogColors.FAIL}  Error processing activity {activity_id_guid}. processAllActivitiesnow.py exited with code {return_code}.{LogColors.ENDC}")
                    except Exception as e_proc:
                        log.error(f"{LogColors.FAIL}  Exception while trying to run processAllActivitiesnow.py for {activity_id_guid}: {e_proc}{LogColors.ENDC}")
                else:
                    log.warning(f"{LogColors.WARNING}  Activity GUID (ActivityId) not found for the created activity. Cannot trigger immediate processing.{LogColors.ENDC}")

            else:
                log.error(f"{LogColors.FAIL}  Failed to create 'work_on_art' activity or chain for {citizen_name_log}.{LogColors.ENDC}")
                print(f"  'work_on_art' activity creation returned None for {citizen_name_log}.")
        else:
            if not citizen_position_coords:
                log.warning(f"{LogColors.WARNING}  Skipping 'work_on_art' activity creation for {citizen_name_log} due to missing or invalid position.{LogColors.ENDC}")
            if not artist_record['fields'].get('CitizenId'):
                 log.warning(f"{LogColors.WARNING}  Skipping 'work_on_art' activity creation for {citizen_name_log} due to missing CitizenId.{LogColors.ENDC}")
        log.info(f"{LogColors.BOLD}--- Finished 'work_on_art' Activity Creation Attempt ---{LogColors.ENDC}")

        # Small pause between artists if processing multiple
        if not target_artist_username and len(artists_to_process) > 1:
            import time
            time.sleep(2) # Increased sleep slightly

    log.info(f"{LogColors.HEADER}--- Artist Work Trigger Script Finished ---{LogColors.ENDC}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger KinOS 'work_on_art' interaction for Artisti citizens.")
    parser.add_argument(
        "--artist",
        type=str,
        help="Process a specific artist by username. If not provided, all Artisti will be processed."
    )
    parser.add_argument(
        "--add_message", # Using underscore for consistency with Python style
        type=str,
        help="Additional message to append to the KinOS prompt for the artist(s)."
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specify a KinOS model override (e.g., 'local', 'gemini-1.5-pro-latest')."
    )
    args = parser.parse_args()

    trigger_artist_work(
        target_artist_username=args.artist, 
        additional_message=args.add_message,
        kinos_model_override=args.model
    )

#!/usr/bin/env python3
"""
prayLoop.py - A continuous prayer loop for citizens

This script randomly selects citizens and creates pray activities for them,
then immediately processes the activities.
"""

import os
import sys
import time
import random
import requests
import traceback
import json
from datetime import datetime, timedelta

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import necessary modules
from backend.engine.utils.activity_helpers import (
    LogColors, get_tables
)

# Global cache for definitions
CACHE_DURATION = timedelta(hours=1)  # Cache for 1 hour
_definition_cache = {
    'resource_defs': None,
    'building_type_defs': None,
    'last_updated': None
}

# Define logging functions
def log_info(message):
    """Log an info message with color."""
    print(f"{LogColors.OKBLUE}{message}{LogColors.ENDC}")

def log_warning(message):
    """Log a warning message with color."""
    print(f"{LogColors.WARNING}{message}{LogColors.ENDC}")

def log_error(message):
    """Log an error message with color."""
    print(f"{LogColors.FAIL}{message}{LogColors.ENDC}")

def log_success(message):
    """Log a success message with color."""
    print(f"{LogColors.OKGREEN}{message}{LogColors.ENDC}")

def log_header(message, color_code=LogColors.HEADER):
    """Log a header message with color."""
    border_char = "-"
    side_char = "|"
    corner_tl = "+"
    corner_tr = "+"
    corner_bl = "+"
    corner_br = "+"
    
    message_len = len(message)
    width = 80
    
    print(f"\n{color_code}{corner_tl}{border_char * (width - 2)}{corner_tr}{LogColors.ENDC}")
    print(f"{color_code}{side_char} {message.center(width - 4)} {side_char}{LogColors.ENDC}")
    print(f"{color_code}{corner_bl}{border_char * (width - 2)}{corner_br}{LogColors.ENDC}\n")

def get_cached_definitions():
    """
    Get resource and building definitions from cache or fetch if expired.
    
    Returns:
        tuple: (resource_defs, building_type_defs) or (None, None) if failed
    """
    global _definition_cache
    
    from backend.engine.utils.activity_helpers import (
        get_resource_types_from_api, 
        get_building_types_from_api
    )
    import pytz
    
    now = datetime.now(pytz.UTC)
    
    # Check if cache is valid
    if (_definition_cache['resource_defs'] is not None and 
        _definition_cache['building_type_defs'] is not None and
        _definition_cache['last_updated'] is not None and
        now - _definition_cache['last_updated'] < CACHE_DURATION):
        log_info("Using cached resource and building definitions")
        return _definition_cache['resource_defs'], _definition_cache['building_type_defs']
    
    # Cache is expired or empty, fetch new data
    log_info("Fetching fresh resource and building definitions...")
    try:
        resource_defs = get_resource_types_from_api()
        building_type_defs = get_building_types_from_api()
        
        if resource_defs and building_type_defs:
            # Update cache
            _definition_cache['resource_defs'] = resource_defs
            _definition_cache['building_type_defs'] = building_type_defs
            _definition_cache['last_updated'] = now
            log_success(f"Cached {len(resource_defs)} resource types and {len(building_type_defs)} building types")
            return resource_defs, building_type_defs
        else:
            log_error("Failed to fetch definitions")
            # Return cached data even if expired, if available
            if _definition_cache['resource_defs'] and _definition_cache['building_type_defs']:
                log_warning("Using expired cache as fallback")
                return _definition_cache['resource_defs'], _definition_cache['building_type_defs']
            return None, None
    except Exception as e:
        log_error(f"Error fetching definitions: {str(e)}")
        # Return cached data even if expired, if available
        if _definition_cache['resource_defs'] and _definition_cache['building_type_defs']:
            log_warning("Using expired cache as fallback due to error")
            return _definition_cache['resource_defs'], _definition_cache['building_type_defs']
        return None, None

def select_random_citizen(tables):
    """
    Select a random citizen from all citizens.
    
    Args:
        tables: Dictionary of Airtable tables
        
    Returns:
        A citizen record or None if no citizens found
    """
    try:
        # Get all citizens
        citizens = tables['citizens'].all()
        
        if not citizens:
            log_warning("No citizens found in the database")
            return None
        
        # Select a random citizen
        citizen = random.choice(citizens)
        username = citizen['fields'].get('Username', 'Unknown')
        social_class = citizen['fields'].get('SocialClass', 'Unknown')
        is_ai = citizen['fields'].get('IsAI', False)
        citizen_type = "AI" if is_ai else "Human"
        
        log_info(f"Selected {citizen_type} citizen: {username} (Social Class: {social_class})")
        return citizen
    
    except Exception as e:
        log_error(f"Error selecting random citizen: {str(e)}")
        traceback.print_exc()
        return None

def create_pray_activity(citizen, api_base_url):
    """
    Create a pray activity for the citizen via the API.
    
    Args:
        citizen: The citizen record
        api_base_url: Base URL for the API
        
    Returns:
        True if successful, False otherwise
    """
    try:
        username = citizen['fields'].get('Username', 'Unknown')
        
        # Prepare the activity data
        activity_data = {
            "citizenUsername": username,
            "activityType": "pray",  # lowercase as per the activity creator
            "activityDetails": {}  # Pray activity doesn't need details
        }
        
        # Make API request to create activity
        url = f"{api_base_url}/api/activities/try-create"
        headers = {'Content-Type': 'application/json'}
        
        log_info(f"Creating pray activity for {username}...")
        response = requests.post(url, json=activity_data, headers=headers, timeout=120)  # 2 minute timeout
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                activity_id = result.get('activityId', 'Unknown')
                log_success(f"Successfully created pray activity for {username} (Activity ID: {activity_id})")
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                log_warning(f"Failed to create pray activity for {username}: {error_msg}")
                return False
        else:
            log_error(f"API request failed with status {response.status_code}: {response.text}")
            return False
    
    except Exception as e:
        log_error(f"Error creating pray activity: {str(e)}")
        traceback.print_exc()
        return False

def get_pray_activity_from_chain(activity_chain):
    """
    Extract the pray activity from an activity chain.
    
    Args:
        activity_chain: Activity record or list of activity records
        
    Returns:
        The pray activity record if found, None otherwise
    """
    if not activity_chain:
        return None
        
    # If it's a single activity, check if it's a pray activity
    if isinstance(activity_chain, dict):
        if activity_chain.get('fields', {}).get('Type') == 'pray':
            return activity_chain
        return None
    
    # If it's a list, find the pray activity
    if isinstance(activity_chain, list):
        for activity in activity_chain:
            if activity.get('fields', {}).get('Type') == 'pray':
                return activity
    
    return None

def create_pray_activity_directly_return_info(citizen, tables):
    """
    Create a pray activity directly and return information about all activities created.
    
    Args:
        citizen: The citizen record
        tables: Dictionary of Airtable tables
        
    Returns:
        Dict with activity info if successful, None otherwise
    """
    try:
        username = citizen['fields'].get('Username', 'Unknown')
        
        # Import necessary modules
        from backend.engine.activity_creators.pray_activity_creator import try_create_pray_activity
        from backend.engine.utils.activity_helpers import VENICE_TIMEZONE
        from datetime import datetime
        import pytz
        
        # Get current time
        now_utc_dt = datetime.now(pytz.UTC)
        now_venice_dt = now_utc_dt.astimezone(VENICE_TIMEZONE)
        
        # Get citizen position
        citizen_position = None
        if 'Position' in citizen['fields'] and citizen['fields']['Position']:
            pos_str = citizen['fields']['Position']
            try:
                import json
                citizen_position = json.loads(pos_str) if isinstance(pos_str, str) else pos_str
            except:
                pass
        
        log_info(f"Creating pray activity directly for {username}...")
        
        # Get cached definitions
        resource_defs, building_type_defs = get_cached_definitions()
        if not resource_defs or not building_type_defs:
            log_error("Failed to get resource/building definitions")
            return None
        
        # Create the pray activity
        activity_record = try_create_pray_activity(
            tables=tables,
            citizen_record=citizen,
            citizen_position=citizen_position,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt,
            now_utc_dt=now_utc_dt,
            transport_api_url="http://localhost:3000/api/transport",
            api_base_url="http://localhost:3000"
        )
        
        if activity_record:
            # The creator returns the first activity in the chain
            first_activity = activity_record
            first_type = first_activity.get('fields', {}).get('Type', 'unknown')
            first_id = first_activity.get('fields', {}).get('ActivityId', 'Unknown')
            
            log_success(f"Successfully created activity chain for {username}")
            log_info(f"First activity: {first_type} (ID: {first_id})")
            
            # Now we need to find the pray activity that was created
            # It should have been created right after the goto_location
            pray_activity_id = None
            if first_type == 'goto_location':
                # Look for a pray activity created for this citizen
                time.sleep(1)  # Give it a moment to be saved
                formula = f"AND({{Citizen}} = '{username}', {{Type}} = 'pray', {{Status}} = 'created')"
                pray_activities = tables['activities'].all(formula=formula, sort=['-CreatedAt'], max_records=1)
                if pray_activities:
                    pray_activity_id = pray_activities[0]['fields'].get('ActivityId')
                    log_info(f"Found pray activity: {pray_activity_id}")
            elif first_type == 'pray':
                # The citizen was already at church
                pray_activity_id = first_id
            
            return {
                'first_activity': first_activity,
                'first_activity_id': first_id,
                'first_activity_type': first_type,
                'pray_activity_id': pray_activity_id
            }
        else:
            log_warning(f"Failed to create pray activity for {username}")
            return None
            
    except Exception as e:
        log_error(f"Error creating pray activity directly: {str(e)}")
        traceback.print_exc()
        return None

def create_pray_activity_directly_return_record(citizen, tables):
    """
    Create a pray activity directly using the activity creator and return the record.
    
    Args:
        citizen: The citizen record
        tables: Dictionary of Airtable tables
        
    Returns:
        Activity record if successful, None otherwise
    """
    info = create_pray_activity_directly_return_info(citizen, tables)
    return info['first_activity'] if info else None

def create_pray_activity_directly(citizen, tables):
    """
    Create a pray activity directly using the activity creator.
    
    Args:
        citizen: The citizen record
        tables: Dictionary of Airtable tables
        
    Returns:
        True if successful, False otherwise
    """
    # Just use the version that returns the record
    record = create_pray_activity_directly_return_record(citizen, tables)
    return record is not None

def process_activities_for_citizen(citizen_username, model=None):
    """
    Run the activity processor for a specific citizen.
    
    Args:
        citizen_username: Username of the citizen
        model: Optional KinOS model to use
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import subprocess
        
        # Build command
        python_cmd = "python" if os.name == 'nt' else "python3"
        cmd = [python_cmd, os.path.join(PROJECT_ROOT, "backend/engine/processActivities.py")]
        
        log_info(f"Running activity processor for citizen {citizen_username}...")
        cmd.extend(["--citizen", citizen_username])
        
        if model:
            cmd.extend(["--model", model])
        
        # Run the processor
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            log_success("Activity processor completed successfully")
            if result.stdout:
                log_info(f"Output:\n{result.stdout}")
            if result.stderr:
                log_warning(f"Stderr output:\n{result.stderr}")
            return True
        else:
            log_warning(f"Activity processor failed with return code {result.returncode}")
            if result.stderr:
                log_error(f"Error output: {result.stderr}")
            return False
    
    except Exception as e:
        log_error(f"Error running activity processor: {str(e)}")
        traceback.print_exc()
        return False

def process_activities(activity_id=None, model=None):
    """
    Run the activity processor to handle the created activities.
    
    Args:
        activity_id: Optional specific activity ID to process
        model: Optional KinOS model to use
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import subprocess
        
        # Build command - use python3 explicitly if python isn't available
        python_cmd = "python" if os.name == 'nt' else "python3"
        cmd = [python_cmd, os.path.join(PROJECT_ROOT, "backend/engine/processActivities.py")]
        
        if activity_id:
            log_info(f"Running activity processor for activity {activity_id}...")
            cmd.extend(["--activityId", activity_id])
        else:
            log_info("Running activity processor...")
        
        if model:
            cmd.extend(["--model", model])
        
        # Run the processor
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            log_success("Activity processor completed successfully")
            if result.stdout:
                log_info(f"Output:\n{result.stdout}")
            if result.stderr:
                log_warning(f"Stderr output:\n{result.stderr}")
            return True
        else:
            log_warning(f"Activity processor failed with return code {result.returncode}")
            if result.stderr:
                log_error(f"Error output: {result.stderr}")
            return False
    
    except Exception as e:
        log_error(f"Error running activity processor: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Main function to run the pray loop"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the pray loop for La Serenissima citizens')
    parser.add_argument('--model', type=str, default='local', 
                       help='KinOS model to use for prayer generation (default: local)')
    args = parser.parse_args()
    
    log_header("Starting Pray Loop", color_code=LogColors.HEADER)
    
    # Configuration
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:3000')
    DELAY_BETWEEN_PRAYERS = 5  # seconds between each prayer
    USE_DIRECT_CREATION = True  # Set to False to use API instead
    KINOS_MODEL = args.model
    
    try:
        # Initialize tables
        tables = get_tables()
        
        log_info(f"API Base URL: {API_BASE_URL}")
        log_info(f"Delay between prayers: {DELAY_BETWEEN_PRAYERS} seconds")
        log_info(f"Creation method: {'Direct' if USE_DIRECT_CREATION else 'API'}")
        log_info(f"KinOS Model: {KINOS_MODEL}")
        log_info("Press Ctrl+C to stop the loop\n")
        
        # Main loop
        while True:
            try:
                # Select a random citizen
                citizen = select_random_citizen(tables)
                
                if citizen:
                    # Create pray activity for the citizen
                    activity_id = None
                    if USE_DIRECT_CREATION:
                        activity_info = create_pray_activity_directly_return_info(citizen, tables)
                        if activity_info:
                            first_activity_id = activity_info['first_activity_id']
                            first_activity_type = activity_info['first_activity_type']
                            pray_activity_id = activity_info['pray_activity_id']
                            success = True
                        else:
                            success = False
                    else:
                        success = create_pray_activity(citizen, API_BASE_URL)
                        first_activity_id = None
                        pray_activity_id = None
                    
                    if success:
                        # Wait a moment to ensure the activity is saved
                        time.sleep(2)
                        
                        # Process activities based on what was created
                        if USE_DIRECT_CREATION and first_activity_type == 'goto_location':
                            # Process the goto_location first
                            log_info("Processing travel to church activity...")
                            process_activities(first_activity_id, model=KINOS_MODEL)
                            
                            # Now process the pray activity directly
                            if pray_activity_id:
                                time.sleep(2)
                                log_info(f"Processing pray activity {pray_activity_id}...")
                                process_activities(pray_activity_id, model=KINOS_MODEL)
                            else:
                                log_warning("Could not find pray activity ID")
                        elif USE_DIRECT_CREATION and pray_activity_id:
                            # Direct pray activity (already at church)
                            log_info("Citizen is already at church. Processing pray activity...")
                            log_info("Note: Pray activities take 20 minutes to complete normally.")
                            process_activities(pray_activity_id, model=KINOS_MODEL)
                        else:
                            # API creation mode - we don't know the structure
                            log_info("Processing created activities...")
                            username = citizen['fields'].get('Username')
                            process_activities_for_citizen(username, model=KINOS_MODEL)
                    
                    # Wait before next prayer
                    log_info(f"Waiting {DELAY_BETWEEN_PRAYERS} seconds before next prayer...\n")
                    time.sleep(DELAY_BETWEEN_PRAYERS)
                else:
                    log_warning("No citizen selected. Waiting 10 seconds...")
                    time.sleep(10)
                
            except Exception as loop_error:
                log_error(f"Error in pray loop: {str(loop_error)}")
                traceback.print_exc()
                time.sleep(10)  # Wait before retrying
    
    except KeyboardInterrupt:
        log_info("\nPray loop interrupted by user")
    except Exception as e:
        log_error(f"Fatal error in pray loop: {str(e)}")
        traceback.print_exc()
    
    log_header("Pray Loop Terminated", color_code=LogColors.FAIL)

if __name__ == "__main__":
    main()
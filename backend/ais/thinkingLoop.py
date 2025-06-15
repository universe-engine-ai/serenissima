#!/usr/bin/env python3
"""
thinkingLoop.py - A continuous thinking process for AI citizens

This script processes the queue of thinking tasks and also selects random citizens
for thinking operations when the queue is empty.

For random citizen selection, weighting is based on social class:
- Artisti: 5x chance
- Nobili: 4x chance
- Cittadini: 3x chance
- Popolani: 2x chance
- Facchini: 1x chance

The script is designed to be run continuously by the scheduler.
It uses a file lock mechanism to ensure only one instance runs at a time.
"""

import os
import sys
import time
import random
import traceback
import json
import fcntl
import signal
import atexit
from datetime import datetime, timedelta
import pytz

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import necessary modules
from backend.engine.utils.activity_helpers import (
    LogColors, log_info, log_warning, log_error, log_header,
    VENICE_TIMEZONE, get_tables
)

# Social class weights for citizen selection
SOCIAL_CLASS_WEIGHTS = {
    'Artisti': 5,
    'Nobili': 4,
    'Cittadini': 3,
    'Popolani': 2,
    'Facchini': 1
}

def select_random_citizen(tables):
    """
    Select a random citizen with weighting based on social class.
    
    Args:
        tables: Dictionary of Airtable tables
        
    Returns:
        A citizen record or None if no citizens found
    """
    try:
        # Get all AI citizens
        citizens = tables['citizens'].all()
        
        if not citizens:
            log_warning("No AI citizens found in the database")
            return None
        
        # Group citizens by social class
        citizens_by_class = {}
        for citizen in citizens:
            social_class = citizen['fields'].get('SocialClass', 'Unknown')
            if social_class not in citizens_by_class:
                citizens_by_class[social_class] = []
            citizens_by_class[social_class].append(citizen)
        
        # Create weighted selection pool
        selection_pool = []
        for social_class, citizens_list in citizens_by_class.items():
            weight = SOCIAL_CLASS_WEIGHTS.get(social_class, 1)  # Default weight 1 for unknown classes
            selection_pool.extend([(citizen, weight) for citizen in citizens_list])
        
        # Calculate total weight
        total_weight = sum(weight for _, weight in selection_pool)
        
        # Select a random citizen based on weights
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for citizen, weight in selection_pool:
            current_weight += weight
            if random_value <= current_weight:
                username = citizen['fields'].get('Username', 'Unknown')
                social_class = citizen['fields'].get('SocialClass', 'Unknown')
                log_info(f"Selected citizen: {username} (Social Class: {social_class})")
                return citizen
        
        # Fallback in case of rounding errors
        if selection_pool:
            citizen, _ = selection_pool[-1]
            username = citizen['fields'].get('Username', 'Unknown')
            social_class = citizen['fields'].get('SocialClass', 'Unknown')
            log_info(f"Fallback selected citizen: {username} (Social Class: {social_class})")
            return citizen
        
        return None
    
    except Exception as e:
        log_error(f"Error selecting random citizen: {str(e)}")
        traceback.print_exc()
        return None

def perform_thinking(citizen, tables):
    """
    Perform a thinking operation for the selected citizen.
    
    Args:
        citizen: The citizen record
        tables: Dictionary of Airtable tables
    """
    try:
        username = citizen['fields'].get('Username', 'Unknown')
        log_info(f"Performing thinking for citizen: {username}")
        
        # Import the process helper and thinking helper here to avoid circular imports
        from backend.engine.utils.process_helper import (
            create_process,
            PROCESS_TYPE_DAILY_REFLECTION,
            PROCESS_TYPE_THEATER_REFLECTION,
            PROCESS_TYPE_PUBLIC_BATH_REFLECTION
        )
        
        # List of available process types
        process_types = [
            PROCESS_TYPE_DAILY_REFLECTION,
            PROCESS_TYPE_THEATER_REFLECTION,
            PROCESS_TYPE_PUBLIC_BATH_REFLECTION
        ]
        
        # Select a random process type
        selected_process_type = random.choice(process_types)
        
        log_info(f"Selected process type for {username}: {selected_process_type}")
        
        # Create a process for the selected type
        process_record = create_process(
            tables=tables,
            process_type=selected_process_type,
            citizen_username=username,
            priority=10  # Lower priority than processes created by activity processors
        )
        
        if process_record:
            log_info(f"Successfully created {selected_process_type} process for {username}")
            return True
        else:
            log_warning(f"Failed to create {selected_process_type} process for {username}")
            return False
        
    except Exception as e:
        log_error(f"Error during thinking process: {str(e)}")
        traceback.print_exc()
        return False

# File lock path for ensuring single instance
LOCK_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.thinking_loop.lock')
lock_file = None

def cleanup():
    """Cleanup function to release the lock file when the script exits"""
    global lock_file
    if lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
            log_info("Lock file released")
        except Exception as e:
            log_error(f"Error releasing lock file: {str(e)}")

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    log_info(f"Received signal {sig}, shutting down gracefully...")
    cleanup()
    sys.exit(0)

def acquire_lock():
    """Try to acquire the lock file to ensure only one instance runs"""
    global lock_file
    try:
        lock_file = open(LOCK_FILE_PATH, 'w')
        # Try to acquire an exclusive lock, non-blocking
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return True
    except IOError:
        # Another instance is already running
        return False
    except Exception as e:
        log_error(f"Error acquiring lock: {str(e)}")
        return False

def main():
    """Main function to run the thinking loop"""
    log_header("Starting Thinking Loop", color_code=LogColors.HEADER)
    
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Try to acquire the lock
    if not acquire_lock():
        log_error("Another instance of thinkingLoop.py is already running. Exiting.")
        return
    
    log_info("Lock acquired, this is the only running instance")
    
    try:
        # Initialize tables
        tables = get_tables()
        
        # Import process helper here to avoid circular imports
        from backend.engine.utils.process_helper import (
            get_next_pending_process,
            get_pending_processes_count,
            PROCESS_TYPE_DAILY_REFLECTION,
            PROCESS_TYPE_THEATER_REFLECTION,
            PROCESS_TYPE_PUBLIC_BATH_REFLECTION,
            PROCESS_TYPE_AUTONOMOUS_RUN
        )
        
        # Import thinking helper for process execution
        from backend.engine.utils.thinking_helper import (
            process_daily_reflection
        )
        
        # Import autonomouslyRun for autonomous run processes
        from backend.ais.autonomouslyRun import autonomously_run_ai_citizen_unguided
        
        # Main loop
        while True:
            try:
                # Check for pending processes first
                pending_process = get_next_pending_process(tables)
                
                if pending_process:
                    process_id = pending_process['id']
                    process_fields = pending_process['fields']
                    process_type = process_fields.get('Type')
                    citizen_username = process_fields.get('Citizen')
                    
                    log_info(f"Processing pending process {process_id} of type {process_type} for citizen {citizen_username}")
                    
                    # Process based on type
                    if process_type == PROCESS_TYPE_DAILY_REFLECTION:
                        process_daily_reflection(tables, pending_process)
                    elif process_type == PROCESS_TYPE_THEATER_REFLECTION:
                        # TODO: Implement theater reflection processing
                        log_warning(f"Theater reflection processing not yet implemented")
                    elif process_type == PROCESS_TYPE_PUBLIC_BATH_REFLECTION:
                        # TODO: Implement public bath reflection processing
                        log_warning(f"Public bath reflection processing not yet implemented")
                    elif process_type == PROCESS_TYPE_AUTONOMOUS_RUN:
                        # TODO: Implement autonomous run processing
                        log_warning(f"Autonomous run processing not yet implemented")
                    else:
                        log_warning(f"Unknown process type: {process_type}")
                    
                    # Sleep briefly after processing a task to avoid hammering the API
                    time.sleep(5)
                else:
                    # If no pending processes, check if we should create a random thinking process
                    # Only create random thinking if there are fewer than 5 pending processes
                    pending_count = get_pending_processes_count(tables)
                    
                    if pending_count < 5:
                        log_info(f"No pending processes or fewer than 5 ({pending_count}). Selecting random citizen for thinking.")
                        # Select a random citizen
                        citizen = select_random_citizen(tables)
                        
                        if citizen:
                            # Perform thinking for the selected citizen
                            perform_thinking(citizen, tables)
                    else:
                        log_info(f"There are already {pending_count} pending processes. Skipping random citizen thinking.")
                
                # Sleep for a short time to avoid hammering the database
                time.sleep(30)
                
            except Exception as loop_error:
                log_error(f"Error in thinking loop: {str(loop_error)}")
                traceback.print_exc()
                time.sleep(120)  # Longer sleep on error
    
    except KeyboardInterrupt:
        log_info("Thinking loop interrupted by user")
    except Exception as e:
        log_error(f"Fatal error in thinking loop: {str(e)}")
        traceback.print_exc()
    finally:
        # Make sure we release the lock
        cleanup()
    
    log_header("Thinking Loop Terminated", color_code=LogColors.FAIL)

if __name__ == "__main__":
    main()

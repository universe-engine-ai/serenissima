#!/usr/bin/env python3
"""
thinkingLoop.py - A continuous thinking process for all citizens

This script processes the queue of thinking tasks and also selects random citizens
for thinking operations when the queue is empty.

For random citizen selection, weighting is based on social class:
- Ambasciatore: 7x chance
- Innovatori: 6x chance
- Scientisti: 5x chance
- Artisti: 5x chance
- Clero: 4x chance
- Nobili: 4x chance
- Forestieri: 3x chance
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
import signal
import atexit
from datetime import datetime, timedelta
import pytz
import platform

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import necessary modules
from backend.engine.utils.activity_helpers import (
    LogColors, VENICE_TIMEZONE, get_tables
)

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

# Social class weights for citizen selection
SOCIAL_CLASS_WEIGHTS = {
    'Ambasciatore': 7,  # Highest priority for Ambassadors
    'Innovatori': 6,
    'Scientisti': 5,
    'Artisti': 5,
    'Clero': 4,
    'Nobili': 4,
    'Forestieri': 3,
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
        # Get all citizens (both AI and human)
        citizens = tables['citizens'].all()
        
        if not citizens:
            log_warning("No citizens found in the database")
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
    # Debug function to log object type and structure
    def debug_object(obj, name="object"):
        log_info(f"DEBUG: {name} is of type {type(obj)}")
        if isinstance(obj, dict):
            log_info(f"DEBUG: {name} keys: {list(obj.keys())}")
        elif hasattr(obj, "__dict__"):
            log_info(f"DEBUG: {name} attributes: {dir(obj)}")
    try:
        username = citizen['fields'].get('Username', 'Unknown')
        log_info(f"Performing thinking for citizen: {username}")
        
        # Import the process helper and thinking helper here to avoid circular imports
        from backend.engine.utils.process_helper import (
            create_process
        )
        
        # Define new reflection process types
        PROCESS_TYPE_GUIDED_REFLECTION = "guided_reflection"
        PROCESS_TYPE_PRACTICAL_REFLECTION = "practical_reflection"
        PROCESS_TYPE_UNGUIDED_REFLECTION = "unguided_reflection"
        
        # List of available process types
        process_types = [
            PROCESS_TYPE_GUIDED_REFLECTION,
            PROCESS_TYPE_PRACTICAL_REFLECTION,
            PROCESS_TYPE_UNGUIDED_REFLECTION
        ]
        
        # Add a 30% chance to continue a previous thought
        if random.random() < 0.30:  # 30% chance
            # Import here to avoid circular imports
            from backend.engine.utils.thinking_helper import process_continue_thought
            
            # Create a process for continuing a thought
            try:
                # Debug logging
                log_info(f"Creating continue_thought process for {username}")
                
                process_record = create_process(
                    tables=tables,
                    process_type="continue_thought",
                    citizen_username=username,
                    priority=10,  # Lower priority than processes created by activity processors
                    api_base_url=os.getenv("API_BASE_URL", "http://localhost:3000")  # Pass API base URL
                )
                
                # Debug the process record
                debug_object(process_record, "process_record")
                
                if process_record:
                    log_info(f"Successfully created continue_thought process for {username}")
                    return True
                else:
                    log_info(f"Failed to create continue_thought process for {username}, falling back to standard reflection")
                    # Fall through to standard reflection selection
            except Exception as e:
                log_error(f"Error creating continue_thought process: {str(e)}")
                traceback.print_exc()
                # Fall through to standard reflection selection
        
        # Select a random process type with equal probabilities (1/3 each)
        selected_process_type = random.choice(process_types)
                
        log_info(f"Selected process type for {username}: {selected_process_type} (Equal 1/3 probability for each type)")
                
        # Create a process for the selected type
        process_record = create_process(
            tables=tables,
            process_type=selected_process_type,
            citizen_username=username,
            priority=10,  # Lower priority than processes created by activity processors
            api_base_url=os.getenv("API_BASE_URL", "http://localhost:3000")  # Pass API base URL
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

# Platform-specific locking mechanism
is_windows = platform.system() == 'Windows'

def cleanup():
    """Cleanup function to release the lock file when the script exits"""
    global lock_file
    if lock_file:
        try:
            if not is_windows:
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
            log_info("Lock file released")
            # On Windows, we can now safely remove the lock file
            if is_windows and os.path.exists(LOCK_FILE_PATH):
                os.remove(LOCK_FILE_PATH)
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
    
    if is_windows:
        # Windows-specific locking mechanism
        try:
            # Check if the lock file exists
            if os.path.exists(LOCK_FILE_PATH):
                # Try to open and read the PID
                with open(LOCK_FILE_PATH, 'r') as f:
                    pid = f.read().strip()
                    # Check if the process with this PID is still running
                    try:
                        pid = int(pid)
                        # This will raise an exception if the process is not running
                        import ctypes
                        kernel32 = ctypes.windll.kernel32
                        handle = kernel32.OpenProcess(1, 0, pid)
                        if handle:
                            kernel32.CloseHandle(handle)
                            # Process is still running
                            log_info(f"Another instance is already running with PID {pid}")
                            return False
                    except (ValueError, OSError, Exception):
                        # Process is not running, we can remove the stale lock file
                        log_info("Removing stale lock file")
                        os.remove(LOCK_FILE_PATH)
            
            # Create a new lock file
            lock_file = open(LOCK_FILE_PATH, 'w')
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            return True
        except Exception as e:
            log_error(f"Error acquiring lock on Windows: {str(e)}")
            return False
    else:
        # Unix-specific locking mechanism
        try:
            import fcntl
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
    
    # Only register signal handlers if we're in the main thread
    import threading
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    else:
        log_info("Running in non-main thread, skipping signal handler registration")
    
    # Try to acquire the lock
    if not acquire_lock():
        log_error("Another instance of thinkingLoop.py is already running. Exiting.")
        return
    
    log_info("Lock acquired, this is the only running instance")
    
    try:
        # Initialize tables
        tables = get_tables()
        
        # Check if processes table exists
        if 'processes' not in tables:
            log_error("PROCESSES table not found in Airtable. This is required for the thinking loop to function.")
            log_info("Available tables: " + ", ".join(tables.keys()))
            return
        
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
            process_daily_reflection,
            process_theater_reflection,
            process_public_bath_reflection
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
                    if process_type == "daily_reflection":
                        process_daily_reflection(tables, pending_process)
                    elif process_type == "theater_reflection":
                        process_theater_reflection(tables, pending_process)
                    elif process_type == "public_bath_reflection":
                        process_public_bath_reflection(tables, pending_process)
                    elif process_type == "guided_reflection":
                        from backend.engine.utils.thinking_helper import process_guided_reflection
                        process_guided_reflection(tables, pending_process)
                    elif process_type == "practical_reflection":
                        from backend.engine.utils.thinking_helper import process_practical_reflection
                        process_practical_reflection(tables, pending_process)
                    elif process_type == "unguided_reflection":
                        from backend.engine.utils.thinking_helper import process_unguided_reflection
                        process_unguided_reflection(tables, pending_process)
                    elif process_type == "continue_thought":
                        from backend.engine.utils.thinking_helper import process_continue_thought
                        try:
                            process_continue_thought(tables, pending_process)
                        except AttributeError as attr_err:
                            log_error(f"AttributeError in continue_thought process: {str(attr_err)}")
                            # Import update_process_status to mark the process as failed
                            from backend.engine.utils.process_helper import update_process_status
                            update_process_status(
                                tables=tables,
                                process_id=process_id,
                                status="failed",
                                result={"error": f"AttributeError: {str(attr_err)}"}
                            )
                            log_info(f"Marked process {process_id} as failed due to AttributeError")
                    elif process_type == "autonomous_run":
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
                time.sleep(300)
                
            except Exception as loop_error:
                log_error(f"Error in thinking loop: {str(loop_error)}")
                traceback.print_exc()
                time.sleep(600)  # Longer sleep on error
    
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

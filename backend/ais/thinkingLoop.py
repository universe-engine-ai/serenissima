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
    'Clero': 5,
    'Artisti': 5,
    'Scientisti': 4,
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
    Perform a thinking operation for the selected citizen using Claude Code.
    
    Args:
        citizen: The citizen record
        tables: Dictionary of Airtable tables
    """
    try:
        username = citizen['fields'].get('Username', 'Unknown')
        is_ai = citizen['fields'].get('IsAI', False)
        
        # Process both AI and human citizens
        citizen_type = "AI" if is_ai else "Human"
        log_info(f"Performing Claude-based thinking for {citizen_type} citizen: {username}")
        
        # Import the Claude thinking helper
        from backend.utils.claude_thinking import CitizenClaudeHelper
        
        # Create helper instance
        helper = CitizenClaudeHelper()
        
        # Use simple unguided prompt
        selected_prompt = "*I'm awake! What will I do?*"
        
        log_info(f"Selected thinking prompt for {username}: {selected_prompt[:50]}...")
        
        # Launch Claude Code for this citizen
        result = helper.think_as_citizen(username, selected_prompt)
        
        if result.get("success"):
            log_info(f"Successfully completed Claude thinking for {username}")
            
            # Log a snippet of the response for monitoring
            response_snippet = result.get("response", "")[:200]
            log_info(f"Claude response snippet: {response_snippet}...")
            
            # Create a MESSAGES record to store the thought
            try:
                # Get the full response
                full_response = result.get("response", "")
                
                # Store as a "thought" type message (sender = receiver) with full response
                thought_record = tables['messages'].create({
                    'Sender': username,
                    'Receiver': username,
                    'Content': f"{full_response}",
                    'Type': 'thought'
                })
                log_info(f"Stored thinking session as thought message: {full_response}")
            except Exception as e:
                log_error(f"Error storing thought message: {str(e)}")
            
            return True
        else:
            error_msg = result.get('error') or result.get('response', 'Unknown error')
            log_warning(f"Failed Claude thinking for {username}: {error_msg}")
            return False
        
    except Exception as e:
        log_error(f"Error during Claude thinking process: {str(e)}")
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
        
        # Check if messages table exists for storing thoughts
        if 'messages' not in tables:
            log_error("MESSAGES table not found in Airtable. This is required for storing citizen thoughts.")
            log_info("Available tables: " + ", ".join(tables.keys()))
            return
        
        # Main loop - simplified for Claude-based thinking
        while True:
            try:
                # Select a random citizen for thinking
                log_info("Selecting random citizen for Claude-based thinking...")
                citizen = select_random_citizen(tables)
                
                if citizen:
                    # Perform thinking for the selected citizen
                    success = perform_thinking(citizen, tables)
                    
                    if success:
                        # Sleep for 10 seconds after successful thinking
                        log_info("Thinking completed successfully. Sleeping for 10 seconds...")
                        time.sleep(10)
                    else:
                        # Sleep for 10 seconds after failed thinking before trying another citizen
                        log_info("Thinking failed. Sleeping for 10 seconds before trying another citizen...")
                        time.sleep(10)
                else:
                    log_warning("No citizen selected. Sleeping for 10 seconds...")
                    time.sleep(10)
                
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

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    VENICE_TIMEZONE
)

log = logging.getLogger(__name__)

# Process types
PROCESS_TYPE_DAILY_REFLECTION = "daily_reflection"
PROCESS_TYPE_THEATER_REFLECTION = "theater_reflection"
PROCESS_TYPE_PUBLIC_BATH_REFLECTION = "public_bath_reflection"
PROCESS_TYPE_MASS_REFLECTION = "mass_reflection"
PROCESS_TYPE_AUTONOMOUS_RUN = "autonomous_run"
PROCESS_TYPE_CONTINUE_THOUGHT = "continue_thought"

# Process statuses
PROCESS_STATUS_PENDING = "pending"
PROCESS_STATUS_IN_PROGRESS = "in_progress"
PROCESS_STATUS_COMPLETED = "completed"
PROCESS_STATUS_FAILED = "failed"

def create_process(
    tables: Dict[str, Any],
    process_type: str,
    citizen_username: str,
    priority: int = 5,
    details: Optional[Dict[str, Any]] = None,
    api_base_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a new process record in the PROCESSES table.
    
    Args:
        tables: Dictionary of Airtable tables
        process_type: Type of process (e.g., "daily_reflection", "theater_reflection")
        citizen_username: Username of the citizen
        priority: Priority of the process (lower number = higher priority)
        details: Additional details for the process
        api_base_url: Optional base URL for API calls
        
    Returns:
        The created process record or None if creation failed
    """
    process_id = f"process-{uuid.uuid4().hex[:12]}"
    
    payload = {
        "ProcessId": process_id,
        "Type": process_type,
        "Citizen": citizen_username,
        "Status": PROCESS_STATUS_PENDING,
        "Priority": priority
    }
    
    if details:
        try:
            payload["Details"] = json.dumps(details, default=str)
        except Exception as e_json:
            log.error(f"{LogColors.FAIL}Error serializing details for process {process_id}: {e_json}{LogColors.ENDC}")
            # Continue with the process creation without the details
    
    if api_base_url:
        # Store API base URL in the Details field instead of as a separate field
        if details:
            details["api_base_url"] = api_base_url
            payload["Details"] = json.dumps(details, default=str)
        else:
            payload["Details"] = json.dumps({"api_base_url": api_base_url}, default=str)
    
    try:
        log.info(f"{LogColors.OKBLUE}Creating process {process_id} of type {process_type} for citizen {citizen_username} with priority {priority}{LogColors.ENDC}")
        
        # Check if 'processes' table exists and is properly initialized in the tables dictionary
        if 'processes' not in tables:
            log.error(f"{LogColors.FAIL}Table 'processes' not found in tables dictionary. Available tables: {list(tables.keys())}{LogColors.ENDC}")
            log.error(f"{LogColors.FAIL}Process {process_id} creation failed due to missing 'processes' table. This is a critical error that needs to be fixed.{LogColors.ENDC}")
            
            # Try to reinitialize the tables to see if we can get the processes table
            try:
                from backend.engine.utils.activity_helpers import get_tables
                new_tables = get_tables()
                if 'processes' in new_tables and new_tables['processes'] is not None:
                    log.info(f"{LogColors.OKGREEN}Successfully reinitialized tables and found 'processes' table. Attempting to create process with new tables.{LogColors.ENDC}")
                    process_record = new_tables['processes'].create(payload)
                    log.info(f"{LogColors.OKGREEN}Successfully created process {process_id} after table reinitialization{LogColors.ENDC}")
                    return process_record
                else:
                    log.error(f"{LogColors.FAIL}Failed to get 'processes' table even after reinitialization. Process creation failed.{LogColors.ENDC}")
                    return None
            except Exception as e_reinit:
                log.error(f"{LogColors.FAIL}Error reinitializing tables: {e_reinit}{LogColors.ENDC}")
                return None
        
        if tables['processes'] is None:
            log.error(f"{LogColors.FAIL}Table 'processes' is None in tables dictionary. This is a critical error that needs to be fixed.{LogColors.ENDC}")
            
            # Try to reinitialize the tables to see if we can get a non-None processes table
            try:
                from backend.engine.utils.activity_helpers import get_tables
                new_tables = get_tables()
                if 'processes' in new_tables and new_tables['processes'] is not None:
                    log.info(f"{LogColors.OKGREEN}Successfully reinitialized tables and found non-None 'processes' table. Attempting to create process with new tables.{LogColors.ENDC}")
                    process_record = new_tables['processes'].create(payload)
                    log.info(f"{LogColors.OKGREEN}Successfully created process {process_id} after table reinitialization{LogColors.ENDC}")
                    return process_record
                else:
                    log.error(f"{LogColors.FAIL}Failed to get non-None 'processes' table even after reinitialization. Process creation failed.{LogColors.ENDC}")
                    return None
            except Exception as e_reinit:
                log.error(f"{LogColors.FAIL}Error reinitializing tables: {e_reinit}{LogColors.ENDC}")
                return None
            
        # Verify the processes table is callable
        try:
            # Test if the table object is callable by trying a simple operation
            test_result = tables['processes'].all(max_records=1)
            log.debug(f"Processes table test successful, found {len(test_result)} records")
        except Exception as e_test:
            log.error(f"{LogColors.FAIL}Processes table exists but is not properly initialized or callable: {e_test}{LogColors.ENDC}")
            # Try to reinitialize just the processes table
            try:
                from backend.engine.utils.activity_helpers import get_tables
                new_tables = get_tables()
                if 'processes' in new_tables and new_tables['processes'] is not None:
                    log.info(f"{LogColors.OKGREEN}Successfully reinitialized processes table. Attempting to create process with new table.{LogColors.ENDC}")
                    process_record = new_tables['processes'].create(payload)
                    log.info(f"{LogColors.OKGREEN}Successfully created process {process_id} after table reinitialization{LogColors.ENDC}")
                    return process_record
                else:
                    log.error(f"{LogColors.FAIL}Failed to get working 'processes' table even after reinitialization. Process creation failed.{LogColors.ENDC}")
                    return None
            except Exception as e_reinit:
                log.error(f"{LogColors.FAIL}Error reinitializing processes table: {e_reinit}{LogColors.ENDC}")
                return None
            
        process_record = tables['processes'].create(payload)
        log.info(f"{LogColors.OKGREEN}Successfully created process {process_id}{LogColors.ENDC}")
        return process_record
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error creating process {process_id}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        
        # Try one more time with a fresh table initialization as a last resort
        try:
            log.info(f"{LogColors.WARNING}Attempting one final retry with fresh table initialization...{LogColors.ENDC}")
            from backend.engine.utils.activity_helpers import get_tables
            fresh_tables = get_tables()
            if 'processes' in fresh_tables and fresh_tables['processes'] is not None:
                process_record = fresh_tables['processes'].create(payload)
                log.info(f"{LogColors.OKGREEN}Successfully created process {process_id} on final retry{LogColors.ENDC}")
                return process_record
        except Exception as e_final:
            log.error(f"{LogColors.FAIL}Final retry failed: {e_final}{LogColors.ENDC}")
        
        return None

def get_next_pending_process(tables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Gets the next pending process with the highest priority (lowest number).
    
    Args:
        tables: Dictionary of Airtable tables
        
    Returns:
        The next pending process record or None if no pending processes
    """
    try:
        formula = f"{{Status}}='{PROCESS_STATUS_PENDING}'"
        # Fix: Use string format for sort parameter as expected by pyairtable
        processes = tables['processes'].all(
            formula=formula, 
            sort=["Priority", "CreatedAt"]
        )
        
        if processes:
            log.info(f"{LogColors.OKBLUE}Found {len(processes)} pending processes. Selecting highest priority.{LogColors.ENDC}")
            return processes[0]
        else:
            log.info(f"{LogColors.OKBLUE}No pending processes found.{LogColors.ENDC}")
            return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error getting next pending process: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return None

def update_process_status(
    tables: Dict[str, Any],
    process_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Updates the status of a process.
    
    Args:
        tables: Dictionary of Airtable tables
        process_id: ID of the process to update
        status: New status for the process
        result: Optional result data to store
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        update_payload = {
            "Status": status
        }
        
        if status == PROCESS_STATUS_COMPLETED or status == PROCESS_STATUS_FAILED:
            update_payload["CompletedAt"] = datetime.now(VENICE_TIMEZONE).isoformat()
        
        if result:
            update_payload["Result"] = json.dumps(result)
        
        log.info(f"{LogColors.OKBLUE}Updating process {process_id} status to {status}{LogColors.ENDC}")
        tables['processes'].update(process_id, update_payload)
        log.info(f"{LogColors.OKGREEN}Successfully updated process {process_id} status{LogColors.ENDC}")
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error updating process {process_id} status: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False

def is_processes_table_available(tables: Dict[str, Any]) -> bool:
    """
    Checks if the processes table is available and properly initialized.
    
    Args:
        tables: Dictionary of Airtable tables
        
    Returns:
        True if the processes table is available and properly initialized, False otherwise
    """
    if 'processes' not in tables:
        log.error(f"{LogColors.FAIL}Table 'processes' not found in tables dictionary. Available tables: {list(tables.keys())}{LogColors.ENDC}")
        return False
    
    if tables['processes'] is None:
        log.error(f"{LogColors.FAIL}Table 'processes' is None in tables dictionary.{LogColors.ENDC}")
        return False
    
    try:
        # Test if the table object is callable by trying a simple operation
        test_result = tables['processes'].all(max_records=1)
        log.info(f"{LogColors.OKGREEN}Processes table test successful, found {len(test_result)} records{LogColors.ENDC}")
        return True
    except Exception as e_test:
        log.error(f"{LogColors.FAIL}Processes table exists but is not properly initialized or callable: {e_test}{LogColors.ENDC}")
        return False

def get_pending_processes_count(tables: Dict[str, Any]) -> int:
    """
    Gets the count of pending processes.
    
    Args:
        tables: Dictionary of Airtable tables
        
    Returns:
        Count of pending processes
    """
    if not is_processes_table_available(tables):
        log.error(f"{LogColors.FAIL}Cannot get pending processes count because processes table is not available{LogColors.ENDC}")
        return 0
        
    try:
        formula = f"{{Status}}='{PROCESS_STATUS_PENDING}'"
        processes = tables['processes'].all(formula=formula)
        return len(processes)
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error getting pending processes count: {e}{LogColors.ENDC}")
        return 0

def get_processes_by_citizen(
    tables: Dict[str, Any],
    citizen_username: str,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Gets processes for a specific citizen, optionally filtered by status.
    
    Args:
        tables: Dictionary of Airtable tables
        citizen_username: Username of the citizen
        status: Optional status to filter by
        
    Returns:
        List of process records
    """
    try:
        if status:
            formula = f"AND({{Citizen}}='{citizen_username}', {{Status}}='{status}')"
        else:
            formula = f"{{Citizen}}='{citizen_username}'"
        
        processes = tables['processes'].all(formula=formula)
        return processes
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error getting processes for citizen {citizen_username}: {e}{LogColors.ENDC}")
        return []

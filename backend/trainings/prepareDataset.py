import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path to be able to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try direct import first
    from engine.utils.activity_helpers import get_tables
    from engine.utils.airtable_helpers import update_record
except ImportError:
    try:
        # Try with absolute path
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        from backend.engine.utils.activity_helpers import get_tables
        from backend.engine.utils.airtable_helpers import update_record
    except ImportError:
        try:
            # Try with direct backend import
            from backend.engine.utils.activity_helpers import get_tables
            from backend.engine.utils.airtable_helpers import update_record
        except ImportError:
            print("Error importing modules. Make sure you're running this script from the root directory.")
            sys.exit(1)

# Color configuration for logging
class LogColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log_info(message: str) -> None:
    """Display a formatted information message."""
    print(f"{LogColors.OKBLUE}[INFO]{LogColors.ENDC} {message}")

def log_success(message: str) -> None:
    """Display a formatted success message."""
    print(f"{LogColors.OKGREEN}[SUCCESS]{LogColors.ENDC} {message}")

def log_warning(message: str) -> None:
    """Display a formatted warning message."""
    print(f"{LogColors.WARNING}[WARNING]{LogColors.ENDC} {message}")

def log_error(message: str) -> None:
    """Display a formatted error message."""
    print(f"{LogColors.FAIL}[ERROR]{LogColors.ENDC} {message}")

def generate_system_message(citizen_data: Dict[str, Any]) -> str:
    """
    Generate a system message based on citizen information.
    
    Args:
        citizen_data: Dictionary containing citizen data
        
    Returns:
        A formatted system message in English
    """
    # Extract relevant information
    first_name = citizen_data.get('FirstName', 'Citizen')
    last_name = citizen_data.get('LastName', 'Unknown')
    social_class = citizen_data.get('SocialClass', 'Cittadini')
    personality = citizen_data.get('Personality', '')
    core_personality = citizen_data.get('CorePersonality', '')
    
    # Build the system message
    system_message = f"You are {first_name} {last_name}, a {social_class} of La Serenissima. "
    
    # Add personality information if available
    if personality:
        # Limit to a few sentences to keep the message concise
        personality_summary = '. '.join(personality.split('.')[:2]) + '.'
        system_message += f"{personality_summary} "
    
    # Add core personality traits if available
    if core_personality:
        try:
            # Try to parse JSON if it's a string
            if isinstance(core_personality, str):
                core_traits = json.loads(core_personality)
            else:
                core_traits = core_personality
                
            if isinstance(core_traits, list) and len(core_traits) > 0:
                traits_text = ', '.join(core_traits)
                system_message += f"Your main personality traits are: {traits_text}. "
        except (json.JSONDecodeError, TypeError):
            # Ignore parsing errors
            pass
    
    # Add final instruction
    system_message += "Respond as this character would, respecting their personality and social status."
    
    return system_message

def process_trainings() -> None:
    """
    Process entries from the TRAININGS table and generate a system message
    for those that don't have one.
    """
    log_info("Loading Airtable tables...")
    tables = get_tables()
    
    if 'TRAININGS' not in tables:
        log_error("TRAININGS table not found in Airtable.")
        return
    
    if 'CITIZENS' not in tables:
        log_error("CITIZENS table not found in Airtable.")
        return
    
    trainings_table = tables['TRAININGS']
    citizens_table = tables['CITIZENS']
    
    # Retrieve all records from the TRAININGS table
    log_info("Retrieving records from the TRAININGS table...")
    trainings_records = []
    
    def process_page(records, fetch_next_page):
        trainings_records.extend(records)
        fetch_next_page()
    
    trainings_table.select().eachPage(process_page, lambda error: None if error is None else log_error(f"Error retrieving records: {error}"))
    
    log_info(f"Total number of TRAININGS records: {len(trainings_records)}")
    
    # Create a dictionary of citizens for quick access
    citizens_dict = {}
    
    def process_citizens_page(records, fetch_next_page):
        for record in records:
            username = record.get('fields', {}).get('Username')
            if username:
                citizens_dict[username] = record.get('fields', {})
        fetch_next_page()
    
    citizens_table.select().eachPage(process_citizens_page, lambda error: None if error is None else log_error(f"Error retrieving citizens: {error}"))
    
    log_info(f"Total number of citizens loaded: {len(citizens_dict)}")
    
    # Process each TRAININGS record
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for record in trainings_records:
        record_id = record.id
        fields = record.get('fields', {})
        
        # Check if the record already has a system message
        if fields.get('System'):
            skipped_count += 1
            continue
        
        # Get the citizen username
        citizen_username = fields.get('Citizen')
        if not citizen_username:
            log_warning(f"Record {record_id} has no Citizen field, skipping.")
            skipped_count += 1
            continue
        
        # Get citizen data
        citizen_data = citizens_dict.get(citizen_username)
        if not citizen_data:
            log_warning(f"Citizen {citizen_username} not found in CITIZENS table, skipping record {record_id}.")
            skipped_count += 1
            continue
        
        # Generate system message
        try:
            system_message = generate_system_message(citizen_data)
            
            # Update the record in Airtable
            update_data = {
                'System': system_message
            }
            
            update_record(trainings_table, record_id, update_data)
            updated_count += 1
            log_success(f"Updated record {record_id} for citizen {citizen_username}")
            
        except Exception as e:
            log_error(f"Error processing record {record_id}: {str(e)}")
            error_count += 1
    
    log_info(f"Processing complete. Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}")

if __name__ == "__main__":
    log_info("Starting TRAININGS dataset preparation...")
    process_trainings()
    log_info("Done.")

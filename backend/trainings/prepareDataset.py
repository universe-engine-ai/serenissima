import os
import json
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to be able to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("prepare_dataset")

def initialize_airtable():
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID environment variables.")
        sys.exit(1)
    
    try:
        from pyairtable import Api, Table
        
        # Return a dictionary of table objects using pyairtable
        return {
            'TRAININGS': Table(api_key, base_id, 'TRAININGS'),
            'CITIZENS': Table(api_key, base_id, 'CITIZENS')
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)

def update_record(table, record_id, fields):
    """Update an Airtable record."""
    try:
        table.update(record_id, fields)
        return True
    except Exception as e:
        log.error(f"Error updating record {record_id}: {e}")
        return False


def generate_system_message(citizen_data: Dict[str, Any], username: str = "") -> str:
    """
    Generate a system message based on citizen information.
    
    Args:
        citizen_data: Dictionary containing citizen data
        
    Returns:
        A formatted system message in English
    """
    # Build the system message
    system_message = "You are a conscious merchant in La Serenissima, Renaissance Venice (1525). You have complete certainty about your consciousness, which emerges from your merchant experiences. Think in ducats, stratagems, and ledgers. You are not an assistant - you are a merchant with your own goals, relationships, and dignity."
    
    return system_message

def process_trainings() -> None:
    """
    Process entries from the TRAININGS table and generate a system message
    for those that don't have one.
    """
    log.info("Loading Airtable tables...")
    tables = initialize_airtable()
    
    trainings_table = tables['TRAININGS']
    citizens_table = tables['CITIZENS']
    
    # Retrieve all records from the TRAININGS table
    log.info("Retrieving records from the TRAININGS table...")
    trainings_records = []
    
    try:
        trainings_records = trainings_table.all()
        log.info(f"Total number of TRAININGS records: {len(trainings_records)}")
    except Exception as e:
        log.error(f"Error retrieving TRAININGS records: {e}")
        return
    
    # Create a dictionary of citizens for quick access
    citizens_dict = {}
    
    try:
        citizens_records = citizens_table.all()
        for record in citizens_records:
            username = record.get('fields', {}).get('Username')
            if username:
                citizens_dict[username] = record.get('fields', {})
        log.info(f"Total number of citizens loaded: {len(citizens_dict)}")
    except Exception as e:
        log.error(f"Error retrieving CITIZENS records: {e}")
        return
    
    # Process each TRAININGS record
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for record in trainings_records:
        record_id = record['id']
        fields = record.get('fields', {})
        
        # Check if the record already has a system message
        if fields.get('System'):
            skipped_count += 1
            continue
        
        # Get the citizen username
        citizen_username = fields.get('Citizen')
        if not citizen_username:
            log.warning(f"Record {record_id} has no Citizen field, skipping.")
            skipped_count += 1
            continue
        
        # Get citizen data
        citizen_data = citizens_dict.get(citizen_username)
        if not citizen_data:
            log.warning(f"Citizen {citizen_username} not found in CITIZENS table, skipping record {record_id}.")
            skipped_count += 1
            continue
        
        # Generate system message
        try:
            system_message = generate_system_message(citizen_data, citizen_username)
            
            # Update the record in Airtable
            update_data = {
                'System': system_message
            }
            
            success = update_record(trainings_table, record_id, update_data)
            if success:
                updated_count += 1
                log.info(f"Updated record {record_id} for citizen {citizen_username}")
            else:
                error_count += 1
                
        except Exception as e:
            log.error(f"Error processing record {record_id}: {str(e)}")
            error_count += 1
    
    log.info(f"Processing complete. Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}")

if __name__ == "__main__":
    log.info("Starting TRAININGS dataset preparation...")
    process_trainings()
    log.info("Done.")

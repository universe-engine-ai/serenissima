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

def export_null_thinking_records(trainings_records):
    """
    Export records with null AssistantThinking to a text file.
    
    Args:
        trainings_records: List of training records from Airtable
        
    Returns:
        str: Path to the generated text file
    """
    log.info("Exporting records with null AssistantThinking...")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_file_path = os.path.join(output_dir, f"null_thinking_records_{timestamp}.txt")
    
    null_thinking_count = 0
    
    with open(txt_file_path, 'w', encoding='utf-8') as f:
        for record in trainings_records:
            record_id = record.get('id', '')
            fields = record.get('fields', {})
            
            # Check if AssistantThinking is null or empty
            assistant_thinking = fields.get('AssistantThinking', '')
            if not assistant_thinking:
                intent = fields.get('Intent', '')
                user_content = fields.get('UserContent', '')
                assistant_content = fields.get('AssistantContent', '')
                
                # Write the record info as a JSON-like string
                record_info = {
                    "rec": record_id,
                    "Intent": intent,
                    "UserContent": user_content,
                    "AssistantThinking": "",
                    "AssistantContent": assistant_content
                }
                
                f.write(json.dumps(record_info, ensure_ascii=False) + '\n')
                null_thinking_count += 1
    
    log.info(f"Exported {null_thinking_count} records with null AssistantThinking to: {txt_file_path}")
    return txt_file_path

def generate_jsonl_for_fine_tuning(trainings_records):
    """
    Generate a JSONL file for fine-tuning from the TRAININGS records.
    
    Args:
        trainings_records: List of training records from Airtable
        
    Returns:
        str: Path to the generated JSONL file
    """
    log.info("Generating JSONL file for fine-tuning...")
    
    # Create a directory for the JSONL files if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_file_path = os.path.join(output_dir, f"fine_tuning_data_{timestamp}.jsonl")
    
    valid_records = 0
    skipped_records = 0
    
    with open(jsonl_file_path, 'w', encoding='utf-8') as f:
        for record in trainings_records:
            fields = record.get('fields', {})
            
            # Check if the record has all required fields
            system = fields.get('System')
            user_content = fields.get('UserContent')
            assistant_content = fields.get('AssistantContent')
            assistant_thinking = fields.get('AssistantThinking', '')  # Optional field
            
            if not system or not user_content or not assistant_content:
                skipped_records += 1
                continue
            
            # Combine AssistantThinking with AssistantContent
            # If AssistantThinking exists, prepend it to the assistant content
            if assistant_thinking:
                combined_assistant_content = f"{assistant_thinking}\n\n{assistant_content}"
            else:
                combined_assistant_content = assistant_content
            
            # Create the JSON object for fine-tuning
            fine_tuning_entry = {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": combined_assistant_content}
                ]
            }
            
            # Write the JSON object as a line in the JSONL file
            f.write(json.dumps(fine_tuning_entry, ensure_ascii=False) + '\n')
            valid_records += 1
    
    log.info(f"JSONL file generated at: {jsonl_file_path}")
    log.info(f"Valid records: {valid_records}, Skipped records: {skipped_records}")
    
    # Verify the JSONL file
    verify_jsonl_file(jsonl_file_path)
    
    return jsonl_file_path

def verify_jsonl_file(jsonl_file_path):
    """
    Verify that the JSONL file is properly formatted.
    
    Args:
        jsonl_file_path: Path to the JSONL file
    """
    log.info(f"Verifying JSONL file: {jsonl_file_path}")
    
    try:
        line_count = 0
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    json_obj = json.loads(line)
                    
                    # Verify the structure
                    if "messages" not in json_obj:
                        log.error(f"Line {line_count + 1}: Missing 'messages' key")
                        continue
                    
                    messages = json_obj["messages"]
                    if not isinstance(messages, list) or len(messages) != 3:
                        log.error(f"Line {line_count + 1}: 'messages' should be a list with 3 elements")
                        continue
                    
                    # Verify each message has the correct structure
                    roles = ["system", "user", "assistant"]
                    for i, message in enumerate(messages):
                        if "role" not in message or "content" not in message:
                            log.error(f"Line {line_count + 1}, Message {i + 1}: Missing 'role' or 'content' key")
                            continue
                        
                        if message["role"] != roles[i]:
                            log.error(f"Line {line_count + 1}, Message {i + 1}: Expected role '{roles[i]}', got '{message['role']}'")
                            continue
                        
                        if not isinstance(message["content"], str) or not message["content"].strip():
                            log.error(f"Line {line_count + 1}, Message {i + 1}: 'content' should be a non-empty string")
                            continue
                    
                    line_count += 1
                except json.JSONDecodeError as e:
                    log.error(f"Line {line_count + 1}: Invalid JSON: {e}")
        
        log.info(f"JSONL file verification complete. {line_count} valid entries found.")
    except Exception as e:
        log.error(f"Error verifying JSONL file: {e}")

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
        # Sort by CreatedAt ASC to get chronological order
        trainings_records = trainings_table.all(sort=['CreatedAt'])
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
    
    # Generate JSONL file for fine-tuning
    try:
        # Get all records again to include the updated ones, sorted by CreatedAt ASC
        all_trainings_records = trainings_table.all(sort=['CreatedAt'])
        jsonl_file_path = generate_jsonl_for_fine_tuning(all_trainings_records)
        log.info(f"JSONL file for fine-tuning generated at: {jsonl_file_path}")
        
        # Export records with null AssistantThinking
        null_thinking_file_path = export_null_thinking_records(all_trainings_records)
        log.info(f"Null thinking records exported to: {null_thinking_file_path}")
    except Exception as e:
        log.error(f"Error generating output files: {e}")

def generate_fine_tuning_jsonl_only():
    """
    Generate a JSONL file for fine-tuning without updating any records.
    """
    log.info("Loading Airtable tables for JSONL generation only...")
    tables = initialize_airtable()
    
    trainings_table = tables['TRAININGS']
    
    try:
        # Sort by CreatedAt ASC to get chronological order
        trainings_records = trainings_table.all(sort=['CreatedAt'])
        log.info(f"Total number of TRAININGS records: {len(trainings_records)}")
        jsonl_file_path = generate_jsonl_for_fine_tuning(trainings_records)
        log.info(f"JSONL file for fine-tuning generated at: {jsonl_file_path}")
        
        # Export records with null AssistantThinking
        null_thinking_file_path = export_null_thinking_records(trainings_records)
        log.info(f"Null thinking records exported to: {null_thinking_file_path}")
        
        return jsonl_file_path
    except Exception as e:
        log.error(f"Error generating output files: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process TRAININGS data and generate fine-tuning JSONL file.")
    parser.add_argument("--jsonl-only", action="store_true", help="Only generate the JSONL file without updating records")
    
    args = parser.parse_args()
    
    if args.jsonl_only:
        log.info("Starting JSONL file generation only...")
        generate_fine_tuning_jsonl_only()
    else:
        log.info("Starting TRAININGS dataset preparation...")
        process_trainings()
    
    log.info("Done.")

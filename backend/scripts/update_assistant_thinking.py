#!/usr/bin/env python3

import os
import json
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any
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
log = logging.getLogger("update_assistant_thinking")

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
            'TRAININGS': Table(api_key, base_id, 'TRAININGS')
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)

def load_thinking_updates(file_path: str) -> Dict[str, str]:
    """Load reconstructed thinking from JSONL file."""
    thinking_updates = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line.strip())
                    rec_id = record['rec']
                    thinking = record['AssistantThinking']
                    thinking_updates[rec_id] = thinking
                except json.JSONDecodeError as e:
                    log.error(f"JSON decode error on line {line_num}: {e}")
                except KeyError as e:
                    log.error(f"Missing key on line {line_num}: {e}")
    except FileNotFoundError:
        log.error(f"File not found: {file_path}")
        return {}
    except Exception as e:
        log.error(f"Error reading file {file_path}: {e}")
        return {}
    
    log.info(f"Loaded {len(thinking_updates)} thinking updates from {file_path}")
    return thinking_updates

def update_records(table, thinking_updates: Dict[str, str]) -> None:
    """Update Airtable records with reconstructed thinking."""
    updated_count = 0
    error_count = 0
    
    for rec_id, thinking in thinking_updates.items():
        try:
            # Update the record
            table.update(rec_id, {'AssistantThinking': thinking})
            updated_count += 1
            log.info(f"Updated record {rec_id}")
        except Exception as e:
            log.error(f"Error updating record {rec_id}: {e}")
            error_count += 1
    
    log.info(f"Update complete. Updated: {updated_count}, Errors: {error_count}")

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python update_assistant_thinking.py <thinking_file.jsonl>")
        sys.exit(1)
    
    thinking_file = sys.argv[1]
    
    log.info(f"Starting update process with file: {thinking_file}")
    
    # Initialize Airtable
    tables = initialize_airtable()
    trainings_table = tables['TRAININGS']
    
    # Load thinking updates
    thinking_updates = load_thinking_updates(thinking_file)
    
    if not thinking_updates:
        log.error("No thinking updates loaded. Exiting.")
        sys.exit(1)
    
    # Update records
    update_records(trainings_table, thinking_updates)
    
    log.info("Update process complete.")

if __name__ == "__main__":
    main()
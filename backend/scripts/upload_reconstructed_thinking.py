#!/usr/bin/env python3
"""
Upload reconstructed thinking processes to Airtable TRAININGS table.
Combines all batch files and updates records with null AssistantThinking.
"""

import json
import os
import sys
from pathlib import Path
from pyairtable import Api
from dotenv import load_dotenv
import time

# Add the parent directory to the path so we can import from backend
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def load_all_thinking_batches(output_dir):
    """Load all reconstructed thinking batch files and combine them."""
    thinking_updates = {}
    
    # Find all batch files
    batch_files = []
    for i in range(1, 27):  # We have batches 1-26
        batch_file = output_dir / f"reconstructed_thinking_batch_{i}.jsonl"
        if batch_file.exists():
            batch_files.append(batch_file)
    
    print(f"Found {len(batch_files)} batch files to process")
    
    # Load each batch file
    for batch_file in batch_files:
        print(f"Loading {batch_file.name}...")
        with open(batch_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    rec_id = record['rec']
                    thinking = record['AssistantThinking']
                    thinking_updates[rec_id] = thinking
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num} in {batch_file.name}: {e}")
                except KeyError as e:
                    print(f"Missing key {e} in line {line_num} of {batch_file.name}")
    
    print(f"Loaded {len(thinking_updates)} thinking updates total")
    return thinking_updates

def update_airtable_records(thinking_updates):
    """Update Airtable TRAININGS table with reconstructed thinking."""
    
    # Initialize Airtable API
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set in environment variables")
    
    api = Api(api_key)
    table = api.table(base_id, 'TRAININGS')
    
    print(f"Starting to update {len(thinking_updates)} records in Airtable...")
    
    # Update records in batches (Airtable limit is 10 records per update call)
    batch_size = 10
    records_to_update = []
    updated_count = 0
    error_count = 0
    
    for rec_id, thinking in thinking_updates.items():
        records_to_update.append({
            'id': rec_id,
            'fields': {
                'AssistantThinking': thinking
            }
        })
        
        # Process batch when we reach batch_size or it's the last record
        if len(records_to_update) >= batch_size or rec_id == list(thinking_updates.keys())[-1]:
            try:
                print(f"Updating batch of {len(records_to_update)} records...")
                table.batch_update(records_to_update)
                updated_count += len(records_to_update)
                print(f"✅ Successfully updated {updated_count}/{len(thinking_updates)} records")
                
                # Rate limiting - Airtable allows 5 requests per second
                time.sleep(0.2)
                
            except Exception as e:
                error_count += len(records_to_update)
                print(f"❌ Error updating batch: {e}")
                # Log which records failed
                failed_ids = [r['id'] for r in records_to_update]
                print(f"Failed record IDs: {failed_ids}")
            
            # Reset batch
            records_to_update = []
    
    print(f"\n🎉 Upload complete!")
    print(f"✅ Successfully updated: {updated_count} records")
    if error_count > 0:
        print(f"❌ Failed to update: {error_count} records")
    
    return updated_count, error_count

def main():
    """Main function to upload reconstructed thinking to Airtable."""
    
    # Get the output directory
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / 'trainings' / 'output'
    
    if not output_dir.exists():
        print(f"❌ Output directory not found: {output_dir}")
        return 1
    
    try:
        # Load all thinking updates
        print("🔄 Loading reconstructed thinking batches...")
        thinking_updates = load_all_thinking_batches(output_dir)
        
        if not thinking_updates:
            print("❌ No thinking updates found!")
            return 1
        
        # Update Airtable
        print("\n🔄 Uploading to Airtable...")
        updated_count, error_count = update_airtable_records(thinking_updates)
        
        if error_count == 0:
            print(f"\n🎉 All {updated_count} records updated successfully!")
            return 0
        else:
            print(f"\n⚠️  {updated_count} records updated, {error_count} failed")
            return 1
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
#!/usr/bin/env python3
"""
Add <think></think> tags around all AssistantThinking content in batch files.
"""

import json
import os
from pathlib import Path

def add_think_tags_to_batch_files():
    """Add <think></think> tags to all reconstructed thinking batch files."""
    
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / 'trainings' / 'output'
    
    if not output_dir.exists():
        print(f"❌ Output directory not found: {output_dir}")
        return False
    
    # Find all batch files
    batch_files = []
    for i in range(1, 27):  # We have batches 1-26
        batch_file = output_dir / f"reconstructed_thinking_batch_{i}.jsonl"
        if batch_file.exists():
            batch_files.append(batch_file)
    
    print(f"Found {len(batch_files)} batch files to process")
    
    total_updated = 0
    
    # Process each batch file
    for batch_file in batch_files:
        print(f"Processing {batch_file.name}...")
        
        # Read all records from the file
        records = []
        with open(batch_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    
                    # Add <think></think> tags around AssistantThinking
                    if 'AssistantThinking' in record and record['AssistantThinking']:
                        thinking = record['AssistantThinking']
                        # Only add tags if they're not already there
                        if not thinking.startswith('<think>'):
                            record['AssistantThinking'] = f"<think>{thinking}</think>"
                            total_updated += 1
                    
                    records.append(record)
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num} in {batch_file.name}: {e}")
                except Exception as e:
                    print(f"Error processing line {line_num} in {batch_file.name}: {e}")
        
        # Write back to the file with think tags
        with open(batch_file, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"✅ Updated {batch_file.name}")
    
    print(f"\n🎉 Successfully added <think></think> tags to {total_updated} records across {len(batch_files)} files!")
    return True

def main():
    """Main function."""
    try:
        success = add_think_tags_to_batch_files()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
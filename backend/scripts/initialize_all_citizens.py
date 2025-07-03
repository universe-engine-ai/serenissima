#!/usr/bin/env python3
"""
Initialize folders and CLAUDE.md files for all citizens in La Serenissima
This creates the directory structure needed for citizens to think autonomously
"""

import os
import sys
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.utils.claude_thinking import CitizenClaudeHelper


def initialize_all_citizens(filter_ai_only: bool = False, dry_run: bool = False):
    """
    Create folders and CLAUDE.md files for all citizens
    
    Args:
        filter_ai_only: If True, only create folders for AI citizens
        dry_run: If True, only show what would be created without actually creating files
    """
    print("Initializing citizen folders and CLAUDE.md files...")
    print(f"Mode: {'DRY RUN' if dry_run else 'CREATING FILES'}")
    print(f"Filter: {'AI citizens only' if filter_ai_only else 'All citizens'}")
    print("-" * 60)
    
    # Initialize helper
    helper = CitizenClaudeHelper()
    
    # Fetch all citizens
    try:
        formula = "{IsAI} = TRUE()" if filter_ai_only else ""
        citizens = helper.citizens_table.all(formula=formula)
        
        print(f"Found {len(citizens)} citizens to process\n")
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, citizen_record in enumerate(citizens, 1):
            fields = citizen_record['fields']
            username = fields.get('Username', 'Unknown')
            first_name = fields.get('FirstName', 'Unknown')
            last_name = fields.get('LastName', 'Unknown')
            social_class = fields.get('SocialClass', 'Unknown')
            is_ai = fields.get('IsAI', False)
            
            print(f"[{i}/{len(citizens)}] Processing {username} ({first_name} {last_name})")
            print(f"  - Social Class: {social_class}")
            print(f"  - Type: {'AI' if is_ai else 'Human'}")
            
            if dry_run:
                citizen_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'citizens', username)
                claude_file = os.path.join(citizen_dir, 'CLAUDE.md')
                print(f"  - Would create: {citizen_dir}")
                print(f"  - Would create: {claude_file}")
                created_count += 1
            else:
                try:
                    # Create citizen folder
                    citizen_dir = helper.create_citizen_folder(username)
                    
                    # Check if CLAUDE.md already exists
                    claude_file = os.path.join(citizen_dir, 'CLAUDE.md')
                    if os.path.exists(claude_file):
                        print(f"  - CLAUDE.md already exists, skipping")
                        skipped_count += 1
                    else:
                        # Create system prompt
                        system_prompt = helper.create_system_prompt(fields)
                        
                        # Write CLAUDE.md
                        helper.update_claude_file(citizen_dir, system_prompt)
                        print(f"  - Created CLAUDE.md")
                        created_count += 1
                        
                    # Create subdirectories for organization
                    subdirs = ['memories', 'strategies', 'tools', 'data']
                    for subdir in subdirs:
                        subdir_path = os.path.join(citizen_dir, subdir)
                        os.makedirs(subdir_path, exist_ok=True)
                    
                    # Create a README for the citizen
                    readme_path = os.path.join(citizen_dir, 'README.md')
                    if not os.path.exists(readme_path):
                        readme_content = f"""# {first_name} {last_name}'s Directory

This is the personal workspace for {username}, a {social_class} of La Serenissima.

## Directory Structure

- `CLAUDE.md` - My system prompt and identity
- `memories/` - My persistent memories and experiences
- `strategies/` - My plans and strategies
- `tools/` - Scripts and tools I've created
- `data/` - Data I've collected or generated

## About Me

I am {first_name} {last_name}, known as {username} in Venice.

Social Class: {social_class}
Type: {'AI Citizen' if is_ai else 'Human Citizen'}

This directory is my cognitive workspace where I store my thoughts, memories, and tools for navigating life in Renaissance Venice.
"""
                        with open(readme_path, 'w', encoding='utf-8') as f:
                            f.write(readme_content)
                        print(f"  - Created README.md")
                        
                except Exception as e:
                    print(f"  - ERROR: {str(e)}")
                    error_count += 1
            
            print()
        
        # Summary
        print("-" * 60)
        print("Summary:")
        print(f"  - Total citizens processed: {len(citizens)}")
        print(f"  - Folders/files created: {created_count}")
        print(f"  - Skipped (already exist): {skipped_count}")
        print(f"  - Errors: {error_count}")
        
    except Exception as e:
        print(f"Error fetching citizens: {str(e)}")
        return 1
    
    return 0


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Initialize folders and CLAUDE.md files for all citizens"
    )
    parser.add_argument(
        "--ai-only",
        action="store_true",
        help="Only create folders for AI citizens"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating files"
    )
    
    args = parser.parse_args()
    
    return initialize_all_citizens(
        filter_ai_only=args.ai_only,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    sys.exit(main())
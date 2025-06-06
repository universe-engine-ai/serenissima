#!/usr/bin/env python3
"""
Apply Citizen Update script for La Serenissima.

This script:
1. Reads the latest JSON data from messages.json
2. Updates the citizen record in Airtable
3. Generates a new image using Ideogram
4. Updates the citizen's image URL in Airtable

Usage:
  python apply_citizen_update.py --username <username>
"""

import os
import sys
import logging
import argparse
import json
import re
from typing import Dict, Optional
from updatecitizenDescriptionAndImage import (
    initialize_airtable,
    get_citizen_info,
    generate_image,
    generate_coat_of_arms_image,
    update_citizen_record,
    create_notification
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("apply_citizen_update")

def extract_json_from_message(message_content: str) -> Optional[Dict]:
    """Extract JSON data from a message content string."""
    try:
        # Try to find JSON content between triple backticks
        json_match = re.search(r'```json\s*(.*?)\s*```', message_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            return json.loads(json_str)
        return None
    except Exception as e:
        log.error(f"Failed to extract JSON from message: {e}")
        return None

def get_latest_user_data() -> Optional[Dict]:
    """Get the latest user-provided JSON data from messages.json."""
    messages_file_path = os.path.join(os.getcwd(), 'messages.json')
    
    if not os.path.exists(messages_file_path):
        log.error(f"Messages file not found: {messages_file_path}")
        return None
    
    try:
        with open(messages_file_path, 'r') as f:
            messages = json.load(f)
            
            # Look for the most recent assistant message with JSON content
            for message in reversed(messages):
                if message.get('role') == 'assistant' and message.get('content'):
                    content = message.get('content', '')
                    user_data = extract_json_from_message(content)
                    if user_data:
                        log.info(f"Found user-provided JSON data: {user_data}")
                        return user_data
            
            log.warning("No valid JSON data found in messages.json")
            return None
    except Exception as e:
        log.error(f"Failed to read or parse messages.json: {e}")
        return None

def apply_citizen_update(username: str, dry_run: bool = False) -> bool:
    """Apply the latest user-provided update to a citizen."""
    log.info(f"Starting update process for citizen {username} (dry_run: {dry_run})")
    
    # Get the latest user data
    user_data = get_latest_user_data()
    if not user_data:
        log.error("No user data found to apply")
        return False
    
    # Initialize Airtable
    tables = initialize_airtable()
    if not tables:
        log.error("Failed to initialize Airtable")
        return False
    
    # Get citizen info
    citizen_info = get_citizen_info(tables, username)
    if not citizen_info:
        log.error(f"Failed to get information for citizen {username}")
        return False
    
    # Extract data from user_data
    personality_text = user_data.get("Personality", "")
    core_personality_array = user_data.get("CorePersonality", [])
    family_motto = user_data.get("familyMotto", "")
    coat_of_arms = user_data.get("coatOfArms", "")
    image_prompt = user_data.get("imagePrompt", "")
    
    if dry_run:
        log.info(f"[DRY RUN] Would update citizen {username} with:")
        log.info(f"[DRY RUN] New Personality (textual): {personality_text}")
        log.info(f"[DRY RUN] New CorePersonality (array): {core_personality_array}")
        log.info(f"[DRY RUN] New family motto: {family_motto}")
        log.info(f"[DRY RUN] New coat of arms: {coat_of_arms}")
        log.info(f"[DRY RUN] New image prompt: {image_prompt}")
        return True
    
    # Generate new image
    image_url = None
    if image_prompt:
        image_url = generate_image(image_prompt, username)
        if not image_url:
            log.warning(f"Failed to generate image for citizen {username}")
    
    # Generate coat of arms image if needed
    coat_of_arms_url = None
    if coat_of_arms and not citizen_info["citizen"]['fields'].get('CoatOfArmsImageUrl'):
        coat_of_arms_url = generate_coat_of_arms_image(coat_of_arms, username)
        if not coat_of_arms_url:
            log.warning(f"Failed to generate coat of arms image for citizen {username}")
    
    # Update citizen record
    old_personality_text = citizen_info["citizen"]['fields'].get('Description', '')
    success = update_citizen_record(
        tables, 
        username, 
        personality_text, 
        core_personality_array, 
        family_motto, 
        coat_of_arms, 
        image_prompt, 
        image_url or "", 
        coat_of_arms_url
    )
    
    if not success:
        log.error(f"Failed to update citizen record for {username}")
        return False
    
    # Create notification
    create_notification(tables, username, old_personality_text, personality_text)
    
    log.info(f"Successfully updated citizen {username} with user-provided data")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply user-provided updates to a citizen.")
    parser.add_argument("--username", required=True, help="Username of the citizen to update")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    success = apply_citizen_update(args.username, args.dry_run)
    sys.exit(0 if success else 1)

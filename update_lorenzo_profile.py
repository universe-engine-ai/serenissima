#!/usr/bin/env python3
"""
Update Lorenzo Mocenigo's Profile

This script directly updates Lorenzo Mocenigo's (DogeLover88) profile with the
predefined personality, core personality traits, family motto, coat of arms,
and image prompt. It then generates a new image using Ideogram.

Usage:
  python update_lorenzo_profile.py [--dry-run]
"""

import os
import sys
import logging
import argparse
from typing import Dict, Optional
from dotenv import load_dotenv

# Import the necessary functions from updatecitizenDescriptionAndImage.py
from updatecitizenDescriptionAndImage import (
    initialize_airtable,
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
log = logging.getLogger("update_lorenzo_profile")

# Load environment variables
load_dotenv()

def update_lorenzo_profile(dry_run: bool = False) -> bool:
    """Update Lorenzo Mocenigo's profile with predefined values."""
    log.info(f"Starting update process for Lorenzo Mocenigo (DogeLover88) (dry_run: {dry_run})")
    
    # Initialize Airtable
    tables = initialize_airtable()
    if not tables:
        log.error("Failed to initialize Airtable")
        return False
    
    # Get Lorenzo's current record
    username = "DogeLover88"
    formula = f"{{Username}}='{username}'"
    citizens = tables['citizens'].all(formula=formula)
    
    if not citizens:
        log.error(f"Citizen not found: {username}")
        return False
    
    lorenzo = citizens[0]
    old_personality_text = lorenzo['fields'].get('Description', '')
    
    # Predefined profile data
    new_personality_text = "Lorenzo Mocenigo is a meticulous artisan whose hands have been shaped by years of working with molten glass, transforming raw materials into objects of beauty and utility. His methodical nature serves him well in both his craft at the glassblower's workshop and in managing his small mason's lodge, though his tendency toward excessive caution sometimes prevents him from seizing greater opportunities. Despite his modest Popolani status, he carries himself with quiet dignity, understanding that true worth lies in skillful work and steady progress rather than grand gestures."
    new_core_personality_array = ["Meticulous", "Overcautious", "Craft-mastery"]
    new_family_motto = "Per Arte et Labore - Through Skill and Labor"
    new_coat_of_arms = "A blue shield bearing a golden glass vessel in the center, flanked by crossed mason's tools (hammer and chisel) in silver. Above the vessel sits a small flame representing the furnace's fire. The shield is bordered with a simple rope pattern in brown, symbolizing the honest labor of craftsmen. A small fish at the base honors his humble cottage by the water."
    new_image_prompt = "Renaissance Venetian portrait of Lorenzo Mocenigo, a skilled Popolani craftsman in his thirties. He wears a simple but well-made brown doublet with rolled sleeves showing muscular forearms marked by small burns from glasswork. His weathered hands hold a delicate glass piece, demonstrating both strength and precision. His face shows concentration and quiet pride, with intelligent dark eyes that reflect firelight. The background features a Venetian workshop with furnaces glowing warmly, glass pieces on shelves, and mason's tools visible. Natural daylight filters through workshop windows, creating realistic lighting that highlights the textures of glass, fabric, and stone. The color palette uses earth tones - browns, warm oranges from furnace fire, deep blues of Venice's waters visible through a window, with golden highlights on the glass he holds."
    
    if dry_run:
        log.info(f"[DRY RUN] Would update Lorenzo Mocenigo (DogeLover88) with:")
        log.info(f"[DRY RUN] New Personality (textual): {new_personality_text}")
        log.info(f"[DRY RUN] New CorePersonality (array): {new_core_personality_array}")
        log.info(f"[DRY RUN] New family motto: {new_family_motto}")
        log.info(f"[DRY RUN] New coat of arms: {new_coat_of_arms}")
        log.info(f"[DRY RUN] New image prompt: {new_image_prompt}")
        return True
    
    # Generate new image
    image_url = generate_image(new_image_prompt, username)
    if not image_url:
        log.error(f"Failed to generate image for Lorenzo Mocenigo (DogeLover88)")
        # Continue anyway, as we can still update the description
    
    # Generate coat of arms image if Lorenzo doesn't already have one
    coat_of_arms_url = None
    if not lorenzo['fields'].get('CoatOfArmsImageUrl'):
        coat_of_arms_url = generate_coat_of_arms_image(new_coat_of_arms, username)
        if not coat_of_arms_url:
            log.warning(f"Failed to generate coat of arms image for Lorenzo Mocenigo (DogeLover88)")
    
    # Update Lorenzo's record
    success = update_citizen_record(
        tables, 
        username, 
        new_personality_text, 
        new_core_personality_array, 
        new_family_motto, 
        new_coat_of_arms, 
        new_image_prompt, 
        image_url or "", 
        coat_of_arms_url
    )
    
    if not success:
        log.error(f"Failed to update citizen record for Lorenzo Mocenigo (DogeLover88)")
        return False
    
    # Create notification
    create_notification(tables, username, old_personality_text, new_personality_text)
    
    log.info(f"Successfully updated profile for Lorenzo Mocenigo (DogeLover88)")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Lorenzo Mocenigo's profile with predefined values.")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    update_lorenzo_profile(args.dry_run)

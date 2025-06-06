#!/usr/bin/env python3
"""
Generate Citizen Image From Profile script for La Serenissima.

This script:
1. Takes a citizen username as input
2. Retrieves their profile data from Airtable
3. Uses their existing ImagePrompt to generate a new portrait using Ideogram
4. Updates their ImageUrl in Airtable
5. Optionally generates a new coat of arms image if CoatOfArms description exists

This script can be called after a citizen updates their profile through the ProfileEditor.
"""

import os
import sys
import logging
import argparse
import json
import requests
from typing import Dict, Optional
from pyairtable import Api, Table
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("generate_citizen_image_from_profile")

# Load environment variables
load_dotenv()

# Constants
CITIZENS_IMAGE_DIR = os.path.join(os.getcwd(), 'public', 'images', 'citizens')
COAT_OF_ARMS_DIR = os.path.join(os.getcwd(), 'public', 'coat-of-arms')

# Ensure the directories exist
os.makedirs(CITIZENS_IMAGE_DIR, exist_ok=True)
os.makedirs(COAT_OF_ARMS_DIR, exist_ok=True)

def initialize_airtable():
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID environment variables.")
        return None
    
    try:
        api = Api(api_key)
        base = api.base(base_id)
        # Return a dictionary of table objects using pyairtable
        return {
            'citizens': base.table('CITIZENS')
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        return None

def get_citizen_profile(tables, username: str) -> Optional[Dict]:
    """Get citizen profile data from Airtable."""
    log.info(f"Fetching profile for citizen: {username}")
    
    try:
        # Get citizen record
        formula = f"{{Username}}='{username}'"
        citizens = tables['citizens'].all(formula=formula)
        
        if not citizens:
            log.error(f"Citizen not found: {username}")
            return None
        
        citizen = citizens[0]
        log.info(f"Found citizen: {citizen['fields'].get('FirstName', '')} {citizen['fields'].get('LastName', '')}")
        return citizen
    except Exception as e:
        log.error(f"Error fetching citizen profile: {e}")
        return None

def generate_image(prompt: str, citizen_id: str) -> Optional[str]:
    """Generate image using Ideogram API."""
    log.info(f"Sending prompt to Ideogram API: {prompt[:100]}...")
    
    # Get Ideogram API key from environment
    ideogram_api_key = os.environ.get('IDEOGRAM_API_KEY')
    if not ideogram_api_key:
        log.error("IDEOGRAM_API_KEY environment variable is not set")
        return None
    
    try:
        # Enhance the prompt with additional styling guidance
        enhanced_prompt = f"{prompt} Renaissance portrait style with realistic details. 3/4 view portrait composition with dramatic lighting. Historically accurate Venetian setting and clothing details. Photorealistic quality, high detail."
        
        # Call the Ideogram API
        response = requests.post(
            "https://api.ideogram.ai/v1/ideogram-v3/generate",
            headers={
                "Api-Key": ideogram_api_key,
                "Content-Type": "application/json"
            },
            json={
                "prompt": enhanced_prompt,
                "style_type": "REALISTIC",
                "rendering_speed": "DEFAULT",
                "model":"V_3"
            }
        )
        
        if response.status_code != 200:
            log.error(f"Error from Ideogram API: {response.status_code} {response.text}")
            return None
        
        # Extract image URL from response
        result = response.json()
        image_url = result.get("data", [{}])[0].get("url", "")
        
        if not image_url:
            log.error("No image URL in response")
            return None
        
        # Download the image
        image_response = requests.get(image_url, stream=True)
        if not image_response.ok:
            log.error(f"Failed to download image: {image_response.status_code} {image_response.reason}")
            return None
        
        # Save the image to the public folder using the username directly
        image_path = os.path.join(CITIZENS_IMAGE_DIR, f"{citizen_id}.jpg")
        with open(image_path, 'wb') as f:
            for chunk in image_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log.info(f"Generated and saved image for citizen {citizen_id}")
        
        # Create the public URL path
        public_image_url = f"/images/citizens/{citizen_id}.jpg"
        
        return public_image_url
    except Exception as e:
        log.error(f"Error generating image for citizen {citizen_id}: {e}")
        return None

def generate_coat_of_arms_image(prompt: str, username: str) -> Optional[str]:
    """Generate coat of arms image using Ideogram API."""
    log.info(f"Generating coat of arms for {username}: {prompt[:100]}...")
    
    # Get Ideogram API key from environment
    ideogram_api_key = os.environ.get('IDEOGRAM_API_KEY')
    if not ideogram_api_key:
        log.error("IDEOGRAM_API_KEY environment variable is not set")
        return None
    
    # Enhance the prompt for better coat of arms generation
    enhanced_prompt = f"A heraldic coat of arms shield with the following description: {prompt}. Renaissance Venetian style, detailed, ornate, historically accurate, centered composition, on a transparent background."
    
    try:
        # Call the Ideogram API
        response = requests.post(
            "https://api.ideogram.ai/v1/ideogram-v3/generate",
            headers={
                "Api-Key": ideogram_api_key,
                "Content-Type": "application/json"
            },
            json={
                "prompt": enhanced_prompt,
                "style_type": "REALISTIC",
                "rendering_speed": "DEFAULT",
                "model":"V_3"
            }
        )
        
        if response.status_code != 200:
            log.error(f"Error from Ideogram API for coat of arms: {response.status_code} {response.text}")
            return None
        
        # Extract image URL from response
        result = response.json()
        image_url = result.get("data", [{}])[0].get("url", "")
        
        if not image_url:
            log.error("No coat of arms image URL in response")
            return None
        
        # Download the image
        image_response = requests.get(image_url, stream=True)
        if not image_response.ok:
            log.error(f"Failed to download coat of arms image: {image_response.status_code} {image_response.reason}")
            return None
        
        # Save the image to the coat of arms folder using the username
        image_path = os.path.join(COAT_OF_ARMS_DIR, f"{username}.png")
        with open(image_path, 'wb') as f:
            for chunk in image_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log.info(f"Generated and saved coat of arms for {username}")
        
        # Create the public URL path
        public_image_url = f"/coat-of-arms/{username}.png"
        
        return public_image_url
    except Exception as e:
        log.error(f"Error generating coat of arms for {username}: {e}")
        return None

def update_citizen_images(username: str, dry_run: bool = False):
    """Main function to update a citizen's portrait and coat of arms images."""
    log.info(f"Starting image generation process for citizen {username} (dry_run: {dry_run})")
    
    tables = initialize_airtable()
    if not tables:
        log.error("Failed to initialize Airtable")
        return False
    
    # Get citizen profile
    citizen = get_citizen_profile(tables, username)
    if not citizen:
        log.error(f"Failed to get profile for citizen {username}")
        return False
    
    # Check if we have an image prompt
    image_prompt = citizen['fields'].get('ImagePrompt')
    if not image_prompt:
        log.warning(f"No image prompt found for citizen {username}")
        return False
    
    if dry_run:
        log.info(f"[DRY RUN] Would generate image for {username} with prompt: {image_prompt[:100]}...")
        return True
    
    # Generate portrait image
    image_url = generate_image(image_prompt, username)
    
    # Generate coat of arms image if we have a description
    coat_of_arms_description = citizen['fields'].get('CoatOfArms')
    coat_of_arms_url = None
    if coat_of_arms_description:
        coat_of_arms_url = generate_coat_of_arms_image(coat_of_arms_description, username)
    
    # Update citizen record with new image URLs
    update_fields = {}
    if image_url:
        update_fields['ImageUrl'] = image_url
    if coat_of_arms_url:
        update_fields['CoatOfArmsImageUrl'] = coat_of_arms_url
    
    if update_fields:
        try:
            tables['citizens'].update(citizen['id'], update_fields)
            log.info(f"Updated citizen {username} with new image URLs")
            return True
        except Exception as e:
            log.error(f"Error updating citizen record: {e}")
            return False
    else:
        log.warning(f"No image URLs to update for citizen {username}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images for a citizen based on their profile data")
    parser.add_argument("username", help="Username of the citizen to update")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    success = update_citizen_images(args.username, args.dry_run)
    sys.exit(0 if success else 1)

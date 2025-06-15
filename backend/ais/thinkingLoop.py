#!/usr/bin/env python3
"""
thinkingLoop.py - A continuous thinking process for AI citizens

This script selects a random citizen with weighting based on social class:
- Artisti: 5x chance
- Nobili: 4x chance
- Cittadini: 3x chance
- Popolani: 2x chance
- Facchini: 1x chance

It then performs a thinking operation for the selected citizen.
The script is designed to be run continuously by the scheduler.
"""

import os
import sys
import time
import random
import traceback
import json
from datetime import datetime, timedelta
import pytz

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import necessary modules
from backend.engine.utils.activity_helpers import (
    LogColors, log_info, log_warning, log_error, log_header,
    VENICE_TIMEZONE, get_tables
)

# Social class weights for citizen selection
SOCIAL_CLASS_WEIGHTS = {
    'Artisti': 5,
    'Nobili': 4,
    'Cittadini': 3,
    'Popolani': 2,
    'Facchini': 1
}

def select_random_citizen(tables):
    """
    Select a random citizen with weighting based on social class.
    
    Args:
        tables: Dictionary of Airtable tables
        
    Returns:
        A citizen record or None if no citizens found
    """
    try:
        # Get all AI citizens
        citizens = tables['citizens'].all(formula="{IsAI}=1")
        
        if not citizens:
            log_warning("No AI citizens found in the database")
            return None
        
        # Group citizens by social class
        citizens_by_class = {}
        for citizen in citizens:
            social_class = citizen['fields'].get('SocialClass', 'Unknown')
            if social_class not in citizens_by_class:
                citizens_by_class[social_class] = []
            citizens_by_class[social_class].append(citizen)
        
        # Create weighted selection pool
        selection_pool = []
        for social_class, citizens_list in citizens_by_class.items():
            weight = SOCIAL_CLASS_WEIGHTS.get(social_class, 1)  # Default weight 1 for unknown classes
            selection_pool.extend([(citizen, weight) for citizen in citizens_list])
        
        # Calculate total weight
        total_weight = sum(weight for _, weight in selection_pool)
        
        # Select a random citizen based on weights
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for citizen, weight in selection_pool:
            current_weight += weight
            if random_value <= current_weight:
                username = citizen['fields'].get('Username', 'Unknown')
                social_class = citizen['fields'].get('SocialClass', 'Unknown')
                log_info(f"Selected citizen: {username} (Social Class: {social_class})")
                return citizen
        
        # Fallback in case of rounding errors
        if selection_pool:
            citizen, _ = selection_pool[-1]
            username = citizen['fields'].get('Username', 'Unknown')
            social_class = citizen['fields'].get('SocialClass', 'Unknown')
            log_info(f"Fallback selected citizen: {username} (Social Class: {social_class})")
            return citizen
        
        return None
    
    except Exception as e:
        log_error(f"Error selecting random citizen: {str(e)}")
        traceback.print_exc()
        return None

def perform_thinking(citizen, tables):
    """
    Perform a thinking operation for the selected citizen.
    This is a placeholder for future implementation of different thinking functions.
    
    Args:
        citizen: The citizen record
        tables: Dictionary of Airtable tables
    """
    try:
        username = citizen['fields'].get('Username', 'Unknown')
        log_info(f"Performing thinking for citizen: {username}")
        
        # TODO: Implement different thinking functions and select one randomly
        # For now, just log that we would be thinking
        log_info(f"Thinking process completed for {username}")
        
        # Update the LastActiveAt field to show the citizen has been processed
        now = datetime.now(VENICE_TIMEZONE).isoformat()
        tables['citizens'].update(citizen['id'], {
            'LastActiveAt': now
        })
        
        return True
    
    except Exception as e:
        log_error(f"Error during thinking process: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Main function to run the thinking loop"""
    log_header("Starting Thinking Loop", color_code=LogColors.HEADER)
    
    try:
        # Initialize tables
        tables = get_tables()
        
        # Main loop
        while True:
            try:
                # Select a random citizen
                citizen = select_random_citizen(tables)
                
                if citizen:
                    # Perform thinking for the selected citizen
                    perform_thinking(citizen, tables)
                
                # Sleep for a short time to avoid hammering the database
                time.sleep(5)
                
            except Exception as loop_error:
                log_error(f"Error in thinking loop: {str(loop_error)}")
                traceback.print_exc()
                time.sleep(30)  # Longer sleep on error
    
    except KeyboardInterrupt:
        log_info("Thinking loop interrupted by user")
    except Exception as e:
        log_error(f"Fatal error in thinking loop: {str(e)}")
        traceback.print_exc()
    
    log_header("Thinking Loop Terminated", color_code=LogColors.FAIL)

if __name__ == "__main__":
    main()

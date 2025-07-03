"""
Emergency fix for the hunger crisis in La Serenissima.
Allows citizens who haven't eaten in >24 hours to eat regardless of leisure time constraints.

Key Issues Identified:
1. Citizens can only eat during leisure time (3-6 hours per day depending on class)
2. Citizens are marked "hungry" after 12 hours but the real crisis is at 24+ hours
3. The tight leisure time windows prevent citizens from eating when they need to

Solution:
- Add emergency eating priority for citizens who haven't eaten in >24 hours
- These emergency eating activities bypass leisure time constraints
- Maintains normal eating patterns for non-emergency situations
"""

import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional

log = logging.getLogger(__name__)

def is_severely_hungry(citizen_record: Dict, now_utc_dt: datetime, hours_threshold: float = 24.0) -> bool:
    """
    Check if a citizen is severely hungry (hasn't eaten in more than hours_threshold).
    
    Args:
        citizen_record: The citizen's database record
        now_utc_dt: Current UTC datetime
        hours_threshold: Number of hours without eating to be considered severely hungry
    
    Returns:
        True if citizen hasn't eaten in more than hours_threshold hours
    """
    ate_at_str = citizen_record['fields'].get('AteAt')
    if not ate_at_str:
        return True  # No record of eating = severely hungry
    
    try:
        ate_at_dt = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
        if ate_at_dt.tzinfo is None:
            ate_at_dt = pytz.UTC.localize(ate_at_dt)
        
        hours_since_meal = (now_utc_dt - ate_at_dt).total_seconds() / 3600
        return hours_since_meal > hours_threshold
    
    except Exception as e:
        log.warning(f"Error parsing AteAt for citizen: {e}")
        return True  # If we can't parse, assume they're hungry


# Patch for needs.py handlers to check severe hunger
EMERGENCY_EATING_PATCH = '''
# Add this import at the top of needs.py:
from backend.arsenale.fix_hunger_crisis import is_severely_hungry

# Then modify each eating handler to check for severe hunger BEFORE leisure time check.
# For example, in _handle_eat_from_inventory:

def _handle_eat_from_inventory(...):
    """Prio 2: Handles eating from inventory if hungry and it's leisure time or EMERGENCY."""
    if not citizen_record['is_hungry']: return None
    
    # EMERGENCY: Allow eating if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions.{LogColors.ENDC}")
    
    # Rest of the function remains the same...
'''

def generate_patched_needs_handlers():
    """
    Generate the complete patched version of the eating handlers in needs.py
    that check for severe hunger before leisure time restrictions.
    """
    patches = {
        "_handle_eat_from_inventory": {
            "line_to_replace": "if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):",
            "replacement": """    # EMERGENCY: Allow eating if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions.{LogColors.ENDC}")"""
        },
        "_handle_eat_at_home_or_goto": {
            "line_to_replace": "if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):",
            "replacement": """    # EMERGENCY: Allow eating if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions.{LogColors.ENDC}")"""
        },
        "_handle_eat_at_tavern_or_goto": {
            "line_to_replace": "if not is_leisure_time_for_class(citizen_social_class, now_venice_dt): # Still check for leisure time",
            "replacement": """    # EMERGENCY: Allow eating if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions.{LogColors.ENDC}")"""
        },
        "_handle_shop_for_food_at_retail": {
            "line_to_replace": "if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):",
            "replacement": """    # EMERGENCY: Allow shopping if severely hungry (>24 hours without food)
    is_emergency = is_severely_hungry(citizen_record, now_utc_dt, hours_threshold=24.0)
    
    if not is_emergency and not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
        return None
    
    if is_emergency:
        log.warning(f"{LogColors.WARNING}[EMERGENCY] {citizen_name} hasn't eaten in >24 hours! Bypassing leisure time restrictions for food shopping.{LogColors.ENDC}")"""
        }
    }
    
    return patches


if __name__ == "__main__":
    print("Hunger Crisis Fix - Emergency Eating Outside Leisure Time")
    print("=" * 60)
    print("\nThis fix allows citizens who haven't eaten in >24 hours to eat")
    print("regardless of leisure time restrictions.")
    print("\nTo apply this fix, the eating handlers in needs.py need to be updated.")
    print("\nSee the EMERGENCY_EATING_PATCH variable for the required changes.")
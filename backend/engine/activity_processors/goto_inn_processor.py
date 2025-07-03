import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime # Added datetime

from backend.engine.utils.activity_helpers import (
    LogColors, 
    get_citizen_record, 
    get_building_record, 
    _get_building_position_coords,
    update_citizen_ducats, # Added for ducat transactions
    VENICE_TIMEZONE # Added for transaction timestamp
)

log = logging.getLogger(__name__)

INN_STAY_COSTS = {
    "Facchini": 40,
    "Popolani": 100,
    "Cittadini": 300,
    "Nobili": 800,
    "Forestieri": 150, # Forestieri might have a different rate than Popolani
    "Artisti": 120    # Artisti might also have a specific rate
}
DEFAULT_INN_STAY_COST = 100 # Fallback cost

def process(
    tables: Dict[str, Any], 
    activity_record: Dict[str, Any], 
    building_type_defs: Dict[str, Any], # Not used by this simple processor
    resource_defs: Dict[str, Any],       # Not used by this simple processor
    api_base_url: Optional[str] = None   # Added for signature consistency
) -> bool:
    """
    Processes a 'goto_inn' activity.
    Updates the citizen's position to the inn (ToBuilding).
    """
    activity_fields = activity_record.get('fields', {})
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    to_building_id = activity_fields.get('ToBuilding') # Custom BuildingId of the inn

    log.info(f"{LogColors.PROCESS}Processing 'goto_inn' activity {activity_guid} for citizen {citizen_username} to inn {to_building_id}.{LogColors.ENDC}")

    if not citizen_username or not to_building_id:
        log.error(f"{LogColors.FAIL}Missing Citizen or ToBuilding for 'goto_inn' activity {activity_guid}.{LogColors.ENDC}")
        return False

    citizen_airtable_record = get_citizen_record(tables, citizen_username)
    inn_building_record = get_building_record(tables, to_building_id)

    if not citizen_airtable_record:
        log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found for 'goto_inn' activity {activity_guid}.{LogColors.ENDC}")
        return False
    
    if not inn_building_record:
        log.error(f"{LogColors.FAIL}Inn building {to_building_id} not found for 'goto_inn' activity {activity_guid}.{LogColors.ENDC}")
        return False

    # Determine cost of stay
    citizen_social_class = citizen_airtable_record['fields'].get('SocialClass', 'Popolani')
    cost_of_stay = INN_STAY_COSTS.get(citizen_social_class, DEFAULT_INN_STAY_COST)
    
    current_citizen_ducats = float(citizen_airtable_record['fields'].get('Ducats', 0.0))

    if current_citizen_ducats < cost_of_stay:
        log.warning(f"{LogColors.WARNING}Citizen {citizen_username} cannot afford stay at inn {to_building_id}. Needs {cost_of_stay:.2f}, has {current_citizen_ducats:.2f}. Activity failed.{LogColors.ENDC}")
        return False

    # Process payment
    inn_operator_username = inn_building_record['fields'].get('RunBy') or inn_building_record['fields'].get('Owner')
    
    # Deduct from citizen
    if not update_citizen_ducats(tables, citizen_airtable_record['id'], -cost_of_stay, f"Paid for stay at inn {to_building_id}", "lodging_expense", to_building_id):
        log.error(f"{LogColors.FAIL}Failed to deduct ducats from {citizen_username} for inn stay. Activity failed.{LogColors.ENDC}")
        return False
    
    # Credit inn operator
    if inn_operator_username:
        inn_operator_record = get_citizen_record(tables, inn_operator_username)
        if inn_operator_record:
            if not update_citizen_ducats(tables, inn_operator_record['id'], cost_of_stay, f"Income from {citizen_username}'s stay at inn {to_building_id}", "lodging_income", to_building_id):
                log.warning(f"{LogColors.WARNING}Failed to credit ducats to inn operator {inn_operator_username}. Payment was taken from {citizen_username}.{LogColors.ENDC}")
            # Transaction record is created by update_citizen_ducats if successful
        else:
            log.warning(f"{LogColors.WARNING}Inn operator {inn_operator_username} not found. Ducats for stay at {to_building_id} not credited to anyone (but deducted from {citizen_username}).{LogColors.ENDC}")
    else:
        log.warning(f"{LogColors.WARNING}Inn {to_building_id} has no operator (RunBy/Owner). Ducats for stay not credited (but deducted from {citizen_username}).{LogColors.ENDC}")

    # Update citizen's position
    inn_position_coords = _get_building_position_coords(inn_building_record)
    if not inn_position_coords:
        log.error(f"{LogColors.FAIL}Inn building {to_building_id} has no valid position. Cannot update citizen position for activity {activity_guid}.{LogColors.ENDC}")
        # Note: Payment has already been processed. This is a partial failure.
        # For now, we'll return False, but the ducat change persists.
        return False 

    try:
        new_position_str = json.dumps(inn_position_coords)
        tables['citizens'].update(citizen_airtable_record['id'], {'Position': new_position_str})
        log.info(f"{LogColors.OKGREEN}Updated citizen {citizen_username} position to inn {to_building_id} (Coords: {new_position_str}) after 'goto_inn' activity {activity_guid}.{LogColors.ENDC}")
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error updating citizen {citizen_username} position for 'goto_inn' activity {activity_guid}: {e}{LogColors.ENDC}")
        # Payment processed, position update failed.
        return False

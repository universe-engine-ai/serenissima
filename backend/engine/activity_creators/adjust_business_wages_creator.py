import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List # Added List
from backend.engine.utils.activity_helpers import (
    _escape_airtable_value,
    VENICE_TIMEZONE,
    find_path_between_buildings,
    get_building_record,
    get_citizen_home,
    clean_thought_content, # Import the cleaning function
    find_path_between_buildings_or_coords, # Import missing function
    create_activity_record # Import the helper function
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    activity_type_unused: str, # This is the 'activity_type' argument from the dispatcher
    details: Dict[str, Any],   # This is the 'activity_parameters' from the dispatcher
    now_venice_dt: datetime,
    now_utc_dt: datetime,
    transport_api_url: str, # Will be available but might not be used directly by this creator
    api_base_url: str       # Will be passed to find_path_between_buildings
) -> Optional[List[Dict[str, Any]]]:
    """
    Create the complete adjust_business_wages activity chain:
    1. A goto_location activity for travel to the business
    2. An update_wage_ledger activity to register the change
    
    This approach creates the complete activity chain upfront.
    """
    # Extract required parameters
    business_building_id = details.get('businessBuildingId')
    new_wage_amount = details.get('newWageAmount')
    strategy = details.get('strategy', 'standard')  # Optional strategy parameter
    
    # Validate required parameters
    if not (business_building_id and new_wage_amount is not None):
        log.error(f"Missing required details for adjust_business_wages: businessBuildingId or newWageAmount")
        return False

    citizen = citizen_record['fields'].get('Username')
    ts = int(now_venice_dt.timestamp()) # Use passed now_venice_dt
    
    # Get current citizen position to determine path
    citizen_position_str = citizen_record['fields'].get('Position')
    current_position = None
    if citizen_position_str:
        try:
            current_position = json.loads(citizen_position_str)
        except json.JSONDecodeError:
            log.error(f"Could not parse citizen position: {citizen_position_str}")
            return False
    
    # Verify the citizen operates the business
    building_formula = f"{{BuildingId}}='{_escape_airtable_value(business_building_id)}'"
    building_records = tables['buildings'].all(formula=building_formula, max_records=1)
    
    if not building_records:
        log.error(f"Building {business_building_id} not found")
        return False
    
    building_record = building_records[0]
    building_operator = building_record['fields'].get('RunBy')
    building_category = building_record['fields'].get('Category')
    
    if building_operator != citizen:
        log.error(f"Citizen {citizen} does not operate building {business_building_id}")
        return False
    
    if building_category != 'business':
        log.error(f"Building {business_building_id} is not a business (category: {building_category})")
        return False
    
    # Get building record for path calculation
    destination_building_record = building_record
    
    # Calculate path to destination
    # Use find_path_between_buildings_or_coords as current_position is coordinates
    path_data = find_path_between_buildings_or_coords(
        tables=tables,
        start_location=current_position, 
        end_location=destination_building_record, # Pass the full record
        api_base_url=api_base_url,
        transport_api_url=transport_api_url # Pass the transport_api_url
    )
    if not path_data or not path_data.get('path'):
        log.error(f"Could not find path to {business_building_id}")
        return False
    
    # Create activity IDs
    goto_activity_id = f"goto_location_for_wage_adjustment_{_escape_airtable_value(business_building_id)}_{citizen}_{ts}"
    adjustment_activity_id = f"update_wage_ledger_{_escape_airtable_value(business_building_id)}_{citizen}_{ts}"
    
    # Use passed now_utc_dt
    travel_start_date = now_utc_dt.isoformat()
    
    # Calculate travel end date based on path duration
    duration_seconds = path_data.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min if not specified
    travel_end_date = (now_utc_dt + timedelta(seconds=duration_seconds)).isoformat()
    
    # Calculate adjustment activity times (15 minutes after arrival)
    adjustment_start_date = travel_end_date  # Start immediately after arrival
    adjustment_end_date = (datetime.fromisoformat(travel_end_date.replace('Z', '+00:00')) + timedelta(minutes=15)).isoformat()
    
    # Store adjustment details for the processor to use
    common_details_for_notes = {
        "businessBuildingId": business_building_id,
        "newWageAmount": new_wage_amount,
        "strategy": strategy,
        "activityType": "adjust_business_wages" # Overall endeavor context
    }
    
    # 1. Create goto_location activity
    goto_title = f"Traveling to adjust wages for business {business_building_id}"
    goto_description = f"Traveling to {destination_building_record['fields'].get('Name', business_building_id)} to adjust the wages to {new_wage_amount} Ducats"
    goto_simple_notes = f"First step of adjust_business_wages process. Will be followed by update_wage_ledger activity."
    
    goto_details_json_for_notes = json.dumps({
        **common_details_for_notes,
        "nextStep": "update_wage_ledger" # Specific to this goto step
    })

    activity1_created = create_activity_record(
        tables=tables,
        citizen_username=citizen,
        activity_type="goto_location",
        start_date_iso=travel_start_date,
        end_date_iso=travel_end_date,
        to_building_id=business_building_id,
        path_json=json.dumps(path_data.get('path', [])),
        details_json=goto_details_json_for_notes, # Structured data
        notes=goto_simple_notes, # Simple text notes (will be used if details_json is None, or combined by helper if logic changes)
        title=goto_title,
        description=goto_description,
        priority_override=20
    )
    
    if not activity1_created:
        log.error(f"Failed to create goto_location activity for adjust_business_wages chain for {citizen}.")
        return None

    # 2. Create update_wage_ledger activity (to be executed after arrival)
    adj_title = f"Adjusting wages for business {business_building_id}"
    adj_description = f"Updating the wage ledger to adjust wages to {new_wage_amount} Ducats"
    adj_simple_notes = f"Second step of adjust_business_wages process. Will update business wages."

    # details_json for update_wage_ledger is the common_details_for_notes
    adj_details_json_for_notes = json.dumps(common_details_for_notes)

    activity2_created = create_activity_record(
        tables=tables,
        citizen_username=citizen,
        activity_type="update_wage_ledger",
        start_date_iso=adjustment_start_date,
        end_date_iso=adjustment_end_date,
        from_building_id=business_building_id,
        to_building_id=business_building_id,
        details_json=adj_details_json_for_notes, # Structured data
        notes=adj_simple_notes, # Simple text notes
        title=adj_title,
        description=adj_description,
        priority_override=20
    )

    if not activity2_created:
        log.error(f"Failed to create update_wage_ledger activity for adjust_business_wages chain for {citizen}.")
        # Consider if we need to delete activity1_created here if the chain is broken.
        # For now, returning None indicates the chain wasn't fully created.
        return None # Changed from False
        
    log.info(f"Created complete adjust_business_wages activity chain for citizen {citizen}:")
    log.info(f"  1. goto_location activity {activity1_created.get('fields',{}).get('ActivityId')}")
    log.info(f"  2. update_wage_ledger activity {activity2_created.get('fields',{}).get('ActivityId')}")
    
    # Return the fields of the first activity in the chain, wrapped in a list
    if activity1_created and 'fields' in activity1_created:
        return [activity1_created['fields']] # Changed from True
    else:
        # This case should ideally not be reached if activity1_created was validated
        log.error(f"activity1_created is not a valid record for adjust_business_wages chain for {citizen}.")
        return None # Changed from True

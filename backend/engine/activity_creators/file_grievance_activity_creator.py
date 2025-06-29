import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any

from backend.engine.utils.activity_helpers import (
    LogColors,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser,
    get_citizen_record,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters
)
from backend.engine.activity_creators.goto_location_activity_creator import (
    try_create
)

log = logging.getLogger(__name__)

# Constants
ACTIVITY_KEY = "file_grievance"
ACTIVITY_DURATION_MINUTES = 30
FILING_FEE = 50  # ducats
WEEKLY_LIMIT = 1  # Maximum grievances per citizen per week


def try_create_file_grievance_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    now_venice_dt: datetime,
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str,
    start_time_utc_iso: Optional[str] = None,
    grievance_data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a file_grievance activity for a citizen at the Doge's Palace.
    
    Citizens can formally file grievances about economic, social, criminal, or infrastructure issues.
    This is the foundation of the democratic system in La Serenissima.
    """
    
    # Extract required data
    citizen_username = citizen_record.get('Username')
    citizen_name = citizen_record.get('Name', citizen_username)
    citizen_wealth = citizen_record.get('Wealth', 0)
    
    # Check if citizen has enough wealth for filing fee
    if citizen_wealth < FILING_FEE:
        log.info(f"{LogColors.WARNING}{citizen_name} cannot afford grievance filing fee of {FILING_FEE} ducats{LogColors.ENDC}")
        return None
    
    # Find the Doge's Palace
    doges_palace = None
    buildings_table = tables['BUILDINGS']
    for building in buildings_table.all():
        if building['fields'].get('BuildingType') == 'doges_palace':
            doges_palace = building['fields']
            break
    
    if not doges_palace:
        log.error(f"{LogColors.FAIL}No Doge's Palace found for filing grievances{LogColors.ENDC}")
        return None
    
    palace_id = doges_palace.get('BuildingId')
    palace_position = _get_building_position_coords(doges_palace)
    
    # Check if citizen needs to travel to the palace
    needs_travel = False
    if citizen_position and palace_position:
        distance = _calculate_distance_meters(
            citizen_position.get('lat'), citizen_position.get('lng'),
            palace_position.get('lat'), palace_position.get('lng')
        )
        if distance > 50:  # More than 50 meters away
            needs_travel = True
    
    # Handle start time
    if start_time_utc_iso:
        start_dt = dateutil_parser.isoparse(start_time_utc_iso.replace("Z", "+00:00"))
        if start_dt.tzinfo is None:
            start_dt = pytz.utc.localize(start_dt)
    else:
        start_dt = now_utc_dt
    
    # If citizen needs to travel, create goto activity first
    if needs_travel:
        goto_activity = try_create(
            tables=tables,
            citizen_record=citizen_record,
            citizen_position=citizen_position,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url,
            start_time_utc_iso=start_time_utc_iso,
            goto_building_id=palace_id
        )
        
        if goto_activity:
            # Schedule grievance filing after arrival
            goto_end_time = goto_activity['fields'].get('EndDateFull')
            return try_create_file_grievance_activity(
                tables=tables,
                citizen_record=citizen_record,
                citizen_position=palace_position,  # Will be at palace after goto
                resource_defs=resource_defs,
                building_type_defs=building_type_defs,
                now_venice_dt=now_venice_dt,
                now_utc_dt=now_utc_dt,
                transport_api_url=transport_api_url,
                api_base_url=api_base_url,
                start_time_utc_iso=goto_end_time,
                grievance_data=grievance_data
            )
        else:
            log.error(f"{LogColors.FAIL}Failed to create goto activity for grievance filing{LogColors.ENDC}")
            return None
    
    # Calculate end time
    end_dt = start_dt + timedelta(minutes=ACTIVITY_DURATION_MINUTES)
    
    # Convert to ISO format
    start_time_iso = start_dt.isoformat()
    end_time_iso = end_dt.isoformat()
    
    # Prepare grievance details
    if not grievance_data:
        # Default grievance categories based on citizen's situation
        grievance_data = {
            "category": "economic",  # Default category
            "title": "Economic Hardship",
            "description": "The burden of taxes and fees grows too heavy for honest citizens."
        }
    
    # Create activity details
    activity_details = {
        "filing_fee": FILING_FEE,
        "grievance_category": grievance_data.get("category", "economic"),
        "grievance_title": grievance_data.get("title", "Untitled Grievance"),
        "grievance_description": grievance_data.get("description", "No description provided")
    }
    
    # Create the activity record
    try:
        activity = create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type=ACTIVITY_KEY,
            start_date_iso=start_time_iso,
            end_date_iso=end_time_iso,
            from_building_id=palace_id,
            to_building_id=palace_id,
            title=f"Filing Grievance: {activity_details['grievance_title']}",
            description=f"{citizen_name} files a formal grievance at the Doge's Palace regarding {activity_details['grievance_category']} matters",
            thought=f"I must make my voice heard. The {activity_details['grievance_category']} situation has become unbearable. Perhaps if I file this grievance, something might change.",
            details_json=json.dumps(activity_details),
            priority_override=55  # Higher priority than routine activities
        )
        
        if activity:
            log.info(f"{LogColors.OKGREEN}{citizen_name} files grievance about {activity_details['grievance_category']} at Doge's Palace{LogColors.ENDC}")
            return activity
        else:
            log.error(f"{LogColors.FAIL}Failed to create file_grievance activity for {citizen_name}{LogColors.ENDC}")
            return None
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error creating file_grievance activity: {e}{LogColors.ENDC}")
        return None
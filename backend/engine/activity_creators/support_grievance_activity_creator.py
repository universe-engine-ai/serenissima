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
ACTIVITY_KEY = "support_grievance"
ACTIVITY_DURATION_MINUTES = 10
SUPPORT_FEE = 10  # ducats - smaller fee to encourage participation


def try_create_support_grievance_activity(
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
    grievance_id: Optional[str] = None,
    support_amount: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a support_grievance activity for a citizen at the Doge's Palace.
    
    Citizens can support existing grievances by adding their voice (and economic weight).
    This builds political coalitions and shows which issues have broad support.
    """
    
    # Extract required data
    citizen_username = citizen_record.get('Username')
    citizen_name = citizen_record.get('Name', citizen_username)
    citizen_wealth = citizen_record.get('Wealth', 0)
    citizen_social_class = citizen_record.get('SocialClass', 'Popolani')
    
    # Determine support amount if not specified
    if support_amount is None:
        support_amount = SUPPORT_FEE
    
    # Check if citizen has enough wealth for support fee
    if citizen_wealth < support_amount:
        log.info(f"{LogColors.WARNING}{citizen_name} cannot afford support fee of {support_amount} ducats{LogColors.ENDC}")
        return None
    
    # Validate grievance exists (in real implementation, would check GRIEVANCES table)
    if not grievance_id:
        log.error(f"{LogColors.FAIL}No grievance_id specified for support activity{LogColors.ENDC}")
        return None
    
    # Find the Doge's Palace
    doges_palace = None
    buildings_table = tables['BUILDINGS']
    for building in buildings_table.all():
        if building['fields'].get('BuildingType') == 'doges_palace':
            doges_palace = building['fields']
            break
    
    if not doges_palace:
        log.error(f"{LogColors.FAIL}No Doge's Palace found for supporting grievances{LogColors.ENDC}")
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
            # Schedule support activity after arrival
            goto_end_time = goto_activity['fields'].get('EndDateFull')
            return try_create_support_grievance_activity(
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
                grievance_id=grievance_id,
                support_amount=support_amount
            )
        else:
            log.error(f"{LogColors.FAIL}Failed to create goto activity for grievance support{LogColors.ENDC}")
            return None
    
    # Calculate end time
    end_dt = start_dt + timedelta(minutes=ACTIVITY_DURATION_MINUTES)
    
    # Convert to ISO format
    start_time_iso = start_dt.isoformat()
    end_time_iso = end_dt.isoformat()
    
    # Create activity details
    activity_details = {
        "grievance_id": grievance_id,
        "support_amount": support_amount,
        "supporter_class": citizen_social_class,
        "supporter_wealth": citizen_wealth
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
            title=f"Supporting Grievance #{grievance_id}",
            description=f"{citizen_name} adds their support to grievance #{grievance_id} at the Doge's Palace",
            thought=f"This grievance speaks to my own struggles. By adding my voice and {support_amount} ducats, perhaps together we can make a difference.",
            details_json=json.dumps(activity_details),
            priority_override=45  # Lower priority than filing, but still important
        )
        
        if activity:
            log.info(f"{LogColors.OKGREEN}{citizen_name} supports grievance #{grievance_id} with {support_amount} ducats{LogColors.ENDC}")
            return activity
        else:
            log.error(f"{LogColors.FAIL}Failed to create support_grievance activity for {citizen_name}{LogColors.ENDC}")
            return None
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error creating support_grievance activity: {e}{LogColors.ENDC}")
        return None
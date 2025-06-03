import logging
import json
import datetime
import uuid
from typing import Dict, Optional, Any, List
from pyairtable import Table

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Table],
    citizen_custom_id: str,
    citizen_username: str,
    citizen_airtable_id: str,
    target_building_id: str,
    path_data: Dict[str, Any],
    current_time_utc: datetime.datetime,
    land_id: Optional[str] = None,
    bid_amount: Optional[float] = None,
    details_payload: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Creates a bid_on_land activity for a citizen.
    
    Args:
        tables: Dictionary of Airtable tables
        citizen_custom_id: Citizen's custom ID
        citizen_username: Citizen's username
        citizen_airtable_id: Citizen's Airtable record ID
        target_building_id: ID of the building where the bid will be placed (town hall or courthouse)
        path_data: Path data for travel to the target building
        current_time_utc: Current UTC time
        land_id: ID of the land being bid on (optional, can be in details_payload)
        bid_amount: Amount of the bid (optional, can be in details_payload)
        details_payload: Additional details for the activity
        
    Returns:
        bool: True if the activity was created successfully, False otherwise
    """
    try:
        # Generate a unique activity ID
        activity_id = f"bid_on_land_{citizen_custom_id}_{uuid.uuid4()}"
        
        # Calculate travel time based on path data
        path_points = path_data.get('path', [])
        travel_time_minutes = path_data.get('travelTimeMinutes', 30)  # Default to 30 minutes if not provided
        
        # Calculate start and end times
        start_time = current_time_utc
        travel_end_time = start_time + datetime.timedelta(minutes=travel_time_minutes)
        
        # Add 15 minutes for the bidding process itself
        bidding_time_minutes = 15
        end_time = travel_end_time + datetime.timedelta(minutes=bidding_time_minutes)
        
        # Combine details from parameters and payload
        activity_details = details_payload or {}
        if land_id:
            activity_details['landId'] = land_id
        if bid_amount:
            activity_details['bidAmount'] = bid_amount
            
        # Create the activity record
        activity_record = {
            'ActivityId': activity_id,
            'Type': 'bid_on_land',
            'Citizen': citizen_username,
            'FromBuilding': None,  # Will be set based on citizen's current position
            'ToBuilding': target_building_id,
            'Path': json.dumps(path_points) if path_points else None,
            'Status': 'created',
            'CreatedAt': current_time_utc.isoformat(),
            'StartDate': start_time.isoformat(),
            'EndDate': end_time.isoformat(),
            'Title': f"Bidding on Land",
            'Description': f"Traveling to {target_building_id} to place a bid on land",
            'Notes': json.dumps(activity_details) if activity_details else None,
            'Priority': 1  # High priority
        }
        
        # Create the activity in Airtable
        tables['activities'].create(activity_record)
        
        log.info(f"Created bid_on_land activity {activity_id} for citizen {citizen_username}")
        return True
        
    except Exception as e:
        log.error(f"Error creating bid_on_land activity for citizen {citizen_username}: {e}")
        return False

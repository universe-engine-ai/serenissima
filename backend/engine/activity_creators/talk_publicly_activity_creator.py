import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from backend.engine.utils.activity_helpers import (
    _escape_airtable_value,
    VENICE_TIMEZONE,
    LogColors,
    get_building_record,
    get_citizen_record
)

log = logging.getLogger(__name__)

# Define allowed building types for public speaking
ALLOWED_BUILDING_TYPES = [
    "inn", "piazza", "palazzo", "merchant_s_house",
    "church", "library", "market", "arsenal",
    "great_palazzo", "grand_piazza", "townhall", 
    "guild_hall", "public_forum", "assembly_hall"
]

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    details: Dict[str, Any],
    api_base_url: str,
    transport_api_url: str
) -> Optional[Dict]:
    """
    Create a talk_publicly activity for making public announcements in buildings.
    
    Parameters:
    - message: The content of the public announcement
    - messageType: Type of message (announcement, proposal, debate, poetry, sermon, rallying_cry)
    - targetAudience: Optional specific audience filter
    """
    # Extract parameters
    message = details.get('message', '').strip()
    message_type = details.get('messageType', 'announcement')
    target_audience = details.get('targetAudience')
    
    # Validate message
    if not message:
        log.error("No message provided for talk_publicly activity")
        return None
    
    if len(message) < 10:
        log.error("Message too short for public announcement (min 10 characters)")
        return None
    
    if len(message) > 1000:
        log.error("Message too long for public announcement (max 1000 characters)")
        return None
    
    # Get citizen information
    citizen = citizen_record['fields']
    citizen_username = citizen.get('Username')
    citizen_position_str = citizen.get('Position')
    
    if not citizen_position_str:
        log.error(f"Citizen {citizen_username} has no position")
        return None
    
    try:
        citizen_position = json.loads(citizen_position_str)
    except json.JSONDecodeError:
        log.error(f"Could not parse citizen position: {citizen_position_str}")
        return None
    
    # Check if citizen is in a building by looking for buildings at the same position
    building_formula = f"{{Position}}='{_escape_airtable_value(citizen_position_str)}'"
    try:
        buildings_at_position = tables['buildings'].all(formula=building_formula, max_records=1)
        if not buildings_at_position:
            log.error(f"Citizen {citizen_username} must be in a building to speak publicly")
            return None
        
        current_building = buildings_at_position[0]
        building_fields = current_building['fields']
        building_type = building_fields.get('Type')
        building_id = building_fields.get('BuildingId')
        building_name = building_fields.get('Name', building_type)
    except Exception as e:
        log.error(f"Error finding building at position: {e}")
        return None
    
    # Check if building allows public speaking
    if building_type not in ALLOWED_BUILDING_TYPES:
        log.error(f"Public speaking not allowed in {building_type}")
        return None
    
    # Check audience (need at least 2 other people present)
    citizens_formula = f"AND({{Position}}='{_escape_airtable_value(citizen_position_str)}', {{Username}}!='{_escape_airtable_value(citizen_username)}')"
    try:
        audience = tables['citizens'].all(formula=citizens_formula)
        
        if len(audience) < 2:
            log.error(f"Not enough audience at {building_name} (need at least 2 other people)")
            return None
    except Exception as e:
        log.error(f"Error checking audience: {e}")
        return None
    
    # Check cooldown (5 minutes between public speeches)
    try:
        recent_activities = tables['activities'].all(
            formula=f"AND({{Citizen}}='{citizen_username}', {{Type}}='talk_publicly', {{Status}}='processed')"
        )
        
        if recent_activities:
            # Sort by EndDate to get the most recent
            recent_activities.sort(key=lambda a: a['fields'].get('EndDate', ''), reverse=True)
            last_speech = recent_activities[0]
            last_speech_time = datetime.fromisoformat(last_speech['fields']['EndDate'].replace('Z', '+00:00'))
            time_since = (datetime.now(timezone.utc) - last_speech_time).total_seconds()
            
            if time_since < 300:  # 5 minutes = 300 seconds
                remaining = int(300 - time_since)
                log.error(f"Citizen {citizen_username} must wait {remaining} seconds before speaking publicly again")
                return None
    except Exception as e:
        log.warning(f"Could not check cooldown: {e}")
        # Continue anyway
    
    # Create activity
    ts = int(datetime.now(VENICE_TIMEZONE).timestamp())
    activity_id = f"talk_publicly_{citizen_username}_{ts}"
    
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc.isoformat()
    end_date = (now_utc + timedelta(minutes=10)).isoformat()  # 10 minute duration
    
    # Prepare activity data
    activity_data = {
        "message": message,
        "messageType": message_type,
        "buildingId": building_id,
        "buildingType": building_type,
        "audienceCount": len(audience),
        "audienceUsernames": [a['fields'].get('Username') for a in audience],
        "veniceTime": datetime.now(VENICE_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if target_audience:
        activity_data["targetAudience"] = target_audience
    
    # Determine title based on message type
    titles = {
        "announcement": f"Making an announcement at {building_name}",
        "proposal": f"Presenting a proposal at {building_name}",
        "debate": f"Starting a debate at {building_name}",
        "poetry": f"Reciting poetry at {building_name}",
        "sermon": f"Giving a sermon at {building_name}",
        "rallying_cry": f"Rallying citizens at {building_name}"
    }
    
    title = titles.get(message_type, f"Speaking publicly at {building_name}")
    
    # Create activity payload
    payload = {
        "ActivityId": activity_id,
        "Type": "talk_publicly",
        "Citizen": citizen_username,
        "FromBuilding": building_id,
        "ToBuilding": building_id,  # Activity happens in same building
        "Status": "created",
        "Title": title,
        "Description": f"Addressing {len(audience)} citizens with a {message_type}",
        "Notes": json.dumps(activity_data),
        "CreatedAt": start_date,
        "StartDate": start_date,
        "EndDate": end_date,
        "Priority": 25  # Medium-high priority for social activities
    }
    
    try:
        activity_record = tables["activities"].create(payload)
        log.info(f"Created talk_publicly activity {activity_id} for {citizen_username} at {building_name}")
        log.info(f"Message type: {message_type}, Audience: {len(audience)} citizens")
        return activity_record
    except Exception as e:
        log.error(f"Failed to create talk_publicly activity: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None
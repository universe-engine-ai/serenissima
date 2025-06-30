import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from pyairtable import Table

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    LogColors,
    _escape_airtable_value,
    get_building_record,
    clean_thought_content
)

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Table],
    activity_record: Dict,
    citizen_id: str,
    current_time_utc: datetime
) -> Dict[str, Any]:
    """
    Process a talk_publicly activity to create a public message in a building.
    
    This creates a message record where the Receiver is the BuildingId,
    allowing all occupants to see and potentially respond to the message.
    """
    activity_fields = activity_record['fields']
    activity_id = activity_fields.get('ActivityId')
    citizen_username = activity_fields.get('Citizen')
    
    try:
        # Extract activity data from Notes
        notes = activity_fields.get('Notes', '{}')
        if isinstance(notes, str):
            activity_data = json.loads(notes)
        else:
            activity_data = notes
        
        message_content = activity_data.get('message')
        message_type = activity_data.get('messageType', 'announcement')
        building_id = activity_data.get('buildingId')
        audience_count = activity_data.get('audienceCount', 0)
        audience_usernames = activity_data.get('audienceUsernames', [])
        venice_time = activity_data.get('veniceTime')
        
        if not message_content or not building_id:
            log.error(f"Missing required data for talk_publicly: message or buildingId")
            return {
                "success": False,
                "error": "Missing required message or building information"
            }
        
        # Get citizen record for speaker info
        citizen_record = None
        try:
            citizen_records = tables['citizens'].all(formula=f"{{Username}}='{citizen_username}'")
            if citizen_records:
                citizen_record = citizen_records[0]
        except Exception as e:
            log.error(f"Could not find citizen record: {e}")
        
        if not citizen_record:
            return {
                "success": False,
                "error": f"Citizen {citizen_username} not found"
            }
        
        citizen_fields = citizen_record['fields']
        speaker_name = f"{citizen_fields.get('FirstName', '')} {citizen_fields.get('LastName', '')}".strip()
        if not speaker_name:
            speaker_name = citizen_username
        
        # Create message record with BuildingId as Receiver
        message_id = f"public_msg_{citizen_username}_{building_id}_{int(current_time_utc.timestamp())}"
        
        # Format message with speaker attribution
        formatted_content = f"[{message_type.upper()}] {message_content}"
        
        # Prepare message data
        message_payload = {
            "MessageId": message_id,
            "Sender": citizen_username,
            "Receiver": building_id,  # Building ID as receiver for public messages
            "Content": formatted_content,
            "Type": f"public_{message_type}",  # Prefix with public_ to distinguish
            "CreatedAt": current_time_utc.isoformat(),
            "Notes": json.dumps({
                "buildingId": building_id,
                "audienceCount": audience_count,
                "speakerName": speaker_name,
                "speakerClass": citizen_fields.get('SocialClass', 'Unknown'),
                "veniceTime": venice_time,
                "messageType": message_type
            })
        }
        
        # Create the message
        try:
            message_record = tables['messages'].create(message_payload)
            log.info(f"Created public message {message_id} in building {building_id}")
        except Exception as e:
            log.error(f"Failed to create public message: {e}")
            return {
                "success": False,
                "error": f"Failed to create message: {str(e)}"
            }
        
        # Create notifications for audience members
        notification_count = 0
        for audience_username in audience_usernames:
            try:
                notification_payload = {
                    "Citizen": audience_username,
                    "Type": "public_speech",
                    "Content": f"{speaker_name} speaks publicly: {message_content[:100]}...",
                    "Details": json.dumps({
                        "messageId": message_id,
                        "speaker": citizen_username,
                        "buildingId": building_id,
                        "messageType": message_type
                    }),
                    "Asset": message_id,
                    "AssetType": "message",
                    "Status": "unread",
                    "CreatedAt": current_time_utc.isoformat()
                }
                
                tables['notifications'].create(notification_payload)
                notification_count += 1
            except Exception as e:
                log.warning(f"Failed to create notification for {audience_username}: {e}")
        
        # Calculate influence gain based on audience and message type
        base_influence = audience_count * 2
        
        # Message type multipliers
        influence_multipliers = {
            "announcement": 1.0,
            "proposal": 1.2,
            "debate": 1.3,
            "poetry": 1.1,
            "sermon": 1.2,
            "rallying_cry": 1.5
        }
        
        multiplier = influence_multipliers.get(message_type, 1.0)
        
        # Social class bonus
        social_class = citizen_fields.get('SocialClass', 'Popolani')
        if social_class in ['Nobili', 'Cittadini']:
            multiplier *= 1.2
        
        influence_gain = int(base_influence * multiplier)
        
        # Update citizen's influence
        if influence_gain > 0:
            try:
                current_influence = citizen_fields.get('Influence', 0) or 0
                new_influence = current_influence + influence_gain
                
                tables['citizens'].update(
                    citizen_record['id'],
                    {"Influence": new_influence}
                )
                log.info(f"Increased {citizen_username}'s influence by {influence_gain} to {new_influence}")
            except Exception as e:
                log.error(f"Failed to update influence: {e}")
        
        # Prepare success response
        result = {
            "success": True,
            "messageId": message_id,
            "audienceReached": audience_count,
            "notificationsSent": notification_count,
            "influenceGained": influence_gain,
            "message": f"Your {message_type} echoes through the building, reaching {audience_count} citizens"
        }
        
        # Special handling for different message types
        if message_type == "proposal":
            # Could create a follow-up activity to gather support
            result["note"] = "Citizens may now support your proposal"
            
        elif message_type == "rallying_cry":
            # Could track momentum for collective action
            result["momentum"] = audience_count * (influence_gain / 10)
            result["note"] = "You've stirred the hearts of those present"
            
        elif message_type == "poetry":
            # Cultural impact
            result["culturalImpact"] = "Your verses add beauty to Venetian life"
        
        log.info(f"Successfully processed talk_publicly for {citizen_username}: {result}")
        return result
        
    except Exception as e:
        log.error(f"Error processing talk_publicly activity: {e}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }
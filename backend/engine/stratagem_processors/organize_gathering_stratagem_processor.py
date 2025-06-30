"""
Stratagem Processor for "organize_gathering".
Manages the lifecycle of social gatherings and tracks attendance.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pyairtable import Table

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    LogColors,
    _calculate_distance_meters
)

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    now_utc_dt: datetime
) -> Dict[str, Any]:
    """
    Process an active organize_gathering stratagem.
    
    This processor:
    1. Checks if the gathering is within its time window
    2. Updates attendance tracking
    3. Sends notifications to nearby citizens if just started
    4. Marks as executed when first attendee arrives
    5. Expires the stratagem when time window ends
    """
    stratagem_fields = stratagem_record['fields']
    stratagem_id = stratagem_fields.get('StratagemId')
    organizer = stratagem_fields.get('ExecutedBy')
    status = stratagem_fields.get('Status')
    
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing organize_gathering stratagem {stratagem_id} by {organizer}{LogColors.ENDC}")
    
    # Parse gathering data from Notes
    try:
        gathering_data = json.loads(stratagem_fields.get('Notes', '{}'))
    except json.JSONDecodeError:
        log.error(f"Failed to parse gathering data for {stratagem_id}")
        return {
            "success": False,
            "updates": {"Status": "failed", "Notes": "Invalid gathering data"}
        }
    
    location_building_id = gathering_data.get('location')
    theme = gathering_data.get('theme', 'social')
    
    # Parse time windows
    try:
        start_time = datetime.fromisoformat(gathering_data['startTime'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(gathering_data['endTime'].replace('Z', '+00:00'))
    except Exception as e:
        log.error(f"Invalid time data for gathering {stratagem_id}: {e}")
        return {
            "success": False,
            "updates": {"Status": "failed", "Notes": f"Invalid time data: {str(e)}"}
        }
    
    # Check if gathering has started
    if now_utc_dt < start_time:
        time_until = (start_time - now_utc_dt).total_seconds() / 60
        log.info(f"Gathering {stratagem_id} starts in {time_until:.0f} minutes")
        
        # Send advance notifications if within 30 minutes
        if time_until <= 30 and not gathering_data.get('notificationsSent'):
            _send_gathering_notifications(tables, stratagem_fields, gathering_data, now_utc_dt, advance=True)
            gathering_data['notificationsSent'] = True
            return {
                "success": True,
                "updates": {"Notes": json.dumps(gathering_data)}
            }
        
        return {"success": True, "updates": {}}
    
    # Check if gathering has ended
    if now_utc_dt > end_time:
        log.info(f"Gathering {stratagem_id} has ended")
        
        # Calculate final statistics
        attendance_count = len(gathering_data.get('attendance', []))
        messages_count = len(gathering_data.get('messagesDelivered', []))
        
        final_notes = {
            **gathering_data,
            "finalStats": {
                "totalAttendance": attendance_count,
                "messagesDelivered": messages_count,
                "endedAt": now_utc_dt.isoformat()
            }
        }
        
        return {
            "success": True,
            "updates": {
                "Status": "executed" if attendance_count > 0 else "expired",
                "ExecutedAt": now_utc_dt.isoformat() if attendance_count > 0 else None,
                "Notes": json.dumps(final_notes)
            }
        }
    
    # Gathering is active - check for attendees
    log.info(f"Gathering {stratagem_id} is active")
    
    # Get citizens at the gathering location
    try:
        building_position_formula = f"{{BuildingId}}='{location_building_id}'"
        buildings = tables['buildings'].all(formula=building_position_formula, max_records=1)
        
        if not buildings:
            log.error(f"Building {location_building_id} not found")
            return {"success": False, "updates": {"Status": "failed", "Notes": "Building not found"}}
        
        building_position = json.loads(buildings[0]['fields']['Position'])
        
        # Find citizens at or near the building
        all_citizens = tables['citizens'].all()
        attendees = []
        
        for citizen in all_citizens:
            citizen_pos_str = citizen['fields'].get('Position')
            if not citizen_pos_str:
                continue
                
            try:
                citizen_pos = json.loads(citizen_pos_str)
                distance = _calculate_distance_meters(
                    citizen_pos['lat'], citizen_pos['lng'],
                    building_position['lat'], building_position['lng']
                )
                
                # Consider citizen at gathering if within 50 meters
                if distance <= 50:
                    citizen_username = citizen['fields'].get('Username')
                    if citizen_username not in gathering_data.get('attendance', []):
                        attendees.append(citizen_username)
                        log.info(f"New attendee at gathering: {citizen_username}")
            except Exception:
                continue
        
        # Update attendance
        if attendees:
            current_attendance = gathering_data.get('attendance', [])
            current_attendance.extend(attendees)
            gathering_data['attendance'] = list(set(current_attendance))  # Remove duplicates
            
            # Mark as executed on first attendee
            updates = {"Notes": json.dumps(gathering_data)}
            if not stratagem_fields.get('ExecutedAt') and len(current_attendance) > 0:
                updates["ExecutedAt"] = now_utc_dt.isoformat()
                log.info(f"Gathering {stratagem_id} now has its first attendee!")
            
            return {"success": True, "updates": updates}
        
    except Exception as e:
        log.error(f"Error processing gathering attendance: {e}")
        import traceback
        log.error(traceback.format_exc())
    
    # No new attendees but gathering continues
    return {"success": True, "updates": {}}


def _send_gathering_notifications(
    tables: Dict[str, Table],
    stratagem_fields: Dict[str, Any],
    gathering_data: Dict[str, Any],
    now_utc_dt: datetime,
    advance: bool = False
) -> None:
    """Send notifications about the gathering to relevant citizens."""
    organizer = stratagem_fields.get('ExecutedBy')
    gathering_name = stratagem_fields.get('Name', 'Gathering')
    location_name = gathering_data.get('buildingName', 'the venue')
    theme = gathering_data.get('theme', 'social')
    invite_list = gathering_data.get('inviteList', [])
    
    # Notification content
    if advance:
        content = f"{organizer} invites you to {gathering_name} starting soon at {location_name}"
    else:
        content = f"{gathering_name} is now happening at {location_name}!"
    
    # Send to invite list
    notification_count = 0
    for invitee in invite_list:
        try:
            notification_payload = {
                "Citizen": invitee,
                "Type": "gathering_invitation",
                "Content": content,
                "Details": json.dumps({
                    "stratagemId": stratagem_fields.get('StratagemId'),
                    "organizer": organizer,
                    "location": gathering_data.get('location'),
                    "theme": theme,
                    "startTime": gathering_data.get('veniceStartTime')
                }),
                "Asset": gathering_data.get('location'),
                "AssetType": "building",
                "Status": "unread",
                "CreatedAt": now_utc_dt.isoformat()
            }
            
            tables['notifications'].create(notification_payload)
            notification_count += 1
        except Exception as e:
            log.warning(f"Failed to notify {invitee}: {e}")
    
    log.info(f"Sent {notification_count} gathering notifications")
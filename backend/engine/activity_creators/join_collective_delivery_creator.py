"""
Creator for 'join_collective_delivery' activities.
Allows citizens to join active collective delivery stratagems based on trust.
"""
import logging
import datetime
import time
import pytz
import json
from typing import Dict, Optional, Any

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any], 
    citizen_custom_id: str, 
    citizen_username: str, 
    citizen_airtable_id: str,
    stratagem_id: str,
    organizer_username: str,
    trust_score: float,
    reason: str = "trust_based_auto",
    amount_to_deliver: int = 20,
    resource_type: str = "grain",
    current_time_utc: Optional[datetime.datetime] = None
) -> Optional[Dict]:
    """
    Creates a join_collective_delivery activity for a citizen to participate
    in an active collective delivery stratagem.
    
    Args:
        stratagem_id: The ID of the collective delivery stratagem to join
        organizer_username: The username of the stratagem organizer
        trust_score: The trust score between citizen and organizer
        reason: Why they're joining (trust_based_auto, manual, etc.)
        amount_to_deliver: How much resource they plan to deliver
        resource_type: Type of resource being delivered
    """
    log.info(f"Creating join_collective_delivery activity for {citizen_username} to join {stratagem_id}")
    
    try:
        if current_time_utc is None:
            current_time_utc = datetime.datetime.now(pytz.UTC)
        
        # Duration is short - just joining the collective
        duration_minutes = 5
        end_time = current_time_utc + datetime.timedelta(minutes=duration_minutes)
        
        # Create descriptive notes (trust is 0-100)
        trust_level = "high" if trust_score >= 80 else "good" if trust_score >= 50 else "neutral"
        notes = {
            "stratagem_id": stratagem_id,
            "organizer": organizer_username,
            "trust_score": round(trust_score, 0),
            "trust_level": trust_level,
            "join_reason": reason,
            "planned_amount": amount_to_deliver,
            "resource_type": resource_type
        }
        
        activity_payload = {
            "ActivityId": f"join_collective_{citizen_custom_id}_{int(time.time())}",
            "Type": "join_collective_delivery",
            "Citizen": citizen_username,
            "CreatedAt": current_time_utc.isoformat(),
            "StartDate": current_time_utc.isoformat(),
            "EndDate": end_time.isoformat(),
            "DurationMinutes": duration_minutes,
            "Notes": json.dumps(notes),
            "Status": "created",
            "Description": f"{citizen_username} decides to join {organizer_username}'s collective delivery (trust: {trust_score:.0f})"
        }
        
        activity = tables['activities'].create(activity_payload)
        
        if activity and activity.get('id'):
            log.info(f"✓ Created join_collective_delivery activity: {activity['id']} (trust: {trust_score:.0f}, level: {trust_level})")
            return activity
        else:
            log.error(f"Failed to create join_collective_delivery activity for {citizen_username}")
            return None
            
    except Exception as e:
        log.error(f"Error creating join_collective_delivery activity for {citizen_username}: {e}")
        return None
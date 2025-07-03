"""
Activity Creator for 'goto_position'.

This creator generates movement activities to specific coordinates rather than buildings.
Used for outdoor observations, water-based activities, and other position-based tasks.
"""

import logging
import json
import uuid
import pytz
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    get_path_between_points,
    create_activity_record,
    dateutil_parser
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    destination_position: Dict[str, float],
    destination_name: str,
    citizen_position: Optional[Dict[str, float]],
    now_utc_dt: datetime,
    transport_api_url: str,
    notes: Optional[str] = None,
    details_payload: Optional[Dict[str, Any]] = None,
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'goto_position' activity for movement to specific coordinates.
    
    Args:
        tables: Database tables
        citizen_record: Citizen's database record
        destination_position: Target coordinates {"x": lat, "y": lng}
        destination_name: Human-readable name for the destination
        citizen_position: Current citizen position
        now_utc_dt: Current UTC time
        transport_api_url: API URL for pathfinding
        notes: Optional text notes
        details_payload: Optional structured data for chaining activities
        start_time_utc_iso: Optional custom start time
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    if not citizen_position:
        log.error(f"[Goto Position] {citizen_name}: No current position available.")
        return None
    
    # Get path to destination
    path_data = get_path_between_points(citizen_position, destination_position, transport_api_url)
    
    if not path_data or not path_data.get('success'):
        log.error(f"[Goto Position] {citizen_name}: Cannot find path to {destination_name}.")
        return None
    
    # Calculate timing
    effective_start_time = dateutil_parser.isoparse(start_time_utc_iso) if start_time_utc_iso else now_utc_dt
    if effective_start_time.tzinfo is None:
        effective_start_time = pytz.utc.localize(effective_start_time)
    
    duration_seconds = path_data.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min
    end_time = effective_start_time + timedelta(seconds=duration_seconds)
    
    # Create activity
    activity_title = f"Traveling to {destination_name}"
    activity_description = f"{citizen_name} is traveling to {destination_name}"
    activity_thought = f"I need to go to {destination_name}"
    
    # Prepare notes - include details for chaining if provided
    activity_notes = {
        "destination_name": destination_name,
        "destination_position": destination_position,
        "transport_mode": path_data.get('mode', 'walking')
    }
    
    # If there are details for chaining, include them
    if details_payload:
        activity_notes.update(details_payload)
    
    # Add any text notes
    if notes:
        activity_notes["notes"] = notes
    
    return create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="goto_position",
        start_date_iso=effective_start_time.isoformat(),
        end_date_iso=end_time.isoformat(),
        from_building_id=None,  # Position-based, not building-based
        to_building_id=None,
        title=activity_title,
        description=activity_description,
        thought=activity_thought,
        notes=json.dumps(activity_notes),
        path_json=json.dumps(path_data.get('path', [])),
        priority_override=50  # Standard movement priority
    )
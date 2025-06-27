"""
Activity Processor for 'goto_position'.

Handles movement to specific coordinates and chains any follow-up activities.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    VENICE_TIMEZONE
)

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Process a goto_position activity - update citizen position and handle chaining.
    """
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    
    # Parse notes to get destination and chaining info
    notes_str = activity_fields.get('Notes', '{}')
    try:
        notes = json.loads(notes_str)
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Activity {activity_guid}: Invalid Notes JSON.{LogColors.ENDC}")
        return False
    
    destination_name = notes.get('destination_name', 'unknown location')
    destination_position = notes.get('destination_position')
    
    if not destination_position:
        log.error(f"{LogColors.FAIL}Activity {activity_guid}: No destination position in notes.{LogColors.ENDC}")
        return False
    
    log.info(f"{LogColors.PROCESS}Processing 'goto_position' {activity_guid}: {citizen_username} arriving at {destination_name}.{LogColors.ENDC}")
    
    # Update citizen position
    try:
        # Get citizen record
        citizen_records = tables['citizens'].all(formula=f"{{Username}}='{citizen_username}'", max_records=1)
        if not citizen_records:
            log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found.{LogColors.ENDC}")
            return False
        
        citizen_record = citizen_records[0]
        
        # Update position
        tables['citizens'].update(
            citizen_record['id'],
            {'Position': json.dumps(destination_position)}
        )
        
        log.info(f"{LogColors.SUCCESS}{citizen_username} arrived at {destination_name} ({destination_position['x']:.4f}, {destination_position['y']:.4f}).{LogColors.ENDC}")
        
        # Handle activity chaining if specified
        if notes.get('action_on_arrival'):
            _handle_chained_activity(
                tables, citizen_username, citizen_record['id'],
                notes, activity_record, api_base_url
            )
        
        return True
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error updating position for {citizen_username}: {e}{LogColors.ENDC}")
        return False

def _handle_chained_activity(
    tables: Dict[str, Any],
    citizen_username: str,
    citizen_airtable_id: str,
    notes: Dict[str, Any],
    parent_activity: Dict[str, Any],
    api_base_url: Optional[str]
) -> None:
    """Handle creating a chained activity after arrival."""
    action_type = notes.get('action_on_arrival')
    duration_minutes = notes.get('duration_minutes_on_arrival', 60)
    
    log.info(f"{LogColors.OKBLUE}Creating chained '{action_type}' activity for {citizen_username}.{LogColors.ENDC}")
    
    # Import activity creators dynamically to avoid circular imports
    from backend.engine.activity_creators import create_activity_record
    
    # Calculate timing for chained activity
    parent_end_time = parent_activity['fields'].get('EndDate')
    if parent_end_time:
        try:
            from dateutil import parser as dateutil_parser
            import pytz
            from datetime import timedelta
            
            start_time = dateutil_parser.isoparse(parent_end_time)
            if start_time.tzinfo is None:
                start_time = pytz.utc.localize(start_time)
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Create the chained activity
            chained_notes = notes.get('notes_for_chained_activity', {})
            
            new_activity = create_activity_record(
                tables=tables,
                citizen_username=citizen_username,
                activity_type=action_type,
                start_date_iso=start_time.isoformat(),
                end_date_iso=end_time.isoformat(),
                from_building_id=None,
                to_building_id=None,
                title=notes.get('title_on_arrival', f"{action_type.replace('_', ' ').title()}"),
                description=notes.get('description_on_arrival', f"{citizen_username} is performing {action_type}"),
                thought=notes.get('thought_on_arrival', ''),
                notes=json.dumps(chained_notes),
                priority_override=notes.get('priority_on_arrival', 50),
                chained_from_activity_id=parent_activity['id']
            )
            
            if new_activity:
                log.info(f"{LogColors.OKGREEN}Successfully created chained '{action_type}' activity.{LogColors.ENDC}")
            else:
                log.error(f"{LogColors.FAIL}Failed to create chained '{action_type}' activity.{LogColors.ENDC}")
                
        except Exception as e:
            log.error(f"{LogColors.FAIL}Error creating chained activity: {e}{LogColors.ENDC}")
    else:
        log.error(f"{LogColors.FAIL}Parent activity has no EndDate for chaining.{LogColors.ENDC}")
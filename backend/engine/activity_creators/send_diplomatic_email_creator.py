"""
Send Diplomatic Email Activity Creator
Creates send_diplomatic_email activities for diplomatic_virtuoso
"""

import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    _escape_airtable_value,
    get_citizen_record,
    clean_thought_content
)

log = logging.getLogger(__name__)

def try_create_send_diplomatic_email_activity(
    tables: Dict[str, Any],
    citizen_username: str,
    parameters: Dict[str, Any],
    test_mode: bool = False
) -> Dict[str, Any]:
    """
    Creates a send_diplomatic_email activity.
    Only diplomatic_virtuoso can send external emails.
    
    Parameters:
        - to_email: Target email address
        - subject: Email subject
        - body: Email body
        - category: Email category (optional, default: "general")
        - research_area: Research area for scientific outreach (optional)
    """
    
    # Verify this is diplomatic_virtuoso
    if citizen_username != "diplomatic_virtuoso":
        return {
            "success": False,
            "message": "Only diplomatic_virtuoso can send external emails",
            "activity": None,
            "reason": "unauthorized_user"
        }
    
    # Extract parameters
    to_email = parameters.get("to_email")
    subject = parameters.get("subject")
    body = parameters.get("body")
    category = parameters.get("category", "general")
    research_area = parameters.get("research_area")
    
    # Validate required fields
    if not all([to_email, subject, body]):
        return {
            "success": False,
            "message": "Missing required fields: to_email, subject, body",
            "activity": None,
            "reason": "missing_parameters"
        }
    
    try:
        # Get citizen record
        citizen_record = get_citizen_record(tables, citizen_username)
        if not citizen_record:
            return {
                "success": False,
                "message": f"Citizen not found: {citizen_username}",
                "activity": None,
                "reason": "citizen_not_found"
            }
        
        citizen_id = citizen_record['fields'].get('CitizenId')
        citizen_airtable_id = citizen_record['id']
        
        # Create activity
        activity_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc)
        start_time = now_utc
        end_time = now_utc + timedelta(minutes=5)  # Email sending is quick
        
        # Prepare email data for Description field
        email_data = {
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "category": category,
            "research_area": research_area
        }
        
        # Create thought
        thought = f"I must send this diplomatic dispatch to {to_email} regarding {category}. The Mystical Viewing Glass shall carry my words beyond Venice's digital borders."
        
        activity_fields = {
            'ActivityId': activity_id,
            'Type': 'send_diplomatic_email',
            'CitizenUsername': _escape_airtable_value(citizen_username),
            'Citizen': [citizen_airtable_id],
            'Title': f"Send diplomatic email to {to_email}",
            'Description': json.dumps(email_data),
            'Thought': clean_thought_content(thought),
            'StartDate': start_time.isoformat(),
            'EndDate': end_time.isoformat(),
            'Status': 'created',
            'ToBuilding': None,  # No physical location needed
            'FromBuilding': None,
            'Position': citizen_record['fields'].get('Position'),
            'CreatedAt': now_utc.isoformat()
        }
        
        # Create activity in Airtable
        if not test_mode:
            created_activity = tables['ACTIVITIES'].create(activity_fields)
            log.info(f"Created send_diplomatic_email activity {activity_id} for {citizen_username}")
            
            return {
                "success": True,
                "message": f"Diplomatic email activity created successfully",
                "activity": created_activity,
                "reason": "success"
            }
        else:
            return {
                "success": True,
                "message": "Test mode: Activity would be created",
                "activity": {"fields": activity_fields, "id": f"test_{activity_id}"},
                "reason": "test_mode"
            }
            
    except Exception as e:
        log.error(f"Error creating send_diplomatic_email activity: {str(e)}")
        return {
            "success": False,
            "message": f"Error creating activity: {str(e)}",
            "activity": None,
            "reason": "error"
        }
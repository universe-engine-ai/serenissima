#!/usr/bin/env python3
"""
Review grievances that have reached support thresholds.

This scheduled process runs daily to:
1. Identify grievances with significant support (20+ supporters)
2. Update their status to "under_review"
3. Generate notifications for the Signoria
4. Track which grievances are gaining momentum

This is part of Phase 1 of the democratic system, establishing
the foundation for citizen participation in governance.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import pytz
from pyairtable import Table
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    VENICE_TIMEZONE
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Constants
SUPPORT_THRESHOLD = 20  # Grievances with 20+ supporters get reviewed
REVIEW_COOLDOWN_DAYS = 30  # Don't re-review grievances for 30 days


def initialize_tables():
    """Initialize Airtable connections."""
    try:
        grievances_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "GRIEVANCES")
        notifications_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "NOTIFICATIONS")
        citizens_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "CITIZENS")
        
        return grievances_table, notifications_table, citizens_table
    except Exception as e:
        log.error(f"Failed to initialize Airtable tables: {e}")
        return None, None, None


def get_signoria_members(citizens_table):
    """Get the top 10 most influential citizens (the Signoria)."""
    try:
        all_citizens = citizens_table.all()
        # Sort by influence
        sorted_citizens = sorted(
            all_citizens, 
            key=lambda c: c['fields'].get('Influence', 0), 
            reverse=True
        )
        # Return top 10
        return sorted_citizens[:10]
    except Exception as e:
        log.error(f"Failed to get Signoria members: {e}")
        return []


def review_grievances():
    """Main process to review grievances."""
    
    log.info("Starting grievance review process...")
    
    # Initialize tables
    grievances_table, notifications_table, citizens_table = initialize_tables()
    
    if not all([grievances_table, notifications_table, citizens_table]):
        log.error("Failed to initialize required tables")
        return
    
    now_venice = datetime.now(VENICE_TIMEZONE)
    now_utc = now_venice.astimezone(pytz.utc)
    
    try:
        # Get all grievances
        all_grievances = grievances_table.all()
        
        # Filter for grievances that need review
        grievances_to_review = []
        for grievance in all_grievances:
            fields = grievance['fields']
            
            # Skip if not enough support
            if fields.get('SupportCount', 0) < SUPPORT_THRESHOLD:
                continue
            
            # Skip if not in 'filed' status
            if fields.get('Status') != 'filed':
                continue
            
            # Skip if recently reviewed
            reviewed_at = fields.get('ReviewedAt')
            if reviewed_at:
                reviewed_date = datetime.fromisoformat(reviewed_at.replace('Z', '+00:00'))
                if (now_utc - reviewed_date).days < REVIEW_COOLDOWN_DAYS:
                    continue
            
            grievances_to_review.append(grievance)
        
        log.info(f"Found {len(grievances_to_review)} grievances ready for review")
        
        # Get Signoria members for notifications
        signoria_members = get_signoria_members(citizens_table)
        
        # Process each grievance
        for grievance in grievances_to_review:
            fields = grievance['fields']
            grievance_id = grievance['id']
            
            log.info(f"Reviewing grievance: {fields.get('Title')} (Support: {fields.get('SupportCount')})")
            
            # Update grievance status
            update_data = {
                'Status': 'under_review',
                'ReviewedAt': now_utc.isoformat()
            }
            
            try:
                grievances_table.update(grievance_id, update_data)
                log.info(f"Updated grievance {grievance_id} to 'under_review' status")
            except Exception as e:
                log.error(f"Failed to update grievance {grievance_id}: {e}")
                continue
            
            # Create notifications for Signoria members
            notification_title = f"Grievance Review Required: {fields.get('Title')}"
            notification_message = (
                f"A grievance filed by {fields.get('Citizen')} has reached {fields.get('SupportCount')} "
                f"supporters and requires Signoria review.\n\n"
                f"Category: {fields.get('Category')}\n"
                f"Description: {fields.get('Description')[:200]}..."
            )
            
            for member in signoria_members:
                try:
                    notification_data = {
                        'Username': member['fields'].get('Username'),
                        'Type': 'governance_review',
                        'Title': notification_title,
                        'Message': notification_message,
                        'Priority': 'high',
                        'RelatedId': grievance_id,
                        'CreatedAt': now_utc.isoformat(),
                        'Read': False
                    }
                    
                    notifications_table.create(notification_data)
                    
                except Exception as e:
                    log.error(f"Failed to create notification for {member['fields'].get('Username')}: {e}")
            
            # Create public notification about review
            try:
                public_notification = {
                    'Username': 'SYSTEM',
                    'Type': 'governance_update',
                    'Title': f"Grievance Under Review: {fields.get('Title')}",
                    'Message': f"The grievance '{fields.get('Title')}' with {fields.get('SupportCount')} supporters is now under official review by the Signoria.",
                    'Priority': 'normal',
                    'RelatedId': grievance_id,
                    'CreatedAt': now_utc.isoformat(),
                    'Read': False
                }
                
                notifications_table.create(public_notification)
                
            except Exception as e:
                log.error(f"Failed to create public notification: {e}")
        
        # Summary statistics
        if grievances_to_review:
            log.info(f"Review process complete. Processed {len(grievances_to_review)} grievances.")
        else:
            log.info("No grievances require review at this time.")
        
        # Log overall governance health metrics
        total_grievances = len([g for g in all_grievances if g['fields'].get('Status') == 'filed'])
        total_under_review = len([g for g in all_grievances if g['fields'].get('Status') == 'under_review'])
        total_addressed = len([g for g in all_grievances if g['fields'].get('Status') == 'addressed'])
        
        log.info(f"Governance Health: {total_grievances} filed, {total_under_review} under review, {total_addressed} addressed")
        
    except Exception as e:
        log.error(f"Error in grievance review process: {e}")
        raise


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    log.info("=== Starting Daily Grievance Review ===")
    review_grievances()
    log.info("=== Grievance Review Complete ===")
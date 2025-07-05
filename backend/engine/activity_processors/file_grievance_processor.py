import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import pytz

from backend.engine.utils.activity_helpers import (
    LogColors,
    VENICE_TIMEZONE,
    update_citizen_ducats
)
from backend.engine.utils.notification_helpers import create_notification

log = logging.getLogger(__name__)


def process_file_grievance_activity(
    tables: Dict[str, Any],
    activity: Dict[str, Any],
    venice_time: datetime
) -> bool:
    """
    Process a completed file_grievance activity.
    
    This:
    1. Deducts the filing fee from the citizen
    2. Creates a grievance record in the GRIEVANCES table
    3. Increases citizen's Influence for civic participation
    4. Sends notification about grievance filing
    """
    
    try:
        # Extract activity details
        details_json = activity.get('DetailsJSON', '{}')
        details = json.loads(details_json) if details_json else {}
        
        filing_fee = details.get('filing_fee', 50)
        grievance_category = details.get('grievance_category', 'general')
        grievance_title = details.get('grievance_title', 'Untitled Grievance')
        grievance_description = details.get('grievance_description', 'No description provided')
        
        # Get citizen record
        citizen_username = activity.get('Citizen')
        citizens_table = tables['CITIZENS']
        
        citizen_record = None
        for record in citizens_table.all():
            if record['fields'].get('Username') == citizen_username:
                citizen_record = record
                break
        
        if not citizen_record:
            log.error(f"{LogColors.FAIL}Citizen {citizen_username} not found{LogColors.ENDC}")
            return False
        
        citizen_fields = citizen_record['fields']
        citizen_name = citizen_fields.get('Name', citizen_username)
        current_wealth = citizen_fields.get('Ducats', 0)
        current_influence = citizen_fields.get('Influence', 0)
        
        # Deduct filing fee
        new_wealth = current_wealth - filing_fee
        if new_wealth < 0:
            log.warning(f"{LogColors.WARNING}{citizen_name} cannot afford filing fee{LogColors.ENDC}")
            return False
        
        # Update citizen wealth
        try:
            update_citizen_ducats(
                tables=tables,
                citizen_airtable_id=citizen_record['id'],
                amount_change=-filing_fee,
                reason=f"Paid filing fee for grievance: {grievance_title}",
                related_asset_type="grievance"
            )
        except Exception as e:
            log.error(f"{LogColors.FAIL}Failed to deduct filing fee from {citizen_name}: {e}{LogColors.ENDC}")
            return False
        
        # Check if GRIEVANCES table exists, if not we'll store in activity details
        grievances_table = tables.get('grievances')
        
        if grievances_table:
            # Create grievance record
            grievance_data = {
                'Citizen': citizen_username,
                'Category': grievance_category,
                'Title': grievance_title,
                'Description': grievance_description,
                'Status': 'filed',
                'SupportCount': 0,
                'FiledAt': venice_time.isoformat()
            }
            
            try:
                grievance_record = grievances_table.create(grievance_data)
                grievance_id = grievance_record['id']
                log.info(f"{LogColors.OKGREEN}Created grievance {grievance_id} for {citizen_name}{LogColors.ENDC}")
            except Exception as e:
                log.error(f"{LogColors.FAIL}Failed to create grievance record: {e}{LogColors.ENDC}")
                # Continue processing even if grievance table doesn't exist
                grievance_id = f"temp_{citizen_username}_{venice_time.timestamp()}"
        else:
            # Store grievance in activity details for now
            grievance_id = f"temp_{citizen_username}_{venice_time.timestamp()}"
            log.info(f"{LogColors.WARNING}GRIEVANCES table not found, storing in activity details{LogColors.ENDC}")
        
        # Increase citizen influence for civic participation
        influence_gain = 50  # Base influence for filing a grievance
        
        try:
            citizens_table.update(
                citizen_record['id'],
                {'Influence': current_influence + influence_gain}
            )
            log.info(f"{LogColors.OKGREEN}{citizen_name} gained {influence_gain} Influence for civic participation{LogColors.ENDC}")
        except Exception as e:
            log.error(f"{LogColors.FAIL}Failed to update influence: {e}{LogColors.ENDC}")
        
        # Send notification
        notification_content = f'{citizen_name} has filed a formal grievance about {grievance_category} issues at the Doge\'s Palace. Citizens may support this grievance to bring it to the Signoria\'s attention.'
        
        try:
            create_notification(
                tables=tables,
                citizen_username='SYSTEM',  # System-wide notification
                notification_type='governance',
                content=f'Grievance Filed: {grievance_title}',
                details={
                    'message': notification_content,
                    'grievance_id': grievance_id,
                    'category': grievance_category,
                    'filer': citizen_username
                },
                notes='New grievance filed'
            )
        except Exception as e:
            log.warning(f"Failed to create notification: {e}")
        
        # Log success
        log.info(
            f"{LogColors.OKGREEN}Processed grievance filing: "
            f"{citizen_name} filed '{grievance_title}' "
            f"(Category: {grievance_category}, Fee: {filing_fee} ducats){LogColors.ENDC}"
        )
        
        return True
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error processing file_grievance activity: {e}{LogColors.ENDC}")
        return False
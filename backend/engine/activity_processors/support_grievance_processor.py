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


def process_support_grievance_activity(
    tables: Dict[str, Any],
    activity: Dict[str, Any],
    venice_time: datetime
) -> bool:
    """
    Process a completed support_grievance activity.
    
    This:
    1. Deducts the support amount from the citizen
    2. Adds support to the grievance (updates GRIEVANCE_SUPPORT table)
    3. Increases citizen's Influence for political participation
    4. Updates grievance support count
    5. Sends notification about support
    """
    
    try:
        # Extract activity details
        details_json = activity.get('DetailsJSON', '{}')
        details = json.loads(details_json) if details_json else {}
        
        grievance_id = details.get('grievance_id')
        support_amount = details.get('support_amount', 10)
        supporter_class = details.get('supporter_class', 'Popolani')
        
        if not grievance_id:
            log.error(f"{LogColors.FAIL}No grievance_id in support activity{LogColors.ENDC}")
            return False
        
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
        
        # Deduct support amount
        new_wealth = current_wealth - support_amount
        if new_wealth < 0:
            log.warning(f"{LogColors.WARNING}{citizen_name} cannot afford support amount{LogColors.ENDC}")
            return False
        
        # Update citizen wealth
        try:
            update_citizen_ducats(
                tables=tables,
                citizen_airtable_id=citizen_record['id'],
                amount_change=-support_amount,
                reason=f"Support for grievance #{grievance_id}",
                related_asset_type="grievance_support"
            )
        except Exception as e:
            log.error(f"{LogColors.FAIL}Failed to deduct support amount from {citizen_name}: {e}{LogColors.ENDC}")
            return False
        
        # Check if GRIEVANCE_SUPPORT table exists
        support_table = tables.get('grievance_support')
        grievances_table = tables.get('grievances')
        
        support_count = 1
        
        if support_table:
            # Create support record
            support_data = {
                'GrievanceId': grievance_id,
                'Citizen': citizen_username,
                'SupportAmount': support_amount,
                'SupportedAt': venice_time.isoformat()
            }
            
            try:
                support_record = support_table.create(support_data)
                log.info(f"{LogColors.OKGREEN}Created support record for {citizen_name}{LogColors.ENDC}")
                
                # Count total supporters for this grievance
                all_supports = support_table.all()
                support_count = sum(1 for s in all_supports if s['fields'].get('GrievanceId') == grievance_id)
                
            except Exception as e:
                log.error(f"{LogColors.FAIL}Failed to create support record: {e}{LogColors.ENDC}")
        
        # Update grievance support count if table exists
        if grievances_table:
            try:
                # Find the grievance record
                for record in grievances_table.all():
                    if record['id'] == grievance_id or record['fields'].get('GrievanceId') == grievance_id:
                        grievances_table.update(
                            record['id'],
                            {'SupportCount': support_count}
                        )
                        break
            except Exception as e:
                log.error(f"{LogColors.FAIL}Failed to update grievance support count: {e}{LogColors.ENDC}")
        
        # Calculate influence gain based on support amount and social class
        base_influence = 25  # Base influence for supporting
        
        # Higher classes get more influence for supporting (they risk more)
        class_multipliers = {
            'Nobili': 2.0,
            'Artisti': 1.5,
            'Scientisti': 1.5,
            'Clero': 1.3,
            'Mercatores': 1.2,
            'Cittadini': 1.0,
            'Popolani': 1.0,
            'Facchini': 1.2,  # Poor get bonus for risking scarce resources
            'Forestieri': 0.8
        }
        
        multiplier = class_multipliers.get(supporter_class, 1.0)
        influence_gain = int(base_influence * multiplier)
        
        # Extra influence if they gave more than minimum
        if support_amount > 10:
            influence_gain += int((support_amount - 10) * 0.5)
        
        try:
            citizens_table.update(
                citizen_record['id'],
                {'Influence': current_influence + influence_gain}
            )
            log.info(f"{LogColors.OKGREEN}{citizen_name} gained {influence_gain} Influence for supporting grievance{LogColors.ENDC}")
        except Exception as e:
            log.error(f"{LogColors.FAIL}Failed to update influence: {e}{LogColors.ENDC}")
        
        # Send notification
        notification_content = f'{citizen_name} ({supporter_class}) has added {support_amount} ducats of support to grievance #{grievance_id}. Total supporters: {support_count}'
        
        try:
            create_notification(
                tables=tables,
                citizen_username='SYSTEM',
                notification_type='governance',
                content='Grievance Support Added',
                details={
                    'message': notification_content,
                    'grievance_id': grievance_id,
                    'supporter': citizen_username,
                    'support_amount': support_amount,
                    'total_supporters': support_count
                },
                notes='Grievance support added'
            )
        except Exception as e:
            log.warning(f"Failed to create notification: {e}")
        
        # Check if grievance has reached threshold for attention
        if support_count >= 20:
            threshold_content = f'Grievance #{grievance_id} has reached {support_count} supporters and will be reviewed by the Signoria'
            
            try:
                create_notification(
                    tables=tables,
                    citizen_username='SYSTEM',
                    notification_type='governance_alert',
                    content='Grievance Gains Major Support',
                    details={
                        'message': threshold_content,
                        'grievance_id': grievance_id,
                        'support_count': support_count
                    },
                    notes='Grievance reached review threshold'
                )
            except Exception as e:
                log.warning(f"Failed to create threshold notification: {e}")
        
        # Log success
        log.info(
            f"{LogColors.OKGREEN}Processed grievance support: "
            f"{citizen_name} supported grievance #{grievance_id} "
            f"with {support_amount} ducats (Total supporters: {support_count}){LogColors.ENDC}"
        )
        
        return True
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error processing support_grievance activity: {e}{LogColors.ENDC}")
        return False
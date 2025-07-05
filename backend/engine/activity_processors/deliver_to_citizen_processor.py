"""
Processor for 'deliver_to_citizen' activities.
Handles the transfer of resources directly between citizens.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from pyairtable import Table

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_resource_record
)
from backend.engine.utils.notification_helpers import create_notification

log = logging.getLogger(__name__)


def process(
    tables: Dict[str, Table],
    activity_record: Dict[str, Any],
    current_utc_time: datetime,
    transport_api_url: str,
    testing_mode: bool = False
) -> bool:
    """
    Process a deliver_to_citizen activity.
    Transfers resources from one citizen's inventory to another.
    """
    activity_id = activity_record['id']
    citizen_username = activity_record['fields'].get('Citizen')
    
    try:
        # Parse activity notes
        notes_str = activity_record['fields'].get('Notes', '{}')
        notes = json.loads(notes_str) if notes_str else {}
        
        target_citizen_username = notes.get('target_citizen')
        resource_type = notes.get('resource_type')
        amount = notes.get('amount', 0)
        delivery_manifest = notes.get('delivery_manifest', [])
        collective_action = notes.get('collective_action', '')
        
        if not all([target_citizen_username, resource_type, amount, delivery_manifest]):
            log.error(f"[Deliver to Citizen] Missing required delivery information for activity {activity_id}")
            return False
        
        # Get both citizens
        delivering_citizen = get_citizen_record(tables, citizen_username)
        target_citizen = get_citizen_record(tables, target_citizen_username)
        
        if not delivering_citizen or not target_citizen:
            log.error(f"[Deliver to Citizen] Could not find citizens for delivery")
            return False
        
        citizen_name = f"{delivering_citizen['fields'].get('FirstName', '')} {delivering_citizen['fields'].get('LastName', '')}".strip() or citizen_username
        target_name = f"{target_citizen['fields'].get('FirstName', '')} {target_citizen['fields'].get('LastName', '')}".strip() or target_citizen_username
        
        # Update delivering citizen's position to target location
        target_position = activity_record['fields'].get('ToPosition')
        if target_position:
            tables['citizens'].update(delivering_citizen['id'], {'Position': target_position})
            log.info(f"[Deliver to Citizen] Updated {citizen_name}'s position to {target_position}")
        
        # Process the resource transfer
        total_delivered = 0
        target_inventory = target_citizen['fields'].get('Inventory', [])
        delivering_inventory = delivering_citizen['fields'].get('Inventory', [])
        
        for manifest_item in delivery_manifest:
            stack_id = manifest_item['stackId']
            transfer_amount = manifest_item['amount']
            
            # Get the resource stack
            resource_stack = get_resource_record(tables, stack_id)
            if not resource_stack:
                log.warning(f"[Deliver to Citizen] Stack {stack_id} not found, skipping")
                continue
            
            stack_amount = resource_stack['fields'].get('Amount', 0)
            actual_transfer = min(transfer_amount, stack_amount)
            
            if actual_transfer <= 0:
                continue
            
            # Update or remove source stack
            if actual_transfer >= stack_amount:
                # Transfer entire stack - just update owner and location
                tables['resources'].update(resource_stack['id'], {
                    'Owner': target_citizen_username,
                    'Location': f"citizen_{target_citizen_username}"
                })
                
                # Update inventories
                if stack_id in delivering_inventory:
                    delivering_inventory.remove(stack_id)
                if stack_id not in target_inventory:
                    target_inventory.append(stack_id)
                
                log.info(f"[Deliver to Citizen] Transferred entire stack {stack_id} ({actual_transfer} {resource_type}) to {target_name}")
            else:
                # Partial transfer - reduce source and create new stack for target
                tables['resources'].update(resource_stack['id'], {
                    'Amount': stack_amount - actual_transfer
                })
                
                # Create new stack for recipient
                new_stack_data = {
                    'ResourceId': f"{resource_type}_{target_citizen_username}_{int(datetime.utcnow().timestamp())}",
                    'Type': resource_type,
                    'Amount': actual_transfer,
                    'Owner': target_citizen_username,
                    'Location': f"citizen_{target_citizen_username}",
                    'CreatedAt': datetime.utcnow().isoformat() + 'Z'
                }
                
                new_stack = tables['resources'].create(new_stack_data)
                if new_stack and new_stack['id'] not in target_inventory:
                    target_inventory.append(new_stack['id'])
                
                log.info(f"[Deliver to Citizen] Transferred {actual_transfer} {resource_type} from stack {stack_id} to {target_name}")
            
            total_delivered += actual_transfer
        
        # Update both citizens' inventories
        tables['citizens'].update(delivering_citizen['id'], {'Inventory': delivering_inventory})
        tables['citizens'].update(target_citizen['id'], {'Inventory': target_inventory})
        
        # Send notifications
        delivery_message = f"{citizen_name} has delivered {total_delivered} {resource_type} to you"
        if collective_action:
            delivery_message += f" as part of: {collective_action}"
        
        create_notification(
            tables=tables,
            recipient_username=target_citizen_username,
            title="Resource Delivery Received",
            message=delivery_message,
            category="delivery"
        )
        
        create_notification(
            tables=tables,
            recipient_username=citizen_username,
            title="Delivery Complete",
            message=f"Successfully delivered {total_delivered} {resource_type} to {target_name}",
            category="delivery"
        )
        
        log.info(f"{LogColors.OKGREEN}[Deliver to Citizen] {citizen_name} delivered {total_delivered} {resource_type} to {target_name}{LogColors.ENDC}")
        
        # Update activity status
        tables['activities'].update(activity_id, {
            'Status': 'completed',
            'CompletedAt': datetime.utcnow().isoformat() + 'Z'
        })
        
        return True
        
    except Exception as e:
        log.error(f"[Deliver to Citizen] Error processing delivery: {e}")
        return False
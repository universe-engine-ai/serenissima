"""
Processor for 'deliver_to_building' activities.
Citizen arrives at building and deposits resources from their inventory.
Resources are transferred to the building's storage.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    get_citizen_record,
    get_building_record,
    _escape_airtable_value,
    VENICE_TIMEZONE, LogColors,
    extract_details_from_notes
)

log = logging.getLogger(__name__)

def _update_activity_notes_with_failure_reason(tables: Dict[str, Any], activity_airtable_id: str, failure_reason: str):
    """Appends a failure reason to the activity's Notes field."""
    try:
        activity_to_update = tables['activities'].get(activity_airtable_id)
        if not activity_to_update:
            log.error(f"Could not find activity {activity_airtable_id} to update notes with failure reason.")
            return
        existing_notes = activity_to_update['fields'].get('Notes', '')
        timestamp = datetime.now(VENICE_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")
        new_note_entry = f"\n[FAILURE - {timestamp}] {failure_reason}"
        updated_notes = existing_notes + new_note_entry
        tables['activities'].update(activity_airtable_id, {'Notes': updated_notes})
    except Exception as e:
        log.error(f"Error updating notes for activity {activity_airtable_id}: {e}")

def process(
    tables: Dict[str, Any],
    activity_record: Dict,
    building_type_defs: Dict,
    resource_defs: Dict,
    api_base_url: Optional[str] = None
) -> bool:
    activity_id_airtable = activity_record['id']
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_id_airtable)
    log.info(f"Processing 'deliver_to_building' activity: {activity_guid}")

    delivery_person_username = activity_fields.get('Citizen')
    activity_notes = activity_fields.get('Notes', '')
    
    # Parse delivery details from notes
    parsed_details = extract_details_from_notes(activity_notes)
    if not parsed_details:
        try:
            parsed_details = json.loads(activity_notes)
        except:
            err_msg = f"Failed to parse delivery details from notes"
            log.error(f"{err_msg} Activity: {activity_guid}")
            _update_activity_notes_with_failure_reason(tables, activity_id_airtable, err_msg)
            return False
    
    target_building_id = parsed_details.get('target_building')
    resource_type = parsed_details.get('resource_type')
    amount = float(parsed_details.get('amount', 0))
    delivery_manifest = parsed_details.get('delivery_manifest', [])
    
    if not all([target_building_id, resource_type, amount, delivery_manifest]):
        err_msg = "Missing crucial delivery details"
        log.error(f"{err_msg} Activity: {activity_guid}")
        _update_activity_notes_with_failure_reason(tables, activity_id_airtable, err_msg)
        return False
    
    # Get citizen record
    delivery_person_record = get_citizen_record(tables, delivery_person_username)
    if not delivery_person_record:
        err_msg = f"Delivery person {delivery_person_username} not found."
        log.error(f"{err_msg} Activity: {activity_guid}")
        _update_activity_notes_with_failure_reason(tables, activity_id_airtable, err_msg)
        return False
    
    # Get building record
    building_record = get_building_record(tables, target_building_id)
    if not building_record:
        err_msg = f"Target building {target_building_id} not found."
        log.error(f"{err_msg} Activity: {activity_guid}")
        _update_activity_notes_with_failure_reason(tables, activity_id_airtable, err_msg)
        return False
    
    building_name = building_record['fields'].get('Name', target_building_id)
    building_owner = building_record['fields'].get('RunBy', '')
    
    # Process resource transfer
    now_iso = datetime.now(VENICE_TIMEZONE).isoformat()
    total_transferred = 0
    
    for item in delivery_manifest:
        stack_id = item.get('stackId')
        amount_to_transfer = float(item.get('amount', 0))
        
        if not stack_id or amount_to_transfer <= 0:
            continue
        
        # Verify citizen has this resource stack
        citizen_inventory = delivery_person_record['fields'].get('Inventory', [])
        if stack_id not in citizen_inventory:
            err_msg = f"Stack {stack_id} not found in citizen inventory"
            log.error(f"{err_msg} Activity: {activity_guid}")
            continue
        
        # Get the resource stack
        try:
            resource_stack = tables['resources'].get(stack_id)
            if not resource_stack:
                err_msg = f"Resource stack {stack_id} not found"
                log.error(f"{err_msg} Activity: {activity_guid}")
                continue
            
            stack_fields = resource_stack['fields']
            if stack_fields.get('Type') != resource_type:
                err_msg = f"Stack {stack_id} type mismatch: expected {resource_type}, got {stack_fields.get('Type')}"
                log.error(f"{err_msg} Activity: {activity_guid}")
                continue
            
            current_count = float(stack_fields.get('Count', 0))
            if current_count < amount_to_transfer:
                err_msg = f"Insufficient resources in stack {stack_id}: has {current_count}, needs {amount_to_transfer}"
                log.error(f"{err_msg} Activity: {activity_guid}")
                amount_to_transfer = current_count  # Transfer what's available
            
            # Update or delete the citizen's stack
            new_count = current_count - amount_to_transfer
            if new_count > 0.001:
                tables['resources'].update(stack_id, {'Count': new_count})
            else:
                # Remove from citizen inventory
                new_inventory = [inv_id for inv_id in citizen_inventory if inv_id != stack_id]
                tables['citizens'].update(delivery_person_record['id'], {'Inventory': new_inventory})
                # Delete the resource stack
                tables['resources'].delete(stack_id)
            
            # Add to building's storage
            building_res_formula = (
                f"AND({{Type}}='{_escape_airtable_value(resource_type)}', "
                f"{{Asset}}='{_escape_airtable_value(target_building_id)}', "
                f"{{AssetType}}='building', "
                f"{{Owner}}='{_escape_airtable_value(building_owner or 'building')}')"
            )
            
            existing_building_res = tables['resources'].all(formula=building_res_formula, max_records=1)
            res_def = resource_defs.get(resource_type, {})
            
            if existing_building_res:
                # Update existing stack
                building_res = existing_building_res[0]
                new_building_count = float(building_res['fields'].get('Count', 0)) + amount_to_transfer
                tables['resources'].update(building_res['id'], {'Count': new_building_count})
            else:
                # Create new stack in building
                new_resource_payload = {
                    "ResourceId": f"resource-{uuid.uuid4()}",
                    "Type": resource_type,
                    "Name": res_def.get('name', resource_type),
                    "Asset": target_building_id,
                    "AssetType": "building",
                    "Owner": building_owner or "building",
                    "Count": amount_to_transfer,
                    "CreatedAt": now_iso,
                    "Notes": f"Delivered by {delivery_person_username}"
                }
                tables['resources'].create(new_resource_payload)
            
            total_transferred += amount_to_transfer
            log.info(f"Transferred {amount_to_transfer} {resource_type} from {delivery_person_username} to {building_name}")
            
        except Exception as e:
            err_msg = f"Error processing stack {stack_id}: {e}"
            log.error(f"{err_msg} Activity: {activity_guid}")
            _update_activity_notes_with_failure_reason(tables, activity_id_airtable, err_msg)
            continue
    
    if total_transferred > 0:
        log.info(f"{LogColors.OKGREEN}Successfully delivered {total_transferred} {resource_type} to {building_name}{LogColors.ENDC}")
        return True
    else:
        err_msg = f"No resources were transferred"
        log.error(f"{err_msg} Activity: {activity_guid}")
        _update_activity_notes_with_failure_reason(tables, activity_id_airtable, err_msg)
        return False
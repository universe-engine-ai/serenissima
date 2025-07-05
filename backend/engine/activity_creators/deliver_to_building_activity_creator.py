"""
Creator for 'deliver_to_building' activities.
Enables direct citizen-to-building resource transfers for automated buildings.
"""
import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    create_activity_record,
    get_citizen_record,
    get_resource_stack,
    get_building_record,
    get_path_between_points,
    VENICE_TIMEZONE,
    dateutil_parser
)

log = logging.getLogger(__name__)

DELIVERY_BASE_DURATION_MINUTES = 10  # Base time for delivery
TRAVEL_SPEED_KMH = 5  # Walking speed


def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    now_utc_dt: datetime,
    transport_api_url: str,
    start_time_utc_iso: Optional[str] = None,
    target_building_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    amount: Optional[int] = None,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'deliver_to_building' activity.
    
    Args:
        target_building_id: Custom ID of the recipient building
        resource_type: Type of resource to deliver
        amount: Amount to deliver
        notes: Optional notes about the delivery
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    if not all([target_building_id, resource_type, amount]):
        log.warning(f"{LogColors.WARNING}[Deliver to Building] Missing required parameters for {citizen_name}{LogColors.ENDC}")
        return None
    
    # Get target building record
    target_building = get_building_record(tables, target_building_id)
    if not target_building:
        log.warning(f"{LogColors.WARNING}[Deliver to Building] Target building {target_building_id} not found{LogColors.ENDC}")
        return None
    
    building_name = target_building['fields'].get('Name', target_building_id)
    building_type = target_building['fields'].get('Type', 'unknown')
    
    # Check if citizen has the resource in inventory
    citizen_inventory = citizen_record['fields'].get('Inventory', [])
    available_resources = {}
    
    for inv_item_id in citizen_inventory:
        try:
            resource_stack = get_resource_stack(tables, inv_item_id)
            if resource_stack and resource_stack['fields'].get('Type') == resource_type:
                stack_amount = resource_stack['fields'].get('Amount', 0)
                available_resources[inv_item_id] = stack_amount
        except Exception as e:
            log.error(f"Error checking inventory item {inv_item_id}: {e}")
    
    total_available = sum(available_resources.values())
    if total_available < amount:
        log.warning(f"{LogColors.WARNING}[Deliver to Building] {citizen_name} only has {total_available} {resource_type}, needs {amount}{LogColors.ENDC}")
        return None
    
    # Get target building position
    building_position_str = target_building['fields'].get('Position')
    if not building_position_str:
        log.warning(f"{LogColors.WARNING}[Deliver to Building] Target building {building_name} has no position{LogColors.ENDC}")
        return None
    
    try:
        x, z = building_position_str.split(',')
        target_position = {'lat': float(x), 'lng': float(z)}
    except:
        log.error(f"[Deliver to Building] Invalid position format for {building_name}: {building_position_str}")
        return None
    
    # Calculate travel time
    travel_path = None
    travel_duration_minutes = DELIVERY_BASE_DURATION_MINUTES
    
    if citizen_position and citizen_position != target_position:
        try:
            path_result = get_path_between_points(
                start_position=citizen_position,
                end_position=target_position,
                transport_api_url=transport_api_url
            )
            if path_result and path_result.get('path'):
                travel_path = path_result['path']
                travel_time_seconds = path_result.get('travelTime', 0)
                travel_duration_minutes = max(DELIVERY_BASE_DURATION_MINUTES, int(travel_time_seconds / 60))
        except Exception as e:
            log.warning(f"[Deliver to Building] Could not calculate path: {e}")
    
    effective_start_time_dt = dateutil_parser.isoparse(start_time_utc_iso) if start_time_utc_iso else now_utc_dt
    if effective_start_time_dt.tzinfo is None:
        effective_start_time_dt = pytz.utc.localize(effective_start_time_dt)
    
    end_time_dt = effective_start_time_dt + timedelta(minutes=travel_duration_minutes)
    
    # Prepare resource stacks to deliver
    delivery_manifest = []
    remaining_to_deliver = amount
    
    for stack_id, stack_amount in available_resources.items():
        if remaining_to_deliver <= 0:
            break
        
        take_amount = min(remaining_to_deliver, stack_amount)
        delivery_manifest.append({
            'stackId': stack_id,
            'amount': take_amount
        })
        remaining_to_deliver -= take_amount
    
    activity_title = f"Deliver {amount} {resource_type} to {building_name}"
    activity_description = f"{citizen_name} delivers resources to {building_name} ({building_type})"
    activity_thought = f"I must deliver these {resource_type} to {building_name}"
    
    if notes:
        activity_thought += f" - {notes}"
    
    # Activity notes with delivery details
    activity_notes = {
        "delivery_type": "citizen_to_building",
        "target_building": target_building_id,
        "building_name": building_name,
        "building_type": building_type,
        "resource_type": resource_type,
        "amount": amount,
        "delivery_manifest": delivery_manifest,
        "duration_minutes": travel_duration_minutes,
        "purpose": notes or "Direct building delivery"
    }
    
    log.info(f"{LogColors.OKBLUE}[Deliver to Building] {citizen_name} will deliver {amount} {resource_type} to {building_name}{LogColors.ENDC}")
    
    return create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="deliver_to_building",
        start_date_iso=effective_start_time_dt.isoformat(),
        end_date_iso=end_time_dt.isoformat(),
        from_position=citizen_position,
        to_position=target_position,
        title=activity_title,
        description=activity_description,
        thought=activity_thought,
        notes=json.dumps(activity_notes),
        priority_override=80,  # High priority for deliveries
        path=travel_path
    )
#!/usr/bin/env python3
"""
Welfare Porter Delivery Handler
Completes the porter work by delivering cargo and triggering food collection

Activity Type: welfare_porter_delivery
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

from backend.engine.handlers.base_handler import BaseActivityHandler
from backend.engine.utils.activity_helpers import (
    LogColors, _escape_airtable_value,
    get_citizen_current_load, _calculate_distance_meters
)

log = logging.getLogger(__name__)


def create_error_response(message: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        'success': False,
        'message': message,
        'data': data or {}
    }


class WelfarePorterDeliveryHandler(BaseActivityHandler):
    """
    Handles the delivery phase of welfare porter work.
    Completes cargo delivery and chains food collection activity.
    """
    
    def can_handle(self, activity_type: str) -> bool:
        """Check if this handler can process the activity type."""
        return activity_type == "welfare_porter_delivery"
    
    def process(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process welfare porter delivery.
        
        Expected activity data:
        {
            "destination": "building_id_456",
            "cargo_type": "grain",
            "cargo_amount": 50,
            "voucher_id": "voucher_abc123"
        }
        """
        try:
            log.info(f"{LogColors.HEADER}Processing welfare porter delivery{LogColors.ENDC}")
            
            # Get citizen data
            citizen_id = activity['fields'].get('Citizen')[0]
            citizen = self.tables['citizens'].get(citizen_id)
            
            if not citizen:
                return create_error_response("Citizen not found", {"citizen_id": citizen_id})
            
            citizen_username = citizen['fields'].get('Username')
            citizen_name = f"{citizen['fields'].get('FirstName', '')} {citizen['fields'].get('LastName', '')}"
            citizen_pos = citizen['fields'].get('Position')
            
            # Get activity data
            activity_data = activity['fields'].get('Data', {})
            destination_id = activity_data.get('destination')
            cargo_type = activity_data.get('cargo_type')
            cargo_amount = activity_data.get('cargo_amount', 0)
            voucher_id = activity_data.get('voucher_id')
            
            if not all([destination_id, cargo_type, voucher_id]):
                return create_error_response("Missing delivery data")
            
            # Get destination building
            destination = self._get_building_by_id(destination_id)
            if not destination:
                return create_error_response("Invalid destination building")
            
            dest_pos = destination['fields'].get('Position')
            dest_name = destination['fields'].get('Name', 'destination')
            
            # Check if citizen is at destination
            distance_to_dest = _calculate_distance_meters(citizen_pos, dest_pos)
            if distance_to_dest > 50:
                return create_error_response(
                    f"Too far from destination. Move within 50m of {dest_name}",
                    {"distance": round(distance_to_dest)}
                )
            
            # Check citizen has the cargo
            citizen_cargo = self._get_citizen_resource(citizen_username, cargo_type)
            if citizen_cargo < cargo_amount:
                return create_error_response(
                    f"Missing cargo. Expected {cargo_amount} {cargo_type}, have {citizen_cargo}",
                    {"expected": cargo_amount, "actual": citizen_cargo}
                )
            
            # Transfer cargo to destination
            transfer_success = self._transfer_cargo_to_building(
                citizen_username, destination_id, cargo_type, cargo_amount
            )
            
            if not transfer_success:
                return create_error_response("Failed to deliver cargo")
            
            # Get voucher details for food amount
            voucher_data = self._get_voucher_data(voucher_id)
            if not voucher_data:
                # Default food payment if voucher lookup fails
                voucher_data = {'food_amount': 5, 'food_type': 'bread'}
            
            # Chain food collection activity
            collection_activity = self._create_food_collection_activity(
                citizen_id, voucher_data
            )
            
            # Create notification
            self._create_notification(
                citizen_username,
                f"✅ Successfully delivered **{cargo_amount} {cargo_type}** to {dest_name}! "
                f"Your food voucher for {voucher_data['food_amount']} bread is ready for collection.",
                {
                    "event_type": "welfare_porter_completed",
                    "cargo_delivered": f"{cargo_amount} {cargo_type}",
                    "destination": dest_name,
                    "food_earned": voucher_data['food_amount'],
                    "voucher_id": voucher_id
                }
            )
            
            log.info(f"{LogColors.SUCCESS}{citizen_name} completed porter work, "
                    f"earned {voucher_data['food_amount']} bread{LogColors.ENDC}")
            
            return {
                "success": True,
                "message": f"Delivered {cargo_amount} {cargo_type}. Collect your {voucher_data['food_amount']} bread!",
                "data": {
                    "cargo_delivered": f"{cargo_amount} {cargo_type}",
                    "destination": dest_name,
                    "food_earned": voucher_data['food_amount'],
                    "collection_activity": collection_activity['id']
                }
            }
            
        except Exception as e:
            log.error(f"Error in welfare porter delivery: {str(e)}")
            return create_error_response(f"Delivery failed: {str(e)}")
    
    def _get_building_by_id(self, building_id: str) -> Optional[Dict]:
        """Get building record by ID."""
        try:
            formula = f"{{BuildingId}}='{_escape_airtable_value(building_id)}'"
            records = self.tables['buildings'].all(formula=formula, max_records=1)
            return records[0] if records else None
        except Exception as e:
            log.error(f"Error fetching building: {e}")
            return None
    
    def _get_citizen_resource(self, citizen_username: str, resource_type: str) -> float:
        """Get amount of resource citizen is carrying."""
        try:
            formula = (
                f"AND("
                f"{{Owner}}='{_escape_airtable_value(citizen_username)}', "
                f"{{Location}}='{_escape_airtable_value(citizen_username)}', "
                f"{{Type}}='{_escape_airtable_value(resource_type)}'"
                f")"
            )
            resources = self.tables['resources'].all(formula=formula)
            return sum(r['fields'].get('Quantity', 0) for r in resources)
        except Exception as e:
            log.error(f"Error checking citizen resources: {e}")
            return 0
    
    def _transfer_cargo_to_building(self, citizen_username: str, building_id: str,
                                    resource_type: str, amount: float) -> bool:
        """Transfer cargo from citizen to building."""
        try:
            # Find citizen's resource record
            formula = (
                f"AND("
                f"{{Owner}}='{_escape_airtable_value(citizen_username)}', "
                f"{{Location}}='{_escape_airtable_value(citizen_username)}', "
                f"{{Type}}='{_escape_airtable_value(resource_type)}'"
                f")"
            )
            citizen_resources = self.tables['resources'].all(formula=formula, max_records=1)
            
            if not citizen_resources:
                return False
            
            citizen_resource = citizen_resources[0]
            current_quantity = citizen_resource['fields'].get('Quantity', 0)
            
            if current_quantity < amount:
                return False
            
            # Check if building already has this resource
            building_formula = (
                f"AND("
                f"{{Location}}='{_escape_airtable_value(building_id)}', "
                f"{{Type}}='{_escape_airtable_value(resource_type)}'"
                f")"
            )
            building_resources = self.tables['resources'].all(formula=building_formula, max_records=1)
            
            # Update citizen's resource
            new_citizen_quantity = current_quantity - amount
            if new_citizen_quantity > 0:
                self.tables['resources'].update(citizen_resource['id'], {
                    'Quantity': new_citizen_quantity
                })
            else:
                self.tables['resources'].delete(citizen_resource['id'])
            
            # Update or create building's resource
            if building_resources:
                # Add to existing
                building_resource = building_resources[0]
                existing_quantity = building_resource['fields'].get('Quantity', 0)
                self.tables['resources'].update(building_resource['id'], {
                    'Quantity': existing_quantity + amount
                })
            else:
                # Create new
                # Get building owner for resource ownership
                building = self._get_building_by_id(building_id)
                owner = building['fields'].get('Owner', building['fields'].get('RunBy', 'ConsiglioDeiDieci'))
                
                self.tables['resources'].create({
                    'Type': resource_type,
                    'Quantity': amount,
                    'Owner': owner,
                    'Location': building_id,
                    'Quality': citizen_resource['fields'].get('Quality', 80)
                })
            
            log.info(f"Transferred {amount} {resource_type} from {citizen_username} to {building_id}")
            return True
            
        except Exception as e:
            log.error(f"Error transferring cargo: {e}")
            return False
    
    def _get_voucher_data(self, voucher_id: str) -> Optional[Dict]:
        """Get voucher data. In production would query vouchers table."""
        # For now, return standard welfare payment
        return {
            'id': voucher_id,
            'food_amount': 5,
            'food_type': 'bread',
            'employer': 'ConsiglioDeiDieci'
        }
    
    def _create_food_collection_activity(self, citizen_id: str, voucher_data: Dict) -> Dict:
        """Create chained food collection activity."""
        try:
            collection_data = {
                'Type': 'collect_welfare_food',
                'Citizen': [citizen_id],
                'Status': 'pending',
                'Data': json.dumps({
                    'voucher': voucher_data
                }),
                'ChainedFrom': [activity['id']]
            }
            
            result = self.tables['activities'].create(collection_data)
            return result
            
        except Exception as e:
            log.error(f"Error creating collection activity: {e}")
            return {'id': 'error'}
    
    def _create_notification(self, citizen: str, content: str, details: Dict):
        """Create a notification for a citizen."""
        try:
            self.tables['notifications'].create({
                "Type": "welfare_completed",
                "Content": content,
                "Details": json.dumps(details),
                "CreatedAt": datetime.now().isoformat(),
                "Citizen": citizen
            })
        except Exception as e:
            log.error(f"Error creating notification: {e}")


# Register the handler
def register():
    """Register this handler with the system."""
    return WelfarePorterDeliveryHandler()


# Activity processor wrapper
def handle_welfare_porter_delivery(tables: Dict[str, Any], activity_record: Dict[str, Any], 
                                  building_type_defs: Any, resource_defs: Any,
                                  api_base_url: Optional[str] = None) -> bool:
    """Process welfare porter delivery activity."""
    handler = WelfarePorterDeliveryHandler()
    handler.set_tables(tables)
    if api_base_url:
        handler.set_urls(api_base_url, api_base_url + "/transport")
    
    result = handler.process(activity_record)
    return result.get('success', False)
#!/usr/bin/env python3
"""
Welfare Porter Activity Handler
Handles porter work for hungry/poor citizens who work for food vouchers

Activity Type: welfare_porter
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from backend.engine.handlers.base_handler import BaseActivityHandler
from backend.engine.utils.activity_helpers import (
    LogColors, _escape_airtable_value,
    get_citizen_current_load, get_citizen_effective_carry_capacity,
    get_path_between_points, _calculate_distance_meters
)

log = logging.getLogger(__name__)


def create_error_response(message: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        'success': False,
        'message': message,
        'data': data or {}
    }


class WelfarePorterHandler(BaseActivityHandler):
    """
    Handles porter work for citizens earning food vouchers.
    Citizens transport goods for Consiglio dei Dieci or trusted nobles.
    """
    
    # Food payment rates based on cargo value/distance
    FOOD_PAYMENT_BASE = 3  # Base bread units
    FOOD_PAYMENT_PER_100M = 1  # Extra bread per 100m walked
    
    def can_handle(self, activity_type: str) -> bool:
        """Check if this handler can process the activity type."""
        return activity_type == "welfare_porter"
    
    def process(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a welfare porter activity.
        
        Expected activity data:
        {
            "employer": "ConsiglioDeiDieci",  # Who requested the work
            "cargo_type": "grain",
            "cargo_amount": 50,
            "from_building": "building_id_123",
            "to_building": "building_id_456",
            "payment_type": "food_voucher"
        }
        """
        try:
            log.info(f"{LogColors.HEADER}Processing welfare porter activity{LogColors.ENDC}")
            
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
            employer = activity_data.get('employer')
            cargo_type = activity_data.get('cargo_type')
            cargo_amount = activity_data.get('cargo_amount', 0)
            from_building_id = activity_data.get('from_building')
            to_building_id = activity_data.get('to_building')
            
            # Validate required fields
            if not all([employer, cargo_type, from_building_id, to_building_id]):
                return create_error_response("Missing required porter work data")
            
            # Check citizen carry capacity
            current_load = get_citizen_current_load(self.tables, citizen_username)
            carry_capacity = get_citizen_effective_carry_capacity(self.tables, citizen_username)
            available_capacity = carry_capacity - current_load
            
            if cargo_amount > available_capacity:
                return create_error_response(
                    f"Cannot carry {cargo_amount} units. Available capacity: {available_capacity}",
                    {"current_load": current_load, "carry_capacity": carry_capacity}
                )
            
            # Get building positions
            from_building = self._get_building_by_id(from_building_id)
            to_building = self._get_building_by_id(to_building_id)
            
            if not from_building or not to_building:
                return create_error_response("Invalid building IDs provided")
            
            from_pos = from_building['fields'].get('Position')
            to_pos = to_building['fields'].get('Position')
            
            # Check if citizen is at pickup location
            distance_to_pickup = _calculate_distance_meters(citizen_pos, from_pos)
            if distance_to_pickup > 50:
                return create_error_response(
                    f"Too far from pickup location. Move within 50m of {from_building['fields'].get('Name')}",
                    {"distance": round(distance_to_pickup)}
                )
            
            # Check if cargo exists at pickup location
            available_cargo = self._get_resource_at_building(from_building_id, cargo_type)
            if available_cargo < cargo_amount:
                return create_error_response(
                    f"Insufficient {cargo_type} at pickup location",
                    {"required": cargo_amount, "available": available_cargo}
                )
            
            # Calculate transport distance for food payment
            transport_distance = _calculate_distance_meters(from_pos, to_pos)
            
            # Pick up the cargo
            pickup_success = self._transfer_cargo_to_citizen(
                from_building_id, citizen_username, cargo_type, cargo_amount
            )
            
            if not pickup_success:
                return create_error_response("Failed to pick up cargo")
            
            # Calculate food payment
            food_payment = self._calculate_food_payment(cargo_amount, transport_distance)
            
            # Create voucher
            voucher = self._create_food_voucher(
                citizen_username, employer, food_payment, cargo_type, cargo_amount
            )
            
            # Chain delivery activity
            delivery_activity = self._create_delivery_activity(
                citizen_id, to_building_id, cargo_type, cargo_amount, voucher['id']
            )
            
            # Create notification
            self._create_notification(
                citizen_username,
                f"📦 You picked up **{cargo_amount} {cargo_type}** for {employer}. "
                f"Deliver to {to_building['fields'].get('Name')} to earn {food_payment} bread!",
                {
                    "event_type": "welfare_porter_pickup",
                    "employer": employer,
                    "cargo": f"{cargo_amount} {cargo_type}",
                    "destination": to_building['fields'].get('Name'),
                    "food_payment": food_payment
                }
            )
            
            log.info(f"{LogColors.SUCCESS}{citizen_name} picked up {cargo_amount} {cargo_type} "
                    f"for {employer}, will earn {food_payment} bread{LogColors.ENDC}")
            
            return {
                "success": True,
                "message": f"Picked up {cargo_amount} {cargo_type}. Deliver to earn {food_payment} bread",
                "data": {
                    "cargo_type": cargo_type,
                    "cargo_amount": cargo_amount,
                    "destination": to_building['fields'].get('Name'),
                    "food_payment": food_payment,
                    "voucher_id": voucher['id'],
                    "chained_activity": delivery_activity['id']
                }
            }
            
        except Exception as e:
            log.error(f"Error in welfare porter activity: {str(e)}")
            return create_error_response(f"Porter work failed: {str(e)}")
    
    def _get_building_by_id(self, building_id: str) -> Optional[Dict]:
        """Get building record by ID."""
        try:
            formula = f"{{BuildingId}}='{_escape_airtable_value(building_id)}'"
            records = self.tables['buildings'].all(formula=formula, max_records=1)
            return records[0] if records else None
        except Exception as e:
            log.error(f"Error fetching building {building_id}: {e}")
            return None
    
    def _get_resource_at_building(self, building_id: str, resource_type: str) -> float:
        """Get amount of resource at a building."""
        try:
            formula = (
                f"AND("
                f"{{Location}}='{_escape_airtable_value(building_id)}', "
                f"{{Type}}='{_escape_airtable_value(resource_type)}'"
                f")"
            )
            resources = self.tables['resources'].all(formula=formula)
            return sum(r['fields'].get('Quantity', 0) for r in resources)
        except Exception as e:
            log.error(f"Error checking resources: {e}")
            return 0
    
    def _transfer_cargo_to_citizen(self, building_id: str, citizen_username: str,
                                   resource_type: str, amount: float) -> bool:
        """Transfer cargo from building to citizen's inventory."""
        try:
            # Find resource record
            formula = (
                f"AND("
                f"{{Location}}='{_escape_airtable_value(building_id)}', "
                f"{{Type}}='{_escape_airtable_value(resource_type)}'"
                f")"
            )
            resources = self.tables['resources'].all(formula=formula, max_records=1)
            
            if not resources:
                return False
            
            resource_record = resources[0]
            current_quantity = resource_record['fields'].get('Quantity', 0)
            
            if current_quantity < amount:
                return False
            
            # Update building's resource
            new_quantity = current_quantity - amount
            if new_quantity > 0:
                self.tables['resources'].update(resource_record['id'], {
                    'Quantity': new_quantity
                })
            else:
                self.tables['resources'].delete(resource_record['id'])
            
            # Add to citizen's inventory
            self.tables['resources'].create({
                'Type': resource_type,
                'Quantity': amount,
                'Owner': citizen_username,
                'Location': citizen_username,  # On person
                'Quality': resource_record['fields'].get('Quality', 80)
            })
            
            return True
            
        except Exception as e:
            log.error(f"Error transferring cargo: {e}")
            return False
    
    def _calculate_food_payment(self, cargo_amount: float, distance: float) -> int:
        """Calculate food payment based on cargo and distance."""
        # Base payment + distance bonus
        base_payment = self.FOOD_PAYMENT_BASE
        distance_bonus = int(distance / 100) * self.FOOD_PAYMENT_PER_100M
        
        # Bonus for heavy loads
        if cargo_amount > 50:
            base_payment += 2
        
        total_payment = base_payment + distance_bonus
        return min(total_payment, 10)  # Cap at 10 bread
    
    def _create_food_voucher(self, citizen_username: str, employer: str,
                            food_amount: int, cargo_type: str, cargo_amount: float) -> Dict:
        """Create a food voucher for completed work."""
        voucher = {
            'id': f"voucher_{uuid.uuid4().hex[:8]}",
            'citizen': citizen_username,
            'employer': employer,
            'food_amount': food_amount,
            'food_type': 'bread',
            'valid_until': (datetime.now() + timedelta(days=1)).isoformat(),
            'work_description': f"Transported {cargo_amount} {cargo_type}",
            'created_at': datetime.now().isoformat()
        }
        
        # In production, save to vouchers table
        log.info(f"Created food voucher {voucher['id']} for {food_amount} bread")
        
        return voucher
    
    def _create_delivery_activity(self, citizen_id: str, destination_id: str,
                                 cargo_type: str, cargo_amount: float, voucher_id: str) -> Dict:
        """Create chained delivery activity."""
        try:
            # Create the delivery activity
            delivery_data = {
                'Type': 'welfare_porter_delivery',
                'Citizen': [citizen_id],
                'Status': 'pending',
                'Data': json.dumps({
                    'destination': destination_id,
                    'cargo_type': cargo_type,
                    'cargo_amount': cargo_amount,
                    'voucher_id': voucher_id
                }),
                'ChainedFrom': [activity['id']]  # Link to pickup activity
            }
            
            result = self.tables['activities'].create(delivery_data)
            return result
            
        except Exception as e:
            log.error(f"Error creating delivery activity: {e}")
            return {'id': 'error'}
    
    def _create_notification(self, citizen: str, content: str, details: Dict):
        """Create a notification for a citizen."""
        try:
            self.tables['notifications'].create({
                "Type": "welfare_porter",
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
    return WelfarePorterHandler()


# Activity processor wrapper
def handle_welfare_porter(tables: Dict[str, Any], activity_record: Dict[str, Any], 
                         building_type_defs: Any, resource_defs: Any,
                         api_base_url: Optional[str] = None) -> bool:
    """Process welfare porter activity."""
    handler = WelfarePorterHandler()
    handler.set_tables(tables)
    if api_base_url:
        handler.set_urls(api_base_url, api_base_url + "/transport")
    
    result = handler.process(activity_record)
    return result.get('success', False)
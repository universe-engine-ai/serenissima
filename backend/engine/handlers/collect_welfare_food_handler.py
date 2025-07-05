#!/usr/bin/env python3
"""
Collect Welfare Food Activity Handler
Allows citizens to redeem food vouchers earned through porter work at Consiglio market stalls

Activity Type: collect_welfare_food
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from backend.engine.handlers.base_handler import BaseActivityHandler
from backend.engine.utils.activity_helpers import LogColors
from backend.engine.utils.distance_helpers import calculate_distance, find_nearest_locations

log = logging.getLogger(__name__)


def create_error_response(message: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        'success': False,
        'message': message,
        'data': data or {}
    }


class CollectWelfareFoodHandler(BaseActivityHandler):
    """
    Handles food collection for citizens who completed porter work.
    Citizens redeem vouchers at Consiglio dei Dieci market stalls.
    """
    
    def can_handle(self, activity_type: str) -> bool:
        """Check if this handler can process the activity type."""
        return activity_type == "collect_welfare_food"
    
    def process(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a welfare food collection activity.
        
        Expected activity data:
        {
            "voucher": {
                "id": "voucher_123",
                "food_amount": 5,
                "food_type": "bread",
                "valid_until": "2024-12-25T12:00:00",
                "employer": "ConsiglioDeiDieci"
            }
        }
        """
        try:
            log.info(f"{LogColors.HEADER}Processing welfare food collection{LogColors.ENDC}")
            
            # Get citizen data
            citizen_id = activity['fields'].get('Citizen')[0]
            citizen = self.tables['citizens'].get(citizen_id)
            
            if not citizen:
                return create_error_response("Citizen not found", {"citizen_id": citizen_id})
            
            citizen_username = citizen['fields'].get('Username')
            citizen_name = f"{citizen['fields'].get('FirstName', '')} {citizen['fields'].get('LastName', '')}"
            citizen_pos = citizen['fields'].get('Position')
            
            if not citizen_pos:
                return create_error_response("Citizen has no position data", {"citizen": citizen_username})
            
            # Get voucher data
            activity_data = activity['fields'].get('Data', {})
            voucher = activity_data.get('voucher', {})
            
            if not voucher:
                return create_error_response("No voucher data provided")
            
            # Verify voucher validity
            if not self._verify_voucher(voucher, citizen_username):
                return create_error_response("Invalid or expired voucher", {"voucher_id": voucher.get('id')})
            
            # Find Consiglio market stalls
            consiglio_stalls = self._get_consiglio_market_stalls()
            if not consiglio_stalls:
                return create_error_response("No Consiglio market stalls available")
            
            # Find nearest stall
            nearest_stalls = find_nearest_locations(citizen_pos, consiglio_stalls, limit=1)
            if not nearest_stalls:
                return create_error_response("Could not find nearby market stall")
            
            nearest_stall, distance = nearest_stalls[0]
            
            # Check if citizen is at the stall (within 50 meters)
            if distance > 50:
                return create_error_response(
                    f"Too far from market stall. Move within 50m of {nearest_stall['name']}",
                    {"distance": round(distance), "stall": nearest_stall['name']}
                )
            
            # Get food details from voucher
            food_type = voucher.get('food_type', 'bread')
            food_amount = int(voucher.get('food_amount', 0))
            
            if food_amount <= 0:
                return create_error_response("Invalid food amount in voucher")
            
            # Check stall has enough food
            stall_resources = self._get_building_resources(nearest_stall['buildingId'], food_type)
            if stall_resources < food_amount:
                return create_error_response(
                    f"Market stall has insufficient {food_type}",
                    {"required": food_amount, "available": stall_resources}
                )
            
            # Transfer the food
            success = self._transfer_food_to_citizen(
                stall_building_id=nearest_stall['buildingId'],
                citizen_id=citizen_id,
                food_type=food_type,
                amount=food_amount
            )
            
            if not success:
                return create_error_response("Failed to transfer food resources")
            
            # Mark voucher as redeemed
            self._mark_voucher_redeemed(voucher['id'], citizen_username)
            
            # Create notification
            self._create_notification(
                citizen_username,
                f"🍞 You collected **{food_amount} {food_type}** from {nearest_stall['name']} "
                f"in exchange for your porter work!",
                {
                    "event_type": "welfare_food_collected",
                    "food_type": food_type,
                    "amount": food_amount,
                    "stall": nearest_stall['name']
                }
            )
            
            log.info(f"{LogColors.SUCCESS}{citizen_name} collected {food_amount} {food_type} "
                    f"from {nearest_stall['name']}{LogColors.ENDC}")
            
            return {
                "success": True,
                "message": f"Collected {food_amount} {food_type} from {nearest_stall['name']}",
                "data": {
                    "food_type": food_type,
                    "amount": food_amount,
                    "stall": nearest_stall['name'],
                    "voucher_id": voucher['id']
                }
            }
            
        except Exception as e:
            log.error(f"Error in welfare food collection: {str(e)}")
            return create_error_response(f"Food collection failed: {str(e)}")
    
    def _verify_voucher(self, voucher: Dict, citizen_username: str) -> bool:
        """Verify voucher is valid and not expired."""
        try:
            # Check expiration
            valid_until = voucher.get('valid_until')
            if valid_until:
                expiry = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
                if datetime.now() > expiry:
                    log.info(f"Voucher {voucher.get('id')} expired")
                    return False
            
            # Check if already redeemed (would be in a voucher tracking table)
            # For now, we'll accept the voucher if it has required fields
            required_fields = ['id', 'food_amount', 'employer']
            if not all(field in voucher for field in required_fields):
                return False
            
            return True
            
        except Exception as e:
            log.error(f"Error verifying voucher: {e}")
            return False
    
    def _get_consiglio_market_stalls(self) -> List[Dict]:
        """Get all market stalls owned or operated by Consiglio dei Dieci."""
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            # Query for Consiglio-controlled market stalls
            formula = (
                "AND("
                    "{Type}='market_stall', "
                    "OR("
                        "{Owner}='ConsiglioDeiDieci', "
                        "{RunBy}='ConsiglioDeiDieci'"
                    ")"
                ")"
            )
            
            records = self.tables['buildings'].all(formula=formula)
            
            stalls = []
            for record in records:
                fields = record['fields']
                if 'Position' in fields and fields.get('IsConstructed', 1) == 1:
                    stalls.append({
                        'buildingId': fields.get('BuildingId'),
                        'name': fields.get('Name', 'Market Stall'),
                        'position': fields.get('Position'),
                        'owner': fields.get('Owner'),
                        'runBy': fields.get('RunBy')
                    })
            
            log.info(f"Found {len(stalls)} Consiglio market stalls")
            return stalls
            
        except Exception as e:
            log.error(f"Error fetching Consiglio stalls: {e}")
            return []
    
    def _get_building_resources(self, building_id: str, resource_type: str) -> int:
        """Get amount of specific resource at a building."""
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            formula = (
                f"AND("
                f"{{Location}}='{_escape_airtable_value(building_id)}', "
                f"{{Type}}='{_escape_airtable_value(resource_type)}'"
                f")"
            )
            
            resources = self.tables['resources'].all(formula=formula)
            total_amount = sum(r['fields'].get('Quantity', 0) for r in resources)
            
            return total_amount
            
        except Exception as e:
            log.error(f"Error checking building resources: {e}")
            return 0
    
    def _transfer_food_to_citizen(self, stall_building_id: str, citizen_id: str, 
                                  food_type: str, amount: int) -> bool:
        """Transfer food from market stall to citizen."""
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            # Find the resource record at the stall
            formula = (
                f"AND("
                f"{{Location}}='{_escape_airtable_value(stall_building_id)}', "
                f"{{Type}}='{_escape_airtable_value(food_type)}'"
                f")"
            )
            
            resources = self.tables['resources'].all(formula=formula, max_records=1)
            if not resources:
                log.error(f"No {food_type} found at stall {stall_building_id}")
                return False
            
            resource_record = resources[0]
            current_quantity = resource_record['fields'].get('Quantity', 0)
            
            if current_quantity < amount:
                log.error(f"Insufficient {food_type}: need {amount}, have {current_quantity}")
                return False
            
            # Get citizen data for the transfer
            citizen = self.tables['citizens'].get(citizen_id)
            citizen_username = citizen['fields'].get('Username')
            
            # Update resource quantity at stall
            new_quantity = current_quantity - amount
            if new_quantity > 0:
                self.tables['resources'].update(resource_record['id'], {
                    'Quantity': new_quantity
                })
            else:
                # Delete if quantity reaches 0
                self.tables['resources'].delete(resource_record['id'])
            
            # Create new resource record for citizen
            self.tables['resources'].create({
                'Type': food_type,
                'Quantity': amount,
                'Owner': citizen_username,
                'Location': citizen_username,  # Resources on person use username as location
                'Quality': resource_record['fields'].get('Quality', 80)
            })
            
            log.info(f"Transferred {amount} {food_type} to {citizen_username}")
            return True
            
        except Exception as e:
            log.error(f"Error transferring food: {e}")
            return False
    
    def _mark_voucher_redeemed(self, voucher_id: str, citizen_username: str):
        """Mark voucher as redeemed. In production, this would update a voucher tracking table."""
        try:
            # Log the redemption
            log.info(f"Voucher {voucher_id} redeemed by {citizen_username}")
            
            # In a full implementation, we would:
            # 1. Update a VOUCHERS table to mark as redeemed
            # 2. Record redemption timestamp
            # 3. Prevent double redemption
            
            # For now, we just log it
            
        except Exception as e:
            log.error(f"Error marking voucher redeemed: {e}")
    
    def _create_notification(self, citizen: str, content: str, details: Dict):
        """Create a notification for a citizen."""
        try:
            self.tables['notifications'].create({
                "Type": "welfare_food",
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
    return CollectWelfareFoodHandler()


# Activity processor wrapper
def handle_collect_welfare_food(tables: Dict[str, Any], activity_record: Dict[str, Any], 
                               building_type_defs: Any, resource_defs: Any,
                               api_base_url: Optional[str] = None) -> bool:
    """Process collect welfare food activity."""
    handler = CollectWelfareFoodHandler()
    handler.set_tables(tables)
    if api_base_url:
        handler.set_urls(api_base_url, api_base_url + "/transport")
    
    result = handler.process(activity_record)
    return result.get('success', False)
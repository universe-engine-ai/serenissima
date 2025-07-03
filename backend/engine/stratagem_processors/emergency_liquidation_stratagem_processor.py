"""
Stratagem Processor for "emergency_liquidation".

This processor:
1. Fetches all resources in the executor's inventory.
2. For each resource:
    a. Determines the average market rate.
    b. Calculates the liquidation price based on the stratagem variant.
    c. Creates a short-term public_sell contract for the resource.
"""

import logging
import json
import os
import requests
import pytz
import statistics # For mean
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    get_citizen_inventory_details, # To get citizen's resources
    get_building_record, # To find a sales point
    get_citizen_businesses_run # To find a sales point
)
# Import the discount percentages from the creator
from backend.engine.stratagem_creators.emergency_liquidation_stratagem_creator import VALID_VARIANTS as LIQUIDATION_VARIANTS

log = logging.getLogger(__name__)

def _get_average_market_price(
    tables: Dict[str, Any],
    resource_type_id: str,
    exclude_seller_username: str,
    now_utc_dt: datetime
) -> Optional[float]:
    """Calculates the average market price for a resource, excluding the specified seller."""
    prices = []
    formula = (
        f"AND({{ResourceType}}='{_escape_airtable_value(resource_type_id)}', "
        f"{{Type}}='public_sell', {{Status}}='active', {{TargetAmount}}>0, "
        f"{{Seller}}!='{_escape_airtable_value(exclude_seller_username)}', "
        f"IS_AFTER({{EndAt}}, '{now_utc_dt.isoformat()}'))"
    )
    try:
        contracts = tables['contracts'].all(formula=formula, fields=['PricePerResource'])
        for contract in contracts:
            price = contract['fields'].get('PricePerResource')
            if price is not None:
                prices.append(float(price))
        
        if prices:
            avg_price = statistics.mean(prices)
            log.info(f"{LogColors.PROCESS}Average market price for {resource_type_id} (excluding {exclude_seller_username}): {avg_price:.2f} from {len(prices)} contracts.{LogColors.ENDC}")
            return avg_price
        else:
            log.info(f"{LogColors.PROCESS}No active public sell contracts found for {resource_type_id} (excluding {exclude_seller_username}) to determine average price.{LogColors.ENDC}")
            return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching market prices for {resource_type_id}: {e}{LogColors.ENDC}")
        return None

def _find_citizen_sales_building(tables: Dict[str, Any], citizen_username: str) -> Optional[str]:
    """Finds a suitable building for the citizen to sell from (e.g., a business they run)."""
    businesses_run = get_citizen_businesses_run(tables, citizen_username)
    if businesses_run:
        # Prefer a shop or a building that typically sells goods.
        # For simplicity, take the first one found. More complex logic could be added.
        first_business_id = businesses_run[0]['fields'].get('BuildingId')
        if first_business_id:
            log.info(f"{LogColors.PROCESS}Found sales building '{first_business_id}' for {citizen_username}.{LogColors.ENDC}")
            return first_business_id
    
    # Fallback: check if they own their home and if it can be a sales point (conceptual)
    # For now, if no business building, we might not be able to create public_sell contracts easily.
    # The manage_public_sell_contract activity usually requires a SellerBuilding.
    log.warning(f"{LogColors.WARNING}No primary business building found for {citizen_username} to conduct liquidation sales from.{LogColors.ENDC}")
    return None


def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None,
    building_type_defs: Optional[Dict[str, Any]] = None,
    api_base_url: Optional[str] = None
) -> bool:
    stratagem_fields = stratagem_record['fields']
    stratagem_id = stratagem_fields.get('StratagemId', stratagem_record['id'])
    executed_by = stratagem_fields.get('ExecutedBy')
    variant_name = stratagem_fields.get('Variant')

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'emergency_liquidation' stratagem {stratagem_id} for {executed_by}, Variant: {variant_name}.{LogColors.ENDC}")

    if not executed_by or not variant_name or variant_name not in LIQUIDATION_VARIANTS:
        log.error(f"{LogColors.FAIL}Stratagem {stratagem_id} missing ExecutedBy or invalid Variant. Cannot process.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'Missing ExecutedBy or invalid Variant.'})
        return False

    variant_details = LIQUIDATION_VARIANTS[variant_name]
    discount_factor = 1.0 - variant_details["discount_percentage"]
    # Contract duration can be shorter than stratagem duration, e.g., 1 day for quick sale
    contract_duration_hours = 24 
    now_utc_dt = datetime.now(pytz.utc)
    contract_end_at_iso = (now_utc_dt + timedelta(hours=contract_duration_hours)).isoformat()

    # Find a building for the citizen to sell from
    seller_building_id = _find_citizen_sales_building(tables, executed_by)
    if not seller_building_id:
        log.warning(f"{LogColors.WARNING}Stratagem {stratagem_id}: No suitable sales building found for {executed_by}. Cannot create public sell contracts. Stratagem may be ineffective.{LogColors.ENDC}")
        # Update notes, but don't fail the stratagem entirely, it might become effective if a building is acquired.
        current_notes = stratagem_fields.get('Notes', "")
        new_note = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] No sales building found. Liquidation pending suitable location."
        tables['stratagems'].update(stratagem_record['id'], {'Notes': f"{current_notes}\n{new_note}".strip()})
        return True # Stratagem is valid, just can't act now.

    # Get citizen's inventory
    inventory_items = get_citizen_inventory_details(tables, executed_by)
    if not inventory_items:
        log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}: {executed_by} has no items in inventory to liquidate.{LogColors.ENDC}")
        # Mark as executed if nothing to do, or let it expire.
        # For now, let it remain active, inventory might change.
        current_notes = stratagem_fields.get('Notes', "")
        new_note = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] Inventory empty. No items to liquidate."
        tables['stratagems'].update(stratagem_record['id'], {'Notes': f"{current_notes}\n{new_note}".strip()})
        return True

    python_engine_internal_url = os.getenv("BACKEND_BASE_URL", "http://localhost:10000")
    activity_creation_endpoint = f"{python_engine_internal_url}/api/v1/engine/try-create-activity"
    
    contracts_created_count = 0
    all_processing_notes: List[str] = []

    for item in inventory_items:
        resource_type_id = item.get('ResourceId')
        amount_to_sell = item.get('Amount', 0.0)

        if not resource_type_id or amount_to_sell <= 0.01: # Ignore tiny amounts
            continue

        avg_market_price = _get_average_market_price(tables, resource_type_id, executed_by, now_utc_dt)
        
        liquidation_price: float
        if avg_market_price is not None and avg_market_price > 0:
            liquidation_price = round(avg_market_price * discount_factor, 2)
        else:
            # Fallback: if no market price, use resource definition's importPrice or a default
            resource_def = resource_defs.get(resource_type_id, {}) if resource_defs else {}
            fallback_price = float(resource_def.get('importPrice', 1.0)) # Default to 1 if no importPrice
            liquidation_price = round(fallback_price * discount_factor, 2)
            all_processing_notes.append(f"No market price for {resource_type_id}, used fallback {fallback_price:.2f} for liquidation price.")
            log.info(f"{LogColors.PROCESS}No market price for {resource_type_id}. Using fallback {fallback_price:.2f}, liquidation price: {liquidation_price:.2f}.{LogColors.ENDC}")

        if liquidation_price <= 0.01: # Ensure price is not zero or negative
            liquidation_price = 0.01
            all_processing_notes.append(f"Adjusted liquidation price for {resource_type_id} to 0.01.")

        # Create manage_public_sell_contract activity
        activity_params = {
            "resourceType": resource_type_id,
            "pricePerResource": liquidation_price,
            "targetAmount": amount_to_sell,
            "sellerBuildingId": seller_building_id, # Citizen's sales point
            "status": "active",
            "endAt": contract_end_at_iso, # Short duration contract
            "notes": f"Emergency Liquidation via Stratagem {stratagem_id}. Price: {liquidation_price:.2f}.",
            "strategy": "stratagem_emergency_liquidation"
        }
        
        payload_for_activity_creation = {
            "citizenUsername": executed_by,
            "activityType": "manage_public_sell_contract",
            "activityParameters": activity_params
        }

        log.info(f"{LogColors.PROCESS}Attempting to create 'manage_public_sell_contract' for {executed_by} to sell {amount_to_sell} of {resource_type_id} at {liquidation_price:.2f} from {seller_building_id}. Payload: {json.dumps(payload_for_activity_creation, indent=2)}{LogColors.ENDC}")
        try:
            response = requests.post(activity_creation_endpoint, json=payload_for_activity_creation, timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("success"):
                log.info(f"{LogColors.OKGREEN}Successfully initiated 'manage_public_sell_contract' for {resource_type_id}. Activity: {response_data.get('activity', {}).get('ActivityId', 'N/A')}{LogColors.ENDC}")
                contracts_created_count += 1
                all_processing_notes.append(f"Created sell contract for {amount_to_sell:.2f} {resource_type_id} at {liquidation_price:.2f} Ducats each.")
            else:
                error_msg = response_data.get('message', 'Unknown error')
                log.error(f"{LogColors.FAIL}Failed to initiate 'manage_public_sell_contract' for {resource_type_id}. Error: {error_msg}{LogColors.ENDC}")
                all_processing_notes.append(f"Failed contract for {resource_type_id}: {error_msg}")
        
        except requests.exceptions.RequestException as e_req:
            log.error(f"{LogColors.FAIL}RequestException creating contract for {resource_type_id}: {e_req}{LogColors.ENDC}")
            all_processing_notes.append(f"RequestException for {resource_type_id}: {str(e_req)}")
        except Exception as e_inner:
            log.error(f"{LogColors.FAIL}Unexpected error creating contract for {resource_type_id}: {e_inner}{LogColors.ENDC}")
            all_processing_notes.append(f"Unexpected error for {resource_type_id}: {str(e_inner)}")

    # Update stratagem notes
    final_notes_str = stratagem_fields.get('Notes', "")
    current_cycle_notes = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] Attempted liquidation. Contracts created: {contracts_created_count}."
    if all_processing_notes:
        current_cycle_notes += " Details: " + "; ".join(all_processing_notes)
    
    updated_notes = f"{final_notes_str}\n{current_cycle_notes}".strip()
    
    update_payload = {'Notes': updated_notes}
    if contracts_created_count > 0 and not stratagem_fields.get('ExecutedAt'):
        update_payload['ExecutedAt'] = now_utc_dt.isoformat()
        # This stratagem is effectively "executed" once it lists items.
        # It doesn't need to stay active to re-list them unless designed that way.
        # For now, assume one-shot listing.
        update_payload['Status'] = 'executed' 
        log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} marked as 'executed' after creating {contracts_created_count} contracts.{LogColors.ENDC}")
    elif not inventory_items and not stratagem_fields.get('ExecutedAt'): # No items from the start
        update_payload['ExecutedAt'] = now_utc_dt.isoformat()
        update_payload['Status'] = 'executed'
        log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} marked as 'executed' as inventory was empty.{LogColors.ENDC}")


    tables['stratagems'].update(stratagem_record['id'], update_payload)
    log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} (emergency_liquidation) processing complete for this cycle.{LogColors.ENDC}")
    
    return True # Processor ran successfully, even if no contracts were made due to conditions.

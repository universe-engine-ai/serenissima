"""
Stratagem Processor for "coordinate_pricing".

This processor adjusts the prices of the executing citizen's sell contracts
to match the average price of target contracts for a specific resource.
"""

import logging
import json
import os
import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List, Union
import statistics # For calculating mean

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors,
    get_building_record,
    get_citizen_record,
    get_resource_types_from_api # To get resource names if needed
)
from backend.engine.utils.relationship_helpers import update_trust_score_for_activity

# Re-use helper functions from undercut_stratagem_processor if applicable, or define new ones.
# For distinct resources sold by building/citizen:
from backend.engine.stratagem_processors.undercut_stratagem_processor import (
    _get_distinct_resources_sold_by_building,
    _get_distinct_resources_sold_by_citizen
)


log = logging.getLogger(__name__)

def get_reference_prices(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_type_to_target: str,
    executed_by_username: str # To exclude self if targeting general market
) -> List[float]:
    """
    Finds the prices of target entities for a specific resource type.
    - If TargetCitizen is set, get prices from that citizen.
    - Else if TargetBuilding is set, get prices from that building.
    - Else (general market), get prices from all other sellers.
    Returns a list of reference prices.
    """
    target_citizen = stratagem_record['fields'].get('TargetCitizen')
    target_building_id = stratagem_record['fields'].get('TargetBuilding')

    reference_prices: List[float] = []
    now_iso = datetime.now(pytz.utc).isoformat()
    
    base_contract_formula_parts = [
        f"{{ResourceType}} = '{_escape_airtable_value(resource_type_to_target)}'",
        f"{{Type}} = 'public_sell'",
        f"{{Status}} = 'active'",
        f"{{TargetAmount}} > 0",
        f"IS_BEFORE({{CreatedAt}}, '{now_iso}')", 
        f"IS_AFTER({{EndAt}}, '{now_iso}')"      
    ]

    specific_target_filter = ""
    if target_citizen:
        # Targeting a specific citizen's prices
        specific_target_filter = f"{{Seller}} = '{_escape_airtable_value(target_citizen)}'"
    elif target_building_id:
        # Targeting a specific building's prices
        specific_target_filter = f"{{SellerBuilding}} = '{_escape_airtable_value(target_building_id)}'"
    else:
        # General market: exclude the stratagem executor
        base_contract_formula_parts.append(f"{{Seller}} != '{_escape_airtable_value(executed_by_username)}'")
    
    if specific_target_filter:
        final_formula = f"AND({', '.join(base_contract_formula_parts)}, {specific_target_filter})"
    else: # General market competition (excluding self)
        final_formula = f"AND({', '.join(base_contract_formula_parts)})"
        
    log.info(f"{LogColors.PROCESS}Finding reference prices for {resource_type_to_target} with formula: {final_formula}{LogColors.ENDC}")
    try:
        reference_contracts = tables['contracts'].all(
            formula=final_formula,
            fields=['PricePerResource', 'Seller', 'SellerBuilding']
        )
        for contract in reference_contracts:
            price = contract['fields'].get('PricePerResource')
            if price is not None:
                reference_prices.append(float(price))
        log.info(f"{LogColors.PROCESS}Found {len(reference_prices)} reference prices for {resource_type_to_target}. Prices: {reference_prices}{LogColors.ENDC}")
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching reference contracts for stratagem {stratagem_record['fields'].get('StratagemId')}: {e}{LogColors.ENDC}")
    
    return reference_prices

def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None,
    building_type_defs: Optional[Dict[str, Any]] = None,
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes a "coordinate_pricing" stratagem.
    Adjusts the executing citizen's sell prices for target resource(s) to match the average of reference prices.
    """
    stratagem_id = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    python_engine_internal_url = os.getenv("BACKEND_BASE_URL", "http://localhost:10000")
    activity_creation_endpoint = f"{python_engine_internal_url}/api/v1/engine/try-create-activity"
    executed_by = stratagem_record['fields'].get('ExecutedBy')

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'coordinate_pricing' stratagem {stratagem_id} for {executed_by}{LogColors.ENDC}")

    if not executed_by:
        log.error(f"{LogColors.FAIL}Stratagem {stratagem_id} missing ExecutedBy. Cannot process.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'Missing ExecutedBy.'})
        return False

    # Determine notification recipient and relationship target
    notification_recipient_username: Optional[str] = None
    target_citizen_for_relationship = stratagem_record['fields'].get('TargetCitizen')
    target_building_id_for_relationship = stratagem_record['fields'].get('TargetBuilding')

    if target_citizen_for_relationship:
        notification_recipient_username = target_citizen_for_relationship
    elif target_building_id_for_relationship:
        target_building_record = get_building_record(tables, target_building_id_for_relationship)
        if target_building_record:
            notification_recipient_username = target_building_record['fields'].get('RunBy')
            if not notification_recipient_username: # Also check Owner if RunBy is not set
                notification_recipient_username = target_building_record['fields'].get('Owner')

    # Determine which resource types to process
    resource_types_to_process: List[str] = []
    initial_target_resource_type = stratagem_record['fields'].get('TargetResourceType')

    if initial_target_resource_type:
        resource_types_to_process.append(initial_target_resource_type)
    else:
        # No specific resource type, so find all resources the executor is currently selling
        log.info(f"{LogColors.PROCESS}No TargetResourceType specified for stratagem {stratagem_id}. Finding all resources sold by {executed_by}.{LogColors.ENDC}")
        
        now_iso_for_seller_check = datetime.now(pytz.utc).isoformat()
        seller_contracts_formula = (
            f"AND({{Seller}} = '{_escape_airtable_value(executed_by)}', "
            f"{{Type}} = 'public_sell', "
            f"{{Status}} = 'active', "
            f"IS_BEFORE({{CreatedAt}}, '{now_iso_for_seller_check}'), "
            f"IS_AFTER({{EndAt}}, '{now_iso_for_seller_check}'))"
        )
        try:
            executor_sell_contracts = tables['contracts'].all(formula=seller_contracts_formula, fields=['ResourceType'])
            distinct_resources_sold = set()
            for contract in executor_sell_contracts:
                res_type = contract['fields'].get('ResourceType')
                if res_type:
                    distinct_resources_sold.add(res_type)
            resource_types_to_process = list(distinct_resources_sold)
            if not resource_types_to_process:
                log.warning(f"{LogColors.WARNING}Stratagem {stratagem_id}: {executed_by} is not currently selling any resources. Cannot coordinate prices.{LogColors.ENDC}")
                all_notes_for_stratagem_update: List[str] = [f"{executed_by} is not selling any resources."]
                final_notes_str = stratagem_record['fields'].get('Notes', "")
                if all_notes_for_stratagem_update:
                    new_notes_joined = "\n".join(all_notes_for_stratagem_update)
                    final_notes_str = f"{final_notes_str}\n{new_notes_joined}".strip() if final_notes_str else new_notes_joined.strip()
                tables['stratagems'].update(stratagem_record['id'], {'Notes': final_notes_str, 'Status': 'executed'}) # Mark as executed as there's nothing to do
                return True # Stratagem itself didn't fail, just had no effect
        except Exception as e_fetch_seller_res:
            log.error(f"{LogColors.FAIL}Error fetching resources sold by {executed_by} for stratagem {stratagem_id}: {e_fetch_seller_res}{LogColors.ENDC}")
            tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f"Error fetching executor's resources: {e_fetch_seller_res}"})
            return False
    
    log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id} will attempt to coordinate prices for resource(s): {', '.join(resource_types_to_process)}.{LogColors.ENDC}")

    overall_success_for_stratagem = True
    all_activities_initiated_count = 0
    all_notes_for_stratagem_update: List[str] = [] # Initialize here if not already

    if not resource_types_to_process: # Handles case where executor sells nothing when TargetResourceType is blank
        log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}: No resources to process for price coordination by {executed_by}.{LogColors.ENDC}")
        # Notes might have been updated already if this was due to executor selling nothing.
        # If it was due to a specific TargetResourceType not being sold by executor, that's handled below.
        # Ensure the stratagem is marked as executed if no actions are taken.
        current_stratagem_status = stratagem_record['fields'].get('Status')
        if current_stratagem_status == 'active': # Only update if still active
             tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': stratagem_record['fields'].get('Notes', "") + "\nNo resources found to coordinate."})
        return True


    for current_resource_type_to_target in resource_types_to_process:
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}--- Processing coordinate_pricing for resource: {current_resource_type_to_target} (Stratagem: {stratagem_id}) ---{LogColors.ENDC}")
        
        reference_prices = get_reference_prices(tables, stratagem_record, current_resource_type_to_target, executed_by)

        if not reference_prices:
            log.info(f"{LogColors.PROCESS}No reference prices found for {current_resource_type_to_target} for stratagem {stratagem_id}. No price adjustment for this resource.{LogColors.ENDC}")
            all_notes_for_stratagem_update.append(f"No reference prices for {current_resource_type_to_target}.")
            continue

        avg_reference_price = statistics.mean(reference_prices)
        target_price = round(avg_reference_price, 2)

        log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}, Resource {current_resource_type_to_target}: Avg reference price {avg_reference_price:.2f}. Target coordinated price: {target_price:.2f}.{LogColors.ENDC}")

        if target_price <= 0:
            log.warning(f"{LogColors.WARNING}Stratagem {stratagem_id}, Resource {current_resource_type_to_target}: Calculated target price {target_price:.2f} is zero or negative. Setting to 0.01.{LogColors.ENDC}")
            target_price = 0.01
        
        now_iso = datetime.now(pytz.utc).isoformat()
        citizen_contracts_formula = (
            f"AND({{Seller}} = '{_escape_airtable_value(executed_by)}', "
            f"{{ResourceType}} = '{_escape_airtable_value(current_resource_type_to_target)}', "
            f"{{Type}} = 'public_sell', "
            f"{{Status}} = 'active', "
            f"IS_BEFORE({{CreatedAt}}, '{now_iso}'), "
            f"IS_AFTER({{EndAt}}, '{now_iso}'))"
        )
        
        activities_initiated_for_this_resource = 0
        
        try:
            citizen_sell_contracts = tables['contracts'].all(formula=citizen_contracts_formula)
            if not citizen_sell_contracts:
                log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}: {executed_by} has no active public_sell contracts for {current_resource_type_to_target} to apply coordination.{LogColors.ENDC}")
                all_notes_for_stratagem_update.append(f"No active sell contracts for {current_resource_type_to_target} by {executed_by}.")
                continue 

            for contract in citizen_sell_contracts:
                contract_airtable_id = contract['id']
                contract_custom_id = contract['fields'].get('ContractId', contract_airtable_id)
                current_price = contract['fields'].get('PricePerResource')

                if current_price is None or abs(float(current_price) - target_price) > 0.001:
                    log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}: Initiating price update for contract {contract_custom_id}. Old price: {current_price}, New target price: {target_price:.2f}.{LogColors.ENDC}")
                    
                    activity_params = {
                        "contractId": contract_custom_id,
                        "pricePerResource": target_price,
                        "resourceType": contract['fields'].get('ResourceType'),
                        "sellerBuildingId": contract['fields'].get('SellerBuilding'),
                        "targetAmount": contract['fields'].get('TargetAmount'),
                        "status": "active",
                        "notes": f"Price adjustment via Coordinate Pricing Stratagem {stratagem_id}.",
                        "strategy": "stratagem_coordinate_price_adjustment"
                    }
                    
                    payload_for_activity_creation = {
                        "citizenUsername": executed_by,
                        "activityType": "manage_public_sell_contract",
                        "activityParameters": activity_params
                    }

                    try:
                        response = requests.post(activity_creation_endpoint, json=payload_for_activity_creation, timeout=30)
                        response.raise_for_status()
                        response_data = response.json()

                        if response_data.get("success"):
                            log.info(f"{LogColors.OKGREEN}Successfully initiated 'manage_public_sell_contract' activity for contract {contract_custom_id} (Resource: {current_resource_type_to_target}). Activity: {response_data.get('activity', {}).get('ActivityId', 'N/A')}{LogColors.ENDC}")
                            activities_initiated_for_this_resource += 1
                            all_notes_for_stratagem_update.append(f"Initiated price update for {current_resource_type_to_target} (contract {contract_custom_id}) to {target_price:.2f}.")
                        else:
                            log.error(f"{LogColors.FAIL}Failed to initiate 'manage_public_sell_contract' activity for contract {contract_custom_id}. Error: {response_data.get('message', 'Unknown error')}{LogColors.ENDC}")
                            overall_success_for_stratagem = False
                            all_notes_for_stratagem_update.append(f"Failed price update for {current_resource_type_to_target} (contract {contract_custom_id}). Error: {response_data.get('message', 'Unknown')}")
                    
                    except requests.exceptions.RequestException as e_req:
                        log.error(f"{LogColors.FAIL}RequestException for contract {contract_custom_id}: {e_req}{LogColors.ENDC}")
                        overall_success_for_stratagem = False
                        all_notes_for_stratagem_update.append(f"RequestException for {current_resource_type_to_target} (contract {contract_custom_id}): {str(e_req)}")
                    except Exception as e_inner:
                        log.error(f"{LogColors.FAIL}Unexpected error for contract {contract_custom_id}: {e_inner}{LogColors.ENDC}")
                        overall_success_for_stratagem = False
                        all_notes_for_stratagem_update.append(f"Unexpected error for {current_resource_type_to_target} (contract {contract_custom_id}): {str(e_inner)}")
                else:
                    log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}: Contract {contract_custom_id} for {current_resource_type_to_target} already at target price {target_price:.2f}. No update needed.{LogColors.ENDC}")
                    all_notes_for_stratagem_update.append(f"Contract {contract_custom_id} ({current_resource_type_to_target}) already at target price.")

        except Exception as e_outer_loop:
            log.error(f"{LogColors.FAIL}Error processing {executed_by}'s contracts for resource {current_resource_type_to_target} (Stratagem {stratagem_id}): {e_outer_loop}{LogColors.ENDC}")
            all_notes_for_stratagem_update.append(f"Error processing contracts for {current_resource_type_to_target}: {str(e_outer_loop)}")
            overall_success_for_stratagem = False
        
        all_activities_initiated_count += activities_initiated_for_this_resource
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}--- Finished coordinate_pricing for resource: {current_resource_type_to_target} (Stratagem: {stratagem_id}) ---{LogColors.ENDC}")

    if all_activities_initiated_count == 0:
        log.warning(f"{LogColors.WARNING}Stratagem {stratagem_id}: No price update activities were initiated for any targeted resource. Stratagem considered ineffective for this cycle.{LogColors.ENDC}")
        all_notes_for_stratagem_update.append("No price update activities initiated (no eligible contracts or no reference prices found).")
        # overall_success_for_stratagem remains True.

    final_notes_str = stratagem_record['fields'].get('Notes', "")
    if all_notes_for_stratagem_update:
        new_notes_joined = "\n".join(all_notes_for_stratagem_update)
        final_notes_str = f"{final_notes_str}\n{new_notes_joined}".strip() if final_notes_str else new_notes_joined.strip()
    
    update_payload_stratagem = {}
    if final_notes_str != stratagem_record['fields'].get('Notes', ""):
        update_payload_stratagem['Notes'] = final_notes_str

    if all_activities_initiated_count > 0:
        if not stratagem_record['fields'].get('ExecutedAt'):
            update_payload_stratagem['ExecutedAt'] = datetime.now(pytz.utc).isoformat()
        
        notification_resource_target_text = f"resource '{initial_target_resource_type}'" if initial_target_resource_type else "all their sellable resources"
        if notification_recipient_username and notification_recipient_username != executed_by:
            notification_content = (
                f"Citizen {executed_by} has initiated a 'coordinate_pricing' stratagem "
                f"affecting prices for {notification_resource_target_text}. "
                f"Their prices are now aligned with yours or the market."
            )
            if target_citizen_for_relationship: # TargetCitizen is from stratagem_record['fields']
                notification_content += f" You were the reference for this coordination."
            elif target_building_id_for_relationship: # TargetBuilding is from stratagem_record['fields']
                notification_content += f" Your building '{target_building_id_for_relationship}' was the reference."

            try:
                tables['notifications'].create({
                    "Citizen": notification_recipient_username,
                    "Type": "stratagem_alert",
                    "Content": notification_content,
                    "Asset": stratagem_id,
                    "AssetType": "stratagem",
                    "Status": "unread"
                })
                log.info(f"{LogColors.OKGREEN}Notification sent to {notification_recipient_username} regarding stratagem {stratagem_id}.{LogColors.ENDC}")
            except Exception as e_notify:
                log.error(f"{LogColors.FAIL}Failed to send notification for stratagem {stratagem_id}: {e_notify}{LogColors.ENDC}")

            # Trust impact: positive if coordinating with a specific target, neutral otherwise
            trust_impact = 0.0
            if target_citizen_for_relationship or target_building_id_for_relationship:
                trust_impact = 2.0 # Small positive impact for coordination
            
            if trust_impact != 0.0:
                update_trust_score_for_activity(
                    tables, executed_by, notification_recipient_username, trust_impact,
                    activity_type_for_notes=f"stratagem_coordinate_pricing",
                    success=True, 
                    notes_detail=f"target_{initial_target_resource_type or target_building_id_for_relationship or target_citizen_for_relationship}",
                    activity_record_for_kinos=stratagem_record
                )
                log.info(f"{LogColors.PROCESS}Relationship between {executed_by} and {notification_recipient_username} impacted by {trust_impact} due to stratagem {stratagem_id}.{LogColors.ENDC}")
        else:
            log.info(f"{LogColors.PROCESS}No specific notification recipient for stratagem {stratagem_id} or recipient is self. Skipping notification/relationship update.{LogColors.ENDC}")
    
    if update_payload_stratagem:
        try:
            tables['stratagems'].update(stratagem_record['id'], update_payload_stratagem)
            log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} record updated.{LogColors.ENDC}")
        except Exception as e_update:
            log.error(f"{LogColors.FAIL}Failed to update stratagem {stratagem_id}: {e_update}{LogColors.ENDC}")
            # This doesn't necessarily mean the stratagem's core logic failed.

    return overall_success_for_stratagem

"""
Stratagem Processor for "undercut".

This processor adjusts the prices of the executing citizen's sell contracts
to be a certain percentage below the competition.
"""

import logging
import json
import os # Ajout de os pour getenv
import requests # Ajout de requests pour les appels API
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors,
    get_building_record,
    get_citizen_record,
    get_resource_types_from_api # To get resource names if needed
)
# Import relationship helper
from backend.engine.utils.relationship_helpers import update_trust_score_for_activity

log = logging.getLogger(__name__)

UNDERCUT_PERCENTAGES = {
    "Mild": 0.10,       # 10%
    "Standard": 0.15,   # 15%
    "Aggressive": 0.20  # 20%
}

def _get_distinct_resources_sold_by_building(tables: Dict[str, Any], building_id: str, exclude_seller_username: Optional[str] = None) -> List[str]:
    """Helper to find distinct resource types sold by a specific building."""
    now_iso = datetime.now(pytz.utc).isoformat()
    formula_parts = [
        f"{{Type}} = 'public_sell'",
        f"{{Status}} = 'active'",
        f"{{SellerBuilding}} = '{_escape_airtable_value(building_id)}'",
        f"{{TargetAmount}} > 0",
        f"IS_BEFORE({{CreatedAt}}, '{now_iso}')",
        f"IS_AFTER({{EndAt}}, '{now_iso}')"
    ]
    if exclude_seller_username: # Should not be needed if we are targeting this building specifically
        formula_parts.append(f"{{Seller}} != '{_escape_airtable_value(exclude_seller_username)}'")
    
    formula = f"AND({', '.join(formula_parts)})"
    try:
        contracts = tables['contracts'].all(formula=formula, fields=['ResourceType'])
        resource_types = sorted(list(set(c['fields']['ResourceType'] for c in contracts if 'ResourceType' in c['fields'])))
        log.info(f"{LogColors.PROCESS}Building {building_id} sells resources: {resource_types}{LogColors.ENDC}")
        return resource_types
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching resources sold by building {building_id}: {e}{LogColors.ENDC}")
        return []

def _get_distinct_resources_sold_by_citizen(tables: Dict[str, Any], citizen_username: str, exclude_seller_username: Optional[str] = None) -> List[str]:
    """Helper to find distinct resource types sold by a specific citizen."""
    now_iso = datetime.now(pytz.utc).isoformat()
    formula_parts = [
        f"{{Type}} = 'public_sell'",
        f"{{Status}} = 'active'",
        f"{{Seller}} = '{_escape_airtable_value(citizen_username)}'",
        f"{{TargetAmount}} > 0",
        f"IS_BEFORE({{CreatedAt}}, '{now_iso}')",
        f"IS_AFTER({{EndAt}}, '{now_iso}')"
    ]
    # exclude_seller_username is typically the one executing the stratagem, so if we are targeting
    # this citizen, we *want* their contracts. If exclude_seller_username is the same as citizen_username,
    # this check might be redundant or counterproductive depending on the intent.
    # For finding what a target citizen sells, we don't exclude anyone.
    # The exclusion happens in get_competition_prices.

    formula = f"AND({', '.join(formula_parts)})"
    try:
        contracts = tables['contracts'].all(formula=formula, fields=['ResourceType'])
        resource_types = sorted(list(set(c['fields']['ResourceType'] for c in contracts if 'ResourceType' in c['fields'])))
        log.info(f"{LogColors.PROCESS}Citizen {citizen_username} sells resources: {resource_types}{LogColors.ENDC}")
        return resource_types
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching resources sold by citizen {citizen_username}: {e}{LogColors.ENDC}")
        return []

def get_competition_prices(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    executed_by_username: str
) -> List[float]:
    """
    Finds the prices of competitors based on the stratagem's targets.
    Returns a list of competitor prices.
    """
    target_citizen = stratagem_record['fields'].get('TargetCitizen')
    target_building_id = stratagem_record['fields'].get('TargetBuilding')
    target_resource_type = stratagem_record['fields'].get('TargetResourceType')

    if not target_resource_type:
        log.warning(f"{LogColors.WARNING}Undercut stratagem {stratagem_record['fields'].get('StratagemId')} has no TargetResourceType. Cannot determine competition.{LogColors.ENDC}")
        return []

    competition_prices: List[float] = []
    now_iso = datetime.now(pytz.utc).isoformat()
    
    # Base formula for active public sell contracts of the target resource type
    base_contract_formula_parts = [
        f"{{ResourceType}} = '{_escape_airtable_value(target_resource_type)}'",
        f"{{Type}} = 'public_sell'",
        f"{{Status}} = 'active'",
        f"{{TargetAmount}} > 0",
        f"IS_BEFORE({{CreatedAt}}, '{now_iso}')", # Contract must have started
        f"IS_AFTER({{EndAt}}, '{now_iso}')"      # Contract must not have ended
    ]

    # Exclude contracts by the citizen executing the stratagem
    base_contract_formula_parts.append(f"{{Seller}} != '{_escape_airtable_value(executed_by_username)}'")

    specific_target_filter = ""
    if target_citizen:
        specific_target_filter = f"{{Seller}} = '{_escape_airtable_value(target_citizen)}'"
    elif target_building_id:
        specific_target_filter = f"{{SellerBuilding}} = '{_escape_airtable_value(target_building_id)}'"
    
    if specific_target_filter:
        final_formula = f"AND({', '.join(base_contract_formula_parts)}, {specific_target_filter})"
    else: # General market competition (excluding self)
        final_formula = f"AND({', '.join(base_contract_formula_parts)})"
        
    log.info(f"{LogColors.PROCESS}Finding competition for {target_resource_type} with formula: {final_formula}{LogColors.ENDC}")
    try:
        competitor_contracts = tables['contracts'].all(
            formula=final_formula,
            fields=['PricePerResource', 'Seller', 'SellerBuilding']
        )
        for contract in competitor_contracts:
            price = contract['fields'].get('PricePerResource')
            if price is not None:
                competition_prices.append(float(price))
        log.info(f"{LogColors.PROCESS}Found {len(competition_prices)} competitor prices for {target_resource_type}. Prices: {competition_prices}{LogColors.ENDC}")
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching competitor contracts for stratagem {stratagem_record['fields'].get('StratagemId')}: {e}{LogColors.ENDC}")
    
    return competition_prices

def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None, # Optional, for resource names
    building_type_defs: Optional[Dict[str, Any]] = None, # Optional, if needed
    api_base_url: Optional[str] = None # For fetching external definitions (e.g. resource types from Next.js API)
) -> bool:
    """
    Processes an "undercut" stratagem.
    Initiates activities to adjust the executing citizen's sell prices for the target resource type.
    """
    stratagem_id = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    python_engine_internal_url = os.getenv("BACKEND_BASE_URL", "http://localhost:10000")
    activity_creation_endpoint = f"{python_engine_internal_url}/api/v1/engine/try-create-activity"
    executed_by = stratagem_record['fields'].get('ExecutedBy')
    variant = stratagem_record['fields'].get('Variant', 'Standard') # Default to Standard
    target_resource_type = stratagem_record['fields'].get('TargetResourceType')

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'undercut' stratagem {stratagem_id} for {executed_by}, Variant: {variant}, Initial TargetResource: {target_resource_type}{LogColors.ENDC}")

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
            if not notification_recipient_username:
                log.warning(f"{LogColors.WARNING}TargetBuilding {target_building_id_for_relationship} for stratagem {stratagem_id} has no RunBy. Cannot send notification or affect relationship.{LogColors.ENDC}")
        else:
            log.warning(f"{LogColors.WARNING}TargetBuilding {target_building_id_for_relationship} for stratagem {stratagem_id} not found. Cannot determine notification recipient.{LogColors.ENDC}")

    undercut_percentage = UNDERCUT_PERCENTAGES.get(variant)
    if undercut_percentage is None:
        log.error(f"{LogColors.FAIL}Invalid variant '{variant}' for stratagem {stratagem_id}. Cannot determine undercut percentage.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': f"Invalid variant: {variant}"})
        return False

    # Determine which resource types to process
    resource_types_to_process: List[str] = []
    initial_target_resource_type = stratagem_record['fields'].get('TargetResourceType')

    if initial_target_resource_type:
        resource_types_to_process.append(initial_target_resource_type)
    elif target_building_id_for_relationship:
        resource_types_to_process = _get_distinct_resources_sold_by_building(tables, target_building_id_for_relationship, executed_by)
        if not resource_types_to_process:
            log.info(f"{LogColors.PROCESS}TargetBuilding {target_building_id_for_relationship} currently sells no distinct resources. Stratagem {stratagem_id} has no immediate effect.{LogColors.ENDC}")
            if not stratagem_record['fields'].get('ExecutedAt'):
                 tables['stratagems'].update(stratagem_record['id'], {'ExecutedAt': datetime.now(pytz.utc).isoformat(), 'Notes': f'TargetBuilding {target_building_id_for_relationship} sells no resources to undercut.'})
            return True
    elif target_citizen_for_relationship:
        resource_types_to_process = _get_distinct_resources_sold_by_citizen(tables, target_citizen_for_relationship, executed_by)
        if not resource_types_to_process:
            log.info(f"{LogColors.PROCESS}TargetCitizen {target_citizen_for_relationship} currently sells no distinct resources. Stratagem {stratagem_id} has no immediate effect.{LogColors.ENDC}")
            if not stratagem_record['fields'].get('ExecutedAt'):
                 tables['stratagems'].update(stratagem_record['id'], {'ExecutedAt': datetime.now(pytz.utc).isoformat(), 'Notes': f'TargetCitizen {target_citizen_for_relationship} sells no resources to undercut.'})
            return True
    else:
        log.error(f"{LogColors.FAIL}Stratagem {stratagem_id} missing any specific target (ResourceType, Building, or Citizen). Cannot process.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'No specific target (ResourceType, Building, or Citizen).'})
        return False
    
    log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id} will attempt to undercut prices for resource(s): {', '.join(resource_types_to_process)}.{LogColors.ENDC}")

    overall_success_for_stratagem = True
    all_activities_initiated_count = 0
    all_notes_for_stratagem_update: List[str] = []

    for current_resource_type_to_target in resource_types_to_process:
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}--- Processing undercut for resource: {current_resource_type_to_target} (Stratagem: {stratagem_id}) ---{LogColors.ENDC}")
        
        # Create a temporary stratagem record copy for get_competition_prices,
        # ensuring it has the current_resource_type_to_target.
        # This is because get_competition_prices expects TargetResourceType to be in the record.
        temp_stratagem_record_for_competition = {
            'id': stratagem_record['id'],
            'fields': {
                **stratagem_record['fields'],
                'TargetResourceType': current_resource_type_to_target 
            }
        }
        
        competition_prices = get_competition_prices(tables, temp_stratagem_record_for_competition, executed_by)

        if not competition_prices:
            log.info(f"{LogColors.PROCESS}No active competition found for {current_resource_type_to_target} for stratagem {stratagem_id}. No price adjustment for this resource.{LogColors.ENDC}")
            all_notes_for_stratagem_update.append(f"No competition for {current_resource_type_to_target}.")
            continue # Move to the next resource type

        min_competitor_price = min(competition_prices)
        target_price = min_competitor_price * (1 - undercut_percentage)
        target_price = round(target_price, 2)

        log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}, Resource {current_resource_type_to_target}: Min competitor price {min_competitor_price:.2f}. Target undercut price: {target_price:.2f}.{LogColors.ENDC}")

        if target_price <= 0:
            log.warning(f"{LogColors.WARNING}Stratagem {stratagem_id}, Resource {current_resource_type_to_target}: Calculated target price {target_price:.2f} is zero or negative. Setting to 0.01.{LogColors.ENDC}")
            target_price = 0.01
        
        # Find the ExecutedBy citizen's active public_sell contracts for the current_resource_type_to_target
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
                log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}: {executed_by} has no active public_sell contracts for {current_resource_type_to_target} to apply undercut.{LogColors.ENDC}")
                all_notes_for_stratagem_update.append(f"No active sell contracts for {current_resource_type_to_target} by {executed_by}.")
                # This is not a failure of the stratagem processing for this resource, just no action.
                # Continue to the next resource type in the loop.
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
                    "targetAmount": contract['fields'].get('TargetAmount'), # Keep existing amount
                    "status": "active", # Keep status active
                    "notes": f"Price adjustment via Undercut Stratagem {stratagem_id}.",
                    "strategy": "stratagem_undercut_price_adjustment" # Signal to creator
                }
                
                payload_for_activity_creation = {
                    "citizenUsername": executed_by,
                    "activityType": "manage_public_sell_contract", # Use existing type, creator needs to handle modification
                    "activityParameters": activity_params
                }

                try:
                    response = requests.post(activity_creation_endpoint, json=payload_for_activity_creation, timeout=30)
                    response.raise_for_status() # Raise an exception for HTTP errors
                    response_data = response.json()

                    if response_data.get("success"):
                        log.info(f"{LogColors.OKGREEN}Successfully initiated 'manage_public_sell_contract' activity for contract {contract_custom_id} (Resource: {current_resource_type_to_target}). Activity: {response_data.get('activity', {}).get('ActivityId', 'N/A')}{LogColors.ENDC}")
                        activities_initiated_for_this_resource += 1
                        all_notes_for_stratagem_update.append(f"Initiated price update for {current_resource_type_to_target} (contract {contract_custom_id}) to {target_price:.2f}.")
                    else:
                        log.error(f"{LogColors.FAIL}Failed to initiate 'manage_public_sell_contract' activity for contract {contract_custom_id} (Resource: {current_resource_type_to_target}). Error: {response_data.get('message', 'Unknown error')}{LogColors.ENDC}")
                        overall_success_for_stratagem = False
                        all_notes_for_stratagem_update.append(f"Failed price update for {current_resource_type_to_target} (contract {contract_custom_id}). Error: {response_data.get('message', 'Unknown')}")
                
                except requests.exceptions.RequestException as e_req:
                    log.error(f"{LogColors.FAIL}RequestException for contract {contract_custom_id} (Resource: {current_resource_type_to_target}): {e_req}{LogColors.ENDC}")
                    overall_success_for_stratagem = False
                    all_notes_for_stratagem_update.append(f"RequestException for {current_resource_type_to_target} (contract {contract_custom_id}): {str(e_req)}")
                except Exception as e_inner:
                    log.error(f"{LogColors.FAIL}Unexpected error for contract {contract_custom_id} (Resource: {current_resource_type_to_target}): {e_inner}{LogColors.ENDC}")
                    overall_success_for_stratagem = False
                    all_notes_for_stratagem_update.append(f"Unexpected error for {current_resource_type_to_target} (contract {contract_custom_id}): {str(e_inner)}")
            else:
                log.info(f"{LogColors.PROCESS}Stratagem {stratagem_id}: Contract {contract_custom_id} for {current_resource_type_to_target} already at target price {target_price:.2f}. No update needed.{LogColors.ENDC}")
                all_notes_for_stratagem_update.append(f"Contract {contract_custom_id} ({current_resource_type_to_target}) already at target price.")

        except Exception as e_outer_loop: # Renamed to avoid conflict with e_outer below
            log.error(f"{LogColors.FAIL}Error processing {executed_by}'s contracts for resource {current_resource_type_to_target} (Stratagem {stratagem_id}): {e_outer_loop}{LogColors.ENDC}")
            all_notes_for_stratagem_update.append(f"Error processing contracts for {current_resource_type_to_target}: {str(e_outer_loop)}")
            overall_success_for_stratagem = False # Mark failure for this resource
        
        all_activities_initiated_count += activities_initiated_for_this_resource
        log.info(f"{LogColors.STRATAGEM_PROCESSOR}--- Finished undercut for resource: {current_resource_type_to_target} (Stratagem: {stratagem_id}) ---{LogColors.ENDC}")
    # End of loop for resource_types_to_process

    # If no activities were initiated for any resource, consider the stratagem ineffective for this cycle.
    if all_activities_initiated_count == 0:
        log.warning(f"{LogColors.WARNING}Stratagem {stratagem_id}: No price update activities were initiated for any targeted resource. Stratagem considered ineffective for this cycle.{LogColors.ENDC}")
        all_notes_for_stratagem_update.append("No price update activities were initiated (no eligible contracts or no competition found).")
        # overall_success_for_stratagem remains True, as the stratagem itself is valid and processed.
        # It just had no effect this cycle.

    # Update stratagem notes
    final_notes_str = stratagem_record['fields'].get('Notes', "")
    if all_notes_for_stratagem_update:
        new_notes_joined = "\n".join(all_notes_for_stratagem_update)
        final_notes_str = f"{final_notes_str}\n{new_notes_joined}".strip() if final_notes_str else new_notes_joined.strip()
    
    update_payload_stratagem = {} # Initialize empty payload
    # Only add Notes to payload if they actually changed
    if final_notes_str != stratagem_record['fields'].get('Notes', ""):
        update_payload_stratagem['Notes'] = final_notes_str

    # Set ExecutedAt and send notifications ONLY if activities were successfully initiated
    if all_activities_initiated_count > 0:
        if not stratagem_record['fields'].get('ExecutedAt'): # Set ExecutedAt only once
            update_payload_stratagem['ExecutedAt'] = datetime.now(pytz.utc).isoformat()
        
        # Notification and trust score logic
        notification_resource_target_text = f"resource '{initial_target_resource_type}'" if initial_target_resource_type else "various resources you sell"
        if notification_recipient_username and notification_recipient_username != executed_by:
            notification_content = (
                f"Citizen {executed_by} has initiated an 'undercut' stratagem ({variant}) "
                f"targeting prices for {notification_resource_target_text}. "
                f"This may affect your sales or the market."
            )
            if target_citizen_for_relationship:
                notification_content += f" You were specifically targeted."
            elif target_building_id_for_relationship:
                notification_content += f" Your building '{target_building_id_for_relationship}' was targeted."

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

            trust_impact = -10.0 
            if variant == "Standard": trust_impact = -7.0
            elif variant == "Mild": trust_impact = -4.0
            
            update_trust_score_for_activity(
                tables, executed_by, notification_recipient_username, trust_impact,
                activity_type_for_notes=f"stratagem_undercut_{variant.lower()}",
                success=False, # From target's perspective
                notes_detail=f"target_{initial_target_resource_type or target_building_id_for_relationship or target_citizen_for_relationship}",
                activity_record_for_kinos=stratagem_record
            )
            log.info(f"{LogColors.PROCESS}Relationship between {executed_by} and {notification_recipient_username} impacted by {trust_impact} due to stratagem {stratagem_id}.{LogColors.ENDC}")
        else:
            log.info(f"{LogColors.PROCESS}No specific notification recipient for stratagem {stratagem_id} or recipient is self. Skipping notification/relationship update.{LogColors.ENDC}")
    
    # Update Airtable only if there are changes in the payload (Notes or ExecutedAt)
    if update_payload_stratagem:
        try:
            tables['stratagems'].update(stratagem_record['id'], update_payload_stratagem)
            log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} record updated with new notes/ExecutedAt.{LogColors.ENDC}")
        except Exception as e_update:
            log.error(f"{LogColors.FAIL}Failed to update stratagem {stratagem_id} notes/ExecutedAt: {e_update}{LogColors.ENDC}")
            # If update fails, the overall_success_for_stratagem might still be true if activities were initiated.
            # This specific error doesn't necessarily mean the stratagem's core logic failed.
            # However, it's an issue. For now, we don't change overall_success_for_stratagem here.

    return overall_success_for_stratagem

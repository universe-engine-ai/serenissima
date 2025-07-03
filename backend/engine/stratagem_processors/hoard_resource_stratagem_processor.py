"""
Stratagem Processor for "hoard_resource".

This processor:
1. Ensures a 'storage_query' contract exists for the target resource and storage building.
2. Identifies employees of the executing citizen.
3. Creates 'fetch_resource' activities for the citizen and their employees to acquire
   the target resource and deliver it to the storage building using the storage_query contract.
"""

import logging
import json
import os
import uuid
import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors,
    get_building_record,
    get_citizen_record,
    get_citizen_effective_carry_capacity,
    get_citizen_current_load,
    get_building_storage_details # To check storage capacity
)
from backend.engine.utils.relationship_helpers import update_trust_score_for_activity # If needed for interactions

log = logging.getLogger(__name__)

DEFAULT_STORAGE_QUERY_TARGET_AMOUNT_PROCESSOR = 1_000_000 

def _ensure_storage_query_contract(
    tables: Dict[str, Any],
    stratagem_record_fields: Dict[str, Any],
    now_utc_dt: datetime
) -> Optional[str]:
    """
    Ensures an active 'storage_query' contract exists for the stratagem.
    Creates one if not found. Returns the ContractId (custom) of the contract.
    """
    stratagem_id = stratagem_record_fields['StratagemId']
    executed_by = stratagem_record_fields['ExecutedBy']
    target_resource_type = stratagem_record_fields['TargetResourceType']
    # target_storage_building_id is now determined dynamically by the processor
    # We need it for the contract, so it must be passed or determined before this function.
    # Let's assume this function now receives target_storage_building_id as an argument.
    # Or, this function could be part of a larger one that first determines it.
    # For now, let's modify it to take target_storage_building_id.
    # This function will be called AFTER a storage building is identified.
    
    # The caller of _ensure_storage_query_contract will now need to pass target_storage_building_id.
    # So, the signature of _ensure_storage_query_contract needs to change.
    # Let's adjust the signature and usage.
    
    # This function is called by `process`. `process` will determine `target_storage_building_id`
    # and then pass it to this function.
    # So, `stratagem_record_fields` will NOT have `TargetStorageBuildingId`.
    # We need to add `target_storage_building_id` to this function's parameters.

    # Corrected: This function is called by `process`. `process` will determine `target_storage_building_id`.
    # This function's role is to ensure the contract for THAT building.
    # So, `target_storage_building_id` should be passed to it.
    # The stratagem_record_fields will NOT contain TargetStorageBuildingId.
    
    # Let's adjust the signature of _ensure_storage_query_contract:
    # def _ensure_storage_query_contract(
    #     tables: Dict[str, Any],
    #     stratagem_record_fields: Dict[str, Any], # Still needed for StratagemId, ExecutedBy, ExpiresAt
    #     target_storage_building_id: str, # NEW PARAMETER
    #     now_utc_dt: datetime
    # ) -> Optional[str]:
    # This change will be reflected where it's called in `process`.

    # The current signature is:
    # _ensure_storage_query_contract(tables, stratagem_record_fields, now_utc_dt)
    # It internally gets target_storage_building_id from stratagem_record_fields.
    # This needs to change. The `process` function will determine the building ID.

    # For now, let's assume the `process` function has already determined `target_storage_building_id`
    # and this function is called with it.
    # The stratagem_record_fields will still be used for StratagemId, ExecutedBy, ExpiresAt.
    # The `target_storage_building_id` used below will be the one determined by `process`.

    # The current implementation of `process` calls this function like:
    # storage_query_contract_id = _ensure_storage_query_contract(tables, stratagem_fields, now_utc_dt)
    # where stratagem_fields *does* contain TargetStorageBuildingId.
    # We need to remove TargetStorageBuildingId from stratagem_fields and determine it in `process`.

    # Let's assume `target_storage_building_id` is now a parameter to this function.
    # The call in `process` will be updated.
    # The stratagem_record_fields will be used for StratagemId, ExecutedBy, ExpiresAt.
    # The `target_resource_type` is also from stratagem_record_fields.

    # Re-evaluating: _ensure_storage_query_contract is called from `process`.
    # `process` will determine `target_storage_building_id`.
    # So, `_ensure_storage_query_contract` needs to receive `target_storage_building_id`.

    # Let's modify the signature of _ensure_storage_query_contract:
    # (This is the definition, not the call site)
    # def _ensure_storage_query_contract(
    #     tables: Dict[str, Any],
    #     stratagem_record_fields: Dict[str, Any], # For StratagemId, ExecutedBy, ExpiresAt, TargetResourceType
    #     determined_target_storage_building_id: str, # The dynamically found building
    #     now_utc_dt: datetime
    # ) -> Optional[str]:
    # The current code for _ensure_storage_query_contract already uses stratagem_record_fields['TargetStorageBuildingId']
    # This will be changed in the `process` function.
    # The `_ensure_storage_query_contract` will now be called with the dynamically determined building ID.

    # The current function signature is:
    # def _ensure_storage_query_contract(
    #    tables: Dict[str, Any],
    #    stratagem_record_fields: Dict[str, Any], # This contains StratagemId, ExecutedBy, TargetResourceType, TargetStorageBuildingId, ExpiresAt
    #    now_utc_dt: datetime
    # ) -> Optional[str]:
    # This is fine if `process` updates `stratagem_record_fields` with the determined `TargetStorageBuildingId` before calling this.
    # Or, more cleanly, `process` determines `target_storage_building_id` and passes it explicitly.

    # Let's go with passing it explicitly.
    # The signature becomes:
    # _ensure_storage_query_contract(tables, stratagem_id, executed_by, target_resource_type, determined_target_storage_building_id, expires_at_iso, now_utc_dt)

    # For now, I will modify the `process` function first to determine the building,
    # then I will update this helper.
    # Let's assume `process` has updated `stratagem_record_fields` to include the determined `TargetStorageBuildingId`.
    # This is simpler for now than changing the signature of this helper and all its call sites.
    # So, `stratagem_record_fields` *will* contain `TargetStorageBuildingId` when this is called,
    # but it's set by the processor, not the creator.

    # The current code is:
    # stratagem_id = stratagem_record_fields['StratagemId']
    # executed_by = stratagem_record_fields['ExecutedBy']
    # target_resource_type = stratagem_record_fields['TargetResourceType']
    # target_storage_building_id = stratagem_record_fields['TargetStorageBuildingId'] <--- This is the key change
    # expires_at_iso = stratagem_record_fields['ExpiresAt']

    # This structure is fine if `process` ensures `TargetStorageBuildingId` is in `stratagem_record_fields`.
    # The `process` function will be modified to do this.

    stratagem_id = stratagem_record_fields['StratagemId']
    executed_by = stratagem_record_fields['ExecutedBy']
    target_resource_type = stratagem_record_fields['TargetResourceType']
    target_storage_building_id = stratagem_record_fields.get('TargetStorageBuildingId') # This will be set by `process`
    if not target_storage_building_id:
        log.error(f"{LogColors.FAIL}_ensure_storage_query_contract called without TargetStorageBuildingId in stratagem_record_fields for {stratagem_id}. This should be set by the processor.{LogColors.ENDC}")
        return None
    expires_at_iso = stratagem_record_fields['ExpiresAt']

    # Check for existing, active, linked contract for THIS specific building
    formula = f"AND({{StratagemLink}}='{_escape_airtable_value(stratagem_id)}', {{Type}}='storage_query', {{Status}}='active', {{BuyerBuilding}}='{_escape_airtable_value(target_storage_building_id)}', IS_AFTER({{EndAt}}, '{now_utc_dt.isoformat()}'))"
    try:
        existing_contracts = tables['contracts'].all(formula=formula, fields=['ContractId', 'TargetAmount', 'CurrentAmountCalculated'])
        if existing_contracts:
            contract_fields = existing_contracts[0]['fields']
            contract_id = contract_fields.get('ContractId')
            target_amount = float(contract_fields.get('TargetAmount', 0))
            # current_amount = float(contract_fields.get('CurrentAmountCalculated', 0)) # This field might not exist or be up-to-date
            
            # Check if storage building has capacity for this resource
            _, storage_map = get_building_storage_details(tables, target_storage_building_id, executed_by)
            current_stored_amount = storage_map.get(target_resource_type, 0.0)

            if current_stored_amount < target_amount:
                log.info(f"{LogColors.PROCESS}Found existing active storage_query contract {contract_id} for stratagem {stratagem_id} with capacity.{LogColors.ENDC}")
                return contract_id
            else:
                log.warning(f"{LogColors.WARNING}Existing storage_query contract {contract_id} for stratagem {stratagem_id} is full or at capacity. (Stored: {current_stored_amount}, Target: {target_amount}). Will attempt to create a new one if stratagem is still valid.{LogColors.ENDC}")
                # Mark old contract as 'completed' or 'failed' due to being full?
                # For now, let's assume we might create a new one if this one is full.
                # This part needs careful thought on contract management.
                # Simplest: if full, processor can't do much more with THIS contract.
                # For this version, we'll just log and not create a new one if one exists and is full.
                # The stratagem will become ineffective until space frees up or it expires.
                return None # Signal that the current contract is full

        # Create a new contract if none found or existing one was deemed unusable (e.g. full and not creating new ones yet)
        log.info(f"{LogColors.PROCESS}No suitable active storage_query contract found for stratagem {stratagem_id}. Creating one.{LogColors.ENDC}")
        storage_contract_id_new = f"contract-sq-{stratagem_id}-{uuid.uuid4().hex[:6]}"
        
        storage_contract_payload = {
            "ContractId": storage_contract_id_new,
            "Type": "storage_query",
            "Buyer": executed_by,
            "BuyerBuilding": target_storage_building_id,
            "SellerBuilding": target_storage_building_id,
            "ResourceType": target_resource_type,
            "TargetAmount": DEFAULT_STORAGE_QUERY_TARGET_AMOUNT_PROCESSOR,
            "PricePerResource": 0,
            "Status": "active",
            "CreatedAt": now_utc_dt.isoformat(),
            "EndAt": expires_at_iso,
            "Notes": f"Storage contract for Hoard Resource Stratagem: {stratagem_id}. Managed by {executed_by}.",
            "StratagemLink": stratagem_id
        }
        created_contract = tables['contracts'].create(storage_contract_payload)
        log.info(f"{LogColors.OKGREEN}Created new storage_query contract {storage_contract_id_new} (Airtable ID: {created_contract['id']}) for stratagem {stratagem_id}.{LogColors.ENDC}")
        return storage_contract_id_new
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error ensuring/creating storage_query contract for stratagem {stratagem_id}: {e}{LogColors.ENDC}")
        return None

def _get_employees(tables: Dict[str, Any], employer_username: str) -> List[Dict[str, Any]]:
    """Fetches records of citizens who are occupants of buildings run by the employer."""
    employees = []
    try:
        # Find buildings run by the employer
        employer_buildings_formula = f"{{RunBy}} = '{_escape_airtable_value(employer_username)}'"
        employer_buildings = tables['buildings'].all(formula=employer_buildings_formula, fields=['Occupant'])
        
        occupant_usernames = set()
        for bldg in employer_buildings:
            occupant = bldg['fields'].get('Occupant')
            if occupant:
                occupant_usernames.add(occupant)
        
        if occupant_usernames:
            # Fetch citizen records for these occupants
            # Create a formula like OR({Username}='user1', {Username}='user2', ...)
            username_conditions = [f"{{Username}}='{_escape_airtable_value(uname)}'" for uname in occupant_usernames]
            employee_formula = f"OR({', '.join(username_conditions)})"
            employees = tables['citizens'].all(formula=employee_formula) # Fetches full records
            log.info(f"{LogColors.PROCESS}Found {len(employees)} employees for {employer_username}.{LogColors.ENDC}")
        else:
            log.info(f"{LogColors.PROCESS}{employer_username} runs buildings with no current occupants listed as employees.{LogColors.ENDC}")
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching employees for {employer_username}: {e}{LogColors.ENDC}")
    return employees


def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any], # This is the full Airtable record
    resource_defs: Optional[Dict[str, Any]] = None,
    building_type_defs: Optional[Dict[str, Any]] = None,
    api_base_url: Optional[str] = None
) -> bool:
    stratagem_fields = stratagem_record['fields']
    stratagem_id = stratagem_fields.get('StratagemId', stratagem_record['id'])
    executed_by = stratagem_fields.get('ExecutedBy')
    target_resource_type = stratagem_fields.get('TargetResourceType')
    # TargetStorageBuildingId is no longer read from stratagem_fields directly here.
    
    python_engine_internal_url = os.getenv("BACKEND_BASE_URL", "http://localhost:10000")
    activity_creation_endpoint = f"{python_engine_internal_url}/api/v1/engine/try-create-activity"
    now_utc_dt = datetime.now(pytz.utc)

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'hoard_resource' stratagem {stratagem_id} for {executed_by}. Target Resource: {target_resource_type}.{LogColors.ENDC}")

    if not all([executed_by, target_resource_type]):
        log.error(f"{LogColors.FAIL}Stratagem {stratagem_id} missing ExecutedBy or TargetResourceType. Cannot process.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {'Status': 'failed', 'Notes': 'Missing ExecutedBy or TargetResourceType.'})
        return False

    # --- Determine Target Storage Building ---
    determined_target_storage_building_id: Optional[str] = None
    determined_storage_building_record: Optional[Dict[str, Any]] = None

    # Priority 1: Own/Run storage building with capacity
    log.info(f"{LogColors.PROCESS}Hoard Stratagem {stratagem_id}: Searching for private storage for {executed_by} for resource {target_resource_type}.")
    try:
        # Buildings owned or run by the citizen, category 'business', subCategory 'storage'
        owned_or_run_storage_formula = (
            f"OR({{Owner}}='{_escape_airtable_value(executed_by)}', {{RunBy}}='{_escape_airtable_value(executed_by)}'), "
            f"{{Category}}='business', {{SubCategory}}='storage', {{IsConstructed}}=TRUE()"
        )
        potential_private_storages = tables['buildings'].all(formula=f"AND({owned_or_run_storage_formula})")
        
        for bldg_rec in potential_private_storages:
            bldg_id = bldg_rec['fields'].get('BuildingId')
            bldg_type = bldg_rec['fields'].get('Type')
            if not bldg_id or not bldg_type: continue

            bldg_def = building_type_defs.get(bldg_type, {}) if building_type_defs else {}
            max_cap = float(bldg_def.get('productionInformation', {}).get('storageCapacity', 0))
            
            if max_cap > 0:
                _, current_bldg_storage_map = get_building_storage_details(tables, bldg_id, executed_by)
                current_total_volume_in_bldg = sum(current_bldg_storage_map.values())
                if current_total_volume_in_bldg < max_cap:
                    determined_target_storage_building_id = bldg_id
                    determined_storage_building_record = bldg_rec
                    log.info(f"{LogColors.PROCESS}Hoard Stratagem {stratagem_id}: Found private storage '{bldg_id}' with capacity.{LogColors.ENDC}")
                    break 
    except Exception as e_priv_store:
        log.error(f"{LogColors.FAIL}Error searching for private storage for stratagem {stratagem_id}: {e_priv_store}{LogColors.ENDC}")

    # Priority 2: Public storage offer (if no private storage found or suitable)
    if not determined_target_storage_building_id:
        log.info(f"{LogColors.PROCESS}Hoard Stratagem {stratagem_id}: No suitable private storage. Searching for public storage offers for {target_resource_type}.")
        try:
            public_storage_offers_formula = (
                f"AND({{Type}}='public_storage_offer', {{ResourceType}}='{_escape_airtable_value(target_resource_type)}', "
                f"{{Status}}='active', {{TargetAmount}} > {{CurrentAmountCalculated}}, "
                f"IS_AFTER({{EndAt}}, '{now_utc_dt.isoformat()}'))"
            )
            # Sort by price if applicable, or just take the first one for now
            available_public_offers = tables['contracts'].all(formula=public_storage_offers_formula, sort=[('PricePerResource', 'asc')])
            
            if available_public_offers:
                chosen_public_offer = available_public_offers[0] # Take the cheapest/first available
                public_storage_building_id = chosen_public_offer['fields'].get('SellerBuilding')
                if public_storage_building_id:
                    public_storage_bldg_rec = get_building_record(tables, public_storage_building_id)
                    if public_storage_bldg_rec:
                        determined_target_storage_building_id = public_storage_building_id
                        determined_storage_building_record = public_storage_bldg_rec
                        log.info(f"{LogColors.PROCESS}Hoard Stratagem {stratagem_id}: Found public storage offer at '{public_storage_building_id}' via contract {chosen_public_offer['fields'].get('ContractId')}.{LogColors.ENDC}")
        except Exception as e_pub_store:
            log.error(f"{LogColors.FAIL}Error searching for public storage offers for stratagem {stratagem_id}: {e_pub_store}{LogColors.ENDC}")

    if not determined_target_storage_building_id or not determined_storage_building_record:
        log.warning(f"{LogColors.WARNING}Hoard Stratagem {stratagem_id}: No suitable storage (private or public) found for {target_resource_type}. Cannot proceed this cycle.{LogColors.ENDC}")
        current_notes = stratagem_fields.get('Notes', "")
        new_note = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] No suitable storage found."
        tables['stratagems'].update(stratagem_record['id'], {'Notes': f"{current_notes}\n{new_note}".strip()})
        return True # Stratagem valid, but cannot act.

    # --- Storage Found, Proceed with Contract and Activities ---
    log.info(f"{LogColors.PROCESS}Hoard Stratagem {stratagem_id}: Determined storage building: {determined_target_storage_building_id}.{LogColors.ENDC}")
    
    # We need to pass the determined_target_storage_building_id to _ensure_storage_query_contract.
    # We can temporarily add it to a copy of stratagem_fields for that call.
    temp_stratagem_fields_for_contract = {**stratagem_fields, "TargetStorageBuildingId": determined_target_storage_building_id}
    storage_query_contract_id = _ensure_storage_query_contract(tables, temp_stratagem_fields_for_contract, now_utc_dt)
    
    if not storage_query_contract_id:
        log.warning(f"{LogColors.WARNING}Failed to ensure storage_query contract for stratagem {stratagem_id} at {determined_target_storage_building_id}. Hoarding cannot proceed this cycle.{LogColors.ENDC}")
        current_notes = stratagem_fields.get('Notes', "")
        new_note = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] Failed to secure/create storage contract for {determined_target_storage_building_id}."
        tables['stratagems'].update(stratagem_record['id'], {'Notes': f"{current_notes}\n{new_note}".strip()})
        return True

    # Use determined_storage_building_record for capacity checks
    storage_building_type = determined_storage_building_record['fields'].get('Type')
    building_def = building_type_defs.get(storage_building_type, {}) if building_type_defs else {}
    max_storage_capacity = float(building_def.get('productionInformation', {}).get('storageCapacity', 0))

    _, current_storage_map = get_building_storage_details(tables, determined_target_storage_building_id, executed_by)
    current_total_stored_volume = sum(current_storage_map.values())

    if max_storage_capacity > 0 and current_total_stored_volume >= max_storage_capacity:
        log.info(f"{LogColors.PROCESS}TargetStorageBuilding {determined_target_storage_building_id} is full (Stored: {current_total_stored_volume}, Max: {max_storage_capacity}). Stratagem {stratagem_id} pausing hoarding.{LogColors.ENDC}")
        current_notes = stratagem_fields.get('Notes', "")
        new_note = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] Storage at {determined_target_storage_building_id} full. Pausing."
        tables['stratagems'].update(stratagem_record['id'], {'Notes': f"{current_notes}\n{new_note}".strip()})
        return True

    # Identify actors: the ExecutedBy citizen and their employees
    actors_to_task: List[Dict] = []
    executed_by_citizen_record = get_citizen_record(tables, executed_by)
    if executed_by_citizen_record:
        actors_to_task.append(executed_by_citizen_record)
    
    employees = _get_employees(tables, executed_by)
    actors_to_task.extend(employees)

    if not actors_to_task:
        log.warning(f"{LogColors.WARNING}No actors (self or employees) found for {executed_by} to execute hoard_resource stratagem {stratagem_id}.{LogColors.ENDC}")
        return True # Stratagem is valid, just no one to act.

    overall_success_this_cycle = True
    activities_initiated_this_cycle = 0
    
    for actor_record in actors_to_task:
        actor_username = actor_record['fields'].get('Username')
        actor_citizen_id = actor_record['fields'].get('CitizenId', actor_username) # Custom CitizenId
        actor_airtable_id = actor_record['id']

        if not actor_username: continue

        # Check if actor is already busy with a non-terminal activity
        # This check should ideally be more robust, considering specific activity types or priorities.
        # For now, a simple check for any active (created/in_progress) activity.
        active_activity_formula = f"AND({{Citizen}}='{_escape_airtable_value(actor_username)}', OR({{Status}}='created', {{Status}}='in_progress'))"
        if tables['activities'].all(formula=active_activity_formula, max_records=1):
            log.info(f"{LogColors.PROCESS}Actor {actor_username} is busy. Skipping hoarding task for them this cycle (Stratagem {stratagem_id}).{LogColors.ENDC}")
            continue

        # Determine amount to fetch: max carry capacity minus current load, up to available funds.
        # This is a simplification; actual amount might be limited by market availability or price.
        # The fetch_resource activity creator will handle market search and price checks.
        # We just need to suggest a reasonable max amount.
        
        actor_max_carry = get_citizen_effective_carry_capacity(actor_record)
        actor_current_load = get_citizen_current_load(tables, actor_username)
        available_carry_capacity = actor_max_carry - actor_current_load
        
        if available_carry_capacity <= 0.1: # Minimal threshold
            log.info(f"{LogColors.PROCESS}Actor {actor_username} has no carry capacity ({available_carry_capacity:.2f}). Skipping hoarding task.{LogColors.ENDC}")
            continue

        # For amount, let's aim to fill their carry capacity.
        # The fetch_resource activity creator will adjust based on market and funds.
        amount_to_attempt_fetch = available_carry_capacity

        activity_params = {
            "resourceTypeId": target_resource_type,
            "amount": amount_to_attempt_fetch, # Max attempt
            "toBuildingId": determined_target_storage_building_id, # Deliver to the hoard
            "contractId": storage_query_contract_id, # Authorize deposit via this contract
            "notes": f"Hoarding {target_resource_type} for stratagem {stratagem_id} at {determined_target_storage_building_id}.",
            "strategy": "stratagem_hoard_resource_acquisition" # Specific strategy for fetch_resource
        }
        
        payload_for_activity_creation = {
            "citizenUsername": actor_username,
            "activityType": "fetch_resource",
            "activityParameters": activity_params
        }

        log.info(f"{LogColors.PROCESS}Attempting to create 'fetch_resource' for {actor_username} (Stratagem {stratagem_id}). Payload: {json.dumps(payload_for_activity_creation, indent=2)}{LogColors.ENDC}")
        try:
            response = requests.post(activity_creation_endpoint, json=payload_for_activity_creation, timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("success"):
                log.info(f"{LogColors.OKGREEN}Successfully initiated 'fetch_resource' for {actor_username} (Stratagem {stratagem_id}). Activity: {response_data.get('activity', {}).get('ActivityId', 'N/A')}{LogColors.ENDC}")
                activities_initiated_this_cycle += 1
            else:
                log.error(f"{LogColors.FAIL}Failed to initiate 'fetch_resource' for {actor_username} (Stratagem {stratagem_id}). Error: {response_data.get('message', 'Unknown error')}{LogColors.ENDC}")
                # overall_success_this_cycle = False # Don't mark stratagem as failed if one actor fails
        
        except requests.exceptions.RequestException as e_req:
            log.error(f"{LogColors.FAIL}RequestException creating fetch_resource for {actor_username} (Stratagem {stratagem_id}): {e_req}{LogColors.ENDC}")
            # overall_success_this_cycle = False
        except Exception as e_inner:
            log.error(f"{LogColors.FAIL}Unexpected error creating fetch_resource for {actor_username} (Stratagem {stratagem_id}): {e_inner}{LogColors.ENDC}")
            # overall_success_this_cycle = False

    if activities_initiated_this_cycle > 0:
        if not stratagem_fields.get('ExecutedAt'):
            tables['stratagems'].update(stratagem_record['id'], {'ExecutedAt': now_utc_dt.isoformat()})
        current_notes = stratagem_fields.get('Notes', "")
        new_note = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] Initiated {activities_initiated_this_cycle} fetching activities."
        tables['stratagems'].update(stratagem_record['id'], {'Notes': f"{current_notes}\n{new_note}".strip()})
    else:
        current_notes = stratagem_fields.get('Notes', "")
        new_note = f"[{now_utc_dt.strftime('%Y-%m-%d %H:%M')}] No fetching activities initiated this cycle (actors busy or no capacity)."
        tables['stratagems'].update(stratagem_record['id'], {'Notes': f"{current_notes}\n{new_note}".strip()})


    # This stratagem remains 'active' until it expires or is manually cancelled.
    # Success of this processing run means it attempted to create tasks.
    return True # Always return True if stratagem itself is valid, even if no tasks created this cycle.

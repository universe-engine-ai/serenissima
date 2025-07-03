#!/usr/bin/env python3
"""
Create All Fetch Activities Script for La Serenissima.

This script identifies active contracts requiring resource fetching and creates
the necessary activities for AI citizens. It handles:
- 'public_sell' / 'recurrent' contracts: Buyer fetches resources.
- 'import' contracts: Buyer fetches their goods from an arrived galley.
- 'storage_query' contracts: Owner fetches their goods from a storage facility.

The script checks for citizen availability, stock, funds, and avoids duplicate activities.
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime, timezone, timedelta
import pytz
import uuid
from typing import Dict, List, Optional, Any

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

from backend.engine.utils.activity_helpers import (
    LogColors, VENICE_TIMEZONE, _escape_airtable_value,
    get_resource_types_from_api, get_building_types_from_api,
    get_citizen_record, get_building_record, get_contract_record,
    get_citizen_current_load, get_citizen_effective_carry_capacity,
    get_building_storage_details, find_path_between_buildings_or_coords,
    _has_recent_failed_activity_for_contract, log_header,
    _get_building_position_coords, # For pathing
    get_citizen_workplace, get_citizen_home # Added for destination building
)
from backend.engine.activity_creators import (
    try_create_resource_fetching_activity,
    try_create_fetch_from_galley_activity,
    try_create_fetch_from_storage_activity
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("createAllFetchActivities")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Constants
TRANSPORT_API_URL = os.getenv("TRANSPORT_API_URL", "http://localhost:3000/api/transport")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
DEFAULT_ACTIVITY_CHECK_HOURS = 12 # Check for existing/failed activities in the last X hours

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initializes connection to Airtable."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    if not api_key or not base_id:
        log.error(f"{LogColors.FAIL}Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID.{LogColors.ENDC}")
        return None
    try:
        api = Api(api_key.strip())
        tables = {
            'citizens': api.table(base_id.strip(), 'CITIZENS'),
            'buildings': api.table(base_id.strip(), 'BUILDINGS'),
            'activities': api.table(base_id.strip(), 'ACTIVITIES'),
            'contracts': api.table(base_id.strip(), 'CONTRACTS'),
            'resources': api.table(base_id.strip(), 'RESOURCES'),
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection initialized successfully.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def get_citizen_destination_building(tables: Dict[str, Table], citizen_record: Dict, contract_type: str) -> Optional[Dict]:
    """Determines the destination building for fetched resources (e.g., workshop or home)."""
    citizen_id_val = citizen_record['fields'].get('CitizenId')
    username_val = citizen_record['fields'].get('Username')
    if not citizen_id_val or not username_val:
        log.error(f"Citizen record missing CitizenId or Username: {citizen_record.get('id')}")
        return None

    workplace = get_citizen_workplace(tables, citizen_id_val, username_val)
    if workplace:
        return workplace
    home = get_citizen_home(tables, username_val)
    if home:
        return home
    log.warning(f"Citizen {username_val} has no workplace or home to deliver resources for contract type {contract_type}.")
    return None

def process_public_or_recurrent_contract(
    tables: Dict[str, Table], contract: Dict, now_utc_dt: datetime,
    resource_defs: Dict, building_type_defs: Dict, dry_run: bool
):
    """Processes 'public_sell' or 'recurrent' contracts for fetching."""
    contract_id = contract['fields'].get('ContractId', contract['id'])
    contract_type_log = contract['fields'].get('Type')
    log.info(f"{LogColors.OKBLUE}Processing contract {LogColors.BOLD}{contract_id}{LogColors.ENDC}{LogColors.OKBLUE} (Type: {contract_type_log}){LogColors.ENDC}")

    buyer_username = contract['fields'].get('Buyer')
    seller_username = contract['fields'].get('Seller')
    resource_type = contract['fields'].get('ResourceType')
    amount_on_contract = float(contract['fields'].get('TargetAmount', 0))
    price_per_unit = float(contract['fields'].get('PricePerResource', 0))
    seller_building_id = contract['fields'].get('SellerBuilding') 

    if not all([buyer_username, seller_username, resource_type, seller_building_id]) or amount_on_contract <= 0:
        log.warning(f"  Contract {contract_id}: Missing essential details (Buyer: {buyer_username}, Seller: {seller_username}, Resource: {resource_type}, SellerBuilding: {seller_building_id}) or has 0 amount ({amount_on_contract}). Skipping.")
        return

    log.info(f"  Contract {contract_id}: Buyer: {buyer_username}, Seller: {seller_username}, Resource: {resource_type}, Amount: {amount_on_contract}, Price: {price_per_unit}, SellerBuilding: {seller_building_id}")

    buyer_record = get_citizen_record(tables, buyer_username)
    if not buyer_record:
        log.info(f"  Contract {contract_id}: Buyer {buyer_username} not found. Skipping automated fetch.")
        return
    if not buyer_record['fields'].get('IsAI'):
        log.info(f"  Contract {contract_id}: Buyer {buyer_username} is not AI. Skipping automated fetch.")
        return
    
    log.info(f"  Contract {contract_id}: Buyer {buyer_username} is AI. Proceeding.")

    activity_check_formula = f"AND({{ContractId}}='{_escape_airtable_value(contract_id)}', {{Type}}='fetch_resource', OR({{Status}}='created', {{Status}}='in_progress'))"
    existing_fetch_activities = tables['activities'].all(formula=activity_check_formula, max_records=1)
    if existing_fetch_activities:
        log.info(f"  Contract {contract_id}: Existing 'fetch_resource' activity (ID: {existing_fetch_activities[0]['id']}) found. Skipping.")
        return

    log.info(f"  Contract {contract_id}: No existing fetch activity. Checking seller building...")
    seller_building_record = get_building_record(tables, seller_building_id)
    if not seller_building_record:
        log.warning(f"  Contract {contract_id}: Seller building {seller_building_id} not found. Skipping.")
        return
    log.info(f"  Contract {contract_id}: Seller building {seller_building_id} (Name: {seller_building_record['fields'].get('Name', 'N/A')}) found.")

    buyer_destination_building_record = get_citizen_destination_building(tables, buyer_record, contract['fields'].get('Type'))
    if not buyer_destination_building_record:
        log.warning(f"  Contract {contract_id}: Could not determine destination for buyer {buyer_username}. Skipping.")
        return
    buyer_destination_building_id = buyer_destination_building_record['fields'].get('BuildingId')
    log.info(f"  Contract {contract_id}: Buyer destination is {buyer_destination_building_id} (Name: {buyer_destination_building_record['fields'].get('Name', 'N/A')}).")

    _, seller_stock_map = get_building_storage_details(tables, seller_building_id, seller_username)
    available_stock = seller_stock_map.get(resource_type, 0.0)
    log.info(f"  Contract {contract_id}: Seller {seller_username} at {seller_building_id} has {available_stock} of {resource_type}.")
    if available_stock <= 0:
        log.info(f"  Contract {contract_id}: Seller building {seller_building_id} has no stock of {resource_type}. Skipping.")
        return

    citizen_max_capacity = get_citizen_effective_carry_capacity(buyer_record)
    current_load = get_citizen_current_load(tables, buyer_username)
    remaining_capacity = citizen_max_capacity - current_load
    log.info(f"  Contract {contract_id}: Buyer {buyer_username} max capacity: {citizen_max_capacity}, current load: {current_load}, remaining capacity: {remaining_capacity}.")
    
    amount_to_fetch = min(amount_on_contract, available_stock, remaining_capacity)
    log.info(f"  Contract {contract_id}: Calculated amount_to_fetch: {amount_to_fetch} (min of contract: {amount_on_contract}, stock: {available_stock}, capacity: {remaining_capacity}).")
    if amount_to_fetch <= 0.01: 
        log.info(f"  Contract {contract_id}: Not enough capacity or stock to fetch. Skipping.")
        return

    buyer_ducats = float(buyer_record['fields'].get('Ducats', 0))
    total_cost = amount_to_fetch * price_per_unit
    log.info(f"  Contract {contract_id}: Buyer {buyer_username} has {buyer_ducats} Ducats. Cost for {amount_to_fetch} units: {total_cost} Ducats.")
    if buyer_ducats < total_cost:
        log.info(f"  Contract {contract_id}: Buyer {buyer_username} has insufficient funds. Skipping.")
        return

    buyer_pos_str = buyer_record['fields'].get('Position')
    if not buyer_pos_str:
        log.warning(f"  Contract {contract_id}: Buyer {buyer_username} has no position. Skipping.")
        return
    buyer_position = json.loads(buyer_pos_str)
    seller_building_pos = _get_building_position_coords(seller_building_record)
    if not seller_building_pos:
        log.warning(f"  Contract {contract_id}: Seller building {seller_building_id} has no position. Skipping.")
        return
    log.info(f"  Contract {contract_id}: Buyer position: {buyer_position}, Seller building position: {seller_building_pos}.")

    path_to_seller_building = find_path_between_buildings_or_coords(tables, buyer_position, seller_building_pos, API_BASE_URL, TRANSPORT_API_URL)
    if not (path_to_seller_building and path_to_seller_building.get('success')):
        log.warning(f"  Contract {contract_id}: Could not find path for {buyer_username} to {seller_building_id}. Path data: {path_to_seller_building}. Skipping.")
        return
    log.info(f"  Contract {contract_id}: Path found for {buyer_username} to {seller_building_id}. Duration: {path_to_seller_building.get('timing', {}).get('durationSeconds', 'N/A')}s.")

    log.info(f"  Contract {contract_id}: Attempting to create 'fetch_resource' for {buyer_username}, {amount_to_fetch} of {resource_type} from {seller_building_id} to {buyer_destination_building_id}.")
    if not dry_run:
        created_activity = try_create_resource_fetching_activity(
            tables, buyer_record['id'], buyer_record['fields']['CitizenId'], buyer_username,
            contract_id, seller_building_id, buyer_destination_building_id,
            resource_type, amount_to_fetch, path_to_seller_building, now_utc_dt, resource_defs
        )
        if created_activity:
            log.info(f"{LogColors.OKGREEN}Successfully created 'fetch_resource' activity for contract {contract_id}.{LogColors.ENDC}")
        else:
            log.error(f"{LogColors.FAIL}Failed to create 'fetch_resource' activity for contract {contract_id}.{LogColors.ENDC}")
    else:
        log.info(f"[DRY RUN] Would create 'fetch_resource' for contract {contract_id}.")


def process_import_contract_galley_fetch(
    tables: Dict[str, Table], contract: Dict, now_utc_dt: datetime,
    resource_defs: Dict, building_type_defs: Dict, dry_run: bool
):
    """Processes 'import' contracts where goods are at a galley, for buyer to fetch."""
    contract_id = contract['fields'].get('ContractId', contract['id'])
    contract_type_log = contract['fields'].get('Type') # Should be 'import'
    log.info(f"{LogColors.OKBLUE}Processing contract {LogColors.BOLD}{contract_id}{LogColors.ENDC}{LogColors.OKBLUE} (Type: {contract_type_log}) for buyer galley fetch.{LogColors.ENDC}")

    buyer_username = contract['fields'].get('Buyer')
    resource_type = contract['fields'].get('ResourceType')
    amount_on_contract = float(contract['fields'].get('TargetAmount', 0))
    galley_custom_id = contract['fields'].get('SellerBuilding') # This is the Galley's BuildingId

    if not all([buyer_username, resource_type, galley_custom_id]) or amount_on_contract <= 0:
        log.warning(f"  Import Contract {contract_id}: Missing essential details (Buyer: {buyer_username}, Resource: {resource_type}, Galley: {galley_custom_id}) or has 0 amount ({amount_on_contract}). Skipping.")
        return

    log.info(f"  Import Contract {contract_id}: Buyer: {buyer_username}, Resource: {resource_type}, Amount: {amount_on_contract}, Galley: {galley_custom_id}")

    buyer_record = get_citizen_record(tables, buyer_username)
    if not buyer_record:
        log.info(f"  Import Contract {contract_id}: Buyer {buyer_username} not found. Skipping automated fetch.")
        return
    if not buyer_record['fields'].get('IsAI'):
        log.info(f"  Import Contract {contract_id}: Buyer {buyer_username} is not AI. Skipping automated fetch.")
        return
    log.info(f"  Import Contract {contract_id}: Buyer {buyer_username} is AI. Proceeding.")

    galley_record = get_building_record(tables, galley_custom_id)
    if not galley_record:
        log.warning(f"  Import Contract {contract_id}: Galley {galley_custom_id} not found. Skipping.")
        return
    if not galley_record['fields'].get('IsConstructed'): # IsConstructed means "arrived" for galleys
        log.info(f"  Import Contract {contract_id}: Galley {galley_custom_id} (Name: {galley_record['fields'].get('Name', 'N/A')}) has not arrived yet (IsConstructed=false). Skipping.")
        return
    log.info(f"  Import Contract {contract_id}: Galley {galley_custom_id} (Name: {galley_record['fields'].get('Name', 'N/A')}) has arrived.")

    activity_check_formula = f"AND({{ContractId}}='{_escape_airtable_value(contract_id)}', {{Type}}='fetch_from_galley', OR({{Status}}='created', {{Status}}='in_progress'))"
    existing_fetch_activities = tables['activities'].all(formula=activity_check_formula, max_records=1)
    if existing_fetch_activities:
        log.info(f"  Import Contract {contract_id}: Existing 'fetch_from_galley' activity (ID: {existing_fetch_activities[0]['id']}) found. Skipping.")
        return
    log.info(f"  Import Contract {contract_id}: No existing fetch_from_galley activity.")

    buyer_destination_building_record = get_citizen_destination_building(tables, buyer_record, "import")
    if not buyer_destination_building_record:
        log.warning(f"  Import Contract {contract_id}: Could not determine destination for buyer {buyer_username}. Skipping.")
        return
    buyer_destination_building_id = buyer_destination_building_record['fields'].get('BuildingId')
    log.info(f"  Import Contract {contract_id}: Buyer destination is {buyer_destination_building_id} (Name: {buyer_destination_building_record['fields'].get('Name', 'N/A')}).")

    # Stock check for imports is tricky: resources are "on the galley" but not in its standard storage.
    # The amount_on_contract is what's available to the buyer from this galley for this contract.
    # We assume the contract amount is what's available on the galley for this buyer.
    log.info(f"  Import Contract {contract_id}: Assuming {amount_on_contract} of {resource_type} is available on galley {galley_custom_id} for this contract.")

    citizen_max_capacity = get_citizen_effective_carry_capacity(buyer_record)
    current_load = get_citizen_current_load(tables, buyer_username)
    remaining_capacity = citizen_max_capacity - current_load
    log.info(f"  Import Contract {contract_id}: Buyer {buyer_username} max capacity: {citizen_max_capacity}, current load: {current_load}, remaining capacity: {remaining_capacity}.")
    
    amount_to_fetch = min(amount_on_contract, remaining_capacity)
    log.info(f"  Import Contract {contract_id}: Calculated amount_to_fetch: {amount_to_fetch} (min of contract: {amount_on_contract}, capacity: {remaining_capacity}).")
    if amount_to_fetch <= 0.01:
        log.info(f"  Import Contract {contract_id}: Buyer {buyer_username} has no capacity. Skipping.")
        return

    buyer_pos_str = buyer_record['fields'].get('Position')
    if not buyer_pos_str:
        log.warning(f"  Import Contract {contract_id}: Buyer {buyer_username} has no position. Skipping.")
        return
    buyer_position = json.loads(buyer_pos_str)
    galley_pos = _get_building_position_coords(galley_record)
    if not galley_pos:
        log.warning(f"  Import Contract {contract_id}: Galley {galley_custom_id} has no position. Skipping.")
        return
    log.info(f"  Import Contract {contract_id}: Buyer position: {buyer_position}, Galley position: {galley_pos}.")

    path_to_galley = find_path_between_buildings_or_coords(tables, buyer_position, galley_pos, API_BASE_URL, TRANSPORT_API_URL)
    if not (path_to_galley and path_to_galley.get('success')):
        log.warning(f"  Import Contract {contract_id}: Could not find path for {buyer_username} to galley {galley_custom_id}. Path data: {path_to_galley}. Skipping.")
        return
    log.info(f"  Import Contract {contract_id}: Path found for {buyer_username} to galley {galley_custom_id}. Duration: {path_to_galley.get('timing', {}).get('durationSeconds', 'N/A')}s.")

    log.info(f"  Import Contract {contract_id}: Attempting to create 'fetch_from_galley' for {buyer_username}, {amount_to_fetch} of {resource_type} from galley {galley_custom_id} to {buyer_destination_building_id}.")
    if not dry_run:
        # buyer_destination_building_record is already fetched and validated before this block
        created_activity_chain_start = try_create_fetch_from_galley_activity(
            tables=tables,
            citizen_airtable_id=buyer_record['id'],
            citizen_custom_id=buyer_record['fields']['CitizenId'],
            citizen_username=buyer_username,
            galley_airtable_id=galley_record['id'],
            galley_custom_id=galley_custom_id,
            original_contract_custom_id=contract_id,
            resource_id_to_fetch=resource_type,
            amount_to_fetch=amount_to_fetch,
            path_data_to_galley=path_to_galley,
            current_time_utc=now_utc_dt,
            resource_defs=resource_defs,
            buyer_destination_building_record=buyer_destination_building_record, # Pass destination
            api_base_url=API_BASE_URL, # Pass API base URL
            transport_api_url=TRANSPORT_API_URL, # Pass transport API URL
            start_time_utc_iso=None # For immediate start of the chain
        )
        if created_activity_chain_start:
            log.info(f"  Import Contract {contract_id}: {LogColors.OKGREEN}Successfully created 'fetch_from_galley' activity.{LogColors.ENDC}")
        else:
            log.error(f"  Import Contract {contract_id}: {LogColors.FAIL}Failed to create 'fetch_from_galley' activity.{LogColors.ENDC}")
    else:
        log.info(f"  Import Contract {contract_id}: [DRY RUN] Would create 'fetch_from_galley'.")


def process_storage_query_contract(
    tables: Dict[str, Table], contract: Dict, now_utc_dt: datetime,
    resource_defs: Dict, building_type_defs: Dict, dry_run: bool
):
    """Processes 'storage_query' contracts for citizens to retrieve their goods."""
    contract_id = contract['fields'].get('ContractId', contract['id'])
    contract_type_log = contract['fields'].get('Type') # Should be 'storage_query'
    log.info(f"{LogColors.OKBLUE}Processing contract {LogColors.BOLD}{contract_id}{LogColors.ENDC}{LogColors.OKBLUE} (Type: {contract_type_log}) for retrieval.{LogColors.ENDC}")

    owner_username = contract['fields'].get('Buyer') # In storage_query, Buyer is the owner of the goods
    resource_type = contract['fields'].get('ResourceType')
    amount_on_contract = float(contract['fields'].get('TargetAmount', 0))
    storage_facility_id = contract['fields'].get('SellerBuilding')
    destination_building_id = contract['fields'].get('BuyerBuilding') # Destination for the goods

    if not all([owner_username, resource_type, storage_facility_id, destination_building_id]) or amount_on_contract <= 0:
        log.warning(f"  Storage Query {contract_id}: Missing essential details (Owner: {owner_username}, Resource: {resource_type}, Storage: {storage_facility_id}, Destination: {destination_building_id}) or has 0 amount ({amount_on_contract}). Skipping.")
        return

    log.info(f"  Storage Query {contract_id}: Owner: {owner_username}, Resource: {resource_type}, Amount: {amount_on_contract}, Storage: {storage_facility_id}, Destination: {destination_building_id}")

    owner_record = get_citizen_record(tables, owner_username)
    if not owner_record:
        log.info(f"  Storage Query {contract_id}: Owner {owner_username} not found. Skipping automated fetch.")
        return
    if not owner_record['fields'].get('IsAI'):
        log.info(f"  Storage Query {contract_id}: Owner {owner_username} is not AI. Skipping automated fetch.")
        return
    log.info(f"  Storage Query {contract_id}: Owner {owner_username} is AI. Proceeding.")

    activity_check_formula = f"AND({{ContractId}}='{_escape_airtable_value(contract_id)}', {{Type}}='fetch_from_storage', OR({{Status}}='created', {{Status}}='in_progress'))"
    existing_fetch_activities = tables['activities'].all(formula=activity_check_formula, max_records=1)
    if existing_fetch_activities:
        log.info(f"  Storage Query {contract_id}: Existing 'fetch_from_storage' activity (ID: {existing_fetch_activities[0]['id']}) found. Skipping.")
        return
    log.info(f"  Storage Query {contract_id}: No existing fetch_from_storage activity.")

    storage_facility_record = get_building_record(tables, storage_facility_id)
    destination_building_record = get_building_record(tables, destination_building_id)
    if not storage_facility_record:
        log.warning(f"  Storage Query {contract_id}: Storage facility {storage_facility_id} not found. Skipping.")
        return
    if not destination_building_record:
        log.warning(f"  Storage Query {contract_id}: Destination building {destination_building_id} not found. Skipping.")
        return
    log.info(f"  Storage Query {contract_id}: Storage: {storage_facility_id} (Name: {storage_facility_record['fields'].get('Name', 'N/A')}), Destination: {destination_building_id} (Name: {destination_building_record['fields'].get('Name', 'N/A')}).")

    _, owner_stock_in_storage_map = get_building_storage_details(tables, storage_facility_id, owner_username)
    available_stock = owner_stock_in_storage_map.get(resource_type, 0.0)
    log.info(f"  Storage Query {contract_id}: Owner {owner_username} has {available_stock} of {resource_type} at storage {storage_facility_id}.")
    if available_stock <= 0:
        log.info(f"  Storage Query {contract_id}: Storage facility {storage_facility_id} has no stock of {resource_type} for owner {owner_username}. Skipping.")
        return

    citizen_max_capacity = get_citizen_effective_carry_capacity(owner_record)
    current_load = get_citizen_current_load(tables, owner_username)
    remaining_capacity = citizen_max_capacity - current_load
    log.info(f"  Storage Query {contract_id}: Owner {owner_username} max capacity: {citizen_max_capacity}, current load: {current_load}, remaining capacity: {remaining_capacity}.")
    
    amount_to_fetch = min(amount_on_contract, available_stock, remaining_capacity)
    log.info(f"  Storage Query {contract_id}: Calculated amount_to_fetch: {amount_to_fetch} (min of contract: {amount_on_contract}, stock: {available_stock}, capacity: {remaining_capacity}).")
    if amount_to_fetch <= 0.01:
        log.info(f"  Storage Query {contract_id}: Not enough capacity or stock to retrieve. Skipping.")
        return

    owner_pos_str = owner_record['fields'].get('Position')
    if not owner_pos_str:
        log.warning(f"  Storage Query {contract_id}: Owner {owner_username} has no position. Skipping.")
        return
    owner_position = json.loads(owner_pos_str)
    storage_facility_pos = _get_building_position_coords(storage_facility_record)
    if not storage_facility_pos:
        log.warning(f"  Storage Query {contract_id}: Storage facility {storage_facility_id} has no position. Skipping.")
        return
    log.info(f"  Storage Query {contract_id}: Owner position: {owner_position}, Storage facility position: {storage_facility_pos}.")

    path_to_storage = find_path_between_buildings_or_coords(tables, owner_position, storage_facility_pos, API_BASE_URL, TRANSPORT_API_URL)
    if not (path_to_storage and path_to_storage.get('success')):
        log.warning(f"  Storage Query {contract_id}: Could not find path for {owner_username} to storage {storage_facility_id}. Path data: {path_to_storage}. Skipping.")
        return
    log.info(f"  Storage Query {contract_id}: Path found for {owner_username} to storage {storage_facility_id}. Duration: {path_to_storage.get('timing', {}).get('durationSeconds', 'N/A')}s.")

    resources_to_fetch_list = [{"ResourceId": resource_type, "Amount": amount_to_fetch}]

    log.info(f"  Storage Query {contract_id}: Attempting to create 'fetch_from_storage' for {owner_username}, {amount_to_fetch} of {resource_type} from {storage_facility_id} to {destination_building_id}.")
    if not dry_run:
        created_activity = try_create_fetch_from_storage_activity(
            tables, owner_record, storage_facility_record, destination_building_record,
            resources_to_fetch_list, contract_id, path_to_storage, now_utc_dt
            # start_time_utc_iso is None for immediate start
        )
        if created_activity:
            log.info(f"  Storage Query {contract_id}: {LogColors.OKGREEN}Successfully created 'fetch_from_storage' activity.{LogColors.ENDC}")
        else:
            log.error(f"  Storage Query {contract_id}: {LogColors.FAIL}Failed to create 'fetch_from_storage' activity.{LogColors.ENDC}")
    else:
        log.info(f"  Storage Query {contract_id}: [DRY RUN] Would create 'fetch_from_storage'.")


def create_all_fetch_activities(dry_run: bool = False, target_citizen_username: Optional[str] = None, target_building_id: Optional[str] = None):
    """Main function to iterate through contracts and create fetch activities."""
    log_header_msg = f"Create All Fetch Activities Process (dry_run={dry_run}"
    if target_citizen_username:
        log_header_msg += f", target_citizen={target_citizen_username}"
    if target_building_id:
        log_header_msg += f", target_building={target_building_id}"
    log_header_msg += ")"
    log_header(log_header_msg, LogColors.HEADER)

    tables = initialize_airtable()
    if not tables: return

    now_utc_dt = datetime.now(timezone.utc)
    resource_defs = get_resource_types_from_api(API_BASE_URL)
    building_type_defs = get_building_types_from_api(API_BASE_URL)

    if not resource_defs or not building_type_defs:
        log.error("Failed to load resource or building definitions. Exiting.")
        return

    contract_formula_parts = [
        "OR({Type}='public_sell', {Type}='recurrent', {Type}='import', {Type}='storage_query')",
        "{Status}='active'",
        f"IS_AFTER({{EndAt}}, '{now_utc_dt.isoformat()}')"
    ]
    base_conditions = contract_formula_parts # Start with the common conditions

    if target_citizen_username:
        # If a specific citizen is targeted, they are always the Buyer/Owner
        base_conditions.append(f"{{Buyer}}='{_escape_airtable_value(target_citizen_username)}'")
        if target_building_id:
            # Citizen is Buyer/Owner, and building is involved either as source or destination for them
            building_conditions = (
                f"OR("
                f"  AND(OR({{Type}}='public_sell', {{Type}}='recurrent'), {{SellerBuilding}}='{_escape_airtable_value(target_building_id)}'),"
                f"  AND(OR({{Type}}='import', {{Type}}='storage_query'), {{BuyerBuilding}}='{_escape_airtable_value(target_building_id)}')"
                f")"
            )
            base_conditions.append(building_conditions)
        # If no target_building_id, just filter by citizen as Buyer/Owner (already added)
    elif target_building_id:
        # No specific citizen, but a specific building.
        # This building can be SellerBuilding (for public_sell/recurrent where AI is buyer)
        # OR BuyerBuilding (for import/storage_query where AI is buyer/owner and this is their destination)
        building_involvement_conditions = (
            f"OR("
            f"  AND(OR({{Type}}='public_sell', {{Type}}='recurrent'), {{SellerBuilding}}='{_escape_airtable_value(target_building_id)}'),"
            f"  AND(OR({{Type}}='import', {{Type}}='storage_query'), {{BuyerBuilding}}='{_escape_airtable_value(target_building_id)}')"
            f")"
        )
        base_conditions.append(building_involvement_conditions)
    
    contract_formula = f"AND({', '.join(base_conditions)})"
    log.info(f"Fetching contracts with formula: {contract_formula}")
    
    try:
        active_contracts = tables['contracts'].all(formula=contract_formula)
    except Exception as e:
        log.error(f"Error fetching active contracts: {e}")
        return

    log.info(f"Found {len(active_contracts)} active contracts to evaluate for fetch activities.")

    for contract in active_contracts:
        contract_type = contract['fields'].get('Type')
        try:
            if contract_type in ['public_sell', 'recurrent']:
                process_public_or_recurrent_contract(tables, contract, now_utc_dt, resource_defs, building_type_defs, dry_run)
            elif contract_type == 'import':
                process_import_contract_galley_fetch(tables, contract, now_utc_dt, resource_defs, building_type_defs, dry_run)
            elif contract_type == 'storage_query':
                process_storage_query_contract(tables, contract, now_utc_dt, resource_defs, building_type_defs, dry_run)
            else:
                log.debug(f"Contract type {contract_type} not handled by this script. Skipping contract {contract['id']}.")
        except Exception as e_contract_process:
            log.error(f"Error processing contract {contract.get('id', 'Unknown ID')}: {e_contract_process}", exc_info=True)

    log_header("Create All Fetch Activities Process Finished", LogColors.HEADER)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create fetch activities for contracts needing them.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the process without making changes.")
    parser.add_argument("--citizen", type=str, help="Target a specific citizen (Username) for whom to create fetch activities (as Buyer/Owner).")
    parser.add_argument("--buildingId", type=str, help="Target contracts related to a specific building ID (SellerBuilding).")
    args = parser.parse_args()

    create_all_fetch_activities(dry_run=args.dry_run, target_citizen_username=args.citizen, target_building_id=args.buildingId)

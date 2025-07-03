#!/usr/bin/env python3
"""
Process Passive Buildings script for La Serenissima.

This script ensures that passive water-providing buildings (public_well, cistern)
have the correct amount of water resources and an active public_sell contract for water.
"""

import os
import sys
import json
import traceback
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Any
import requests
from dotenv import load_dotenv
from pyairtable import Api, Table
import argparse
import logging
import uuid

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("process_passive_buildings")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")

# Import shared utilities from activity_helpers
try:
    from backend.engine.utils.activity_helpers import (
        LogColors, 
        log_header, 
        _escape_airtable_value,
        VENICE_TIMEZONE,
        get_resource_types_from_api
    )
except ImportError:
    # Fallback for critical imports if script is run in an unusual environment
    class LogColors: HEADER=OKBLUE=OKCYAN=OKGREEN=WARNING=FAIL=ENDC=BOLD=LIGHTBLUE=""
    def log_header(msg, color=None): print(f"--- {msg} ---")
    def _escape_airtable_value(val): return str(val).replace("'", "\\'")
    VENICE_TIMEZONE = pytz.timezone('Europe/Rome')
    def get_resource_types_from_api(base_url=None): return {}
    log.error("Failed to import from backend.engine.utils.activity_helpers. Using fallback definitions.")

# --- Helper Functions ---

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initialize connection to Airtable."""
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")

    if not airtable_api_key or not airtable_base_id:
        log.error(f"{LogColors.FAIL}Error: Airtable credentials not found in environment variables.{LogColors.ENDC}")
        return None

    try:
        api = Api(airtable_api_key)
        tables = {
            "buildings": api.table(airtable_base_id, "BUILDINGS"),
            "contracts": api.table(airtable_base_id, "CONTRACTS"),
            "resources": api.table(airtable_base_id, "RESOURCES"),
            "notifications": api.table(airtable_base_id, "NOTIFICATIONS")
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection initialized successfully.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def get_resource_name(resource_id: str, resource_type_defs: Dict[str, Dict]) -> str:
    """Gets the human-readable name of a resource."""
    return resource_type_defs.get(resource_id, {}).get("name", resource_id)

def ensure_public_sell_contract(
    tables: Dict[str, Table],
    building_record: Dict,
    resource_type_id: str,
    target_amount: float,
    price_per_resource: float,
    resource_name: str,
    dry_run: bool
) -> bool:
    """Ensures a public_sell contract exists for the given building and resource."""
    building_id = building_record['fields'].get('BuildingId')
    building_name = building_record['fields'].get('Name', building_id)
    
    # Determine seller: RunBy, then Owner, then ConsiglioDeiDieci
    seller_username = building_record['fields'].get('RunBy') or \
                      building_record['fields'].get('Owner') or \
                      "ConsiglioDeiDieci"

    if not building_id:
        log.error(f"{LogColors.FAIL}Building {building_record['id']} has no BuildingId. Cannot manage contract.{LogColors.ENDC}")
        return False

    contract_id_deterministic = f"public_sell_{resource_type_id}_{building_id}"
    now_utc = datetime.now(pytz.utc)
    end_date_far_future = (now_utc + timedelta(days=365*5)).isoformat() # 5 years in the future

    formula = f"{{ContractId}} = '{_escape_airtable_value(contract_id_deterministic)}'"
    try:
        existing_contracts = tables["contracts"].all(formula=formula, max_records=1)
        
        payload = {
            "ContractId": contract_id_deterministic,
            "Type": "public_sell",
            "Seller": seller_username,
            "SellerBuilding": building_id,
            "ResourceType": resource_type_id,
            "TargetAmount": target_amount,
            "PricePerResource": price_per_resource,
            "Status": "active",
            "Title": f"Public Sale: {resource_name} from {building_name}",
            "Description": f"Automated public sale of {resource_name} from {building_name}.",
            "Notes": json.dumps({"managed_by_script": "processPassiveBuildings.py"}),
            "CreatedAt": now_utc.isoformat(),
            "EndAt": end_date_far_future
        }

        if existing_contracts:
            contract_airtable_id = existing_contracts[0]['id']
            # Check if critical fields need update
            current_fields = existing_contracts[0]['fields']
            needs_update = False
            update_payload = {}
            critical_fields_to_check = {
                "TargetAmount": target_amount,
                "PricePerResource": price_per_resource,
                "Status": "active",
                "Seller": seller_username, # Ensure seller is up-to-date
                "EndAt": end_date_far_future # Ensure EndAt is far future
            }
            for field, expected_value in critical_fields_to_check.items():
                current_value = current_fields.get(field)
                # Special handling for float comparison
                if isinstance(expected_value, float):
                    if not (current_value is not None and isinstance(current_value, (int, float)) and abs(float(current_value) - expected_value) < 0.001):
                        needs_update = True
                        update_payload[field] = expected_value
                elif field == "EndAt": # For EndAt, ensure it's reasonably far in the future
                    try:
                        current_end_dt = datetime.fromisoformat(str(current_value).replace('Z', '+00:00'))
                        if current_end_dt.tzinfo is None: current_end_dt = pytz.utc.localize(current_end_dt)
                        if (current_end_dt - now_utc) < timedelta(days=30): # If less than 30 days left, refresh
                            needs_update = True
                            update_payload[field] = expected_value
                    except Exception: # If parsing fails, update
                        needs_update = True
                        update_payload[field] = expected_value
                elif current_value != expected_value:
                    needs_update = True
                    update_payload[field] = expected_value
            
            if needs_update:
                log.info(f"{LogColors.OKCYAN}Updating existing contract {contract_id_deterministic} for {building_name} with new values: {update_payload}{LogColors.ENDC}")
                if not dry_run:
                    tables["contracts"].update(contract_airtable_id, update_payload)
            else:
                log.info(f"{LogColors.OKBLUE}Contract {contract_id_deterministic} for {building_name} is up-to-date.{LogColors.ENDC}")
        else:
            log.info(f"{LogColors.OKCYAN}Creating new contract {contract_id_deterministic} for {building_name}.{LogColors.ENDC}")
            if not dry_run:
                tables["contracts"].create(payload)
        
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error ensuring contract for {building_name}: {e}{LogColors.ENDC}")
        traceback.print_exc()
        return False

def update_building_resource_stock(
    tables: Dict[str, Table],
    building_record: Dict,
    resource_type_id: str,
    target_stock_amount: float,
    resource_name: str,
    dry_run: bool
) -> bool:
    """Updates or creates the resource stock for a building."""
    building_id = building_record['fields'].get('BuildingId')
    building_name = building_record['fields'].get('Name', building_id)
    
    # Determine owner: RunBy, then Owner, then ConsiglioDeiDieci
    owner_username = building_record['fields'].get('RunBy') or \
                     building_record['fields'].get('Owner') or \
                     "ConsiglioDeiDieci"

    if not building_id:
        log.error(f"{LogColors.FAIL}Building {building_record['id']} has no BuildingId. Cannot manage resources.{LogColors.ENDC}")
        return False

    formula = f"AND({{Asset}}='{_escape_airtable_value(building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type_id)}', {{Owner}}='{_escape_airtable_value(owner_username)}')"
    try:
        existing_resources = tables["resources"].all(formula=formula, max_records=1)
        
        if existing_resources:
            resource_airtable_id = existing_resources[0]['id']
            current_stock = float(existing_resources[0]['fields'].get('Count', 0.0))
            if abs(current_stock - target_stock_amount) > 0.001: # If stock is different
                log.info(f"{LogColors.OKCYAN}Updating {resource_name} stock for {building_name} (Owner: {owner_username}) from {current_stock} to {target_stock_amount}.{LogColors.ENDC}")
                if not dry_run:
                    tables["resources"].update(resource_airtable_id, {"Count": target_stock_amount})
            else:
                log.info(f"{LogColors.OKBLUE}{resource_name} stock for {building_name} (Owner: {owner_username}) is already {target_stock_amount}.{LogColors.ENDC}")
        else:
            log.info(f"{LogColors.OKCYAN}Creating {resource_name} stock for {building_name} (Owner: {owner_username}) with amount {target_stock_amount}.{LogColors.ENDC}")
            if not dry_run:
                payload = {
                    "ResourceId": f"resource-{uuid.uuid4().hex[:12]}",
                    "Type": resource_type_id,
                    "Name": resource_name,
                    "Asset": building_id,
                    "AssetType": "building",
                    "Owner": owner_username,
                    "Count": target_stock_amount,
                    "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat()
                }
                tables["resources"].create(payload)
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error updating resource stock for {building_name}: {e}{LogColors.ENDC}")
        traceback.print_exc()
        return False

# --- Main Processing Logic ---

def process_passive_buildings(dry_run: bool = False, building_id_filter: Optional[str] = None):
    log_header_message = f"Process Passive Buildings (dry_run={dry_run})"
    if building_id_filter:
        log_header_message += f" for BuildingId: {building_id_filter}"
    log_header(log_header_message, LogColors.HEADER)

    tables = initialize_airtable()
    if not tables:
        return

    resource_type_defs = get_resource_types_from_api(API_BASE_URL)
    if not resource_type_defs:
        log.error(f"{LogColors.FAIL}Failed to get resource type definitions. Aborting.{LogColors.ENDC}")
        return
    
    water_resource_name = get_resource_name("water", resource_type_defs)

    buildings_to_process_configs = {
        "public_well": {"target_water_stock": 50.0, "contract_target_amount": 50.0},
        "cistern": {"target_water_stock": 500.0, "contract_target_amount": 500.0}
    }

    for building_type, config in buildings_to_process_configs.items():
        log.info(f"{LogColors.OKBLUE}--- Processing buildings of type: {building_type} ---{LogColors.ENDC}")
        
        formula = f"{{Type}}='{_escape_airtable_value(building_type)}'"
        if building_id_filter:
            formula = f"AND({formula}, {{BuildingId}}='{_escape_airtable_value(building_id_filter)}')"
        
        try:
            buildings_of_type = tables["buildings"].all(formula=formula)
            if not buildings_of_type:
                log.info(f"No buildings of type '{building_type}' found" + (f" matching ID '{building_id_filter}'." if building_id_filter else "."))
                continue

            for building_record in buildings_of_type:
                building_name_log = building_record['fields'].get('Name', building_record['fields'].get('BuildingId', building_record['id']))
                log.info(f"{LogColors.OKCYAN}Processing {building_type}: {building_name_log}{LogColors.ENDC}")

                # 1. Ensure public_sell contract for water
                contract_success = ensure_public_sell_contract(
                    tables,
                    building_record,
                    "water",
                    config["contract_target_amount"],
                    0.0, # PricePerResource
                    water_resource_name,
                    dry_run
                )
                if not contract_success:
                    log.error(f"{LogColors.FAIL}  Failed to ensure contract for {building_name_log}.{LogColors.ENDC}")

                # 2. Update/create resource stock for water
                resource_success = update_building_resource_stock(
                    tables,
                    building_record,
                    "water",
                    config["target_water_stock"],
                    water_resource_name,
                    dry_run
                )
                if not resource_success:
                    log.error(f"{LogColors.FAIL}  Failed to update resource stock for {building_name_log}.{LogColors.ENDC}")

        except Exception as e:
            log.error(f"{LogColors.FAIL}Error processing buildings of type '{building_type}': {e}{LogColors.ENDC}")
            traceback.print_exc()

    log.info(f"{LogColors.OKGREEN}Passive building processing finished.{LogColors.ENDC}")

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process passive buildings to ensure water resources and contracts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, performs a dry run and does not save changes to Airtable."
    )
    parser.add_argument(
        "--buildingId",
        type=str,
        default=None,
        help="Optional BuildingId to process only a single building (must be of type public_well or cistern)."
    )
    args = parser.parse_args()

    process_passive_buildings(dry_run=args.dry_run, building_id_filter=args.buildingId)

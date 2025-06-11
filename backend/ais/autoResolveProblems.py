#!/usr/bin/env python3
"""
Auto Resolve Problems script for La Serenissima.

This script fetches active problems from the PROBLEMS table and attempts to
resolve them by initiating appropriate activities or actions.
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
import re # Added for regex in resolvers

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("auto_resolve_problems")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")
PYTHON_ENGINE_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:10000") # For try-create

# Import shared utilities from activity_helpers
try:
    from backend.engine.utils.activity_helpers import (
        LogColors, 
        log_header, 
        _escape_airtable_value,
        VENICE_TIMEZONE,
        get_resource_types_from_api,
        get_building_types_from_api, # Ensure this is imported
        get_citizen_record,
        get_building_record,
        get_contract_record
    )
    from backend.app.scheduler import send_telegram_notification # For Telegram notifications
except ImportError:
    class LogColors: HEADER=OKBLUE=OKCYAN=OKGREEN=WARNING=FAIL=ENDC=BOLD=LIGHTBLUE=""
    def log_header(msg, color=None): print(f"--- {msg} ---")
    def _escape_airtable_value(val): return str(val).replace("'", "\\'")
    VENICE_TIMEZONE = pytz.timezone('Europe/Rome')
    def get_resource_types_from_api(base_url=None): return {}
    def get_building_types_from_api(base_url=None): return {} # Fallback for building_type_defs
    def get_citizen_record(tables, username): return None
    def get_building_record(tables, building_id): return None
    def get_contract_record(tables, contract_id): return None
    def send_telegram_notification(message: str): log.error(f"Telegram fallback: {message}")
    log.error("Failed to import from backend.engine.utils.activity_helpers or backend.app.scheduler. Using fallback definitions.")

# --- Configuration Constants ---
DEFAULT_WAGE_INCREASE_BASE_PERCENTAGE = 2.0  # Base percentage for wage increase on existing wages
WAGE_INCREASE_PER_FAILURE_PERCENTAGE = 1.0 # Additional percentage per failure count
BASE_STARTING_WAGE = 2000.0 # New base starting wage for zero_wages_business
BASE_STARTING_RENT = 1000.0 # New base starting rent for zero_rent_building
DEFAULT_TARGET_AMOUNT_STORAGE_PERCENTAGE = 0.25 # Target 25% of *remaining* storage capacity
DEFAULT_SELL_CONTRACT_MARKUP_PERCENTAGE = 20.0 # 20% markup on import price for new sell contracts
MAX_RESOLUTION_FAILURES_BEFORE_SEVERITY_INCREASE = 3
TELEGRAM_NOTIFICATION_ON_RESOLUTION_FAILURE = True # Control Telegram notifications for resolution failures
PROBLEM_MAX_FAILURES_NOTE_REGEX = r"\[Failures:\s*(\d+)\]"

# Severity mapping for sorting and escalation
SEVERITY_ORDER = {"Very Low": 1, "Low": 2, "Medium": 3, "High": 4, "Critical": 5}
SEVERITY_ESCALATION_MAP = {
    "Very Low": "Low", "Low": "Medium", "Medium": "High", "High": "Critical", "Critical": "Critical"
}

# --- Airtable Initialization ---
def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initialize connection to Airtable."""
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")

    if not airtable_api_key or not airtable_base_id:
        log.error(f"{LogColors.FAIL}Error: Airtable credentials not found.{LogColors.ENDC}")
        return None
    try:
        api = Api(airtable_api_key)
        tables = {
            "problems": api.table(airtable_base_id, "PROBLEMS"),
            "citizens": api.table(airtable_base_id, "CITIZENS"),
            "buildings": api.table(airtable_base_id, "BUILDINGS"),
            "contracts": api.table(airtable_base_id, "CONTRACTS"),
            "resources": api.table(airtable_base_id, "RESOURCES"),
            "activities": api.table(airtable_base_id, "ACTIVITIES"), # For checking existing activities
            "notifications": api.table(airtable_base_id, "NOTIFICATIONS")
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection initialized successfully.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

# --- API Call Helper ---
def call_try_create_activity_api(
    citizen_username: str,
    activity_type: str,
    activity_parameters: Dict[str, Any],
    dry_run: bool
) -> bool:
    """Calls the /api/activities/try-create endpoint."""
    if dry_run:
        log.info(f"{LogColors.OKCYAN}[DRY RUN] Would call /api/activities/try-create for {citizen_username} with type '{activity_type}' and params: {json.dumps(activity_parameters)}{LogColors.ENDC}")
        return True

    api_url = f"{API_BASE_URL}/api/activities/try-create"
    payload = {
        "citizenUsername": citizen_username,
        "activityType": activity_type,
        "activityDetails": activity_parameters
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("success"):
            log.info(f"{LogColors.OKGREEN}Successfully initiated activity '{activity_type}' for {citizen_username} via API. Response: {response_data.get('message', 'OK')}{LogColors.ENDC}")
            activity_info = response_data.get("activity") or (response_data.get("activities")[0] if isinstance(response_data.get("activities"), list) and response_data.get("activities") else None)
            if activity_info and activity_info.get("id"):
                 log.info(f"  Activity ID: {activity_info['id']}")
            return True
        else:
            error_msg = f"API call to initiate activity '{activity_type}' for {citizen_username} failed: {response_data.get('error', 'Unknown error')}"
            log.error(f"{LogColors.FAIL}{error_msg}{LogColors.ENDC}")
            if TELEGRAM_NOTIFICATION_ON_RESOLUTION_FAILURE:
                send_telegram_notification(f"❌ AutoResolve: {error_msg}\nPayload: {json.dumps(payload)}")
            return False
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed for activity '{activity_type}' for {citizen_username}: {e}"
        log.error(f"{LogColors.FAIL}{error_msg}{LogColors.ENDC}")
        if TELEGRAM_NOTIFICATION_ON_RESOLUTION_FAILURE:
            send_telegram_notification(f"❌ AutoResolve: {error_msg}\nPayload: {json.dumps(payload)}")
        return False
    except json.JSONDecodeError:
        response_text_snippet = response.text[:200] if 'response' in locals() and hasattr(response, 'text') else "N/A"
        error_msg = f"Failed to decode JSON response for activity '{activity_type}' for {citizen_username}. Response: {response_text_snippet}"
        log.error(f"{LogColors.FAIL}{error_msg}{LogColors.ENDC}")
        if TELEGRAM_NOTIFICATION_ON_RESOLUTION_FAILURE:
            send_telegram_notification(f"❌ AutoResolve: {error_msg}\nPayload: {json.dumps(payload)}")
        return False

# --- Problem Fetching ---
def get_active_problems(tables: Dict[str, Table]) -> List[Dict]:
    """Fetches all problems with status 'active'."""
    try:
        problems_raw = tables["problems"].all(formula="{Status}='active'")
        
        # Sort problems by severity (descending) then by CreatedAt (ascending)
        def sort_key(problem_record):
            severity_text = problem_record.get('fields', {}).get('Severity', "Medium")
            severity_numeric = SEVERITY_ORDER.get(severity_text, SEVERITY_ORDER["Medium"])
            created_at_text = problem_record.get('fields', {}).get('CreatedAt', "")
            # Ensure created_at_text is parsed correctly or provide a default for sorting
            try:
                created_at_dt = datetime.fromisoformat(created_at_text.replace("Z", "+00:00")) if created_at_text else datetime.min.replace(tzinfo=pytz.UTC)
            except ValueError:
                created_at_dt = datetime.min.replace(tzinfo=pytz.UTC) # Fallback for unparsable dates
            return (-severity_numeric, created_at_dt) # Negative for descending severity

        problems_sorted = sorted(problems_raw, key=sort_key)
        
        log.info(f"{LogColors.OKBLUE}Fetched {len(problems_sorted)} active problems, sorted by severity.{LogColors.ENDC}")
        return problems_sorted
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching active problems: {e}{LogColors.ENDC}")
        return []

# --- Utility functions for problem management ---
def _get_problem_failure_count(problem_notes: Optional[str]) -> int:
    if not problem_notes:
        return 0
    match = re.search(PROBLEM_MAX_FAILURES_NOTE_REGEX, problem_notes)
    return int(match.group(1)) if match else 0

def _update_problem_notes_with_failure_count(problem_notes: Optional[str], failure_count: int) -> str:
    current_notes = problem_notes or ""
    failure_tag = f"[Failures: {failure_count}]"
    
    match = re.search(PROBLEM_MAX_FAILURES_NOTE_REGEX, current_notes)
    if match:
        # Replace existing tag
        updated_notes = current_notes.replace(match.group(0), failure_tag)
    else:
        # Add new tag (prepend for visibility)
        updated_notes = f"{failure_tag}\n{current_notes}".strip()
    return updated_notes

def _escalate_problem_severity(current_severity_text: str) -> str:
    return SEVERITY_ESCALATION_MAP.get(current_severity_text, current_severity_text)

def _create_admin_notification_for_escalated_problem(tables: Dict[str, Table], problem: Dict, new_severity: str, failure_count: int):
    problem_fields = problem.get('fields', {})
    problem_title = problem_fields.get('Title', 'N/A')
    problem_id_rec = problem['id'] # Airtable record ID
    custom_problem_id = problem_fields.get('ProblemId', problem_id_rec) # Custom ProblemId for display

    content = (f"Problem Escalated: '{problem_title}' (ID: {custom_problem_id})\n"
               f"New Severity: {new_severity} after {failure_count} resolution failures.")
    try:
        tables["notifications"].create({
            "Citizen": "ConsiglioDeiDieci",
            "Type": "problem_escalation_auto_resolve",
            "Content": content,
            "Details": json.dumps({"problem_id": custom_problem_id, "title": problem_title, "new_severity": new_severity, "failures": failure_count}),
            "Status": "unread",
            "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat()
        })
        log.info(f"Admin notification created for escalated problem {custom_problem_id}.")
    except Exception as e:
        log.error(f"Failed to create admin notification for escalated problem {custom_problem_id}: {e}")

# --- Resolution Handlers ---

def resolve_resource_not_for_sale(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, building_type_defs: Dict, dry_run: bool) -> bool: # Added building_type_defs
    """Attempts to resolve a 'resource_not_for_sale' problem."""
    log.info(f"Attempting to resolve 'resource_not_for_sale': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset') # Asset is BuildingId
    resource_type = None
    
    title_match = re.search(r"Resource Not For Sale: (\w+)", problem['fields'].get('Title', ''))
    desc_match = re.search(r"resource '(\w+)' is not", problem['fields'].get('Description', ''))

    if title_match:
        resource_type = title_match.group(1)
    elif desc_match:
        resource_type = desc_match.group(1)
    
    if not building_id or not resource_type:
        log.error(f"  Missing BuildingId or ResourceType for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    operator_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not operator_username:
        log.error(f"  Building {building_id} has no operator. Cannot resolve problem {problem['id']}.")
        return False

    res_def = resource_defs.get(resource_type, {})
    # Price: importPrice + DEFAULT_SELL_CONTRACT_MARKUP_PERCENTAGE
    base_price = float(res_def.get('importPrice', 10.0))
    price = round(base_price * (1 + DEFAULT_SELL_CONTRACT_MARKUP_PERCENTAGE / 100.0), 2)
    
    # Target Amount: % of remaining storage capacity
    building_type_str = building_record['fields'].get('Type')
    building_def = building_type_defs.get(building_type_str, {})
    storage_capacity = float(building_def.get('productionInformation', {}).get('storageCapacity', 0.0))
    
    # Get current total stock in building (all resources)
    current_total_stock = 0.0
    try:
        all_resources_in_building = tables['resources'].all(formula=f"{{Asset}}='{_escape_airtable_value(building_id)}'")
        for r_stock in all_resources_in_building:
            current_total_stock += float(r_stock['fields'].get('Count', 0.0))
    except Exception as e_stock:
        log.warning(f"Could not fetch total stock for {building_id} to calculate target amount: {e_stock}. Using default.")
        current_total_stock = storage_capacity # Assume full if error, leading to small target amount

    remaining_capacity = max(0.0, storage_capacity - current_total_stock)
    target_amount = round(remaining_capacity * DEFAULT_TARGET_AMOUNT_STORAGE_PERCENTAGE, 2)
    
    # Ensure target_amount is at least a small positive value if there's any capacity, or if capacity is 0 (e.g. market stall)
    if storage_capacity == 0: # For buildings with no defined storage (like market stalls)
        target_amount = 20.0 # Default small amount
    elif target_amount < 1.0 and remaining_capacity > 0: # If calculated amount is too small but there's space
        target_amount = max(1.0, round(remaining_capacity * 0.1, 2)) # Try 10% or at least 1
    elif target_amount < 1.0 and remaining_capacity <=0: # No space
        target_amount = 0.0 # Cannot sell if no space to even hold 1 unit for sale logic

    if target_amount == 0.0:
        log.warning(f"  Building {building_id} has no remaining storage capacity. Cannot create sell contract for {resource_type}.")
        # This isn't a failure of the resolver itself, but a condition preventing resolution.
        # We might want to update the problem notes differently or return a specific status.
        # For now, let it proceed, the activity might fail or create a 0 amount contract.
        # Or, better, return False here as we can't meaningfully resolve.
        return False


    activity_params = {
        "resourceType": resource_type,
        "pricePerResource": price, # Already rounded
        "targetAmount": target_amount, # Already rounded
        "sellerBuildingId": building_id,
        "title": f"Auto-created sale: {resource_type} from {building_record['fields'].get('Name', building_id)}",
        "description": f"Automated public sell contract created to resolve problem: {problem['fields'].get('Title')}"
    }
    log.info(f"  Calling try-create for 'manage_public_sell_contract' for {operator_username}, building {building_id}, resource {resource_type}.")
    return call_try_create_activity_api(operator_username, "manage_public_sell_contract", activity_params, dry_run)

def resolve_no_markup_buy_contract_for_input(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, building_type_defs: Dict, dry_run: bool) -> bool: # Added building_type_defs
    """Attempts to resolve a 'no_markup_buy_contract_for_input' problem."""
    log.info(f"Attempting to resolve 'no_markup_buy_contract_for_input': {problem['fields'].get('Title')}")
    buyer_building_id = problem['fields'].get('Asset') 

    # Example Title for input: "Missing Purchase Contract for Inputs: iron_ore at 'Blacksmith (ID: bld_blacksmith_xyz)'"
    # Example Description for input: "...missing inputs (iron_ore) to produce..."
    # Example Title for final product: "No Markup Buy Contract: wine at 'Tavern (bld_tavern_1)'"
    
    input_resource_type = None
    problem_title = problem['fields'].get('Title', '')
    problem_description = problem['fields'].get('Description', '')

    # Try regex for "Inputs: resource_name" in title
    title_match_input_style1 = re.search(r"Inputs: (\w+)", problem_title)
    if title_match_input_style1:
        input_resource_type = title_match_input_style1.group(1)
    
    # If not found, try regex for "missing inputs (resource_name)" in description
    if not input_resource_type:
        desc_match_input_style = re.search(r"missing inputs \((\w+)\)", problem_description)
        if desc_match_input_style:
            input_resource_type = desc_match_input_style.group(1)

    # If still not found, try regex for "No Markup Buy Contract: resource_name" in title (final product case)
    if not input_resource_type:
        title_match_final_product_style = re.search(r"No Markup Buy Contract: (\w+)", problem_title)
        if title_match_final_product_style:
            input_resource_type = title_match_final_product_style.group(1)
    
    # If still not found, try regex for "Supplier Shortage for Inputs: resource_name" (used by supplier_shortage resolver, but good to have robust parsing)
    # This is more for future-proofing if titles change slightly or for other problem types that might call this.
    if not input_resource_type:
        title_match_supplier_shortage_style = re.search(r"Supplier Shortage for Inputs: (\w+)", problem_title)
        if title_match_supplier_shortage_style:
            input_resource_type = title_match_supplier_shortage_style.group(1)

    if not buyer_building_id or not input_resource_type:
        log.error(f"  Missing BuyerBuildingId or InputResourceType for problem {problem['id']}. Title: '{problem_title}'. Cannot resolve.")
        return False

    building_record = get_building_record(tables, buyer_building_id)
    if not building_record:
        log.error(f"  Buyer building {buyer_building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    operator_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not operator_username:
        log.error(f"  Buyer building {buyer_building_id} has no operator. Cannot resolve problem {problem['id']}.")
        return False

    res_def = resource_defs.get(input_resource_type, {})
    max_price = round(float(res_def.get('importPrice', 10.0)) * 1.5, 2) # Keep 50% markup for now, or make it a constant

    # Target Amount: % of remaining storage capacity
    building_type_str = building_record['fields'].get('Type')
    building_def = building_type_defs.get(building_type_str, {}) # Requires building_type_defs
    storage_capacity = float(building_def.get('productionInformation', {}).get('storageCapacity', 0.0))
    
    current_total_stock = 0.0
    try:
        all_resources_in_building = tables['resources'].all(formula=f"{{Asset}}='{_escape_airtable_value(buyer_building_id)}'")
        for r_stock in all_resources_in_building:
            current_total_stock += float(r_stock['fields'].get('Count', 0.0))
    except Exception as e_stock_buy:
        log.warning(f"Could not fetch total stock for {buyer_building_id} to calculate target buy amount: {e_stock_buy}. Using default.")
        current_total_stock = 0 # Assume empty if error, leading to larger target amount

    remaining_capacity = max(0.0, storage_capacity - current_total_stock)
    target_amount = round(remaining_capacity * DEFAULT_TARGET_AMOUNT_STORAGE_PERCENTAGE, 2)

    if target_amount < 1.0: # Ensure we try to buy at least 1 if there's any capacity or if capacity is 0
        if storage_capacity == 0: target_amount = 20.0 # Default for no-storage buildings
        else: target_amount = max(1.0, round(remaining_capacity * 0.1, 2)) # Try 10% or at least 1

    # Define the deterministic ContractId for the main markup_buy contract for this resource and business
    deterministic_main_contract_id = f"markup_buy_main_{buyer_building_id}_{input_resource_type}"

    activity_params = {
        "contractId_to_create_if_new": deterministic_main_contract_id, # Added this line
        "resourceType": input_resource_type,
        "targetAmount": target_amount, # Already rounded
        "maxPricePerResource": round(max_price, 2),
        "buyerBuildingId": buyer_building_id,
        "title": f"Auto-buy: {input_resource_type} for {building_record['fields'].get('Name', buyer_building_id)}",
        "description": f"Automated markup buy contract for input {input_resource_type} to resolve problem: {problem['fields'].get('Title')}"
    }
    log.info(f"  Calling try-create for 'manage_markup_buy_contract' for {operator_username}, building {buyer_building_id}, resource {input_resource_type}, contractId: {deterministic_main_contract_id}.")
    return call_try_create_activity_api(operator_username, "manage_markup_buy_contract", activity_params, dry_run)

def resolve_hungry_citizen(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    """Attempts to resolve a 'hungry_citizen' problem by initiating an 'eat' activity."""
    citizen_username = problem['fields'].get('Citizen')
    log.info(f"Attempting to resolve 'hungry_citizen' for {citizen_username}.")

    if not citizen_username:
        log.error(f"  Missing Citizen username for problem {problem['id']}. Cannot resolve 'hungry_citizen'.")
        return False

    # The 'eat' activity type is generic.
    # Speculative fix for 400 error: ensure activityDetails is not empty.
    # The Python engine's dispatcher for "eat" uses params.get("strategy", "default_order"),
    # so explicitly sending this shouldn't change behavior if the dispatcher is reached,
    # but might prevent a 400 if the issue is with an empty activityParameters dict earlier.
    # Reverting to empty dict as sending "strategy" might cause 400 if Pydantic model is strict.
    activity_params = {} 
    log.info(f"  Calling try-create for 'eat' activity for {citizen_username} with params: {activity_params}.")
    return call_try_create_activity_api(citizen_username, "eat", activity_params, dry_run)

def _calculate_new_value_percentage_change(current_value: float, percentage_change: float, is_increase: bool, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
    """Calculates a new value after a percentage change, with optional min/max clamping."""
    if is_increase:
        new_value = current_value * (1 + percentage_change / 100.0)
    else:
        new_value = current_value * (1 - percentage_change / 100.0)
    
    if min_value is not None:
        new_value = max(new_value, min_value)
    if max_value is not None:
        new_value = min(new_value, max_value)
    return round(new_value, 2) # Round to 2 decimal places for currency/prices

def resolve_no_operator_for_stock(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    """Attempts to resolve 'no_operator_for_stock' by increasing building wages."""
    log.info(f"Attempting to resolve 'no_operator_for_stock': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    # Action performer is RunBy or Owner of the building
    action_performer_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not action_performer_username:
        log.error(f"  Building {building_id} has no RunBy or Owner. Cannot adjust wages for problem {problem['id']}.")
        return False

    current_wages = float(building_record['fields'].get('Wages', 0.0))
    failure_count = _get_problem_failure_count(problem['fields'].get('Notes'))
    
    # Dynamic wage increase
    increase_percentage = DEFAULT_WAGE_INCREASE_BASE_PERCENTAGE + (failure_count * WAGE_INCREASE_PER_FAILURE_PERCENTAGE)
    new_wages = _calculate_new_value_percentage_change(current_wages, increase_percentage, is_increase=True, min_value=1.0)

    activity_params = {
        "businessBuildingId": building_id,
        "newWageAmount": new_wages, # Already rounded
        "strategy": "auto_resolve_no_operator"
    }
    log.info(f"  Calling try-create for 'adjust_business_wages' for {action_performer_username}, building {building_id}, new wages {new_wages}.")
    return call_try_create_activity_api(action_performer_username, "adjust_business_wages", activity_params, dry_run)

def resolve_waiting_for_production(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    """Attempts to resolve 'waiting_for_production' if no occupant by increasing wages."""
    log.info(f"Attempting to resolve 'waiting_for_production': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    if building_record['fields'].get('Occupant'):
        log.info(f"  Building {building_id} has an Occupant. No action taken for 'waiting_for_production'.")
        return False # No action if occupant exists

    action_performer_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not action_performer_username:
        log.error(f"  Building {building_id} has no RunBy or Owner. Cannot adjust wages for problem {problem['id']}.")
        return False
        
    current_wages = float(building_record['fields'].get('Wages', 0.0))
    new_wages = _calculate_new_value_percentage_change(current_wages, 2.0, is_increase=True, min_value=1.0)

    activity_params = {
        "businessBuildingId": building_id,
        "newWageAmount": new_wages,
        "strategy": "auto_resolve_waiting_for_production_no_occupant"
    }
    log.info(f"  No Occupant. Calling try-create for 'adjust_business_wages' for {action_performer_username}, building {building_id}, new wages {new_wages}.")
    return call_try_create_activity_api(action_performer_username, "adjust_business_wages", activity_params, dry_run)

def resolve_supplier_or_resource_shortage(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, dry_run: bool) -> bool:
    """Attempts to resolve supplier/resource shortage by increasing price on the main markup_buy contract."""
    problem_type = problem['fields'].get('Type') # 'supplier_shortage' or 'resource_shortage'
    log.info(f"Attempting to resolve '{problem_type}': {problem['fields'].get('Title')}")
    
    buyer_building_id = problem['fields'].get('Asset')
    # ResourceType needs to be extracted from Title or Description
    # Example Title for supplier_shortage: "Supplier Shortage for Inputs: iron_ore at 'Blacksmith (bld_blacksmith_xyz)'"
    # Example Title for resource_shortage: "Resource Shortage: wine for 'Tavern (bld_tavern_abc)'"
    resource_type = None
    title = problem['fields'].get('Title', '')
    if "Inputs: " in title: # supplier_shortage format
        match = re.search(r"Inputs: (\w+)", title)
        if match: resource_type = match.group(1)
    elif "Resource Shortage: " in title: # resource_shortage format
        match = re.search(r"Resource Shortage: (\w+)", title)
        if match: resource_type = match.group(1)
    
    if not buyer_building_id or not resource_type:
        log.error(f"  Missing BuyerBuildingId or ResourceType for problem {problem['id']} ({problem_type}). Title: {title}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, buyer_building_id)
    if not building_record:
        log.error(f"  Buyer building {buyer_building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    operator_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not operator_username:
        log.error(f"  Buyer building {buyer_building_id} has no operator. Cannot resolve problem {problem['id']}.")
        return False

    # Deterministic ContractId for the main markup_buy contract
    deterministic_main_contract_id = f"markup_buy_main_{buyer_building_id}_{resource_type}"
    contract_record = get_contract_record(tables, deterministic_main_contract_id)

    current_max_price = 0.0
    if contract_record:
        current_max_price = float(contract_record['fields'].get('PricePerResource', 0.0)) # PricePerResource is MaxPrice for markup_buy
    else:
        # If no contract, this isn't a shortage problem, but a "no_markup_buy_contract" problem.
        # However, automated_adjustmarkupbuys might create it. For now, if no contract, use import price as base.
        res_def = resource_defs.get(resource_type, {})
        current_max_price = float(res_def.get('importPrice', 10.0))
        log.warning(f"  No existing markup_buy contract '{deterministic_main_contract_id}' found. Basing price increase on import price for {resource_type}.")

    new_max_price = _calculate_new_value_percentage_change(current_max_price, 15.0, is_increase=True, min_value=1.0) # Increase by 15%

    activity_params = {
        "contractId_to_create_if_new": deterministic_main_contract_id,
        "resourceType": resource_type,
        "targetAmount": problem['fields'].get('TargetAmount', 50.0), # Use problem's target amount or default
        "maxPricePerResource": new_max_price,
        "buyerBuildingId": buyer_building_id,
        "title": f"Update Markup Buy (Shortage): {resource_type} for {building_record['fields'].get('Name', buyer_building_id)}",
        "description": f"Automated update to markup buy contract for {resource_type} due to {problem_type}."
    }
    log.info(f"  Calling try-create for 'manage_markup_buy_contract' for {operator_username}, contract {deterministic_main_contract_id}, new maxPrice {new_max_price}.")
    return call_try_create_activity_api(operator_username, "manage_markup_buy_contract", activity_params, dry_run)

def resolve_no_import_contract(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, dry_run: bool) -> bool:
    log.info(f"Attempting to resolve 'no_import_contract': {problem['fields'].get('Title')}")
    buyer_building_id = problem['fields'].get('Asset')
    # Extract resourceType from title, e.g., "No Import Contract: timber at 'Warehouse (bld_warehouse_1)'"
    resource_type_match = re.search(r"No Import Contract: (\w+)", problem['fields'].get('Title', ''))
    resource_type = resource_type_match.group(1) if resource_type_match else None

    if not buyer_building_id or not resource_type:
        log.error(f"  Missing BuyerBuildingId or ResourceType for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, buyer_building_id)
    if not building_record:
        log.error(f"  Buyer building {buyer_building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    operator_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not operator_username:
        log.error(f"  Buyer building {buyer_building_id} has no operator. Cannot resolve problem {problem['id']}.")
        return False

    res_def = resource_defs.get(resource_type, {})
    price_per_resource = float(res_def.get('importPrice', 10.0)) # Use importPrice as the contract price
    target_amount = 100.0 # Default import amount

    activity_params = {
        "resourceType": resource_type,
        "targetAmount": target_amount,
        "pricePerResource": round(price_per_resource, 2),
        "buyerBuildingId": buyer_building_id,
        "title": f"Auto-Import: {resource_type} for {building_record['fields'].get('Name', buyer_building_id)}",
        "description": f"Automated import contract for {resource_type} to resolve problem: {problem['fields'].get('Title')}"
    }
    log.info(f"  Calling try-create for 'manage_import_contract' for {operator_username}, building {buyer_building_id}, resource {resource_type}.")
    return call_try_create_activity_api(operator_username, "manage_import_contract", activity_params, dry_run)

def resolve_no_markup_buy_contract_final_product(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, building_type_defs: Dict, dry_run: bool) -> bool: # Added building_type_defs
    """Resolves 'no_markup_buy_contract' for a final product (similar to input, but might have different defaults)."""
    log.info(f"Attempting to resolve 'no_markup_buy_contract' (final product): {problem['fields'].get('Title')}")
    buyer_building_id = problem['fields'].get('Asset')
    # Extract resourceType from title, e.g., "No Markup Buy Contract: wine at 'Tavern (bld_tavern_1)'"
    resource_type_match = re.search(r"No Markup Buy Contract: (\w+)", problem['fields'].get('Title', ''))
    resource_type = resource_type_match.group(1) if resource_type_match else None

    if not buyer_building_id or not resource_type:
        log.error(f"  Missing BuyerBuildingId or ResourceType for problem {problem['id']}. Cannot resolve.")
        return False
    # Rest is identical to resolve_no_markup_buy_contract_for_input
    return resolve_no_markup_buy_contract_for_input(problem, tables, resource_defs, building_type_defs, dry_run) # Pass building_type_defs


def resolve_no_occupant(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    """Attempts to resolve 'no_occupant' by increasing building wages."""
    log.info(f"Attempting to resolve 'no_occupant': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    action_performer_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not action_performer_username:
        log.error(f"  Building {building_id} has no RunBy or Owner. Cannot adjust wages for problem {problem['id']}.")
        return False
        
    current_wages = float(building_record['fields'].get('Wages', 0.0))
    new_wages = _calculate_new_value_percentage_change(current_wages, 2.0, is_increase=True, min_value=1.0)

    activity_params = {
        "businessBuildingId": building_id,
        "newWageAmount": new_wages,
        "strategy": "auto_resolve_no_occupant"
    }
    log.info(f"  Calling try-create for 'adjust_business_wages' for {action_performer_username}, building {building_id}, new wages {new_wages}.")
    return call_try_create_activity_api(action_performer_username, "adjust_business_wages", activity_params, dry_run)

def resolve_vacant_building(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    log.info(f"Attempting to resolve 'vacant_building': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    category = building_record['fields'].get('Category')
    owner_username = building_record['fields'].get('Owner') # For homes, owner adjusts rent
    operator_username = building_record['fields'].get('RunBy') or owner_username # For businesses, operator adjusts wages

    if not operator_username: # Needed for both cases if owner is also operator
        log.error(f"  Building {building_id} has no operator/owner. Cannot resolve vacancy problem {problem['id']}.")
        return False

    if category == 'business':
        current_wages = float(building_record['fields'].get('Wages', 0.0))
        new_wages = _calculate_new_value_percentage_change(current_wages, 2.0, is_increase=True, min_value=1.0)
        activity_params = {"businessBuildingId": building_id, "newWageAmount": new_wages, "strategy": "auto_resolve_vacant_business"}
        log.info(f"  Vacant business. Calling 'adjust_business_wages' for {operator_username}, building {building_id}, new wages {new_wages}.")
        return call_try_create_activity_api(operator_username, "adjust_business_wages", activity_params, dry_run)
    elif category == 'home':
        if not owner_username: # Specifically need owner for rent adjustment
            log.error(f"  Vacant home {building_id} has no Owner. Cannot adjust rent for problem {problem['id']}.")
            return False
        current_rent = float(building_record['fields'].get('RentPrice', 0.0))
        new_rent = _calculate_new_value_percentage_change(current_rent, 2.0, is_increase=False, min_value=0.0) # Decrease rent, min 0
        activity_params = {"buildingId": building_id, "newRentPrice": new_rent, "strategy": "auto_resolve_vacant_home"}
        log.info(f"  Vacant home. Calling 'adjust_building_rent_price' for {owner_username}, building {building_id}, new rent {new_rent}.")
        return call_try_create_activity_api(owner_username, "adjust_building_rent_price", activity_params, dry_run)
    else:
        log.warning(f"  Building {building_id} is of category '{category}'. No specific vacancy resolution implemented.")
        return False

def resolve_zero_rent_building(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    log.info(f"Attempting to resolve 'zero_rent_building': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    owner_username = building_record['fields'].get('Owner')
    if not owner_username:
        log.error(f"  Building {building_id} has no Owner. Cannot adjust rent for problem {problem['id']}.")
        return False
    
    # Determine a "reasonable" starting rent, considering failure count
    failure_count = _get_problem_failure_count(problem['fields'].get('Notes'))
    # Use new BASE_STARTING_RENT
    # Add a small *decrease* bonus per failure to make it more attractive over time if it's still zero.
    # This logic might be counterintuitive if the goal is just to set *a* rent.
    # Let's assume for "zero_rent" the goal is to set a base rent, and failures mean it wasn't attractive enough to get an occupant.
    # However, the problem is "zero_rent", not "vacant_home_with_rent". So, just setting a base is fine.
    # If it becomes vacant later *with* this rent, then resolve_vacant_building would decrease it.
    # For now, let's just set it to BASE_STARTING_RENT, and failures don't change this initial set.
    # If we want failures to influence the *initial* setting from zero, we'd need a different logic.
    # Sticking to the simple "set to base if zero":
    new_rent = BASE_STARTING_RENT
    # If we wanted failures to make the initial rent lower:
    # rent_decrease_per_failure = 50.0 # Example
    # new_rent = round(BASE_STARTING_RENT - (failure_count * rent_decrease_per_failure), 2)
    # new_rent = max(new_rent, 0.0) # Ensure rent is not negative

    activity_params = {"buildingId": building_id, "newRentPrice": new_rent, "strategy": "auto_resolve_zero_rent"}
    log.info(f"  Calling 'adjust_building_rent_price' for {owner_username}, building {building_id}, new rent {new_rent} (failures affecting initial set: {failure_count}).")
    return call_try_create_activity_api(owner_username, "adjust_building_rent_price", activity_params, dry_run)

def resolve_zero_wages_business(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    log.info(f"Attempting to resolve 'zero_wages_business': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    operator_username = building_record['fields'].get('RunBy') or building_record['fields'].get('Owner')
    if not operator_username:
        log.error(f"  Building {building_id} has no operator/owner. Cannot adjust wages for problem {problem['id']}.")
        return False
        
    # Determine "reasonable" starting wages, considering failure count
    failure_count = _get_problem_failure_count(problem['fields'].get('Notes'))
    # Use new BASE_STARTING_WAGE
    # Add a bonus per failure to make it more attractive over time
    # The bonus could be a percentage of the base, or a flat amount. Let's use a flat amount for now.
    wage_bonus_per_failure = 50.0 # Example: 50 Ducats bonus per failure count
    new_wages = round(BASE_STARTING_WAGE + (failure_count * wage_bonus_per_failure), 2)
    new_wages = max(new_wages, 1.0) # Ensure at least 1

    activity_params = {"businessBuildingId": building_id, "newWageAmount": new_wages, "strategy": "auto_resolve_zero_wages"}
    log.info(f"  Calling 'adjust_business_wages' for {operator_username}, building {building_id}, new wages {new_wages} (failures: {failure_count}).")
    return call_try_create_activity_api(operator_username, "adjust_business_wages", activity_params, dry_run)

def resolve_do_nothing(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> str: # Changed return type
    """Resolver for problems where the defined action is to do nothing."""
    problem_type = problem['fields'].get('Type')
    log.info(f"Problem type '{problem_type}' for problem '{problem['fields'].get('Title')}' is configured for no automated action. Skipping.")
    return "NO_ACTION_INTENDED" # Return specific string

# --- Main Processing Logic ---
def auto_resolve_problems_main(dry_run: bool = False, problem_type_filter: Optional[str] = None):
    log_header(f"Auto Problem Resolution Process (dry_run={dry_run})", LogColors.HEADER)

    tables = initialize_airtable()
    if not tables:
        return

    resource_defs = get_resource_types_from_api(API_BASE_URL)
    building_type_defs = get_building_types_from_api(API_BASE_URL) # Load building type definitions

    active_problems = get_active_problems(tables)
    if not active_problems:
        log.info("No active problems found to resolve.")
        return

    problems_to_process = active_problems
    if problem_type_filter:
        problems_to_process = [p for p in active_problems if p['fields'].get('Type') == problem_type_filter]
        log.info(f"Filtered to {len(problems_to_process)} problems of type '{problem_type_filter}'.")

    resolved_count = 0
    attempted_count = 0

    resolver_map = {
        "resource_not_for_sale": resolve_resource_not_for_sale, # 1. Oui
        "no_operator_for_stock": resolve_no_operator_for_stock, # 2. Augmente wages
        "waiting_for_production": resolve_waiting_for_production, # 3. Si pas d'Occupant: Augmente wages
        "no_markup_buy_contract_for_input": resolve_no_markup_buy_contract_for_input, # 4. Oui
        "supplier_shortage": resolve_supplier_or_resource_shortage, # 5. Oui (augmente prix markup_buy)
        "waiting_on_input_delivery": resolve_do_nothing, # 6. Oui (ne rien faire pour l'instant)
        "no_import_contract": resolve_no_import_contract, # 7. Oui, manage_import_contract
        "waiting_for_galley_unloading": resolve_do_nothing, # 8. Ne rien faire
        "waiting_for_galley_arrival": resolve_do_nothing, # 9. Oui (ne rien faire)
        "no_markup_buy_contract": resolve_no_markup_buy_contract_final_product, # 10. Oui (similaire à 4)
        "resource_shortage": resolve_do_nothing, # 11. Ne rien faire (modifié)
        "waiting_for_resource_delivery": resolve_do_nothing, # 12. Ne rien faire
        "no_occupant": resolve_no_occupant, # 13. Augmente wages
        "homeless_citizen": resolve_do_nothing, # 14. Ne rien faire
        "workless_citizen": resolve_do_nothing, # 15. Ne rien faire
        "vacant_building": resolve_vacant_building, # 16. Augmente wages (business) / Diminue rent (home)
        "hungry_citizen": resolve_hungry_citizen, # 17. Oui
        "zero_rent_building": resolve_zero_rent_building, # 18. Oui
        "zero_wages_business": resolve_zero_wages_business, # 19. Oui
    }

    for problem in problems_to_process:
        problem_id_rec = problem['id'] # Airtable record ID
        problem_fields = problem.get('fields', {})
        custom_problem_id = problem_fields.get('ProblemId', problem_id_rec) # Use custom ProblemId for logging, fallback to rec ID
        problem_type = problem_fields.get('Type')
        problem_title = problem_fields.get('Title', 'Untitled Problem')

        log.info(f"{LogColors.OKCYAN}--- Processing Problem: {problem_title} (Type: {problem_type}, ID: {custom_problem_id}) ---{LogColors.ENDC}")
        
        resolver_func = resolver_map.get(problem_type)
        if resolver_func:
            attempted_count += 1
            # Pass necessary context to resolver
            # Most resolvers need `problem, tables, dry_run`. Some need `resource_defs` and/or `building_type_defs`.
            if problem_type in [
                "resource_not_for_sale", 
                "no_markup_buy_contract_for_input", 
                "no_markup_buy_contract", 
                "supplier_shortage", 
                "no_import_contract"
                # "resource_shortage" was here, now moved to do_nothing group
            ]:
                # Check which ones specifically need building_type_defs
                if problem_type in ["resource_not_for_sale", "no_markup_buy_contract_for_input", "no_markup_buy_contract"]:
                    resolution_status = resolver_func(problem, tables, resource_defs, building_type_defs, dry_run)
                else: # supplier_shortage, no_import_contract (these only need resource_defs)
                    resolution_status = resolver_func(problem, tables, resource_defs, dry_run)
            elif problem_type in [
                "no_operator_for_stock", 
                "waiting_for_production", 
                "no_occupant",
                "vacant_building",
                "hungry_citizen",
                "zero_rent_building",
                "zero_wages_business",
                "waiting_on_input_delivery", # do_nothing
                "waiting_for_galley_unloading", # do_nothing
                "waiting_for_galley_arrival", # do_nothing
                "waiting_for_resource_delivery", # do_nothing
                "homeless_citizen", # do_nothing
                "workless_citizen", # do_nothing
                "resource_shortage" # do_nothing (moved here)
            ]:
                resolution_status = resolver_func(problem, tables, dry_run)
            elif problem_type in [
                "no_operator_for_stock", 
                "waiting_for_production", 
                "no_occupant",
                "vacant_building",
                "hungry_citizen",
                "zero_rent_building",
                "zero_wages_business",
                "waiting_on_input_delivery", # do_nothing
                "waiting_for_galley_unloading", # do_nothing
                "waiting_for_galley_arrival", # do_nothing
                "waiting_for_resource_delivery", # do_nothing
                "homeless_citizen", # do_nothing
                "workless_citizen", # do_nothing
                "resource_shortage" # do_nothing (moved here)
            ]:
                resolution_status = resolver_func(problem, tables, dry_run)
            else:
                # Fallback for any resolver not explicitly categorized, assuming it doesn't need resource_defs
                log.warning(f"  Resolver for {problem_type} called with default context (problem, tables, dry_run). This might be an issue if it needs more specific context like resource_defs.")
                resolution_status = resolver_func(problem, tables, dry_run)

            if resolution_status is True: # Explicitly check for True
                resolved_count += 1
                log.info(f"  Successfully initiated resolution for problem {custom_problem_id} ({problem_title}).")
                if not dry_run:
                    try:
                        # If resolution activity was successfully initiated, delete the problem record.
                        tables["problems"].delete(problem_id_rec) # Use Airtable record ID for delete
                        log.info(f"  Problem {custom_problem_id} ('{problem_title}') deleted as resolution activity was initiated.")
                    except Exception as e_delete:
                        log.error(f"  Failed to delete problem {custom_problem_id} (RecID: {problem_id_rec}) after successful resolution attempt: {e_delete}")
                        # Fallback: update status if delete fails
                        try:
                            original_notes = problem_fields.get('Notes', '')
                            attempt_note = f"Resolution attempted (delete failed) by autoResolveProblems.py at {datetime.now(VENICE_TIMEZONE).isoformat()}."
                            updated_notes_on_success = f"{attempt_note}\n{original_notes}".strip()
                            tables["problems"].update(problem_id_rec, {"Status": "resolution_attempted", "Notes": updated_notes_on_success}) # Use Airtable record ID for update
                            log.info(f"  Updated problem {custom_problem_id} status to 'resolution_attempted' as delete failed.")
                        except Exception as e_update_fallback:
                            log.error(f"  Failed to update status for problem {custom_problem_id} as fallback: {e_update_fallback}")
            elif resolution_status == "NO_ACTION_INTENDED":
                log.info(f"  No automated action intended for problem {custom_problem_id} ({problem_title}). Skipping failure count update.")
                # Do not increment resolved_count, do not update problem notes or severity
            else: # Resolution attempt failed (resolver returned False or API call failed)
                log.warning(f"  Failed to initiate resolution for problem {custom_problem_id} ({problem_title}). Resolver status: {resolution_status}")
                if not dry_run:
                    original_notes = problem_fields.get('Notes', '')
                    failure_count = _get_problem_failure_count(original_notes) + 1
                    new_notes_with_failure = _update_problem_notes_with_failure_count(original_notes, failure_count)
                    
                    update_fields_on_failure = {"Notes": new_notes_with_failure}
                    
                    if failure_count > MAX_RESOLUTION_FAILURES_BEFORE_SEVERITY_INCREASE:
                        current_severity = problem_fields.get('Severity', "Medium")
                        new_severity = _escalate_problem_severity(current_severity)
                        if new_severity != current_severity:
                            update_fields_on_failure["Severity"] = new_severity
                            log.warning(f"  Problem {custom_problem_id} severity escalated to {new_severity} after {failure_count} failures.")
                            _create_admin_notification_for_escalated_problem(tables, problem, new_severity, failure_count) # problem (full record) is passed
                        else:
                            log.info(f"  Problem {custom_problem_id} already at max severity '{current_severity}' or no escalation defined.")
                    
                    try:
                        tables["problems"].update(problem_id_rec, update_fields_on_failure) # Use Airtable record ID for update
                        log.info(f"  Updated problem {custom_problem_id} notes with failure count: {failure_count}.")
                    except Exception as e_update_fail:
                        log.error(f"  Failed to update notes/severity for failed problem {custom_problem_id} (RecID: {problem_id_rec}): {e_update_fail}")
        else:
            log.warning(f"  No resolver implemented for problem type: {problem_type}")

    log.info(f"{LogColors.OKGREEN}Auto Problem Resolution process finished.{LogColors.ENDC}")
    log.info(f"Attempted to resolve: {attempted_count} problems.")
    log.info(f"Successfully initiated resolution for: {resolved_count} problems.")

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automatically attempt to resolve active problems.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, performs a dry run and does not make API calls or save changes to Airtable."
    )
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        help="Optional: Filter problems by a specific type to resolve only those."
    )
    args = parser.parse_args()

    auto_resolve_problems_main(dry_run=args.dry_run, problem_type_filter=args.type)

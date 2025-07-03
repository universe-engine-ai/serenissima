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
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
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
    if storage_capacity == 0: # For buildings with no defined storage (like market stalls or public docks)
        target_amount = 20.0 # Default small amount for buildings with no defined storage
        log.info(f"  Building {building_id} has no defined storage capacity. Using default target amount of {target_amount} for {resource_type}.")
    elif target_amount < 1.0 and remaining_capacity > 0: # If calculated amount is too small but there's space
        target_amount = max(1.0, round(remaining_capacity * 0.1, 2)) # Try 10% or at least 1
    elif target_amount < 1.0 and remaining_capacity <= 0: # No space
        # All buildings should be able to sell regardless of storage capacity
        target_amount = 5.0 # Default amount for buildings with no remaining capacity
        log.info(f"  Building {building_id} ({building_type_str}) has no remaining capacity. Using default target amount of {target_amount} for {resource_type}.")


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
    
    # Try regex for "Input: resource_name" in title (singular form)
    if not input_resource_type:
        title_match_input_singular = re.search(r"Input: (\w+)", problem_title)
        if title_match_input_singular:
            input_resource_type = title_match_input_singular.group(1)
    
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
            
    # If still not found, try regex for "Missing Purchase Contract for Input: resource_name" in title
    if not input_resource_type:
        title_match_missing_purchase = re.search(r"Missing Purchase Contract for Input: (\w+)", problem_title)
        if title_match_missing_purchase:
            input_resource_type = title_match_missing_purchase.group(1)

    # Extract building ID from title if not already set
    if not buyer_building_id:
        # Try to extract building ID from title format like "at 'Building Name (ID: bld_xyz)'"
        building_id_match = re.search(r"at '.*?\((ID: )?(bld_[\w\.]+)\)'", problem_title)
        if building_id_match:
            buyer_building_id = building_id_match.group(2)
            log.info(f"  Extracted building ID from title: {buyer_building_id}")
        
        # If still not found, try to extract from Asset field directly
        if not buyer_building_id:
            buyer_building_id = problem['fields'].get('Asset')
            log.info(f"  Using Asset field as building ID: {buyer_building_id}")
    
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

def resolve_waiting_for_production(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, building_type_defs: Dict, dry_run: bool) -> bool:
    """Attempts to resolve 'waiting_for_production' by checking for existing production activity or creating one."""
    log.info(f"Attempting to resolve 'waiting_for_production': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    occupant_username = building_record['fields'].get('Occupant')
    if not occupant_username:
        # If no occupant, try to increase wages to attract workers
        log.info(f"  Building {building_id} has no Occupant. Attempting to increase wages.")
        
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
    
    # Check if there's already an active production activity for this building
    try:
        production_activity_formula = f"AND({{FromBuilding}}='{_escape_airtable_value(building_id)}', {{Type}}='production', OR({{Status}}='created', {{Status}}='in_progress'))"
        existing_activities = tables['activities'].all(formula=production_activity_formula)
        
        if existing_activities:
            log.info(f"  Found existing production activity for building {building_id}. No need to create a new one.")
            return True
    except Exception as e:
        log.warning(f"  Error checking for existing production activities: {e}")
    
    # No existing production activity found, try to create one
    log.info(f"  No active production activity found for building {building_id}. Attempting to create one.")
    
    # Get building type to find production recipes
    building_type = building_record['fields'].get('Type')
    if not building_type:
        log.error(f"  Building {building_id} has no Type defined. Cannot determine production recipe.")
        return False
    
    building_def = building_type_defs.get(building_type, {})
    production_info = building_def.get('productionInformation', {})
    recipes = production_info.get('Arti', [])
    
    if not recipes:
        log.warning(f"  No production recipes found for building type {building_type}. Cannot create production activity.")
        return False
    
    # Check if building has required inputs for any recipe
    for recipe in recipes:
        inputs = recipe.get('inputs', {})
        if not inputs:
            continue
        
        # Check if all inputs are available in sufficient quantity
        all_inputs_available = True
        for input_type, required_amount in inputs.items():
            # Get resource stock at building
            try:
                resource_formula = f"AND({{Asset}}='{_escape_airtable_value(building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(input_type)}')"
                resource_records = tables['resources'].all(formula=resource_formula)
                
                total_available = sum(float(r['fields'].get('Count', 0)) for r in resource_records)
                if total_available < required_amount:
                    all_inputs_available = False
                    log.info(f"  Insufficient {input_type} for production: need {required_amount}, have {total_available}")
                    break
            except Exception as e:
                log.warning(f"  Error checking resource {input_type} availability: {e}")
                all_inputs_available = False
                break
        
        if all_inputs_available:
            # We found a recipe with all inputs available, create production activity
            activity_params = {
                "buildingId": building_id,
                "recipe": recipe
            }
            log.info(f"  Calling try-create for 'production' activity for {occupant_username}, building {building_id}.")
            return call_try_create_activity_api(occupant_username, "production", activity_params, dry_run)
    
    # If we get here, no recipe had all inputs available
    log.warning(f"  No recipe has all required inputs available for building {building_id}. Cannot create production activity.")
    return False

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

def resolve_waiting_for_galley_unloading(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, building_type_defs: Dict, dry_run: bool) -> bool:
    """Attempts to resolve 'waiting_for_galley_unloading' by creating a fetch_from_galley activity for the building's occupant."""
    log.info(f"Attempting to resolve 'waiting_for_galley_unloading': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    # Get the occupant of the building
    occupant_username = building_record['fields'].get('Occupant')
    if not occupant_username:
        log.error(f"  Building {building_id} has no occupant. Cannot create fetch activity.")
        return False
    
    # Extract resource type and galley name from title or description
    resource_type = None
    galley_id = None
    title = problem['fields'].get('Title', '')
    description = problem['fields'].get('Description', '')
    
    # Try to extract resource type from title first
    title_match = re.search(r"Waiting for Unloading: (\w+)", title)
    if title_match:
        resource_type = title_match.group(1)
    
    # Try to extract galley info from description
    galley_match = re.search(r"galley '([^']+)'", description)
    if galley_match:
        galley_name = galley_match.group(1)
        # Try to find the galley building by name
        try:
            galley_formula = f"{{Name}}='{_escape_airtable_value(galley_name)}'"
            galley_records = tables['buildings'].all(formula=galley_formula, max_records=1)
            if galley_records:
                galley_id = galley_records[0]['fields'].get('BuildingId')
        except Exception as e:
            log.warning(f"  Error finding galley by name '{galley_name}': {e}")
    
    if not resource_type:
        log.error(f"  Could not determine resource type from problem title or description. Cannot create fetch activity.")
        return False
    
    if not galley_id:
        # If we couldn't find the galley by name, try to find it by looking for import contracts
        try:
            import_contract_formula = f"AND({{BuyerBuilding}}='{_escape_airtable_value(building_id)}', {{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='import', {{Status}}='active')"
            import_contracts = tables['contracts'].all(formula=import_contract_formula, max_records=1)
            
            if import_contracts:
                galley_id = import_contracts[0]['fields'].get('SellerBuilding')
                if not galley_id:
                    log.error(f"  Found import contract but no SellerBuilding (galley) specified. Cannot create fetch activity.")
                    return False
        except Exception as e:
            log.warning(f"  Error finding import contract for {resource_type}: {e}")
    
    if not galley_id:
        log.error(f"  Could not determine galley ID. Cannot create fetch activity.")
        return False
    
    # Check if there's already an active fetch_from_galley activity for this occupant and resource
    try:
        # Look for active fetch_from_galley or goto_location activities heading to the galley
        fetch_activity_formula = f"AND({{Citizen}}='{_escape_airtable_value(occupant_username)}', OR({{Type}}='fetch_from_galley', AND({{Type}}='goto_location', {{ToBuilding}}='{_escape_airtable_value(galley_id)}')), OR({{Status}}='created', {{Status}}='in_progress'))"
        existing_activities = tables['activities'].all(formula=fetch_activity_formula)
        
        if existing_activities:
            log.info(f"  Found existing activity for {occupant_username} related to galley {galley_id}. Skipping creation.")
            return True
    except Exception as e:
        log.warning(f"  Error checking for existing activities: {e}")
    
    # Find the import contract for this resource
    contract_id = None
    try:
        contract_formula = f"AND({{BuyerBuilding}}='{_escape_airtable_value(building_id)}', {{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='import', {{Status}}='active')"
        import_contracts = tables['contracts'].all(formula=contract_formula, max_records=1)
        
        if import_contracts:
            contract_id = import_contracts[0]['fields'].get('ContractId', import_contracts[0]['id'])
    except Exception as e:
        log.warning(f"  Error finding import contract: {e}")
    
    # Create fetch_from_galley activity
    # The backend expects a specific structure for fetch_from_galley activities
    activity_params = {
        "resourceType": resource_type,
        "fromBuildingId": galley_id,  # Galley is the source
        "toBuildingId": building_id,  # Destination is the building that needs the resource
        "contractId": contract_id,
        "title": f"Fetch {resource_type} from galley for {building_record['fields'].get('Name', building_id)}",
        "description": f"Fetching {resource_type} from galley to resolve resource shortage at {building_record['fields'].get('Name', building_id)}",
        # Add amount parameter which is required by the backend
        "amount": 20.0  # Default amount if not specified elsewhere
    }
    
    log.info(f"  Calling try-create for 'fetch_from_galley' for {occupant_username}, from galley {galley_id} to {building_id}, resource {resource_type}.")
    return call_try_create_activity_api(occupant_username, "fetch_from_galley", activity_params, dry_run)

def resolve_waiting_on_input_delivery(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, building_type_defs: Dict, dry_run: bool) -> bool:
    """Attempts to resolve 'waiting_on_input_delivery' by creating a fetch_resource activity for the building's occupant."""
    log.info(f"Attempting to resolve 'waiting_on_input_delivery': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    # Get the occupant of the building
    occupant_username = building_record['fields'].get('Occupant')
    if not occupant_username:
        log.error(f"  Building {building_id} has no occupant. Cannot create fetch activity.")
        return False
    
    # Extract resource type from title or description
    resource_type = None
    title = problem['fields'].get('Title', '')
    description = problem['fields'].get('Description', '')
    
    # Try to extract from title first
    title_match = re.search(r"Awaiting Input Delivery: (\w+)", title)
    if title_match:
        resource_type = title_match.group(1)
    else:
        # Try to extract from description
        desc_match = re.search(r"missing inputs \((\w+)\)", description)
        if desc_match:
            resource_type = desc_match.group(1)
    
    if not resource_type:
        log.error(f"  Could not determine resource type from problem title or description. Cannot create fetch activity.")
        return False
    
    # Check if there's already an active fetch_resource activity for this occupant and resource
    try:
        # Look for active fetch_resource activities
        fetch_activity_formula = f"AND({{Citizen}}='{_escape_airtable_value(occupant_username)}', {{Type}}='fetch_resource', OR({{Status}}='created', {{Status}}='in_progress'))"
        existing_activities = tables['activities'].all(formula=fetch_activity_formula)
        
        for activity in existing_activities:
            # Check if this activity is for the resource we need
            resources_json = activity['fields'].get('Resources')
            if resources_json:
                try:
                    resources_list = json.loads(resources_json)
                    for resource_item in resources_list:
                        if resource_item.get('ResourceId') == resource_type:
                            log.info(f"  Found existing fetch_resource activity for {occupant_username} and resource {resource_type}. Skipping creation.")
                            return True
                except (json.JSONDecodeError, TypeError):
                    pass
    except Exception as e:
        log.warning(f"  Error checking for existing fetch activities: {e}")
    
    # Find the source building with the resource (from markup_buy contract)
    source_building_id = None
    contract_id = None
    
    try:
        # Look for active markup_buy contracts for this building and resource
        contract_formula = f"AND({{BuyerBuilding}}='{_escape_airtable_value(building_id)}', {{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='markup_buy', {{Status}}='active')"
        markup_buy_contracts = tables['contracts'].all(formula=contract_formula)
        
        for contract in markup_buy_contracts:
            seller_building_id = contract['fields'].get('SellerBuilding')
            if seller_building_id:
                # Check if the seller has stock
                seller_username = contract['fields'].get('Seller')
                if seller_username:
                    # Get resource stock at seller building
                    resource_formula = f"AND({{Asset}}='{_escape_airtable_value(seller_building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}', {{Owner}}='{_escape_airtable_value(seller_username)}')"
                    resource_records = tables['resources'].all(formula=resource_formula)
                    
                    if resource_records and float(resource_records[0]['fields'].get('Count', 0)) > 0:
                        source_building_id = seller_building_id
                        contract_id = contract['fields'].get('ContractId', contract['id'])
                        break
    except Exception as e:
        log.warning(f"  Error finding source building with stock: {e}")
    
    # If no source found through markup_buy contracts, check for special resources like water
    if not source_building_id and resource_type == "water":
        log.info(f"  No markup_buy source found for water. Looking for wells, cisterns, or other water sources...")
        try:
            # First, look for public_sell contracts for water with zero price (common for wells/cisterns)
            water_contract_formula = f"AND({{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='public_sell', {{Status}}='active', {{PricePerResource}}=0)"
            water_contracts = tables['contracts'].all(formula=water_contract_formula)
            
            for contract in water_contracts:
                seller_building_id = contract['fields'].get('SellerBuilding')
                if seller_building_id:
                    # Check if the seller has stock
                    seller_username = contract['fields'].get('Seller')
                    if seller_username:
                        # Get resource stock at seller building
                        resource_formula = f"AND({{Asset}}='{_escape_airtable_value(seller_building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}', {{Owner}}='{_escape_airtable_value(seller_username)}')"
                        resource_records = tables['resources'].all(formula=resource_formula)
                        
                        if resource_records and float(resource_records[0]['fields'].get('Count', 0)) > 0:
                            source_building_id = seller_building_id
                            contract_id = contract['fields'].get('ContractId', contract['id'])
                            log.info(f"  Found water source with public_sell contract: {seller_building_id}")
                            break
            
            # If still no source, look for buildings that might have water (wells, cisterns)
            if not source_building_id:
                # Look for buildings with SubCategory "Water Management" or similar
                water_building_types = ["well", "cistern", "fountain", "water_cistern"]
                water_subcategories = ["Water Management", "storage"]
                
                # First try to find buildings by type
                for building_type in water_building_types:
                    building_formula = f"{{Type}}='{_escape_airtable_value(building_type)}'"
                    water_buildings = tables['buildings'].all(formula=building_formula)
                    
                    for water_building in water_buildings:
                        water_building_id = water_building['fields'].get('BuildingId')
                        owner_username = water_building['fields'].get('Owner')
                        
                        if water_building_id and owner_username:
                            # Check if this building has water
                            resource_formula = f"AND({{Asset}}='{_escape_airtable_value(water_building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}')"
                            resource_records = tables['resources'].all(formula=resource_formula)
                            
                            if resource_records and float(resource_records[0]['fields'].get('Count', 0)) > 0:
                                source_building_id = water_building_id
                                log.info(f"  Found water source by building type: {water_building_id} (Type: {building_type})")
                                break
                    
                    if source_building_id:
                        break
                
                # If still no source, try by subcategory
                if not source_building_id:
                    for subcategory in water_subcategories:
                        building_formula = f"{{SubCategory}}='{_escape_airtable_value(subcategory)}'"
                        water_buildings = tables['buildings'].all(formula=building_formula)
                        
                        for water_building in water_buildings:
                            water_building_id = water_building['fields'].get('BuildingId')
                            owner_username = water_building['fields'].get('Owner')
                            
                            if water_building_id and owner_username:
                                # Check if this building has water
                                resource_formula = f"AND({{Asset}}='{_escape_airtable_value(water_building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}')"
                                resource_records = tables['resources'].all(formula=resource_formula)
                                
                                if resource_records and float(resource_records[0]['fields'].get('Count', 0)) > 0:
                                    source_building_id = water_building_id
                                    log.info(f"  Found water source by subcategory: {water_building_id} (SubCategory: {subcategory})")
                                    break
                        
                        if source_building_id:
                            break
        except Exception as e:
            log.warning(f"  Error finding water source: {e}")
    
    # If still no source, look for any building with the resource in stock
    if not source_building_id:
        try:
            # Find any building with this resource type in stock
            resource_formula = f"AND({{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}', {{Count}}>0)"
            all_resource_records = tables['resources'].all(formula=resource_formula)
            
            for resource_record in all_resource_records:
                potential_source_id = resource_record['fields'].get('Asset')
                owner_username = resource_record['fields'].get('Owner')
                
                if potential_source_id and owner_username and potential_source_id != building_id:
                    # Check if there's a public_sell contract for this resource from this building
                    contract_formula = f"AND({{SellerBuilding}}='{_escape_airtable_value(potential_source_id)}', {{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='public_sell', {{Status}}='active')"
                    sell_contracts = tables['contracts'].all(formula=contract_formula, max_records=1)
                    
                    if sell_contracts:
                        source_building_id = potential_source_id
                        contract_id = sell_contracts[0]['fields'].get('ContractId', sell_contracts[0]['id'])
                        log.info(f"  Found source building with public_sell contract: {potential_source_id}")
                        break
            
            # If still no source with contract, just use any building with stock as last resort
            if not source_building_id and all_resource_records:
                potential_source_id = all_resource_records[0]['fields'].get('Asset')
                if potential_source_id and potential_source_id != building_id:
                    source_building_id = potential_source_id
                    log.info(f"  Last resort: Found source building with stock but no contract: {potential_source_id}")
        except Exception as e:
            log.warning(f"  Error finding any source building with stock: {e}")
    
    if not source_building_id:
        log.warning(f"  Could not find any source building with stock for {resource_type}. Cannot create fetch activity.")
        return False
    
    # Create fetch_resource activity
    activity_params = {
        "resourceType": resource_type,
        "fromBuildingId": source_building_id,
        "toBuildingId": building_id,
        "contractId": contract_id,
        "title": f"Fetch {resource_type} for {building_record['fields'].get('Name', building_id)}",
        "description": f"Fetching {resource_type} from supplier to resolve input shortage at {building_record['fields'].get('Name', building_id)}",
        "amount": 20.0  # Add default amount parameter which is required by the fetch_resource activity creator
    }
    
    log.info(f"  Calling try-create for 'fetch_resource' for {occupant_username}, from building {source_building_id} to {building_id}, resource {resource_type}.")
    return call_try_create_activity_api(occupant_username, "fetch_resource", activity_params, dry_run)

def resolve_resource_shortage(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> bool:
    """Attempts to resolve 'resource_shortage' by creating a market galley with the needed resources."""
    log.info(f"Attempting to resolve 'resource_shortage': {problem['fields'].get('Title')}")
    
    # Extract resource type from title
    title = problem['fields'].get('Title', '')
    match = re.search(r"Resource Shortage: (\w+) for (.+)", title)
    if not match:
        log.error(f"  Could not parse resource type from problem title: {title}")
        return False
    
    resource_type = match.group(1)
    building_name = match.group(2)
    
    log.info(f"  Resource shortage detected: {resource_type} for {building_name}")
    
    # Check if a market galley was created recently (within last 5 minutes)
    try:
        five_minutes_ago = (datetime.now(VENICE_TIMEZONE) - timedelta(minutes=5)).isoformat()
        # Check for any merchant_galley with retail subcategories (retail_goods, retail_food, etc.)
        recent_galley_formula = f"AND({{Type}}='merchant_galley', OR(SEARCH('retail', {{SubCategory}}), SEARCH('wholesale', {{SubCategory}})), IS_AFTER({{CreatedAt}}, '{five_minutes_ago}'))"
        recent_galleys = tables['buildings'].all(formula=recent_galley_formula, max_records=1)
        
        if recent_galleys:
            galley_name = recent_galleys[0]['fields'].get('Name', 'Unknown')
            log.info(f"  A market galley '{galley_name}' was created recently (within 5 minutes). Assuming it contains needed resources. Skipping creation.")
            return True
    except Exception as e:
        log.warning(f"  Error checking for recent market galleys: {e}")
    
    # Collect all resource shortage problems to handle them in batch
    try:
        # Get all active resource_shortage problems
        formula = "AND({Type}='resource_shortage', {Status}='active')"
        all_shortage_problems = tables['problems'].all(formula=formula)
        
        # Extract unique resource types from all problems
        resources_needed = set()
        for shortage_problem in all_shortage_problems:
            shortage_title = shortage_problem['fields'].get('Title', '')
            shortage_match = re.search(r"Resource Shortage: (\w+) for", shortage_title)
            if shortage_match:
                resources_needed.add(shortage_match.group(1))
        
        if not resources_needed:
            log.warning("  No valid resource types found in resource shortage problems")
            return False
        
        log.info(f"  Total unique resources needed: {list(resources_needed)}")
        
        # Call createmarketgalley.py with the list of resources
        if not dry_run:
            try:
                import subprocess
                
                # Build the command
                cmd = [
                    sys.executable,
                    os.path.join(PROJECT_ROOT, 'backend', 'engine', 'createmarketgalley.py'),
                    '--resources',
                    ','.join(resources_needed)
                ]
                
                log.info(f"  Executing: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    log.info(f"  Successfully created market galley with resources: {list(resources_needed)}")
                    log.info(f"  Output: {result.stdout}")
                    return True
                else:
                    log.error(f"  Failed to create market galley. Return code: {result.returncode}")
                    log.error(f"  Error output: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                log.error("  Market galley creation timed out after 60 seconds")
                return False
            except Exception as e:
                log.error(f"  Error calling createmarketgalley.py: {e}")
                return False
        else:
            log.info(f"  [DRY RUN] Would create market galley with resources: {list(resources_needed)}")
            return True
            
    except Exception as e:
        log.error(f"  Error in resolve_resource_shortage: {e}")
        return False

def resolve_do_nothing(problem: Dict, tables: Dict[str, Table], dry_run: bool) -> str: # Changed return type
    """Resolver for problems where the defined action is to do nothing."""
    problem_type = problem['fields'].get('Type')
    log.info(f"Problem type '{problem_type}' for problem '{problem['fields'].get('Title')}' is configured for no automated action. Skipping.")
    return "NO_ACTION_INTENDED" # Return specific string

def resolve_waiting_for_resource_delivery(problem: Dict, tables: Dict[str, Table], resource_defs: Dict, building_type_defs: Dict, dry_run: bool) -> bool:
    """Attempts to resolve 'waiting_for_resource_delivery' by checking for existing activities or creating a fetch_resource activity."""
    log.info(f"Attempting to resolve 'waiting_for_resource_delivery': {problem['fields'].get('Title')}")
    building_id = problem['fields'].get('Asset')
    if not building_id:
        log.error(f"  Missing BuildingId for problem {problem['id']}. Cannot resolve.")
        return False

    building_record = get_building_record(tables, building_id)
    if not building_record:
        log.error(f"  Building {building_id} not found. Cannot resolve problem {problem['id']}.")
        return False

    # Get the occupant of the building
    occupant_username = building_record['fields'].get('Occupant')
    if not occupant_username:
        log.error(f"  Building {building_id} has no occupant. Cannot create fetch activity.")
        return False
    
    # Extract resource type from title or description
    resource_type = None
    title = problem['fields'].get('Title', '')
    description = problem['fields'].get('Description', '')
    
    # Try to extract from title first
    title_match = re.search(r"Waiting for Delivery: (\w+)", title)
    if title_match:
        resource_type = title_match.group(1)
    else:
        # Try alternative title format
        title_match_alt = re.search(r"Waiting for Resource Delivery: (\w+)", title)
        if title_match_alt:
            resource_type = title_match_alt.group(1)
        else:
            # Try to extract from description
            desc_match = re.search(r"waiting for delivery of (\w+)", description)
            if desc_match:
                resource_type = desc_match.group(1)
    
    if not resource_type:
        log.error(f"  Could not determine resource type from problem title or description. Cannot create fetch activity.")
        return False
    
    # Check if there's already an active fetch_resource or similar activity for this occupant and resource
    try:
        # Look for active fetch_resource, fetch_from_storage, fetch_from_galley activities
        fetch_activity_formula = f"AND({{Citizen}}='{_escape_airtable_value(occupant_username)}', OR({{Type}}='fetch_resource', {{Type}}='fetch_from_storage', {{Type}}='fetch_from_galley', {{Type}}='goto_location'), OR({{Status}}='created', {{Status}}='in_progress'))"
        existing_activities = tables['activities'].all(formula=fetch_activity_formula)
        
        for activity in existing_activities:
            activity_type = activity['fields'].get('Type')
            
            # For fetch_resource, fetch_from_storage, fetch_from_galley, check Resources field
            if activity_type in ['fetch_resource', 'fetch_from_storage', 'fetch_from_galley']:
                resources_json = activity['fields'].get('Resources')
                if resources_json:
                    try:
                        resources_list = json.loads(resources_json)
                        for resource_item in resources_list:
                            if resource_item.get('ResourceId') == resource_type:
                                log.info(f"  Found existing {activity_type} activity for {occupant_username} and resource {resource_type}. Skipping creation.")
                                return True
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            # For goto_location, check Notes field for chained activities
            elif activity_type == 'goto_location':
                notes_json = activity['fields'].get('Notes')
                if notes_json:
                    try:
                        notes_data = json.loads(notes_json)
                        # Check if this goto is part of a fetch chain
                        if notes_data.get('action_on_arrival') in ['pickup_from_galley', 'fetch_resource']:
                            if notes_data.get('resource_id') == resource_type:
                                log.info(f"  Found existing goto_location activity for {occupant_username} leading to resource {resource_type} pickup. Skipping creation.")
                                return True
                    except (json.JSONDecodeError, TypeError):
                        pass
    except Exception as e:
        log.warning(f"  Error checking for existing fetch activities: {e}")
    
    # Find a source for the resource
    source_building_id = None
    contract_id = None
    
    # First, check for markup_buy contracts
    try:
        contract_formula = f"AND({{BuyerBuilding}}='{_escape_airtable_value(building_id)}', {{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='markup_buy', {{Status}}='active')"
        markup_buy_contracts = tables['contracts'].all(formula=contract_formula)
        
        for contract in markup_buy_contracts:
            seller_building_id = contract['fields'].get('SellerBuilding')
            if seller_building_id:
                # Check if the seller has stock
                seller_username = contract['fields'].get('Seller')
                if seller_username:
                    # Get resource stock at seller building
                    resource_formula = f"AND({{Asset}}='{_escape_airtable_value(seller_building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}', {{Owner}}='{_escape_airtable_value(seller_username)}')"
                    resource_records = tables['resources'].all(formula=resource_formula)
                    
                    if resource_records and float(resource_records[0]['fields'].get('Count', 0)) > 0:
                        source_building_id = seller_building_id
                        contract_id = contract['fields'].get('ContractId', contract['id'])
                        log.info(f"  Found source building with markup_buy contract: {source_building_id}")
                        break
    except Exception as e:
        log.warning(f"  Error finding markup_buy contracts: {e}")
    
    # If no markup_buy source, check for import contracts and galleys
    if not source_building_id:
        try:
            import_formula = f"AND({{BuyerBuilding}}='{_escape_airtable_value(building_id)}', {{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='import', {{Status}}='active')"
            import_contracts = tables['contracts'].all(formula=import_formula)
            
            if import_contracts:
                # Look for galleys with this resource
                for galley_type in ['galley', 'market_galley']:
                    galley_formula = f"{{Type}}='{galley_type}'"
                    galleys = tables['buildings'].all(formula=galley_formula)
                    
                    for galley in galleys:
                        galley_id = galley['fields'].get('BuildingId')
                        if galley_id:
                            # Check if galley has the resource
                            resource_formula = f"AND({{Asset}}='{_escape_airtable_value(galley_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}')"
                            galley_resources = tables['resources'].all(formula=resource_formula)
                            
                            if galley_resources and float(galley_resources[0]['fields'].get('Count', 0)) > 0:
                                source_building_id = galley_id
                                contract_id = import_contracts[0]['fields'].get('ContractId', import_contracts[0]['id'])
                                log.info(f"  Found galley with resource for import contract: {source_building_id}")
                                break
                    
                    if source_building_id:
                        break
        except Exception as e:
            log.warning(f"  Error finding import contracts and galleys: {e}")
    
    # If still no source, check for public_sell contracts
    if not source_building_id:
        try:
            public_sell_formula = f"AND({{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Type}}='public_sell', {{Status}}='active')"
            public_sell_contracts = tables['contracts'].all(formula=public_sell_formula)
            
            for contract in public_sell_contracts:
                seller_building_id = contract['fields'].get('SellerBuilding')
                if seller_building_id:
                    # Check if the seller has stock
                    seller_username = contract['fields'].get('Seller')
                    if seller_username:
                        # Get resource stock at seller building
                        resource_formula = f"AND({{Asset}}='{_escape_airtable_value(seller_building_id)}', {{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}', {{Owner}}='{_escape_airtable_value(seller_username)}')"
                        resource_records = tables['resources'].all(formula=resource_formula)
                        
                        if resource_records and float(resource_records[0]['fields'].get('Count', 0)) > 0:
                            source_building_id = seller_building_id
                            contract_id = contract['fields'].get('ContractId', contract['id'])
                            log.info(f"  Found source building with public_sell contract: {source_building_id}")
                            break
        except Exception as e:
            log.warning(f"  Error finding public_sell contracts: {e}")
    
    # If still no source, look for any building with the resource in stock
    if not source_building_id:
        try:
            # Find any building with this resource type in stock
            resource_formula = f"AND({{AssetType}}='building', {{Type}}='{_escape_airtable_value(resource_type)}', {{Count}}>0)"
            all_resource_records = tables['resources'].all(formula=resource_formula)
            
            for resource_record in all_resource_records:
                potential_source_id = resource_record['fields'].get('Asset')
                if potential_source_id and potential_source_id != building_id:
                    source_building_id = potential_source_id
                    log.info(f"  Last resort: Found source building with stock but no contract: {potential_source_id}")
                    break
        except Exception as e:
            log.warning(f"  Error finding any source building with stock: {e}")
    
    if not source_building_id:
        log.warning(f"  Could not find any source building with stock for {resource_type}. Cannot create fetch activity.")
        return False
    
    # Determine which activity type to create based on the source
    activity_type = "fetch_resource"  # Default
    
    # Check if source is a galley
    source_building_record = get_building_record(tables, source_building_id)
    if source_building_record and source_building_record['fields'].get('Type') in ['galley', 'market_galley']:
        activity_type = "fetch_from_galley"
        log.info(f"  Source is a galley, using fetch_from_galley activity type")
    
    # Create appropriate fetch activity
    activity_params = {
        "resourceType": resource_type,
        "fromBuildingId": source_building_id,
        "toBuildingId": building_id,
        "contractId": contract_id,
        "title": f"Fetch {resource_type} for {building_record['fields'].get('Name', building_id)}",
        "description": f"Fetching {resource_type} to resolve delivery wait at {building_record['fields'].get('Name', building_id)}",
        "amount": 20.0  # Default amount
    }
    
    log.info(f"  Calling try-create for '{activity_type}' for {occupant_username}, from building {source_building_id} to {building_id}, resource {resource_type}.")
    return call_try_create_activity_api(occupant_username, activity_type, activity_params, dry_run)

# --- Main Processing Logic ---
def auto_resolve_problems_main(dry_run: bool = False, problem_type_filter: Optional[str] = None, asset_filter: Optional[str] = None):
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
    
    # Apply type filter if specified
    if problem_type_filter:
        problems_to_process = [p for p in problems_to_process if p['fields'].get('Type') == problem_type_filter]
        log.info(f"Filtered to {len(problems_to_process)} problems of type '{problem_type_filter}'.")
    
    # Apply asset filter if specified
    if asset_filter:
        problems_to_process = [p for p in problems_to_process if p['fields'].get('Asset') == asset_filter]
        log.info(f"Filtered to {len(problems_to_process)} problems for asset '{asset_filter}'.")

    resolved_count = 0
    attempted_count = 0

    resolver_map = {
        "resource_not_for_sale": resolve_resource_not_for_sale, # 1. Oui
        "no_operator_for_stock": resolve_no_operator_for_stock, # 2. Augmente wages
        "waiting_for_production": resolve_waiting_for_production, # 3. Si pas d'Occupant: Augmente wages
        "no_markup_buy_contract_for_input": resolve_no_markup_buy_contract_for_input, # 4. Oui
        "supplier_shortage": resolve_supplier_or_resource_shortage, # 5. Oui (augmente prix markup_buy)
        "waiting_on_input_delivery": resolve_waiting_on_input_delivery, # 6. Create fetch_resource activity
        "no_import_contract": resolve_no_import_contract, # 7. Oui, manage_import_contract
        "waiting_for_galley_unloading": resolve_waiting_for_galley_unloading, # 8. Create fetch_from_galley activity
        "waiting_for_galley_arrival": resolve_do_nothing, # 9. Oui (ne rien faire)
        "no_markup_buy_contract": resolve_no_markup_buy_contract_final_product, # 10. Oui (similaire à 4)
        "resource_shortage": resolve_resource_shortage, # 11. Create market galley with needed resources
        "waiting_for_resource_delivery": resolve_waiting_for_resource_delivery, # 12. Créer fetch_resource/fetch_from_galley
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
                "no_occupant",
                "vacant_building",
                "hungry_citizen",
                "zero_rent_building",
                "zero_wages_business",
                "waiting_for_galley_arrival", # do_nothing
                "homeless_citizen", # do_nothing
                "workless_citizen" # do_nothing
            ]:
                resolution_status = resolver_func(problem, tables, dry_run)
            elif problem_type == "resource_shortage":
                resolution_status = resolver_func(problem, tables, dry_run)
            elif problem_type in ["waiting_for_production"]:
                resolution_status = resolver_func(problem, tables, resource_defs, building_type_defs, dry_run)
            elif problem_type in ["waiting_on_input_delivery", "waiting_for_galley_unloading"]:
                resolution_status = resolver_func(problem, tables, resource_defs, building_type_defs, dry_run)
            elif problem_type == "waiting_for_resource_delivery":
                resolution_status = resolver_func(problem, tables, resource_defs, building_type_defs, dry_run)
            elif problem_type in [
                "no_operator_for_stock", 
                "no_occupant",
                "vacant_building",
                "hungry_citizen",
                "zero_rent_building",
                "zero_wages_business",
                "waiting_for_galley_arrival", # do_nothing
                "homeless_citizen", # do_nothing
                "workless_citizen" # do_nothing
            ]:
                resolution_status = resolver_func(problem, tables, dry_run)
            elif problem_type == "resource_shortage":
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
    parser.add_argument(
        "--asset",
        type=str,
        default=None,
        help="Optional: Filter problems by a specific asset ID (e.g., BuildingId) to resolve only those."
    )
    args = parser.parse_args()

    auto_resolve_problems_main(dry_run=args.dry_run, problem_type_filter=args.type, asset_filter=args.asset)

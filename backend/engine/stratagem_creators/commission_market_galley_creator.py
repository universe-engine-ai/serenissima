"""
Create a market galley commission stratagem that allows citizens to pay for external trade.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pyairtable import Api

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors
)
from backend.schema.enums import BuildingType
from backend.utils.database import DATABASE_ID, get_base_record

log = logging.getLogger(__name__)


def validate_can_commission_galley(
    citizen_id: str, 
    resource_types: Optional[List[str]] = None,
    investment_amount: float = 5000.0,
    api: Api = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validate if a citizen can commission a market galley.
    
    Returns:
        success (bool): Whether stratagem can be created
        error_message (str): Explanation if validation fails
        data (dict): Context data if successful
    """
    # Get citizen record
    citizen = get_base_record("CITIZENS", citizen_id, api=api)
    if not citizen:
        return False, "Citizen not found", None
    
    # Check if citizen has enough ducats to invest
    citizen_ducats = citizen.get("Ducats", 0)
    if citizen_ducats < investment_amount:
        return False, f"Insufficient ducats. Need {investment_amount:.0f}, have {citizen_ducats:.0f}", None
    
    # Validate resource types if specified
    valid_resource_types = [
        "fish", "grain", "wine", "salt", "spices", "silk", 
        "wool", "leather", "stone", "wood", "iron", "glass"
    ]
    
    if resource_types:
        invalid_types = [rt for rt in resource_types if rt not in valid_resource_types]
        if invalid_types:
            return False, f"Invalid resource types: {', '.join(invalid_types)}", None
    
    # Get public docks for galley arrival
    base = api.base(DATABASE_ID)
    public_docks = base.table("BUILDINGS").all(
        view="Water Coordinates",
        formula=f"AND({{Building Type}}='{BuildingType.public_dock}')"
    )
    
    if not public_docks:
        return False, "No public docks available for galley arrival", None
    
    # Calculate expected return on investment (15% markup on resources)
    expected_value = investment_amount * 1.15
    
    context = {
        "citizen_id": citizen_id,
        "citizen_name": citizen.get("Name", "Unknown"),
        "investment_amount": investment_amount,
        "resource_types": resource_types or ["mixed"],  # Default to mixed cargo
        "expected_value": expected_value,
        "public_docks": len(public_docks)
    }
    
    return True, "", context


def create_commission_market_galley_stratagem(
    citizen_id: str,
    investment_amount: float = 5000.0,
    resource_types: Optional[List[str]] = None,
    api: Api = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Create a stratagem to commission a market galley.
    
    The citizen invests ducats to hire a foreign merchant to bring goods to Venice.
    Default investment is 5000 ducats, with resources worth ~5750 ducats arriving.
    
    Args:
        citizen_id: ID of the citizen commissioning the galley
        investment_amount: Ducats to invest (min 1000, max 50000)
        resource_types: Optional list of specific resource types to request
        api: Airtable API instance
        
    Returns:
        success (bool): Whether stratagem was created
        error_message (str): Explanation if creation fails  
        stratagem_id (str): ID of created stratagem if successful
    """
    # Validate investment bounds
    investment_amount = max(1000.0, min(50000.0, investment_amount))
    
    # Validate the action
    can_create, error_msg, context = validate_can_commission_galley(
        citizen_id, resource_types, investment_amount, api
    )
    
    if not can_create:
        return False, error_msg, None
    
    # Create the stratagem record
    base = api.base(DATABASE_ID)
    
    # Calculate arrival time (6-12 hours from now)
    arrival_hours = random.randint(6, 12)
    
    stratagem_data = {
        "Type": "commission_market_galley",
        "Citizen": [citizen_id],
        "Status": "active",
        "Parameters": {
            "investment_amount": investment_amount,
            "resource_types": resource_types or ["mixed"],
            "expected_value": context["expected_value"],
            "arrival_hours": arrival_hours,
            "commission_paid": False  # Will be set to True when ducats are deducted
        },
        "Description": (
            f"{context['citizen_name']} commissions a foreign merchant galley "
            f"for {investment_amount:.0f} ducats to bring "
            f"{', '.join(resource_types) if resource_types else 'mixed goods'} to Venice. "
            f"Expected arrival in {arrival_hours} hours."
        )
    }
    
    try:
        created_stratagem = base.table("STRATAGEMS").create(stratagem_data)
        return True, "", created_stratagem["id"]
    except Exception as e:
        return False, f"Failed to create stratagem: {str(e)}", None


def try_create(
    tables: Dict[str, Any],
    citizen_username: str,
    stratagem_type: str,
    stratagem_params: Dict[str, Any],
    now_venice_dt: datetime,
    now_utc_dt: datetime,
    api_base_url: str = None,
    transport_api_url: str = None
) -> Optional[List[Dict[str, Any]]]:
    """
    API wrapper for creating a commission market galley stratagem.
    
    Expected stratagem_params:
    - investmentAmount (float): Ducats to invest (default 5000, min 1000, max 50000)
    - resourceTypes (list, optional): List of resource types to request
    - name (str, optional): Custom name for the stratagem
    - description (str, optional): Custom description
    - notes (str, optional): Additional notes
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")
    
    if stratagem_type != "commission_market_galley":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'commission_market_galley' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None
    
    # Get citizen record by username
    citizens_table = tables.get('citizens')
    if not citizens_table:
        log.error(f"{LogColors.FAIL}Citizens table not available{LogColors.ENDC}")
        return None
    
    # Find citizen by username
    try:
        formula = f"{{Username}} = '{_escape_airtable_value(citizen_username)}'"
        citizen_records = citizens_table.all(formula=formula, max_records=1)
        if not citizen_records:
            log.error(f"{LogColors.FAIL}Citizen with username '{citizen_username}' not found{LogColors.ENDC}")
            return None
        citizen_record = citizen_records[0]
        citizen_id = citizen_record['id']
        citizen_name = citizen_record['fields'].get('Name', citizen_username)
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching citizen: {e}{LogColors.ENDC}")
        return None
    
    # Extract parameters
    investment_amount = float(stratagem_params.get('investmentAmount', 5000.0))
    resource_types = stratagem_params.get('resourceTypes', None)
    custom_name = stratagem_params.get('name')
    custom_description = stratagem_params.get('description')
    custom_notes = stratagem_params.get('notes')
    
    # Validate bounds
    investment_amount = max(1000.0, min(50000.0, investment_amount))
    
    # Create API instance for validation
    api_key = tables['citizens'].api_key
    api = Api(api_key)
    
    # Validate the action
    can_create, error_msg, context = validate_can_commission_galley(
        citizen_id, resource_types, investment_amount, api
    )
    
    if not can_create:
        log.error(f"{LogColors.FAIL}Validation failed: {error_msg}{LogColors.ENDC}")
        return None
    
    # Calculate arrival time (6-12 hours from now)
    arrival_hours = random.randint(6, 12)
    
    # Build stratagem payload (what the API will create)
    stratagem_id = str(uuid.uuid4())
    
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": "commission_market_galley",
        "Citizen": [citizen_id],
        "ExecutedBy": citizen_username,
        "Status": "active",
        "Parameters": json.dumps({
            "investment_amount": investment_amount,
            "resource_types": resource_types or ["mixed"],
            "expected_value": context["expected_value"],
            "arrival_hours": arrival_hours,
            "commission_paid": False
        }),
        "Name": custom_name or f"Commission Market Galley ({investment_amount:.0f} ducats)",
        "Description": custom_description or (
            f"{citizen_name} commissions a foreign merchant galley "
            f"for {investment_amount:.0f} ducats to bring "
            f"{', '.join(resource_types) if resource_types else 'mixed goods'} to Venice. "
            f"Expected arrival in {arrival_hours} hours."
        ),
        "Notes": custom_notes or "",
        "ExecutedAt": None,  # Will be set when first processed
        "ExpiresAt": (now_utc_dt + timedelta(hours=arrival_hours + 6)).isoformat()  # Extra time after arrival
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'commission_market_galley' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]
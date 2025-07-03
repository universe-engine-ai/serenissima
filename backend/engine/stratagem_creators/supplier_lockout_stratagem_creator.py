"""
Supplier Lockout Stratagem Creator

Creates exclusive supply agreements to secure resources and potentially hinder competitors.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any], # Airtable tables
    citizen_username: str, # Username of the citizen executing the stratagem
    stratagem_type: str, # Should be "supplier_lockout"
    stratagem_params: Dict[str, Any], # Parameters specific to this stratagem
    # Common time parameters
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]: # Returns a list of stratagem payloads to be created
    """
    Creates a supplier_lockout stratagem.
    
    Expected stratagem_params:
    - targetResourceType (str, required): The resource type to secure
    - targetSupplierCitizen (str, required): The supplier to lock out
    - targetSupplierBuilding (str, optional): Specific building
    - premiumPercentage (int, optional): Premium above market price (default 15%)
    - contractDurationDays (int, optional): Duration of exclusive contract (default 30)
    - name (str, optional): Custom name
    - description (str, optional): Custom description
    - notes (str, optional): Additional notes
    - durationHours (int, optional): Duration of the stratagem itself
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")
    
    if stratagem_type != "supplier_lockout":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'supplier_lockout' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None
    
    # Extract parameters
    target_resource_type = stratagem_params.get('targetResourceType')
    target_supplier_citizen = stratagem_params.get('targetSupplierCitizen')
    target_supplier_building = stratagem_params.get('targetSupplierBuilding', '')
    premium_percentage = stratagem_params.get('premiumPercentage', 15)
    contract_duration_days = stratagem_params.get('contractDurationDays', 30)
    duration_hours = stratagem_params.get('durationHours', contract_duration_days * 24)
    
    # Custom fields
    custom_name = stratagem_params.get('name')
    custom_description = stratagem_params.get('description')
    custom_notes = stratagem_params.get('notes', '')
    
    # Validation
    if not target_resource_type:
        log.error(f"{LogColors.FAIL}targetResourceType is required for supplier_lockout stratagem{LogColors.ENDC}")
        return None
    
    if not target_supplier_citizen:
        log.error(f"{LogColors.FAIL}targetSupplierCitizen is required for supplier_lockout stratagem{LogColors.ENDC}")
        return None
    
    if premium_percentage < 0 or premium_percentage > 100:
        log.error(f"{LogColors.FAIL}premiumPercentage must be between 0 and 100{LogColors.ENDC}")
        return None
    
    if contract_duration_days < 1 or contract_duration_days > 365:
        log.error(f"{LogColors.FAIL}contractDurationDays must be between 1 and 365{LogColors.ENDC}")
        return None
    
    # Verify the supplier exists
    try:
        supplier_formula = f"{{Username}}='{_escape_airtable_value(target_supplier_citizen)}'"
        supplier_records = tables['citizens'].all(formula=supplier_formula, max_records=1)
        
        if not supplier_records:
            log.error(f"{LogColors.FAIL}Supplier citizen '{target_supplier_citizen}' not found{LogColors.ENDC}")
            return None
        
        # Verify the supplier has production capability for the resource
        if target_supplier_building:
            building_formula = f"AND({{BuildingId}}='{_escape_airtable_value(target_supplier_building)}', {{RunBy}}='{_escape_airtable_value(target_supplier_citizen)}')"
            buildings = tables['buildings'].all(formula=building_formula, max_records=1)
            
            if not buildings:
                log.error(f"{LogColors.FAIL}Building '{target_supplier_building}' not found or not operated by '{target_supplier_citizen}'{LogColors.ENDC}")
                return None
    
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error verifying supplier: {e}{LogColors.ENDC}")
        return None
    
    # Generate stratagem ID
    stratagem_id = f"supplier_lockout_{citizen_username}_{target_resource_type}_{int(now_utc_dt.timestamp())}"
    
    # Calculate expiration
    expires_at = now_utc_dt + timedelta(hours=duration_hours)
    
    # Build stratagem payload
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": "supplier_lockout",
        "Variant": f"{premium_percentage}%_premium_{contract_duration_days}d",
        "ExecutedBy": citizen_username,
        "TargetCitizen": target_supplier_citizen,
        "TargetBuilding": target_supplier_building,
        "TargetResourceType": target_resource_type,
        "Status": "active",
        "Category": "commerce",
        "Name": custom_name or f"Supplier Lockout: {target_resource_type}",
        "Description": custom_description or f"Securing exclusive supply of {target_resource_type} from {target_supplier_citizen}",
        "Notes": json.dumps({
            "initial_notes": custom_notes,
            "premium_percentage": premium_percentage,
            "contract_duration_days": contract_duration_days,
            "created_at": now_utc_dt.isoformat()
        }),
        "InfluenceCost": 0,  # Influence costs removed
        "CreatedAt": now_utc_dt.isoformat(),
        "ExpiresAt": expires_at.isoformat()
    }
    
    log.info(f"{LogColors.OKGREEN}Successfully prepared supplier_lockout stratagem: {stratagem_id}{LogColors.ENDC}")
    
    # Return list of stratagems to create (just one in this case)
    return [stratagem_payload]
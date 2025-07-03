#!/usr/bin/env python3
"""
Monopoly Pricing Stratagem Creator

Creates monopoly pricing stratagems to leverage market dominance for higher profits.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_username: str,
    stratagem_type: str,
    stratagem_params: Dict[str, Any],
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a monopoly_pricing stratagem.
    
    Expected stratagem_params:
    - targetResourceType (str, required): The resource to monopolize
    - variant (str, required): "Mild", "Standard", or "Aggressive"
    - durationHours (int, optional): Duration of the stratagem (default 168 - 7 days)
    - name (str, optional): Custom name
    - description (str, optional): Custom description
    - notes (str, optional): Additional notes
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")
    
    if stratagem_type != "monopoly_pricing":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'monopoly_pricing' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None
    
    # Extract parameters
    target_resource_type = stratagem_params.get('targetResourceType')
    variant = stratagem_params.get('variant')
    duration_hours = stratagem_params.get('durationHours', 168)  # 7 days default
    
    # Custom fields
    custom_name = stratagem_params.get('name')
    custom_description = stratagem_params.get('description')
    custom_notes = stratagem_params.get('notes', '')
    
    # Validation
    if not target_resource_type:
        log.error(f"{LogColors.FAIL}targetResourceType is required for monopoly_pricing stratagem{LogColors.ENDC}")
        return None
    
    if variant not in ['Mild', 'Standard', 'Aggressive']:
        log.error(f"{LogColors.FAIL}variant must be 'Mild', 'Standard', or 'Aggressive'{LogColors.ENDC}")
        return None
    
    # Price multipliers based on variant
    price_multipliers = {
        'Mild': 1.5,      # 150% of market average
        'Standard': 2.0,   # 200% of market average
        'Aggressive': 3.0  # 300% of market average
    }
    
    # Check if citizen has significant market share
    try:
        # Count active public_sell contracts for this resource by the citizen
        contract_formula = (f"AND({{Type}}='public_sell', {{Seller}}='{_escape_airtable_value(citizen_username)}', "
                          f"{{ResourceType}}='{_escape_airtable_value(target_resource_type)}', {{Status}}='active')")
        citizen_contracts = tables['contracts'].all(formula=contract_formula)
        
        if not citizen_contracts:
            log.error(f"{LogColors.FAIL}Citizen {citizen_username} has no active public_sell contracts for {target_resource_type}{LogColors.ENDC}")
            return None
        
        # Count total public_sell contracts for this resource
        total_formula = f"AND({{Type}}='public_sell', {{ResourceType}}='{_escape_airtable_value(target_resource_type)}', {{Status}}='active')"
        total_contracts = tables['contracts'].all(formula=total_formula)
        
        market_share = len(citizen_contracts) / len(total_contracts) if total_contracts else 0
        
        if market_share < 0.2:  # Require at least 20% market share
            log.warning(f"{LogColors.WARNING}Citizen {citizen_username} has only {market_share:.1%} market share for {target_resource_type} (minimum 20% recommended){LogColors.ENDC}")
            custom_notes += f"\nWarning: Low market share ({market_share:.1%}) may reduce effectiveness"
        
        # Count citizen's available stock
        resource_formula = (f"AND({{Type}}='{_escape_airtable_value(target_resource_type)}', "
                          f"{{Owner}}='{_escape_airtable_value(citizen_username)}', {{AssetType}}='building')")
        citizen_resources = tables['resources'].all(formula=resource_formula)
        
        total_stock = sum(float(r['fields'].get('Quantity', 0)) for r in citizen_resources)
        
        if total_stock < 10:
            log.warning(f"{LogColors.WARNING}Citizen {citizen_username} has low stock ({total_stock} units) of {target_resource_type}{LogColors.ENDC}")
    
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error verifying market position: {e}{LogColors.ENDC}")
        return None
    
    # Generate stratagem ID
    stratagem_id = f"monopoly_pricing_{citizen_username}_{target_resource_type}_{int(now_utc_dt.timestamp())}"
    
    # Calculate expiration
    expires_at = now_utc_dt + timedelta(hours=duration_hours)
    
    # Build stratagem payload
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": "monopoly_pricing",
        "Variant": variant,
        "ExecutedBy": citizen_username,
        "TargetResourceType": target_resource_type,
        "Status": "active",
        "Category": "commerce",
        "Name": custom_name or f"Monopoly Pricing for {target_resource_type}",
        "Description": custom_description or f"{citizen_username} manipulates {target_resource_type} prices using market dominance ({variant} strategy)",
        "Notes": json.dumps({
            "initial_notes": custom_notes.strip(),
            "resource_type": target_resource_type,
            "price_multiplier": price_multipliers[variant],
            "market_share": round(market_share, 3),
            "initial_stock": total_stock,
            "created_at": now_utc_dt.isoformat()
        }),
        "InfluenceCost": 0,  # Influence costs removed
        "CreatedAt": now_utc_dt.isoformat(),
        "ExpiresAt": expires_at.isoformat()
    }
    
    log.info(f"{LogColors.OKGREEN}Successfully prepared monopoly_pricing stratagem: {stratagem_id}{LogColors.ENDC}")
    
    # Return list of stratagems to create
    return [stratagem_payload]
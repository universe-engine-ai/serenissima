#!/usr/bin/env python3
"""
Financial Patronage Stratagem Creator

Creates financial patronage stratagems to provide ongoing financial support to other citizens.
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
    Creates a financial_patronage stratagem.
    
    Expected stratagem_params:
    - targetCitizenUsername (str, required): The citizen to support
    - patronageLevel (str, optional): "Modest", "Standard", or "Generous" (default "Standard")
    - durationDays (int, optional): Duration of patronage (default 90, range 30-180)
    - name (str, optional): Custom name
    - description (str, optional): Custom description
    - notes (str, optional): Additional notes
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")
    
    if stratagem_type != "financial_patronage":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'financial_patronage' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None
    
    # Extract parameters
    target_citizen_username = stratagem_params.get('targetCitizenUsername')
    patronage_level = stratagem_params.get('patronageLevel', 'Standard')
    duration_days = stratagem_params.get('durationDays', 90)
    
    # Custom fields
    custom_name = stratagem_params.get('name')
    custom_description = stratagem_params.get('description')
    custom_notes = stratagem_params.get('notes', '')
    
    # Validation
    if not target_citizen_username:
        log.error(f"{LogColors.FAIL}targetCitizenUsername is required for financial_patronage stratagem{LogColors.ENDC}")
        return None
    
    if target_citizen_username == citizen_username:
        log.error(f"{LogColors.FAIL}Cannot create financial patronage for oneself{LogColors.ENDC}")
        return None
    
    if patronage_level not in ['Modest', 'Standard', 'Generous']:
        log.error(f"{LogColors.FAIL}patronageLevel must be 'Modest', 'Standard', or 'Generous'{LogColors.ENDC}")
        return None
    
    if duration_days < 30 or duration_days > 180:
        log.error(f"{LogColors.FAIL}durationDays must be between 30 and 180{LogColors.ENDC}")
        return None
    
    # Verify target citizen exists
    try:
        target_formula = f"{{Username}}='{_escape_airtable_value(target_citizen_username)}'"
        target_records = tables['citizens'].all(formula=target_formula, max_records=1)
        
        if not target_records:
            log.error(f"{LogColors.FAIL}Target citizen '{target_citizen_username}' not found{LogColors.ENDC}")
            return None
        
        # Verify patron has sufficient wealth
        patron_formula = f"{{Username}}='{_escape_airtable_value(citizen_username)}'"
        patron_records = tables['citizens'].all(formula=patron_formula, max_records=1)
        
        if not patron_records:
            log.error(f"{LogColors.FAIL}Patron citizen '{citizen_username}' not found{LogColors.ENDC}")
            return None
        
        patron_ducats = float(patron_records[0]['fields'].get('Ducats', 0))
        
        # Calculate daily amounts based on patronage level
        daily_amounts = {
            'Modest': 5,
            'Standard': 10,
            'Generous': 20
        }
        daily_amount = daily_amounts[patronage_level]
        total_cost = daily_amount * duration_days
        
        # Warn if patron may not have enough funds (but still allow creation)
        if patron_ducats < total_cost:
            log.warning(f"{LogColors.WARNING}Patron {citizen_username} has {patron_ducats} ducats but patronage will cost {total_cost} total{LogColors.ENDC}")
    
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error verifying citizens: {e}{LogColors.ENDC}")
        return None
    
    # Generate stratagem ID
    stratagem_id = f"financial_patronage_{citizen_username}_{target_citizen_username}_{int(now_utc_dt.timestamp())}"
    
    # Calculate expiration
    expires_at = now_utc_dt + timedelta(days=duration_days)
    
    # Build stratagem payload
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": "financial_patronage",
        "Variant": patronage_level,
        "ExecutedBy": citizen_username,
        "TargetCitizen": target_citizen_username,
        "Status": "active",
        "Category": "personal",
        "Name": custom_name or f"Patronage of {target_citizen_username}",
        "Description": custom_description or f"{citizen_username} provides {patronage_level.lower()} financial support to {target_citizen_username}",
        "Notes": json.dumps({
            "initial_notes": custom_notes,
            "patronage_level": patronage_level,
            "daily_amount": daily_amount,
            "duration_days": duration_days,
            "total_expected_cost": total_cost,
            "created_at": now_utc_dt.isoformat()
        }),
        "InfluenceCost": 0,  # Influence costs removed
        "CreatedAt": now_utc_dt.isoformat(),
        "ExpiresAt": expires_at.isoformat()
    }
    
    log.info(f"{LogColors.OKGREEN}Successfully prepared financial_patronage stratagem: {stratagem_id}{LogColors.ENDC}")
    
    # Return list of stratagems to create
    return [stratagem_payload]
#!/usr/bin/env python3
"""
Transfer Ducats Stratagem Creator

Creates a stratagem for directly transferring ducats from one citizen to another.
Can be used to sell services, exchange favors, or make simple payments.
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
    now_utc_dt: datetime,
    api_base_url: Optional[str] = None,
    transport_api_url: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a transfer_ducats stratagem.
    
    Expected stratagem_params:
    - targetCitizenUsername (str, required): The citizen to receive ducats
    - amount (float, required): The amount of ducats to transfer
    - reason (str, optional): Reason for the transfer (e.g., "Payment for services", "Gift", etc.)
    - name (str, optional): Custom name for the stratagem
    - description (str, optional): Custom description
    - notes (str, optional): Additional notes
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")
    
    if stratagem_type != "transfer_ducats":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'transfer_ducats' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None
    
    # Extract parameters
    target_citizen_username = stratagem_params.get('targetCitizenUsername')
    amount = stratagem_params.get('amount')
    reason = stratagem_params.get('reason', 'Direct transfer')
    
    # Custom fields
    custom_name = stratagem_params.get('name')
    custom_description = stratagem_params.get('description')
    custom_notes = stratagem_params.get('notes', '')
    
    # Validation
    if not target_citizen_username:
        log.error(f"{LogColors.FAIL}targetCitizenUsername is required for transfer_ducats stratagem{LogColors.ENDC}")
        return None
    
    if amount is None:
        log.error(f"{LogColors.FAIL}amount is required for transfer_ducats stratagem{LogColors.ENDC}")
        return None
    
    try:
        amount = float(amount)
        if amount <= 0:
            log.error(f"{LogColors.FAIL}amount must be positive for transfer_ducats stratagem{LogColors.ENDC}")
            return None
    except ValueError:
        log.error(f"{LogColors.FAIL}amount must be a valid number for transfer_ducats stratagem{LogColors.ENDC}")
        return None
    
    if target_citizen_username == citizen_username:
        log.error(f"{LogColors.FAIL}Cannot transfer ducats to oneself{LogColors.ENDC}")
        return None
    
    # Verify both citizens exist and sender has sufficient funds
    try:
        # Check target citizen exists
        target_formula = f"{{Username}}='{_escape_airtable_value(target_citizen_username)}'"
        target_records = tables['citizens'].all(formula=target_formula, max_records=1)
        
        if not target_records:
            log.error(f"{LogColors.FAIL}Target citizen '{target_citizen_username}' not found{LogColors.ENDC}")
            return None
        
        # Check sender has sufficient funds
        sender_formula = f"{{Username}}='{_escape_airtable_value(citizen_username)}'"
        sender_records = tables['citizens'].all(formula=sender_formula, max_records=1)
        
        if not sender_records:
            log.error(f"{LogColors.FAIL}Sender citizen '{citizen_username}' not found{LogColors.ENDC}")
            return None
        
        sender_ducats = float(sender_records[0]['fields'].get('Ducats', 0))
        
        if sender_ducats < amount:
            log.error(f"{LogColors.FAIL}Sender {citizen_username} has insufficient funds ({sender_ducats} ducats) to transfer {amount} ducats{LogColors.ENDC}")
            return None
    
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error verifying citizens: {e}{LogColors.ENDC}")
        return None
    
    # Generate stratagem ID
    stratagem_id = f"transfer_ducats_{citizen_username}_{target_citizen_username}_{int(now_utc_dt.timestamp())}"
    
    # This is an instant stratagem that executes immediately
    expires_at = now_utc_dt + timedelta(minutes=5)  # Expires quickly since it's instant
    
    # Build stratagem payload
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": "transfer_ducats",
        "Variant": "instant",  # This is an instant execution stratagem
        "ExecutedBy": citizen_username,
        "TargetCitizen": target_citizen_username,
        "Status": "active",
        "Category": "economic",
        "Name": custom_name or f"Transfer {amount} ducats to {target_citizen_username}",
        "Description": custom_description or f"{citizen_username} transfers {amount} ducats to {target_citizen_username}. Reason: {reason}",
        "Notes": json.dumps({
            "initial_notes": custom_notes,
            "amount": amount,
            "reason": reason,
            "sender_balance_before": sender_ducats,
            "created_at": now_utc_dt.isoformat()
        }),
        "ExpiresAt": expires_at.isoformat()
    }
    
    log.info(f"{LogColors.OKGREEN}Successfully prepared transfer_ducats stratagem: {stratagem_id}{LogColors.ENDC}")
    
    # Return list of stratagems to create
    return [stratagem_payload]
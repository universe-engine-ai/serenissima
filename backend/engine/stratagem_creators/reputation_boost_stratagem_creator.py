#!/usr/bin/env python3
"""
Reputation Boost Stratagem Creator

Creates reputation boost stratagems to improve a citizen's public image.
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
    Creates a reputation_boost stratagem.
    
    Expected stratagem_params:
    - targetCitizenUsername (str, required): The citizen whose reputation to boost
    - campaignIntensity (str, optional): "Modest", "Standard", or "Intense" (default "Standard")
    - campaignDurationDays (int, optional): Duration of campaign (default 30, range 30-60)
    - campaignBudget (int, optional): Ducats for campaign (defaults based on intensity)
    - name (str, optional): Custom name
    - description (str, optional): Custom description
    - notes (str, optional): Additional notes
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")
    
    if stratagem_type != "reputation_boost":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'reputation_boost' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None
    
    # Extract parameters
    target_citizen_username = stratagem_params.get('targetCitizenUsername')
    campaign_intensity = stratagem_params.get('campaignIntensity', 'Standard')
    campaign_duration_days = stratagem_params.get('campaignDurationDays', 30)
    campaign_budget = stratagem_params.get('campaignBudget')
    
    # Custom fields
    custom_name = stratagem_params.get('name')
    custom_description = stratagem_params.get('description')
    custom_notes = stratagem_params.get('notes', '')
    
    # Validation
    if not target_citizen_username:
        log.error(f"{LogColors.FAIL}targetCitizenUsername is required for reputation_boost stratagem{LogColors.ENDC}")
        return None
    
    if campaign_intensity not in ['Modest', 'Standard', 'Intense']:
        log.error(f"{LogColors.FAIL}campaignIntensity must be 'Modest', 'Standard', or 'Intense'{LogColors.ENDC}")
        return None
    
    if campaign_duration_days < 30 or campaign_duration_days > 60:
        log.error(f"{LogColors.FAIL}campaignDurationDays must be between 30 and 60{LogColors.ENDC}")
        return None
    
    # Default budgets based on intensity
    default_budgets = {
        'Modest': 300,
        'Standard': 600,
        'Intense': 1200
    }
    
    if campaign_budget is None:
        campaign_budget = default_budgets[campaign_intensity]
    elif campaign_budget < 100:
        log.error(f"{LogColors.FAIL}campaignBudget must be at least 100 ducats{LogColors.ENDC}")
        return None
    
    # Daily budget calculation
    daily_budget = campaign_budget / campaign_duration_days
    
    # Verify target citizen exists
    try:
        target_formula = f"{{Username}}='{_escape_airtable_value(target_citizen_username)}'"
        target_records = tables['citizens'].all(formula=target_formula, max_records=1)
        
        if not target_records:
            log.error(f"{LogColors.FAIL}Target citizen '{target_citizen_username}' not found{LogColors.ENDC}")
            return None
        
        # Verify sponsor has sufficient wealth
        sponsor_formula = f"{{Username}}='{_escape_airtable_value(citizen_username)}'"
        sponsor_records = tables['citizens'].all(formula=sponsor_formula, max_records=1)
        
        if not sponsor_records:
            log.error(f"{LogColors.FAIL}Sponsor citizen '{citizen_username}' not found{LogColors.ENDC}")
            return None
        
        sponsor_ducats = float(sponsor_records[0]['fields'].get('Ducats', 0))
        
        # Warn if sponsor may not have enough funds
        if sponsor_ducats < campaign_budget:
            log.warning(f"{LogColors.WARNING}Sponsor {citizen_username} has {sponsor_ducats} ducats but campaign will cost {campaign_budget} total{LogColors.ENDC}")
            custom_notes += f"\nWarning: Sponsor has limited funds ({sponsor_ducats} ducats)"
    
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error verifying citizens: {e}{LogColors.ENDC}")
        return None
    
    # Generate stratagem ID
    stratagem_id = f"reputation_boost_{citizen_username}_{target_citizen_username}_{int(now_utc_dt.timestamp())}"
    
    # Calculate expiration
    expires_at = now_utc_dt + timedelta(days=campaign_duration_days)
    
    # Build stratagem payload
    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": "reputation_boost",
        "Variant": campaign_intensity,
        "ExecutedBy": citizen_username,
        "TargetCitizen": target_citizen_username,
        "Status": "active",
        "Category": "personal",
        "Name": custom_name or f"Reputation Campaign for {target_citizen_username}",
        "Description": custom_description or f"{citizen_username} sponsors a {campaign_intensity.lower()} campaign to improve {target_citizen_username}'s reputation",
        "Notes": json.dumps({
            "initial_notes": custom_notes.strip(),
            "campaign_intensity": campaign_intensity,
            "campaign_budget": campaign_budget,
            "daily_budget": round(daily_budget, 2),
            "duration_days": campaign_duration_days,
            "created_at": now_utc_dt.isoformat()
        }),
        "InfluenceCost": 0,  # Influence costs removed
        "CreatedAt": now_utc_dt.isoformat(),
        "ExpiresAt": expires_at.isoformat()
    }
    
    log.info(f"{LogColors.OKGREEN}Successfully prepared reputation_boost stratagem: {stratagem_id}{LogColors.ENDC}")
    
    # Return list of stratagems to create
    return [stratagem_payload]
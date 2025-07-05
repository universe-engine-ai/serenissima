"""
Activity Creator: Create Galley Grain Contracts
Bridges the gap between foreign grain in galleys and local mill needs

This creates public_sell contracts from galleys to enable mills to purchase grain
through the existing commerce system.
"""

import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    get_building_record,
    get_citizen_record,
    create_activity_record
)

log = logging.getLogger(__name__)

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    details: Dict[str, Any],
    api_base_url: Optional[str] = None,
    transport_api_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates an activity for a citizen to create public_sell contracts for grain in galleys.
    
    This bridges the commerce gap where foreign merchants have grain but mills can't access it.
    
    Parameters:
    - tables: Airtable instances
    - citizen_record: The citizen creating the contracts (usually a merchant or administrator)
    - details: {
        'galley_id': ID of the galley with grain
        'target_mills': List of mill IDs that need grain (optional)
        'price_multiplier': Price adjustment (default 0.9 for emergency discount)
        'duration_hours': How long contracts should last (default 24)
    }
    """
    
    citizen_username = citizen_record['fields'].get('Username')
    citizen_id = citizen_record['fields'].get('CitizenId')
    
    log.info(f"{LogColors.HEADER}Bridge-Shepherd: Creating galley grain contracts for {citizen_username}{LogColors.ENDC}")
    
    # Validate inputs
    galley_id = details.get('galley_id')
    if not galley_id:
        log.error(f"{LogColors.FAIL}No galley_id provided for grain contract creation{LogColors.ENDC}")
        return None
        
    # Get galley record
    galley_record = get_building_record(tables, galley_id)
    if not galley_record:
        log.error(f"{LogColors.FAIL}Galley {galley_id} not found{LogColors.ENDC}")
        return None
        
    if galley_record['fields'].get('Type') != 'merchant_galley':
        log.error(f"{LogColors.FAIL}Building {galley_id} is not a merchant galley{LogColors.ENDC}")
        return None
        
    # Check for grain in galley
    grain_formula = f"AND({{Type}}='grain', {{Asset}}='{_escape_airtable_value(galley_id)}', {{AssetType}}='building', {{decayedAt}}=BLANK())"
    grain_resources = tables['resources'].all(formula=grain_formula)
    
    if not grain_resources:
        log.warning(f"{LogColors.WARNING}No grain found in galley {galley_id}{LogColors.ENDC}")
        return None
        
    total_grain = sum(r['fields'].get('Count', 0) for r in grain_resources)
    log.info(f"{LogColors.OKBLUE}Found {total_grain} grain in galley {galley_id}{LogColors.ENDC}")
    
    # Determine target mills
    target_mills = details.get('target_mills', [])
    if not target_mills:
        # Find all mills with low grain
        log.info(f"{LogColors.OKBLUE}No specific mills targeted, finding hungry mills...{LogColors.ENDC}")
        mill_formula = "AND(OR({Type}='mill', {Type}='automated_mill'), {IsConstructed}=TRUE())"
        all_mills = tables['buildings'].all(formula=mill_formula)
        
        for mill in all_mills:
            mill_id = mill['fields'].get('BuildingId')
            if not mill_id:
                continue
                
            # Check grain at mill
            mill_grain_formula = f"AND({{Type}}='grain', {{Asset}}='{_escape_airtable_value(mill_id)}', {{AssetType}}='building', {{decayedAt}}=BLANK())"
            mill_grain = tables['resources'].all(formula=mill_grain_formula)
            current_grain = sum(r['fields'].get('Count', 0) for r in mill_grain)
            
            if current_grain < 50:  # Mills with less than 50 grain are hungry
                target_mills.append(mill_id)
                log.info(f"{LogColors.OKBLUE}Mill {mill_id} has only {current_grain} grain, adding to targets{LogColors.ENDC}")
    
    if not target_mills:
        log.warning(f"{LogColors.WARNING}No target mills found that need grain{LogColors.ENDC}")
        return None
    
    # Create activity parameters
    price_multiplier = details.get('price_multiplier', 0.9)  # 10% discount by default
    duration_hours = details.get('duration_hours', 24)
    
    activity_details = {
        'galley_id': galley_id,
        'galley_owner': galley_record['fields'].get('Owner'),
        'total_grain': total_grain,
        'target_mills': target_mills[:5],  # Limit to 5 mills per activity
        'price_multiplier': price_multiplier,
        'duration_hours': duration_hours,
        'contracts_to_create': min(len(target_mills), 5),
        'grain_per_contract': total_grain // min(len(target_mills), 5)
    }
    
    # Create the activity
    now_utc = datetime.now(pytz.utc)
    activity = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type='create_galley_grain_contracts',
        start_date_iso=now_utc.isoformat(),
        end_date_iso=(now_utc + timedelta(minutes=5)).isoformat(),  # Quick administrative task
        from_building_id=galley_id,
        to_building_id=None,
        resource_json=json.dumps([{
            'ResourceId': 'grain',
            'Amount': total_grain
        }]),
        contract_id=None,
        path_json=None,
        details_json=json.dumps(activity_details),
        priority_override=15,  # High priority for emergency response
        title=f"Bridge Commerce: Create grain contracts from {galley_id}"
    )
    
    if activity:
        log.info(f"{LogColors.OKGREEN}Created galley grain contract activity {activity['id']} for {citizen_username}{LogColors.ENDC}")
        log.info(f"{LogColors.OKGREEN}Will create {activity_details['contracts_to_create']} contracts for {total_grain} grain{LogColors.ENDC}")
        
        # Send notification to citizen
        notification_content = (
            f"EMERGENCY COMMERCE BRIDGE: You've been tasked with creating grain contracts "
            f"from galley {galley_id} to help feed starving citizens. "
            f"{total_grain} grain available for distribution to {len(target_mills)} mills."
        )
        
        try:
            tables['notifications'].create({
                'Citizen': citizen_username,
                'Type': 'emergency_task',
                'Content': notification_content,
                'CreatedAt': now_utc.isoformat(),
                'Status': 'unread'
            })
        except Exception as e:
            log.warning(f"{LogColors.WARNING}Failed to create notification: {e}{LogColors.ENDC}")
    
    return activity
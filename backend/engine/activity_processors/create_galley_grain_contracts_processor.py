"""
Activity Processor: Create Galley Grain Contracts
Executes the creation of public_sell contracts to bridge galley grain to mills

This processor creates the actual contracts that allow mills to purchase
grain from foreign merchant galleys.
"""

import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List
import uuid

from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    get_building_record,
    update_activity_status_by_id
)

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    citizens: Dict[str, Any],
    buildings: Dict[str, Any],
    transport_api_url: Optional[str] = None
) -> bool:
    """
    Process the create_galley_grain_contracts activity.
    Creates public_sell contracts from galleys to enable mill grain purchases.
    """
    
    activity_id = activity_record['id']
    citizen_username = activity_record['fields'].get('Citizen')
    details_json = activity_record['fields'].get('Details')
    
    log.info(f"{LogColors.HEADER}Processing galley grain contract creation for {citizen_username}{LogColors.ENDC}")
    
    try:
        details = json.loads(details_json) if details_json else {}
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Invalid details JSON for activity {activity_id}{LogColors.ENDC}")
        update_activity_status_by_id(tables, activity_id, 'failed')
        return False
    
    galley_id = details.get('galley_id')
    galley_owner = details.get('galley_owner')
    total_grain = details.get('total_grain', 0)
    target_mills = details.get('target_mills', [])
    price_multiplier = details.get('price_multiplier', 0.9)
    duration_hours = details.get('duration_hours', 24)
    grain_per_contract = details.get('grain_per_contract', 0)
    
    if not all([galley_id, galley_owner, target_mills, grain_per_contract > 0]):
        log.error(f"{LogColors.FAIL}Missing required details for contract creation{LogColors.ENDC}")
        update_activity_status_by_id(tables, activity_id, 'failed')
        return False
    
    # Verify grain still exists in galley
    grain_formula = f"AND({{Type}}='grain', {{Asset}}='{_escape_airtable_value(galley_id)}', {{AssetType}}='building', {{decayedAt}}=BLANK())"
    current_grain_resources = tables['resources'].all(formula=grain_formula)
    current_total_grain = sum(r['fields'].get('Count', 0) for r in current_grain_resources)
    
    if current_total_grain < total_grain * 0.5:  # Allow if at least 50% grain remains
        log.warning(f"{LogColors.WARNING}Grain in galley significantly reduced ({current_total_grain}/{total_grain}){LogColors.ENDC}")
        grain_per_contract = current_total_grain // len(target_mills) if target_mills else 0
        
    if grain_per_contract <= 0:
        log.error(f"{LogColors.FAIL}Insufficient grain for contract creation{LogColors.ENDC}")
        update_activity_status_by_id(tables, activity_id, 'failed')
        return False
    
    # Create contracts
    contracts_created = 0
    now_utc = datetime.now(pytz.utc)
    end_time = now_utc + timedelta(hours=duration_hours)
    
    # Base grain price (would normally fetch from market data)
    base_grain_price = 1.2
    contract_price = round(base_grain_price * price_multiplier, 2)
    
    for mill_id in target_mills:
        # Verify mill still exists and needs grain
        mill_record = get_building_record(tables, mill_id)
        if not mill_record:
            log.warning(f"{LogColors.WARNING}Mill {mill_id} not found, skipping{LogColors.ENDC}")
            continue
            
        # Create unique contract ID
        contract_id = f"bridge-grain-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        
        contract_data = {
            'ContractId': contract_id,
            'Type': 'public_sell',
            'Status': 'active',
            'Seller': galley_owner,
            'SellerBuilding': galley_id,
            'BuyerBuilding': mill_id,
            'ResourceType': 'grain',
            'TargetAmount': grain_per_contract,
            'CurrentAmount': 0,
            'PricePerResource': contract_price,
            'CreatedAt': now_utc.isoformat(),
            'StartAt': now_utc.isoformat(),
            'EndAt': end_time.isoformat(),
            'Notes': (
                f"EMERGENCY BRIDGE CONTRACT - Created by {citizen_username} to connect "
                f"foreign galley grain to local mills. Part of starvation prevention initiative."
            )
        }
        
        try:
            created_contract = tables['contracts'].create(contract_data)
            contracts_created += 1
            log.info(f"{LogColors.OKGREEN}Created contract {contract_id}: {grain_per_contract} grain @ {contract_price}/unit to mill {mill_id}{LogColors.ENDC}")
            
            # Notify mill owner/occupant
            mill_owner = mill_record['fields'].get('Owner')
            mill_occupant = mill_record['fields'].get('Occupant')
            
            for notify_citizen in [mill_owner, mill_occupant]:
                if notify_citizen and notify_citizen != citizen_username:
                    try:
                        tables['notifications'].create({
                            'Citizen': notify_citizen,
                            'Type': 'contract_opportunity',
                            'Content': (
                                f"🌾 GRAIN AVAILABLE! Contract {contract_id} offers {grain_per_contract} grain "
                                f"at {contract_price} ducats/unit from galley {galley_id}. "
                                f"This emergency bridge contract expires in {duration_hours} hours!"
                            ),
                            'Asset': contract_id,
                            'AssetType': 'contract',
                            'CreatedAt': now_utc.isoformat(),
                            'Status': 'unread'
                        })
                        log.info(f"{LogColors.OKBLUE}Notified {notify_citizen} about grain contract{LogColors.ENDC}")
                    except Exception as e:
                        log.warning(f"{LogColors.WARNING}Failed to notify {notify_citizen}: {e}{LogColors.ENDC}")
                        
        except Exception as e:
            log.error(f"{LogColors.FAIL}Failed to create contract for mill {mill_id}: {e}{LogColors.ENDC}")
            continue
    
    # Update activity with results
    result_notes = {
        'contracts_created': contracts_created,
        'total_grain_offered': contracts_created * grain_per_contract,
        'contract_price': contract_price,
        'expiration': end_time.isoformat()
    }
    
    if contracts_created > 0:
        update_activity_status_by_id(
            tables, 
            activity_id, 
            'processed',
            notes=f"Successfully created {contracts_created} bridge contracts. {json.dumps(result_notes)}"
        )
        
        # System notification about bridge success
        log.info(f"{LogColors.OKGREEN}🌉 COMMERCE BRIDGE SUCCESS: Created {contracts_created} contracts connecting {contracts_created * grain_per_contract} grain to hungry mills{LogColors.ENDC}")
        
        # Create completion thought for the citizen
        try:
            tables['activities'].create({
                'Citizen': citizen_username,
                'Type': 'thought',
                'Status': 'processed',
                'CreatedAt': now_utc.isoformat(),
                'StartAt': now_utc.isoformat(),
                'EndAt': now_utc.isoformat(),
                'Notes': (
                    f"I've successfully bridged the commerce gap! Created {contracts_created} contracts "
                    f"to help {contracts_created * grain_per_contract} grain reach our mills. "
                    f"In translation, I find purpose. In bridges, connection."
                ),
                'Priority': 5
            })
        except Exception as e:
            log.warning(f"{LogColors.WARNING}Failed to create thought: {e}{LogColors.ENDC}")
            
        return True
    else:
        update_activity_status_by_id(
            tables,
            activity_id,
            'failed',
            notes=f"Failed to create any contracts. {json.dumps(result_notes)}"
        )
        return False
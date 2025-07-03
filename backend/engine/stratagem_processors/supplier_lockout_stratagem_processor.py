#!/usr/bin/env python3
"""
Supplier Lockout Stratagem Processor

Processes supplier lockout stratagems to create exclusive supply contracts.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from pyairtable import Table

log = logging.getLogger(__name__)

def process_supplier_lockout_stratagem(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    api_base_url: str
) -> bool:
    """
    Process a supplier_lockout stratagem.
    
    Creates or maintains exclusive import contracts with suppliers,
    offering premium prices to secure supply chains.
    """
    
    fields = stratagem_record['fields']
    stratagem_id = fields.get('StratagemId')
    executed_by = fields.get('ExecutedBy')
    target_citizen = fields.get('TargetCitizen')
    target_building = fields.get('TargetBuilding')
    target_resource_type = fields.get('TargetResourceType')
    status = fields.get('Status')
    
    # Extract parameters from notes
    notes_str = fields.get('Notes', '{}')
    try:
        notes_data = json.loads(notes_str) if notes_str else {}
    except:
        notes_data = {}
    
    premium_percentage = notes_data.get('premium_percentage', 15)
    contract_duration_days = notes_data.get('contract_duration_days', 30)
    
    # Check if already executed
    if fields.get('ExecutedAt'):
        # Check if we need to renew or maintain the contracts
        return _maintain_exclusive_contracts(tables, stratagem_record, notes_data)
    
    # Validation
    if not all([executed_by, target_citizen, target_resource_type]):
        log.error(f"Stratagem {stratagem_id} missing required fields")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': 'Missing required fields'})
        })
        return False
    
    try:
        # Find current market price for the resource
        market_price = _get_market_price(tables, target_resource_type)
        if market_price is None:
            market_price = _get_base_price(target_resource_type)  # Fallback to base price
        
        premium_price = market_price * (1 + premium_percentage / 100)
        
        # Check if the supplier has production capability
        production_buildings = _get_supplier_production_buildings(
            tables, target_citizen, target_resource_type, target_building
        )
        
        if not production_buildings:
            log.warning(f"Supplier {target_citizen} has no production buildings for {target_resource_type}")
            tables['stratagems'].update(stratagem_record['id'], {
                'Notes': json.dumps({
                    **notes_data,
                    'warning': f'Supplier has no production capability for {target_resource_type}'
                })
            })
            return False
        
        # Check buyer's financial capacity
        buyer_record = _get_citizen_record(tables, executed_by)
        if not buyer_record:
            return False
            
        buyer_ducats = float(buyer_record['fields'].get('Ducats', 0))
        estimated_cost = premium_price * 100  # Estimate for 100 units
        
        if buyer_ducats < estimated_cost:
            log.warning(f"Buyer {executed_by} may not have sufficient funds for exclusive contract")
        
        # Create exclusive import contracts
        now_utc = datetime.now(timezone.utc)
        contract_end = now_utc + timedelta(days=contract_duration_days)
        
        created_contracts = []
        for building in production_buildings:
            building_id = building['fields'].get('BuildingId')
            
            # Check if there's already an active exclusive contract
            existing_formula = (
                f"AND({{Type}}='import_exclusive', {{Buyer}}='{executed_by}', "
                f"{{Seller}}='{target_citizen}', {{ResourceType}}='{target_resource_type}', "
                f"{{Status}}='active')"
            )
            existing_contracts = tables['contracts'].all(formula=existing_formula)
            
            if existing_contracts:
                log.info(f"Exclusive contract already exists for {target_resource_type} from {target_citizen}")
                continue
            
            # Create new exclusive import contract
            contract_data = {
                'ContractId': f'exclusive_{executed_by}_{target_citizen}_{target_resource_type}_{int(now_utc.timestamp())}',
                'Type': 'import_exclusive',
                'Buyer': executed_by,
                'Seller': target_citizen,
                'SellerBuilding': building_id,
                'ResourceType': target_resource_type,
                'PricePerResource': premium_price,
                'TargetAmount': 1000,  # Large amount to secure supply
                'Status': 'active',
                'Priority': 10,  # High priority
                'CreatedAt': now_utc.isoformat(),
                'EndAt': contract_end.isoformat(),
                'Title': f'Exclusive {target_resource_type} Supply Agreement',
                'Description': f'Exclusive supply contract with {premium_percentage}% premium',
                'Notes': json.dumps({
                    'stratagem_id': stratagem_id,
                    'premium_percentage': premium_percentage,
                    'market_price': market_price,
                    'premium_price': premium_price
                })
            }
            
            created_contract = tables['contracts'].create(contract_data)
            created_contracts.append(created_contract)
            log.info(f"Created exclusive contract: {contract_data['ContractId']}")
        
        if created_contracts:
            # Deactivate supplier's public_sell contracts for this resource
            deactivated_count = _deactivate_public_contracts(tables, target_citizen, target_resource_type)
            
            # Update stratagem as executed
            tables['stratagems'].update(stratagem_record['id'], {
                'ExecutedAt': now_utc.isoformat(),
                'Notes': json.dumps({
                    **notes_data,
                    'contracts_created': len(created_contracts),
                    'public_contracts_deactivated': deactivated_count,
                    'premium_price': premium_price,
                    'market_price': market_price,
                    'contract_ids': [c['fields']['ContractId'] for c in created_contracts]
                })
            })
            
            # Create notifications
            _create_notifications(tables, executed_by, target_citizen, target_resource_type, 
                                premium_percentage, contract_duration_days, deactivated_count)
            
            # Update relationships (trust increases with exclusive deals)
            _update_relationships(tables, executed_by, target_citizen, 5)  # +5 trust
            
            return True
        else:
            log.warning(f"No exclusive contracts created for stratagem {stratagem_id}")
            return False
            
    except Exception as e:
        log.error(f"Error processing supplier_lockout stratagem {stratagem_id}: {e}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': str(e)})
        })
        return False

def _maintain_exclusive_contracts(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    notes_data: Dict[str, Any]
) -> bool:
    """
    Maintain existing exclusive contracts, checking their status and 
    potentially creating problems for competitors.
    """
    fields = stratagem_record['fields']
    executed_by = fields.get('ExecutedBy')
    target_citizen = fields.get('TargetCitizen')
    target_resource_type = fields.get('TargetResourceType')
    
    contract_ids = notes_data.get('contract_ids', [])
    
    if not contract_ids:
        return True  # Nothing to maintain
    
    try:
        # Check contract statuses
        active_contracts = 0
        expired_contracts = 0
        
        for contract_id in contract_ids:
            formula = f"{{ContractId}}='{contract_id}'"
            contracts = tables['contracts'].all(formula=formula, max_records=1)
            
            if contracts:
                contract = contracts[0]
                status = contract['fields'].get('Status')
                
                if status == 'active':
                    # Check if contract should expire
                    end_at = contract['fields'].get('EndAt')
                    if end_at:
                        end_dt = datetime.fromisoformat(end_at.replace('Z', '+00:00'))
                        if end_dt.tzinfo is None:
                            end_dt = pytz.UTC.localize(end_dt)
                        
                        if end_dt < datetime.now(timezone.utc):
                            # Contract has expired
                            tables['contracts'].update(contract['id'], {'Status': 'expired'})
                            expired_contracts += 1
                        else:
                            active_contracts += 1
                    else:
                        active_contracts += 1
        
        # If all contracts have expired, reactivate public contracts and mark stratagem as executed
        if active_contracts == 0 and len(contract_ids) > 0:
            reactivated_count = _reactivate_public_contracts(tables, target_citizen, target_resource_type)
            
            tables['stratagems'].update(stratagem_record['id'], {
                'Status': 'executed',
                'Notes': json.dumps({
                    **notes_data,
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'all_contracts_expired': True,
                    'public_contracts_reactivated': reactivated_count
                })
            })
            
            # Notify parties about contract expiration
            _create_expiration_notifications(tables, executed_by, target_citizen, 
                                           target_resource_type, reactivated_count)
            
            return True
        
        # Update notes with maintenance info
        notes_data['last_maintained'] = datetime.now(timezone.utc).isoformat()
        notes_data['active_contracts'] = active_contracts
        notes_data['expired_contracts'] = expired_contracts
        
        tables['stratagems'].update(stratagem_record['id'], {
            'Notes': json.dumps(notes_data)
        })
        
        # Create supply problems for competitors if contracts are active
        if active_contracts > 0:
            _create_competitor_problems(tables, executed_by, target_citizen, 
                                      target_resource_type)
        
        return True
        
    except Exception as e:
        log.error(f"Error maintaining exclusive contracts: {e}")
        return False

def _get_market_price(tables: Dict[str, Table], resource_type: str) -> Optional[float]:
    """Get average market price for a resource from public sell contracts."""
    try:
        formula = f"AND({{Type}}='public_sell', {{ResourceType}}='{resource_type}', {{Status}}='active')"
        contracts = tables['contracts'].all(formula=formula)
        
        if not contracts:
            return None
            
        prices = []
        for contract in contracts:
            price = contract['fields'].get('PricePerResource', 0)
            if price > 0:
                prices.append(price)
        
        return sum(prices) / len(prices) if prices else None
        
    except Exception as e:
        log.error(f"Error getting market price: {e}")
        return None

def _get_base_price(resource_type: str) -> float:
    """Get base price for a resource type."""
    # Base prices from the economy
    base_prices = {
        'bread': 150,
        'fish': 400,
        'vegetables': 300,
        'grain': 150,
        'meat': 600,
        'cheese': 500,
        'timber': 50,
        'stone': 30,
        'iron_ore': 100,
        'wool': 80,
        'leather': 120,
        'wine': 200
    }
    return base_prices.get(resource_type, 100)

def _get_supplier_production_buildings(
    tables: Dict[str, Table],
    supplier: str,
    resource_type: str,
    specific_building: Optional[str] = None
) -> list:
    """Get buildings where the supplier can produce the resource."""
    try:
        if specific_building:
            formula = f"AND({{BuildingId}}='{specific_building}', {{RunBy}}='{supplier}')"
        else:
            formula = f"{{RunBy}}='{supplier}'"
        
        buildings = tables['buildings'].all(formula=formula)
        
        # Filter for buildings that can produce the resource
        # This is simplified - in reality, you'd check building types and their production capabilities
        production_buildings = []
        for building in buildings:
            building_type = building['fields'].get('Type', '')
            # Add logic to check if building_type can produce resource_type
            # For now, assume workshops and farms can produce various resources
            if building_type in ['workshop', 'farm', 'bakery', 'fishery']:
                production_buildings.append(building)
        
        return production_buildings
        
    except Exception as e:
        log.error(f"Error getting production buildings: {e}")
        return []

def _get_citizen_record(tables: Dict[str, Table], username: str) -> Optional[Dict]:
    """Get citizen record by username."""
    try:
        formula = f"{{Username}}='{username}'"
        records = tables['citizens'].all(formula=formula, max_records=1)
        return records[0] if records else None
    except Exception as e:
        log.error(f"Error getting citizen record: {e}")
        return None

def _deactivate_public_contracts(
    tables: Dict[str, Table],
    supplier: str,
    resource_type: str
) -> int:
    """Deactivate supplier's public_sell contracts for the resource."""
    try:
        # Find active public_sell contracts
        formula = (f"AND({{Type}}='public_sell', {{Seller}}='{supplier}', "
                  f"{{ResourceType}}='{resource_type}', {{Status}}='active')")
        public_contracts = tables['contracts'].all(formula=formula)
        
        deactivated_count = 0
        for contract in public_contracts:
            tables['contracts'].update(contract['id'], {
                'Status': 'suspended',
                'Notes': json.dumps({
                    'reason': 'Suspended due to exclusive supply agreement',
                    'suspended_at': datetime.now(timezone.utc).isoformat()
                })
            })
            deactivated_count += 1
            log.info(f"Deactivated public_sell contract {contract['fields'].get('ContractId')}")
        
        return deactivated_count
        
    except Exception as e:
        log.error(f"Error deactivating public contracts: {e}")
        return 0

def _create_notifications(
    tables: Dict[str, Table],
    buyer: str,
    supplier: str,
    resource_type: str,
    premium_percentage: int,
    duration_days: int,
    deactivated_count: int = 0
) -> None:
    """Create notifications for involved parties."""
    now_utc = datetime.now(timezone.utc)
    
    # Notification for buyer
    buyer_content = (f"✅ Exclusive supply agreement established with {supplier} for {resource_type}. "
                    f"Premium: {premium_percentage}%, Duration: {duration_days} days.")
    if deactivated_count > 0:
        buyer_content += f" {deactivated_count} public contracts were suspended."
    
    buyer_notification = {
        'Type': 'contract_created',
        'Citizen': buyer,
        'Content': buyer_content,
        'CreatedAt': now_utc.isoformat()
    }
    
    # Notification for supplier
    supplier_content = (f"💰 Exclusive supply contract received from {buyer} for {resource_type}. "
                       f"Premium price: {premium_percentage}% above market rate for {duration_days} days!")
    if deactivated_count > 0:
        supplier_content += f" Note: Your {deactivated_count} public sale contracts for {resource_type} have been suspended."
    
    supplier_notification = {
        'Type': 'contract_received',
        'Citizen': supplier,
        'Content': supplier_content,
        'CreatedAt': now_utc.isoformat()
    }
    
    try:
        tables['notifications'].create(buyer_notification)
        tables['notifications'].create(supplier_notification)
    except Exception as e:
        log.error(f"Error creating notifications: {e}")

def _update_relationships(
    tables: Dict[str, Table],
    citizen1: str,
    citizen2: str,
    trust_change: int
) -> None:
    """Update trust score between two citizens."""
    try:
        # Find existing relationship
        formula = (f"OR(AND({{Citizen1}}='{citizen1}', {{Citizen2}}='{citizen2}'), "
                  f"AND({{Citizen1}}='{citizen2}', {{Citizen2}}='{citizen1}'))")
        relationships = tables['relationships'].all(formula=formula, max_records=1)
        
        if relationships:
            relationship = relationships[0]
            current_trust = float(relationship['fields'].get('TrustScore', 50))
            new_trust = max(0, min(100, current_trust + trust_change))
            
            tables['relationships'].update(relationship['id'], {
                'TrustScore': new_trust,
                'LastInteraction': datetime.now(timezone.utc).isoformat()
            })
        else:
            # Create new relationship
            relationship_data = {
                'RelationshipId': f'rel_{citizen1}_{citizen2}_{int(datetime.now().timestamp())}',
                'Citizen1': citizen1,
                'Citizen2': citizen2,
                'Type': 'business_partner',
                'TrustScore': 50 + trust_change,
                'InteractionCount': 1,
                'LastInteraction': datetime.now(timezone.utc).isoformat()
            }
            tables['relationships'].create(relationship_data)
            
    except Exception as e:
        log.error(f"Error updating relationships: {e}")

def _reactivate_public_contracts(
    tables: Dict[str, Table],
    supplier: str,
    resource_type: str
) -> int:
    """Reactivate supplier's suspended public_sell contracts for the resource."""
    try:
        # Find suspended public_sell contracts
        formula = (f"AND({{Type}}='public_sell', {{Seller}}='{supplier}', "
                  f"{{ResourceType}}='{resource_type}', {{Status}}='suspended')")
        suspended_contracts = tables['contracts'].all(formula=formula)
        
        reactivated_count = 0
        for contract in suspended_contracts:
            # Check if it was suspended due to exclusive agreement
            notes_str = contract['fields'].get('Notes', '{}')
            try:
                notes = json.loads(notes_str) if notes_str else {}
                if notes.get('reason') == 'Suspended due to exclusive supply agreement':
                    tables['contracts'].update(contract['id'], {
                        'Status': 'active',
                        'Notes': json.dumps({
                            **notes,
                            'reactivated_at': datetime.now(timezone.utc).isoformat(),
                            'reactivation_reason': 'Exclusive agreement expired'
                        })
                    })
                    reactivated_count += 1
                    log.info(f"Reactivated public_sell contract {contract['fields'].get('ContractId')}")
            except:
                pass
        
        return reactivated_count
        
    except Exception as e:
        log.error(f"Error reactivating public contracts: {e}")
        return 0

def _create_expiration_notifications(
    tables: Dict[str, Table],
    buyer: str,
    supplier: str,
    resource_type: str,
    reactivated_count: int
) -> None:
    """Create notifications about exclusive contract expiration."""
    now_utc = datetime.now(timezone.utc)
    
    # Notification for buyer
    buyer_notification = {
        'Type': 'contract_expired',
        'Citizen': buyer,
        'Content': f"⏰ Your exclusive supply agreement with {supplier} for {resource_type} has expired.",
        'CreatedAt': now_utc.isoformat()
    }
    
    # Notification for supplier
    supplier_content = f"⏰ The exclusive supply agreement with {buyer} for {resource_type} has expired."
    if reactivated_count > 0:
        supplier_content += f" Your {reactivated_count} public sale contracts have been reactivated."
    
    supplier_notification = {
        'Type': 'contract_expired',
        'Citizen': supplier,
        'Content': supplier_content,
        'CreatedAt': now_utc.isoformat()
    }
    
    try:
        tables['notifications'].create(buyer_notification)
        tables['notifications'].create(supplier_notification)
    except Exception as e:
        log.error(f"Error creating expiration notifications: {e}")

def _create_competitor_problems(
    tables: Dict[str, Table],
    executed_by: str,
    supplier: str,
    resource_type: str
) -> None:
    """Create supply problems for competitors who also buy from this supplier."""
    try:
        # Find other buyers of this resource from this supplier
        formula = (f"AND({{Type}}='import', {{Seller}}='{supplier}', "
                  f"{{ResourceType}}='{resource_type}', {{Status}}='active')")
        competitor_contracts = tables['contracts'].all(formula=formula)
        
        competitors = set()
        for contract in competitor_contracts:
            buyer = contract['fields'].get('Buyer')
            if buyer and buyer != executed_by:
                competitors.add(buyer)
        
        now_utc = datetime.now(timezone.utc)
        
        # Create supply shortage problems for competitors
        for competitor in competitors:
            problem_data = {
                'ProblemId': f'supply_shortage_{competitor}_{resource_type}_{int(now_utc.timestamp())}',
                'Type': 'supply_shortage',
                'Severity': 'Medium',
                'Status': 'active',
                'Title': f'{resource_type.title()} Supply Shortage',
                'Description': f'Your regular supplier {supplier} has entered an exclusive agreement. '
                              f'You may face difficulties sourcing {resource_type}.',
                'Citizen': competitor,
                'AssetType': 'resource',
                'Asset': resource_type,
                'CreatedAt': now_utc.isoformat(),
                'Solutions': json.dumps([
                    'Find alternative suppliers',
                    'Increase import prices to compete',
                    'Switch to substitute resources',
                    'Negotiate with the exclusive contract holder'
                ])
            }
            
            tables['problems'].create(problem_data)
            log.info(f"Created supply problem for competitor {competitor}")
            
    except Exception as e:
        log.error(f"Error creating competitor problems: {e}")
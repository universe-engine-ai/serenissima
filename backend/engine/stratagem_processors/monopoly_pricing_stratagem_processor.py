#!/usr/bin/env python3
"""
Monopoly Pricing Stratagem Processor

Processes monopoly pricing stratagems to manipulate market prices.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pyairtable import Table

log = logging.getLogger(__name__)

def process_monopoly_pricing_stratagem(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    api_base_url: str
) -> bool:
    """
    Process a monopoly_pricing stratagem.
    
    Leverages market dominance to increase prices significantly.
    """
    
    fields = stratagem_record['fields']
    stratagem_id = fields.get('StratagemId')
    executed_by = fields.get('ExecutedBy')
    target_resource_type = fields.get('TargetResourceType')
    variant = fields.get('Variant', 'Standard')
    status = fields.get('Status')
    
    # Extract parameters from notes
    notes_str = fields.get('Notes', '{}')
    try:
        notes_data = json.loads(notes_str) if notes_str else {}
    except:
        notes_data = {}
    
    price_multiplier = notes_data.get('price_multiplier', 2.0)
    
    # Validation
    if not all([executed_by, target_resource_type]):
        log.error(f"Stratagem {stratagem_id} missing required fields")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': 'Missing required fields'})
        })
        return False
    
    try:
        now_utc = datetime.now(timezone.utc)
        
        # Get current market price (excluding the monopolist's own contracts)
        market_price = _get_market_price_excluding(tables, target_resource_type, executed_by)
        
        if market_price is None:
            # No other sellers, use base price
            market_price = _get_base_price(target_resource_type)
        
        # Calculate monopoly price
        monopoly_price = market_price * price_multiplier
        
        # Update all active public_sell contracts
        updated_contracts = _update_citizen_prices(
            tables, executed_by, target_resource_type, monopoly_price
        )
        
        if updated_contracts == 0:
            log.warning(f"No contracts updated for monopoly pricing stratagem {stratagem_id}")
            tables['stratagems'].update(stratagem_record['id'], {
                'Status': 'failed',
                'Notes': json.dumps({
                    **notes_data,
                    'error': 'No active contracts to update',
                    'failed_at': now_utc.isoformat()
                })
            })
            return False
        
        # Create problems for dependent consumers
        affected_citizens = _create_consumer_problems(
            tables, target_resource_type, monopoly_price, executed_by, stratagem_id
        )
        
        # Update relationships (negative impact)
        for affected in affected_citizens[:10]:  # Limit to avoid too many updates
            _update_relationships(tables, executed_by, affected, -5)  # Reduce trust
        
        # Create notifications
        _create_notification(
            tables,
            executed_by,
            'monopoly_pricing_active',
            f"💰 Your monopoly pricing for {target_resource_type} is now active. "
            f"Prices increased to {monopoly_price:.1f} ducats ({price_multiplier}x market rate). "
            f"{updated_contracts} contracts updated."
        )
        
        # Notify major consumers
        for affected in affected_citizens[:3]:
            _create_notification(
                tables,
                affected,
                'price_increase',
                f"⚠️ {executed_by} has dramatically increased {target_resource_type} prices to "
                f"{monopoly_price:.1f} ducats! Consider finding alternative suppliers."
            )
        
        # Update notes
        notes_data['last_update'] = now_utc.isoformat()
        notes_data['contracts_updated'] = updated_contracts
        notes_data['market_price'] = market_price
        notes_data['monopoly_price'] = monopoly_price
        notes_data['affected_citizens'] = len(affected_citizens)
        
        # Mark ExecutedAt on first execution
        update_data = {'Notes': json.dumps(notes_data)}
        if not fields.get('ExecutedAt'):
            update_data['ExecutedAt'] = now_utc.isoformat()
        
        tables['stratagems'].update(stratagem_record['id'], update_data)
        
        log.info(f"Successfully processed monopoly pricing for {target_resource_type} by {executed_by}")
        
        # Check if stratagem should expire
        expires_at_str = fields.get('ExpiresAt')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                import pytz
                expires_at = pytz.UTC.localize(expires_at)
            
            if expires_at <= now_utc:
                # Stratagem has expired - restore normal prices
                _restore_market_prices(tables, executed_by, target_resource_type)
                
                tables['stratagems'].update(stratagem_record['id'], {
                    'Status': 'completed',
                    'Notes': json.dumps({
                        **notes_data,
                        'completed_at': now_utc.isoformat(),
                        'prices_restored': True
                    })
                })
                
                _create_notification(
                    tables,
                    executed_by,
                    'monopoly_ended',
                    f"📊 Your monopoly pricing for {target_resource_type} has ended. "
                    f"Prices have been restored to market rates."
                )
        
        return True
        
    except Exception as e:
        log.error(f"Error processing monopoly_pricing stratagem {stratagem_id}: {e}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': str(e)})
        })
        return False

def _get_market_price_excluding(
    tables: Dict[str, Table], 
    resource_type: str, 
    exclude_seller: str
) -> Optional[float]:
    """Get average market price excluding a specific seller."""
    try:
        formula = (f"AND({{Type}}='public_sell', {{ResourceType}}='{resource_type}', "
                  f"{{Status}}='active', {{Seller}}!='{exclude_seller}')")
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
        'wine': 200,
        'spices': 800,
        'silk': 1000,
        'cloth': 400
    }
    return base_prices.get(resource_type, 100)

def _update_citizen_prices(
    tables: Dict[str, Table],
    seller: str,
    resource_type: str,
    new_price: float
) -> int:
    """Update all public_sell contracts to the new monopoly price."""
    try:
        formula = (f"AND({{Type}}='public_sell', {{Seller}}='{seller}', "
                  f"{{ResourceType}}='{resource_type}', {{Status}}='active')")
        contracts = tables['contracts'].all(formula=formula)
        
        updated_count = 0
        for contract in contracts:
            # Store original price if not already stored
            notes_str = contract['fields'].get('Notes', '{}')
            try:
                notes = json.loads(notes_str) if notes_str else {}
            except:
                notes = {}
            
            if 'original_price' not in notes:
                notes['original_price'] = contract['fields'].get('PricePerResource', 0)
            
            notes['monopoly_price'] = new_price
            notes['price_updated_at'] = datetime.now(timezone.utc).isoformat()
            
            tables['contracts'].update(contract['id'], {
                'PricePerResource': new_price,
                'Notes': json.dumps(notes)
            })
            updated_count += 1
        
        return updated_count
        
    except Exception as e:
        log.error(f"Error updating prices: {e}")
        return 0

def _create_consumer_problems(
    tables: Dict[str, Table],
    resource_type: str,
    new_price: float,
    monopolist: str,
    stratagem_id: str
) -> List[str]:
    """Create problems for citizens dependent on this resource."""
    affected_citizens = []
    
    try:
        # Find recent buyers of this resource
        formula = (f"AND({{Type}}='import', {{ResourceType}}='{resource_type}', "
                  f"{{Status}}='active', {{Seller}}!='{monopolist}')")
        import_contracts = tables['contracts'].all(formula=formula)
        
        buyers = set()
        for contract in import_contracts:
            buyer = contract['fields'].get('Buyer')
            if buyer and buyer != monopolist:
                buyers.add(buyer)
        
        now_utc = datetime.now(timezone.utc)
        
        # Create problems for major consumers
        for buyer in list(buyers)[:20]:  # Limit to avoid too many problems
            problem_data = {
                'ProblemId': f'monopoly_price_{buyer}_{resource_type}_{int(now_utc.timestamp())}',
                'Type': 'resource_shortage_high_price',
                'Severity': 'High',
                'Status': 'active',
                'Title': f'{resource_type.title()} Price Crisis',
                'Description': f'{monopolist} has monopolized {resource_type} and raised prices to {new_price:.1f} ducats. '
                              f'Your business operations may be severely impacted.',
                'Citizen': buyer,
                'AssetType': 'resource',
                'Asset': resource_type,
                'CreatedAt': now_utc.isoformat(),
                'Solutions': json.dumps([
                    'Find alternative suppliers',
                    'Switch to substitute resources',
                    'Negotiate with the monopolist',
                    'Reduce consumption',
                    'Organize collective bargaining'
                ]),
                'Notes': json.dumps({
                    'caused_by_stratagem': stratagem_id,
                    'monopolist': monopolist,
                    'inflated_price': new_price
                })
            }
            
            tables['problems'].create(problem_data)
            affected_citizens.append(buyer)
            
    except Exception as e:
        log.error(f"Error creating consumer problems: {e}")
    
    return affected_citizens

def _restore_market_prices(
    tables: Dict[str, Table],
    seller: str,
    resource_type: str
) -> None:
    """Restore prices to original or market levels."""
    try:
        formula = (f"AND({{Type}}='public_sell', {{Seller}}='{seller}', "
                  f"{{ResourceType}}='{resource_type}', {{Status}}='active')")
        contracts = tables['contracts'].all(formula=formula)
        
        # Get current market price
        market_price = _get_market_price_excluding(tables, resource_type, seller)
        if market_price is None:
            market_price = _get_base_price(resource_type)
        
        for contract in contracts:
            notes_str = contract['fields'].get('Notes', '{}')
            try:
                notes = json.loads(notes_str) if notes_str else {}
            except:
                notes = {}
            
            # Use original price if stored, otherwise use market price
            restore_price = notes.get('original_price', market_price)
            
            tables['contracts'].update(contract['id'], {
                'PricePerResource': restore_price,
                'Notes': json.dumps({
                    **notes,
                    'price_restored_at': datetime.now(timezone.utc).isoformat()
                })
            })
            
    except Exception as e:
        log.error(f"Error restoring prices: {e}")

def _create_notification(
    tables: Dict[str, Table],
    citizen: str,
    notification_type: str,
    content: str
) -> None:
    """Create a notification for a citizen."""
    try:
        notification_data = {
            'Type': notification_type,
            'Citizen': citizen,
            'Content': content,
            'CreatedAt': datetime.now(timezone.utc).isoformat()
        }
        tables['notifications'].create(notification_data)
    except Exception as e:
        log.error(f"Error creating notification: {e}")

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
                'Type': 'business_adversary',
                'TrustScore': 50 + trust_change,
                'InteractionCount': 1,
                'LastInteraction': datetime.now(timezone.utc).isoformat()
            }
            tables['relationships'].create(relationship_data)
            
    except Exception as e:
        log.error(f"Error updating relationships: {e}")
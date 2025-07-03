#!/usr/bin/env python3
"""
Financial Patronage Stratagem Processor

Processes financial patronage stratagems to provide ongoing financial support to other citizens.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from pyairtable import Table

log = logging.getLogger(__name__)

def process_financial_patronage_stratagem(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    api_base_url: str
) -> bool:
    """
    Process a financial_patronage stratagem.
    
    Provides daily financial support to the target citizen and builds relationships.
    """
    
    fields = stratagem_record['fields']
    stratagem_id = fields.get('StratagemId')
    executed_by = fields.get('ExecutedBy')
    target_citizen = fields.get('TargetCitizen')
    variant = fields.get('Variant', 'Standard')  # Patronage level
    status = fields.get('Status')
    
    # Extract parameters from notes
    notes_str = fields.get('Notes', '{}')
    try:
        notes_data = json.loads(notes_str) if notes_str else {}
    except:
        notes_data = {}
    
    daily_amount = notes_data.get('daily_amount', 10)
    last_payment_date = notes_data.get('last_payment_date')
    total_paid = notes_data.get('total_paid', 0)
    payments_made = notes_data.get('payments_made', 0)
    
    # Validation
    if not all([executed_by, target_citizen]):
        log.error(f"Stratagem {stratagem_id} missing required fields")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': 'Missing required fields'})
        })
        return False
    
    try:
        now_utc = datetime.now(timezone.utc)
        today_date = now_utc.date().isoformat()
        
        # Check if we've already made today's payment
        if last_payment_date == today_date:
            log.info(f"Already made payment for stratagem {stratagem_id} today")
            return True
        
        # Get patron's current funds
        patron_record = _get_citizen_record(tables, executed_by)
        if not patron_record:
            log.error(f"Patron {executed_by} not found")
            return False
        
        patron_ducats = float(patron_record['fields'].get('Ducats', 0))
        
        # Check if patron has sufficient funds
        if patron_ducats < daily_amount:
            log.warning(f"Patron {executed_by} has insufficient funds ({patron_ducats} < {daily_amount})")
            
            # Create notification about insufficient funds
            _create_notification(
                tables,
                executed_by,
                'insufficient_funds',
                f"❌ Unable to fulfill patronage payment to {target_citizen}. Insufficient funds ({patron_ducats:.1f} ducats < {daily_amount} required)."
            )
            
            # Mark stratagem as suspended
            tables['stratagems'].update(stratagem_record['id'], {
                'Status': 'suspended',
                'Notes': json.dumps({
                    **notes_data,
                    'suspended_at': now_utc.isoformat(),
                    'suspension_reason': 'Insufficient funds',
                    'patron_balance': patron_ducats
                })
            })
            return False
        
        # Get beneficiary record
        beneficiary_record = _get_citizen_record(tables, target_citizen)
        if not beneficiary_record:
            log.error(f"Beneficiary {target_citizen} not found")
            return False
        
        beneficiary_ducats = float(beneficiary_record['fields'].get('Ducats', 0))
        
        # Execute the transfer
        new_patron_balance = patron_ducats - daily_amount
        new_beneficiary_balance = beneficiary_ducats + daily_amount
        
        # Update patron's balance
        tables['citizens'].update(patron_record['id'], {
            'Ducats': new_patron_balance
        })
        
        # Update beneficiary's balance
        tables['citizens'].update(beneficiary_record['id'], {
            'Ducats': new_beneficiary_balance
        })
        
        # Record transaction
        transaction_data = {
            'TransactionId': f'patronage_{stratagem_id}_{int(now_utc.timestamp())}',
            'Type': 'patronage',
            'From': executed_by,
            'To': target_citizen,
            'Amount': daily_amount,
            'Description': f"{variant} patronage payment from {executed_by} to {target_citizen}",
            'CreatedAt': now_utc.isoformat(),
            'Notes': json.dumps({
                'stratagem_id': stratagem_id,
                'patronage_level': variant,
                'payment_number': payments_made + 1
            })
        }
        
        try:
            tables['transactions'].create(transaction_data)
        except:
            # If transactions table doesn't exist, log but continue
            log.warning("Could not record transaction - table may not exist")
        
        # Update relationship
        relationship_bonus = {
            'Modest': 3,
            'Standard': 5,
            'Generous': 8
        }.get(variant, 5)
        
        _update_relationships(tables, executed_by, target_citizen, relationship_bonus)
        
        # Create notifications
        _create_notification(
            tables,
            executed_by,
            'patronage_sent',
            f"💰 Sent {daily_amount} ducats to {target_citizen} as part of your {variant.lower()} patronage agreement."
        )
        
        _create_notification(
            tables,
            target_citizen,
            'patronage_received',
            f"💎 Received {daily_amount} ducats from your patron {executed_by}. Their generosity continues to support you!"
        )
        
        # Update stratagem notes
        notes_data['last_payment_date'] = today_date
        notes_data['total_paid'] = total_paid + daily_amount
        notes_data['payments_made'] = payments_made + 1
        notes_data['last_payment_time'] = now_utc.isoformat()
        
        # Mark ExecutedAt on first payment
        update_data = {'Notes': json.dumps(notes_data)}
        if not fields.get('ExecutedAt'):
            update_data['ExecutedAt'] = now_utc.isoformat()
        
        tables['stratagems'].update(stratagem_record['id'], update_data)
        
        log.info(f"Successfully processed patronage payment {payments_made + 1} for stratagem {stratagem_id}")
        
        # Check if stratagem should expire
        expires_at_str = fields.get('ExpiresAt')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                expires_at = pytz.UTC.localize(expires_at)
            
            if expires_at <= now_utc:
                # Stratagem has expired
                tables['stratagems'].update(stratagem_record['id'], {
                    'Status': 'completed',
                    'Notes': json.dumps({
                        **notes_data,
                        'completed_at': now_utc.isoformat(),
                        'completion_reason': 'Duration expired'
                    })
                })
                
                # Send completion notifications
                _create_notification(
                    tables,
                    executed_by,
                    'patronage_completed',
                    f"✅ Your {variant.lower()} patronage of {target_citizen} has completed. Total support provided: {notes_data['total_paid']} ducats over {notes_data['payments_made']} payments."
                )
                
                _create_notification(
                    tables,
                    target_citizen,
                    'patronage_ended',
                    f"📋 The patronage agreement with {executed_by} has concluded. You received {notes_data['total_paid']} ducats in total support."
                )
                
                # Final relationship boost for completing the patronage
                _update_relationships(tables, executed_by, target_citizen, 10)
        
        return True
        
    except Exception as e:
        log.error(f"Error processing financial_patronage stratagem {stratagem_id}: {e}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': str(e)})
        })
        return False

def _get_citizen_record(tables: Dict[str, Table], username: str) -> Optional[Dict]:
    """Get citizen record by username."""
    try:
        formula = f"{{Username}}='{username}'"
        records = tables['citizens'].all(formula=formula, max_records=1)
        return records[0] if records else None
    except Exception as e:
        log.error(f"Error getting citizen record: {e}")
        return None

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
            
            # Also increase strength score for patronage relationships
            current_strength = float(relationship['fields'].get('StrengthScore', 50))
            new_strength = max(0, min(100, current_strength + trust_change * 0.5))
            
            tables['relationships'].update(relationship['id'], {
                'TrustScore': new_trust,
                'StrengthScore': new_strength,
                'LastInteraction': datetime.now(timezone.utc).isoformat()
            })
        else:
            # Create new relationship
            relationship_data = {
                'RelationshipId': f'rel_{citizen1}_{citizen2}_{int(datetime.now().timestamp())}',
                'Citizen1': citizen1,
                'Citizen2': citizen2,
                'Type': 'patron_beneficiary',
                'TrustScore': 50 + trust_change,
                'StrengthScore': 50 + trust_change * 0.5,
                'InteractionCount': 1,
                'LastInteraction': datetime.now(timezone.utc).isoformat()
            }
            tables['relationships'].create(relationship_data)
            
    except Exception as e:
        log.error(f"Error updating relationships: {e}")
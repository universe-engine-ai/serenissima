"""
Stratagem Processor for "transfer_ducats".

This processor:
1. Validates that the sender still has sufficient funds
2. Transfers the specified amount from sender to receiver
3. Creates transaction records for both parties
4. Marks the stratagem as executed
"""

import logging
import json
from datetime import datetime
import pytz
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    VENICE_TIMEZONE
)

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None,
    building_type_defs: Optional[Dict[str, Any]] = None,
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes a "transfer_ducats" stratagem.
    This immediately transfers ducats from the executor to the target citizen.
    """
    stratagem_fields = stratagem_record['fields']
    stratagem_id = stratagem_fields.get('StratagemId', stratagem_record['id'])
    executed_by = stratagem_fields.get('ExecutedBy')
    target_citizen = stratagem_fields.get('TargetCitizen')
    
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'transfer_ducats' stratagem {stratagem_id} from {executed_by} to {target_citizen}.{LogColors.ENDC}")
    
    # Parse notes to get transfer details
    try:
        notes_data = json.loads(stratagem_fields.get('Notes', '{}'))
        amount = float(notes_data.get('amount', 0))
        reason = notes_data.get('reason', 'Direct transfer')
    except (json.JSONDecodeError, ValueError) as e:
        log.error(f"{LogColors.FAIL}Failed to parse stratagem notes: {e}{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': stratagem_fields.get('Notes', '') + f"\n[ERROR] Failed to parse transfer details: {e}"
        })
        return False
    
    if not executed_by or not target_citizen or amount <= 0:
        log.error(f"{LogColors.FAIL}Stratagem {stratagem_id} missing required fields or invalid amount.{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': stratagem_fields.get('Notes', '') + "\n[ERROR] Missing required fields or invalid amount."
        })
        return False
    
    now_utc_dt = datetime.now(pytz.utc)
    now_venice_dt = now_utc_dt.astimezone(VENICE_TIMEZONE)
    
    try:
        # Fetch current balances
        sender_formula = f"{{Username}}='{_escape_airtable_value(executed_by)}'"
        sender_records = tables['citizens'].all(formula=sender_formula, max_records=1)
        
        if not sender_records:
            log.error(f"{LogColors.FAIL}Sender {executed_by} not found.{LogColors.ENDC}")
            tables['stratagems'].update(stratagem_record['id'], {
                'Status': 'failed',
                'Notes': stratagem_fields.get('Notes', '') + f"\n[ERROR] Sender {executed_by} not found."
            })
            return False
        
        receiver_formula = f"{{Username}}='{_escape_airtable_value(target_citizen)}'"
        receiver_records = tables['citizens'].all(formula=receiver_formula, max_records=1)
        
        if not receiver_records:
            log.error(f"{LogColors.FAIL}Receiver {target_citizen} not found.{LogColors.ENDC}")
            tables['stratagems'].update(stratagem_record['id'], {
                'Status': 'failed',
                'Notes': stratagem_fields.get('Notes', '') + f"\n[ERROR] Receiver {target_citizen} not found."
            })
            return False
        
        sender_record = sender_records[0]
        receiver_record = receiver_records[0]
        
        sender_ducats = float(sender_record['fields'].get('Ducats', 0))
        receiver_ducats = float(receiver_record['fields'].get('Ducats', 0))
        
        # Check if sender has sufficient funds
        if sender_ducats < amount:
            log.error(f"{LogColors.FAIL}Sender {executed_by} has insufficient funds ({sender_ducats} < {amount}).{LogColors.ENDC}")
            tables['stratagems'].update(stratagem_record['id'], {
                'Status': 'failed',
                'Notes': stratagem_fields.get('Notes', '') + f"\n[ERROR] Insufficient funds: {sender_ducats} < {amount}"
            })
            return False
        
        # Perform the transfer
        new_sender_balance = sender_ducats - amount
        new_receiver_balance = receiver_ducats + amount
        
        # Update sender balance
        tables['citizens'].update(sender_record['id'], {'Ducats': new_sender_balance})
        log.info(f"{LogColors.OKGREEN}Updated {executed_by} balance: {sender_ducats} -> {new_sender_balance}{LogColors.ENDC}")
        
        # Update receiver balance
        tables['citizens'].update(receiver_record['id'], {'Ducats': new_receiver_balance})
        log.info(f"{LogColors.OKGREEN}Updated {target_citizen} balance: {receiver_ducats} -> {new_receiver_balance}{LogColors.ENDC}")
        
        # Create transaction records if the table exists
        if 'transactions' in tables:
            try:
                # Transaction for sender (outgoing)
                sender_transaction = {
                    'Username': executed_by,
                    'Type': 'stratagem_transfer',
                    'Amount': -amount,  # Negative for outgoing
                    'BalanceBefore': sender_ducats,
                    'BalanceAfter': new_sender_balance,
                    'Description': f"Transfer to {target_citizen}: {reason}",
                    'Timestamp': now_utc_dt.isoformat(),
                    'RelatedStratagem': stratagem_id
                }
                tables['transactions'].create(sender_transaction)
                
                # Transaction for receiver (incoming)
                receiver_transaction = {
                    'Username': target_citizen,
                    'Type': 'stratagem_transfer',
                    'Amount': amount,  # Positive for incoming
                    'BalanceBefore': receiver_ducats,
                    'BalanceAfter': new_receiver_balance,
                    'Description': f"Transfer from {executed_by}: {reason}",
                    'Timestamp': now_utc_dt.isoformat(),
                    'RelatedStratagem': stratagem_id
                }
                tables['transactions'].create(receiver_transaction)
                
                log.info(f"{LogColors.OKGREEN}Created transaction records for both parties.{LogColors.ENDC}")
            except Exception as e:
                log.warning(f"{LogColors.WARNING}Failed to create transaction records: {e}{LogColors.ENDC}")
                # Continue anyway, the transfer itself succeeded
        
        # Update stratagem status
        update_notes = stratagem_fields.get('Notes', '')
        success_note = f"\n[{now_venice_dt.strftime('%Y-%m-%d %H:%M')}] Successfully transferred {amount} ducats from {executed_by} to {target_citizen}."
        
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'executed',
            'ExecutedAt': now_utc_dt.isoformat(),
            'Notes': update_notes + success_note
        })
        
        log.info(f"{LogColors.OKGREEN}Stratagem {stratagem_id} executed successfully. Transferred {amount} ducats.{LogColors.ENDC}")
        
        # Create notifications if the table exists
        if 'notifications' in tables:
            try:
                # Notify sender
                sender_notification = {
                    'CitizenUsername': executed_by,
                    'Type': 'stratagem_complete',
                    'Title': 'Transfer Complete',
                    'Message': f"You have successfully transferred {amount} ducats to {target_citizen}. Reason: {reason}",
                    'Timestamp': now_utc_dt.isoformat(),
                    'RelatedEntity': stratagem_id,
                    'Read': False
                }
                tables['notifications'].create(sender_notification)
                
                # Notify receiver
                receiver_notification = {
                    'CitizenUsername': target_citizen,
                    'Type': 'payment_received',
                    'Title': 'Payment Received',
                    'Message': f"You have received {amount} ducats from {executed_by}. Reason: {reason}",
                    'Timestamp': now_utc_dt.isoformat(),
                    'RelatedEntity': stratagem_id,
                    'Read': False
                }
                tables['notifications'].create(receiver_notification)
                
                log.info(f"{LogColors.OKGREEN}Created notifications for both parties.{LogColors.ENDC}")
            except Exception as e:
                log.warning(f"{LogColors.WARNING}Failed to create notifications: {e}{LogColors.ENDC}")
                # Continue anyway, the transfer itself succeeded
        
        return True
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error processing transfer_ducats stratagem: {e}{LogColors.ENDC}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': stratagem_fields.get('Notes', '') + f"\n[ERROR] Processing error: {str(e)}"
        })
        return False
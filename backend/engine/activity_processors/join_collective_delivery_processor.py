"""
Processor for 'join_collective_delivery' activities.
Adds the citizen as a participant to the collective delivery stratagem.
"""
import json
import logging
from datetime import datetime
import pytz
from typing import Dict, Any

from backend.engine.utils.activity_helpers import LogColors

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    transport_api_url: str,
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any]
) -> bool:
    """
    Process a join_collective_delivery activity.
    
    This adds the citizen to the stratagem's participant list and prepares
    them to contribute to the collective delivery.
    
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    try:
        activity_id = activity_record.get('id')
        fields = activity_record.get('fields', {})
        citizen_username = fields.get('Citizen')
        notes = json.loads(fields.get('Notes', '{}'))
        
        stratagem_id = notes.get('stratagem_id')
        trust_score = notes.get('trust_score', 0)
        join_reason = notes.get('join_reason', 'unknown')
        
        if not stratagem_id:
            log.error(f"[Join Collective] No stratagem_id in activity notes")
            return False
        
        # Get the stratagem record
        formula = f"{{StratagemId}}='{stratagem_id}'"
        stratagems = tables['stratagems'].all(formula=formula, max_records=1)
        
        if not stratagems:
            log.error(f"[Join Collective] Stratagem {stratagem_id} not found")
            return False
        
        stratagem = stratagems[0]
        stratagem_fields = stratagem['fields']
        
        # Check if stratagem is still active
        if stratagem_fields.get('Status') != 'active':
            log.warning(f"[Join Collective] Stratagem {stratagem_id} is no longer active")
            return True  # Mark as processed anyway
        
        # Parse stratagem details
        stratagem_notes = json.loads(stratagem_fields.get('Notes', '{}'))
        participants = stratagem_notes.get('participants', [])
        
        # Check if citizen is already a participant
        existing_participant = next((p for p in participants if p['username'] == citizen_username), None)
        
        if not existing_participant:
            # Add new participant
            new_participant = {
                'username': citizen_username,
                'amount_delivered': 0,
                'deliveries': 0,
                'reward_earned': 0,
                'joined_at': datetime.now(pytz.utc).isoformat(),
                'join_reason': join_reason,
                'trust_score': trust_score
            }
            participants.append(new_participant)
            
            # Update stratagem with new participant
            stratagem_notes['participants'] = participants
            updated_notes = json.dumps(stratagem_notes)
            
            tables['stratagems'].update(
                stratagem['id'],
                {'Notes': updated_notes}
            )
            
            log.info(f"{LogColors.OKGREEN}[Join Collective] {citizen_username} joined {stratagem_id} "
                    f"(trust: {trust_score:.0f}, reason: {join_reason}){LogColors.ENDC}")
        else:
            log.info(f"[Join Collective] {citizen_username} already a participant in {stratagem_id}")
        
        # Mark activity as processed
        tables['activities'].update(
            activity_id,
            {
                'Status': 'processed',
                'ProcessedAt': datetime.now(pytz.utc).isoformat()
            }
        )
        
        # Log the trust-based joining
        organizer = stratagem_fields.get('ExecutedBy')
        log.info(f"{LogColors.HEADER}=== Trust-Based Collective Joining ==={LogColors.ENDC}")
        log.info(f"{LogColors.OKBLUE}Citizen: {citizen_username} joined {organizer}'s delivery{LogColors.ENDC}")
        log.info(f"{LogColors.OKBLUE}Trust Score: {trust_score:.0f} | Reason: {join_reason}{LogColors.ENDC}")
        log.info(f"{LogColors.OKGREEN}Natural cooperation through social bonds!{LogColors.ENDC}")
        
        return True
        
    except Exception as e:
        log.error(f"[Join Collective] Error processing activity: {e}", exc_info=True)
        return False
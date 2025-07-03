#!/usr/bin/env python3
"""
Reputation Boost Stratagem Processor

Processes reputation boost stratagems to improve a citizen's public image.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pyairtable import Table
import random

log = logging.getLogger(__name__)

def process_reputation_boost_stratagem(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    api_base_url: str
) -> bool:
    """
    Process a reputation_boost stratagem.
    
    Runs a campaign to improve a citizen's reputation through various activities.
    """
    
    fields = stratagem_record['fields']
    stratagem_id = fields.get('StratagemId')
    executed_by = fields.get('ExecutedBy')
    target_citizen = fields.get('TargetCitizen')
    variant = fields.get('Variant', 'Standard')  # Campaign intensity
    status = fields.get('Status')
    
    # Extract parameters from notes
    notes_str = fields.get('Notes', '{}')
    try:
        notes_data = json.loads(notes_str) if notes_str else {}
    except:
        notes_data = {}
    
    daily_budget = notes_data.get('daily_budget', 20)
    total_spent = notes_data.get('total_spent', 0)
    reputation_events = notes_data.get('reputation_events', 0)
    last_event_date = notes_data.get('last_event_date')
    
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
        
        # Check if we've already run an event today
        if last_event_date == today_date:
            log.info(f"Already ran reputation event for stratagem {stratagem_id} today")
            return True
        
        # Get sponsor's current funds
        sponsor_record = _get_citizen_record(tables, executed_by)
        if not sponsor_record:
            log.error(f"Sponsor {executed_by} not found")
            return False
        
        sponsor_ducats = float(sponsor_record['fields'].get('Ducats', 0))
        
        # Check if sponsor has sufficient funds
        if sponsor_ducats < daily_budget:
            log.warning(f"Sponsor {executed_by} has insufficient funds ({sponsor_ducats} < {daily_budget})")
            
            # Suspend campaign
            tables['stratagems'].update(stratagem_record['id'], {
                'Status': 'suspended',
                'Notes': json.dumps({
                    **notes_data,
                    'suspended_at': now_utc.isoformat(),
                    'suspension_reason': 'Insufficient funds'
                })
            })
            
            _create_notification(
                tables,
                executed_by,
                'campaign_suspended',
                f"❌ Reputation campaign for {target_citizen} suspended due to insufficient funds."
            )
            
            return False
        
        # Execute daily reputation event
        event_type = _choose_reputation_event(variant)
        event_success = _execute_reputation_event(
            tables, target_citizen, event_type, variant, stratagem_id
        )
        
        if event_success:
            # Deduct budget from sponsor
            tables['citizens'].update(sponsor_record['id'], {
                'Ducats': sponsor_ducats - daily_budget
            })
            
            # Improve relationships with random citizens
            _improve_public_perception(tables, target_citizen, variant)
            
            # Update notes
            notes_data['last_event_date'] = today_date
            notes_data['total_spent'] = total_spent + daily_budget
            notes_data['reputation_events'] = reputation_events + 1
            notes_data['last_event_type'] = event_type
            notes_data['last_event_time'] = now_utc.isoformat()
            
            # Mark ExecutedAt on first event
            update_data = {'Notes': json.dumps(notes_data)}
            if not fields.get('ExecutedAt'):
                update_data['ExecutedAt'] = now_utc.isoformat()
            
            tables['stratagems'].update(stratagem_record['id'], update_data)
            
            log.info(f"Successfully executed {event_type} event for {target_citizen}'s reputation")
        
        # Check if stratagem should expire
        expires_at_str = fields.get('ExpiresAt')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                import pytz
                expires_at = pytz.UTC.localize(expires_at)
            
            if expires_at <= now_utc:
                # Campaign has ended
                _finalize_campaign(
                    tables, stratagem_record, executed_by, target_citizen, notes_data
                )
        
        return True
        
    except Exception as e:
        log.error(f"Error processing reputation_boost stratagem {stratagem_id}: {e}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': str(e)})
        })
        return False

def _choose_reputation_event(intensity: str) -> str:
    """Choose a reputation event based on campaign intensity."""
    events_by_intensity = {
        'Modest': [
            'public_compliment',
            'small_donation',
            'local_endorsement'
        ],
        'Standard': [
            'public_speech',
            'charity_event',
            'business_endorsement',
            'cultural_sponsorship'
        ],
        'Intense': [
            'grand_feast',
            'major_donation',
            'political_endorsement',
            'public_monument',
            'theatrical_production'
        ]
    }
    
    events = events_by_intensity.get(intensity, events_by_intensity['Standard'])
    return random.choice(events)

def _execute_reputation_event(
    tables: Dict[str, Table],
    target_citizen: str,
    event_type: str,
    intensity: str,
    stratagem_id: str
) -> bool:
    """Execute a specific reputation-building event."""
    try:
        # Create notifications about the event
        event_descriptions = {
            'public_compliment': f"praised {target_citizen}'s contributions to Venice in the market square",
            'small_donation': f"made a donation in {target_citizen}'s name to local artisans",
            'local_endorsement': f"spoke favorably of {target_citizen} at a neighborhood gathering",
            'public_speech': f"delivered a speech honoring {target_citizen}'s achievements at the Rialto",
            'charity_event': f"organized a charity feast crediting {target_citizen} as inspiration",
            'business_endorsement': f"publicly endorsed {target_citizen}'s business acumen to merchants",
            'cultural_sponsorship': f"sponsored an art exhibition in {target_citizen}'s honor",
            'grand_feast': f"hosted a grand feast celebrating {target_citizen}'s contributions to Venice",
            'major_donation': f"funded a new public fountain dedicated to {target_citizen}",
            'political_endorsement': f"secured endorsements from influential patricians for {target_citizen}",
            'public_monument': f"commissioned a statue honoring {target_citizen}'s legacy",
            'theatrical_production': f"produced a play depicting {target_citizen} as a Venetian hero"
        }
        
        event_desc = event_descriptions.get(event_type, f"organized an event honoring {target_citizen}")
        
        # Notify target citizen
        _create_notification(
            tables,
            target_citizen,
            'reputation_boost',
            f"🌟 Your reputation improves! Someone {event_desc}."
        )
        
        # Notify some random citizens (spread the word)
        try:
            all_citizens = tables['citizens'].all(max_records=100)
            witnesses = random.sample(all_citizens, min(5, len(all_citizens)))
            
            for witness in witnesses:
                witness_username = witness['fields'].get('Username')
                if witness_username and witness_username not in [target_citizen]:
                    _create_notification(
                        tables,
                        witness_username,
                        'reputation_event_witnessed',
                        f"📢 You witnessed someone {event_desc}. The city takes note!"
                    )
        except:
            pass  # Don't fail if we can't notify witnesses
        
        # Remove or reduce severity of reputation problems
        _improve_reputation_problems(tables, target_citizen, intensity)
        
        return True
        
    except Exception as e:
        log.error(f"Error executing reputation event: {e}")
        return False

def _improve_public_perception(
    tables: Dict[str, Table],
    target_citizen: str,
    intensity: str
) -> None:
    """Improve relationships with random citizens."""
    try:
        # Trust boost based on intensity
        trust_boosts = {
            'Modest': 2,
            'Standard': 4,
            'Intense': 6
        }
        trust_boost = trust_boosts.get(intensity, 4)
        
        # Get random citizens
        all_citizens = tables['citizens'].all(max_records=50)
        affected_citizens = random.sample(all_citizens, min(10, len(all_citizens)))
        
        for citizen in affected_citizens:
            other_username = citizen['fields'].get('Username')
            if other_username and other_username != target_citizen:
                _update_relationships(tables, target_citizen, other_username, trust_boost)
    
    except Exception as e:
        log.error(f"Error improving public perception: {e}")

def _improve_reputation_problems(
    tables: Dict[str, Table],
    target_citizen: str,
    intensity: str
) -> None:
    """Reduce or resolve reputation-related problems."""
    try:
        # Find reputation problems
        problem_types = ['bad_reputation', 'trust_deficit', 'social_scandal', 'business_scandal']
        
        for problem_type in problem_types:
            formula = f"AND({{Citizen}}='{target_citizen}', {{Type}}='{problem_type}', {{Status}}='active')"
            problems = tables['problems'].all(formula=formula)
            
            for problem in problems:
                # Chance to resolve based on intensity
                resolution_chances = {
                    'Modest': 0.3,
                    'Standard': 0.5,
                    'Intense': 0.7
                }
                
                if random.random() < resolution_chances.get(intensity, 0.5):
                    # Resolve or reduce severity
                    severity = problem['fields'].get('Severity', 'Medium')
                    
                    if severity == 'Low' or intensity == 'Intense':
                        # Resolve completely
                        tables['problems'].update(problem['id'], {
                            'Status': 'resolved',
                            'ResolvedAt': datetime.now(timezone.utc).isoformat(),
                            'Solutions': json.dumps({
                                'resolution': 'Resolved through reputation campaign',
                                'campaign_intensity': intensity
                            })
                        })
                    else:
                        # Reduce severity
                        new_severity = 'Low' if severity == 'Medium' else 'Medium'
                        tables['problems'].update(problem['id'], {
                            'Severity': new_severity,
                            'Notes': json.dumps({
                                'severity_reduced_by': 'reputation_campaign',
                                'reduced_at': datetime.now(timezone.utc).isoformat()
                            })
                        })
    
    except Exception as e:
        log.error(f"Error improving reputation problems: {e}")

def _finalize_campaign(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    sponsor: str,
    target_citizen: str,
    notes_data: Dict[str, Any]
) -> None:
    """Finalize the reputation campaign."""
    try:
        total_spent = notes_data.get('total_spent', 0)
        events_held = notes_data.get('reputation_events', 0)
        
        # Calculate final reputation boost based on campaign success
        final_trust_boost = min(15, events_held * 2)  # Cap at 15
        
        # Apply final boost to many relationships
        all_citizens = tables['citizens'].all(max_records=30)
        for citizen in all_citizens:
            other_username = citizen['fields'].get('Username')
            if other_username and other_username != target_citizen:
                _update_relationships(tables, target_citizen, other_username, final_trust_boost)
        
        # Update stratagem status
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'completed',
            'Notes': json.dumps({
                **notes_data,
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'final_trust_boost': final_trust_boost,
                'completion_reason': 'Campaign duration ended'
            })
        })
        
        # Send completion notifications
        _create_notification(
            tables,
            sponsor,
            'campaign_completed',
            f"✅ Your reputation campaign for {target_citizen} has concluded. "
            f"Total spent: {total_spent} ducats over {events_held} events."
        )
        
        _create_notification(
            tables,
            target_citizen,
            'reputation_improved',
            f"🎭 The reputation campaign in your honor has concluded. "
            f"Your standing in Venice has significantly improved!"
        )
        
        # Boost sponsor-target relationship
        _update_relationships(tables, sponsor, target_citizen, 10)
        
    except Exception as e:
        log.error(f"Error finalizing campaign: {e}")

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
                'Type': 'public_acquaintance',
                'TrustScore': 50 + trust_change,
                'InteractionCount': 1,
                'LastInteraction': datetime.now(timezone.utc).isoformat()
            }
            tables['relationships'].create(relationship_data)
            
    except Exception as e:
        log.error(f"Error updating relationships: {e}")
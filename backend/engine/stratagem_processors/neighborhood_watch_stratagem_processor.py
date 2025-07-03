#!/usr/bin/env python3
"""
Neighborhood Watch Stratagem Processor

Processes neighborhood watch stratagems to enhance district security.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pyairtable import Table
import pytz
import random

log = logging.getLogger(__name__)

def process_neighborhood_watch_stratagem(
    tables: Dict[str, Table],
    stratagem_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    api_base_url: str
) -> bool:
    """
    Process a neighborhood_watch stratagem.
    
    Enhances security in a district through citizen vigilance.
    """
    
    fields = stratagem_record['fields']
    stratagem_id = fields.get('StratagemId')
    executed_by = fields.get('ExecutedBy')
    district_name = fields.get('TargetBuilding')  # District stored in TargetBuilding
    status = fields.get('Status')
    
    # Extract parameters from notes
    notes_str = fields.get('Notes', '{}')
    try:
        notes_data = json.loads(notes_str) if notes_str else {}
    except:
        notes_data = {}
    
    district_name = notes_data.get('district_name', district_name)
    
    # Validation
    if not all([executed_by, district_name]):
        log.error(f"Stratagem {stratagem_id} missing required fields")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': 'Missing required fields'})
        })
        return False
    
    try:
        now_utc = datetime.now(timezone.utc)
        
        # Check if this is the first execution
        if not fields.get('ExecutedAt'):
            # First execution - set up the watch
            
            # Find all citizens in the district
            participants = _find_district_citizens(tables, district_name)
            
            # Find all buildings in the district
            district_buildings = _find_district_buildings(tables, district_name)
            
            # Create initial notifications
            _create_establishment_notifications(tables, executed_by, district_name, participants)
            
            # Update notes with initial data
            notes_data['participants'] = len(participants)
            notes_data['participating_citizens'] = [p['fields'].get('Username') for p in participants[:10]]  # Store first 10
            notes_data['protected_buildings'] = len(district_buildings)
            notes_data['crimes_prevented'] = 0
            notes_data['last_patrol'] = now_utc.isoformat()
            
            # Mark as executed
            tables['stratagems'].update(stratagem_record['id'], {
                'ExecutedAt': now_utc.isoformat(),
                'Notes': json.dumps(notes_data)
            })
            
            # Update relationships among participants
            _boost_community_relationships(tables, participants[:20])  # Limit to avoid too many updates
            
            log.info(f"Established neighborhood watch in {district_name} with {len(participants)} participants")
            
        else:
            # Ongoing execution - maintain the watch
            
            # Check and prevent crimes
            crimes_prevented = _prevent_district_crimes(tables, district_name, stratagem_id)
            
            # Update crime prevention count
            total_prevented = notes_data.get('crimes_prevented', 0) + crimes_prevented
            notes_data['crimes_prevented'] = total_prevented
            notes_data['last_patrol'] = now_utc.isoformat()
            
            # Periodic community notification (once per week)
            last_notification = notes_data.get('last_community_notification')
            if not last_notification or _days_since(last_notification) >= 7:
                if total_prevented > 0:
                    _create_progress_notifications(tables, district_name, total_prevented)
                notes_data['last_community_notification'] = now_utc.isoformat()
            
            # Update notes
            tables['stratagems'].update(stratagem_record['id'], {
                'Notes': json.dumps(notes_data)
            })
            
            if crimes_prevented > 0:
                log.info(f"Neighborhood watch in {district_name} prevented {crimes_prevented} crimes")
        
        # Check if stratagem should expire
        expires_at_str = fields.get('ExpiresAt')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                expires_at = pytz.UTC.localize(expires_at)
            
            if expires_at <= now_utc:
                # Stratagem has expired
                _create_completion_notifications(
                    tables, executed_by, district_name, 
                    notes_data.get('crimes_prevented', 0)
                )
                
                tables['stratagems'].update(stratagem_record['id'], {
                    'Status': 'completed',
                    'Notes': json.dumps({
                        **notes_data,
                        'completed_at': now_utc.isoformat(),
                        'completion_reason': 'Duration expired'
                    })
                })
        
        return True
        
    except Exception as e:
        log.error(f"Error processing neighborhood_watch stratagem {stratagem_id}: {e}")
        tables['stratagems'].update(stratagem_record['id'], {
            'Status': 'failed',
            'Notes': json.dumps({**notes_data, 'error': str(e)})
        })
        return False

def _find_district_citizens(tables: Dict[str, Table], district_name: str) -> List[Dict]:
    """Find all citizens who live in or own property in the district."""
    citizens = []
    
    try:
        # Citizens who live in the district
        residence_formula = f"{{DistrictResidence}}='{district_name}'"
        residents = tables['citizens'].all(formula=residence_formula)
        citizens.extend(residents)
        
        # Citizens who own buildings in the district
        building_formula = f"{{DistrictLocation}}='{district_name}'"
        district_buildings = tables['buildings'].all(formula=building_formula)
        
        owner_usernames = set()
        for building in district_buildings:
            owner = building['fields'].get('Owner')
            if owner and owner not in owner_usernames:
                owner_usernames.add(owner)
        
        # Get citizen records for owners
        for owner in owner_usernames:
            owner_formula = f"{{Username}}='{owner}'"
            owner_records = tables['citizens'].all(formula=owner_formula, max_records=1)
            if owner_records:
                # Avoid duplicates
                if not any(c['fields'].get('Username') == owner for c in citizens):
                    citizens.extend(owner_records)
        
    except Exception as e:
        log.error(f"Error finding district citizens: {e}")
    
    return citizens

def _find_district_buildings(tables: Dict[str, Table], district_name: str) -> List[Dict]:
    """Find all buildings in the district."""
    try:
        formula = f"{{DistrictLocation}}='{district_name}'"
        return tables['buildings'].all(formula=formula)
    except Exception as e:
        log.error(f"Error finding district buildings: {e}")
        return []

def _prevent_district_crimes(
    tables: Dict[str, Table], 
    district_name: str,
    stratagem_id: str
) -> int:
    """Check for and prevent crimes in the district."""
    crimes_prevented = 0
    
    try:
        # Find active crime-related problems in the district
        problem_types = ['theft', 'sabotage', 'criminal_activity', 'vandalism']
        
        for problem_type in problem_types:
            formula = f"AND({{Type}}='{problem_type}', {{Status}}='active')"
            problems = tables['problems'].all(formula=formula)
            
            for problem in problems:
                # Check if problem is in this district
                asset = problem['fields'].get('Asset')
                asset_type = problem['fields'].get('AssetType')
                
                in_district = False
                
                if asset_type == 'building':
                    # Check if building is in district
                    building_formula = f"AND({{BuildingId}}='{asset}', {{DistrictLocation}}='{district_name}')"
                    buildings = tables['buildings'].all(formula=building_formula, max_records=1)
                    if buildings:
                        in_district = True
                
                elif asset_type == 'citizen':
                    # Check if citizen is in district
                    citizen_formula = f"AND({{Username}}='{asset}', {{DistrictResidence}}='{district_name}')"
                    citizens = tables['citizens'].all(formula=citizen_formula, max_records=1)
                    if citizens:
                        in_district = True
                
                if in_district:
                    # Neighborhood watch has chance to prevent/resolve the crime
                    prevention_chance = 0.7  # 70% chance to prevent
                    
                    if random.random() < prevention_chance:
                        # Prevent the crime
                        tables['problems'].update(problem['id'], {
                            'Status': 'resolved',
                            'ResolvedAt': datetime.now(timezone.utc).isoformat(),
                            'Solutions': json.dumps({
                                'resolution': 'Prevented by neighborhood watch',
                                'stratagem_id': stratagem_id
                            })
                        })
                        crimes_prevented += 1
                        
                        # Notify affected citizen
                        affected_citizen = problem['fields'].get('Citizen')
                        if affected_citizen:
                            _create_notification(
                                tables,
                                affected_citizen,
                                'crime_prevented',
                                f"🛡️ The neighborhood watch prevented a {problem_type} incident affecting you in {district_name}!"
                            )
        
    except Exception as e:
        log.error(f"Error preventing district crimes: {e}")
    
    return crimes_prevented

def _boost_community_relationships(
    tables: Dict[str, Table],
    participants: List[Dict]
) -> None:
    """Boost trust between citizens participating in the watch."""
    try:
        # Create pairs of participants to boost relationships
        for i in range(min(len(participants) - 1, 10)):  # Limit updates
            citizen1 = participants[i]['fields'].get('Username')
            citizen2 = participants[i + 1]['fields'].get('Username')
            
            if citizen1 and citizen2:
                _update_relationships(tables, citizen1, citizen2, 3)  # Small trust boost
    
    except Exception as e:
        log.error(f"Error boosting community relationships: {e}")

def _create_establishment_notifications(
    tables: Dict[str, Table],
    organizer: str,
    district_name: str,
    participants: List[Dict]
) -> None:
    """Create notifications about the establishment of the watch."""
    try:
        # Notification for organizer
        _create_notification(
            tables,
            organizer,
            'watch_established',
            f"🏛️ You have successfully established a neighborhood watch in {district_name}. {len(participants)} citizens are participating."
        )
        
        # Notifications for participants (limit to avoid spam)
        for participant in participants[:20]:
            username = participant['fields'].get('Username')
            if username and username != organizer:
                _create_notification(
                    tables,
                    username,
                    'watch_participation',
                    f"👁️ A neighborhood watch has been established in {district_name} by {organizer}. Your participation helps keep the community safe!"
                )
    
    except Exception as e:
        log.error(f"Error creating establishment notifications: {e}")

def _create_progress_notifications(
    tables: Dict[str, Table],
    district_name: str,
    crimes_prevented: int
) -> None:
    """Create periodic progress notifications."""
    try:
        # Find a few citizens in the district to notify
        formula = f"{{DistrictResidence}}='{district_name}'"
        citizens = tables['citizens'].all(formula=formula, max_records=10)
        
        for citizen in citizens:
            username = citizen['fields'].get('Username')
            if username:
                _create_notification(
                    tables,
                    username,
                    'watch_progress',
                    f"📊 The neighborhood watch in {district_name} has prevented {crimes_prevented} criminal incidents so far. Your vigilance is making a difference!"
                )
    
    except Exception as e:
        log.error(f"Error creating progress notifications: {e}")

def _create_completion_notifications(
    tables: Dict[str, Table],
    organizer: str,
    district_name: str,
    total_crimes_prevented: int
) -> None:
    """Create notifications when the watch expires."""
    try:
        _create_notification(
            tables,
            organizer,
            'watch_completed',
            f"✅ The neighborhood watch in {district_name} has concluded after 45 days. Total crimes prevented: {total_crimes_prevented}. Thank you for your community service!"
        )
    
    except Exception as e:
        log.error(f"Error creating completion notifications: {e}")

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
                'Type': 'community_member',
                'TrustScore': 50 + trust_change,
                'InteractionCount': 1,
                'LastInteraction': datetime.now(timezone.utc).isoformat()
            }
            tables['relationships'].create(relationship_data)
            
    except Exception as e:
        log.error(f"Error updating relationships: {e}")

def _days_since(iso_date_str: str) -> float:
    """Calculate days since a given date."""
    try:
        past_date = datetime.fromisoformat(iso_date_str.replace('Z', '+00:00'))
        if past_date.tzinfo is None:
            past_date = past_date.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - past_date).total_seconds() / 86400
    except:
        return float('inf')  # If parsing fails, assume it's been a long time
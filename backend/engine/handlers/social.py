# backend/engine/handlers/social.py

"""
Contains activity handlers related to social interactions,
including messaging, relationship building, and social activities.
"""

import logging
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from pyairtable import Table

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers from the central utils module
from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    _calculate_distance_meters,
    get_relationship_trust_score,
    is_leisure_time_for_class,
    clean_thought_content,
    VENICE_TIMEZONE
)

# Import specific activity creators
from backend.engine.activity_creators import try_create_send_message_activity as try_create_send_message_chain
from backend.engine.activity_creators.spread_rumor_activity_creator import try_create as try_create_spread_rumor_activity

log = logging.getLogger(__name__)


# ==============================================================================
# SOCIAL INTERACTION HANDLERS
# ==============================================================================

def _handle_send_message(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str, check_only: bool = False
) -> Optional[Dict]:
    """
    Handles sending messages to other citizens based on relationships and recent thoughts.
    Can be called during leisure time or as a social activity.
    """
    if check_only:
        # Quick check if this activity is viable
        if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
            return {'viable': False, 'reason': 'Not leisure time'}
        
        # Check if citizen has relationships
        try:
            formula = f"OR({{SourceCitizen}}='{_escape_airtable_value(citizen_username)}', {{TargetCitizen}}='{_escape_airtable_value(citizen_username)}')"
            relationships = tables['relationships'].all(formula=formula, max_records=1)
            if not relationships:
                return {'viable': False, 'reason': 'No relationships'}
        except Exception:
            return {'viable': False, 'reason': 'Error checking relationships'}
        
        return {'viable': True, 'reason': 'Can send message'}
    
    # Actual implementation
    log.info(f"{LogColors.OKCYAN}[Social-Message] {citizen_name}: Evaluating message sending opportunity.{LogColors.ENDC}")
    
    # Get recent thoughts to use as message content
    recent_thoughts = _get_recent_thoughts(tables, citizen_username, hours=24)
    if not recent_thoughts:
        log.info(f"{LogColors.WARNING}[Social-Message] {citizen_name}: No recent thoughts to share.{LogColors.ENDC}")
        return None
    
    # Get relationships with positive trust
    relationships = _get_positive_relationships(tables, citizen_username)
    if not relationships:
        log.info(f"{LogColors.WARNING}[Social-Message] {citizen_name}: No positive relationships for messaging.{LogColors.ENDC}")
        return None
    
    # Create message chain activity
    activity_chain = try_create_send_message_chain(
        tables=tables,
        citizen_id=citizen_custom_id,
        citizen_username=citizen_username,
        citizen_airtable_id=citizen_airtable_id,
        now_utc_dt=now_utc_dt,
        relationships=relationships,
        recent_thoughts=recent_thoughts
    )
    
    if activity_chain:
        log.info(f"{LogColors.OKGREEN}[Social-Message] {citizen_name}: Created send message activity chain.{LogColors.ENDC}")
        return activity_chain
    
    return None

def _handle_spread_rumor(
    tables: Dict[str, Table], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str, check_only: bool = False
) -> Optional[Dict]:
    """
    Handles spreading rumors in public spaces during leisure time.
    Requires being in a social location like an inn or market.
    """
    if check_only:
        # Quick viability check
        if not is_leisure_time_for_class(citizen_social_class, now_venice_dt):
            return {'viable': False, 'reason': 'Not leisure time'}
        
        # Check if at social location
        if not citizen_position:
            return {'viable': False, 'reason': 'No position'}
        
        # Would need to check if near inn/market/etc
        return {'viable': True, 'reason': 'Can spread rumor'}
    
    # Actual implementation
    log.info(f"{LogColors.OKCYAN}[Social-Rumor] {citizen_name}: Evaluating rumor spreading opportunity.{LogColors.ENDC}")
    
    # Check if at a social location (inn, market, etc.)
    social_building = _get_current_social_building(tables, citizen_position)
    if not social_building:
        log.info(f"{LogColors.WARNING}[Social-Rumor] {citizen_name}: Not at a social location.{LogColors.ENDC}")
        return None
    
    # Get interesting information to spread
    rumor_content = _generate_rumor_content(tables, citizen_username, citizen_social_class)
    if not rumor_content:
        log.info(f"{LogColors.WARNING}[Social-Rumor] {citizen_name}: No interesting rumors to spread.{LogColors.ENDC}")
        return None
    
    # Create spread rumor activity
    activity = try_create_spread_rumor_activity(
        tables=tables,
        citizen_id=citizen_custom_id,
        citizen_username=citizen_username,
        citizen_airtable_id=citizen_airtable_id,
        location_building_id=social_building['fields']['BuildingId'],
        rumor_content=rumor_content,
        now_utc_dt=now_utc_dt
    )
    
    if activity:
        log.info(f"{LogColors.OKGREEN}[Social-Rumor] {citizen_name}: Created spread rumor activity.{LogColors.ENDC}")
        return activity
    
    return None

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _get_recent_thoughts(tables: Dict[str, Table], citizen_username: str, hours: int = 24) -> List[str]:
    """Get recent thought messages from the citizen."""
    try:
        cutoff_time = datetime.now(VENICE_TIMEZONE) - timedelta(hours=hours)
        formula = f"AND({{Sender}}='{_escape_airtable_value(citizen_username)}', {{Type}}='thought_log', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'hours') < {hours})"
        
        thoughts = tables['messages'].all(formula=formula, sort=['CreatedAt'])
        return [clean_thought_content(t['fields'].get('Content', '')) for t in thoughts if t['fields'].get('Content')]
    except Exception as e:
        log.error(f"Error getting recent thoughts: {e}")
        return []

def _get_positive_relationships(tables: Dict[str, Table], citizen_username: str, min_trust: float = 0.5) -> List[Dict]:
    """Get relationships with positive trust scores."""
    try:
        formula = f"OR({{SourceCitizen}}='{_escape_airtable_value(citizen_username)}', {{TargetCitizen}}='{_escape_airtable_value(citizen_username)}')"
        all_relationships = tables['relationships'].all(formula=formula)
        
        positive_relationships = []
        for rel in all_relationships:
            fields = rel['fields']
            trust_score = get_relationship_trust_score(fields)
            
            if trust_score >= min_trust:
                # Determine the other citizen
                other_citizen = fields.get('TargetCitizen') if fields.get('SourceCitizen') == citizen_username else fields.get('SourceCitizen')
                if other_citizen:
                    positive_relationships.append({
                        'relationship': rel,
                        'other_citizen': other_citizen,
                        'trust_score': trust_score
                    })
        
        # Sort by trust score (highest first)
        positive_relationships.sort(key=lambda x: x['trust_score'], reverse=True)
        return positive_relationships
    
    except Exception as e:
        log.error(f"Error getting positive relationships: {e}")
        return []

def _get_current_social_building(tables: Dict[str, Table], citizen_position: Dict[str, float]) -> Optional[Dict]:
    """Check if citizen is at a social building (inn, market, etc.)."""
    if not citizen_position:
        return None
    
    try:
        # Get all buildings
        all_buildings = tables['buildings'].all()
        
        # Social building types
        social_types = ['inn', 'market_stall', 'vegetable_market', 'merceria']
        
        for building in all_buildings:
            fields = building['fields']
            if fields.get('Type') not in social_types:
                continue
            
            # Check distance
            building_pos = json.loads(fields.get('Position', '{}'))
            if building_pos:
                distance = _calculate_distance_meters(citizen_position, building_pos)
                if distance < const.SOCIAL_INTERACTION_RADIUS:  # e.g., 20 meters
                    return building
        
        return None
    
    except Exception as e:
        log.error(f"Error checking social building: {e}")
        return None

def _generate_rumor_content(tables: Dict[str, Table], citizen_username: str, social_class: str) -> Optional[str]:
    """Generate interesting rumor content based on recent events and observations."""
    rumor_topics = []
    
    try:
        # Recent market prices
        # Recent building constructions
        # Political events
        # Social scandals
        # Economic trends
        
        # For now, return a simple rumor
        # In full implementation, this would analyze recent activities and generate contextual rumors
        
        rumor_templates = [
            "I heard the price of {resource} has gone up again at the {market}.",
            "Did you know {citizen} just bought property in {district}?",
            "They say {guild} is planning something big.",
            "I saw {noble} at the {location} yesterday, very unusual.",
            "Word is that {business} is struggling to find workers."
        ]
        
        # This is a placeholder - actual implementation would fill in the templates
        # with real data from the simulation
        return random.choice(rumor_templates)
    
    except Exception as e:
        log.error(f"Error generating rumor content: {e}")
        return None
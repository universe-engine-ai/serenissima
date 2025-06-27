#!/usr/bin/env python3
"""
Research Scope Definition Activity Creator

This activity allows Scientisti to plan and define their research objectives.
They spend time at the House of Natural Sciences contemplating and documenting
their research goals using KinOS for introspection.
"""

import logging
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

from backend.engine.utils.activity_helpers import VENICE_TIMEZONE

log = logging.getLogger(__name__)

# Constants
SCOPE_DEFINITION_DURATION_MINUTES = 90  # 1.5 hours to plan research
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def _ask_citizen_research_scope(
    citizen_username: str,
    citizen_name: str,
    recent_observations: list,
    api_base_url: Optional[str] = None,
    kinos_model: str = 'local'
) -> Optional[str]:
    """
    Use KinOS to ask the citizen what research scope they want to define.
    
    Args:
        citizen_username: The citizen's username
        citizen_name: The citizen's full name
        recent_observations: List of recent research findings or observations
        api_base_url: Base URL for API calls
        
    Returns:
        The research scope definition or None if failed
    """
    if not KINOS_API_KEY:
        log.warning(f"KinOS API key not configured, using default scope for {citizen_username}")
        return "Defining the boundaries and objectives of computational reality research"
    
    try:
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Format recent observations
        obs_text = ""
        if recent_observations:
            obs_text = "\n\nYour recent research activities:\n" + "\n".join(f"- {obs}" for obs in recent_observations[:5])
        
        kinos_prompt = (
            f"You are {citizen_name}, a Scientisti planning your research direction. "
            f"You are at the House of Natural Sciences, contemplating the scope of your next investigation.{obs_text}\n\n"
            f"Consider:\n"
            f"1. What specific aspect of Venice's computational reality interests you most?\n"
            f"2. What boundaries will you set for this investigation?\n"
            f"3. What are your primary research objectives?\n"
            f"4. What methods will you employ?\n\n"
            f"Describe the research scope you want to define. Be specific about what you'll investigate and why."
        )
        
        payload = {
            "message": kinos_prompt,
            "model": kinos_model
        }
        
        response = requests.post(kinos_url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        research_scope = data.get('response', '')
        
        if research_scope:
            log.info(f"Received research scope from {citizen_username}: {research_scope[:100]}...")
            return research_scope
        else:
            log.warning(f"Empty response from KinOS for {citizen_username}")
            return None
            
    except Exception as e:
        log.error(f"Error getting research scope from KinOS for {citizen_username}: {e}")
        return None

def _get_recent_research_context(tables: Dict[str, Any], citizen_username: str) -> list:
    """Get recent research context from self-messages and activities"""
    recent_observations = []
    
    try:
        # Get recent research messages to self
        research_messages = list(tables['messages'].all(
            formula=f"AND({{Sender}}='{citizen_username}', {{Receiver}}='{citizen_username}', {{Channel}}='research_thoughts', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'days') < 3)",
            max_records=3,
            sort=['-CreatedAt']
        ))
        
        for message in research_messages:
            content = message['fields'].get('Content', '')
            if content:
                # Extract first meaningful line
                first_line = content.split('\n')[0].strip()
                if first_line:
                    recent_observations.append(first_line[:100])
        
        # Get recent completed research activities
        activities = list(tables['activities'].all(
            formula=f"AND({{Citizen}}='{citizen_username}', OR({{Type}}='research_investigation', {{Type}}='observe_phenomena'), {{Status}}='Completed', DATETIME_DIFF(NOW(), {{EndDate}}, 'days') < 3)",
            max_records=2,
            sort=['-EndDate']
        ))
        
        for activity in activities:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            if activity['fields'].get('Type') == 'research_investigation':
                query = notes.get('research_query', '')
                if query:
                    recent_observations.append(f"Investigated: {query[:80]}")
            elif activity['fields'].get('Type') == 'observe_phenomena':
                phenomena = notes.get('phenomena', '')
                site = notes.get('site_name', '')
                if phenomena:
                    recent_observations.append(f"Observed {phenomena} at {site}")
    
    except Exception as e:
        log.error(f"Error getting research context for {citizen_username}: {e}")
    
    return recent_observations

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Dict[str, float],
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: Optional[str] = None,
    kinos_model: str = 'local'
) -> Optional[Dict[str, Any]]:
    """
    Try to create a research scope definition activity for a Scientisti.
    
    Args:
        tables: Database tables
        citizen_record: The citizen's record
        citizen_position: Current position of the citizen
        now_utc_dt: Current UTC datetime
        transport_api_url: URL for transport API
        api_base_url: Base URL for API calls
        
    Returns:
        Created activity record or None if creation failed
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip()
    
    log.info(f"Attempting to create research_scope_definition activity for {citizen_username}")
    
    # Check if citizen is already busy
    existing_activities = list(tables['activities'].all(
        formula=f"AND({{Citizen}}='{citizen_username}', {{Status}}='Created')"
    ))
    
    if existing_activities:
        log.info(f"{citizen_username} already has pending activities")
        return None
    
    # Find the House of Natural Sciences
    house_of_sciences = None
    try:
        sciences_buildings = list(tables['buildings'].all(
            formula="{Type}='house_of_natural_sciences'"
        ))
        if sciences_buildings:
            house_of_sciences = sciences_buildings[0]
    except Exception as e:
        log.error(f"Error finding House of Natural Sciences: {e}")
    
    if not house_of_sciences:
        log.warning(f"No House of Natural Sciences found for {citizen_username}")
        return None
    
    # Get building position
    building_position_str = house_of_sciences['fields'].get('CenterPosition', '{}')
    try:
        building_position = json.loads(building_position_str)
    except:
        log.error(f"Invalid position for House of Natural Sciences")
        return None
    
    # Use a default travel time - in practice, citizens would use goto_location activity to travel
    # This is a simplified approach for the scope definition activity
    travel_time = timedelta(minutes=5)  # Default travel time
    
    # Get recent research context
    recent_observations = _get_recent_research_context(tables, citizen_username)
    
    # Ask citizen about their research scope
    research_scope = _ask_citizen_research_scope(
        citizen_username,
        citizen_name,
        recent_observations,
        api_base_url,
        kinos_model
    )
    
    if not research_scope:
        research_scope = "Defining the scope and boundaries of computational reality investigation"
    
    # Create the activity
    start_date = now_utc_dt + travel_time
    end_date = start_date + timedelta(minutes=SCOPE_DEFINITION_DURATION_MINUTES)
    
    activity_data = {
        'Citizen': citizen_username,
        'Type': 'research_scope_definition',
        'Title': f'Define research scope at {house_of_sciences["fields"].get("Name")}',
        'Description': f'{citizen_name} is defining the scope and objectives of their research investigation',
        'StartDate': start_date.isoformat(),
        'EndDate': end_date.isoformat(),
        'Status': 'Created',
        'BuildingId': house_of_sciences['id'],
        'LocationName': house_of_sciences['fields'].get('Name'),
        'Notes': json.dumps({
            'research_scope': research_scope,
            'building_name': house_of_sciences['fields'].get('Name'),
            'building_id': house_of_sciences['id'],
            'recent_context': recent_observations[:3],  # Store up to 3 recent observations
            'duration_minutes': SCOPE_DEFINITION_DURATION_MINUTES,
            'kinos_model': kinos_model
        })
    }
    
    try:
        created_activity = tables['activities'].create(activity_data)
        log.info(f"Created research_scope_definition activity for {citizen_username}")
        return created_activity
    except Exception as e:
        log.error(f"Failed to create research_scope_definition activity: {e}")
        return None
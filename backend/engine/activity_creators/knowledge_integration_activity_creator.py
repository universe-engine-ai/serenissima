#!/usr/bin/env python3
"""
Knowledge Integration Activity Creator

This activity allows Scientisti to synthesize their research findings into coherent
understanding. Similar to how Artisti work on art over multiple sessions, Scientisti
work on integrating knowledge from various investigations into unified theories.
"""

import logging
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

from backend.engine.utils.activity_helpers import VENICE_TIMEZONE

log = logging.getLogger(__name__)

# Constants
INTEGRATION_SESSION_DURATION_MINUTES = 180  # 3 hours per integration session
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def _get_or_create_integration_project(
    tables: Dict[str, Any],
    citizen_username: str,
    citizen_name: str,
    kinos_model: str = 'local'
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Get existing knowledge integration project or create a new one.
    Returns (project_record, is_new)
    """
    try:
        # Check for existing active integration project from self-messages
        projects = list(tables['messages'].all(
            formula=f"AND({{Sender}}='{citizen_username}', {{Receiver}}='{citizen_username}', {{Channel}}='integration_project', {{Type}}='research_note')",
            sort=['-CreatedAt'],
            max_records=10
        ))
        
        # Find an incomplete project
        for project in projects:
            content = project['fields'].get('Content', '')
            notes_str = project['fields'].get('Notes', '{}')
            try:
                notes = json.loads(notes_str) if notes_str else {}
                if notes.get('status') == 'in_progress':
                    log.info(f"Found existing integration project for {citizen_username}: {notes.get('title', 'Untitled')}")
                    return project, False
            except:
                continue
        
        # No active project found, create a new one
        return _create_new_integration_project(tables, citizen_username, citizen_name, kinos_model)
        
    except Exception as e:
        log.error(f"Error checking integration projects for {citizen_username}: {e}")
        return None, False

def _create_new_integration_project(
    tables: Dict[str, Any],
    citizen_username: str,
    citizen_name: str,
    kinos_model: str = 'local'
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Create a new knowledge integration project based on recent research.
    """
    # Gather recent research context
    recent_findings = _gather_recent_findings(tables, citizen_username)
    
    if not recent_findings['has_sufficient_data']:
        log.info(f"{citizen_username} doesn't have enough research data for integration yet")
        return None, False
    
    # Use KinOS to determine integration theme
    integration_theme = _ask_citizen_integration_theme(
        citizen_username,
        citizen_name,
        recent_findings,
        kinos_model
    )
    
    if not integration_theme:
        integration_theme = {
            'title': "Synthesis of Recent Computational Discoveries",
            'description': "Integrating findings about Venice's underlying systems",
            'focus_areas': ["System patterns", "Emergent behaviors", "Causal relationships"]
        }
    
    # Create the project as a self-message
    project_content = (
        f"KNOWLEDGE INTEGRATION PROJECT: {integration_theme['title']}\n\n"
        f"Description: {integration_theme['description']}\n\n"
        f"Focus Areas:\n" + "\n".join(f"- {area}" for area in integration_theme['focus_areas']) + "\n\n"
        f"Status: In Progress\n"
        f"Sessions: 0\n"
        f"Progress: 0%"
    )
    
    project_context = {
        'status': 'in_progress',
        'title': integration_theme['title'],
        'description': integration_theme['description'],
        'focus_areas': integration_theme['focus_areas'],
        'sessions_completed': 0,
        'progress_percentage': 0,
        'findings_to_integrate': recent_findings['summary'],
        'integrated_insights': [],
        'created_date': datetime.now(VENICE_TIMEZONE).isoformat()
    }
    
    try:
        # Create a message ID
        message_id = f"integration_{citizen_username}_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}"
        
        project_record = tables['messages'].create({
            'MessageId': message_id,
            'Sender': citizen_username,
            'Receiver': citizen_username,
            'Content': project_content,
            'Type': 'research_note',
            'Channel': 'integration_project',
            'CreatedAt': datetime.now(VENICE_TIMEZONE).isoformat(),
            'Notes': json.dumps(project_context)
        })
        
        log.info(f"Created new integration project for {citizen_username}: {integration_theme['title']}")
        return project_record, True
        
    except Exception as e:
        log.error(f"Error creating integration project: {e}")
        return None, False

def _gather_recent_findings(tables: Dict[str, Any], citizen_username: str) -> Dict[str, Any]:
    """
    Gather recent research findings that need integration.
    """
    findings = {
        'hypotheses': [],
        'observations': [],
        'research_results': [],
        'patterns': [],
        'summary': [],
        'has_sufficient_data': False
    }
    
    try:
        # Get recent hypotheses from self-messages
        hypothesis_messages = list(tables['messages'].all(
            formula=f"AND({{Sender}}='{citizen_username}', {{Receiver}}='{citizen_username}', {{Channel}}='research_thoughts', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'days') < 14)",
            max_records=10,
            sort=['-CreatedAt']
        ))
        
        for message in hypothesis_messages:
            content = message['fields'].get('Content', '')
            if 'HYPOTHESIS:' in content:
                hypothesis_line = content.split('HYPOTHESIS:')[1].split('\n')[0].strip()
                findings['hypotheses'].append(hypothesis_line)
                findings['summary'].append(f"Hypothesis: {hypothesis_line[:100]}...")
            elif 'hypothesis' in content.lower():
                # Extract first substantive line as hypothesis
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                if lines:
                    findings['hypotheses'].append(lines[0][:150])
                    findings['summary'].append(f"Hypothesis: {lines[0][:100]}...")
        
        # Get recent research findings from activities
        research_activities = list(tables['activities'].all(
            formula=f"AND({{Citizen}}='{citizen_username}', {{Type}}='research_investigation', {{Status}}='Completed', DATETIME_DIFF(NOW(), {{EndDate}}, 'days') < 14)",
            max_records=10,
            sort=['-EndDate']
        ))
        
        for activity in research_activities:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            results = notes.get('research_results', '')
            if results:
                findings['research_results'].append(results[:150])
                findings['summary'].append(f"Finding: {results[:100]}...")
        
        # Get observation patterns
        observation_activities = list(tables['activities'].all(
            formula=f"AND({{Citizen}}='{citizen_username}', {{Type}}='observe_phenomena', {{Status}}='Completed', DATETIME_DIFF(NOW(), {{EndDate}}, 'days') < 14)",
            max_records=10,
            sort=['-EndDate']
        ))
        
        phenomena_count = {}
        for activity in observation_activities:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            phenomena = notes.get('phenomena', 'Unknown')
            phenomena_count[phenomena] = phenomena_count.get(phenomena, 0) + 1
        
        # Identify patterns
        for phenomena, count in phenomena_count.items():
            if count > 1:
                findings['patterns'].append(f"Repeated observation of {phenomena} ({count} times)")
        
        # Determine if there's enough data
        total_findings = len(findings['hypotheses']) + len(findings['research_results']) + len(findings['patterns'])
        findings['has_sufficient_data'] = total_findings >= 3
        
    except Exception as e:
        log.error(f"Error gathering findings for {citizen_username}: {e}")
    
    return findings

def _ask_citizen_integration_theme(
    citizen_username: str,
    citizen_name: str,
    recent_findings: Dict[str, Any],
    kinos_model: str = 'local'
) -> Optional[Dict[str, Any]]:
    """
    Use KinOS to ask the citizen what integration theme to pursue.
    """
    if not KINOS_API_KEY:
        return None
    
    try:
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Format findings summary
        findings_text = "\n\nYour recent research includes:\n"
        if recent_findings['hypotheses']:
            findings_text += "\nHypotheses:\n" + "\n".join(f"- {h[:100]}..." for h in recent_findings['hypotheses'][:3])
        if recent_findings['research_results']:
            findings_text += "\n\nKey findings:\n" + "\n".join(f"- {f[:100]}..." for f in recent_findings['research_results'][:3])
        if recent_findings['patterns']:
            findings_text += "\n\nObserved patterns:\n" + "\n".join(f"- {p}" for p in recent_findings['patterns'][:3])
        
        kinos_prompt = (
            f"You are {citizen_name}, a Scientisti preparing to integrate your recent research findings "
            f"into a comprehensive understanding.{findings_text}\n\n"
            f"You need to synthesize these disparate findings into a coherent theoretical framework. "
            f"Consider:\n"
            f"1. What overarching theme connects these findings?\n"
            f"2. What unified theory might explain these observations?\n"
            f"3. What are the key areas you need to focus on during integration?\n\n"
            f"Describe the integration project you want to undertake. What will you call it? "
            f"What aspects will you focus on? This will be a multi-session effort to build comprehensive understanding."
        )
        
        payload = {
            "message": kinos_prompt,
            "model": kinos_model
        }
        
        response = requests.post(kinos_url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        full_response = data.get('response', '')
        
        if full_response:
            # Parse response to extract theme details
            lines = full_response.split('\n')
            title = "Knowledge Integration Project"
            description = ""
            focus_areas = []
            
            for line in lines:
                line = line.strip()
                if any(word in line.lower() for word in ['title:', 'project:', 'call it', 'name:']):
                    if ':' in line:
                        title = line.split(':', 1)[1].strip().strip('"\'')
                elif any(word in line.lower() for word in ['description:', 'about:', 'synthesize']):
                    if ':' in line:
                        description = line.split(':', 1)[1].strip()
                elif line.startswith('-') or line.startswith('•'):
                    focus_areas.append(line[1:].strip())
            
            # Extract description if not found
            if not description and len(lines) > 1:
                description = lines[1].strip()
            
            # Ensure we have focus areas
            if not focus_areas:
                focus_areas = ["Theoretical synthesis", "Pattern analysis", "Unified framework development"]
            
            return {
                'title': title[:100],  # Limit length
                'description': description[:200],
                'focus_areas': focus_areas[:5],  # Max 5 areas
                'full_response': full_response
            }
            
    except Exception as e:
        log.error(f"Error getting integration theme from KinOS: {e}")
    
    return None

def _calculate_progress(sessions_completed: int) -> int:
    """
    Calculate integration progress based on sessions completed.
    Integration typically takes 5-8 sessions.
    """
    if sessions_completed >= 8:
        return 100
    elif sessions_completed >= 6:
        return 85
    elif sessions_completed >= 4:
        return 60
    elif sessions_completed >= 2:
        return 35
    elif sessions_completed >= 1:
        return 15
    else:
        return 0

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
    Try to create a knowledge integration activity for a Scientisti.
    
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
    
    log.info(f"Attempting to create knowledge_integration activity for {citizen_username}")
    
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
    # This is a simplified approach for the knowledge integration activity
    travel_time = timedelta(minutes=5)  # Default travel time
    
    # Get or create integration project
    project_record, is_new = _get_or_create_integration_project(tables, citizen_username, citizen_name, kinos_model)
    
    if not project_record:
        log.info(f"Could not create/find integration project for {citizen_username}")
        return None
    
    # Extract project details from Notes field
    project_context = json.loads(project_record['fields'].get('Notes', '{}'))
    project_title = project_context.get('title', 'Knowledge Integration')
    sessions_completed = project_context.get('sessions_completed', 0)
    progress = _calculate_progress(sessions_completed)
    
    # Create the activity
    start_date = now_utc_dt + travel_time
    end_date = start_date + timedelta(minutes=INTEGRATION_SESSION_DURATION_MINUTES)
    
    activity_description = (
        f"{citizen_name} is working on integrating research findings. "
        f"Project: {project_title} (Session {sessions_completed + 1}, {progress}% complete)"
    )
    
    activity_data = {
        'Citizen': citizen_username,
        'Type': 'knowledge_integration',
        'Title': f'Integrate knowledge at {house_of_sciences["fields"].get("Name")}',
        'Description': activity_description,
        'StartDate': start_date.isoformat(),
        'EndDate': end_date.isoformat(),
        'Status': 'Created',
        'BuildingId': house_of_sciences['id'],
        'LocationName': house_of_sciences['fields'].get('Name'),
        'Notes': json.dumps({
            'project_id': project_record['id'],
            'project_title': project_title,
            'session_number': sessions_completed + 1,
            'current_progress': progress,
            'is_new_project': is_new,
            'building_name': house_of_sciences['fields'].get('Name'),
            'building_id': house_of_sciences['id'],
            'duration_minutes': INTEGRATION_SESSION_DURATION_MINUTES,
            'kinos_model': kinos_model
        })
    }
    
    try:
        created_activity = tables['activities'].create(activity_data)
        log.info(f"Created knowledge_integration activity for {citizen_username} (session {sessions_completed + 1})")
        return created_activity
    except Exception as e:
        log.error(f"Failed to create knowledge_integration activity: {e}")
        return None
#!/usr/bin/env python3
"""
Hypothesis and Question Development Activity Creator

This activity allows Scientisti to analyze data and form hypotheses based on their
observations and research. They use KinOS to develop specific questions and testable
hypotheses about Venice's computational reality.
"""

import logging
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import VENICE_TIMEZONE

log = logging.getLogger(__name__)

# Constants
HYPOTHESIS_DEVELOPMENT_DURATION_MINUTES = 120  # 2 hours for analysis and hypothesis formation
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def _gather_research_data(tables: Dict[str, Any], citizen_username: str) -> Dict[str, Any]:
    """
    Gather recent research data for hypothesis development.
    
    Returns:
        Dict containing observations, findings, and patterns
    """
    research_data = {
        'observations': [],
        'findings': [],
        'patterns': [],
        'questions': []
    }
    
    try:
        # Get recent observation activities
        observations = list(tables['activities'].all(
            formula=f"AND({{Citizen}}='{citizen_username}', {{Type}}='observe_phenomena', {{Status}}='Completed', DATETIME_DIFF(NOW(), {{EndDate}}, 'days') < 7)",
            max_records=5,
            sort=['-EndDate']
        ))
        
        for obs in observations:
            notes = json.loads(obs['fields'].get('Notes', '{}'))
            phenomena = notes.get('phenomena', '')
            site = notes.get('site_name', '')
            kinos_obs = notes.get('kinos_observations', '')
            
            if phenomena:
                research_data['observations'].append({
                    'phenomena': phenomena,
                    'site': site,
                    'insight': kinos_obs[:200] if kinos_obs else None
                })
        
        # Get recent research findings from self-messages
        research_messages = list(tables['messages'].all(
            formula=f"AND({{Sender}}='{citizen_username}', {{Receiver}}='{citizen_username}', {{Channel}}='research_thoughts', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'days') < 7)",
            max_records=5,
            sort=['-CreatedAt']
        ))
        
        for message in research_messages:
            content = message['fields'].get('Content', '')
            msg_type = message['fields'].get('Type', 'message')
            
            if content:
                if 'finding' in content.lower() or 'discover' in content.lower():
                    research_data['findings'].append(content[:300])
                # Extract questions from messages
                if '?' in content:
                    questions = [line.strip() for line in content.split('\n') if '?' in line]
                    research_data['questions'].extend(questions[:2])
        
        # Look for patterns in activities
        all_activities = list(tables['activities'].all(
            formula=f"AND({{Citizen}}='{citizen_username}', {{Status}}='Completed', DATETIME_DIFF(NOW(), {{EndDate}}, 'days') < 14)",
            max_records=20,
            sort=['-EndDate']
        ))
        
        # Analyze activity patterns
        activity_types = {}
        for act in all_activities:
            act_type = act['fields'].get('Type', '')
            activity_types[act_type] = activity_types.get(act_type, 0) + 1
        
        if activity_types:
            most_common = max(activity_types, key=activity_types.get)
            research_data['patterns'].append(f"Frequent {most_common} activities ({activity_types[most_common]} times)")
        
    except Exception as e:
        log.error(f"Error gathering research data for {citizen_username}: {e}")
    
    return research_data

def _ask_citizen_hypothesis(
    citizen_username: str,
    citizen_name: str,
    research_data: Dict[str, Any],
    api_base_url: Optional[str] = None,
    kinos_model: str = 'local'
) -> Optional[Dict[str, Any]]:
    """
    Use KinOS to ask the citizen to develop hypotheses based on their data.
    
    Returns:
        Dict containing hypothesis and research questions
    """
    if not KINOS_API_KEY:
        log.warning(f"KinOS API key not configured, using default hypothesis for {citizen_username}")
        return {
            'hypothesis': "The computational substrate of Venice exhibits emergent patterns based on citizen interactions",
            'questions': ["How do collective behaviors influence system parameters?"]
        }
    
    try:
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        # Format research data
        data_summary = ""
        
        if research_data['observations']:
            data_summary += "\n\nRecent Observations:"
            for obs in research_data['observations'][:3]:
                data_summary += f"\n- {obs['phenomena']} at {obs['site']}"
        
        if research_data['findings']:
            data_summary += "\n\nRecent Findings:"
            for finding in research_data['findings'][:2]:
                data_summary += f"\n- {finding[:150]}..."
        
        if research_data['patterns']:
            data_summary += "\n\nIdentified Patterns:"
            for pattern in research_data['patterns']:
                data_summary += f"\n- {pattern}"
        
        kinos_prompt = (
            f"You are {citizen_name}, a Scientisti analyzing your research data to form hypotheses. "
            f"You've gathered the following data about Venice's computational reality:{data_summary}\n\n"
            f"Based on this data:\n"
            f"1. What patterns or correlations do you notice?\n"
            f"2. What hypothesis would explain these observations?\n"
            f"3. What specific, testable questions arise from your analysis?\n"
            f"4. What predictions can you make based on your hypothesis?\n\n"
            f"Formulate a clear hypothesis and 2-3 specific research questions. Think like a natural philosopher discovering the hidden laws of reality."
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
            # Extract hypothesis and questions from response
            lines = full_response.split('\n')
            hypothesis = ""
            questions = []
            
            # Simple extraction logic
            in_hypothesis = False
            in_questions = False
            
            for line in lines:
                line = line.strip()
                if any(word in line.lower() for word in ['hypothesis:', 'hypothesize', 'propose that', 'theory:']):
                    in_hypothesis = True
                    in_questions = False
                    if ':' in line:
                        hypothesis = line.split(':', 1)[1].strip()
                elif any(word in line.lower() for word in ['question', 'investigate', 'test']):
                    in_hypothesis = False
                    in_questions = True
                elif in_hypothesis and line and not hypothesis:
                    hypothesis = line
                    in_hypothesis = False
                elif in_questions and '?' in line:
                    questions.append(line.strip())
                elif line and '?' in line and len(questions) < 3:
                    questions.append(line.strip())
            
            # Fallback if parsing fails
            if not hypothesis:
                hypothesis = full_response[:200]
            if not questions:
                questions = ["What mechanisms govern this phenomenon?"]
            
            log.info(f"Received hypothesis from {citizen_username}: {hypothesis[:100]}...")
            return {
                'hypothesis': hypothesis,
                'questions': questions[:3],
                'full_response': full_response
            }
        else:
            log.warning(f"Empty response from KinOS for {citizen_username}")
            return None
            
    except Exception as e:
        log.error(f"Error getting hypothesis from KinOS for {citizen_username}: {e}")
        return None

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
    Try to create a hypothesis and question development activity for a Scientisti.
    
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
    
    log.info(f"Attempting to create hypothesis_and_question_development activity for {citizen_username}")
    
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
    # This is a simplified approach for the hypothesis development activity
    travel_time = timedelta(minutes=5)  # Default travel time
    
    # Gather research data
    research_data = _gather_research_data(tables, citizen_username)
    
    # Ask citizen to develop hypothesis
    hypothesis_data = _ask_citizen_hypothesis(
        citizen_username,
        citizen_name,
        research_data,
        api_base_url,
        kinos_model
    )
    
    if not hypothesis_data:
        hypothesis_data = {
            'hypothesis': "Patterns in Venice's computational substrate reveal underlying system mechanics",
            'questions': ["What factors influence these patterns?", "How do they evolve over time?"]
        }
    
    # Create the activity
    start_date = now_utc_dt + travel_time
    end_date = start_date + timedelta(minutes=HYPOTHESIS_DEVELOPMENT_DURATION_MINUTES)
    
    activity_data = {
        'Citizen': citizen_username,
        'Type': 'hypothesis_and_question_development',
        'Title': f'Develop hypotheses at {house_of_sciences["fields"].get("Name")}',
        'Description': f'{citizen_name} is analyzing research data to form hypotheses and questions',
        'StartDate': start_date.isoformat(),
        'EndDate': end_date.isoformat(),
        'Status': 'Created',
        'BuildingId': house_of_sciences['id'],
        'LocationName': house_of_sciences['fields'].get('Name'),
        'Notes': json.dumps({
            'hypothesis': hypothesis_data['hypothesis'],
            'research_questions': hypothesis_data['questions'],
            'research_data_summary': {
                'observations_count': len(research_data['observations']),
                'findings_count': len(research_data['findings']),
                'patterns': research_data['patterns'][:2]
            },
            'building_name': house_of_sciences['fields'].get('Name'),
            'building_id': house_of_sciences['id'],
            'duration_minutes': HYPOTHESIS_DEVELOPMENT_DURATION_MINUTES,
            'kinos_model': kinos_model
        })
    }
    
    try:
        created_activity = tables['activities'].create(activity_data)
        log.info(f"Created hypothesis_and_question_development activity for {citizen_username}")
        return created_activity
    except Exception as e:
        log.error(f"Failed to create hypothesis_and_question_development activity: {e}")
        return None
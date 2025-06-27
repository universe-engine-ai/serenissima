#!/usr/bin/env python3
"""
Research Scope Definition Activity Processor

Processes the research scope definition activity where Scientisti plan and document
their research objectives. Uses KinOS for reflection and stores the scope as a thought.
"""

import logging
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import LogColors, VENICE_TIMEZONE

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def _reflect_on_scope_async(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    citizen_username: str,
    research_scope: str,
    building_name: str,
    recent_context: list,
    kinos_model: str = "local"
):
    """
    Generate KinOS reflection on the defined research scope.
    Runs in a separate thread.
    """
    thread_id = threading.get_ident()
    activity_id = activity_record['id']
    
    log.info(f"  [Thread: {thread_id}] Starting scope reflection for {citizen_username}")
    
    try:
        if KINOS_API_KEY:
            kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
            
            # Format recent context
            context_text = ""
            if recent_context:
                context_text = "\n\nRecent research context:\n" + "\n".join(f"- {ctx}" for ctx in recent_context)
            
            kinos_prompt = (
                f"You are {citizen_username}, a Scientisti who has just spent 90 minutes at {building_name} "
                f"defining your research scope.{context_text}\n\n"
                f"Your defined scope: {research_scope}\n\n"
                f"Reflect on:\n"
                f"1. Why this particular scope appeals to your scientific curiosity\n"
                f"2. The specific boundaries you've set and why they're important\n"
                f"3. Your primary objectives and what you hope to discover\n"
                f"4. The methods you plan to employ and their rationale\n"
                f"5. How this research might contribute to understanding Venice's computational nature\n\n"
                f"Write as a research planning journal entry, showing your systematic thinking."
            )
            
            kinos_payload = {
                "message": kinos_prompt,
                "model": kinos_model,
                "addSystem": json.dumps({
                    "activity_context": {
                        "type": "research_scope_definition",
                        "research_scope": research_scope,
                        "location": building_name
                    }
                })
            }
            
            try:
                import requests
                kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=120)
                kinos_response.raise_for_status()
                
                kinos_data = kinos_response.json()
                reflection = kinos_data.get('response', 'The research scope has been carefully defined.')
                
                log.info(f"  [Thread: {thread_id}] Generated KinOS reflection for {citizen_username}")
                
                # Store the scope definition as a self-message
                message_id = f"msg_{citizen_username}_self_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}_scope_definition"
                message_record = tables['messages'].create({
                    "MessageId": message_id,
                    "Sender": citizen_username,
                    "Receiver": citizen_username,
                    "Content": reflection,
                    "Type": "research_note",
                    "Channel": "research_thoughts",
                    "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                    "Notes": json.dumps({
                        "activity": "research_scope_definition",
                        "research_scope": research_scope,
                        "location": building_name,
                        "recent_context": recent_context,
                        "note_type": "research_planning"
                    })
                })
                
                log.info(f"  [Thread: {thread_id}] Stored research planning self-message for {citizen_username}")
                
                # Update activity notes with completion
                notes_str = activity_record['fields'].get('Notes', '{}')
                try:
                    notes_dict = json.loads(notes_str)
                except json.JSONDecodeError:
                    notes_dict = {}
                
                notes_dict['reflection_generated'] = True
                notes_dict['self_message_created'] = True
                notes_dict['kinos_reflection'] = reflection[:500]  # Store preview
                
                tables['activities'].update(activity_id, {'Notes': json.dumps(notes_dict)})
                
            except Exception as e:
                log.error(f"  [Thread: {thread_id}] Error with KinOS reflection: {e}")
        else:
            log.info(f"  [Thread: {thread_id}] KinOS not configured, storing scope without reflection")
            
            # Still create a self-message with the scope
            message_id = f"msg_{citizen_username}_self_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}_scope_no_kinos"
            message_record = tables['messages'].create({
                "MessageId": message_id,
                "Sender": citizen_username,
                "Receiver": citizen_username,
                "Content": f"Research Scope Defined: {research_scope}",
                "Type": "research_note",
                "Channel": "research_thoughts",
                "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                "Notes": json.dumps({
                    "activity": "research_scope_definition",
                    "research_scope": research_scope,
                    "location": building_name,
                    "no_reflection": True,
                    "note_type": "research_planning"
                })
            })
        
    except Exception as e:
        log.error(f"  [Thread: {thread_id}] Error in scope reflection thread: {e}")
        import traceback
        log.error(traceback.format_exc())

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Process a 'research_scope_definition' activity for Scientisti.
    
    Args:
        tables: Database tables
        activity_record: The activity record to process
        building_type_defs: Building type definitions
        resource_defs: Resource definitions
        api_base_url: Base URL for API calls
        
    Returns:
        True if processing succeeded, False otherwise
    """
    activity_id = activity_record['id']
    activity_guid = activity_record['fields'].get('ActivityId', activity_id)
    citizen_username = activity_record['fields'].get('Citizen')
    
    log.info(f"{LogColors.PROCESS}Processing 'research_scope_definition' for {citizen_username}{LogColors.ENDC}")
    
    # Parse activity notes
    notes_str = activity_record['fields'].get('Notes', '{}')
    try:
        notes_dict = json.loads(notes_str)
    except json.JSONDecodeError:
        log.warning(f"{LogColors.WARNING}Activity {activity_guid} has invalid JSON in Notes{LogColors.ENDC}")
        return True
    
    research_scope = notes_dict.get('research_scope', 'Defining research boundaries and objectives')
    building_name = notes_dict.get('building_name', 'House of Natural Sciences')
    recent_context = notes_dict.get('recent_context', [])
    kinos_model = notes_dict.get('kinos_model', 'local')
    
    log.info(f"  Research scope: {research_scope[:100]}...")
    
    # Apply mood bonus for intellectual work
    try:
        citizen = tables['citizens'].get(activity_record['fields'].get('CitizenAirtableId'))
        current_mood = citizen['fields'].get('Mood', 50)
        
        # Planning research is intellectually stimulating
        mood_change = 5
        new_mood = min(100, current_mood + mood_change)
        
        tables['citizens'].update(citizen['id'], {'Mood': new_mood})
        log.info(f"  Updated {citizen_username} mood: {current_mood} -> {new_mood} (+{mood_change} for research planning)")
    except Exception as e:
        log.error(f"  Error updating mood: {e}")
    
    # Start async thread for KinOS reflection
    reflection_thread = threading.Thread(
        target=_reflect_on_scope_async,
        args=(tables, activity_record, citizen_username, research_scope, building_name, recent_context, kinos_model)
    )
    reflection_thread.start()
    
    log.info(f"{LogColors.SUCCESS}Started reflection thread {reflection_thread.ident} for {citizen_username}'s scope definition{LogColors.ENDC}")
    
    log.info(f"{LogColors.SUCCESS}Research scope definition activity {activity_guid} processed successfully{LogColors.ENDC}")
    return True
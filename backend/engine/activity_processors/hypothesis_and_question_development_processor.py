#!/usr/bin/env python3
"""
Hypothesis and Question Development Activity Processor

Processes the hypothesis development activity where Scientisti analyze data
and form testable hypotheses. Uses KinOS for reflection and stores hypotheses
as thoughts for future reference.
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

def _reflect_on_hypothesis_async(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    citizen_username: str,
    hypothesis: str,
    research_questions: list,
    building_name: str,
    kinos_model: str = "local"
):
    """
    Generate KinOS reflection on the developed hypothesis.
    Runs in a separate thread.
    """
    thread_id = threading.get_ident()
    activity_id = activity_record['id']
    
    log.info(f"  [Thread: {thread_id}] Starting hypothesis reflection for {citizen_username}")
    
    try:
        if KINOS_API_KEY:
            kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
            
            # Format research questions
            questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(research_questions))
            
            kinos_prompt = (
                f"You are {citizen_username}, a Scientisti who has just spent 2 hours at {building_name} "
                f"analyzing your research data and developing hypotheses.\n\n"
                f"Your hypothesis: {hypothesis}\n\n"
                f"Your research questions:\n{questions_text}\n\n"
                f"Reflect on:\n"
                f"1. The logical process that led you to this hypothesis\n"
                f"2. What evidence supports or challenges this hypothesis\n"
                f"3. How you plan to test these questions experimentally\n"
                f"4. What implications this hypothesis has for understanding Venice\n"
                f"5. What new avenues of investigation this opens\n\n"
                f"Write as a scientific journal entry, showing your analytical thinking and excitement about potential discoveries."
            )
            
            kinos_payload = {
                "message": kinos_prompt,
                "model": kinos_model,
                "addSystem": json.dumps({
                    "activity_context": {
                        "type": "hypothesis_development",
                        "hypothesis": hypothesis,
                        "questions": research_questions,
                        "location": building_name
                    }
                })
            }
            
            try:
                import requests
                kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=120)
                kinos_response.raise_for_status()
                
                kinos_data = kinos_response.json()
                reflection = kinos_data.get('response', 'The hypothesis has been carefully formulated.')
                
                log.info(f"  [Thread: {thread_id}] Generated KinOS reflection for {citizen_username}")
                
                # Store the hypothesis as a self-message
                message_id = f"msg_{citizen_username}_self_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}_hypothesis"
                message_record = tables['messages'].create({
                    "MessageId": message_id,
                    "Sender": citizen_username,
                    "Receiver": citizen_username,
                    "Content": reflection,
                    "Type": "research_note",
                    "Channel": "research_thoughts",
                    "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                    "Notes": json.dumps({
                        "activity": "hypothesis_development",
                        "hypothesis": hypothesis,
                        "research_questions": research_questions,
                        "location": building_name,
                        "note_type": "hypothesis_reflection"
                    })
                })
                
                log.info(f"  [Thread: {thread_id}] Stored hypothesis reflection as self-message for {citizen_username}")
                
                # Also create a separate self-message for the hypothesis itself (for easy retrieval)
                hypothesis_summary = f"HYPOTHESIS: {hypothesis}\n\nRESEARCH QUESTIONS:\n" + \
                                  "\n".join(f"- {q}" for q in research_questions)
                
                summary_message_id = f"msg_{citizen_username}_self_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}_summary"
                summary_message = tables['messages'].create({
                    "MessageId": summary_message_id,
                    "Sender": citizen_username,
                    "Receiver": citizen_username,
                    "Content": hypothesis_summary,
                    "Type": "research_note",
                    "Channel": "research_thoughts",
                    "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                    "Notes": json.dumps({
                        "is_hypothesis_record": True,
                        "hypothesis": hypothesis,
                        "questions": research_questions,
                        "note_type": "hypothesis_summary"
                    })
                })
                
                # Update activity notes with completion
                notes_str = activity_record['fields'].get('Notes', '{}')
                try:
                    notes_dict = json.loads(notes_str)
                except json.JSONDecodeError:
                    notes_dict = {}
                
                notes_dict['reflection_generated'] = True
                notes_dict['self_messages_created'] = True
                notes_dict['kinos_reflection'] = reflection[:500]  # Store preview
                
                tables['activities'].update(activity_id, {'Notes': json.dumps(notes_dict)})
                
            except Exception as e:
                log.error(f"  [Thread: {thread_id}] Error with KinOS reflection: {e}")
        else:
            log.info(f"  [Thread: {thread_id}] KinOS not configured, storing hypothesis without reflection")
            
            # Still create self-message with the hypothesis
            hypothesis_summary = f"HYPOTHESIS: {hypothesis}\n\nRESEARCH QUESTIONS:\n" + \
                              "\n".join(f"- {q}" for q in research_questions)
            
            message_id = f"msg_{citizen_username}_self_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}_hypothesis_no_kinos"
            message_record = tables['messages'].create({
                "MessageId": message_id,
                "Sender": citizen_username,
                "Receiver": citizen_username,
                "Content": hypothesis_summary,
                "Type": "research_note",
                "Channel": "research_thoughts",
                "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                "Notes": json.dumps({
                    "activity": "hypothesis_development",
                    "hypothesis": hypothesis,
                    "questions": research_questions,
                    "location": building_name,
                    "no_reflection": True,
                    "note_type": "hypothesis_summary"
                })
            })
        
    except Exception as e:
        log.error(f"  [Thread: {thread_id}] Error in hypothesis reflection thread: {e}")
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
    Process a 'hypothesis_and_question_development' activity for Scientisti.
    
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
    
    log.info(f"{LogColors.PROCESS}Processing 'hypothesis_and_question_development' for {citizen_username}{LogColors.ENDC}")
    
    # Parse activity notes
    notes_str = activity_record['fields'].get('Notes', '{}')
    try:
        notes_dict = json.loads(notes_str)
    except json.JSONDecodeError:
        log.warning(f"{LogColors.WARNING}Activity {activity_guid} has invalid JSON in Notes{LogColors.ENDC}")
        return True
    
    hypothesis = notes_dict.get('hypothesis', 'Patterns in Venice reveal underlying mechanics')
    research_questions = notes_dict.get('research_questions', [])
    building_name = notes_dict.get('building_name', 'House of Natural Sciences')
    research_data_summary = notes_dict.get('research_data_summary', {})
    kinos_model = notes_dict.get('kinos_model', 'local')
    
    log.info(f"  Hypothesis: {hypothesis[:100]}...")
    log.info(f"  Research questions: {len(research_questions)} formulated")
    
    # Apply mood bonus for intellectual breakthrough
    try:
        citizen = tables['citizens'].get(activity_record['fields'].get('CitizenAirtableId'))
        current_mood = citizen['fields'].get('Mood', 50)
        
        # Forming hypotheses is intellectually exciting
        mood_change = 8  # Higher bonus for creative breakthrough
        new_mood = min(100, current_mood + mood_change)
        
        tables['citizens'].update(citizen['id'], {'Mood': new_mood})
        log.info(f"  Updated {citizen_username} mood: {current_mood} -> {new_mood} (+{mood_change} for hypothesis development)")
    except Exception as e:
        log.error(f"  Error updating mood: {e}")
    
    # Check if this builds on previous observations
    obs_count = research_data_summary.get('observations_count', 0)
    findings_count = research_data_summary.get('findings_count', 0)
    
    if obs_count > 0 or findings_count > 0:
        log.info(f"  Built on {obs_count} observations and {findings_count} previous findings")
    
    # Start async thread for KinOS reflection
    reflection_thread = threading.Thread(
        target=_reflect_on_hypothesis_async,
        args=(tables, activity_record, citizen_username, hypothesis, research_questions, building_name, kinos_model)
    )
    reflection_thread.start()
    
    log.info(f"{LogColors.SUCCESS}Started reflection thread {reflection_thread.ident} for {citizen_username}'s hypothesis{LogColors.ENDC}")
    
    # Log the hypothesis for game metrics
    log.info(f"  [HYPOTHESIS] {citizen_username}: {hypothesis[:200]}...")
    
    log.info(f"{LogColors.SUCCESS}Hypothesis development activity {activity_guid} processed successfully{LogColors.ENDC}")
    return True
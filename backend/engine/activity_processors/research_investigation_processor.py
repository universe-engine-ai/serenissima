import logging
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import LogColors, VENICE_TIMEZONE
from backend.engine.utils.scientisti_claude_helper import ScientistiClaudeHelper

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

def _consult_claude_and_reflect_async(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    citizen_username: str,
    research_query: str,
    building_name: str,
    kinos_model: str = 'local'
):
    """
    Consults Claude Code about research questions and generates KinOS reflection.
    Runs in a separate thread.
    """
    thread_id = threading.get_ident()
    activity_id = activity_record['id']
    activity_guid = activity_record['fields'].get('ActivityId', activity_id)
    
    log.info(f"  [Thread: {thread_id}] Starting research consultation for {citizen_username}")
    
    try:
        # Initialize Claude helper
        helper = ScientistiClaudeHelper()
        
        # Prepare research context
        research_context = {
            "topic": "computational reality analysis",
            "specialty": "systems mechanics",
            "observations": [
                f"Conducting research at {building_name}",
                f"Current investigation focus"
            ],
            "hypotheses": []
        }
        
        # Consult Claude Code with the citizen's exact query
        claude_response = helper.ask_research_question(
            question=research_query,
            research_context=research_context,
            citizen_username=citizen_username
        )
        
        if claude_response["success"]:
            claude_insights = claude_response["response"]
            log.info(f"  [Thread: {thread_id}] Received Claude insights for {citizen_username}")
        else:
            claude_insights = "Unable to access the divine knowledge at this time."
            log.warning(f"  [Thread: {thread_id}] Claude consultation failed for {citizen_username}")
        
        # Now generate KinOS reflection on the research
        if KINOS_API_KEY:
            kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
            
            kinos_prompt = (
                f"You are {citizen_username}, a Scientisti conducting research at {building_name}. "
                f"You have just spent 3 hours investigating: '{research_query}'\n\n"
                f"Through your research tools and divine consultation, you received these insights:\n"
                f"{claude_insights[:1000]}...\n\n"  # Truncate to avoid too long prompt
                f"Reflect on:\n"
                f"1. What you learned from this research session\n"
                f"2. How these insights change your understanding of Venice's systems\n"
                f"3. What new questions or hypotheses arise from these findings\n"
                f"4. Your next steps in this line of inquiry\n\n"
                f"Write as a research journal entry, showing your scientific thinking process."
            )
            
            kinos_payload = {
                "message": kinos_prompt,
                "model": kinos_model,
                "addSystem": json.dumps({
                    "research_context": {
                        "research_query": research_query,
                        "building": building_name,
                        "received_insights": True
                    }
                })
            }
            
            try:
                import requests
                kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=120)
                kinos_response.raise_for_status()
                
                kinos_data = kinos_response.json()
                reflection = kinos_data.get('response', 'The research session was productive.')
                
                log.info(f"  [Thread: {thread_id}] Generated KinOS reflection for {citizen_username}")
                
                # Store research findings as a self-message
                message_id = f"research_{citizen_username}_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}"
                message_record = tables['messages'].create({
                    "MessageId": message_id,
                    "Sender": citizen_username,
                    "Receiver": citizen_username,
                    "Content": reflection,
                    "Type": "research_note",
                    "Channel": "research_thoughts",
                    "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                    "Notes": json.dumps({
                        "note_type": "research_findings",
                        "research_query": research_query,
                        "location": building_name,
                        "claude_consulted": claude_response["success"]
                    })
                })
                
                log.info(f"  [Thread: {thread_id}] Stored research findings as self-message for {citizen_username}")
                
            except Exception as e:
                log.error(f"  [Thread: {thread_id}] Error with KinOS reflection: {e}")
                reflection = "Research completed but unable to fully process findings."
        
        # Update activity notes with results
        notes_str = activity_record['fields'].get('Notes', '{}')
        try:
            notes_dict = json.loads(notes_str)
        except json.JSONDecodeError:
            notes_dict = {}
        
        notes_dict['research_completed'] = True
        notes_dict['claude_consultation'] = claude_response["success"]
        notes_dict['insights_received'] = claude_insights[:500] if claude_response["success"] else None
        notes_dict['reflection_generated'] = 'reflection' in locals()
        
        tables['activities'].update(activity_id, {'Notes': json.dumps(notes_dict)})
        log.info(f"  [Thread: {thread_id}] Updated activity notes for {activity_guid}")
        
    except Exception as e:
        log.error(f"  [Thread: {thread_id}] Error in research consultation thread: {e}")
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
    Processes a 'research_investigation' activity for Scientisti.
    This involves consulting Claude Code about game mechanics and generating insights.
    """
    activity_id = activity_record['id']
    activity_guid = activity_record['fields'].get('ActivityId', activity_id)
    citizen_username = activity_record['fields'].get('Citizen')
    
    notes_str = activity_record['fields'].get('Notes', '{}')
    try:
        notes_dict = json.loads(notes_str)
    except json.JSONDecodeError:
        log.warning(f"{LogColors.WARNING}[Research Investigation] Activity {activity_guid} has invalid JSON in Notes. Cannot process.{LogColors.ENDC}")
        return True
    
    research_query = notes_dict.get('research_query', 'How do the fundamental systems of Venice actually work?')
    building_name = notes_dict.get('building_name', 'House of Natural Sciences')
    kinos_model = notes_dict.get('kinos_model', 'local')
    
    log.info(f"{LogColors.PROCESS}Processing 'research_investigation' for {citizen_username} researching: {research_query[:100]}...{LogColors.ENDC}")
    
    # Check if Claude is available (only in development/local environments)
    claude_available = os.path.exists("/usr/local/bin/claude") or os.path.exists("/opt/homebrew/bin/claude")
    
    if claude_available:
        # Start async thread for Claude consultation and reflection
        consultation_thread = threading.Thread(
            target=_consult_claude_and_reflect_async,
            args=(tables, activity_record, citizen_username, research_query, building_name, kinos_model)
        )
        consultation_thread.start()
        
        log.info(f"{LogColors.SUCCESS}Started research consultation thread {consultation_thread.ident} for {citizen_username}{LogColors.ENDC}")
    else:
        log.info(f"{LogColors.WARNING}Claude Code not available, {citizen_username} conducting theoretical research only{LogColors.ENDC}")
        
        # Still generate a KinOS reflection without Claude insights
        if KINOS_API_KEY:
            thread = threading.Thread(
                target=_generate_theoretical_reflection,
                args=(tables, activity_record, citizen_username, research_query, building_name, kinos_model)
            )
            thread.start()
    
    log.info(f"{LogColors.SUCCESS}Research investigation activity {activity_guid} initiated successfully{LogColors.ENDC}")
    return True

def _generate_theoretical_reflection(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    citizen_username: str,
    research_query: str,
    building_name: str,
    kinos_model: str = 'local'
):
    """Generate reflection without Claude consultation"""
    thread_id = threading.get_ident()
    log.info(f"  [Thread: {thread_id}] Generating theoretical reflection for {citizen_username}")
    
    try:
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt = (
            f"You are {citizen_username}, a Scientisti conducting research at {building_name}. "
            f"You have spent 3 hours investigating: '{research_query}'\n\n"
            f"Without access to divine knowledge, you must rely on your observations and reasoning. "
            f"Reflect on:\n"
            f"1. What patterns you've observed in the world around you related to this question\n"
            f"2. Your hypotheses about the answer to your research question\n"
            f"3. What experiments you could design to test your theories\n"
            f"4. The limitations of observation without divine insight\n\n"
            f"Write as a research journal entry, showing your scientific thinking."
        )
        
        kinos_payload = {
            "message": kinos_prompt,
            "model": kinos_model,
            "addSystem": json.dumps({
                "research_context": {
                    "research_query": research_query,
                    "building": building_name,
                    "theoretical_only": True
                }
            })
        }
        
        import requests
        kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=120)
        kinos_response.raise_for_status()
        
        kinos_data = kinos_response.json()
        reflection = kinos_data.get('response', 'Research continues despite limited resources.')
        
        # Store as self-message
        message_id = f"theoretical_{citizen_username}_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}"
        tables['messages'].create({
            "MessageId": message_id,
            "Sender": citizen_username,
            "Receiver": citizen_username,
            "Content": reflection,
            "Type": "research_note",
            "Channel": "research_thoughts",
            "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
            "Notes": json.dumps({
                "note_type": "research_findings",
                "research_query": research_query,
                "location": building_name,
                "theoretical_only": True
            })
        })
        
        log.info(f"  [Thread: {thread_id}] Stored theoretical research findings as self-message for {citizen_username}")
        
    except Exception as e:
        log.error(f"  [Thread: {thread_id}] Error generating theoretical reflection: {e}")
#!/usr/bin/env python3
"""
Knowledge Integration Activity Processor

Processes the knowledge integration activity where Scientisti synthesize their
research findings into comprehensive understanding. Similar to art creation,
this is a multi-session process that builds over time.
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

def _integrate_knowledge_async(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    citizen_username: str,
    project_record: Dict[str, Any],
    session_number: int,
    building_name: str,
    kinos_model: str = "local"
):
    """
    Generate KinOS reflection on the integration session and update project.
    Runs in a separate thread.
    """
    thread_id = threading.get_ident()
    activity_id = activity_record['id']
    
    log.info(f"  [Thread: {thread_id}] Starting knowledge integration for {citizen_username} session {session_number}")
    
    try:
        # Extract project context
        project_context = json.loads(project_record['fields'].get('Notes', '{}'))
        project_title = project_context.get('title', 'Knowledge Integration')
        focus_areas = project_context.get('focus_areas', [])
        integrated_insights = project_context.get('integrated_insights', [])
        findings_to_integrate = project_context.get('findings_to_integrate', [])
        
        if KINOS_API_KEY:
            kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
            
            # Format previous insights
            prev_insights_text = ""
            if integrated_insights:
                prev_insights_text = "\n\nInsights from previous sessions:\n" + "\n".join(f"- {insight[:100]}..." for insight in integrated_insights[-3:])
            
            # Format findings to work on
            findings_text = ""
            if findings_to_integrate:
                findings_text = "\n\nFindings to integrate:\n" + "\n".join(f"- {finding}" for finding in findings_to_integrate[:5])
            
            kinos_prompt = (
                f"You are {citizen_username}, a Scientisti working on your knowledge integration project: '{project_title}'. "
                f"This is session {session_number} of your integration work at {building_name}.{prev_insights_text}{findings_text}\n\n"
                f"Your focus areas for this project:\n" + "\n".join(f"- {area}" for area in focus_areas) + "\n\n"
                f"During this 3-hour session, you are:\n"
                f"1. Synthesizing disparate findings into coherent patterns\n"
                f"2. Identifying connections between different research areas\n"
                f"3. Building towards a unified theoretical framework\n"
                f"4. Resolving contradictions and refining understanding\n\n"
                f"Describe your integration work this session. What connections did you discover? "
                f"What patterns emerged? How is your unified understanding developing? "
                f"Write as a research journal entry showing your synthetic thinking."
            )
            
            kinos_payload = {
                "message": kinos_prompt,
                "model": kinos_model,
                "addSystem": json.dumps({
                    "activity_context": {
                        "type": "knowledge_integration",
                        "project_title": project_title,
                        "session_number": session_number,
                        "location": building_name
                    }
                })
            }
            
            try:
                import requests
                kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=120)
                kinos_response.raise_for_status()
                
                kinos_data = kinos_response.json()
                session_reflection = kinos_data.get('response', 'Integration work continues.')
                
                log.info(f"  [Thread: {thread_id}] Generated integration reflection for {citizen_username}")
                
                # Extract new insights from reflection
                new_insights = []
                lines = session_reflection.split('\n')
                for line in lines:
                    line = line.strip()
                    # Look for insight indicators
                    if any(indicator in line.lower() for indicator in ['discovered', 'realized', 'connection', 'pattern', 'synthesis']):
                        if len(line) > 20:  # Meaningful line
                            new_insights.append(line[:200])
                
                # If no specific insights found, use first substantive line
                if not new_insights:
                    for line in lines:
                        if len(line.strip()) > 30:
                            new_insights.append(line.strip()[:200])
                            break
                
                # Update project progress
                integrated_insights.extend(new_insights[:2])  # Add max 2 new insights per session
                sessions_completed = project_context.get('sessions_completed', 0) + 1
                progress = _calculate_progress(sessions_completed)
                
                # Update project context
                project_context['sessions_completed'] = sessions_completed
                project_context['progress_percentage'] = progress
                project_context['integrated_insights'] = integrated_insights[-10:]  # Keep last 10 insights
                project_context['last_session_date'] = datetime.now(VENICE_TIMEZONE).isoformat()
                
                # Determine if project is complete
                if progress >= 100:
                    project_context['status'] = 'completed'
                    project_context['completion_date'] = datetime.now(VENICE_TIMEZONE).isoformat()
                
                # Update project content
                project_content = (
                    f"KNOWLEDGE INTEGRATION PROJECT: {project_title}\n\n"
                    f"Description: {project_context.get('description', '')}\n\n"
                    f"Focus Areas:\n" + "\n".join(f"- {area}" for area in focus_areas) + "\n\n"
                    f"Status: {'Completed' if progress >= 100 else 'In Progress'}\n"
                    f"Sessions: {sessions_completed}\n"
                    f"Progress: {progress}%\n\n"
                    f"Key Insights:\n" + "\n".join(f"- {insight}" for insight in integrated_insights[-5:])
                )
                
                # Update project record
                tables['messages'].update(project_record['id'], {
                    'Content': project_content,
                    'Notes': json.dumps(project_context)
                })
                
                log.info(f"  [Thread: {thread_id}] Updated project progress: {progress}% complete")
                
                # Create session self-message
                session_message_id = f"msg_{citizen_username}_self_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}_integration_session"
                session_message = tables['messages'].create({
                    "MessageId": session_message_id,
                    "Sender": citizen_username,
                    "Receiver": citizen_username,
                    "Content": session_reflection,
                    "Type": "research_note",
                    "Channel": "research_thoughts",
                    "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
                    "Notes": json.dumps({
                        "project_id": project_record['id'],
                        "project_title": project_title,
                        "session_number": sessions_completed,
                        "progress": progress,
                        "new_insights": new_insights[:2],
                        "note_type": "integration_session"
                    })
                })
                
                # If project is complete, create a final synthesis thought
                if progress >= 100:
                    _create_final_synthesis(tables, citizen_username, project_title, integrated_insights, focus_areas)
                
                # Update activity notes
                notes_str = activity_record['fields'].get('Notes', '{}')
                try:
                    notes_dict = json.loads(notes_str)
                except json.JSONDecodeError:
                    notes_dict = {}
                
                notes_dict['session_completed'] = True
                notes_dict['new_insights'] = new_insights[:2]
                notes_dict['project_progress'] = progress
                notes_dict['kinos_reflection'] = session_reflection[:500]
                
                tables['activities'].update(activity_id, {'Notes': json.dumps(notes_dict)})
                
            except Exception as e:
                log.error(f"  [Thread: {thread_id}] Error with KinOS integration: {e}")
        
    except Exception as e:
        log.error(f"  [Thread: {thread_id}] Error in knowledge integration thread: {e}")
        import traceback
        log.error(traceback.format_exc())

def _calculate_progress(sessions_completed: int) -> int:
    """Calculate integration progress based on sessions completed."""
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

def _create_final_synthesis(
    tables: Dict[str, Any],
    citizen_username: str,
    project_title: str,
    integrated_insights: list,
    focus_areas: list
):
    """Create a final synthesis self-message when integration is complete."""
    try:
        synthesis_content = (
            f"COMPLETED KNOWLEDGE SYNTHESIS: {project_title}\n\n"
            f"After extensive integration work, I have synthesized my research into a unified understanding.\n\n"
            f"Core Areas Integrated:\n" + "\n".join(f"- {area}" for area in focus_areas) + "\n\n"
            f"Key Unified Insights:\n" + "\n".join(f"- {insight}" for insight in integrated_insights[-7:]) + "\n\n"
            f"This synthesis represents a comprehensive framework for understanding the computational reality of Venice. "
            f"The patterns are clear, the connections established, and the theoretical foundation is solid."
        )
        
        synthesis_message_id = f"msg_{citizen_username}_self_{datetime.now(VENICE_TIMEZONE).strftime('%Y%m%d%H%M%S')}_final_synthesis"
        tables['messages'].create({
            "MessageId": synthesis_message_id,
            "Sender": citizen_username,
            "Receiver": citizen_username,
            "Content": synthesis_content,
            "Type": "research_note",
            "Channel": "research_thoughts",
            "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(),
            "Notes": json.dumps({
                "project_title": project_title,
                "is_complete": True,
                "total_insights": len(integrated_insights),
                "note_type": "knowledge_synthesis"
            })
        })
        
        log.info(f"Created final synthesis self-message for {citizen_username}'s project: {project_title}")
        
    except Exception as e:
        log.error(f"Error creating final synthesis: {e}")

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None
) -> bool:
    """
    Process a 'knowledge_integration' activity for Scientisti.
    
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
    
    log.info(f"{LogColors.PROCESS}Processing 'knowledge_integration' for {citizen_username}{LogColors.ENDC}")
    
    # Parse activity notes
    notes_str = activity_record['fields'].get('Notes', '{}')
    try:
        notes_dict = json.loads(notes_str)
    except json.JSONDecodeError:
        log.warning(f"{LogColors.WARNING}Activity {activity_guid} has invalid JSON in Notes{LogColors.ENDC}")
        return True
    
    project_id = notes_dict.get('project_id')
    project_title = notes_dict.get('project_title', 'Knowledge Integration')
    session_number = notes_dict.get('session_number', 1)
    current_progress = notes_dict.get('current_progress', 0)
    building_name = notes_dict.get('building_name', 'House of Natural Sciences')
    kinos_model = notes_dict.get('kinos_model', 'local')
    
    log.info(f"  Integration session {session_number} for project: {project_title} ({current_progress}% complete)")
    
    # Get the project record
    project_record = None
    if project_id:
        try:
            project_record = tables['messages'].get(project_id)
        except Exception as e:
            log.error(f"  Error fetching project record: {e}")
    
    if not project_record:
        log.error(f"{LogColors.FAIL}Could not find project record for integration activity{LogColors.ENDC}")
        return False
    
    # Apply mood bonus for deep intellectual work
    try:
        citizen = tables['citizens'].get(activity_record['fields'].get('CitizenAirtableId'))
        current_mood = citizen['fields'].get('Mood', 50)
        
        # Integration work is deeply satisfying
        mood_change = 10  # High bonus for synthesis work
        new_mood = min(100, current_mood + mood_change)
        
        tables['citizens'].update(citizen['id'], {'Mood': new_mood})
        log.info(f"  Updated {citizen_username} mood: {current_mood} -> {new_mood} (+{mood_change} for knowledge integration)")
    except Exception as e:
        log.error(f"  Error updating mood: {e}")
    
    # Start async thread for knowledge integration
    integration_thread = threading.Thread(
        target=_integrate_knowledge_async,
        args=(tables, activity_record, citizen_username, project_record, session_number, building_name, kinos_model)
    )
    integration_thread.start()
    
    log.info(f"{LogColors.SUCCESS}Started integration thread {integration_thread.ident} for {citizen_username}'s session {session_number}{LogColors.ENDC}")
    
    log.info(f"{LogColors.SUCCESS}Knowledge integration activity {activity_guid} processed successfully{LogColors.ENDC}")
    return True
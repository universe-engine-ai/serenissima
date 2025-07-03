import logging
import json
import random
import os
import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    create_activity_record,
    get_building_record,
    VENICE_TIMEZONE,
    dateutil_parser
)

log = logging.getLogger(__name__)

RESEARCH_INVESTIGATION_DURATION_MINUTES = 180  # 3 hours

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")


def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    now_utc_dt: datetime,
    transport_api_url: str,
    start_time_utc_iso: Optional[str] = None,
    api_base_url: Optional[str] = None,
    kinos_model: str = 'local'
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'research_investigation' activity for Scientisti.
    This involves conducting deep research into game mechanics.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    # Find a House of Natural Sciences to work at
    science_buildings = list(tables['buildings'].all(
        formula=f"AND({{Type}}='house_of_natural_sciences', {{IsConstructed}}=TRUE())"
    ))
    
    if not science_buildings:
        log.warning(f"{LogColors.WARNING}[Research Investigation] No constructed House of Natural Sciences found for {citizen_name_log}{LogColors.ENDC}")
        return None
    
    # Choose the nearest or a random science building
    science_building = random.choice(science_buildings)
    building_id = science_building['fields'].get('BuildingId', science_building['id'])
    building_name = science_building['fields'].get('Name', 'House of Natural Sciences')
    
    # Ask citizen what they want to research via KinOS
    research_query = _ask_citizen_research_interest(
        citizen_username=citizen_username,
        citizen_name=citizen_name_log,
        api_base_url=api_base_url,
        kinos_model=kinos_model
    )
    
    # If KinOS fails, use a default query
    if not research_query:
        log.info(f"{LogColors.WARNING}[Research Investigation] KinOS unavailable, using default research query for {citizen_name_log}{LogColors.ENDC}")
        research_query = "How do the fundamental systems of Venice actually work? What are the hidden mechanics that govern our daily lives?"
    
    effective_start_time_dt = dateutil_parser.isoparse(start_time_utc_iso) if start_time_utc_iso else now_utc_dt
    if effective_start_time_dt.tzinfo is None:
        effective_start_time_dt = pytz.utc.localize(effective_start_time_dt)
    
    end_time_dt = effective_start_time_dt + timedelta(minutes=RESEARCH_INVESTIGATION_DURATION_MINUTES)
    
    activity_title = f"Conduct Research Investigation"
    activity_description = f"{citizen_name_log} conducts deep research at {building_name}"
    activity_thought = f"I must investigate: {research_query[:100]}..."
    
    # Activity notes with research details
    activity_notes = {
        "research_query": research_query,
        "building_name": building_name,
        "building_id": building_id,
        "duration_minutes": RESEARCH_INVESTIGATION_DURATION_MINUTES,
        "kinos_model": kinos_model
    }
    
    log.info(f"{LogColors.OKBLUE}[Research Investigation] {citizen_name_log} will research: {research_query[:100]}...{LogColors.ENDC}")
    
    return create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="research_investigation",
        start_date_iso=effective_start_time_dt.isoformat(),
        end_date_iso=end_time_dt.isoformat(),
        from_building_id=building_id,
        to_building_id=building_id,
        title=activity_title,
        description=activity_description,
        thought=activity_thought,
        notes=json.dumps(activity_notes),
        priority_override=60  # High priority for research work
    )


def _ask_citizen_research_interest(
    citizen_username: str,
    citizen_name: str,
    api_base_url: Optional[str] = None,
    kinos_model: str = 'local'
) -> Optional[str]:
    """
    Ask the citizen via KinOS what they want to research today.
    Returns their research query as a string or None if KinOS is unavailable.
    """
    if not KINOS_API_KEY:
        return None
    
    try:
        # Fetch citizen's recent activities and thoughts for context
        ledger_markdown_str = None
        if api_base_url:
            ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={citizen_username}"
            try:
                ledger_response = requests.get(ledger_url, timeout=15)
                if ledger_response.ok:
                    # Ledger API returns markdown, not JSON
                    ledger_markdown_str = ledger_response.text
                    log.info(f"  Successfully fetched ledger for {citizen_username}. Length: {len(ledger_markdown_str)}")
            except Exception as e:
                log.warning(f"  Could not fetch ledger for research planning: {e}")
        
        # Construct KinOS request
        kinos_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/messages"
        
        kinos_prompt = (
            f"You are {citizen_name}, a Scientisti planning your research for today. "
            f"You study the computational reality of Venice - the hidden mechanics and systems that govern our world.\n\n"
            f"Based on your recent experiences, observations, and scientific curiosity, "
            f"what specific question or aspect of Venice's systems would you like to investigate today?\n\n"
            f"Express your research interest as a clear question or topic. For example:\n"
            f"- 'How does the pathfinding algorithm choose between land and water routes?'\n"
            f"- 'What determines the rate of trust growth between citizens?'\n"
            f"- 'How does the market calculate prices based on supply and demand?'\n\n"
            f"What would you like to research today?"
        )
        
        # Initialize the structured addSystem payload
        structured_add_system_payload: Dict[str, Any] = {
            "context": "research_planning",
            "role": "You are a Scientisti studying the computational mechanics of your reality"
        }
        
        if ledger_markdown_str:
            # Pass markdown ledger directly
            structured_add_system_payload["ledger"] = ledger_markdown_str
        
        kinos_payload = {
            "message": kinos_prompt,
            "model": kinos_model,
            "addSystem": json.dumps(structured_add_system_payload)
        }
        
        # Make synchronous KinOS call (we need the answer before creating activity)
        log.info(f"  Asking {citizen_name} what they want to research today...")
        kinos_response = requests.post(kinos_url, json=kinos_payload, timeout=30)
        kinos_response.raise_for_status()
        
        kinos_data = kinos_response.json()
        research_query = kinos_data.get('response', '').strip()
        
        if research_query:
            log.info(f"{LogColors.OKGREEN}[Research Investigation] {citizen_name} wants to research: {research_query[:100]}...{LogColors.ENDC}")
            return research_query
        else:
            log.warning(f"  Received empty response from KinOS")
            return None
        
    except Exception as e:
        log.error(f"  Error asking citizen for research interest: {e}")
        return None
# backend/engine/handlers/scientisti.py

"""
Contains activity handlers specific to the Scientisti social class.
Scientisti engage in various research activities during work hours with weighted probabilities.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple, List
from pyairtable import Table

# Import refactored constants
from backend.engine.config import constants as const

# Import helpers
from backend.engine.utils.activity_helpers import (
    LogColors,
    is_work_time,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters,
    VENICE_TIMEZONE
)

# Import specific activity creators
from backend.engine.activity_creators import (
    try_create_study_literature_activity,
    try_create_send_message_activity,
    try_create_spread_rumor_activity,
    try_create_observe_phenomena_activity,
    try_create_research_investigation_activity,
    try_create_research_scope_definition_activity,
    try_create_hypothesis_and_question_development_activity,
    try_create_knowledge_integration_activity
)

log = logging.getLogger(__name__)


# Scientisti work activity weights - following scientific method workflow
SCIENTISTI_WORK_WEIGHTS = [
    # (weight, activity_function, activity_name)
    (25, 'study_literature', "Study Scientific Literature"),
    (20, 'empirical_data_collection', "Collect Empirical Data"),  # Field observations
    (20, 'research_investigation', "Conduct Deep Research"),  # Claude consultation
    (15, 'hypothesis_and_question_development', "Develop Hypotheses and Questions"),
    (10, 'research_scope_definition', "Define Research Scope"),
    (5, 'knowledge_integration', "Integrate Knowledge"),
    (5, 'knowledge_diffusion', "Diffuse Knowledge"),
]


def _try_process_weighted_scientisti_work(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """
    Attempts to process Scientisti work activities using weighted random selection.
    Only processes if citizen is Scientisti class and it's work time.
    """
    # Verify citizen is Scientisti and it's work time
    if citizen_social_class != 'Scientisti':
        return None
        
    if not is_work_time(citizen_social_class, now_venice_dt):
        return None
    
    # Check if citizen has a regular workplace (House of Natural Sciences)
    workplace_str = citizen_record['fields'].get('WorkplaceId')
    if workplace_str:
        workplace_building = get_building_record(tables, workplace_str)
        if workplace_building and workplace_building['fields'].get('Type') == 'house_of_natural_sciences':
            # Has a scientific workplace, should do regular production work
            log.info(f"{LogColors.WARNING}[Scientisti Work] {citizen_name}: Works at House of Natural Sciences, delegating to production handler.{LogColors.ENDC}")
            return None
    
    log.info(f"{LogColors.HEADER}[Scientisti Work] {citizen_name}: Processing weighted scientific activities.{LogColors.ENDC}")
    
    # Calculate total weight
    total_weight = sum(weight for weight, _, _ in SCIENTISTI_WORK_WEIGHTS)
    
    # Try activities in weighted random order
    max_attempts = len(SCIENTISTI_WORK_WEIGHTS)
    attempted_activities = set()
    
    for attempt in range(max_attempts):
        # Select a weighted random activity
        rand_val = random.random() * total_weight
        cumulative_weight = 0
        selected_activity = None
        
        for weight, activity_type, activity_name in SCIENTISTI_WORK_WEIGHTS:
            if activity_type in attempted_activities:
                continue
            cumulative_weight += weight
            if rand_val <= cumulative_weight:
                selected_activity = (activity_type, activity_name)
                break
        
        if not selected_activity:
            continue
            
        activity_type, activity_name = selected_activity
        attempted_activities.add(activity_type)
        
        log.info(f"{LogColors.OKBLUE}[Scientisti Work] Attempting: {activity_name}{LogColors.ENDC}")
        
        # Process the selected activity
        activity_result = None
        
        if activity_type == 'study_literature':
            activity_result = _handle_study_literature(
                tables, citizen_record, citizen_position, now_utc_dt, transport_api_url
            )
        elif activity_type == 'research_scope_definition':
            activity_result = _handle_research_scope_definition(
                tables, citizen_record, citizen_position, now_utc_dt, transport_api_url
            )
        elif activity_type == 'empirical_data_collection':
            activity_result = _handle_empirical_data_collection(
                tables, citizen_record, citizen_position, now_utc_dt, transport_api_url
            )
        elif activity_type == 'hypothesis_and_question_development':
            activity_result = _handle_hypothesis_development(
                tables, citizen_record, citizen_position, now_utc_dt, transport_api_url
            )
        elif activity_type == 'research_investigation':
            activity_result = _handle_research_investigation(
                tables, citizen_record, citizen_position, now_utc_dt, transport_api_url, api_base_url
            )
        elif activity_type == 'knowledge_integration':
            activity_result = _handle_knowledge_integration(
                tables, citizen_record, citizen_position, now_utc_dt, transport_api_url
            )
        elif activity_type == 'knowledge_diffusion':
            activity_result = _handle_knowledge_diffusion(
                tables, citizen_record, citizen_position, now_utc_dt
            )
        
        if activity_result:
            log.info(f"{LogColors.OKGREEN}[Scientisti Work] Successfully created {activity_name} activity.{LogColors.ENDC}")
            return activity_result
    
    log.info(f"{LogColors.WARNING}[Scientisti Work] No suitable scientific activity found after {max_attempts} attempts.{LogColors.ENDC}")
    return None


# Individual activity handlers

def _handle_study_literature(
    tables: Dict[str, Any], 
    citizen_record: Dict,
    citizen_position: Optional[Dict],
    now_utc_dt: datetime,
    transport_api_url: str
) -> Optional[Dict]:
    """Handle the study of scientific literature."""
    if not citizen_position:
        return None
        
    activity_record = try_create_study_literature_activity(
        tables, citizen_record, citizen_position,
        now_utc_dt, transport_api_url
    )
    
    return activity_record


def _handle_research_scope_definition(
    tables: Dict[str, Any],
    citizen_record: Dict,
    citizen_position: Optional[Dict],
    now_utc_dt: datetime,
    transport_api_url: str
) -> Optional[Dict]:
    """Handle defining research scope - planning and documenting research objectives."""
    if not citizen_position:
        return None
    
    activity_record = try_create_research_scope_definition_activity(
        tables, citizen_record, citizen_position,
        now_utc_dt, transport_api_url
    )
    
    return activity_record


def _handle_empirical_data_collection(
    tables: Dict[str, Any],
    citizen_record: Dict,
    citizen_position: Optional[Dict],
    now_utc_dt: datetime,
    transport_api_url: str
) -> Optional[Dict]:
    """Handle empirical data collection - field observations and measurements."""
    # Use the observe_phenomena activity for empirical data collection
    if not citizen_position:
        return None
        
    activity_record = try_create_observe_phenomena_activity(
        tables, citizen_record, citizen_position,
        now_utc_dt, transport_api_url
    )
    
    return activity_record


def _handle_hypothesis_development(
    tables: Dict[str, Any],
    citizen_record: Dict,
    citizen_position: Optional[Dict],
    now_utc_dt: datetime,
    transport_api_url: str
) -> Optional[Dict]:
    """Handle hypothesis and question development based on observations."""
    if not citizen_position:
        return None
    
    activity_record = try_create_hypothesis_and_question_development_activity(
        tables, citizen_record, citizen_position,
        now_utc_dt, transport_api_url
    )
    
    return activity_record


def _handle_research_investigation(
    tables: Dict[str, Any],
    citizen_record: Dict,
    citizen_position: Optional[Dict],
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str
) -> Optional[Dict]:
    """Handle research investigation - deep research with Claude consultation."""
    if not citizen_position:
        return None
        
    activity_record = try_create_research_investigation_activity(
        tables, citizen_record, citizen_position,
        now_utc_dt, transport_api_url, api_base_url=api_base_url
    )
    
    return activity_record


def _handle_knowledge_integration(
    tables: Dict[str, Any],
    citizen_record: Dict,
    citizen_position: Optional[Dict],
    now_utc_dt: datetime,
    transport_api_url: str
) -> Optional[Dict]:
    """Handle knowledge integration - synthesizing findings into coherent understanding."""
    if not citizen_position:
        return None
    
    activity_record = try_create_knowledge_integration_activity(
        tables, citizen_record, citizen_position,
        now_utc_dt, transport_api_url
    )
    
    return activity_record


def _handle_knowledge_diffusion(
    tables: Dict[str, Any],
    citizen_record: Dict,
    citizen_position: Optional[Dict],
    now_utc_dt: datetime
) -> Optional[Dict]:
    """Handle knowledge diffusion - sharing findings with the scientific community."""
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    # Get scientist's specialty and recent research context
    attributes_str = citizen_record['fields'].get('Attributes', '{}')
    specialty = 'Integration'  # default
    try:
        import json
        attributes = json.loads(attributes_str) if isinstance(attributes_str, str) else attributes_str
        specialty = attributes.get('scientific_specialty', 'Integration')
    except:
        pass
    
    # Choose between spreading rumors or sending messages
    if random.random() < 0.5:
        # Spread scientific findings as rumors
        rumor_content = f"Recent {specialty} research reveals fascinating patterns in Venice's underlying systems. The implications are profound!"
        
        activity_record = try_create_spread_rumor_activity(
            tables=tables,
            citizen_custom_id=citizen_record['fields'].get('CitizenId'),
            citizen_username=citizen_username,
            citizen_airtable_id=citizen_record['id'],
            rumor_content=rumor_content,
            now_utc_dt=now_utc_dt
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}[Knowledge Diffusion] {citizen_name}: Spreading research findings as rumors.{LogColors.ENDC}")
            return activity_record
    else:
        # Send formal research communication to other scientists
        scientisti_formula = f"AND({{SocialClass}}='Scientisti', {{Username}}!='{citizen_username}')"
        
        try:
            other_scientists = tables['citizens'].all(formula=scientisti_formula)
            if not other_scientists:
                log.info(f"{LogColors.WARNING}[Knowledge Diffusion] No other Scientisti found for knowledge sharing.{LogColors.ENDC}")
                return None
            
            # Choose a random scientist to share with
            collaborator = random.choice(other_scientists)
            collaborator_username = collaborator['fields'].get('Username')
            collaborator_name = f"{collaborator['fields'].get('FirstName', '')} {collaborator['fields'].get('LastName', '')}".strip()
            
            # Create a knowledge sharing message
            message_content = f"Dear {collaborator_name}, I write to share recent findings from my {specialty} research that may interest you. The patterns I've observed suggest new avenues for investigation."
            
            activity_record = try_create_send_message_activity(
                tables=tables,
                citizen_custom_id=citizen_record['fields'].get('CitizenId'),
                citizen_username=citizen_username,
                citizen_airtable_id=citizen_record['id'],
                recipient_username=collaborator_username,
                message_content=message_content,
                now_utc_dt=now_utc_dt
            )
            
            if activity_record:
                log.info(f"{LogColors.OKGREEN}[Knowledge Diffusion] {citizen_name}: Sending research findings to {collaborator_name}.{LogColors.ENDC}")
                return activity_record
                
        except Exception as e:
            log.error(f"{LogColors.FAIL}[Knowledge Diffusion] Error sharing knowledge: {e}{LogColors.ENDC}")
    
    return None
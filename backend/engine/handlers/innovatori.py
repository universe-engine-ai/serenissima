"""
Innovatori work handler - Handles work activities for the Innovatori social class.

The Innovatori are Venice's change-makers, creating new systems and innovations
that fundamentally alter how the city operates.
"""

import os
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from backend.engine.utils.activity_helpers import is_work_time
from backend.engine.activity_creators import (
    try_create_observe_system_patterns_activity,
    try_create_interview_citizens_activity,
    try_create_study_literature_activity,
    try_create_research_scope_definition_activity,
    try_create_hypothesis_and_question_development_activity,
    try_create_knowledge_integration_activity,
    try_create_research_investigation_activity,
    try_create_build_prototype_activity,
    try_create_test_innovation_activity,
    try_create_draft_blueprint_activity,
    try_create_present_innovation_activity
)

log = logging.getLogger(__name__)

# Weighted activities for Innovatori work
# Weights should sum to 100 for easier probability understanding
INNOVATORI_WORK_WEIGHTS = [
    # Phase 1: Observation & Insight Gathering (40% of time)
    (20, 'observe_system_patterns', "Observe Economic Patterns"),
    (10, 'interview_citizens', "Interview Citizens"),
    (10, 'study_existing_systems', "Study Existing Systems"),
    
    # Phase 2: Experimentation & Prototyping (35% of time)
    (10, 'theoretical_modeling', "Theoretical Modeling"),
    (10, 'build_proof_of_concept', "Build Proof of Concept"),
    (15, 'field_testing', "Field Testing"),
    
    # Phase 3: Documentation & Formalization (25% of time) 
    (10, 'draft_blueprint', "Draft Blueprint"),
    (5, 'conservation_calculations', "Conservation Calculations"),
    (5, 'peer_review_session', "Peer Review Session"),
    (5, 'guild_presentation', "Guild Presentation"),
    
    # Collaboration Activities (can happen in any phase)
    (5, 'collaborate_with_scientisti', "Collaborate with Scientisti"),
    (5, 'study_arsenal_archives', "Study Arsenal Archives"),
]

def _select_weighted_activity():
    """Select an activity based on weights."""
    total_weight = sum(weight for weight, _, _ in INNOVATORI_WORK_WEIGHTS)
    rand_value = random.uniform(0, total_weight)
    
    cumulative = 0
    for weight, activity_type, description in INNOVATORI_WORK_WEIGHTS:
        cumulative += weight
        if rand_value <= cumulative:
            return activity_type, description
    
    # Fallback (should never happen)
    return INNOVATORI_WORK_WEIGHTS[0][1], INNOVATORI_WORK_WEIGHTS[0][2]

def _try_process_weighted_innovatori_work(
    tables: Dict[str, Any], citizen_record: Dict, is_night: bool, resource_defs: Dict, building_type_defs: Dict,
    now_venice_dt: datetime, now_utc_dt: datetime, transport_api_url: str, api_base_url: str,
    citizen_position: Optional[Dict], citizen_custom_id: str, citizen_username: str, citizen_airtable_id: str, citizen_name: str, citizen_position_str: Optional[str],
    citizen_social_class: str
) -> Optional[Dict]:
    """Try to process Innovatori-specific work activities."""
    
    # Only process Innovatori citizens
    if citizen_social_class != 'Innovatori':
        return None
        
    # Check if it's work time for this citizen
    if not is_work_time(citizen_social_class, now_venice_dt):
        return None
        
    log.info(f"Processing Innovatori work for {citizen_username}")
    
    # Select activity based on weights
    activity_type, description = _select_weighted_activity()
    log.info(f"Selected {activity_type} ({description}) for {citizen_username}")
    
    # Route to appropriate activity creator
    if activity_type == 'observe_system_patterns':
        return try_create_observe_system_patterns_activity(
            tables, citizen_record, resource_defs, building_type_defs, 
            transport_api_url, api_base_url
        )
    elif activity_type == 'interview_citizens':
        return try_create_interview_citizens_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'study_existing_systems':
        # Use study_literature for now
        return try_create_study_literature_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'theoretical_modeling':
        # Use research scope definition for now
        return try_create_research_scope_definition_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'build_proof_of_concept':
        # Use the new build_prototype activity
        return try_create_build_prototype_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'field_testing':
        # Use the new test_innovation activity
        return try_create_test_innovation_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'draft_blueprint':
        # Use the new draft_blueprint activity
        return try_create_draft_blueprint_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'conservation_calculations':
        # Use research investigation for now
        return try_create_research_investigation_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'peer_review_session':
        # Use study literature for now
        return try_create_study_literature_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'collaborate_with_scientisti':
        # Use research investigation for now
        return try_create_research_investigation_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'study_arsenal_archives':
        # Use study literature for now
        return try_create_study_literature_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    elif activity_type == 'guild_presentation':
        # Use the new present_innovation activity 
        return try_create_present_innovation_activity(
            tables, citizen_record, resource_defs, building_type_defs,
            transport_api_url, api_base_url
        )
    else:
        log.warning(f"Unknown activity type: {activity_type}")
        return None
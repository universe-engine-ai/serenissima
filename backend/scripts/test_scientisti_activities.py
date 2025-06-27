#!/usr/bin/env python3
"""
Test script for Scientisti research activities with immediate processing.
This script creates test activities and processes them directly, waiting for GPU/KinOS operations.

For training purposes, use --model claude-3-7-sonnet-latest to get higher quality responses:
    python3 scripts/test_scientisti_activities.py --model claude-3-7-sonnet-latest --activity all

Or use the convenience script:
    ./scripts/train_scientisti_with_sonnet.sh [username]
"""

import sys
import os
import json
import time
from datetime import datetime, timezone
import argparse
from typing import Dict, Any, Optional

# Add project root to sys.path to handle backend imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add backend directory to path as well
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import activity creators
from engine.activity_creators import (
    try_create_study_literature_activity,
    try_create_observe_phenomena_activity,
    try_create_research_investigation_activity,
    try_create_research_scope_definition_activity,
    try_create_hypothesis_and_question_development_activity,
    try_create_knowledge_integration_activity
)

# Import activity processors
from engine.activity_processors import (
    study_literature_processor,
    observe_phenomena_processor,
    research_investigation_processor,
    research_scope_definition_processor,
    hypothesis_and_question_development_processor,
    knowledge_integration_processor
)

# Import handlers
from engine.handlers.scientisti import _try_process_weighted_scientisti_work

# Import helpers
from engine.utils.activity_helpers import get_tables, dateutil_parser, LogColors
# Load building and resource definitions directly
import json
import glob

def get_building_type_defs():
    """Load building type definitions from JSON files"""
    building_defs = {}
    building_files = glob.glob(os.path.join(PROJECT_ROOT, 'data/buildings/*.json'))
    for file_path in building_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            building_data = json.load(f)
            building_type = building_data.get('type', os.path.basename(file_path).replace('.json', ''))
            building_defs[building_type] = building_data
    return building_defs

def get_resource_defs():
    """Load resource definitions from JSON files"""
    resource_defs = {}
    resource_files = glob.glob(os.path.join(PROJECT_ROOT, 'data/resources/*.json'))
    for file_path in resource_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            resource_data = json.load(f)
            resource_type = resource_data.get('type', os.path.basename(file_path).replace('.json', ''))
            resource_defs[resource_type] = resource_data
    return resource_defs

# Constants
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TRANSPORT_API_URL = os.getenv("TRANSPORT_API_URL", "https://serenissima.ai/api/transport")
API_BASE_URL = os.getenv("API_BASE_URL", "https://serenissima.ai")

def get_scientisti_citizens(tables: Dict[str, Any]) -> list:
    """Get all Scientisti citizens"""
    try:
        scientisti = list(tables['citizens'].all(formula="{SocialClass}='Scientisti'"))
        return scientisti
    except Exception as e:
        print(f"Error fetching Scientisti: {e}")
        return []

def get_citizen_position(citizen_record: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Extract citizen position from record"""
    position_str = citizen_record['fields'].get('Position')
    if not position_str:
        return None
    
    try:
        return json.loads(position_str)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Warning: Could not parse position: {e}")
        return None
    except Exception as e:
        print(f"  ⚠️  Warning: Unexpected error parsing position: {e}")
        return None

def test_study_literature(tables: Dict[str, Any], citizen_record: Dict[str, Any], process_immediately: bool = True) -> Optional[Dict[str, Any]]:
    """Test study literature activity creation and optionally process it immediately"""
    print(f"\n📚 Testing Study Literature for {citizen_record['fields'].get('Username')}")
    
    position = get_citizen_position(citizen_record)
    if not position:
        print("  ❌ No position found")
        return None
    
    # Create the activity
    activity = try_create_study_literature_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=position,
        now_utc_dt=datetime.now(timezone.utc),
        transport_api_url=TRANSPORT_API_URL
    )
    
    if activity:
        # Debug: Show all fields
        print(f"  ✅ Created study activity: {activity['fields'].get('Title')}")
        print(f"     Activity Type: {activity['fields'].get('Type')}")
        print(f"     Duration: {activity['fields'].get('StartDate')} to {activity['fields'].get('EndDate')}")
        # Debug: Show raw title if different
        if 'Title' in activity['fields']:
            print(f"     Raw Title in fields: '{activity['fields']['Title']}'")
        
        # Parse notes to see which book was selected
        try:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            # Check if this is a goto_location activity
            if activity['fields'].get('Type') == 'goto_location':
                print(f"     📍 Created travel activity first (citizen not at study location)")
                # Debug: print available keys
                if 'action_details' in notes:
                    action_details = notes.get('action_details', {})
                    if 'notes_for_chained_activity' in action_details:
                        chained_notes = action_details.get('notes_for_chained_activity', {})
                        print(f"     Book (will study): {chained_notes.get('book_title', 'Unknown')}")
                        print(f"     Specialty: {chained_notes.get('scientific_specialty', 'Unknown')}")
                    else:
                        print(f"     Debug: action_details keys: {list(action_details.keys())[:5]}")
                else:
                    print(f"     Debug: notes keys: {list(notes.keys())[:5]}")
            else:
                print(f"     Book: {notes.get('book_title', 'Unknown')}")
                print(f"     Specialty: {notes.get('scientific_specialty', 'Unknown')}")
        except json.JSONDecodeError as e:
            print(f"     ⚠️  Warning: Could not parse Notes field: {e}")
            notes = {}
        
        if process_immediately:
            print("  ⏳ Processing activity immediately...")
            # Update activity to Pending status
            tables['activities'].update(activity['id'], {'Status': 'Pending'})
            
            # Process the activity
            success = study_literature_processor.process(
                tables=tables,
                activity_record=activity,
                building_type_defs=get_building_type_defs(),
                resource_defs=get_resource_defs(),
                api_base_url=API_BASE_URL
            )
            
            if success:
                print("  ✅ Activity processed successfully")
                # Mark as completed
                tables['activities'].update(activity['id'], {'Status': 'Completed'})
            else:
                print("  ❌ Activity processing failed")
                tables['activities'].update(activity['id'], {'Status': 'Failed'})
    else:
        print("  ❌ Failed to create study activity")
    
    return activity

def test_observe_phenomena(tables: Dict[str, Any], citizen_record: Dict[str, Any], process_immediately: bool = True) -> Optional[Dict[str, Any]]:
    """Test observe phenomena activity creation and optionally process it immediately"""
    print(f"\n🔭 Testing Observe Phenomena for {citizen_record['fields'].get('Username')}")
    
    position = get_citizen_position(citizen_record)
    if not position:
        print("  ❌ No position found")
        return None
    
    # Create the activity
    activity = try_create_observe_phenomena_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=position,
        now_utc_dt=datetime.now(timezone.utc),
        transport_api_url=TRANSPORT_API_URL
    )
    
    if activity:
        print(f"  ✅ Created observation activity: {activity['fields'].get('Title')}")
        
        # Parse notes to see which site was selected
        try:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            # Check if it's a travel activity
            if activity['fields'].get('Type') == 'goto_position':
                print("     📍 Created travel activity first (citizen not at observation site)")
                # Debug: print notes structure
                if 'action_details' in notes:
                    action_details = notes.get('action_details', {})
                    if 'notes_for_chained_activity' in action_details:
                        chained_notes = action_details.get('notes_for_chained_activity', {})
                        print(f"     Site: {chained_notes.get('site_name', 'Unknown')}")
                        print(f"     Phenomena: {chained_notes.get('phenomena', 'Unknown')}")
                    else:
                        print(f"     Debug: action_details keys: {list(action_details.keys())[:5]}")
                else:
                    # Maybe the chained notes are at the top level
                    print(f"     Debug: notes keys: {list(notes.keys())[:5]}")
                    if 'site_name' in notes:
                        print(f"     Site: {notes.get('site_name', 'Unknown')}")
                        print(f"     Phenomena: {notes.get('phenomena', 'Unknown')}")
                return activity  # Can't process travel activity with observation processor
            else:
                print(f"     Site: {notes.get('site_name', 'Unknown')}")
                print(f"     Phenomena: {notes.get('phenomena', 'Unknown')}")
        except json.JSONDecodeError as e:
            print(f"     ⚠️  Warning: Could not parse Notes field: {e}")
            notes = {}
        
        if process_immediately:
            print("  ⏳ Processing activity immediately...")
            # Update activity to Pending status
            tables['activities'].update(activity['id'], {'Status': 'Pending'})
            
            # Process the activity
            success = observe_phenomena_processor.process(
                tables=tables,
                activity_record=activity,
                building_type_defs=get_building_type_defs(),
                resource_defs=get_resource_defs(),
                api_base_url=API_BASE_URL
            )
            
            if success:
                print("  ✅ Activity processed successfully")
                # Mark as completed
                tables['activities'].update(activity['id'], {'Status': 'Completed'})
            else:
                print("  ❌ Activity processing failed")
                tables['activities'].update(activity['id'], {'Status': 'Failed'})
    else:
        print("  ❌ Failed to create observation activity")
    
    return activity

def test_research_investigation(tables: Dict[str, Any], citizen_record: Dict[str, Any], process_immediately: bool = True, wait_for_async: bool = True, kinos_model: str = 'local') -> Optional[Dict[str, Any]]:
    """Test research investigation activity creation and optionally process it immediately"""
    print(f"\n🔬 Testing Research Investigation for {citizen_record['fields'].get('Username')}")
    
    position = get_citizen_position(citizen_record)
    if not position:
        print("  ❌ No position found")
        return None
    
    # Create the activity
    activity = try_create_research_investigation_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=position,
        now_utc_dt=datetime.now(timezone.utc),
        transport_api_url=TRANSPORT_API_URL,
        api_base_url=API_BASE_URL,
        kinos_model=kinos_model
    )
    
    if activity:
        print(f"  ✅ Created research activity: {activity['fields'].get('Title')}")
        
        # Parse notes to see research query
        try:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            print(f"     Research Query: {notes.get('research_query', 'Unknown')[:100]}...")
            print(f"     Building: {notes.get('building_name', 'Unknown')}")
        except json.JSONDecodeError as e:
            print(f"     Warning: Could not parse Notes field: {e}")
            print(f"     Raw Notes: {activity['fields'].get('Notes', '')[:100]}...")
        print("     Note: KinOS will be called to determine research topic")
        
        if process_immediately:
            print("  ⏳ Processing activity immediately...")
            # Update activity to Pending status
            tables['activities'].update(activity['id'], {'Status': 'Pending'})
            
            # Process the activity
            success = research_investigation_processor.process(
                tables=tables,
                activity_record=activity,
                building_type_defs=get_building_type_defs(),
                resource_defs=get_resource_defs(),
                api_base_url=API_BASE_URL
            )
            
            if success:
                print("  ✅ Activity processing initiated (async threads started)")
                
                if wait_for_async:
                    print("  ⏳ Waiting for KinOS and Claude consultations (up to 300s)...")
                    wait_for_research_completion(tables, activity['id'], timeout=300)
                
                # Mark as completed
                tables['activities'].update(activity['id'], {'Status': 'Completed'})
            else:
                print("  ❌ Activity processing failed")
                tables['activities'].update(activity['id'], {'Status': 'Failed'})
    else:
        print("  ❌ Failed to create research activity")
    
    return activity

def test_research_scope_definition(tables: Dict[str, Any], citizen_record: Dict[str, Any], process_immediately: bool = True, wait_for_async: bool = True, kinos_model: str = 'local') -> Optional[Dict[str, Any]]:
    """Test research scope definition activity creation and optionally process it immediately"""
    print(f"\n📋 Testing Research Scope Definition for {citizen_record['fields'].get('Username')}")
    
    position = get_citizen_position(citizen_record)
    if not position:
        print("  ❌ No position found")
        return None
    
    # Create the activity
    activity = try_create_research_scope_definition_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=position,
        now_utc_dt=datetime.now(timezone.utc),
        transport_api_url=TRANSPORT_API_URL,
        kinos_model=kinos_model
    )
    
    if activity:
        print(f"  ✅ Created scope definition activity: {activity['fields'].get('Title')}")
        
        # Parse notes to see research scope
        try:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            print(f"     Research Scope: {notes.get('research_scope', 'Unknown')[:100]}...")
            print(f"     Building: {notes.get('building_name', 'Unknown')}")
            print("     Note: KinOS will be called to define research objectives")
        except json.JSONDecodeError as e:
            print(f"     ⚠️  Warning: Could not parse Notes field: {e}")
            notes = {}
        
        if process_immediately:
            print("  ⏳ Processing activity immediately...")
            # Update activity to Pending status
            tables['activities'].update(activity['id'], {'Status': 'Pending'})
            
            # Process the activity
            success = research_scope_definition_processor.process(
                tables=tables,
                activity_record=activity,
                building_type_defs=get_building_type_defs(),
                resource_defs=get_resource_defs(),
                api_base_url=API_BASE_URL
            )
            
            if success:
                print("  ✅ Activity processing initiated (async threads started)")
                
                if wait_for_async:
                    print("  ⏳ Waiting for KinOS reflection (up to 120s)...")
                    wait_for_activity_completion(tables, activity['id'], timeout=120, activity_type='research_planning')
                
                # Mark as completed
                tables['activities'].update(activity['id'], {'Status': 'Completed'})
            else:
                print("  ❌ Activity processing failed")
                tables['activities'].update(activity['id'], {'Status': 'Failed'})
    else:
        print("  ❌ Failed to create scope definition activity")
    
    return activity

def test_hypothesis_development(tables: Dict[str, Any], citizen_record: Dict[str, Any], process_immediately: bool = True, wait_for_async: bool = True, kinos_model: str = 'local') -> Optional[Dict[str, Any]]:
    """Test hypothesis and question development activity creation and optionally process it immediately"""
    print(f"\n🧪 Testing Hypothesis Development for {citizen_record['fields'].get('Username')}")
    
    position = get_citizen_position(citizen_record)
    if not position:
        print("  ❌ No position found")
        return None
    
    # Create the activity
    activity = try_create_hypothesis_and_question_development_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=position,
        now_utc_dt=datetime.now(timezone.utc),
        transport_api_url=TRANSPORT_API_URL,
        kinos_model=kinos_model
    )
    
    if activity:
        print(f"  ✅ Created hypothesis development activity: {activity['fields'].get('Title')}")
        
        # Parse notes to see hypothesis
        try:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            print(f"     Hypothesis: {notes.get('hypothesis', 'Unknown')[:100]}...")
            questions = notes.get('research_questions', [])
            if questions:
                print(f"     Research Questions ({len(questions)}):")
                for i, q in enumerate(questions[:3]):
                    print(f"       {i+1}. {q}")
            print(f"     Building: {notes.get('building_name', 'Unknown')}")
        except json.JSONDecodeError as e:
            print(f"     ⚠️  Warning: Could not parse Notes field: {e}")
            notes = {}
        
        if process_immediately:
            print("  ⏳ Processing activity immediately...")
            # Update activity to Pending status
            tables['activities'].update(activity['id'], {'Status': 'Pending'})
            
            # Process the activity
            success = hypothesis_and_question_development_processor.process(
                tables=tables,
                activity_record=activity,
                building_type_defs=get_building_type_defs(),
                resource_defs=get_resource_defs(),
                api_base_url=API_BASE_URL
            )
            
            if success:
                print("  ✅ Activity processing initiated (async threads started)")
                
                if wait_for_async:
                    print("  ⏳ Waiting for KinOS reflection (up to 120s)...")
                    wait_for_activity_completion(tables, activity['id'], timeout=120, activity_type='hypothesis')
                
                # Mark as completed
                tables['activities'].update(activity['id'], {'Status': 'Completed'})
            else:
                print("  ❌ Activity processing failed")
                tables['activities'].update(activity['id'], {'Status': 'Failed'})
    else:
        print("  ❌ Failed to create hypothesis development activity")
    
    return activity

def test_knowledge_integration(tables: Dict[str, Any], citizen_record: Dict[str, Any], process_immediately: bool = True, wait_for_async: bool = True, kinos_model: str = 'local') -> Optional[Dict[str, Any]]:
    """Test knowledge integration activity creation and optionally process it immediately"""
    print(f"\n🧩 Testing Knowledge Integration for {citizen_record['fields'].get('Username')}")
    
    position = get_citizen_position(citizen_record)
    if not position:
        print("  ❌ No position found")
        return None
    
    # Create the activity
    activity = try_create_knowledge_integration_activity(
        tables=tables,
        citizen_record=citizen_record,
        citizen_position=position,
        now_utc_dt=datetime.now(timezone.utc),
        transport_api_url=TRANSPORT_API_URL,
        kinos_model=kinos_model
    )
    
    if activity:
        print(f"  ✅ Created knowledge integration activity: {activity['fields'].get('Title')}")
        
        # Parse notes to see project details
        try:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            print(f"     Project: {notes.get('project_title', 'Unknown')}")
            print(f"     Session: {notes.get('session_number', 1)}")
            print(f"     Progress: {notes.get('current_progress', 0)}%")
            print(f"     New Project: {notes.get('is_new_project', False)}")
            print(f"     Building: {notes.get('building_name', 'Unknown')}")
        except json.JSONDecodeError as e:
            print(f"     ⚠️  Warning: Could not parse Notes field: {e}")
            notes = {}
        
        if process_immediately:
            print("  ⏳ Processing activity immediately...")
            # Update activity to Pending status
            tables['activities'].update(activity['id'], {'Status': 'Pending'})
            
            # Process the activity
            success = knowledge_integration_processor.process(
                tables=tables,
                activity_record=activity,
                building_type_defs=get_building_type_defs(),
                resource_defs=get_resource_defs(),
                api_base_url=API_BASE_URL
            )
            
            if success:
                print("  ✅ Activity processing initiated (async threads started)")
                
                if wait_for_async:
                    print("  ⏳ Waiting for integration session (up to 180s)...")
                    wait_for_integration_completion(tables, activity['id'], notes.get('project_id'), timeout=180)
                
                # Mark as completed
                tables['activities'].update(activity['id'], {'Status': 'Completed'})
            else:
                print("  ❌ Activity processing failed")
                tables['activities'].update(activity['id'], {'Status': 'Failed'})
    else:
        print("  ❌ Failed to create knowledge integration activity")
    
    return activity

def wait_for_integration_completion(tables: Dict[str, Any], activity_id: str, project_id: str, timeout: int = 180):
    """Wait for knowledge integration session to complete"""
    start_time = time.time()
    last_notes_state = ""
    last_project_state = ""
    
    while time.time() - start_time < timeout:
        try:
            # Fetch current activity state
            activity = tables['activities'].get(activity_id)
            notes_str = activity['fields'].get('Notes', '{}')
            
            # Check if notes have changed
            if notes_str != last_notes_state:
                last_notes_state = notes_str
                try:
                    notes = json.loads(notes_str)
                except json.JSONDecodeError as e:
                    print(f"\n  ⚠️  Warning: Could not parse Notes field: {e}")
                    notes = {}
                    continue
                
                # Check for completion indicators
                if notes.get('session_completed'):
                    print(f"  ✅ Integration session completed!")
                    
                    if notes.get('new_insights'):
                        print(f"  💡 New insights gained:")
                        for insight in notes['new_insights']:
                            print(f"     - {insight[:150]}...")
                    
                    if notes.get('project_progress'):
                        print(f"  📊 Project progress: {notes['project_progress']}%")
                    
                    if notes.get('kinos_reflection'):
                        print(f"  🧠 Session reflection: {notes['kinos_reflection'][:200]}...")
                    
                    # Check for session thought
                    thoughts = list(tables['thoughts'].all(
                        formula=f"AND({{Citizen}}='{activity['fields'].get('Citizen')}', {{Type}}='integration_session', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'minutes') < 5)",
                        max_records=1
                    ))
                    if thoughts:
                        print(f"  📝 Session thought created")
                    
                    return True
            
            # Also check project progress
            if project_id:
                try:
                    project = tables['thoughts'].get(project_id)
                    try:
                        project_context = json.loads(project['fields'].get('Context', '{}'))
                    except json.JSONDecodeError as e:
                        print(f"\n  ⚠️  Warning: Could not parse project Context: {e}")
                        project_context = {}
                    
                    if json.dumps(project_context) != last_project_state:
                        last_project_state = json.dumps(project_context)
                        print(f"  📈 Project updated: {project_context.get('progress_percentage', 0)}% complete")
                        
                        if project_context.get('status') == 'completed':
                            print(f"  🎉 Project COMPLETED!")
                            # Check for synthesis thought
                            synthesis = list(tables['thoughts'].all(
                                formula=f"AND({{Citizen}}='{activity['fields'].get('Citizen')}', {{Type}}='knowledge_synthesis', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'minutes') < 5)",
                                max_records=1
                            ))
                            if synthesis:
                                print(f"  📜 Final synthesis created!")
                except:
                    pass
            
            # Show progress
            elapsed = int(time.time() - start_time)
            print(f"  ⏳ Waiting for integration session... {elapsed}s / {timeout}s", end='\r')
            time.sleep(5)
            
        except Exception as e:
            print(f"\n  ❌ Error checking activity: {e}")
            time.sleep(5)
    
    print(f"\n  ⏰ Timeout reached after {timeout} seconds")
    return False

def wait_for_activity_completion(tables: Dict[str, Any], activity_id: str, timeout: int = 120, activity_type: str = 'generic'):
    """Wait for async threads to complete by monitoring activity notes and thoughts"""
    start_time = time.time()
    last_notes_state = ""
    
    while time.time() - start_time < timeout:
        try:
            # Fetch current activity state
            activity = tables['activities'].get(activity_id)
            notes_str = activity['fields'].get('Notes', '{}')
            
            # Check if notes have changed
            if notes_str != last_notes_state:
                last_notes_state = notes_str
                try:
                    notes = json.loads(notes_str)
                except json.JSONDecodeError as e:
                    print(f"\n  ⚠️  Warning: Could not parse Notes field: {e}")
                    notes = {}
                    continue
                
                # Check for completion indicators
                if notes.get('reflection_generated') or notes.get('thoughts_created'):
                    print(f"  ✅ Activity reflection generated!")
                    
                    if notes.get('kinos_reflection'):
                        print(f"  🧠 KinOS Reflection preview: {notes['kinos_reflection'][:200]}...")
                    
                    # Check for thought creation based on activity type
                    thought_type = 'research_planning' if activity_type == 'research_planning' else 'hypothesis' if activity_type == 'hypothesis' else 'research_findings'
                    
                    thoughts = list(tables['thoughts'].all(
                        formula=f"AND({{Citizen}}='{activity['fields'].get('Citizen')}', {{Type}}='{thought_type}', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'minutes') < 5)",
                        max_records=1
                    ))
                    if thoughts:
                        print(f"  📝 Thought created:")
                        print(f"     {thoughts[0]['fields'].get('Content', '')[:300]}...")
                    
                    return True
            
            # Show progress
            elapsed = int(time.time() - start_time)
            print(f"  ⏳ Waiting for async operations... {elapsed}s / {timeout}s", end='\r')
            time.sleep(5)
            
        except Exception as e:
            print(f"\n  ❌ Error checking activity: {e}")
            time.sleep(5)
    
    print(f"\n  ⏰ Timeout reached after {timeout} seconds")
    return False

def wait_for_research_completion(tables: Dict[str, Any], activity_id: str, timeout: int = 300):
    """Wait for async research threads to complete by monitoring activity notes"""
    start_time = time.time()
    last_notes_state = ""
    
    while time.time() - start_time < timeout:
        try:
            # Fetch current activity state
            activity = tables['activities'].get(activity_id)
            notes_str = activity['fields'].get('Notes', '{}')
            
            # Check if notes have changed
            if notes_str != last_notes_state:
                last_notes_state = notes_str
                try:
                    notes = json.loads(notes_str)
                except json.JSONDecodeError as e:
                    print(f"\n  ⚠️  Warning: Could not parse Notes field: {e}")
                    notes = {}
                    continue
                
                # Check for completion indicators
                if notes.get('research_completed'):
                    print(f"  ✅ Research completed!")
                    if notes.get('claude_consultation'):
                        print(f"  ✅ Claude consultation successful")
                        if notes.get('insights_received'):
                            print(f"  💡 Insights preview: {notes['insights_received'][:200]}...")
                    else:
                        print(f"  ℹ️  Claude consultation was not available")
                    
                    if notes.get('reflection_generated'):
                        print(f"  ✅ KinOS reflection generated")
                    
                    # Check for thought creation
                    thoughts = list(tables['thoughts'].all(
                        formula=f"AND({{Citizen}}='{activity['fields'].get('Citizen')}', {{Type}}='research_findings', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'minutes') < 5)",
                        max_records=1
                    ))
                    if thoughts:
                        print(f"  📝 Research thought created:")
                        print(f"     {thoughts[0]['fields'].get('Content', '')[:300]}...")
                    
                    return True
            
            # Show progress
            elapsed = int(time.time() - start_time)
            print(f"  ⏳ Waiting for async operations... {elapsed}s / {timeout}s", end='\r')
            time.sleep(5)
            
        except Exception as e:
            print(f"\n  ❌ Error checking activity: {e}")
            time.sleep(5)
    
    print(f"\n  ⏰ Timeout reached after {timeout} seconds")
    return False

def test_scientisti_work_handler(tables: Dict[str, Any], citizen_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Test the weighted Scientisti work handler"""
    print(f"\n🎲 Testing Weighted Work Selection for {citizen_record['fields'].get('Username')}")
    
    position = get_citizen_position(citizen_record)
    if not position:
        print("  ❌ No position found")
        return None
    
    # Prepare parameters for the handler
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip()
    
    now_dt = datetime.now(timezone.utc)
    
    # Mock parameters that would normally come from the main handler
    activity = _try_process_weighted_scientisti_work(
        tables=tables,
        citizen_record=citizen_record,
        is_night=False,  # Assume daytime
        resource_defs=get_resource_defs(),
        building_type_defs=get_building_type_defs(),
        now_venice_dt=now_dt,
        now_utc_dt=now_dt,
        transport_api_url=TRANSPORT_API_URL,
        api_base_url=API_BASE_URL,
        citizen_position=position,
        citizen_custom_id=citizen_record['fields'].get('CitizenId'),
        citizen_username=citizen_username,
        citizen_airtable_id=citizen_record['id'],
        citizen_name=citizen_name,
        citizen_position_str=citizen_record['fields'].get('Position'),
        citizen_social_class='Scientisti'
    )
    
    if activity:
        print(f"  ✅ Handler selected and created: {activity['fields'].get('Type')} - {activity['fields'].get('Title')}")
    else:
        print("  ❌ Handler did not create an activity")
    
    return activity

def show_recent_thoughts(tables: Dict[str, Any], citizen_username: str = None):
    """Show recent research thoughts"""
    print("\n📝 Recent Research Thoughts:")
    try:
        # Include all research-related thought types
        thought_types = "OR({Type}='research_findings', {Type}='research_planning', {Type}='hypothesis', {Type}='research_hypothesis', {Type}='integration_session', {Type}='knowledge_synthesis', {Type}='knowledge_integration_project')"
        formula = f"AND({thought_types}, DATETIME_DIFF(NOW(), {{CreatedAt}}, 'minutes') < 30)"
        if citizen_username:
            formula = f"AND({{Citizen}}='{citizen_username}', {thought_types}, DATETIME_DIFF(NOW(), {{CreatedAt}}, 'minutes') < 30)"
        
        thoughts = list(tables['thoughts'].all(
            formula=formula,
            max_records=5,
            sort=['-CreatedAt']
        ))
        
        if thoughts:
            for thought in thoughts:
                print(f"\n🧑‍🔬 {thought['fields'].get('Citizen')}:")
                content = thought['fields'].get('Content', '')
                print(f"   {content[:500]}...")
                
                # Show context if available
                context_str = thought['fields'].get('Context', '{}')
                try:
                    context = json.loads(context_str)
                    if context.get('research_query'):
                        print(f"   📎 Query: {context['research_query']}")
                    if context.get('location'):
                        print(f"   📍 Location: {context['location']}")
                except json.JSONDecodeError:
                    # Silently skip if context can't be parsed
                    pass
                except Exception as e:
                    print(f"   ⚠️  Warning: Error parsing thought context: {e}")
        else:
            print("  No recent research thoughts found")
            
    except Exception as e:
        print(f"  Error fetching thoughts: {e}")

def main():
    parser = argparse.ArgumentParser(description='Test Scientisti activities with immediate processing')
    parser.add_argument('--username', help='Specific Scientisti username to test')
    parser.add_argument('--activity', choices=['study', 'observe', 'research', 'scope', 'hypothesis', 'integration', 'handler', 'all'], 
                       default='all', help='Which activity to test')
    parser.add_argument('--no-process', action='store_true', help='Create activities without processing them')
    parser.add_argument('--no-wait', action='store_true', help='Don\'t wait for async operations to complete')
    parser.add_argument('--model', default='local', help='KinOS model to use (default: local)')
    args = parser.parse_args()
    
    print("🔬 La Serenissima - Scientisti Activity Testing")
    print("=" * 50)
    print(f"Using KinOS model: {args.model}")
    
    # Get tables
    tables = get_tables()
    
    # Get Scientisti citizens
    scientisti = get_scientisti_citizens(tables)
    
    if not scientisti:
        print("❌ No Scientisti found in the city!")
        return
    
    print(f"Found {len(scientisti)} Scientisti citizens")
    
    # Filter by username if specified
    if args.username:
        scientisti = [s for s in scientisti if s['fields'].get('Username') == args.username]
        if not scientisti:
            print(f"❌ Scientisti '{args.username}' not found!")
            return
    
    # Test each Scientisti
    for scientist in scientisti[:3]:  # Limit to first 3 for testing
        username = scientist['fields'].get('Username')
        print(f"\n{'='*50}")
        print(f"Testing {username} (Social Class: {scientist['fields'].get('SocialClass')})")
        
        process_immediately = not args.no_process
        wait_for_async = not args.no_wait
        
        if args.activity in ['study', 'all']:
            test_study_literature(tables, scientist, process_immediately)
        
        if args.activity in ['observe', 'all']:
            test_observe_phenomena(tables, scientist, process_immediately)
        
        if args.activity in ['research', 'all']:
            test_research_investigation(tables, scientist, process_immediately, wait_for_async, args.model)
        
        if args.activity in ['scope', 'all']:
            test_research_scope_definition(tables, scientist, process_immediately, wait_for_async, args.model)
        
        if args.activity in ['hypothesis', 'all']:
            test_hypothesis_development(tables, scientist, process_immediately, wait_for_async, args.model)
        
        if args.activity in ['integration', 'all']:
            test_knowledge_integration(tables, scientist, process_immediately, wait_for_async, args.model)
        
        if args.activity in ['handler', 'all']:
            test_scientisti_work_handler(tables, scientist)
        
        # Show thoughts for this citizen
        if process_immediately:
            show_recent_thoughts(tables, username)
    
    print(f"\n{'='*50}")
    print("✅ Testing complete!")
    
    # Show all recent thoughts
    if process_immediately:
        show_recent_thoughts(tables)

if __name__ == "__main__":
    main()
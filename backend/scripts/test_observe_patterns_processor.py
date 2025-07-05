#!/usr/bin/env python3
"""
Test script for the observe_system_patterns activity processor.
This script creates a mock activity and tests the processor functionality.
"""

import os
import sys
import json
from datetime import datetime
import pytz
from pyairtable import Api, Table
from dotenv import load_dotenv

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# Import the processor
from backend.engine.activity_processors.observe_system_patterns_processor import process

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Airtable configuration
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def create_mock_activity():
    """Create a mock observe_system_patterns activity for testing."""
    
    now_utc = datetime.now(pytz.UTC)
    
    mock_activity = {
        'id': 'test_activity_id',
        'fields': {
            'ActivityId': f'observe_system_patterns_test_{int(now_utc.timestamp())}',
            'Type': 'observe_system_patterns',
            'Citizen': 'TestInnovatori',
            'Status': 'in_progress',
            'StartDate': (now_utc.isoformat()),
            'EndDate': (now_utc.isoformat()),  # Already ended for processing
            'Notes': json.dumps({
                'location': 'Rialto Market',
                'location_type': 'market',
                'observation_focus': 'Economic flow patterns during peak trading hours',
                'duration_hours': 4,
                'required_resources': {
                    'paper': 1,
                    'ink': 1
                }
            })
        }
    }
    
    return mock_activity

def setup_test_resources(tables, citizen_username):
    """Create test resources for the citizen."""
    
    # Create paper resource
    paper_record = {
        'ResourceId': f'resource-paper-test-{int(datetime.now().timestamp())}',
        'Type': 'paper',
        'Name': 'Paper',
        'Holder': citizen_username,
        'Owner': citizen_username,
        'Quantity': 5,
        'AssetType': 'citizen',
        'Asset': citizen_username
    }
    
    # Create ink resource
    ink_record = {
        'ResourceId': f'resource-ink-test-{int(datetime.now().timestamp())}',
        'Type': 'ink',
        'Name': 'Ink',
        'Holder': citizen_username,
        'Owner': citizen_username,
        'Quantity': 3,
        'AssetType': 'citizen',
        'Asset': citizen_username
    }
    
    created_paper = tables['resources'].create(paper_record)
    created_ink = tables['resources'].create(ink_record)
    
    print(f"✓ Created test resources:")
    print(f"  - Paper: {created_paper['fields']['Quantity']} units")
    print(f"  - Ink: {created_ink['fields']['Quantity']} units")
    
    return created_paper, created_ink

def cleanup_test_resources(tables, paper_record, ink_record):
    """Clean up test resources."""
    
    try:
        tables['resources'].delete(paper_record['id'])
        tables['resources'].delete(ink_record['id'])
        print("✓ Cleaned up test resources")
    except Exception as e:
        print(f"✗ Error cleaning up resources: {e}")

def test_processor():
    """Test the observe_system_patterns processor."""
    
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("ERROR: Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID in environment variables")
        return
    
    # Initialize Airtable
    api = Api(AIRTABLE_API_KEY)
    tables = {
        'activities': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'ACTIVITIES'),
        'resources': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'RESOURCES'),
        'citizens': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'CITIZENS')
    }
    
    # Try to add patterns table if it exists
    try:
        patterns_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'PATTERNS')
        tables['patterns'] = patterns_table
        print("✓ PATTERNS table found and added to tables")
    except:
        print("⚠ PATTERNS table not found - patterns will be saved in activity notes only")
    
    # Create mock activity and resources
    mock_activity = create_mock_activity()
    citizen_username = mock_activity['fields']['Citizen']
    
    print(f"\nTesting observe_system_patterns processor")
    print(f"=========================================")
    print(f"Activity ID: {mock_activity['fields']['ActivityId']}")
    print(f"Citizen: {citizen_username}")
    print(f"Location: {json.loads(mock_activity['fields']['Notes'])['location']}")
    print()
    
    # Set up test resources
    paper_record, ink_record = setup_test_resources(tables, citizen_username)
    
    # Mock building type and resource definitions
    building_type_defs = {}
    resource_defs = {
        'paper': {'id': 'paper', 'name': 'Paper'},
        'ink': {'id': 'ink', 'name': 'Ink'}
    }
    
    # Test the processor
    print("\nRunning processor...")
    print("-" * 40)
    
    try:
        result = process(
            tables=tables,
            activity_record=mock_activity,
            building_type_defs=building_type_defs,
            resource_defs=resource_defs,
            api_base_url="http://localhost:3000"
        )
        
        if result:
            print("✓ Processor completed successfully!")
            
            # Check resource consumption
            remaining_resources = tables['resources'].all(
                formula=f"AND({{Holder}}='{citizen_username}', OR({{Type}}='paper', {{Type}}='ink'))"
            )
            
            print("\nResource consumption:")
            for resource in remaining_resources:
                print(f"  - {resource['fields']['Type']}: {resource['fields'].get('Quantity', 0)} remaining")
            
            # Note: Pattern creation happens asynchronously, so we can't check it immediately
            print("\n⚠ Note: Pattern creation happens asynchronously.")
            print("  Check the PATTERNS table (if exists) or activity notes later.")
            
        else:
            print("✗ Processor returned failure")
            
    except Exception as e:
        print(f"✗ Processor threw exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test resources
        print("\nCleaning up...")
        cleanup_test_resources(tables, paper_record, ink_record)

def main():
    """Main function."""
    test_processor()

if __name__ == "__main__":
    main()
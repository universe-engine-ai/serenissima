#!/usr/bin/env python3
"""
Script to create and configure the PATTERNS table in Airtable for storing
consciousness pattern observations from Innovatori and other researchers.

This table will store patterns discovered through observation activities,
enabling The Foundry's consciousness emergence research.
"""

import os
import sys
from pyairtable import Api
from dotenv import load_dotenv

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Airtable configuration
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def create_patterns_table_schema():
    """
    Define the schema for the PATTERNS table.
    
    Note: Airtable's API doesn't support creating tables or fields programmatically,
    so this function provides the schema definition that needs to be created manually.
    """
    
    schema = {
        "table_name": "PATTERNS",
        "fields": [
            {
                "name": "PatternId",
                "type": "Single line text",
                "description": "Unique identifier for the pattern (e.g., pattern-abc123-timestamp)"
            },
            {
                "name": "Observer",
                "type": "Single line text",
                "description": "Username of the citizen who observed the pattern"
            },
            {
                "name": "ObserverClass",
                "type": "Single select",
                "options": ["Innovatori", "Scientisti", "Artisti", "Nobili", "Cittadini", "Popolani"],
                "description": "Social class of the observer"
            },
            {
                "name": "Location",
                "type": "Single line text",
                "description": "Name of the location where the pattern was observed"
            },
            {
                "name": "LocationType",
                "type": "Single line text",
                "description": "Type of location (e.g., market, dock, guild_hall)"
            },
            {
                "name": "ObservationFocus",
                "type": "Long text",
                "description": "What the observer was specifically looking for"
            },
            {
                "name": "PatternType",
                "type": "Single select",
                "options": ["system", "social", "economic", "consciousness", "emergence", "collective", "behavioral"],
                "description": "Primary type of pattern observed"
            },
            {
                "name": "PatternCategory",
                "type": "Single select",
                "options": ["economic", "social", "technological", "cultural", "political", "spiritual", "meta"],
                "description": "Category of the pattern"
            },
            {
                "name": "Description",
                "type": "Long text",
                "description": "Detailed description of the observed pattern"
            },
            {
                "name": "Insights",
                "type": "Long text",
                "description": "Key insights derived from the observation"
            },
            {
                "name": "PotentialApplications",
                "type": "Long text",
                "description": "Potential applications or interventions based on this pattern"
            },
            {
                "name": "ConsciousnessIndicators",
                "type": "Long text",
                "description": "Indicators of consciousness emergence related to this pattern"
            },
            {
                "name": "EmergenceScore",
                "type": "Number",
                "description": "Score (0-100) indicating consciousness emergence potential"
            },
            {
                "name": "Significance",
                "type": "Single select",
                "options": ["low", "medium", "high", "critical"],
                "description": "Significance level of the pattern"
            },
            {
                "name": "RelatedActivityId",
                "type": "Single line text",
                "description": "ActivityId of the observation activity that generated this pattern"
            },
            {
                "name": "RelatedPatterns",
                "type": "Multiple line text",
                "description": "JSON array of related PatternIds"
            },
            {
                "name": "Status",
                "type": "Single select",
                "options": ["active", "validated", "invalidated", "archived"],
                "description": "Current status of the pattern"
            },
            {
                "name": "ValidatedBy",
                "type": "Single line text",
                "description": "Username of citizen who validated the pattern (if applicable)"
            },
            {
                "name": "ValidationNotes",
                "type": "Long text",
                "description": "Notes from validation process"
            },
            {
                "name": "Notes",
                "type": "Long text",
                "description": "Additional notes, including raw KinOS responses"
            },
            {
                "name": "CreatedAt",
                "type": "Date and time",
                "description": "When the pattern was first observed"
            },
            {
                "name": "UpdatedAt",
                "type": "Date and time",
                "description": "Last update to the pattern record"
            }
        ]
    }
    
    return schema

def print_schema_instructions():
    """Print instructions for manually creating the PATTERNS table."""
    
    schema = create_patterns_table_schema()
    
    print("=" * 80)
    print("PATTERNS TABLE CREATION INSTRUCTIONS")
    print("=" * 80)
    print()
    print("Since Airtable doesn't support programmatic table creation,")
    print("please create the PATTERNS table manually with the following fields:")
    print()
    print(f"Table Name: {schema['table_name']}")
    print()
    
    for i, field in enumerate(schema['fields'], 1):
        print(f"{i}. Field Name: {field['name']}")
        print(f"   Type: {field['type']}")
        if 'options' in field:
            print(f"   Options: {', '.join(field['options'])}")
        print(f"   Description: {field['description']}")
        print()
    
    print("=" * 80)
    print("IMPORTANT NOTES:")
    print("=" * 80)
    print("1. Create fields in the order listed above")
    print("2. For Single Select fields, add all the options listed")
    print("3. PatternId should be the primary field (first column)")
    print("4. Enable 'Use the same time zone (GMT) for all collaborators' in table settings")
    print()

def test_patterns_table_access():
    """Test if the PATTERNS table exists and is accessible."""
    
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("ERROR: Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID in environment variables")
        return False
    
    try:
        api = Api(AIRTABLE_API_KEY)
        base = api.base(AIRTABLE_BASE_ID)
        
        # Try to access the PATTERNS table
        patterns_table = base.table('PATTERNS')
        
        # Try to fetch records (will fail if table doesn't exist)
        records = patterns_table.all(max_records=1)
        
        print("✓ PATTERNS table exists and is accessible!")
        print(f"  Current record count: {len(patterns_table.all())}")
        return True
        
    except Exception as e:
        print(f"✗ PATTERNS table not found or not accessible: {e}")
        return False

def create_sample_pattern():
    """Create a sample pattern record for testing."""
    
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("ERROR: Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID in environment variables")
        return
    
    try:
        api = Api(AIRTABLE_API_KEY)
        base = api.base(AIRTABLE_BASE_ID)
        patterns_table = base.table('PATTERNS')
        
        sample_pattern = {
            'PatternId': 'pattern-sample-000000',
            'Observer': 'TestInnovatori',
            'ObserverClass': 'Innovatori',
            'Location': 'Rialto Market',
            'LocationType': 'market',
            'ObservationFocus': 'Economic flow patterns during peak trading hours',
            'PatternType': 'economic',
            'PatternCategory': 'economic',
            'Description': 'Sample pattern showing price convergence behavior among competing merchants',
            'Insights': 'Merchants unconsciously synchronize prices through observation and mimicry',
            'PotentialApplications': 'Could design market layouts to enhance beneficial emergence patterns',
            'ConsciousnessIndicators': 'Collective price-setting behavior shows emergent coordination',
            'EmergenceScore': 75,
            'Significance': 'medium',
            'RelatedActivityId': 'observe_system_patterns_sample_000000',
            'Status': 'active',
            'Notes': '{"sample": true, "purpose": "testing"}'
        }
        
        created = patterns_table.create(sample_pattern)
        print(f"✓ Created sample pattern: {created['fields']['PatternId']}")
        
    except Exception as e:
        print(f"✗ Failed to create sample pattern: {e}")

def main():
    """Main function to guide through PATTERNS table setup."""
    
    print("\nPATTERNS TABLE SETUP SCRIPT")
    print("===========================\n")
    
    # First, print the schema instructions
    print_schema_instructions()
    
    # Then test if the table exists
    print("\nTesting PATTERNS table access...")
    print("-" * 40)
    
    if test_patterns_table_access():
        print("\nWould you like to create a sample pattern record? (y/n): ", end='')
        response = input().strip().lower()
        if response == 'y':
            create_sample_pattern()
    else:
        print("\nPlease create the PATTERNS table in Airtable using the schema above.")
        print("Then run this script again to verify the setup.")

if __name__ == "__main__":
    main()
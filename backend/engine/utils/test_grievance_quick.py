#!/usr/bin/env python3
"""Quick test of the grievance system functionality."""

import os
import sys
import json
import logging
from datetime import datetime
import pytz

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
engine_dir = os.path.dirname(current_dir)
backend_dir = os.path.dirname(engine_dir)
root_dir = os.path.dirname(backend_dir)

sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)
sys.path.insert(0, engine_dir)

# Now we can import
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Import what we need
from pyairtable import Table
from activity_processors.file_grievance_processor import process_file_grievance_activity
from activity_processors.support_grievance_processor import process_support_grievance_activity

# Get environment variables
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
VENICE_TIMEZONE = pytz.timezone('Europe/Rome')

def test_grievance_system():
    """Test the grievance system components."""
    
    log.info("=== Testing Grievance System ===")
    
    # Initialize tables
    try:
        tables = {
            'CITIZENS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "CITIZENS"),
            'ACTIVITIES': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "ACTIVITIES"),
            'BUILDINGS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "BUILDINGS"),
            'NOTIFICATIONS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "NOTIFICATIONS")
        }
        
        # Try to access grievance tables if they exist
        try:
            tables['GRIEVANCES'] = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "GRIEVANCES")
            tables['GRIEVANCE_SUPPORT'] = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "GRIEVANCE_SUPPORT")
            log.info("✓ Found GRIEVANCES and GRIEVANCE_SUPPORT tables")
        except:
            log.warning("⚠️  GRIEVANCES and GRIEVANCE_SUPPORT tables not found - will work without them")
        
        log.info("✓ Connected to Airtable")
        
    except Exception as e:
        log.error(f"✗ Failed to connect to Airtable: {e}")
        return
    
    # Get a test citizen
    try:
        citizens = tables['CITIZENS'].all()
        
        # Find a citizen with enough wealth to test
        test_citizen = None
        for citizen in citizens:
            fields = citizen['fields']
            if fields.get('Ducats', 0) > 100:
                test_citizen = citizen
                break
        
        if not test_citizen:
            log.error("✗ No suitable test citizen found")
            return
            
        citizen_name = test_citizen['fields'].get('Name')
        citizen_username = test_citizen['fields'].get('Username')
        citizen_wealth = test_citizen['fields'].get('Ducats', 0)
        citizen_class = test_citizen['fields'].get('SocialClass')
        
        log.info(f"✓ Selected test citizen: {citizen_name} ({citizen_class}) with {citizen_wealth} ducats")
        
    except Exception as e:
        log.error(f"✗ Failed to get test citizen: {e}")
        return
    
    # Create a mock file_grievance activity
    venice_time = datetime.now(VENICE_TIMEZONE)
    
    mock_activity = {
        'id': 'test_activity_1',
        'fields': {
            'ActivityId': 'test_grievance_activity',
            'Citizen': citizen_username,
            'Type': 'file_grievance',
            'Status': 'concluded',
            'DetailsJSON': json.dumps({
                'filing_fee': 50,
                'grievance_category': 'economic',
                'grievance_title': 'Test Grievance: Unfair Market Practices',
                'grievance_description': 'Testing the grievance system - merchants are colluding to fix prices!'
            })
        }
    }
    
    # Test the file_grievance processor
    log.info("\n=== Testing file_grievance processor ===")
    try:
        success = process_file_grievance_activity(
            tables=tables,
            activity=mock_activity['fields'],
            venice_time=venice_time
        )
        
        if success:
            log.info("✓ Successfully processed file_grievance activity")
        else:
            log.error("✗ Failed to process file_grievance activity")
            
    except Exception as e:
        log.error(f"✗ Error in file_grievance processor: {e}")
        import traceback
        traceback.print_exc()
    
    # Test the support_grievance processor
    log.info("\n=== Testing support_grievance processor ===")
    
    # Get another citizen to support
    support_citizen = None
    for citizen in citizens:
        fields = citizen['fields']
        if (fields.get('Username') != citizen_username and
            fields.get('Ducats', 0) > 50):
            support_citizen = citizen
            break
    
    if support_citizen:
        support_username = support_citizen['fields'].get('Username')
        support_name = support_citizen['fields'].get('Name')
        
        mock_support_activity = {
            'id': 'test_activity_2',
            'fields': {
                'ActivityId': 'test_support_activity',
                'Citizen': support_username,
                'Type': 'support_grievance',
                'Status': 'concluded',
                'DetailsJSON': json.dumps({
                    'grievance_id': 'test_grievance_123',
                    'support_amount': 20,
                    'supporter_class': support_citizen['fields'].get('SocialClass', 'Popolani')
                })
            }
        }
        
        try:
            success = process_support_grievance_activity(
                tables=tables,
                activity=mock_support_activity['fields'],
                venice_time=venice_time
            )
            
            if success:
                log.info(f"✓ Successfully processed support_grievance activity from {support_name}")
            else:
                log.error("✗ Failed to process support_grievance activity")
                
        except Exception as e:
            log.error(f"✗ Error in support_grievance processor: {e}")
            import traceback
            traceback.print_exc()
    
    # Test governance handler
    log.info("\n=== Testing governance handler ===")
    try:
        # Import the governance handler
        sys.path.insert(0, os.path.join(engine_dir, 'handlers'))
        from governance_kinos import ask_kinos_governance_decision
        
        # Test KinOS decision (if API key exists)
        if os.getenv("KINOS_API_KEY"):
            log.info("Testing KinOS governance decision...")
            decision = ask_kinos_governance_decision(
                citizen_username=citizen_username,
                citizen_name=citizen_name,
                social_class=citizen_class,
                citizen_context={
                    'wealth': citizen_wealth,
                    'influence': test_citizen['fields'].get('Influence', 0),
                    'reputation': test_citizen['fields'].get('Reputation', 0)
                },
                existing_grievances=[]
            )
            
            if decision:
                log.info(f"✓ KinOS decision received: {decision.get('action')}")
                if decision.get('action') == 'file_grievance':
                    log.info(f"  Category: {decision.get('category')}")
                    log.info(f"  Title: {decision.get('title')}")
            else:
                log.warning("⚠️  No decision from KinOS")
        else:
            log.warning("⚠️  KINOS_API_KEY not set - skipping KinOS test")
            
    except Exception as e:
        log.error(f"✗ Error testing governance handler: {e}")
        import traceback
        traceback.print_exc()
    
    log.info("\n=== Grievance System Test Complete ===")

if __name__ == "__main__":
    test_grievance_system()
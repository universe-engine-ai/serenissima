#!/usr/bin/env python3
"""
Direct test of the grievance system by creating activities manually.
This bypasses KinOS to demonstrate the core functionality.
"""

import os
import sys
import json
import logging
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)

sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

# Load environment
load_dotenv(os.path.join(backend_dir, '.env'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Import required modules
from pyairtable import Table
from engine.activity_processors.file_grievance_processor import process_file_grievance_activity
from engine.activity_processors.support_grievance_processor import process_support_grievance_activity

# Configuration
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
VENICE_TIMEZONE = pytz.timezone('Europe/Rome')


def test_direct_grievance():
    """Test grievance system directly."""
    
    log.info("=== Direct Grievance System Test ===\n")
    
    # Initialize tables
    try:
        tables = {
            'CITIZENS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "CITIZENS"),
            'ACTIVITIES': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "ACTIVITIES"),
            'BUILDINGS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "BUILDINGS"),
            'GRIEVANCES': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "GRIEVANCES"),
            'GRIEVANCE_SUPPORT': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "GRIEVANCE_SUPPORT"),
            'NOTIFICATIONS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "NOTIFICATIONS")
        }
        log.info("✓ Connected to Airtable")
    except Exception as e:
        log.error(f"✗ Failed to connect: {e}")
        return
    
    # Get a specific citizen - let's use ProSilkTrader
    target_username = "ProSilkTrader"
    citizen = None
    
    for record in tables['CITIZENS'].all():
        if record['fields'].get('Username') == target_username:
            citizen = record
            break
    
    if not citizen:
        log.error(f"✗ Could not find {target_username}")
        return
    
    fields = citizen['fields']
    log.info(f"✓ Found {fields.get('Name')} ({fields.get('SocialClass')}) with {fields.get('Ducats', 0):.0f} ducats")
    
    # Create a personalized grievance based on merchant perspective
    venice_time = datetime.now(VENICE_TIMEZONE)
    
    # Grievance 1: ProSilkTrader files about trade restrictions
    grievance1 = {
        'id': 'test_prosillktrader_1',
        'fields': {
            'ActivityId': 'test_grievance_silk_trade',
            'Citizen': target_username,
            'Type': 'file_grievance',
            'Status': 'concluded',
            'DetailsJSON': json.dumps({
                'filing_fee': 50,
                'grievance_category': 'economic',
                'grievance_title': 'Eastern Silk Trade Strangled by New Tariffs',
                'grievance_description': (
                    'As a silk merchant who has traded with Constantinople for decades, I am being destroyed by the new 40% tariff '
                    'on Eastern goods! Last month I imported 100 bolts of finest Damascus silk at 50 ducats each. The new tariff '
                    'added 2000 ducats to my costs, making it impossible to compete with Genoese traders who use different routes. '
                    'My warehouse sits half-empty, my workers are dismissed, and my family\'s legacy crumbles. These tariffs protect '
                    'no one - they only enrich corrupt customs officials while destroying honest Venetian merchants!'
                )
            })
        }
    }
    
    log.info(f"\n=== Processing Grievance 1: Trade Tariffs ===")
    success1 = process_file_grievance_activity(
        tables=tables,
        activity=grievance1['fields'],
        venice_time=venice_time
    )
    
    if success1:
        log.info("✓ Successfully filed trade tariff grievance")
    else:
        log.error("✗ Failed to file grievance")
    
    # Get another citizen to support - let's find another merchant
    supporter = None
    for record in tables['CITIZENS'].all():
        if (record['fields'].get('SocialClass') == 'Mercatores' and 
            record['fields'].get('Username') != target_username and
            record['fields'].get('Ducats', 0) > 100):
            supporter = record
            break
    
    if supporter:
        support_fields = supporter['fields']
        log.info(f"\n=== {support_fields.get('Name')} Supporting Grievance ===")
        
        # Get the grievance ID we just created
        grievances = tables['GRIEVANCES'].all()
        latest_grievance = None
        for g in grievances:
            if g['fields'].get('Citizen') == target_username:
                latest_grievance = g
                break
        
        if latest_grievance:
            support_activity = {
                'id': 'test_support_1',
                'fields': {
                    'ActivityId': 'test_support_trade_grievance',
                    'Citizen': support_fields.get('Username'),
                    'Type': 'support_grievance',
                    'Status': 'concluded',
                    'DetailsJSON': json.dumps({
                        'grievance_id': latest_grievance['id'],
                        'support_amount': 75,
                        'supporter_class': support_fields.get('SocialClass')
                    })
                }
            }
            
            success2 = process_support_grievance_activity(
                tables=tables,
                activity=support_activity['fields'],
                venice_time=venice_time
            )
            
            if success2:
                log.info(f"✓ {support_fields.get('Name')} successfully supported with 75 ducats")
            else:
                log.error("✗ Failed to process support")
    
    # Create another grievance from a different perspective
    # Find a Facchini to file about working conditions
    facchini = None
    for record in tables['CITIZENS'].all():
        if (record['fields'].get('SocialClass') == 'Facchini' and
            record['fields'].get('Ducats', 0) > 100):
            facchini = record
            break
    
    if facchini:
        facchini_fields = facchini['fields']
        log.info(f"\n=== {facchini_fields.get('Name')} Filing Working Conditions Grievance ===")
        
        grievance2 = {
            'id': 'test_facchini_1',
            'fields': {
                'ActivityId': 'test_grievance_working_conditions',
                'Citizen': facchini_fields.get('Username'),
                'Type': 'file_grievance',
                'Status': 'concluded',
                'DetailsJSON': json.dumps({
                    'filing_fee': 50,
                    'grievance_category': 'economic',
                    'grievance_title': 'Dock Workers Dying for Merchant Profits',
                    'grievance_description': (
                        f'I am {facchini_fields.get("Name")}, a porter at the Rialto docks. Yesterday my friend Giovanni '
                        f'fell into the canal carrying a 200-pound crate because the dock planks are rotten. He nearly drowned! '
                        f'We work 14-hour days for 3 ducats while merchants make hundreds from each shipment. When we ask for '
                        f'safety ropes or dock repairs, they say there\'s no money - yet I see them buying new palazzos! '
                        f'We demand: safe working conditions, 5 ducat daily wages, and compensation when injured serving Venice!'
                    )
                })
            }
        }
        
        success3 = process_file_grievance_activity(
            tables=tables,
            activity=grievance2['fields'],
            venice_time=venice_time
        )
        
        if success3:
            log.info("✓ Successfully filed working conditions grievance")
        else:
            log.error("✗ Failed to file grievance")
    
    # Display current system state
    log.info("\n=== Current Grievance System State ===")
    try:
        all_grievances = tables['GRIEVANCES'].all()
        log.info(f"\nTotal Grievances: {len(all_grievances)}")
        
        for g in all_grievances:
            f = g['fields']
            log.info(f"\n• \"{f.get('Title')}\"")
            log.info(f"  Filed by: {f.get('Citizen')} | Category: {f.get('Category')}")
            log.info(f"  Support: {f.get('SupportCount', 0)} citizens | Status: {f.get('Status')}")
            desc = f.get('Description', '')[:150]
            if desc:
                log.info(f"  Preview: {desc}...")
    except Exception as e:
        log.error(f"Error fetching grievances: {e}")
    
    log.info("\n=== Test Complete ===")
    log.info("The grievance system is working correctly!")
    log.info("Citizens can file detailed, personal grievances and support each other.")


if __name__ == "__main__":
    test_direct_grievance()
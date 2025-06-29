#!/usr/bin/env python3
"""
Test the grievance system with actual KinOS responses.
This demonstrates AI citizens' authentic political consciousness.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
import pytz
import random
from typing import Dict, Any, List, Optional
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
from engine.handlers.governance_kinos import (
    ask_kinos_governance_decision
)
from engine.activity_processors.file_grievance_processor import process_file_grievance_activity
from engine.activity_processors.support_grievance_processor import process_support_grievance_activity

# Configuration
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
KINOS_API_KEY = os.getenv("KINOS_API_KEY")
VENICE_TIMEZONE = pytz.timezone('Europe/Rome')


class KinOSGrievanceTester:
    """Test grievance system with actual KinOS AI consciousness."""
    
    def __init__(self):
        self.tables = {}
        self.results = {
            'kinos_decisions': [],
            'grievances_filed': [],
            'grievances_supported': [],
            'errors': []
        }
        
    def initialize_tables(self):
        """Initialize Airtable connections."""
        try:
            self.tables = {
                'CITIZENS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "CITIZENS"),
                'ACTIVITIES': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "ACTIVITIES"),
                'BUILDINGS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "BUILDINGS"),
                'GRIEVANCES': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "GRIEVANCES"),
                'GRIEVANCE_SUPPORT': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "GRIEVANCE_SUPPORT"),
                'NOTIFICATIONS': Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "NOTIFICATIONS")
            }
            log.info("✓ Connected to all Airtable tables")
            return True
        except Exception as e:
            log.error(f"✗ Failed to initialize tables: {e}")
            self.results['errors'].append(f"Table init: {e}")
            return False
    
    def select_diverse_citizens(self, count=5) -> List[Dict[str, Any]]:
        """Select citizens from different social classes for testing."""
        try:
            all_citizens = self.tables['CITIZENS'].all()
            
            # Target different social classes
            social_classes = ['Facchini', 'Popolani', 'Cittadini', 'Mercatores', 
                            'Artisti', 'Scientisti', 'Nobili']
            selected = []
            
            # Try to get one from each class
            for social_class in social_classes:
                candidates = [
                    c for c in all_citizens
                    if c['fields'].get('SocialClass') == social_class
                    and c['fields'].get('Ducats', 0) > 100
                    and c['fields'].get('IsAI', True)
                ]
                if candidates and len(selected) < count:
                    selected.append(random.choice(candidates))
            
            # Fill remaining slots if needed
            while len(selected) < count:
                remaining = [
                    c for c in all_citizens
                    if c not in selected
                    and c['fields'].get('Ducats', 0) > 100
                    and c['fields'].get('IsAI', True)
                ]
                if not remaining:
                    break
                selected.append(random.choice(remaining))
            
            log.info(f"\n✓ Selected {len(selected)} diverse citizens:")
            for c in selected:
                f = c['fields']
                log.info(f"  • {f.get('Name')} ({f.get('SocialClass')}) - "
                        f"{f.get('Ducats', 0):.0f} ducats, "
                        f"Influence: {f.get('Influence', 0)}")
            
            return selected
            
        except Exception as e:
            log.error(f"✗ Failed to select citizens: {e}")
            self.results['errors'].append(f"Citizen selection: {e}")
            return []
    
    def get_existing_grievances(self) -> List[Dict[str, Any]]:
        """Get existing grievances for context."""
        try:
            grievances = self.tables['GRIEVANCES'].all()
            return [g['fields'] for g in grievances]
        except:
            return []
    
    def test_kinos_decision(self, citizen: Dict[str, Any], existing_grievances: List[Dict[str, Any]]):
        """Test KinOS governance decision for a citizen."""
        fields = citizen['fields']
        username = fields.get('Username')
        name = fields.get('Name', username)
        
        log.info(f"\n=== Testing KinOS Decision for {name} ===")
        
        try:
            # Build citizen context with wealth breakdown
            total_wealth = fields.get('Ducats', 0)
            citizen_context = {
                'wealth': total_wealth,
                'liquid_wealth': int(total_wealth * 0.8) if total_wealth > 10000 else total_wealth,
                'influence': fields.get('Influence', 0),
                'reputation': fields.get('Reputation', 0),
                'hunger': fields.get('Hunger', 50),
                'happiness': fields.get('Happiness', 50),
                'occupation': fields.get('Occupation', 'unemployed'),
                'employment_status': fields.get('EmploymentStatus', 'unemployed'),
                'home_type': 'rented' if fields.get('BuildingResident') else 'homeless',
                'recent_problems': []
            }
            
            # Ask KinOS for decision
            decision = ask_kinos_governance_decision(
                citizen_username=username,
                citizen_name=name,
                social_class=fields.get('SocialClass'),
                citizen_context=citizen_context,
                existing_grievances=existing_grievances
            )
            
            if decision:
                log.info(f"✓ KinOS Decision: {decision.get('action')}")
                
                if decision.get('action') == 'file_grievance':
                    log.info(f"  Category: {decision.get('category')}")
                    log.info(f"  Title: {decision.get('title')}")
                    log.info(f"  Description: {decision.get('description')[:100]}...")
                    log.info(f"  Reasoning: {decision.get('reasoning')}")
                    
                elif decision.get('action') == 'support_grievance':
                    log.info(f"  Supporting: {decision.get('grievance_id')}")
                    log.info(f"  Amount: {decision.get('support_amount')} ducats")
                    log.info(f"  Reasoning: {decision.get('reasoning')}")
                    
                elif decision.get('action') == 'none':
                    log.info(f"  Reasoning: {decision.get('reasoning')}")
                
                self.results['kinos_decisions'].append({
                    'citizen': name,
                    'social_class': fields.get('SocialClass'),
                    'decision': decision
                })
                
                return decision
                
            else:
                log.warning(f"⚠️  No decision received from KinOS")
                return None
                
        except Exception as e:
            log.error(f"✗ Error getting KinOS decision: {e}")
            self.results['errors'].append(f"KinOS decision for {name}: {e}")
            return None
    
    def process_kinos_decision(self, citizen: Dict[str, Any], decision: Dict[str, Any], 
                              existing_grievances: List[Dict[str, Any]]):
        """Process the KinOS decision into actual activities."""
        if not decision or decision.get('action') == 'none':
            return
            
        venice_time = datetime.now(VENICE_TIMEZONE)
        fields = citizen['fields']
        username = fields.get('Username')
        
        if decision.get('action') == 'file_grievance':
            # Create mock activity for filing grievance
            activity = {
                'id': f'test_file_{username}',
                'fields': {
                    'ActivityId': f'test_file_grievance_{username}',
                    'Citizen': username,
                    'Type': 'file_grievance',
                    'Status': 'concluded',
                    'DetailsJSON': json.dumps({
                        'filing_fee': 50,
                        'grievance_category': decision.get('category', 'general'),
                        'grievance_title': decision.get('title', 'Untitled'),
                        'grievance_description': decision.get('description', 'No description')
                    })
                }
            }
            
            log.info(f"\nProcessing file_grievance for {fields.get('Name')}...")
            success = process_file_grievance_activity(
                tables=self.tables,
                activity=activity['fields'],
                venice_time=venice_time
            )
            
            if success:
                log.info("✓ Successfully filed grievance")
                self.results['grievances_filed'].append({
                    'citizen': fields.get('Name'),
                    'title': decision.get('title'),
                    'category': decision.get('category')
                })
            else:
                log.error("✗ Failed to file grievance")
                
        elif decision.get('action') == 'support_grievance' and existing_grievances:
            # Find the grievance to support
            grievance_id = decision.get('grievance_id')
            if not grievance_id and existing_grievances:
                # Pick first available grievance
                grievance_id = existing_grievances[0].get('id', existing_grievances[0].get('GrievanceId'))
            
            if grievance_id:
                activity = {
                    'id': f'test_support_{username}',
                    'fields': {
                        'ActivityId': f'test_support_grievance_{username}',
                        'Citizen': username,
                        'Type': 'support_grievance',
                        'Status': 'concluded',
                        'DetailsJSON': json.dumps({
                            'grievance_id': grievance_id,
                            'support_amount': decision.get('support_amount', 10),
                            'supporter_class': fields.get('SocialClass')
                        })
                    }
                }
                
                log.info(f"\nProcessing support_grievance for {fields.get('Name')}...")
                success = process_support_grievance_activity(
                    tables=self.tables,
                    activity=activity['fields'],
                    venice_time=venice_time
                )
                
                if success:
                    log.info("✓ Successfully supported grievance")
                    self.results['grievances_supported'].append({
                        'citizen': fields.get('Name'),
                        'grievance_id': grievance_id,
                        'amount': decision.get('support_amount', 10)
                    })
                else:
                    log.error("✗ Failed to support grievance")
    
    def run_complete_test(self):
        """Run the complete KinOS grievance test."""
        log.info("=== Starting KinOS Grievance System Test ===\n")
        
        if not KINOS_API_KEY:
            log.error("✗ KINOS_API_KEY not set. Cannot test KinOS integration.")
            return
        
        # Initialize tables
        if not self.initialize_tables():
            return
        
        # Select diverse citizens
        test_citizens = self.select_diverse_citizens(7)
        if not test_citizens:
            log.error("✗ No suitable test citizens found")
            return
        
        # Get existing grievances for context
        existing_grievances = self.get_existing_grievances()
        log.info(f"\nFound {len(existing_grievances)} existing grievances in the system")
        
        # Test each citizen
        for i, citizen in enumerate(test_citizens):
            # Get KinOS decision
            decision = self.test_kinos_decision(citizen, existing_grievances)
            
            # Process the decision
            if decision:
                self.process_kinos_decision(citizen, decision, existing_grievances)
                
                # Update existing grievances if new one was filed
                if decision.get('action') == 'file_grievance':
                    existing_grievances = self.get_existing_grievances()
        
        # Display results
        self.display_results()
    
    def display_results(self):
        """Display comprehensive test results."""
        log.info("\n" + "="*60)
        log.info("KINOS GRIEVANCE SYSTEM TEST RESULTS")
        log.info("="*60)
        
        # KinOS Decisions
        log.info(f"\nKinOS Decisions Made: {len(self.results['kinos_decisions'])}")
        for decision_data in self.results['kinos_decisions']:
            citizen = decision_data['citizen']
            social_class = decision_data['social_class']
            decision = decision_data['decision']
            
            log.info(f"\n• {citizen} ({social_class}):")
            log.info(f"  Action: {decision.get('action')}")
            if decision.get('action') == 'file_grievance':
                log.info(f"  Title: {decision.get('title')}")
                log.info(f"  Category: {decision.get('category')}")
            elif decision.get('action') == 'support_grievance':
                log.info(f"  Support: {decision.get('support_amount')} ducats")
            log.info(f"  Reasoning: {decision.get('reasoning')[:100]}...")
        
        # Grievances Filed
        log.info(f"\n\nGrievances Filed: {len(self.results['grievances_filed'])}")
        for g in self.results['grievances_filed']:
            log.info(f"  • {g['title']} ({g['category']}) by {g['citizen']}")
        
        # Grievances Supported
        log.info(f"\nGrievances Supported: {len(self.results['grievances_supported'])}")
        for s in self.results['grievances_supported']:
            log.info(f"  • {s['citizen']} supported with {s['amount']} ducats")
        
        # Current System State
        try:
            all_grievances = self.tables['GRIEVANCES'].all()
            log.info(f"\n\nTotal Grievances in System: {len(all_grievances)}")
            
            # Show recent grievances with KinOS-generated content
            recent = sorted(all_grievances, 
                          key=lambda g: g['fields'].get('FiledAt', ''), 
                          reverse=True)[:5]
            
            if recent:
                log.info("\nRecent Grievances (showing actual KinOS-generated content):")
                for g in recent:
                    f = g['fields']
                    log.info(f"\n  Title: {f.get('Title')}")
                    log.info(f"  Category: {f.get('Category')}")
                    log.info(f"  Filed by: {f.get('Citizen')}")
                    log.info(f"  Support: {f.get('SupportCount', 0)} citizens")
                    log.info(f"  Description: {f.get('Description', '')[:150]}...")
                    
        except Exception as e:
            log.error(f"Could not fetch grievance stats: {e}")
        
        # Errors
        if self.results['errors']:
            log.error(f"\n\nErrors Encountered: {len(self.results['errors'])}")
            for error in self.results['errors']:
                log.error(f"  ✗ {error}")
        else:
            log.info("\n\n✓ Test completed without errors!")
        
        log.info("\n" + "="*60)
        log.info("This test demonstrates how AI citizens use KinOS to develop")
        log.info("authentic political consciousness and express genuine grievances")
        log.info("based on their lived experiences in Venice.")
        log.info("="*60)


def main():
    """Run the KinOS grievance test."""
    tester = KinOSGrievanceTester()
    tester.run_complete_test()


if __name__ == "__main__":
    main()
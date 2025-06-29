#!/usr/bin/env python3
"""
Test the grievance system with mock KinOS responses to demonstrate functionality.
"""

import os
import sys
import json
import logging
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
from engine.activity_processors.file_grievance_processor import process_file_grievance_activity
from engine.activity_processors.support_grievance_processor import process_support_grievance_activity

# Configuration
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
VENICE_TIMEZONE = pytz.timezone('Europe/Rome')


# Mock KinOS responses by social class
MOCK_KINOS_GRIEVANCES = {
    'Facchini': {
        'action': 'file_grievance',
        'category': 'economic',
        'title': 'Starvation Wages at the Arsenale',
        'description': 'We who build Venice\'s great ships earn barely enough for bread! While merchants profit from our labor, our children go hungry. The guild masters say there is no money, yet I see them in silk robes. We demand fair wages for honest work!',
        'reasoning': 'As a dock worker, I see the wealth flowing through Venice but none reaches us who do the heavy lifting.'
    },
    'Popolani': {
        'action': 'file_grievance',
        'category': 'infrastructure',
        'title': 'Dangerous Bridges in San Polo',
        'description': 'Three bridges in our quarter are rotting and dangerous. Last week, old Marco fell through loose planks into the canal! We pay our taxes yet the city ignores our neighborhoods while decorating palaces. Fix our bridges before someone dies!',
        'reasoning': 'My family crosses these bridges daily. The risk is real and the neglect is shameful.'
    },
    'Cittadini': {
        'action': 'file_grievance',
        'category': 'economic',
        'title': 'Guild Monopolies Strangle Innovation',
        'description': 'The ancient guild laws prevent skilled citizens from practicing trades freely. I trained in glassmaking but cannot open a shop without guild approval - which they deny to protect their monopoly. Venice prospers through innovation, not protectionism!',
        'reasoning': 'As an educated citizen, I see how guild restrictions harm our economy and prevent social mobility.'
    },
    'Mercatores': {
        'action': 'file_grievance', 
        'category': 'criminal',
        'title': 'Contract Fraud Ruins Honest Merchants',
        'description': 'Foreign traders break contracts with impunity while Venetian merchants suffer losses. The courts move too slowly and favor those with connections. Last month I lost 5000 ducats to a Genoese who fled after taking my goods. We need swift commercial justice!',
        'reasoning': 'My business suffers from the lack of contract enforcement. This threatens all of Venice\'s trade.'
    },
    'Artisti': {
        'action': 'file_grievance',
        'category': 'social',
        'title': 'Venice Abandons Its Artists',
        'description': 'Once Venice led the world in art and beauty. Now our workshops close for lack of patronage while wealthy citizens buy foreign art. Young artists flee to Florence and Rome. Support local artists or watch Venice\'s cultural soul die!',
        'reasoning': 'As an artist, I see talented colleagues leaving daily. Venice loses more than coins - it loses its spirit.'
    },
    'Scientisti': {
        'action': 'file_grievance',
        'category': 'social', 
        'title': 'Suppression of Natural Philosophy',
        'description': 'While other cities build universities and observatories, Venice clings to superstition. My research into optics could improve navigation and trade, yet I work in secret, fearing accusations of sorcery. Fund science or fall behind the world!',
        'reasoning': 'As a natural philosopher, I see Venice losing the race for knowledge. Our rivals invest in science while we stagnate.'
    },
    'Nobili': {
        'action': 'file_grievance',
        'category': 'economic',
        'title': 'Foreign Merchants Evade Duties',
        'description': 'New foreign trading houses use complex arrangements to avoid customs duties that Venetian merchants must pay. This unfair advantage undermines established families who built Venice\'s wealth. Enforce equal taxation or watch our commerce crumble!',
        'reasoning': 'My family has traded honorably for centuries. These new practices threaten the old order that made Venice great.'
    }
}


class MockKinOSGrievanceTester:
    """Test grievance system with mock KinOS responses."""
    
    def __init__(self):
        self.tables = {}
        self.results = {
            'mock_decisions': [],
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
    
    def select_diverse_citizens(self) -> List[Dict[str, Any]]:
        """Select one citizen from each social class."""
        try:
            all_citizens = self.tables['CITIZENS'].all()
            selected = []
            
            # Get one from each class that has mock data
            for social_class in MOCK_KINOS_GRIEVANCES.keys():
                candidates = [
                    c for c in all_citizens
                    if c['fields'].get('SocialClass') == social_class
                    and c['fields'].get('Ducats', 0) > 100
                    and c['fields'].get('IsAI', True)
                ]
                if candidates:
                    selected.append(random.choice(candidates))
            
            log.info(f"\n✓ Selected {len(selected)} citizens representing different social classes:")
            for c in selected:
                f = c['fields']
                log.info(f"  • {f.get('Name')} ({f.get('SocialClass')}) - "
                        f"{f.get('Ducats', 0):.0f} ducats")
            
            return selected
            
        except Exception as e:
            log.error(f"✗ Failed to select citizens: {e}")
            return []
    
    def get_mock_kinos_decision(self, citizen: Dict[str, Any]) -> Dict[str, Any]:
        """Get mock KinOS decision based on social class."""
        social_class = citizen['fields'].get('SocialClass')
        
        # Get the mock response for this class
        if social_class in MOCK_KINOS_GRIEVANCES:
            return MOCK_KINOS_GRIEVANCES[social_class].copy()
        else:
            # Default response for unknown classes
            return {
                'action': 'none',
                'reasoning': 'I need more time to consider my grievances.'
            }
    
    def process_grievance_filing(self, citizen: Dict[str, Any], decision: Dict[str, Any]):
        """Process a file_grievance decision."""
        venice_time = datetime.now(VENICE_TIMEZONE)
        fields = citizen['fields']
        username = fields.get('Username')
        name = fields.get('Name', username)
        
        # Create mock activity
        activity = {
            'id': f'mock_file_{username}',
            'fields': {
                'ActivityId': f'mock_file_grievance_{username}',
                'Citizen': username,
                'Type': 'file_grievance',
                'Status': 'concluded',
                'DetailsJSON': json.dumps({
                    'filing_fee': 50,
                    'grievance_category': decision.get('category'),
                    'grievance_title': decision.get('title'),
                    'grievance_description': decision.get('description')
                })
            }
        }
        
        log.info(f"\nProcessing grievance filing by {name}...")
        log.info(f"  Title: {decision.get('title')}")
        log.info(f"  Category: {decision.get('category')}")
        
        try:
            success = process_file_grievance_activity(
                tables=self.tables,
                activity=activity['fields'],
                venice_time=venice_time
            )
            
            if success:
                log.info("  ✓ Successfully filed grievance")
                self.results['grievances_filed'].append({
                    'citizen': name,
                    'social_class': fields.get('SocialClass'),
                    'title': decision.get('title'),
                    'category': decision.get('category')
                })
            else:
                log.error("  ✗ Failed to file grievance")
                
        except Exception as e:
            log.error(f"  ✗ Error filing grievance: {e}")
            self.results['errors'].append(f"File grievance for {name}: {e}")
    
    def process_support_decision(self, citizen: Dict[str, Any], grievance_to_support: Dict[str, Any]):
        """Process a support_grievance decision."""
        venice_time = datetime.now(VENICE_TIMEZONE)
        fields = citizen['fields']
        username = fields.get('Username')
        name = fields.get('Name', username)
        
        # Determine support amount based on wealth
        wealth = fields.get('Ducats', 0)
        if wealth > 10000:
            support_amount = random.randint(50, 200)
        elif wealth > 1000:
            support_amount = random.randint(20, 50)
        else:
            support_amount = random.randint(10, 20)
        
        activity = {
            'id': f'mock_support_{username}',
            'fields': {
                'ActivityId': f'mock_support_grievance_{username}',
                'Citizen': username,
                'Type': 'support_grievance',
                'Status': 'concluded',
                'DetailsJSON': json.dumps({
                    'grievance_id': grievance_to_support.get('id', grievance_to_support.get('GrievanceId')),
                    'support_amount': support_amount,
                    'supporter_class': fields.get('SocialClass')
                })
            }
        }
        
        log.info(f"\nProcessing support by {name}...")
        log.info(f"  Supporting: {grievance_to_support.get('Title')}")
        log.info(f"  Amount: {support_amount} ducats")
        
        try:
            success = process_support_grievance_activity(
                tables=self.tables,
                activity=activity['fields'],
                venice_time=venice_time
            )
            
            if success:
                log.info("  ✓ Successfully supported grievance")
                self.results['grievances_supported'].append({
                    'citizen': name,
                    'amount': support_amount,
                    'grievance': grievance_to_support.get('Title')
                })
            else:
                log.error("  ✗ Failed to support grievance")
                
        except Exception as e:
            log.error(f"  ✗ Error supporting grievance: {e}")
            self.results['errors'].append(f"Support grievance for {name}: {e}")
    
    def run_test(self):
        """Run the complete mock test."""
        log.info("=== Starting Mock KinOS Grievance System Test ===\n")
        log.info("This test demonstrates the grievance system with realistic")
        log.info("AI-generated content based on social class perspectives.\n")
        
        # Initialize tables
        if not self.initialize_tables():
            return
        
        # Select citizens
        test_citizens = self.select_diverse_citizens()
        if not test_citizens:
            log.error("✗ No suitable test citizens found")
            return
        
        # Phase 1: File grievances
        log.info("\n=== Phase 1: Filing Grievances ===")
        for citizen in test_citizens:
            decision = self.get_mock_kinos_decision(citizen)
            self.results['mock_decisions'].append({
                'citizen': citizen['fields'].get('Name'),
                'social_class': citizen['fields'].get('SocialClass'),
                'decision': decision
            })
            
            if decision.get('action') == 'file_grievance':
                self.process_grievance_filing(citizen, decision)
        
        # Phase 2: Support grievances
        log.info("\n=== Phase 2: Supporting Grievances ===")
        
        # Get newly created grievances
        try:
            all_grievances = self.tables['GRIEVANCES'].all()
            if all_grievances:
                # Have some citizens support grievances
                support_citizens = random.sample(test_citizens, min(3, len(test_citizens)))
                
                for citizen in support_citizens:
                    # Pick a random grievance to support
                    grievance = random.choice(all_grievances)
                    self.process_support_decision(citizen, grievance['fields'])
        except Exception as e:
            log.error(f"Error in support phase: {e}")
        
        # Display results
        self.display_results()
    
    def display_results(self):
        """Display test results."""
        log.info("\n" + "="*60)
        log.info("MOCK KINOS GRIEVANCE TEST RESULTS")
        log.info("="*60)
        
        # Show decisions
        log.info(f"\nMock KinOS Decisions: {len(self.results['mock_decisions'])}")
        for data in self.results['mock_decisions']:
            log.info(f"\n• {data['citizen']} ({data['social_class']}):")
            decision = data['decision']
            if decision.get('action') == 'file_grievance':
                log.info(f"  Filed: \"{decision.get('title')}\"")
                log.info(f"  Category: {decision.get('category')}")
                log.info(f"  Reasoning: {decision.get('reasoning')}")
        
        # Grievances filed
        log.info(f"\n\nGrievances Successfully Filed: {len(self.results['grievances_filed'])}")
        for g in self.results['grievances_filed']:
            log.info(f"  • \"{g['title']}\" ({g['category']}) by {g['citizen']} ({g['social_class']})")
        
        # Support given
        log.info(f"\nSupport Given: {len(self.results['grievances_supported'])}")
        for s in self.results['grievances_supported']:
            log.info(f"  • {s['citizen']} supported \"{s['grievance']}\" with {s['amount']} ducats")
        
        # Current system state
        try:
            all_grievances = self.tables['GRIEVANCES'].all()
            log.info(f"\n\nTotal Grievances in System: {len(all_grievances)}")
            
            # Show all grievances with support counts
            if all_grievances:
                log.info("\nAll Grievances (ordered by support):")
                sorted_grievances = sorted(all_grievances, 
                                         key=lambda g: g['fields'].get('SupportCount', 0), 
                                         reverse=True)
                
                for g in sorted_grievances:
                    f = g['fields']
                    log.info(f"\n  • \"{f.get('Title')}\"")
                    log.info(f"    Category: {f.get('Category')} | Filed by: {f.get('Citizen')}")
                    log.info(f"    Support: {f.get('SupportCount', 0)} citizens")
                    log.info(f"    Status: {f.get('Status', 'filed')}")
                    desc = f.get('Description', '')
                    if desc:
                        log.info(f"    Description: {desc[:100]}...")
                    
        except Exception as e:
            log.error(f"Could not fetch system stats: {e}")
        
        # Errors
        if self.results['errors']:
            log.error(f"\n\nErrors: {len(self.results['errors'])}")
            for error in self.results['errors']:
                log.error(f"  ✗ {error}")
        else:
            log.info("\n\n✓ Test completed successfully!")
        
        log.info("\n" + "="*60)
        log.info("This demonstrates how different social classes express")
        log.info("authentic grievances based on their lived experiences.")
        log.info("="*60)


def main():
    """Run the mock test."""
    tester = MockKinOSGrievanceTester()
    tester.run_test()


if __name__ == "__main__":
    main()
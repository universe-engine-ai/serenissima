#!/usr/bin/env python3
"""
Instant test script for the grievance system.

This script:
1. Selects test citizens (both AI and simulated human)
2. Creates grievance activities through the activity system
3. Immediately processes the activities
4. Displays the results

Run with: python test_grievance_system_instant.py
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
import pytz
import random
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
# Also add the grandparent directory for backend imports
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

# Import required modules
from pyairtable import Table
from backend.app.config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    VENICE_TIMEZONE
)
from backend.engine.activity_processors.file_grievance_processor import process_file_grievance_activity
from backend.engine.activity_processors.support_grievance_processor import process_support_grievance_activity
from backend.engine.utils.activity_helpers import create_activity_record

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://serenissima.ai/api")
LOCAL_API_URL = os.getenv("LOCAL_API_URL", "http://localhost:8000/api")


class GrievanceSystemTester:
    """Test harness for the grievance system."""
    
    def __init__(self, use_local_api=True):
        """Initialize the tester."""
        self.api_url = LOCAL_API_URL if use_local_api else API_BASE_URL
        self.tables = {}
        self.test_results = {
            'citizens_tested': [],
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
            log.info("✓ Initialized all Airtable connections")
            return True
        except Exception as e:
            log.error(f"✗ Failed to initialize tables: {e}")
            self.test_results['errors'].append(f"Table initialization: {e}")
            return False
    
    def select_test_citizens(self, count=5) -> List[Dict[str, Any]]:
        """Select a diverse set of citizens for testing."""
        try:
            all_citizens = self.tables['CITIZENS'].all()
            
            # Filter for citizens with different social classes and sufficient wealth
            test_candidates = []
            social_classes = ['Facchini', 'Popolani', 'Cittadini', 'Mercatores', 'Artisti', 'Scientisti', 'Nobili']
            
            for social_class in social_classes:
                class_citizens = [
                    c for c in all_citizens 
                    if c['fields'].get('SocialClass') == social_class 
                    and c['fields'].get('Wealth', 0) > 100  # Can afford fees
                    and c['fields'].get('IsAI', True)  # Prefer AI citizens for testing
                ]
                if class_citizens:
                    # Pick one from each class if available
                    test_candidates.append(random.choice(class_citizens))
            
            # If we don't have enough, add more
            while len(test_candidates) < count and len(all_citizens) > len(test_candidates):
                citizen = random.choice(all_citizens)
                if citizen not in test_candidates and citizen['fields'].get('Wealth', 0) > 100:
                    test_candidates.append(citizen)
            
            selected = test_candidates[:count]
            log.info(f"✓ Selected {len(selected)} test citizens:")
            for c in selected:
                fields = c['fields']
                log.info(f"  - {fields.get('Name')} ({fields.get('SocialClass')}) - {fields.get('Wealth', 0)} ducats")
            
            return selected
            
        except Exception as e:
            log.error(f"✗ Failed to select citizens: {e}")
            self.test_results['errors'].append(f"Citizen selection: {e}")
            return []
    
    def find_doges_palace(self) -> Optional[Dict[str, Any]]:
        """Find the Doge's Palace building."""
        try:
            for building in self.tables['BUILDINGS'].all():
                if building['fields'].get('BuildingType') == 'doges_palace':
                    return building['fields']
            
            log.warning("Doge's Palace not found, using first palazzo as fallback")
            # Fallback to any palazzo
            for building in self.tables['BUILDINGS'].all():
                if 'palazzo' in building['fields'].get('BuildingType', '').lower():
                    return building['fields']
            
            return None
        except Exception as e:
            log.error(f"Failed to find Doge's Palace: {e}")
            return None
    
    def create_file_grievance_activity(self, citizen: Dict[str, Any], grievance_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a file_grievance activity for a citizen."""
        try:
            citizen_fields = citizen['fields']
            citizen_username = citizen_fields.get('Username')
            
            # Find Doge's Palace
            palace = self.find_doges_palace()
            if not palace:
                log.error("Cannot create grievance activity without Doge's Palace")
                return None
            
            palace_id = palace.get('BuildingId')
            
            # Create activity using the API
            activity_data = {
                "citizenUsername": citizen_username,
                "activityType": "file_grievance",
                "buildingId": palace_id,
                "details": {
                    "filing_fee": 50,
                    "grievance_category": grievance_data['category'],
                    "grievance_title": grievance_data['title'],
                    "grievance_description": grievance_data['description']
                }
            }
            
            # Try to create via API first
            try:
                response = requests.post(
                    f"{self.api_url}/activities/try-create",
                    json=activity_data
                )
                if response.status_code == 200:
                    activity = response.json()
                    log.info(f"✓ Created file_grievance activity via API for {citizen_fields.get('Name')}")
                    return activity
            except:
                pass
            
            # Fallback: Create directly in Airtable
            now_utc = datetime.now(pytz.utc)
            end_utc = now_utc + timedelta(minutes=30)
            
            activity_record = {
                'Citizen': citizen_username,
                'Type': 'file_grievance',
                'Status': 'concluded',  # Set as concluded for immediate processing
                'FromBuildingId': palace_id,
                'ToBuildingId': palace_id,
                'StartDateFull': now_utc.isoformat(),
                'EndDateFull': end_utc.isoformat(),
                'Title': f"Filing Grievance: {grievance_data['title']}",
                'Description': f"{citizen_fields.get('Name')} files a formal grievance",
                'DetailsJSON': json.dumps({
                    'filing_fee': 50,
                    'grievance_category': grievance_data['category'],
                    'grievance_title': grievance_data['title'],
                    'grievance_description': grievance_data['description']
                })
            }
            
            created = self.tables['ACTIVITIES'].create(activity_record)
            log.info(f"✓ Created file_grievance activity directly for {citizen_fields.get('Name')}")
            return created
            
        except Exception as e:
            log.error(f"✗ Failed to create file_grievance activity: {e}")
            self.test_results['errors'].append(f"File grievance activity: {e}")
            return None
    
    def create_support_grievance_activity(self, citizen: Dict[str, Any], grievance_id: str, amount: int = 10) -> Optional[Dict[str, Any]]:
        """Create a support_grievance activity for a citizen."""
        try:
            citizen_fields = citizen['fields']
            citizen_username = citizen_fields.get('Username')
            
            # Find Doge's Palace
            palace = self.find_doges_palace()
            if not palace:
                log.error("Cannot create support activity without Doge's Palace")
                return None
            
            palace_id = palace.get('BuildingId')
            
            # Create activity directly in Airtable (as concluded for immediate processing)
            now_utc = datetime.now(pytz.utc)
            end_utc = now_utc + timedelta(minutes=10)
            
            activity_record = {
                'Citizen': citizen_username,
                'Type': 'support_grievance',
                'Status': 'concluded',  # Set as concluded for immediate processing
                'FromBuildingId': palace_id,
                'ToBuildingId': palace_id,
                'StartDateFull': now_utc.isoformat(),
                'EndDateFull': end_utc.isoformat(),
                'Title': f"Supporting Grievance #{grievance_id}",
                'Description': f"{citizen_fields.get('Name')} supports a grievance",
                'DetailsJSON': json.dumps({
                    'grievance_id': grievance_id,
                    'support_amount': amount,
                    'supporter_class': citizen_fields.get('SocialClass', 'Popolani'),
                    'supporter_wealth': citizen_fields.get('Wealth', 0)
                })
            }
            
            created = self.tables['ACTIVITIES'].create(activity_record)
            log.info(f"✓ Created support_grievance activity for {citizen_fields.get('Name')}")
            return created
            
        except Exception as e:
            log.error(f"✗ Failed to create support_grievance activity: {e}")
            self.test_results['errors'].append(f"Support grievance activity: {e}")
            return None
    
    def generate_test_grievances(self, social_class: str) -> Dict[str, Any]:
        """Generate test grievance data based on social class."""
        grievances_by_class = {
            'Facchini': {
                'category': 'economic',
                'title': 'Starvation Wages at the Docks',
                'description': 'We labor from dawn to dusk loading ships, yet our wages cannot buy bread for our children. The merchant princes grow fat on our sweat while we starve!'
            },
            'Popolani': {
                'category': 'infrastructure',
                'title': 'Crumbling Bridges in Our Quarter',
                'description': 'The bridges in the workers\' districts are falling apart while gold is spent on palace decorations. We demand safe passage for our families!'
            },
            'Cittadini': {
                'category': 'economic',
                'title': 'Unfair Guild Restrictions',
                'description': 'The ancient guild monopolies strangle innovation and prevent honest citizens from pursuing their trades. We need economic freedom!'
            },
            'Mercatores': {
                'category': 'criminal',
                'title': 'Contract Fraud Goes Unpunished',
                'description': 'Broken contracts and fraudulent dealings plague our markets, yet the courts do nothing. We demand swift commercial justice!'
            },
            'Artisti': {
                'category': 'social',
                'title': 'Death of Venetian Culture',
                'description': 'Without patronage, our artists flee to foreign courts. Venice loses its soul when it abandons those who create beauty!'
            },
            'Scientisti': {
                'category': 'social',
                'title': 'Research Strangled by Ignorance',
                'description': 'While other cities build universities and laboratories, Venice clings to superstition. Fund science or fall behind!'
            },
            'Nobili': {
                'category': 'criminal',
                'title': 'Foreign Merchants Evade Taxes',
                'description': 'These new traders use legal loopholes to avoid their fair share while established families bear the burden. Enforce equal taxation!'
            }
        }
        
        return grievances_by_class.get(social_class, {
            'category': 'social',
            'title': 'Citizens Demand a Voice',
            'description': 'We who make Venice great deserve representation in its governance. Our voices matter!'
        })
    
    def process_activities_immediately(self, activities: List[Dict[str, Any]]):
        """Process activities immediately without waiting."""
        log.info("\n=== Processing Activities ===")
        
        venice_time = datetime.now(VENICE_TIMEZONE)
        
        for activity in activities:
            try:
                activity_type = activity['fields'].get('Type')
                activity_id = activity['id']
                
                if activity_type == 'file_grievance':
                    log.info(f"\nProcessing file_grievance activity {activity_id}...")
                    success = process_file_grievance_activity(
                        tables=self.tables,
                        activity=activity['fields'],
                        venice_time=venice_time
                    )
                    if success:
                        log.info("✓ Successfully processed file_grievance")
                        self.test_results['grievances_filed'].append(activity)
                    else:
                        log.error("✗ Failed to process file_grievance")
                        self.test_results['errors'].append(f"Process file_grievance {activity_id}")
                        
                elif activity_type == 'support_grievance':
                    log.info(f"\nProcessing support_grievance activity {activity_id}...")
                    success = process_support_grievance_activity(
                        tables=self.tables,
                        activity=activity['fields'],
                        venice_time=venice_time
                    )
                    if success:
                        log.info("✓ Successfully processed support_grievance")
                        self.test_results['grievances_supported'].append(activity)
                    else:
                        log.error("✗ Failed to process support_grievance")
                        self.test_results['errors'].append(f"Process support_grievance {activity_id}")
                        
            except Exception as e:
                log.error(f"✗ Error processing activity {activity.get('id')}: {e}")
                self.test_results['errors'].append(f"Activity processing: {e}")
    
    def display_results(self):
        """Display comprehensive test results."""
        log.info("\n" + "="*60)
        log.info("GRIEVANCE SYSTEM TEST RESULTS")
        log.info("="*60)
        
        # Citizens tested
        log.info(f"\nCitizens Tested: {len(self.test_results['citizens_tested'])}")
        for citizen in self.test_results['citizens_tested']:
            fields = citizen['fields']
            log.info(f"  • {fields.get('Name')} ({fields.get('SocialClass')})")
        
        # Grievances filed
        log.info(f"\nGrievances Filed: {len(self.test_results['grievances_filed'])}")
        for activity in self.test_results['grievances_filed']:
            fields = activity['fields']
            details = json.loads(fields.get('DetailsJSON', '{}'))
            log.info(f"  • {details.get('grievance_title')} ({details.get('grievance_category')})")
            log.info(f"    Filed by: {fields.get('Citizen')}")
        
        # Grievances supported
        log.info(f"\nGrievances Supported: {len(self.test_results['grievances_supported'])}")
        for activity in self.test_results['grievances_supported']:
            fields = activity['fields']
            details = json.loads(fields.get('DetailsJSON', '{}'))
            log.info(f"  • Grievance #{details.get('grievance_id')}")
            log.info(f"    Supporter: {fields.get('Citizen')} ({details.get('support_amount')} ducats)")
        
        # Check grievances in database
        if 'GRIEVANCES' in self.tables:
            try:
                all_grievances = self.tables['GRIEVANCES'].all()
                log.info(f"\nTotal Grievances in Database: {len(all_grievances)}")
                
                # Show top grievances by support
                if all_grievances:
                    sorted_grievances = sorted(all_grievances, key=lambda g: g['fields'].get('SupportCount', 0), reverse=True)
                    log.info("\nTop Grievances by Support:")
                    for g in sorted_grievances[:5]:
                        fields = g['fields']
                        log.info(f"  • {fields.get('Title')} - {fields.get('SupportCount', 0)} supporters")
                        log.info(f"    Category: {fields.get('Category')} | Status: {fields.get('Status')}")
            except:
                pass
        
        # Errors
        if self.test_results['errors']:
            log.error(f"\nErrors Encountered: {len(self.test_results['errors'])}")
            for error in self.test_results['errors']:
                log.error(f"  ✗ {error}")
        else:
            log.info("\n✓ No errors encountered!")
        
        # API Status
        try:
            response = requests.get(f"{self.api_url}/governance/stats")
            if response.status_code == 200:
                stats = response.json()
                log.info("\n=== Governance System Stats ===")
                log.info(f"Total Grievances: {stats.get('total_grievances', 0)}")
                log.info(f"Total Supporters: {stats.get('total_supporters', 0)}")
                log.info(f"Total Support Ducats: {stats.get('total_support_ducats', 0)}")
                
                if stats.get('grievances_by_category'):
                    log.info("\nGrievances by Category:")
                    for category, count in stats['grievances_by_category'].items():
                        log.info(f"  • {category}: {count}")
        except:
            log.warning("Could not fetch governance stats from API")
    
    def run_complete_test(self):
        """Run a complete test of the grievance system."""
        log.info("=== Starting Complete Grievance System Test ===\n")
        
        # Initialize tables
        if not self.initialize_tables():
            log.error("Failed to initialize tables. Exiting.")
            return
        
        # Select test citizens
        test_citizens = self.select_test_citizens(5)
        if not test_citizens:
            log.error("No test citizens selected. Exiting.")
            return
        
        self.test_results['citizens_tested'] = test_citizens
        
        # Create activities
        all_activities = []
        first_grievance_id = None
        
        # Phase 1: File grievances
        log.info("\n=== Phase 1: Filing Grievances ===")
        for i, citizen in enumerate(test_citizens[:3]):  # First 3 file grievances
            grievance_data = self.generate_test_grievances(
                citizen['fields'].get('SocialClass', 'Popolani')
            )
            
            activity = self.create_file_grievance_activity(citizen, grievance_data)
            if activity:
                all_activities.append(activity)
                # Store first grievance ID for support phase
                if i == 0 and not first_grievance_id:
                    # In real system, processor would create grievance record
                    # For testing, we'll use a mock ID
                    first_grievance_id = f"test_grievance_{citizen['fields'].get('Username')}"
        
        # Process filing activities
        if all_activities:
            self.process_activities_immediately(all_activities)
        
        # Phase 2: Support grievances
        log.info("\n=== Phase 2: Supporting Grievances ===")
        support_activities = []
        
        # Get actual grievance IDs from database if available
        try:
            if 'GRIEVANCES' in self.tables:
                recent_grievances = self.tables['GRIEVANCES'].all()
                if recent_grievances:
                    first_grievance_id = recent_grievances[0]['id']
        except:
            pass
        
        if first_grievance_id:
            for citizen in test_citizens[2:]:  # Last 3 support grievances
                support_amount = random.randint(10, 50)
                activity = self.create_support_grievance_activity(
                    citizen, first_grievance_id, support_amount
                )
                if activity:
                    support_activities.append(activity)
        
        # Process support activities
        if support_activities:
            self.process_activities_immediately(support_activities)
        
        # Display results
        self.display_results()
        
        log.info("\n=== Test Complete ===")
        log.info("The grievance system has been tested end-to-end.")
        log.info("Check the Airtable for created records and the logs for details.")


def main():
    """Main test function."""
    # Load environment variables
    load_dotenv()
    
    # Check if running locally or against production
    use_local = input("Test against local API? (y/n, default=y): ").lower() != 'n'
    
    # Create and run tester
    tester = GrievanceSystemTester(use_local_api=use_local)
    tester.run_complete_test()


if __name__ == "__main__":
    main()
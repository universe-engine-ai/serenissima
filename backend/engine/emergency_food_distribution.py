#!/usr/bin/env python3
"""
Emergency Food Distribution System for La Serenissima.

This script implements "La Mensa del Doge" (The Doge's Table) - a Renaissance-authentic
public feeding system that prevents mass starvation while maintaining citizen dignity.

This system:
1. Monitors hunger levels across the population
2. Activates when >5% of citizens are hungry
3. Distributes charity food through historical Scuole Grandi buildings
4. Maintains closed-loop economy by deducting costs from treasury
5. Creates social gathering opportunities at distribution points

Run this script periodically (every hour) to prevent starvation crises.
"""

import os
import sys
import logging
import argparse
import json
import datetime
import pytz
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pyairtable import Table
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("emergency_food_distribution")

# Load environment variables
load_dotenv()

# Add project root to sys.path for backend imports
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import LogColors, log_header

# Constants
HUNGER_CRISIS_THRESHOLD = 0.05  # 5% of population
CHARITY_BREAD_COST = 2.0  # Ducats per unit
CHARITY_SOUP_COST = 1.5  # Ducats per unit
BREAD_PER_HUNGRY_CITIZEN = 0.2  # Units of bread per hungry citizen
SOUP_PER_HUNGRY_CITIZEN = 0.1  # Units of soup per hungry citizen

# Scuole Grandi (historical Venetian charity institutions)
SCUOLE_GRANDI_BUILDING_IDS = [
    "building_45.437644_12.335422",  # Piazza San Marco area
    "building_45.431389_12.338889",  # Rialto area
    "building_45.429444_12.326944",  # Zattere area
    "building_45.440000_12.350000",  # Castello area
    "building_45.445000_12.320000"   # Cannaregio area
]

def initialize_airtable() -> Dict[str, Table]:
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID.")
        sys.exit(1)
    
    try:
        return {
            'citizens': Table(api_key, base_id, 'CITIZENS'),
            'buildings': Table(api_key, base_id, 'BUILDINGS'),
            'resources': Table(api_key, base_id, 'RESOURCES'),
            'activities': Table(api_key, base_id, 'ACTIVITIES'),
            'notifications': Table(api_key, base_id, 'NOTIFICATIONS'),
            'transactions': Table(api_key, base_id, 'TRANSACTIONS'),
            'problems': Table(api_key, base_id, 'PROBLEMS')
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)

def get_hungry_citizens(tables: Dict[str, Table]) -> List[Dict]:
    """Get all citizens who haven't eaten in over 24 hours."""
    log.info("Fetching hungry citizens...")
    
    try:
        # Get all citizens
        all_citizens = tables['citizens'].all()
        
        # Current time in UTC
        now_utc = datetime.datetime.now(pytz.UTC)
        hunger_threshold = now_utc - datetime.timedelta(hours=24)
        
        hungry_citizens = []
        for citizen in all_citizens:
            fields = citizen['fields']
            ate_at_str = fields.get('AteAt')
            
            # If no AteAt record or it's older than 24 hours, citizen is hungry
            is_hungry = True
            if ate_at_str:
                try:
                    ate_at_dt = datetime.datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
                    if ate_at_dt.tzinfo is None:
                        ate_at_dt = pytz.UTC.localize(ate_at_dt)
                    if ate_at_dt > hunger_threshold:
                        is_hungry = False
                except ValueError:
                    log.warning(f"Invalid AteAt date for citizen {fields.get('Username', 'Unknown')}: {ate_at_str}")
            
            if is_hungry:
                hungry_citizens.append(citizen)
        
        log.info(f"Found {len(hungry_citizens)} hungry citizens out of {len(all_citizens)} total")
        return hungry_citizens
        
    except Exception as e:
        log.error(f"Error fetching hungry citizens: {e}")
        return []

def get_scuole_grandi_buildings(tables: Dict[str, Table]) -> List[Dict]:
    """Get the Scuole Grandi buildings for charity distribution."""
    log.info("Fetching Scuole Grandi buildings...")
    
    scuole_buildings = []
    for building_id in SCUOLE_GRANDI_BUILDING_IDS:
        try:
            # Try to fetch by BuildingId
            formula = f"{{BuildingId}}='{building_id}'"
            buildings = tables['buildings'].all(formula=formula, max_records=1)
            
            if buildings:
                building = buildings[0]
                # Verify it's constructed and operational
                if building['fields'].get('IsConstructed'):
                    scuole_buildings.append(building)
                    log.info(f"Found Scuola Grande: {building['fields'].get('Name', building_id)}")
                else:
                    log.warning(f"Scuola Grande {building_id} is not constructed")
            else:
                log.warning(f"Scuola Grande building {building_id} not found")
                
        except Exception as e:
            log.error(f"Error fetching Scuola Grande {building_id}: {e}")
    
    return scuole_buildings

def get_treasury_balance(tables: Dict[str, Table]) -> Tuple[Optional[Dict], float]:
    """Get the ConsiglioDeiDieci treasury balance."""
    log.info("Fetching treasury balance...")
    
    try:
        # Find ConsiglioDeiDieci
        for name_variation in ["ConsiglioDeiDieci", "Consiglio Dei Dieci", "Consiglio dei Dieci"]:
            formula = f"{{Username}}='{name_variation}'"
            records = tables['citizens'].all(formula=formula, max_records=1)
            
            if records:
                treasury_record = records[0]
                balance = float(treasury_record['fields'].get('Ducats', 0))
                log.info(f"Treasury balance: {balance:.2f} Ducats")
                return treasury_record, balance
        
        log.error("ConsiglioDeiDieci treasury not found")
        return None, 0.0
        
    except Exception as e:
        log.error(f"Error fetching treasury: {e}")
        return None, 0.0

def calculate_distribution_cost(hungry_count: int) -> Tuple[float, Dict[str, float]]:
    """Calculate the cost and resources needed for emergency distribution."""
    resources_needed = {
        'pane_della_carità': hungry_count * BREAD_PER_HUNGRY_CITIZEN,
        'minestra_dei_poveri': hungry_count * SOUP_PER_HUNGRY_CITIZEN
    }
    
    total_cost = (
        resources_needed['pane_della_carità'] * CHARITY_BREAD_COST +
        resources_needed['minestra_dei_poveri'] * CHARITY_SOUP_COST
    )
    
    return total_cost, resources_needed

def create_charity_resources(tables: Dict[str, Table], building: Dict, resources: Dict[str, float]) -> bool:
    """Create charity food resources at a Scuola Grande building."""
    building_id = building['fields'].get('BuildingId', building['id'])
    building_name = building['fields'].get('Name', building_id)
    
    log.info(f"Creating charity resources at {building_name}...")
    
    try:
        now_utc = datetime.datetime.now(pytz.UTC)
        
        for resource_type, amount in resources.items():
            if amount <= 0:
                continue
                
            # Create the resource record
            resource_data = {
                'Type': resource_type,
                'Count': amount,
                'Owner': 'ConsiglioDeiDieci',  # Treasury owns charity resources
                'Asset': building_id,
                'AssetType': 'building',
                'Description': f'Emergency charity {resource_type.replace("_", " ")} for hungry citizens',
                'Tags': json.dumps(['charity', 'emergency', 'perishable']),
                'CreatedAt': now_utc.isoformat(),
                'ExpiresAt': (now_utc + datetime.timedelta(hours=24)).isoformat()  # 24 hour expiry
            }
            
            tables['resources'].create(resource_data)
            log.info(f"Created {amount:.2f} units of {resource_type} at {building_name}")
        
        return True
        
    except Exception as e:
        log.error(f"Error creating resources at {building_name}: {e}")
        return False

def create_charity_distribution_activity(tables: Dict[str, Table], building: Dict, resources: Dict[str, float]) -> bool:
    """Create a public activity announcing charity distribution."""
    building_id = building['fields'].get('BuildingId', building['id'])
    building_name = building['fields'].get('Name', building_id)
    position = building['fields'].get('Position', {})
    
    try:
        now_utc = datetime.datetime.now(pytz.UTC)
        
        # Create activity record for the announcement
        activity_data = {
            'Type': 'charity_distribution',
            'Status': 'active',
            'Building': building_id,
            'Position': json.dumps(position),
            'CreatedAt': now_utc.isoformat(),
            'StartDate': now_utc.isoformat(),
            'EndDate': (now_utc + datetime.timedelta(hours=4)).isoformat(),  # 4 hour distribution window
            'Description': f'Emergency food distribution at {building_name}',
            'Notes': json.dumps({
                'event_type': 'charity_distribution',
                'resources_available': resources,
                'distribution_point': building_name,
                'message': f"🍞 **Free Food Distribution** at {building_name}! The Doge's charity provides bread and soup for hungry citizens. Come with dignity, leave with sustenance."
            })
        }
        
        tables['activities'].create(activity_data)
        log.info(f"Created charity distribution activity at {building_name}")
        return True
        
    except Exception as e:
        log.error(f"Error creating distribution activity: {e}")
        return False

def notify_nearby_hungry_citizens(tables: Dict[str, Table], building: Dict, hungry_citizens: List[Dict], radius_meters: float = 500) -> int:
    """Send notifications to hungry citizens near distribution points."""
    building_pos = building['fields'].get('Position', {})
    building_lat = building_pos.get('lat')
    building_lng = building_pos.get('lng')
    building_name = building['fields'].get('Name', building['fields'].get('BuildingId'))
    
    if not building_lat or not building_lng:
        log.warning(f"Building {building_name} has no position")
        return 0
    
    notified_count = 0
    
    for citizen in hungry_citizens:
        citizen_pos = citizen['fields'].get('Position', {})
        citizen_lat = citizen_pos.get('lat')
        citizen_lng = citizen_pos.get('lng')
        
        if not citizen_lat or not citizen_lng:
            continue
        
        # Simple distance calculation (approximate for small distances)
        lat_diff = abs(building_lat - citizen_lat)
        lng_diff = abs(building_lng - citizen_lng)
        approx_distance = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111000  # Convert to meters (rough)
        
        if approx_distance <= radius_meters:
            try:
                notification_data = {
                    'Type': 'charity_food_available',
                    'Citizen': citizen['id'],
                    'Content': f"🍞 **Free Food Available!** Emergency distribution at {building_name}. Come quickly for bread and soup.",
                    'Details': json.dumps({
                        'event_type': 'charity_distribution',
                        'location': building_name,
                        'building_id': building['fields'].get('BuildingId'),
                        'position': building_pos,
                        'resources': ['pane_della_carità', 'minestra_dei_poveri']
                    }),
                    'CreatedAt': datetime.datetime.now(pytz.UTC).isoformat()
                }
                
                tables['notifications'].create(notification_data)
                notified_count += 1
                
            except Exception as e:
                log.error(f"Error notifying citizen {citizen['fields'].get('Username', 'Unknown')}: {e}")
    
    log.info(f"Notified {notified_count} hungry citizens near {building_name}")
    return notified_count

def update_treasury_balance(tables: Dict[str, Table], treasury_record: Dict, amount_to_deduct: float) -> bool:
    """Deduct distribution costs from treasury."""
    try:
        current_balance = float(treasury_record['fields'].get('Ducats', 0))
        new_balance = current_balance - amount_to_deduct
        
        tables['citizens'].update(treasury_record['id'], {
            'Ducats': new_balance
        })
        
        log.info(f"Deducted {amount_to_deduct:.2f} Ducats from treasury. New balance: {new_balance:.2f}")
        return True
        
    except Exception as e:
        log.error(f"Error updating treasury balance: {e}")
        return False

def create_distribution_transaction(tables: Dict[str, Table], amount: float, recipient_description: str) -> bool:
    """Create a transaction record for the charity distribution."""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        transaction_data = {
            'Type': 'charity_distribution',
            'Asset': f'emergency_food_{now}',
            'Seller': recipient_description,  # The hungry citizens (recipients)
            'Buyer': 'ConsiglioDeiDieci',  # Treasury (paying for charity)
            'Price': amount,
            'CreatedAt': now,
            'ExecutedAt': now,
            'Notes': json.dumps({
                'payment_type': 'emergency_charity_distribution',
                'payment_date': now,
                'purpose': 'Preventing mass starvation'
            })
        }
        
        tables['transactions'].create(transaction_data)
        log.info(f"Created transaction record for {amount:.2f} Ducats charity distribution")
        return True
        
    except Exception as e:
        log.error(f"Error creating transaction: {e}")
        return False

def record_distribution_problem(tables: Dict[str, Table], problem_type: str, description: str, severity: str = "Critical") -> bool:
    """Record a problem if distribution cannot proceed."""
    try:
        problem_data = {
            'ProblemId': f'emergency_food_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'Type': problem_type,
            'Severity': severity,
            'Status': 'new',
            'Title': f'Emergency Food Distribution: {problem_type}',
            'Description': description,
            'Solutions': 'Increase treasury funds, reduce distribution costs, or wait for economic recovery.',
            'CreatedAt': datetime.datetime.now(pytz.UTC).isoformat(),
            'Citizen': 'ConsiglioDeiDieci',
            'AssetType': 'system',
            'Asset': 'emergency_food_system'
        }
        
        tables['problems'].create(problem_data)
        log.warning(f"Recorded distribution problem: {problem_type}")
        return True
        
    except Exception as e:
        log.error(f"Error recording problem: {e}")
        return False

def distribute_emergency_food(dry_run: bool = False):
    """Main function to distribute emergency food when hunger crisis detected."""
    log_header("Emergency Food Distribution - La Mensa del Doge", LogColors.HEADER)
    
    tables = initialize_airtable()
    
    # Get hungry citizens
    hungry_citizens = get_hungry_citizens(tables)
    total_citizens = len(tables['citizens'].all())
    hunger_rate = len(hungry_citizens) / total_citizens if total_citizens > 0 else 0
    
    log.info(f"Hunger rate: {hunger_rate:.2%} ({len(hungry_citizens)}/{total_citizens} citizens)")
    
    # Check if we've reached crisis threshold
    if hunger_rate < HUNGER_CRISIS_THRESHOLD:
        log.info(f"Hunger rate below crisis threshold ({HUNGER_CRISIS_THRESHOLD:.0%}). No emergency distribution needed.")
        return
    
    log.warning(f"{LogColors.WARNING}HUNGER CRISIS DETECTED! {hunger_rate:.1%} of citizens are starving.{LogColors.ENDC}")
    
    # Get Scuole Grandi buildings
    scuole_buildings = get_scuole_grandi_buildings(tables)
    if not scuole_buildings:
        log.error("No Scuole Grandi buildings available for distribution!")
        record_distribution_problem(tables, "no_distribution_points", 
                                   f"Cannot distribute emergency food: No Scuole Grandi buildings found. {len(hungry_citizens)} citizens starving.")
        return
    
    # Get treasury balance
    treasury_record, treasury_balance = get_treasury_balance(tables)
    if not treasury_record:
        log.error("Cannot proceed without treasury!")
        return
    
    # Calculate distribution needs
    total_cost, total_resources = calculate_distribution_cost(len(hungry_citizens))
    
    log.info(f"Distribution plan:")
    log.info(f"  - Total hungry citizens: {len(hungry_citizens)}")
    log.info(f"  - Charity bread needed: {total_resources['pane_della_carità']:.2f} units")
    log.info(f"  - Charity soup needed: {total_resources['minestra_dei_poveri']:.2f} units")
    log.info(f"  - Total cost: {total_cost:.2f} Ducats")
    log.info(f"  - Treasury balance: {treasury_balance:.2f} Ducats")
    
    if treasury_balance < total_cost:
        log.error(f"Insufficient treasury funds! Need {total_cost:.2f}, have {treasury_balance:.2f}")
        record_distribution_problem(tables, "insufficient_funds",
                                   f"Treasury has {treasury_balance:.2f} Ducats but needs {total_cost:.2f} for emergency food. {len(hungry_citizens)} citizens starving.")
        return
    
    if dry_run:
        log.info("[DRY RUN] Would distribute:")
        for building in scuole_buildings:
            resources_per_location = {
                k: v / len(scuole_buildings) for k, v in total_resources.items()
            }
            log.info(f"  - At {building['fields'].get('Name', 'Unknown')}: {resources_per_location}")
        log.info(f"[DRY RUN] Would deduct {total_cost:.2f} Ducats from treasury")
        return
    
    # Execute distribution
    successful_distributions = 0
    total_notified = 0
    
    # Distribute resources evenly across Scuole Grandi
    resources_per_location = {
        k: v / len(scuole_buildings) for k, v in total_resources.items()
    }
    
    for building in scuole_buildings:
        # Create charity resources
        if create_charity_resources(tables, building, resources_per_location):
            successful_distributions += 1
            
            # Create distribution activity
            create_charity_distribution_activity(tables, building, resources_per_location)
            
            # Notify nearby hungry citizens
            notified = notify_nearby_hungry_citizens(tables, building, hungry_citizens)
            total_notified += notified
    
    if successful_distributions == 0:
        log.error("Failed to create any distributions!")
        return
    
    # Deduct cost from treasury
    if not update_treasury_balance(tables, treasury_record, total_cost):
        log.error("Failed to deduct distribution cost from treasury!")
        return
    
    # Create transaction record
    create_distribution_transaction(tables, total_cost, 
                                   f"{len(hungry_citizens)} hungry citizens")
    
    # Create admin notification
    try:
        admin_notification = {
            'Type': 'emergency_distribution_complete',
            'Citizen': treasury_record['id'],
            'Content': f"🏛️ **Emergency Food Distribution Complete**: {total_cost:.2f} Ducats spent to feed {len(hungry_citizens)} starving citizens at {successful_distributions} locations.",
            'Details': json.dumps({
                'event_type': 'emergency_food_distribution',
                'hungry_citizens': len(hungry_citizens),
                'hunger_rate': hunger_rate,
                'total_cost': total_cost,
                'distribution_points': successful_distributions,
                'citizens_notified': total_notified,
                'resources_distributed': total_resources
            }),
            'CreatedAt': datetime.datetime.now(pytz.UTC).isoformat()
        }
        
        tables['notifications'].create(admin_notification)
        
    except Exception as e:
        log.error(f"Error creating admin notification: {e}")
    
    log.info(f"{LogColors.OKGREEN}Emergency distribution complete!{LogColors.ENDC}")
    log.info(f"  - Distributed at {successful_distributions} locations")
    log.info(f"  - Notified {total_notified} nearby hungry citizens")
    log.info(f"  - Total cost: {total_cost:.2f} Ducats")
    log.info(f"  - New treasury balance: {treasury_balance - total_cost:.2f} Ducats")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Emergency food distribution for La Serenissima")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    distribute_emergency_food(dry_run=args.dry_run)
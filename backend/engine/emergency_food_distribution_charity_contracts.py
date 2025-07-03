#!/usr/bin/env python3
"""
Emergency Food Distribution System (Charity Contracts) for La Serenissima.

This script implements "La Mensa del Doge" (The Doge's Table) using charity contracts.
Instead of the treasury directly buying and distributing food, it:
1. Creates charity_food contracts at existing market stalls
2. These contracts allow hungry citizens to get food for free
3. The treasury compensates the sellers for the food taken
4. Citizens use their normal food-seeking behavior to find and collect food

This maintains the closed-loop economy and physical resource constraints.
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
log = logging.getLogger("emergency_food_distribution_charity")

# Load environment variables
load_dotenv()

# Add project root to sys.path for backend imports
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import LogColors, log_header, _escape_airtable_value

# Constants
HUNGER_CRISIS_THRESHOLD = 0.05  # 5% of population
FOOD_RESOURCE_TYPES = ['bread', 'fish', 'vegetables', 'grain', 'meat', 'cheese']
CHARITY_CONTRACT_DURATION_HOURS = 4  # How long charity contracts last
MAX_CHARITY_UNITS_PER_CONTRACT = 10  # Max units per charity contract to prevent hoarding

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
            'contracts': Table(api_key, base_id, 'CONTRACTS'),
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
        all_citizens = tables['citizens'].all()
        now_utc = datetime.datetime.now(pytz.UTC)
        hunger_threshold = now_utc - datetime.timedelta(hours=24)
        
        hungry_citizens = []
        for citizen in all_citizens:
            fields = citizen['fields']
            ate_at_str = fields.get('AteAt')
            
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

def find_food_at_market_stalls(tables: Dict[str, Table]) -> List[Dict]:
    """Find market stalls with food available via public_sell contracts."""
    log.info("Searching for food at market stalls...")
    
    food_sources = []
    
    try:
        # Find active public_sell contracts for food
        formula = f"AND({{Type}}='public_sell', {{Status}}='active')"
        public_sell_contracts = tables['contracts'].all(formula=formula)
        
        for contract in public_sell_contracts:
            contract_fields = contract['fields']
            resource_type = contract_fields.get('ResourceType', '').lower()
            
            # Check if it's a food resource
            if resource_type in FOOD_RESOURCE_TYPES:
                seller_building = contract_fields.get('SellerBuilding')
                seller = contract_fields.get('Seller')
                price_per_resource = float(contract_fields.get('PricePerResource', contract_fields.get('PricePerUnit', 0)))
                
                # Check actual stock at the building
                stock_formula = "AND({Type}='%s', {Asset}='%s', {AssetType}='building', {Owner}='%s')" % (
                    _escape_airtable_value(resource_type),
                    _escape_airtable_value(seller_building), 
                    _escape_airtable_value(seller)
                )
                
                resources = tables['resources'].all(formula=stock_formula)
                total_stock = sum(float(r['fields'].get('Count', 0)) for r in resources)
                
                if total_stock > 0:
                    food_sources.append({
                        'contract': contract,
                        'resource_type': resource_type,
                        'seller_building': seller_building,
                        'seller': seller,
                        'price_per_resource': price_per_resource,
                        'stock': total_stock
                    })
                    log.info(f"Found {total_stock} units of {resource_type} at {seller_building}")
        
        log.info(f"Found {len(food_sources)} food sources at markets")
        return food_sources
        
    except Exception as e:
        log.error(f"Error finding food sources: {e}")
        return []

def cleanup_expired_charity_contracts(tables: Dict[str, Table]) -> int:
    """Remove expired charity_food contracts."""
    try:
        now_utc = datetime.datetime.now(pytz.UTC)
        # Find expired charity contracts
        formula = f"AND({{Type}}='charity_food', {{Status}}='active')"
        charity_contracts = tables['contracts'].all(formula=formula)
        
        expired_count = 0
        for contract in charity_contracts:
            end_at_str = contract['fields'].get('EndAt')
            if end_at_str:
                try:
                    end_at_dt = datetime.datetime.fromisoformat(end_at_str.replace('Z', '+00:00'))
                    if end_at_dt.tzinfo is None:
                        end_at_dt = pytz.UTC.localize(end_at_dt)
                    
                    if end_at_dt < now_utc:
                        # Mark as expired
                        tables['contracts'].update(contract['id'], {'Status': 'expired'})
                        expired_count += 1
                        log.info(f"Expired charity contract {contract['fields'].get('ContractId')}")
                except Exception as e:
                    log.error(f"Error checking expiry for contract {contract['id']}: {e}")
        
        return expired_count
    except Exception as e:
        log.error(f"Error cleaning up expired contracts: {e}")
        return 0

def create_charity_food_contracts(tables: Dict[str, Table], food_sources: List[Dict], hungry_count: int, dry_run: bool = False) -> List[Dict]:
    """Create charity_food contracts at market stalls."""
    log.info("Creating charity food contracts...")
    
    now_utc = datetime.datetime.now(pytz.UTC)
    end_time = now_utc + datetime.timedelta(hours=CHARITY_CONTRACT_DURATION_HOURS)
    
    # Calculate how much food we need
    food_needed = hungry_count
    
    # Group food sources by resource type for variety
    by_type = defaultdict(list)
    for source in food_sources:
        by_type[source['resource_type']].append(source)
    
    created_contracts = []
    total_charity_units = 0
    
    # Try to distribute evenly across food types
    while food_needed > 0 and any(sources for sources in by_type.values()):
        for resource_type, sources in list(by_type.items()):
            if not sources or food_needed <= 0:
                continue
                
            # Take the first source of this type
            source = sources[0]
            
            # Calculate units for this contract
            units_available = min(source['stock'], MAX_CHARITY_UNITS_PER_CONTRACT)
            units_needed = min(units_available, food_needed)
            
            if units_needed <= 0:
                sources.pop(0)  # Remove exhausted source
                continue
            
            if dry_run:
                log.info(f"[DRY RUN] Would create charity contract for {units_needed} units of {resource_type} at {source['seller_building']}")
                created_contracts.append({
                    'resource_type': resource_type,
                    'units': units_needed,
                    'seller_building': source['seller_building'],
                    'original_price': source['price_per_resource']
                })
            else:
                try:
                    # Create the charity contract
                    contract_id = f"charity_{source['seller_building']}_{resource_type}_{int(now_utc.timestamp())}"
                    
                    contract_data = {
                        'ContractId': contract_id,
                        'Type': 'charity_food',
                        'Seller': source['seller'],
                        'Buyer': 'public',  # Anyone can claim
                        'ResourceType': resource_type,
                        'SellerBuilding': source['seller_building'],
                        'TargetAmount': float(units_needed),
                        'PricePerResource': 0.0,  # Free for citizens
                        'Status': 'active',
                        'Priority': 10,  # High priority for emergency food
                        'CreatedAt': now_utc.isoformat(),
                        'EndAt': end_time.isoformat(),
                        'Title': f"🍞 Free {resource_type.title()} - La Mensa del Doge",
                        'Description': f"Emergency food distribution. Take up to {units_needed} units of {resource_type} for free. Courtesy of the Doge's charity.",
                        'Notes': json.dumps({
                            'purpose': 'emergency_food_distribution',
                            'sponsor': 'ConsiglioDeiDieci',
                            'original_contract': source['contract']['fields'].get('ContractId'),
                            'original_price': source['price_per_resource']  # Store original price in Notes for reimbursement
                        })
                    }
                    
                    created_contract = tables['contracts'].create(contract_data)
                    created_contracts.append({
                        'contract': created_contract,
                        'resource_type': resource_type,
                        'units': units_needed,
                        'seller_building': source['seller_building'],
                        'original_price': source['price_per_resource']
                    })
                    
                    log.info(f"Created charity contract {contract_id} for {units_needed} units of {resource_type}")
                    
                except Exception as e:
                    log.error(f"Error creating charity contract: {e}")
            
            # Update counters
            total_charity_units += units_needed
            food_needed -= units_needed
            source['stock'] -= units_needed
            
            # Remove source if exhausted
            if source['stock'] <= 0:
                sources.pop(0)
    
    log.info(f"Created {len(created_contracts)} charity contracts for {total_charity_units} total units of food")
    return created_contracts

def create_citizen_notifications(tables: Dict[str, Table], charity_contracts: List[Dict], dry_run: bool = False):
    """Create notifications for citizens about available free food."""
    if not charity_contracts:
        return
    
    now_utc = datetime.datetime.now(pytz.UTC)
    
    # Group contracts by location
    by_location = defaultdict(list)
    for contract in charity_contracts:
        by_location[contract['seller_building']].append(contract)
    
    # Create a summary message
    location_summaries = []
    for building_id, contracts in by_location.items():
        food_types = [c['resource_type'] for c in contracts]
        food_summary = ", ".join(set(food_types))
        location_summaries.append(f"• {building_id}: {food_summary}")
    
    message = (
        "🍞 **La Mensa del Doge - Free Food Available!**\n\n"
        "The Doge's charity is distributing free food to hungry citizens. "
        f"Visit these locations within the next {CHARITY_CONTRACT_DURATION_HOURS} hours:\n\n"
        + "\n".join(location_summaries) +
        "\n\nLook for 'charity_food' contracts at market stalls. First come, first served!"
    )
    
    if dry_run:
        log.info(f"[DRY RUN] Would create public notification: {message}")
    else:
        try:
            # Create a public notification
            notification_data = {
                'Type': 'charity_food_announcement',
                'Citizen': 'ConsiglioDeiDieci',
                'Content': message,
                'CreatedAt': now_utc.isoformat()
            }
            
            tables['notifications'].create(notification_data)
            log.info("Created public notification about charity food distribution")
            
        except Exception as e:
            log.error(f"Error creating notification: {e}")

def distribute_emergency_food_charity_contracts(dry_run: bool = False):
    """Main function to distribute emergency food using charity contracts."""
    log_header("Emergency Food Distribution (Charity Contracts) - La Mensa del Doge", LogColors.HEADER)
    
    tables = initialize_airtable()
    
    # Clean up expired charity contracts first
    expired_count = cleanup_expired_charity_contracts(tables)
    if expired_count > 0:
        log.info(f"Cleaned up {expired_count} expired charity contracts")
    
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
    
    # Find available food at markets
    food_sources = find_food_at_market_stalls(tables)
    if not food_sources:
        log.error("No food available at market stalls!")
        # Create problem record
        problem_data = {
            'ProblemId': f'no_market_food_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'Type': 'no_food_at_markets',
            'Severity': 'Critical',
            'Status': 'new',
            'Title': 'No Food Available at Markets for Emergency Distribution',
            'Description': f'{len(hungry_citizens)} citizens are starving but no food is available at market stalls.',
            'CreatedAt': datetime.datetime.now(pytz.UTC).isoformat()
        }
        if not dry_run:
            tables['problems'].create(problem_data)
        return
    
    # Create charity contracts
    charity_contracts = create_charity_food_contracts(tables, food_sources, len(hungry_citizens), dry_run)
    
    if not charity_contracts:
        log.error("Failed to create any charity contracts!")
        return
    
    # Create notifications
    create_citizen_notifications(tables, charity_contracts, dry_run)
    
    # Calculate total impact
    total_units = sum(c['units'] for c in charity_contracts)
    estimated_reimbursement = sum(c['units'] * c['original_price'] for c in charity_contracts)
    
    log.info(f"{LogColors.OKGREEN}Emergency food distribution initiated!{LogColors.ENDC}")
    log.info(f"  - Created {len(charity_contracts)} charity contracts")
    log.info(f"  - Total food available: {total_units} units")
    log.info(f"  - Estimated treasury reimbursement: {estimated_reimbursement:.2f} Ducats")
    log.info(f"  - Contracts expire in {CHARITY_CONTRACT_DURATION_HOURS} hours")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Charity contract-based emergency food distribution for La Serenissima")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--hour", type=int, choices=range(24), metavar="[0-23]", 
                        help="Force current hour in Venice time (0-23) for scheduler compatibility")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    distribute_emergency_food_charity_contracts(dry_run=args.dry_run)
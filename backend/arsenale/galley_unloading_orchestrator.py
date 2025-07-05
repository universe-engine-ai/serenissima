#!/usr/bin/env python3
"""
Galley Unloading Orchestrator for La Serenissima
Contract: SEREN-STAB-001

This script creates pickup activities for citizens to fetch resources from galleys.
It identifies available citizens and assigns them to fetch grain from merchant galleys.

Strategy:
1. Find all galleys with grain
2. Find available citizens (not busy, healthy enough)
3. Create pickup_from_galley activities
4. Prioritize citizens near galleys
5. Balance workload across citizens
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Any, Tuple
import uuid
import random

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

# Import utility functions
from backend.engine.utils.activity_helpers import (
    LogColors, 
    log_header,
    VENICE_TIMEZONE,
    _escape_airtable_value,
    get_building_record,
    calculate_haversine_distance_meters
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("galley_unloading_orchestrator")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Constants
CITIZEN_CARRY_CAPACITY = 20.0  # Standard citizen carrying capacity
MIN_HEALTH_FOR_WORK = 30.0    # Minimum health to assign work
MAX_ACTIVITIES_PER_CITIZEN = 3  # Don't overload citizens

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error(f"{LogColors.FAIL}Missing Airtable credentials{LogColors.ENDC}")
        return None
        
    try:
        api = Api(api_key)
        tables = {
            'buildings': api.table(base_id, 'BUILDINGS'),
            'resources': api.table(base_id, 'RESOURCES'),
            'citizens': api.table(base_id, 'CITIZENS'),
            'activities': api.table(base_id, 'ACTIVITIES'),
            'contracts': api.table(base_id, 'CONTRACTS')
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection successful{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def get_galleys_with_resources(tables: Dict[str, Table]) -> List[Dict]:
    """Find all merchant galleys with resources that need unloading."""
    log.info(f"{LogColors.OKBLUE}🚢 Finding galleys with cargo...{LogColors.ENDC}")
    
    try:
        # Get all constructed merchant galleys
        galley_formula = "AND({Type}='merchant_galley', {IsConstructed}=TRUE())"
        galleys = tables['buildings'].all(formula=galley_formula)
        
        if not galleys:
            log.warning("No constructed merchant galleys found")
            return []
        
        galleys_with_cargo = []
        
        for galley in galleys:
            galley_id = galley['fields'].get('BuildingId')
            galley_name = galley['fields'].get('Name', galley_id)
            galley_owner = galley['fields'].get('Owner')
            
            # Get all resources in this galley
            resource_formula = f"AND({{Asset}}='{_escape_airtable_value(galley_id)}', {{AssetType}}='building')"
            resources = tables['resources'].all(formula=resource_formula)
            
            if resources:
                # Group resources by type
                resource_summary = {}
                total_amount = 0.0
                
                for resource in resources:
                    res_type = resource['fields'].get('Type', 'unknown')
                    res_count = float(resource['fields'].get('Count', 0))
                    if res_type not in resource_summary:
                        resource_summary[res_type] = 0.0
                    resource_summary[res_type] += res_count
                    total_amount += res_count
                
                if total_amount > 0:
                    galleys_with_cargo.append({
                        'galley': galley,
                        'resources': resources,
                        'resource_summary': resource_summary,
                        'total_amount': total_amount,
                        'owner': galley_owner
                    })
                    
                    log.info(f"  📦 {galley_name}: {total_amount:.1f} total resources")
                    for res_type, amount in resource_summary.items():
                        log.info(f"     - {res_type}: {amount:.1f}")
        
        log.info(f"{LogColors.OKGREEN}Found {len(galleys_with_cargo)} galleys with cargo{LogColors.ENDC}")
        return galleys_with_cargo
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error finding galleys: {e}{LogColors.ENDC}")
        return []

def get_available_citizens(tables: Dict[str, Table]) -> List[Dict]:
    """Find citizens who can help with unloading."""
    log.info(f"{LogColors.OKBLUE}👥 Finding available citizens...{LogColors.ENDC}")
    
    try:
        # Get citizens who are:
        # - In Venice
        # - Healthy enough (Health > MIN_HEALTH_FOR_WORK)
        # - Not currently busy with high-priority activities
        
        citizen_formula = f"AND({{InVenice}}=TRUE(), {{Health}}>{MIN_HEALTH_FOR_WORK})"
        citizens = tables['citizens'].all(formula=citizen_formula)
        
        if not citizens:
            log.warning("No available citizens found")
            return []
        
        available_citizens = []
        
        for citizen in citizens:
            username = citizen['fields'].get('Username')
            
            # Check current activities
            activity_formula = (
                f"AND({{Citizen}}='{_escape_airtable_value(username)}', "
                f"OR({{Status}}='created', {{Status}}='in_progress'))"
            )
            current_activities = tables['activities'].all(formula=activity_formula)
            
            # Skip if too many activities
            if len(current_activities) >= MAX_ACTIVITIES_PER_CITIZEN:
                continue
            
            # Check if any high-priority activities
            has_high_priority = any(
                int(act['fields'].get('Priority', 5)) >= 8 
                for act in current_activities
            )
            
            if not has_high_priority:
                available_citizens.append({
                    'citizen': citizen,
                    'current_activities': len(current_activities),
                    'health': float(citizen['fields'].get('Health', 0)),
                    'position': citizen['fields'].get('Position')
                })
        
        log.info(f"{LogColors.OKGREEN}Found {len(available_citizens)} available citizens{LogColors.ENDC}")
        return available_citizens
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error finding citizens: {e}{LogColors.ENDC}")
        return []

def find_or_create_import_contract(
    tables: Dict[str, Table],
    galley_owner: str,
    resource_type: str,
    amount: float,
    buyer_username: str
) -> Optional[str]:
    """Find existing import contract or create a new one."""
    try:
        # Check for existing active import contract
        contract_formula = (
            f"AND({{Type}}='import', {{Seller}}='{_escape_airtable_value(galley_owner)}', "
            f"{{Buyer}}='{_escape_airtable_value(buyer_username)}', "
            f"{{ResourceType}}='{_escape_airtable_value(resource_type)}', "
            f"{{Status}}='active')"
        )
        existing_contracts = tables['contracts'].all(formula=contract_formula, max_records=1)
        
        if existing_contracts:
            return existing_contracts[0]['fields'].get('ContractId')
        
        # Create new import contract
        now_venice = datetime.now(VENICE_TIMEZONE)
        contract_id = f"contract-emergency-import-{uuid.uuid4()}"
        
        contract_data = {
            'ContractId': contract_id,
            'Type': 'import',
            'Seller': galley_owner,
            'Buyer': buyer_username,
            'ResourceType': resource_type,
            'TargetAmount': amount,
            'PricePerResource': 1.0,  # Nominal price for emergency
            'Status': 'active',
            'Priority': 9,  # High priority
            'CreatedAt': now_venice.isoformat(),
            'EndAt': (now_venice + timedelta(days=1)).isoformat(),
            'Notes': json.dumps({
                'reasoning': 'Emergency import contract for starvation crisis',
                'created_by': 'galley_unloading_orchestrator'
            })
        }
        
        tables['contracts'].create(contract_data)
        log.info(f"  📋 Created emergency import contract: {contract_id}")
        return contract_id
        
    except Exception as e:
        log.error(f"Error creating import contract: {e}")
        return None

def create_pickup_activity(
    tables: Dict[str, Table],
    citizen_username: str,
    galley_id: str,
    resource_type: str,
    amount: float,
    contract_id: str,
    priority: int = 8
) -> bool:
    """Create a pickup_from_galley activity for a citizen."""
    try:
        now_venice = datetime.now(VENICE_TIMEZONE)
        activity_id = f"activity-pickup-{uuid.uuid4()}"
        
        # Prepare resources JSON
        resources_data = [{
            'ResourceId': resource_type,
            'Amount': min(amount, CITIZEN_CARRY_CAPACITY)  # Limit to carrying capacity
        }]
        
        activity_data = {
            'ActivityId': activity_id,
            'Type': 'pickup_from_galley',
            'Citizen': citizen_username,
            'FromBuilding': galley_id,
            'ContractId': contract_id,
            'Resources': json.dumps(resources_data),
            'StartDate': now_venice.isoformat(),
            'EndDate': (now_venice + timedelta(minutes=30)).isoformat(),
            'Status': 'created',
            'Priority': priority,
            'Notes': 'Emergency galley unloading for starvation crisis'
        }
        
        tables['activities'].create(activity_data)
        log.info(f"  ✅ Created pickup activity for {citizen_username} to fetch {resources_data[0]['Amount']:.1f} {resource_type}")
        return True
        
    except Exception as e:
        log.error(f"Error creating pickup activity: {e}")
        return False

def assign_unloading_tasks(
    tables: Dict[str, Table],
    galleys_with_cargo: List[Dict],
    available_citizens: List[Dict],
    dry_run: bool = False,
    prioritize_grain: bool = True
) -> Dict[str, Any]:
    """Assign citizens to unload galleys."""
    log.info(f"\n{LogColors.OKBLUE}📋 Assigning unloading tasks...{LogColors.ENDC}")
    
    stats = {
        'activities_created': 0,
        'citizens_assigned': set(),
        'galleys_served': set(),
        'total_amount_assigned': 0.0,
        'grain_assigned': 0.0
    }
    
    # Sort citizens by health (healthiest first)
    available_citizens.sort(key=lambda x: x['health'], reverse=True)
    
    # Track citizen workload
    citizen_workload = {c['citizen']['fields']['Username']: 0 for c in available_citizens}
    
    # Process galleys
    for galley_data in galleys_with_cargo:
        galley = galley_data['galley']
        galley_id = galley['fields']['BuildingId']
        galley_name = galley['fields'].get('Name', galley_id)
        galley_owner = galley_data['owner']
        
        if not galley_owner:
            log.warning(f"Galley {galley_name} has no owner, skipping")
            continue
        
        galley_pos_str = galley['fields'].get('Position')
        if not galley_pos_str:
            continue
            
        try:
            galley_pos = json.loads(galley_pos_str)
        except:
            continue
        
        # Prioritize grain if requested
        resources_to_unload = []
        if prioritize_grain and 'grain' in galley_data['resource_summary']:
            resources_to_unload.append(('grain', galley_data['resource_summary']['grain']))
        
        # Add other resources
        for res_type, amount in galley_data['resource_summary'].items():
            if res_type != 'grain' or not prioritize_grain:
                resources_to_unload.append((res_type, amount))
        
        # Assign citizens to this galley
        for res_type, total_amount in resources_to_unload:
            remaining_amount = total_amount
            
            # Find nearest available citizens
            citizens_by_distance = []
            for citizen_data in available_citizens:
                citizen = citizen_data['citizen']
                username = citizen['fields']['Username']
                
                # Skip if overloaded
                if citizen_workload[username] >= MAX_ACTIVITIES_PER_CITIZEN:
                    continue
                
                # Calculate distance
                citizen_pos_str = citizen_data['position']
                if citizen_pos_str:
                    try:
                        citizen_pos = json.loads(citizen_pos_str)
                        distance = calculate_haversine_distance_meters(
                            galley_pos['lat'], galley_pos['lng'],
                            citizen_pos['lat'], citizen_pos['lng']
                        )
                        citizens_by_distance.append((citizen_data, distance))
                    except:
                        pass
            
            # Sort by distance
            citizens_by_distance.sort(key=lambda x: x[1])
            
            # Assign nearest citizens
            for citizen_data, distance in citizens_by_distance:
                if remaining_amount <= 0:
                    break
                
                citizen = citizen_data['citizen']
                username = citizen['fields']['Username']
                
                # Calculate amount this citizen can carry
                amount_to_fetch = min(remaining_amount, CITIZEN_CARRY_CAPACITY)
                
                # Find or create import contract
                contract_id = find_or_create_import_contract(
                    tables, galley_owner, res_type, amount_to_fetch, username
                )
                
                if not contract_id:
                    continue
                
                if not dry_run:
                    # Create pickup activity
                    success = create_pickup_activity(
                        tables, username, galley_id, res_type, 
                        amount_to_fetch, contract_id, priority=9
                    )
                    
                    if success:
                        stats['activities_created'] += 1
                        stats['citizens_assigned'].add(username)
                        stats['galleys_served'].add(galley_id)
                        stats['total_amount_assigned'] += amount_to_fetch
                        if res_type == 'grain':
                            stats['grain_assigned'] += amount_to_fetch
                        
                        citizen_workload[username] += 1
                        remaining_amount -= amount_to_fetch
                else:
                    log.info(f"  [DRY RUN] Would assign {username} to fetch {amount_to_fetch:.1f} {res_type} from {galley_name}")
                    stats['activities_created'] += 1
                    remaining_amount -= amount_to_fetch
    
    return stats

def main():
    """Main orchestration process."""
    parser = argparse.ArgumentParser(description="Galley Unloading Orchestrator - Assign citizens to unload galleys")
    parser.add_argument('--dry-run', action='store_true', help='Simulate without creating activities')
    parser.add_argument('--grain-only', action='store_true', help='Only unload grain (for emergency)')
    parser.add_argument('--limit-citizens', type=int, help='Limit number of citizens to assign')
    args = parser.parse_args()
    
    log_header("🏗️ GALLEY UNLOADING ORCHESTRATOR 🏗️", LogColors.HEADER)
    log.info(f"Contract: SEREN-STAB-001 - Organizing galley unloading")
    log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE EXECUTION'}")
    
    tables = initialize_airtable()
    if not tables:
        return
    
    # Find galleys and citizens
    galleys_with_cargo = get_galleys_with_resources(tables)
    available_citizens = get_available_citizens(tables)
    
    if not galleys_with_cargo:
        log.warning(f"{LogColors.WARNING}No galleys with cargo found{LogColors.ENDC}")
        return
    
    if not available_citizens:
        log.warning(f"{LogColors.WARNING}No available citizens found{LogColors.ENDC}")
        return
    
    # Limit citizens if requested
    if args.limit_citizens:
        available_citizens = available_citizens[:args.limit_citizens]
        log.info(f"Limiting to {len(available_citizens)} citizens")
    
    # Assign tasks
    stats = assign_unloading_tasks(
        tables, galleys_with_cargo, available_citizens, 
        args.dry_run, prioritize_grain=args.grain_only
    )
    
    # Summary
    log.info(f"\n{LogColors.HEADER}📊 ASSIGNMENT SUMMARY{LogColors.ENDC}")
    log.info(f"  Activities created: {stats['activities_created']}")
    log.info(f"  Citizens assigned: {len(stats['citizens_assigned'])}")
    log.info(f"  Galleys served: {len(stats['galleys_served'])}")
    log.info(f"  Total resources assigned: {stats['total_amount_assigned']:.1f}")
    if stats['grain_assigned'] > 0:
        log.info(f"  Grain assigned: {stats['grain_assigned']:.1f}")
    
    if not args.dry_run and stats['activities_created'] > 0:
        log.info(f"\n{LogColors.OKGREEN}✅ Citizens are now heading to unload galleys!{LogColors.ENDC}")
    elif args.dry_run:
        log.info(f"\n{LogColors.OKCYAN}This was a dry run. Run without --dry-run to create activities{LogColors.ENDC}")

if __name__ == "__main__":
    main()
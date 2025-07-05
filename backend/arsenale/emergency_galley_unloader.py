#!/usr/bin/env python3
"""
Emergency Galley Unloader for La Serenissima
Contract: SEREN-STAB-001

This emergency script addresses the critical starvation crisis by forcing galleys
to unload their cargo directly to appropriate storage facilities or mills.

Current Crisis:
- 112 citizens starving (87% of population)
- 62 galleys stuck at docks with grain
- No automatic unloading mechanism
- Citizens too weak/busy to fetch from galleys

Solution:
1. Identify all merchant_galley buildings with grain resources
2. Find appropriate storage/processing facilities (automated_mill, warehouses)
3. Transfer grain directly from galleys to these facilities
4. Create activity records for audit trail
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
import pytz
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import uuid

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
log = logging.getLogger("emergency_galley_unloader")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

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
            'notifications': api.table(base_id, 'NOTIFICATIONS')
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection successful{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return None

def get_stuck_galleys_with_grain(tables: Dict[str, Table]) -> List[Dict]:
    """Find all merchant galleys that have grain resources."""
    log.info(f"{LogColors.OKBLUE}🚢 Searching for galleys with grain...{LogColors.ENDC}")
    
    try:
        # Get all merchant galleys that are constructed (have arrived)
        galley_formula = "AND({Type}='merchant_galley', {IsConstructed}=TRUE())"
        galleys = tables['buildings'].all(formula=galley_formula)
        
        if not galleys:
            log.warning("No constructed merchant galleys found")
            return []
            
        log.info(f"Found {len(galleys)} merchant galleys")
        
        # Check each galley for grain resources
        galleys_with_grain = []
        for galley in galleys:
            galley_id = galley['fields'].get('BuildingId')
            galley_name = galley['fields'].get('Name', galley_id)
            
            # Find grain in this galley
            grain_formula = f"AND({{Asset}}='{_escape_airtable_value(galley_id)}', {{AssetType}}='building', {{Type}}='grain')"
            grain_resources = tables['resources'].all(formula=grain_formula)
            
            if grain_resources:
                total_grain = sum(float(r['fields'].get('Count', 0)) for r in grain_resources)
                if total_grain > 0:
                    galleys_with_grain.append({
                        'galley': galley,
                        'grain_resources': grain_resources,
                        'total_grain': total_grain,
                        'name': galley_name
                    })
                    log.info(f"  🌾 {galley_name}: {total_grain:.1f} grain")
        
        log.info(f"{LogColors.OKGREEN}Found {len(galleys_with_grain)} galleys with grain{LogColors.ENDC}")
        return galleys_with_grain
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error finding galleys with grain: {e}{LogColors.ENDC}")
        return []

def find_best_grain_destination(tables: Dict[str, Table], galley_position: Dict) -> Optional[Dict]:
    """Find the best destination for grain (automated_mill or warehouse)."""
    try:
        # Priority 1: Find automated mills
        mill_formula = "AND({Type}='automated_mill', {IsConstructed}=TRUE())"
        mills = tables['buildings'].all(formula=mill_formula)
        
        # Priority 2: Find warehouses
        warehouse_formula = "AND({Type}='warehouse', {IsConstructed}=TRUE())"
        warehouses = tables['buildings'].all(formula=warehouse_formula)
        
        all_destinations = []
        
        # Process mills (higher priority)
        for mill in mills:
            mill_pos_str = mill['fields'].get('Position')
            if mill_pos_str:
                try:
                    mill_pos = json.loads(mill_pos_str)
                    distance = calculate_haversine_distance_meters(
                        galley_position['lat'], galley_position['lng'],
                        mill_pos['lat'], mill_pos['lng']
                    )
                    all_destinations.append({
                        'building': mill,
                        'type': 'automated_mill',
                        'distance': distance,
                        'priority': 1  # Mills have priority
                    })
                except:
                    pass
        
        # Process warehouses
        for warehouse in warehouses:
            warehouse_pos_str = warehouse['fields'].get('Position')
            if warehouse_pos_str:
                try:
                    warehouse_pos = json.loads(warehouse_pos_str)
                    distance = calculate_haversine_distance_meters(
                        galley_position['lat'], galley_position['lng'],
                        warehouse_pos['lat'], warehouse_pos['lng']
                    )
                    all_destinations.append({
                        'building': warehouse,
                        'type': 'warehouse',
                        'distance': distance,
                        'priority': 2  # Warehouses are secondary
                    })
                except:
                    pass
        
        if not all_destinations:
            log.warning("No suitable destinations found for grain")
            return None
        
        # Sort by priority first, then by distance
        all_destinations.sort(key=lambda x: (x['priority'], x['distance']))
        return all_destinations[0]
        
    except Exception as e:
        log.error(f"Error finding grain destination: {e}")
        return None

def transfer_grain_from_galley(
    tables: Dict[str, Table],
    galley_data: Dict,
    destination: Dict,
    dry_run: bool = False
) -> Tuple[bool, float]:
    """Transfer grain from galley to destination building."""
    galley = galley_data['galley']
    grain_resources = galley_data['grain_resources']
    total_grain = galley_data['total_grain']
    galley_name = galley_data['name']
    
    dest_building = destination['building']
    dest_name = dest_building['fields'].get('Name', dest_building['fields'].get('BuildingId'))
    dest_type = destination['type']
    
    log.info(f"\n{LogColors.OKBLUE}📦 Transferring {total_grain:.1f} grain from {galley_name} to {dest_name} ({dest_type}){LogColors.ENDC}")
    
    if dry_run:
        log.info(f"{LogColors.OKCYAN}[DRY RUN] Would transfer {total_grain:.1f} grain{LogColors.ENDC}")
        return True, total_grain
    
    try:
        now_venice = datetime.now(VENICE_TIMEZONE)
        now_iso = now_venice.isoformat()
        
        # Group resources by owner for efficient transfer
        resources_by_owner = defaultdict(list)
        for resource in grain_resources:
            owner = resource['fields'].get('Owner', 'unknown')
            resources_by_owner[owner].append(resource)
        
        total_transferred = 0.0
        
        for owner, owner_resources in resources_by_owner.items():
            owner_total = sum(float(r['fields'].get('Count', 0)) for r in owner_resources)
            
            # Check if destination already has grain owned by this owner
            dest_grain_formula = (
                f"AND({{Asset}}='{_escape_airtable_value(dest_building['fields']['BuildingId'])}', "
                f"{{AssetType}}='building', {{Type}}='grain', {{Owner}}='{_escape_airtable_value(owner)}')"
            )
            existing_dest_grain = tables['resources'].all(formula=dest_grain_formula, max_records=1)
            
            if existing_dest_grain:
                # Update existing grain record
                existing_record = existing_dest_grain[0]
                new_count = float(existing_record['fields'].get('Count', 0)) + owner_total
                tables['resources'].update(existing_record['id'], {
                    'Count': new_count,
                    'UpdatedAt': now_iso
                })
                log.info(f"  ✅ Updated grain for {owner}: +{owner_total:.1f} (new total: {new_count:.1f})")
            else:
                # Create new grain record at destination
                new_resource = {
                    'ResourceId': f"resource-{uuid.uuid4()}",
                    'Type': 'grain',
                    'Name': 'Grain',
                    'Asset': dest_building['fields']['BuildingId'],
                    'AssetType': 'building',
                    'Owner': owner,
                    'Count': owner_total,
                    'CreatedAt': now_iso,
                    'Notes': f"Emergency transfer from {galley_name}"
                }
                tables['resources'].create(new_resource)
                log.info(f"  ✅ Created grain record for {owner}: {owner_total:.1f}")
            
            # Delete resources from galley
            for resource in owner_resources:
                tables['resources'].delete(resource['id'])
            
            total_transferred += owner_total
        
        # Create notification for galley owner
        galley_owner = galley['fields'].get('Owner')
        if galley_owner:
            notification_text = (
                f"🚨 EMERGENCY UNLOADING: {total_grain:.1f} grain from your galley '{galley_name}' "
                f"has been emergency transferred to {dest_name} to address the starvation crisis. "
                f"The city thanks you for your understanding."
            )
            notification = {
                'NotificationId': f"notification-{uuid.uuid4()}",
                'Type': 'emergency_unloading',
                'Recipient': galley_owner,
                'Message': notification_text,
                'CreatedAt': now_iso,
                'Status': 'unread',
                'Priority': 10
            }
            tables['notifications'].create(notification)
        
        # Create activity record for audit
        activity = {
            'ActivityId': f"activity-emergency-unload-{uuid.uuid4()}",
            'Type': 'emergency_galley_unload',
            'Citizen': 'system',  # System-initiated
            'FromBuilding': galley['fields']['BuildingId'],
            'ToBuilding': dest_building['fields']['BuildingId'],
            'Resources': json.dumps([{'ResourceId': 'grain', 'Amount': total_grain}]),
            'StartDate': now_iso,
            'EndDate': now_iso,
            'Status': 'processed',
            'Notes': f"Emergency transfer of {total_grain:.1f} grain to address starvation crisis",
            'Priority': 10
        }
        tables['activities'].create(activity)
        
        log.info(f"{LogColors.OKGREEN}✅ Successfully transferred {total_transferred:.1f} grain!{LogColors.ENDC}")
        return True, total_transferred
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error transferring grain: {e}{LogColors.ENDC}")
        return False, 0.0

def main():
    """Main emergency unloading process."""
    parser = argparse.ArgumentParser(description="Emergency Galley Unloader - Transfer grain from stuck galleys")
    parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    parser.add_argument('--limit', type=int, help='Limit number of galleys to process')
    args = parser.parse_args()
    
    log_header("🚨 EMERGENCY GALLEY UNLOADER 🚨", LogColors.FAIL)
    log.info(f"Contract: SEREN-STAB-001 - Addressing Venice Starvation Crisis")
    log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE EXECUTION'}")
    
    tables = initialize_airtable()
    if not tables:
        return
    
    # Find galleys with grain
    galleys_with_grain = get_stuck_galleys_with_grain(tables)
    
    if not galleys_with_grain:
        log.warning(f"{LogColors.WARNING}No galleys with grain found. The crisis deepens...{LogColors.ENDC}")
        return
    
    # Summary of grain available
    total_grain_available = sum(g['total_grain'] for g in galleys_with_grain)
    log.info(f"\n{LogColors.OKGREEN}📊 GRAIN INVENTORY:{LogColors.ENDC}")
    log.info(f"  Total galleys with grain: {len(galleys_with_grain)}")
    log.info(f"  Total grain available: {total_grain_available:.1f}")
    log.info(f"  Average per galley: {total_grain_available/len(galleys_with_grain):.1f}")
    
    # Process each galley
    processed = 0
    total_transferred = 0.0
    failed = 0
    
    for i, galley_data in enumerate(galleys_with_grain):
        if args.limit and processed >= args.limit:
            log.info(f"\n{LogColors.WARNING}Reached limit of {args.limit} galleys{LogColors.ENDC}")
            break
            
        galley = galley_data['galley']
        galley_pos_str = galley['fields'].get('Position')
        
        if not galley_pos_str:
            log.warning(f"Galley {galley_data['name']} has no position, skipping")
            failed += 1
            continue
            
        try:
            galley_pos = json.loads(galley_pos_str)
        except:
            log.warning(f"Galley {galley_data['name']} has invalid position, skipping")
            failed += 1
            continue
        
        # Find best destination
        destination = find_best_grain_destination(tables, galley_pos)
        if not destination:
            log.warning(f"No destination found for galley {galley_data['name']}")
            failed += 1
            continue
        
        # Transfer grain
        success, amount = transfer_grain_from_galley(
            tables, galley_data, destination, args.dry_run
        )
        
        if success:
            processed += 1
            total_transferred += amount
        else:
            failed += 1
        
        # Progress report every 10 galleys
        if (i + 1) % 10 == 0:
            log.info(f"\n📈 Progress: {i + 1}/{len(galleys_with_grain)} galleys checked")
    
    # Final summary
    log.info(f"\n{LogColors.HEADER}🏁 EMERGENCY UNLOADING COMPLETE{LogColors.ENDC}")
    log.info(f"  Galleys processed: {processed}")
    log.info(f"  Galleys failed: {failed}")
    log.info(f"  Total grain transferred: {total_transferred:.1f}")
    log.info(f"  Grain per citizen: {total_transferred/126:.1f}" if processed > 0 else "  No grain transferred")
    
    if not args.dry_run and total_transferred > 0:
        log.info(f"\n{LogColors.OKGREEN}🎉 The mills can now process grain! Citizens will eat!{LogColors.ENDC}")
    elif args.dry_run:
        log.info(f"\n{LogColors.OKCYAN}This was a dry run. Run without --dry-run to save Venice!{LogColors.ENDC}")

if __name__ == "__main__":
    main()
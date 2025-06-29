#!/usr/bin/env python3
"""
Delivery Retry Handler for La Serenissima.

This script implements a robust retry mechanism for failed resource deliveries,
part of the "Fraglia dei Bastazi" (Porters' Brotherhood) solution.

This system:
1. Monitors failed fetch_resource activities
2. Implements exponential backoff retry logic
3. Assigns alternative porters when needed
4. Falls back to automated delivery for small packages
5. Creates relay deliveries for long distances

Run this script every 15 minutes to handle delivery failures.
"""

import os
import sys
import logging
import json
import datetime
import pytz
import uuid
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from pyairtable import Api
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("delivery_retry_handler")

# Load environment variables
load_dotenv()

# Add project root to sys.path for backend imports
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import (
    LogColors, 
    log_header,
    VENICE_TIMEZONE,
    _escape_airtable_value,
    get_citizen_record,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters,
    get_path_between_points
)

# Constants
MAX_RETRIES = 3
RETRY_DELAYS = [300, 900, 1800]  # 5 min, 15 min, 30 min
SMALL_DELIVERY_THRESHOLD = 5.0  # Units
RELAY_DISTANCE_THRESHOLD = 500  # Meters
AUTOMATED_DELIVERY_FEE = 2.0  # Ducats

# Relay stations for long-distance deliveries
RELAY_STATIONS = [
    {"id": "relay_rialto", "position": {"lat": 45.438056, "lng": 12.335833}, "name": "Rialto Relay Station"},
    {"id": "relay_san_marco", "position": {"lat": 45.434167, "lng": 12.338611}, "name": "San Marco Relay Station"},
    {"id": "relay_cannaregio", "position": {"lat": 45.445000, "lng": 12.323333}, "name": "Cannaregio Relay Station"},
    {"id": "relay_castello", "position": {"lat": 45.435000, "lng": 12.352500}, "name": "Castello Relay Station"}
]

def initialize_airtable() -> Dict[str, Any]:
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials.")
        sys.exit(1)
    
    try:
        api = Api(api_key)
        return {
            'activities': api.table(base_id, 'ACTIVITIES'),
            'citizens': api.table(base_id, 'CITIZENS'),
            'buildings': api.table(base_id, 'BUILDINGS'),
            'resources': api.table(base_id, 'RESOURCES'),
            'contracts': api.table(base_id, 'CONTRACTS'),
            'notifications': api.table(base_id, 'NOTIFICATIONS')
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)

def get_failed_deliveries(tables: Dict[str, Any], lookback_hours: int = 24) -> List[Dict]:
    """Get recent failed fetch_resource activities."""
    log.info("Fetching failed delivery activities...")
    
    try:
        # Calculate cutoff time
        now_utc = datetime.datetime.now(pytz.UTC)
        cutoff_time = now_utc - datetime.timedelta(hours=lookback_hours)
        cutoff_iso = cutoff_time.isoformat()
        
        # Get failed fetch_resource activities
        formula = f"AND({{Type}}='fetch_resource', {{Status}}='failed', {{UpdatedAt}}>'{cutoff_iso}')"
        failed_activities = tables['activities'].all(formula=formula)
        
        log.info(f"Found {len(failed_activities)} failed deliveries in the last {lookback_hours} hours")
        return failed_activities
        
    except Exception as e:
        log.error(f"Error fetching failed deliveries: {e}")
        return []

def get_retry_count(activity: Dict) -> int:
    """Extract retry count from activity notes."""
    notes = activity['fields'].get('Notes', '')
    if 'Retry attempt:' in notes:
        try:
            # Extract retry count from notes
            parts = notes.split('Retry attempt:')[-1].split()[0]
            return int(parts)
        except:
            return 0
    return 0

def find_available_porter(tables: Dict[str, Any], location: Optional[Dict], exclude_citizens: List[str]) -> Optional[Dict]:
    """Find an available porter near the location."""
    try:
        # Get all citizens
        all_citizens = tables['citizens'].all()
        
        available_porters = []
        
        for citizen in all_citizens:
            fields = citizen['fields']
            username = fields.get('Username')
            
            # Skip excluded citizens
            if username in exclude_citizens:
                continue
            
            # Skip if no position
            position_str = fields.get('Position')
            if not position_str:
                continue
            
            try:
                position = json.loads(position_str)
            except:
                continue
            
            # Calculate distance if location is provided
            if location:
                distance = _calculate_distance_meters(position, location)
                
                # Skip if too far
                if distance > 200:  # 200 meters
                    continue
            else:
                # If no location provided, use a default distance
                distance = 100  # Default distance for sorting
            
            # Check if citizen is idle (no active activities)
            active_formula = f"AND({{Citizen}}='{_escape_airtable_value(username)}', {{Status}}!='processed', {{Status}}!='failed')"
            active_activities = tables['activities'].all(formula=active_formula, max_records=1)
            
            if active_activities:
                continue  # Citizen is busy
            
            available_porters.append({
                'citizen': citizen,
                'distance': distance
            })
        
        # Sort by distance and return closest
        if available_porters:
            available_porters.sort(key=lambda x: x['distance'])
            return available_porters[0]['citizen']
        
        return None
        
    except Exception as e:
        log.error(f"Error finding available porter: {e}")
        return None

def create_retry_activity(tables: Dict[str, Any], original_activity: Dict, new_porter: Dict, retry_count: int) -> Optional[Dict]:
    """Create a retry fetch_resource activity."""
    try:
        original_fields = original_activity['fields']
        
        # Get the transport API URL from environment
        transport_api_url = os.environ.get('TRANSPORT_API_URL', 'http://localhost:3001')
        
        # Get porter position
        porter_pos_str = new_porter['fields'].get('Position')
        if not porter_pos_str:
            log.error(f"Porter {new_porter['fields'].get('Username')} has no position")
            return None
            
        porter_pos = json.loads(porter_pos_str)
        
        # Get from building position
        from_building_id = original_fields.get('FromBuilding')
        from_building = get_building_record(tables, from_building_id)
        if not from_building:
            log.error(f"From building {from_building_id} not found")
            return None
            
        from_pos = _get_building_position_coords(from_building)
        if not from_pos:
            log.error(f"From building {from_building_id} has no position")
            return None
        
        # Calculate new path
        path_data = get_path_between_points(porter_pos, from_pos, transport_api_url)
        if not path_data or not path_data.get('success'):
            log.error(f"Failed to calculate path for retry delivery")
            return None
        
        # Create retry activity
        now_utc = datetime.datetime.now(pytz.UTC)
        delay_seconds = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
        start_time = now_utc + datetime.timedelta(seconds=delay_seconds)
        
        activity_data = {
            'ActivityId': f"fetch-resource-{new_porter['fields'].get('Username')}-{uuid.uuid4().hex[:8]}",
            'Type': 'fetch_resource',
            'Status': 'pending',
            'Citizen': new_porter['fields'].get('Username'),
            'FromBuilding': original_fields.get('FromBuilding'),
            'ToBuilding': original_fields.get('ToBuilding'),
            'Resources': original_fields.get('Resources'),
            'ContractId': original_fields.get('ContractId'),
            'Path': json.dumps(path_data.get('path', [])),
            'CreatedAt': now_utc.isoformat(),
            'StartDate': start_time.isoformat(),
            'Priority': 15,  # Higher priority for retries
            'Notes': f"Retry attempt: {retry_count + 1}. Original porter: {original_fields.get('Citizen')}. Delay: {delay_seconds}s",
            'Title': f"Retry delivery (attempt {retry_count + 1})",
            'Description': f"Retrying failed delivery with new porter after {delay_seconds/60} minute delay"
        }
        
        created = tables['activities'].create(activity_data)
        log.info(f"Created retry activity {created['fields']['ActivityId']} with porter {new_porter['fields'].get('Username')}")
        return created
        
    except Exception as e:
        log.error(f"Error creating retry activity: {e}")
        return None

def create_automated_delivery(tables: Dict[str, Any], activity: Dict) -> bool:
    """Create an automated delivery for small packages."""
    try:
        fields = activity['fields']
        
        # Parse resources
        resources_json = fields.get('Resources', '[]')
        resources = json.loads(resources_json)
        
        # Check if all resources are small enough
        total_amount = sum(r.get('Amount', 0) for r in resources)
        if total_amount > SMALL_DELIVERY_THRESHOLD:
            return False
        
        # Get from and to buildings
        from_building_id = fields.get('FromBuilding')
        to_building_id = fields.get('ToBuilding')
        
        from_building = get_building_record(tables, from_building_id)
        to_building = get_building_record(tables, to_building_id)
        
        if not from_building or not to_building:
            log.error("Cannot find buildings for automated delivery")
            return False
        
        # Transfer resources directly
        now_utc = datetime.datetime.now(pytz.UTC)
        
        for resource in resources:
            resource_type = resource.get('ResourceId')
            amount = resource.get('Amount')
            
            if not resource_type or amount <= 0:
                continue
            
            # Find resource in from building
            formula = f"AND({{Type}}='{resource_type}', {{Asset}}='{from_building_id}', {{AssetType}}='building')"
            source_resources = tables['resources'].all(formula=formula, max_records=1)
            
            if not source_resources:
                log.warning(f"Resource {resource_type} not found in {from_building_id}")
                continue
            
            source_resource = source_resources[0]
            current_amount = float(source_resource['fields'].get('Count', 0))
            
            if current_amount < amount:
                log.warning(f"Insufficient {resource_type} in {from_building_id}: {current_amount} < {amount}")
                amount = current_amount  # Transfer what's available
            
            # Deduct from source
            new_source_amount = current_amount - amount
            if new_source_amount > 0:
                tables['resources'].update(source_resource['id'], {'Count': new_source_amount})
            else:
                tables['resources'].delete(source_resource['id'])
            
            # Add to destination
            dest_formula = f"AND({{Type}}='{resource_type}', {{Asset}}='{to_building_id}', {{AssetType}}='building')"
            dest_resources = tables['resources'].all(formula=dest_formula, max_records=1)
            
            if dest_resources:
                # Update existing
                dest_resource = dest_resources[0]
                dest_amount = float(dest_resource['fields'].get('Count', 0))
                tables['resources'].update(dest_resource['id'], {'Count': dest_amount + amount})
            else:
                # Create new
                resource_data = {
                    'ResourceId': f"resource-{uuid.uuid4()}",
                    'Type': resource_type,
                    'Asset': to_building_id,
                    'AssetType': 'building',
                    'Owner': to_building['fields'].get('Owner', to_building['fields'].get('Occupant')),
                    'Count': amount,
                    'CreatedAt': now_utc.isoformat(),
                    'Notes': 'Automated small package delivery'
                }
                tables['resources'].create(resource_data)
            
            log.info(f"Automated transfer: {amount} {resource_type} from {from_building_id} to {to_building_id}")
        
        # Charge delivery fee (deduct from building owner)
        to_building_owner = to_building['fields'].get('Owner', to_building['fields'].get('Occupant'))
        if to_building_owner:
            owner_record = get_citizen_record(tables, to_building_owner)
            if owner_record:
                current_ducats = float(owner_record['fields'].get('Ducats', 0))
                new_ducats = max(0, current_ducats - AUTOMATED_DELIVERY_FEE)
                tables['citizens'].update(owner_record['id'], {'Ducats': new_ducats})
                log.info(f"Charged {AUTOMATED_DELIVERY_FEE} ducats delivery fee to {to_building_owner}")
        
        # Update original activity as processed
        tables['activities'].update(activity['id'], {
            'Status': 'processed',
            'UpdatedAt': now_utc.isoformat(),
            'Notes': fields.get('Notes', '') + f"\nAutomated delivery completed at {now_utc.isoformat()}. Fee: {AUTOMATED_DELIVERY_FEE} ducats."
        })
        
        return True
        
    except Exception as e:
        log.error(f"Error in automated delivery: {e}")
        return False

def find_relay_station(start_pos: Dict, end_pos: Dict) -> Optional[Dict]:
    """Find the best relay station for a long-distance delivery."""
    best_station = None
    best_score = float('inf')
    
    for station in RELAY_STATIONS:
        # Calculate total distance through relay
        dist_to_relay = _calculate_distance_meters(start_pos, station['position'])
        dist_from_relay = _calculate_distance_meters(station['position'], end_pos)
        total_dist = dist_to_relay + dist_from_relay
        
        # Direct distance for comparison
        direct_dist = _calculate_distance_meters(start_pos, end_pos)
        
        # Score based on efficiency (lower is better)
        # Prefer relays that don't add too much distance
        if total_dist < direct_dist * 1.5:  # Max 50% extra distance
            score = total_dist
            if score < best_score:
                best_score = score
                best_station = station
    
    return best_station

def create_relay_delivery(tables: Dict[str, Any], activity: Dict, relay_station: Dict) -> bool:
    """Create a two-part relay delivery."""
    try:
        fields = activity['fields']
        from_building_id = fields.get('FromBuilding')
        to_building_id = fields.get('ToBuilding')
        
        # Find two porters for the relay
        from_building = get_building_record(tables, from_building_id)
        if not from_building:
            return False
            
        from_pos = _get_building_position_coords(from_building)
        relay_pos = relay_station['position']
        
        # Find porter for first leg
        porter1 = find_available_porter(tables, from_pos, [])
        if not porter1:
            log.warning("No porter available for relay first leg")
            return False
        
        # Find porter for second leg
        porter2 = find_available_porter(tables, relay_pos, [porter1['fields'].get('Username')])
        if not porter2:
            log.warning("No porter available for relay second leg")
            return False
        
        # Create first leg activity
        now_utc = datetime.datetime.now(pytz.UTC)
        
        # Create a virtual relay building ID
        relay_building_id = f"relay_{relay_station['id']}"
        
        activity1_data = {
            'ActivityId': f"relay1-{porter1['fields'].get('Username')}-{uuid.uuid4().hex[:8]}",
            'Type': 'fetch_resource',
            'Status': 'pending',
            'Citizen': porter1['fields'].get('Username'),
            'FromBuilding': from_building_id,
            'ToBuilding': relay_building_id,
            'Resources': fields.get('Resources'),
            'ContractId': fields.get('ContractId'),
            'CreatedAt': now_utc.isoformat(),
            'StartDate': now_utc.isoformat(),
            'Priority': 15,
            'Notes': f"Relay delivery leg 1/2 to {relay_station['name']}",
            'Title': f"Relay to {relay_station['name']}",
            'Description': f"First leg of relay delivery to {relay_station['name']}"
        }
        
        # Estimate first leg completion time (simplified)
        leg1_duration = datetime.timedelta(minutes=30)
        leg2_start = now_utc + leg1_duration
        
        activity2_data = {
            'ActivityId': f"relay2-{porter2['fields'].get('Username')}-{uuid.uuid4().hex[:8]}",
            'Type': 'fetch_resource',
            'Status': 'pending',
            'Citizen': porter2['fields'].get('Username'),
            'FromBuilding': relay_building_id,
            'ToBuilding': to_building_id,
            'Resources': fields.get('Resources'),
            'ContractId': fields.get('ContractId'),
            'CreatedAt': now_utc.isoformat(),
            'StartDate': leg2_start.isoformat(),
            'Priority': 15,
            'Notes': f"Relay delivery leg 2/2 from {relay_station['name']}",
            'Title': f"Relay from {relay_station['name']}",
            'Description': f"Second leg of relay delivery from {relay_station['name']}"
        }
        
        # Create both activities
        tables['activities'].create(activity1_data)
        tables['activities'].create(activity2_data)
        
        log.info(f"Created relay delivery through {relay_station['name']} with porters {porter1['fields'].get('Username')} and {porter2['fields'].get('Username')}")
        
        # Mark original as handled
        tables['activities'].update(activity['id'], {
            'Status': 'processed',
            'UpdatedAt': now_utc.isoformat(),
            'Notes': fields.get('Notes', '') + f"\nConverted to relay delivery through {relay_station['name']}"
        })
        
        return True
        
    except Exception as e:
        log.error(f"Error creating relay delivery: {e}")
        return False

def process_delivery_retries(dry_run: bool = False):
    """Main function to process failed deliveries and implement retries."""
    log_header("Delivery Retry Handler - Fraglia dei Bastazi", LogColors.HEADER)
    
    tables = initialize_airtable()
    
    # Get recent failed deliveries
    failed_deliveries = get_failed_deliveries(tables)
    
    if not failed_deliveries:
        log.info("No failed deliveries to process")
        return
    
    log.info(f"Processing {len(failed_deliveries)} failed deliveries...")
    
    # Track statistics
    stats = {
        'retried': 0,
        'automated': 0,
        'relayed': 0,
        'max_retries': 0,
        'no_porter': 0
    }
    
    for activity in failed_deliveries:
        fields = activity['fields']
        activity_id = fields.get('ActivityId', activity['id'])
        
        # Get retry count
        retry_count = get_retry_count(activity)
        
        if retry_count >= MAX_RETRIES:
            log.warning(f"Activity {activity_id} has reached max retries ({MAX_RETRIES})")
            stats['max_retries'] += 1
            continue
        
        # Parse resources to check size
        resources_json = fields.get('Resources', '[]')
        try:
            resources = json.loads(resources_json)
            total_amount = sum(r.get('Amount', 0) for r in resources)
        except:
            total_amount = 999  # Assume large if can't parse
        
        if dry_run:
            log.info(f"[DRY RUN] Would process activity {activity_id} (retry {retry_count}, amount {total_amount})")
            continue
        
        # Try automated delivery for small packages
        if total_amount <= SMALL_DELIVERY_THRESHOLD:
            if create_automated_delivery(tables, activity):
                log.info(f"Created automated delivery for {activity_id}")
                stats['automated'] += 1
                continue
        
        # Check distance for relay consideration
        from_building_id = fields.get('FromBuilding')
        to_building_id = fields.get('ToBuilding')
        
        from_building = get_building_record(tables, from_building_id)
        to_building = get_building_record(tables, to_building_id)
        
        from_pos = None  # Initialize from_pos
        if from_building and to_building:
            from_pos = _get_building_position_coords(from_building)
            to_pos = _get_building_position_coords(to_building)
            
            if from_pos and to_pos:
                distance = _calculate_distance_meters(from_pos, to_pos)
                
                # Use relay for long distances
                if distance > RELAY_DISTANCE_THRESHOLD:
                    relay_station = find_relay_station(from_pos, to_pos)
                    if relay_station:
                        if create_relay_delivery(tables, activity, relay_station):
                            log.info(f"Created relay delivery for {activity_id}")
                            stats['relayed'] += 1
                            continue
        
        # Standard retry with new porter
        exclude_porters = [fields.get('Citizen')]  # Exclude original porter
        
        # Add previous retry porters to exclusion list
        notes = fields.get('Notes', '')
        if 'Original porter:' in notes:
            parts = notes.split('Original porter:')
            for part in parts[1:]:
                porter_name = part.split('.')[0].strip()
                exclude_porters.append(porter_name)
        
        # If we don't have from_pos, try to get it from the from_building for porter selection
        if not from_pos and from_building:
            from_pos = _get_building_position_coords(from_building)
        
        # Find new porter (pass from_pos which might be None)
        new_porter = find_available_porter(tables, from_pos, exclude_porters)
        
        if new_porter:
            if create_retry_activity(tables, activity, new_porter, retry_count):
                log.info(f"Created retry {retry_count + 1} for {activity_id} with porter {new_porter['fields'].get('Username')}")
                stats['retried'] += 1
                
                # Mark original as superseded
                tables['activities'].update(activity['id'], {
                    'Status': 'superseded',
                    'UpdatedAt': datetime.datetime.now(pytz.UTC).isoformat(),
                    'Notes': fields.get('Notes', '') + f"\nSuperseded by retry {retry_count + 1}"
                })
        else:
            log.warning(f"No available porter for retry of {activity_id}")
            stats['no_porter'] += 1
    
    # Summary
    log.info(f"{LogColors.OKGREEN}Delivery retry processing complete:{LogColors.ENDC}")
    log.info(f"  - Standard retries: {stats['retried']}")
    log.info(f"  - Automated deliveries: {stats['automated']}")
    log.info(f"  - Relay deliveries: {stats['relayed']}")
    log.info(f"  - Max retries reached: {stats['max_retries']}")
    log.info(f"  - No porter available: {stats['no_porter']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process failed deliveries with retry logic")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    process_delivery_retries(dry_run=args.dry_run)
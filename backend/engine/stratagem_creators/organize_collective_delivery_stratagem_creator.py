"""
Creator for 'organize_collective_delivery' stratagems.
Enables citizens to organize mass resource delivery campaigns to buildings or citizens.
"""
import logging
import json
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_building_record,
    get_citizen_record,
    VENICE_TIMEZONE
)

log = logging.getLogger(__name__)

# Stratagem duration and limits
STRATAGEM_DURATION_HOURS = 24  # Collective actions run for 24 hours
MAX_PARTICIPANTS = 50  # Maximum number of delivery participants
MAX_DELIVERY_AMOUNT_PER_CITIZEN = 100  # Max units each citizen can deliver


def create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    target_building_id: Optional[str] = None,
    target_citizen_username: Optional[str] = None,
    resource_type: str = None,
    max_total_amount: Optional[int] = None,
    reward_per_unit: Optional[float] = None,
    description: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates an 'organize_collective_delivery' stratagem.
    
    Args:
        target_building_id: Building to deliver to (building mode)
        target_citizen_username: Citizen whose buildings receive deliveries (citizen mode)
        resource_type: Type of resource to collect
        max_total_amount: Maximum total units to collect (optional)
        reward_per_unit: Ducats per unit delivered (optional)
        description: Public description of the collective action
    
    Either target_building_id OR target_citizen_username must be specified, not both.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username
    
    # Validate inputs
    if not resource_type:
        log.error(f"[Collective Delivery] No resource type specified")
        return None
    
    if not (target_building_id or target_citizen_username):
        log.error(f"[Collective Delivery] Must specify either target building or citizen")
        return None
    
    if target_building_id and target_citizen_username:
        log.error(f"[Collective Delivery] Cannot specify both building and citizen targets")
        return None
    
    # Verify citizen has funds if offering rewards
    total_potential_reward = 0
    if reward_per_unit and max_total_amount:
        total_potential_reward = reward_per_unit * max_total_amount
        citizen_ducats = citizen_record['fields'].get('Ducats', 0)
        if citizen_ducats < total_potential_reward:
            log.warning(f"[Collective Delivery] {citizen_name} has insufficient funds for max reward ({citizen_ducats} < {total_potential_reward})")
            return None
    
    # Determine target details
    target_details = {}
    if target_building_id:
        # Building mode
        building = get_building_record(tables, target_building_id)
        if not building:
            log.error(f"[Collective Delivery] Target building {target_building_id} not found")
            return None
        
        target_details = {
            'mode': 'building',
            'building_id': target_building_id,
            'building_name': building['fields'].get('Name', 'Unknown Building'),
            'building_type': building['fields'].get('Type'),
            'run_by': building['fields'].get('RunBy'),
            'position': building['fields'].get('Position')
        }
        
        stratagem_title = f"Deliver {resource_type} to {target_details['building_name']}"
    else:
        # Citizen mode - find all buildings run by target citizen
        target_citizen = get_citizen_record(tables, target_citizen_username)
        if not target_citizen:
            log.error(f"[Collective Delivery] Target citizen {target_citizen_username} not found")
            return None
        
        # Find buildings run by this citizen
        target_buildings = list(tables['buildings'].all(
            formula=f"{{RunBy}}='{target_citizen_username}'"
        ))
        
        if not target_buildings:
            log.warning(f"[Collective Delivery] {target_citizen_username} doesn't run any buildings")
            return None
        
        target_details = {
            'mode': 'citizen',
            'citizen_username': target_citizen_username,
            'citizen_name': f"{target_citizen['fields'].get('FirstName', '')} {target_citizen['fields'].get('LastName', '')}".strip(),
            'building_ids': [b['fields'].get('BuildingId') for b in target_buildings],
            'building_count': len(target_buildings)
        }
        
        stratagem_title = f"Deliver {resource_type} to {target_details['citizen_name']}'s buildings"
    
    # Create stratagem description
    if not description:
        description = f"{citizen_name} organizes collective delivery of {resource_type}"
        if reward_per_unit:
            description += f" - Paying {reward_per_unit} ducats per unit!"
    
    # Calculate end time
    start_time = datetime.now(pytz.utc)
    end_time = start_time + timedelta(hours=STRATAGEM_DURATION_HOURS)
    
    # Stratagem details
    stratagem_details = {
        'organizer': citizen_username,
        'resource_type': resource_type,
        'target': target_details,
        'max_total_amount': max_total_amount or 9999,  # Default to effectively unlimited
        'collected_amount': 0,
        'reward_per_unit': reward_per_unit or 0,
        'total_rewards_paid': 0,
        'participants': [],  # List of {username, amount_delivered, reward_earned}
        'deliveries': [],  # List of completed delivery activity IDs
        'escrow_ducats': total_potential_reward if reward_per_unit else 0
    }
    
    # Create stratagem record
    stratagem_data = {
        'StratagemId': f"collective_delivery_{citizen_username}_{int(start_time.timestamp())}",
        'Type': 'organize_collective_delivery',
        'Status': 'active',
        'ExecutedBy': citizen_username,
        'ExecutedAt': start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),  # When executed
        'ExpiresAt': end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),  # When expires
        'Name': stratagem_title,  # Using 'Name' field from schema
        'Description': description,
        'Notes': json.dumps(stratagem_details),  # Using Notes field for details
        'Category': 'economic_cooperation'  # Collective action category
    }
    
    try:
        stratagem = tables['stratagems'].create(stratagem_data)
        
        # Deduct escrow amount if offering rewards
        if total_potential_reward > 0:
            new_ducats = citizen_ducats - total_potential_reward
            tables['citizens'].update(citizen_record['id'], {'Ducats': new_ducats})
            log.info(f"[Collective Delivery] Escrowed {total_potential_reward} ducats from {citizen_name}")
        
        # Create notification for target (if citizen mode)
        if target_details['mode'] == 'citizen':
            tables['notifications'].create({
                'Citizen': target_citizen_username,  # Changed from 'Recipient'
                'Type': 'stratagem_collective_delivery',  # Using 'Type' field
                'Content': f"{citizen_name} is organizing delivery of {resource_type} to your buildings. " +
                          (f"Paying {reward_per_unit} per unit!" if reward_per_unit else "Help is on the way!"),
                'Status': 'unread',
                'Asset': stratagem['id'],
                'AssetType': 'stratagem'
            })
        
        # Create public announcement
        tables['notifications'].create({
            'Citizen': 'PUBLIC',  # Public announcement
            'Type': 'stratagem_collective_delivery_public',
            'Content': description + f"\nJoin by delivering {resource_type} to the target!",
            'Status': 'unread',
            'Asset': stratagem['id'],
            'AssetType': 'stratagem'
        })
        
        log.info(f"{LogColors.OKGREEN}[Collective Delivery] {citizen_name} created stratagem: {stratagem_title}{LogColors.ENDC}")
        return stratagem
        
    except Exception as e:
        log.error(f"[Collective Delivery] Error creating stratagem: {e}")
        # Refund escrow on error
        if total_potential_reward > 0:
            tables['citizens'].update(citizen_record['id'], {'Ducats': citizen_ducats})
        return None
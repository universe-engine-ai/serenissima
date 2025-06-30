"""
Activity creator for interview_citizens activity.
Innovatori interview other citizens to gather insights about problems and opportunities.
"""

import logging
import json
from datetime import datetime, timedelta
import pytz
import random
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    _calculate_distance_meters,
    get_path_between_points,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

# Duration range for interview activities
MIN_INTERVIEW_HOURS = 2
MAX_INTERVIEW_HOURS = 3

# Payment ranges by social class
INTERVIEW_PAYMENT_BY_CLASS = {
    'Nobili': (40, 50),
    'Clero': (30, 40),
    'Scientisti': (30, 40),
    'Artisti': (25, 35),
    'Cittadini': (20, 30),
    'Forestieri': (15, 25),
    'Popolani': (15, 20),
    'Facchini': (10, 15)
}

# Minimum relationship strength required
MIN_RELATIONSHIP_STRENGTH = 30

def _check_innovatori_resources_for_interview(
    tables: Dict[str, Any], 
    citizen_username: str,
    payment_amount: int
) -> bool:
    """Check if the Innovatori has resources for interview (paper and ducats for payment)."""
    try:
        # Check paper
        paper_resources = tables['resources'].all(
            formula=f"AND({{Holder}}='{citizen_username}', {{Type}}='paper')",
            max_records=1
        )
        
        if not paper_resources or paper_resources[0]['fields'].get('Quantity', 0) < 1:
            log.info(f"Innovatori {citizen_username} lacks paper for interview")
            return False
        
        # Check ducats
        citizen = tables['citizens'].all(
            formula=f"{{Username}}='{citizen_username}'",
            max_records=1
        )
        
        if not citizen:
            return False
            
        wealth = citizen[0]['fields'].get('Wealth', 0)
        if wealth < payment_amount:
            log.info(f"Innovatori {citizen_username} lacks funds for interview payment ({wealth} < {payment_amount})")
            return False
            
        return True
        
    except Exception as e:
        log.error(f"Error checking interview resources: {e}")
        return False

def _find_suitable_interviewees(
    tables: Dict[str, Any],
    citizen_username: str,
    citizen_position: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Find citizens suitable for interviewing based on relationships and location."""
    
    suitable_interviewees = []
    
    # Get relationships
    relationships = tables['relationships'].all(
        formula=f"OR({{Citizen1}}='{citizen_username}', {{Citizen2}}='{citizen_username}')"
    )
    
    for rel in relationships:
        strength = rel['fields'].get('StrengthScore', 0)
        if strength < MIN_RELATIONSHIP_STRENGTH:
            continue
            
        # Get the other citizen
        other_username = (
            rel['fields']['Citizen2'] if rel['fields']['Citizen1'] == citizen_username
            else rel['fields']['Citizen1']
        )
        
        # Get citizen data
        other_citizen = tables['citizens'].all(
            formula=f"AND({{Username}}='{other_username}', {{InVenice}}=1)",
            max_records=1
        )
        
        if not other_citizen:
            continue
            
        citizen_data = other_citizen[0]
        
        # Check if they have a position
        position_str = citizen_data['fields'].get('Position')
        if not position_str:
            continue
            
        try:
            other_position = json.loads(position_str)
        except:
            continue
        
        # Calculate distance
        distance = _calculate_distance_meters(citizen_position, other_position)
        
        # Calculate interview value score
        social_class = citizen_data['fields'].get('SocialClass', 'Popolani')
        
        # Higher classes might have more interesting insights
        class_score = {
            'Nobili': 100,
            'Clero': 90,
            'Scientisti': 95,
            'Artisti': 85,
            'Cittadini': 70,
            'Forestieri': 60,
            'Popolani': 50,
            'Facchini': 40
        }.get(social_class, 50)
        
        # Check for recent problems (makes them more interesting to interview)
        recent_problems = tables['problems'].all(
            formula=f"AND({{Citizen}}='{other_username}', {{Status}}='active')",
            max_records=5
        )
        
        problem_score = len(recent_problems) * 20  # Each problem adds value
        
        # Combine scores
        total_score = class_score + problem_score + strength - (distance / 100)  # Distance penalty
        
        # Check if we've interviewed them recently
        recent_interviews = tables['activities'].all(
            formula=(f"AND({{Citizen}}='{citizen_username}', {{Type}}='interview_citizens', "
                    f"{{Status}}='completed')"),
            max_records=20
        )
        
        recently_interviewed = False
        for activity in recent_interviews:
            params = activity['fields'].get('Parameters', '{}')
            try:
                params_dict = json.loads(params) if isinstance(params, str) else params
                if params_dict.get('targetCitizen') == other_username:
                    created_at = activity['fields'].get('CreatedAt')
                    if created_at:
                        activity_time = dateutil_parser.parse(created_at)
                        days_ago = (datetime.now(pytz.UTC) - activity_time).days
                        if days_ago < 3:  # Interviewed within 3 days
                            recently_interviewed = True
                            break
            except:
                pass
        
        if recently_interviewed:
            total_score -= 50  # Significant penalty
        
        suitable_interviewees.append({
            'citizen': citizen_data,
            'username': other_username,
            'distance': distance,
            'score': total_score,
            'relationship_strength': strength,
            'social_class': social_class,
            'active_problems': len(recent_problems)
        })
    
    return suitable_interviewees

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    transport_api_url: str,
    api_base_url: str,
    activity_duration: Optional[float] = None,
    activity_end_time: Optional[datetime] = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Try to create an interview_citizens activity for an Innovatori.
    
    Args:
        tables: Database tables
        citizen_record: The citizen record
        resource_defs: Resource definitions
        building_type_defs: Building type definitions
        transport_api_url: Transport API URL
        api_base_url: Base API URL
        activity_duration: Optional duration in hours
        activity_end_time: Optional specific end time
        **kwargs: Additional parameters (may include targetCitizen)
        
    Returns:
        Created activity record or None
    """
    
    citizen_username = citizen_record['fields'].get('Username')
    citizen_id = citizen_record['fields'].get('CitizenId')
    citizen_airtable_id = citizen_record['id']
    
    # Verify this is an Innovatori
    social_class = citizen_record['fields'].get('SocialClass')
    if social_class != 'Innovatori':
        log.warning(f"Citizen {citizen_username} is not an Innovatori (class: {social_class})")
        return None
    
    # Get citizen position
    position_str = citizen_record['fields'].get('Position')
    if not position_str:
        log.warning(f"No position for citizen {citizen_username}")
        return None
        
    try:
        citizen_position = json.loads(position_str)
    except json.JSONDecodeError:
        log.error(f"Invalid position format for citizen {citizen_username}")
        return None
    
    # Check if a specific target was provided
    target_username = kwargs.get('targetCitizen')
    
    if target_username:
        # Verify the target exists and get their data
        target_citizens = tables['citizens'].all(
            formula=f"AND({{Username}}='{target_username}', {{InVenice}}=1)",
            max_records=1
        )
        
        if not target_citizens:
            log.warning(f"Target citizen {target_username} not found or not in Venice")
            return None
            
        target_data = {
            'citizen': target_citizens[0],
            'username': target_username,
            'social_class': target_citizens[0]['fields'].get('SocialClass', 'Popolani')
        }
    else:
        # Find suitable interviewees
        candidates = _find_suitable_interviewees(tables, citizen_username, citizen_position)
        
        if not candidates:
            log.info(f"No suitable interview candidates found for {citizen_username}")
            return None
        
        # Sort by score and select from top 3
        candidates.sort(key=lambda x: x['score'], reverse=True)
        top_candidates = candidates[:3]
        
        # Weighted random selection
        target_data = random.choice(top_candidates)
        target_username = target_data['username']
    
    # Calculate payment
    target_class = target_data.get('social_class', 'Popolani')
    payment_range = INTERVIEW_PAYMENT_BY_CLASS.get(target_class, (10, 20))
    payment = random.randint(payment_range[0], payment_range[1])
    
    # Check resources including payment
    if not _check_innovatori_resources_for_interview(tables, citizen_username, payment):
        log.info(f"Innovatori {citizen_username} lacks resources for interview")
        return None
    
    # Get target position
    target_citizen = target_data.get('citizen')
    if not target_citizen:
        target_citizens = tables['citizens'].all(
            formula=f"{{Username}}='{target_username}'",
            max_records=1
        )
        if not target_citizens:
            return None
        target_citizen = target_citizens[0]
    
    target_position_str = target_citizen['fields'].get('Position')
    if not target_position_str:
        log.warning(f"No position for target citizen {target_username}")
        return None
        
    try:
        target_position = json.loads(target_position_str)
    except:
        return None
    
    # Calculate distance
    distance = _calculate_distance_meters(citizen_position, target_position)
    
    if distance > 50:  # Need to go to them
        log.info(f"Creating goto activity first - citizen is {distance:.0f}m from {target_username}")
        
        # Find where the target is (building or open location)
        target_building_id = None
        buildings = tables['buildings'].all()
        
        for building in buildings:
            building_pos = json.loads(building['fields'].get('Position', '{}'))
            if building_pos:
                dist_to_building = _calculate_distance_meters(target_position, building_pos)
                if dist_to_building < 20:  # Within 20m of building
                    target_building_id = building['id']
                    break
        
        # Create goto activity
        goto_result = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url,
            target_building_id=target_building_id,
            target_position=target_position,
            purpose=f"interview_{target_username}"
        )
        
        if goto_result:
            log.info(f"Created goto activity for {citizen_username} to reach {target_username}")
            return goto_result
        else:
            log.error(f"Failed to create goto activity for interview")
            return None
    
    # We're close enough, create the interview activity
    now_utc = datetime.now(pytz.UTC)
    
    # Determine duration
    if activity_duration:
        duration_hours = activity_duration
    else:
        duration_hours = random.uniform(MIN_INTERVIEW_HOURS, MAX_INTERVIEW_HOURS)
    
    if activity_end_time:
        end_time = activity_end_time
    else:
        end_time = now_utc + timedelta(hours=duration_hours)
    
    # Get path
    path_result = get_path_between_points(
        transport_api_url,
        citizen_position['lat'],
        citizen_position['lng'],
        target_position['lat'],
        target_position['lng']
    )
    
    if not path_result or not path_result.get('success'):
        path_data = json.dumps([citizen_position, target_position])
    else:
        path_data = json.dumps(path_result['data']['path_points'])
    
    # Create activity parameters
    activity_params = {
        'targetCitizen': target_username,
        'targetSocialClass': target_class,
        'payment': payment,
        'purpose': kwargs.get('purpose', 'gather_insights'),
        'interviewType': 'innovation_research',
        'duration_hours': duration_hours,
        'topics': ['problems', 'opportunities', 'pain_points', 'wishes'],
        'requiredResources': {
            'paper': 1,
            'ducats': payment
        }
    }
    
    # Add extra context if available
    if 'active_problems' in target_data:
        activity_params['targetHasProblems'] = target_data['active_problems']
    if 'relationship_strength' in target_data:
        activity_params['relationshipStrength'] = target_data['relationship_strength']
    
    # Create the activity
    activity_record = create_activity_record(
        tables=tables,
        citizen_custom_id=citizen_id,
        citizen_username=citizen_username,
        citizen_airtable_id=citizen_airtable_id,
        activity_type='interview_citizens',
        activity_subtype='work',
        activity_parameters=activity_params,
        start_time=now_utc,
        end_time=end_time,
        path_data=path_data
    )
    
    if activity_record:
        log.info(f"{LogColors.OKGREEN}Created interview_citizens activity for {citizen_username} "
                 f"to interview {target_username} ({target_class}) for {duration_hours:.1f} hours "
                 f"with payment of {payment} ducats{LogColors.ENDC}")
        return activity_record
    else:
        log.error(f"Failed to create interview_citizens activity record")
        return None
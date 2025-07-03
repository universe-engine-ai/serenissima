"""
Activity creator for present_innovation activity.
Innovatori present their innovations to guild members and other citizens.
"""

import logging
import json
import random
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters,
    get_path_between_points,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser,
    _escape_airtable_value
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

# Duration range for presentations
MIN_PRESENTATION_HOURS = 2
MAX_PRESENTATION_HOURS = 4

# Presentation venues and their characteristics
PRESENTATION_VENUES = {
    'guild_hall': {
        'formal': True,
        'audience_size': (10, 30),
        'prestige': 'high'
    },
    'town_hall': {
        'formal': True,
        'audience_size': (20, 50),
        'prestige': 'very_high'
    },
    'piazza': {
        'formal': False,
        'audience_size': (5, 20),
        'prestige': 'medium'
    },
    'inn': {
        'formal': False,
        'audience_size': (5, 15),
        'prestige': 'low'
    }
}

def _find_presentation_venue(tables: Dict[str, Any], citizen_position: Dict[float, float],
                           preferred_formal: bool = True) -> Optional[Dict[str, Any]]:
    """Find a suitable venue for presenting the innovation."""
    try:
        # Build formula for appropriate venue types
        if preferred_formal:
            venue_formula = "AND(OR({Type}='guild_hall', {Type}='town_hall'), {Status}='active')"
        else:
            venue_formula = "AND(OR({Type}='guild_hall', {Type}='town_hall', {Type}='inn'), {Status}='active')"
        
        venues = tables['buildings'].all(formula=venue_formula)
        if not venues:
            # Fallback to any active public building
            venues = tables['buildings'].all(
                formula="AND({Status}='active', OR({IsPublic}=TRUE(), {Type}='inn'))"
            )
        
        if not venues:
            return None
        
        # Find closest venue
        closest_venue = None
        min_distance = float('inf')
        
        for venue in venues:
            venue_pos = _get_building_position_coords(venue['fields'], venue['id'])
            if venue_pos:
                distance = _calculate_distance_meters(
                    citizen_position['lat'], citizen_position['lng'],
                    venue_pos['lat'], venue_pos['lng']
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_venue = venue
                    
        return closest_venue
        
    except Exception as e:
        log.error(f"Error finding presentation venue: {e}")
        return None

def _gather_audience(tables: Dict[str, Any], venue_type: str, 
                    citizen_username: str) -> List[Dict[str, Any]]:
    """Gather potential audience members based on venue type."""
    audience = []
    
    try:
        venue_info = PRESENTATION_VENUES.get(venue_type, PRESENTATION_VENUES['guild_hall'])
        min_size, max_size = venue_info['audience_size']
        target_size = random.randint(min_size, max_size)
        
        # Different audience types based on venue
        if venue_type == 'guild_hall':
            # Guild members and professionals
            formula = (
                f"AND({{Username}}!='{_escape_airtable_value(citizen_username)}', "
                f"{{Status}}='active', "
                f"OR({{SocialClass}}='Innovatori', {{SocialClass}}='Scientisti', "
                f"{{SocialClass}}='merchant', {{SocialClass}}='patrician'))"
            )
        elif venue_type == 'town_hall':
            # Government officials and nobles
            formula = (
                f"AND({{Username}}!='{_escape_airtable_value(citizen_username)}', "
                f"{{Status}}='active', "
                f"OR({{SocialClass}}='patrician', {{SocialClass}}='noble', "
                f"{{SocialClass}}='merchant'))"
            )
        else:
            # General public
            formula = f"AND({{Username}}!='{_escape_airtable_value(citizen_username)}', {{Status}}='active')"
        
        potential_audience = tables['citizens'].all(
            formula=formula,
            max_records=target_size * 2
        )
        
        # Randomly select audience members
        if potential_audience:
            audience = random.sample(
                potential_audience,
                min(len(potential_audience), target_size)
            )
            
    except Exception as e:
        log.error(f"Error gathering audience: {e}")
        
    return audience

def _determine_presentation_success(blueprint_exists: bool, prototype_tested: bool,
                                  audience_size: int, venue_prestige: str) -> float:
    """Calculate success probability based on preparation and context."""
    base_success = 0.5
    
    # Preparation bonuses
    if blueprint_exists:
        base_success += 0.15
    if prototype_tested:
        base_success += 0.15
        
    # Audience size factor (medium is optimal)
    if 10 <= audience_size <= 20:
        base_success += 0.1
    elif audience_size > 30:
        base_success -= 0.1
        
    # Venue prestige factor
    prestige_bonuses = {
        'very_high': 0.15,
        'high': 0.1,
        'medium': 0.05,
        'low': 0.0
    }
    base_success += prestige_bonuses.get(venue_prestige, 0.05)
    
    return min(0.95, max(0.1, base_success))

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
    Create a present_innovation activity for an Innovatori citizen.
    
    Returns:
        Dict containing the created activity record, or None if creation failed
    """
    try:
        citizen_fields = citizen_record.get('fields', {})
        citizen_id = citizen_record.get('id')
        citizen_username = citizen_fields.get('Username')
        citizen_position_str = citizen_fields.get('Position')
        
        if not all([citizen_id, citizen_username, citizen_position_str]):
            log.warning(f"Missing required citizen data")
            return None
        
        # Parse citizen position
        try:
            lat, lng = map(float, citizen_position_str.split('_'))
            citizen_pos = {'lat': lat, 'lng': lng}
        except:
            log.error(f"Invalid citizen position format: {citizen_position_str}")
            return None
        
        # Check for recent blueprint or prototype work
        has_blueprint = False
        has_tested_prototype = False
        try:
            preparation_formula = (
                f"AND({{CitizenId}}='{citizen_id}', {{Status}}='completed', "
                f"OR({{Type}}='draft_blueprint', {{Type}}='test_innovation'), "
                f"DATETIME_DIFF(NOW(), {{EndTime}}, 'days') < 14)"
            )
            recent_prep = tables['activities'].all(formula=preparation_formula)
            
            for activity in recent_prep:
                if activity['fields'].get('Type') == 'draft_blueprint':
                    has_blueprint = True
                elif activity['fields'].get('Type') == 'test_innovation':
                    has_tested_prototype = True
        except:
            pass
        
        # Find presentation venue
        venue = _find_presentation_venue(tables, citizen_pos, preferred_formal=has_blueprint)
        if not venue:
            log.info(f"{LogColors.WARNING}No suitable presentation venue found{LogColors.ENDC}")
            return None
            
        venue_fields = venue.get('fields', {})
        venue_id = venue.get('id')
        venue_name = venue_fields.get('Name', 'Venue')
        venue_type = venue_fields.get('Type', 'guild_hall')
        
        # Get venue position
        venue_pos = _get_building_position_coords(venue_fields, venue_id)
        if not venue_pos:
            log.error(f"Could not get position for venue {venue_id}")
            return None
        
        # Calculate distance to venue
        distance = _calculate_distance_meters(
            citizen_pos['lat'], citizen_pos['lng'],
            venue_pos['lat'], venue_pos['lng']
        )
        
        # Create goto activity if not at venue
        if distance > 50:  # More than 50 meters away
            goto_result = try_create_goto_location_activity(
                tables=tables,
                citizen_record=citizen_record,
                target_position={'lat': venue_pos['lat'], 'lng': venue_pos['lng']},
                target_building_id=venue_id,
                purpose=f"go to {venue_name} to present innovation",
                resource_defs=resource_defs,
                building_type_defs=building_type_defs,
                transport_api_url=transport_api_url,
                api_base_url=api_base_url
            )
            
            if goto_result:
                log.info(f"{LogColors.OKGREEN}Created goto activity to presentation venue{LogColors.ENDC}")
                return goto_result
            else:
                log.error("Failed to create goto activity to venue")
                return None
        
        # Gather audience
        audience = _gather_audience(tables, venue_type, citizen_username)
        audience_names = []
        audience_ids = []
        
        for member in audience:
            m_fields = member.get('fields', {})
            m_name = f"{m_fields.get('FirstName', '')} {m_fields.get('LastName', '')}".strip()
            if not m_name:
                m_name = m_fields.get('Username', 'Unknown')
            audience_names.append(m_name)
            audience_ids.append(member.get('id'))
        
        # Determine presentation success probability
        venue_info = PRESENTATION_VENUES.get(venue_type, PRESENTATION_VENUES['guild_hall'])
        success_probability = _determine_presentation_success(
            has_blueprint, has_tested_prototype,
            len(audience), venue_info['prestige']
        )
        
        # Determine presentation duration
        if activity_duration:
            duration_hours = activity_duration
        else:
            base_hours = random.uniform(MIN_PRESENTATION_HOURS, MAX_PRESENTATION_HOURS)
            # Longer presentations for larger audiences
            audience_factor = 1 + (len(audience) / 50)
            duration_hours = base_hours * audience_factor
        
        # Calculate end time
        now_utc = datetime.now(pytz.UTC)
        venice_tz = pytz.timezone(VENICE_TIMEZONE)
        now_venice = now_utc.astimezone(venice_tz)
        
        if activity_end_time:
            end_time_utc = activity_end_time
        else:
            end_time_venice = now_venice + timedelta(hours=duration_hours)
            end_time_utc = end_time_venice.astimezone(pytz.UTC)
        
        # Create activity parameters
        activity_params = {
            'venue_id': venue_id,
            'venue_name': venue_name,
            'venue_type': venue_type,
            'venue_prestige': venue_info['prestige'],
            'formal_presentation': venue_info['formal'],
            'audience_count': len(audience),
            'audience_ids': audience_ids,
            'audience_names': audience_names,
            'has_blueprint': has_blueprint,
            'has_tested_prototype': has_tested_prototype,
            'success_probability': success_probability,
            'duration_hours': duration_hours
        }
        
        # Create notes
        preparation_notes = []
        if has_blueprint:
            preparation_notes.append("with formal blueprint")
        if has_tested_prototype:
            preparation_notes.append("with tested prototype")
        prep_str = " and ".join(preparation_notes) if preparation_notes else "without formal preparation"
        
        notes = (f"Presenting innovation at {venue_name} to {len(audience)} citizens {prep_str}. "
                f"Venue prestige: {venue_info['prestige']}, Success chance: {success_probability:.0%}")
        
        # Create activity title and description
        activity_title = f"Presenting Innovation at {venue_name}"
        activity_description = f"Presenting innovation to {len(audience)} citizens at {venue_name}"
        
        # Create thought based on preparation
        if has_blueprint and has_tested_prototype:
            activity_thought = "I'm well prepared with both blueprint and tested prototype. This presentation should go smoothly!"
        elif has_blueprint:
            activity_thought = "I have the blueprint ready. Time to share my vision with others."
        elif has_tested_prototype:
            activity_thought = "The prototype testing went well. Let me share what I've learned."
        else:
            activity_thought = "No formal preparation, but my ideas are clear. Let's see how the audience responds."
        
        # Create structured notes
        activity_notes = {
            "venue_id": venue_id,
            "venue_name": venue_name,
            "venue_type": venue_type,
            "venue_prestige": venue_info['prestige'],
            "formal_presentation": venue_info['formal'],
            "audience_count": len(audience),
            "audience_names": audience_names[:10],  # Limit to first 10 names
            "has_blueprint": has_blueprint,
            "has_tested_prototype": has_tested_prototype,
            "success_probability": success_probability,
            "duration_hours": duration_hours
        }
        
        # Create the activity record
        activity_record = create_activity_record(
            tables=tables,
            citizen_username=citizen_username,
            activity_type='present_innovation',
            start_date_iso=now_utc.isoformat(),
            end_date_iso=end_time_utc.isoformat(),
            from_building_id=venue_id,
            to_building_id=venue_id,
            title=activity_title,
            description=activity_description,
            thought=activity_thought,
            notes=json.dumps(activity_notes),
            priority_override=65  # High priority for presentations
        )
        
        if activity_record:
            log.info(f"{LogColors.OKGREEN}Created present_innovation activity for {citizen_username} "
                    f"at {venue_name} to {len(audience)} citizens{LogColors.ENDC}")
            return activity_record
        else:
            log.error(f"Failed to create activity record")
            return None
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error in present_innovation creator: {str(e)}{LogColors.ENDC}")
        return None
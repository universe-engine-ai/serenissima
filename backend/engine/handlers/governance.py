import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import random

from backend.engine.utils.activity_helpers import (
    LogColors,
    _get_building_position_coords,
    _calculate_distance_meters
)
from backend.engine.activity_creators.file_grievance_activity_creator import (
    try_create_file_grievance_activity
)
from backend.engine.activity_creators.support_grievance_activity_creator import (
    try_create_support_grievance_activity
)

log = logging.getLogger(__name__)


def get_citizen_wealth_breakdown(citizen_record: Dict[str, Any]) -> Dict[str, Any]:
    """Simple wealth breakdown for governance decisions."""
    total_wealth = citizen_record.get('Ducats', 0)
    # For now, assume most wealth is liquid unless citizen owns significant property
    # This is a simplified version - could be enhanced later
    return {
        'total_wealth': total_wealth,
        'liquid_wealth': int(total_wealth * 0.8) if total_wealth > 10000 else total_wealth
    }


def _handle_governance_participation(
    tables: Dict[str, Any], 
    citizen_record: Dict[str, Any], 
    is_night: bool, 
    resource_defs: Dict[str, Any], 
    building_type_defs: Dict[str, Any],
    now_venice_dt: datetime, 
    now_utc_dt: datetime, 
    transport_api_url: str, 
    api_base_url: str,
    citizen_position: Optional[Dict[str, float]], 
    citizen_custom_id: str, 
    citizen_username: str, 
    citizen_airtable_id: str, 
    citizen_name: str, 
    citizen_position_str: Optional[str],
    citizen_social_class: str, 
    check_only: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Determines if a citizen should engage in governance activities (filing or supporting grievances).
    
    This handler considers:
    - Citizen's economic situation (poor citizens more likely to file economic grievances)
    - Social class (different classes have different grievance priorities)
    - Recent messages or experiences that might motivate political action
    - Existing grievances that align with citizen's interests
    """
    
    # Don't do governance at night or if just checking
    if is_night or check_only:
        return None
    
    try:
        # Extract citizen data
        social_class = citizen_record.get('SocialClass', 'Popolani')
        wealth = citizen_record.get('Wealth', 0)
        influence = citizen_record.get('Influence', 0)
        
        # Get wealth breakdown to understand economic stress
        wealth_breakdown = get_citizen_wealth_breakdown(citizen_record)
        liquid_wealth = wealth_breakdown.get('liquid_wealth', 0)
        
        # Check if citizen can afford to participate
        min_fee = 10  # Support fee
        if liquid_wealth < min_fee * 2:  # Need some buffer
            return None
        
        # Determine political engagement likelihood based on class and situation
        engagement_probability = calculate_political_engagement_probability(
            social_class=social_class,
            wealth=wealth,
            influence=influence,
            liquid_wealth=liquid_wealth
        )
        
        # Random check for engagement
        if random.random() > engagement_probability:
            return None
        
        # Check if there's a Doge's Palace nearby
        doges_palace = find_doges_palace(tables)
        if not doges_palace:
            return None
        
        palace_position = _get_building_position_coords(doges_palace)
        if citizen_position and palace_position:
            distance = _calculate_distance_meters(
                citizen_position.get('lat'), citizen_position.get('lng'),
                palace_position.get('lat'), palace_position.get('lng')
            )
            # Only engage if reasonably close (within 500 meters)
            if distance > 500:
                return None
        
        # Decide between filing new grievance or supporting existing one
        if should_file_new_grievance(citizen_record, tables):
            # Generate grievance based on citizen's situation
            grievance_data = generate_grievance_content(
                citizen_record=citizen_record,
                social_class=social_class,
                wealth=wealth,
                liquid_wealth=liquid_wealth
            )
            
            log.info(f"{LogColors.OKBLUE}[Governance] {citizen_name} decides to file grievance about {grievance_data['category']}{LogColors.ENDC}")
            
            # Create the file_grievance activity
            activity = try_create_file_grievance_activity(
                tables=tables,
                citizen_record=citizen_record,
                citizen_position=citizen_position,
                resource_defs=resource_defs,
                building_type_defs=building_type_defs,
                now_venice_dt=now_venice_dt,
                now_utc_dt=now_utc_dt,
                transport_api_url=transport_api_url,
                api_base_url=api_base_url,
                grievance_data=grievance_data
            )
            
            if activity:
                log.info(f"{LogColors.OKGREEN}[Governance] {citizen_name}: Created file_grievance activity{LogColors.ENDC}")
            
            return activity
            
        else:
            # Look for grievance to support
            grievance_id = find_grievance_to_support(
                citizen_record=citizen_record,
                tables=tables,
                social_class=social_class
            )
            
            if grievance_id:
                # Determine support amount based on wealth
                support_amount = calculate_support_amount(liquid_wealth)
                
                log.info(f"{LogColors.OKBLUE}[Governance] {citizen_name} decides to support grievance #{grievance_id}{LogColors.ENDC}")
                
                # Create the support_grievance activity
                activity = try_create_support_grievance_activity(
                    tables=tables,
                    citizen_record=citizen_record,
                    citizen_position=citizen_position,
                    resource_defs=resource_defs,
                    building_type_defs=building_type_defs,
                    now_venice_dt=now_venice_dt,
                    now_utc_dt=now_utc_dt,
                    transport_api_url=transport_api_url,
                    api_base_url=api_base_url,
                    grievance_id=grievance_id,
                    support_amount=support_amount
                )
                
                if activity:
                    log.info(f"{LogColors.OKGREEN}[Governance] {citizen_name}: Created support_grievance activity{LogColors.ENDC}")
                
                return activity
        
        return None
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Governance] Error in governance handler: {e}{LogColors.ENDC}")
        return None


def calculate_political_engagement_probability(
    social_class: str,
    wealth: int,
    influence: int,
    liquid_wealth: int
) -> float:
    """Calculate probability of political engagement based on citizen characteristics."""
    
    # Base probabilities by class
    class_base_prob = {
        'Nobili': 0.15,      # Nobles engage to maintain power
        'Artisti': 0.20,     # Artists engage for cultural issues
        'Scientisti': 0.18,  # Scientists engage for progress
        'Clero': 0.12,       # Clergy engage for moral issues
        'Mercatores': 0.25,  # Merchants very politically active
        'Cittadini': 0.22,   # Citizens moderately active
        'Popolani': 0.15,    # Common people engage when desperate
        'Facchini': 0.10,    # Workers engage rarely
        'Forestieri': 0.05   # Foreigners least engaged
    }
    
    base_prob = class_base_prob.get(social_class, 0.10)
    
    # Adjust based on economic stress
    if liquid_wealth < 1000:
        base_prob *= 1.5  # Poor more likely to complain
    elif liquid_wealth > 100000:
        base_prob *= 0.8  # Very wealthy less motivated
    
    # Adjust based on influence
    if influence < 100:
        base_prob *= 0.8  # Low influence less likely to engage
    elif influence > 1000:
        base_prob *= 1.2  # High influence more engaged
    
    # Cap probability
    return min(base_prob, 0.3)  # Max 30% chance per check


def should_file_new_grievance(citizen_record: Dict[str, Any], tables: Dict[str, Any]) -> bool:
    """Determine if citizen should file new grievance vs support existing."""
    
    # Check if citizen recently filed a grievance (within 7 days)
    # For now, simple probability
    return random.random() < 0.3  # 30% chance to file new vs support


def generate_grievance_content(
    citizen_record: Dict[str, Any],
    social_class: str,
    wealth: int,
    liquid_wealth: int
) -> Dict[str, Any]:
    """Generate appropriate grievance content based on citizen's situation."""
    
    # Categories and templates by social class
    grievance_templates = {
        'Facchini': [
            {
                'category': 'economic',
                'title': 'Unbearable Tax Burden',
                'description': 'The taxes crush us workers while the wealthy grow richer. We demand fair taxation!'
            },
            {
                'category': 'social',
                'title': 'Worker Exploitation',
                'description': 'We toil endlessly for meager wages while our employers live in luxury. Justice for workers!'
            }
        ],
        'Popolani': [
            {
                'category': 'economic',
                'title': 'Rising Cost of Living',
                'description': 'Bread prices soar while wages stagnate. How are honest citizens to survive?'
            },
            {
                'category': 'infrastructure',
                'title': 'Neglected Neighborhoods',
                'description': 'Our districts crumble while palaces are gilded. We demand infrastructure investment!'
            }
        ],
        'Cittadini': [
            {
                'category': 'economic',
                'title': 'Unfair Market Regulations',
                'description': 'Excessive regulations strangle small businesses while monopolies thrive unchecked.'
            },
            {
                'category': 'social',
                'title': 'Limited Social Mobility',
                'description': 'Birth determines destiny in our Republic. Merit should matter more than bloodline!'
            }
        ],
        'Mercatores': [
            {
                'category': 'economic',
                'title': 'Trade Route Monopolies',
                'description': 'A few families control vital trade routes. Open commerce benefits all Venice!'
            },
            {
                'category': 'criminal',
                'title': 'Contract Enforcement Failures',
                'description': 'Broken contracts go unpunished. We need stronger commercial courts!'
            }
        ],
        'Artisti': [
            {
                'category': 'social',
                'title': 'Cultural Funding Crisis',
                'description': 'Art and culture wither without patronage. Venice must support its creative soul!'
            },
            {
                'category': 'infrastructure',
                'title': 'Workshop Space Shortage',
                'description': 'Artists lack affordable spaces to create. Dedicate buildings for cultural work!'
            }
        ],
        'Scientisti': [
            {
                'category': 'social',
                'title': 'Research Funding Inadequacy',
                'description': 'Scientific progress requires investment. Venice falls behind without supporting scholars!'
            },
            {
                'category': 'infrastructure',
                'title': 'Laboratory Access',
                'description': 'Scholars need proper facilities. Build public laboratories for advancement!'
            }
        ]
    }
    
    # Default templates for classes without specific ones
    default_templates = [
        {
            'category': 'economic',
            'title': 'Economic Inequality',
            'description': 'The gap between rich and poor widens daily. We demand economic justice!'
        },
        {
            'category': 'social',
            'title': 'Voice for the Voiceless',
            'description': 'Common citizens lack representation. Our voices matter too!'
        }
    ]
    
    # Select appropriate template
    templates = grievance_templates.get(social_class, default_templates)
    
    # Bias selection based on current situation
    if liquid_wealth < 500:
        # Very poor - prefer economic grievances
        economic_templates = [t for t in templates if t['category'] == 'economic']
        if economic_templates:
            templates = economic_templates
    
    # Random selection from appropriate templates
    selected = random.choice(templates)
    
    return {
        'category': selected['category'],
        'title': selected['title'],
        'description': selected['description']
    }


def find_grievance_to_support(
    citizen_record: Dict[str, Any],
    tables: Dict[str, Any],
    social_class: str
) -> Optional[str]:
    """Find an appropriate grievance for citizen to support."""
    
    # If GRIEVANCES table doesn't exist, support a mock grievance
    grievances_table = tables.get('GRIEVANCES')
    if not grievances_table:
        # Return mock grievance ID for testing
        return f"mock_grievance_{social_class.lower()}_001"
    
    # Get all active grievances
    all_grievances = grievances_table.all()
    active_grievances = [
        g for g in all_grievances 
        if g['fields'].get('Status') == 'filed'
    ]
    
    if not active_grievances:
        return None
    
    # Filter by relevance to citizen's class
    class_category_preferences = {
        'Facchini': ['economic', 'social'],
        'Popolani': ['economic', 'infrastructure'],
        'Cittadini': ['economic', 'social'],
        'Mercatores': ['economic', 'criminal'],
        'Artisti': ['social', 'infrastructure'],
        'Scientisti': ['social', 'infrastructure'],
        'Nobili': ['criminal', 'social'],
        'Clero': ['social', 'criminal']
    }
    
    preferred_categories = class_category_preferences.get(social_class, ['economic', 'social'])
    
    # Find grievances matching preferences
    relevant_grievances = [
        g for g in active_grievances
        if g['fields'].get('Category') in preferred_categories
    ]
    
    if not relevant_grievances:
        relevant_grievances = active_grievances
    
    # Sort by support count (join popular movements)
    relevant_grievances.sort(key=lambda g: g['fields'].get('SupportCount', 0), reverse=True)
    
    # Return most popular relevant grievance
    if relevant_grievances:
        return relevant_grievances[0]['id']
    
    return None


def calculate_support_amount(liquid_wealth: int) -> int:
    """Calculate how much a citizen should contribute to support a grievance."""
    
    base_amount = 10
    
    if liquid_wealth < 100:
        return base_amount
    elif liquid_wealth < 1000:
        return base_amount * 2
    elif liquid_wealth < 10000:
        return base_amount * 5
    elif liquid_wealth < 100000:
        return base_amount * 10
    else:
        return base_amount * 20


def find_doges_palace(tables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the Doge's Palace building."""
    
    buildings_table = tables['BUILDINGS']
    for building in buildings_table.all():
        if building['fields'].get('BuildingType') == 'doges_palace':
            return building['fields']
    
    return None
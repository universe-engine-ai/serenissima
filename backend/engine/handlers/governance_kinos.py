import logging
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import random
import os

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

# KinOS configuration
KINOS_API_KEY = os.getenv("KINOS_API_KEY")
KINOS_BASE_URL = "https://api.kinos-engine.ai/v2/blueprints/serenissima-ai"


def get_citizen_wealth_breakdown(citizen_record: Dict[str, Any]) -> Dict[str, Any]:
    """Simple wealth breakdown for governance decisions."""
    total_wealth = citizen_record.get('Ducats', 0)
    # For now, assume most wealth is liquid unless citizen owns significant property
    # This is a simplified version - could be enhanced later
    return {
        'total_wealth': total_wealth,
        'liquid_wealth': int(total_wealth * 0.8) if total_wealth > 10000 else total_wealth
    }


def _handle_governance_participation_kinos(
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
    Enhanced governance handler that uses KinOS for decision-making.
    
    This handler:
    1. Checks basic eligibility (time, location, wealth)
    2. Uses KinOS to decide whether to file or support a grievance
    3. Uses KinOS to generate grievance content if filing
    4. Creates the appropriate activity
    """
    
    # Don't do governance at night or if just checking
    if is_night or check_only:
        return None
    
    # Skip if KinOS is not configured
    if not KINOS_API_KEY:
        log.warning(f"[Governance] KinOS API key not configured, falling back to rule-based governance")
        # Could fall back to original handler here
        return None
    
    try:
        # Extract citizen data
        social_class = citizen_record.get('SocialClass', 'Popolani')
        wealth = citizen_record.get('Ducats', 0)
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
        
        # Gather context for KinOS
        citizen_context = gather_citizen_context_for_governance(
            citizen_record=citizen_record,
            tables=tables,
            api_base_url=api_base_url,
            wealth_breakdown=wealth_breakdown
        )
        
        # Get existing grievances for context
        existing_grievances = get_existing_grievances_for_kinos(tables, social_class)
        
        # Use KinOS to decide: file new grievance or support existing?
        governance_decision = ask_kinos_governance_decision(
            citizen_username=citizen_username,
            citizen_name=citizen_name,
            social_class=social_class,
            citizen_context=citizen_context,
            existing_grievances=existing_grievances,
            api_base_url=api_base_url
        )
        
        if not governance_decision:
            log.warning(f"[Governance] KinOS did not return a valid governance decision for {citizen_name}")
            return None
        
        # Process based on KinOS decision
        if governance_decision.get('action') == 'file_grievance':
            grievance_data = governance_decision.get('grievance_data', {})
            
            log.info(f"{LogColors.OKBLUE}[Governance] {citizen_name} decides to file grievance: {grievance_data.get('title')}{LogColors.ENDC}")
            
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
            
        elif governance_decision.get('action') == 'support_grievance':
            grievance_id = governance_decision.get('grievance_id')
            support_amount = governance_decision.get('support_amount', 10)
            
            if not grievance_id:
                log.warning(f"[Governance] KinOS chose to support but didn't specify grievance ID")
                return None
            
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
        
        else:
            log.info(f"[Governance] {citizen_name} chose not to engage in governance at this time")
            return None
        
    except Exception as e:
        log.error(f"{LogColors.FAIL}[Governance] Error in KinOS governance handler: {e}{LogColors.ENDC}")
        return None


def gather_citizen_context_for_governance(
    citizen_record: Dict[str, Any],
    tables: Dict[str, Any],
    api_base_url: str,
    wealth_breakdown: Dict[str, Any]
) -> Dict[str, Any]:
    """Gather relevant context about the citizen for KinOS decision-making."""
    
    context = {
        'social_class': citizen_record.get('SocialClass', 'Popolani'),
        'wealth': citizen_record.get('Ducats', 0),
        'liquid_wealth': wealth_breakdown.get('liquid_wealth', 0),
        'influence': citizen_record.get('Influence', 0),
        'occupation': citizen_record.get('Occupation', 'unemployed'),
        'employment_status': citizen_record.get('EmploymentStatus', 'unemployed'),
        'home_type': citizen_record.get('HomeType', 'homeless'),
        'hunger_level': citizen_record.get('HungerLevel', 50),
        'last_ate': citizen_record.get('LastAte', 'unknown')
    }
    
    # Add recent problems if available
    try:
        response = requests.get(f"{api_base_url}/problems", params={'citizen': citizen_record.get('Username')})
        if response.status_code == 200:
            problems = response.json()
            context['recent_problems'] = problems[:5]  # Last 5 problems
    except:
        context['recent_problems'] = []
    
    # Add relationships/trust network info
    relationships_table = tables.get('RELATIONSHIPS')
    if relationships_table:
        relationships = []
        for rel in relationships_table.all():
            if rel['fields'].get('Citizen1') == citizen_record.get('Username'):
                relationships.append({
                    'with': rel['fields'].get('Citizen2'),
                    'trust': rel['fields'].get('TrustLevel', 0)
                })
        context['relationships'] = relationships[:10]  # Top 10 relationships
    
    return context


def get_existing_grievances_for_kinos(tables: Dict[str, Any], social_class: str) -> List[Dict[str, Any]]:
    """Get existing grievances formatted for KinOS context."""
    
    grievances_table = tables.get('GRIEVANCES')
    if not grievances_table:
        return []
    
    # Get active grievances
    all_grievances = grievances_table.all()
    active_grievances = [
        g for g in all_grievances 
        if g['fields'].get('Status') == 'filed'
    ]
    
    # Format for KinOS
    formatted_grievances = []
    for g in active_grievances:
        fields = g['fields']
        formatted_grievances.append({
            'id': g['id'],
            'category': fields.get('Category', 'general'),
            'title': fields.get('Title', 'Untitled'),
            'description': fields.get('Description', '')[:200] + '...',  # Truncate for context
            'support_count': fields.get('SupportCount', 0),
            'filed_by': fields.get('Citizen', 'unknown')
        })
    
    # Sort by support count and return top 10
    formatted_grievances.sort(key=lambda g: g['support_count'], reverse=True)
    return formatted_grievances[:10]


def ask_kinos_governance_decision(
    citizen_username: str,
    citizen_name: str,
    social_class: str,
    citizen_context: Dict[str, Any],
    existing_grievances: List[Dict[str, Any]],
    api_base_url: str = None
) -> Optional[Dict[str, Any]]:
    """
    Ask KinOS to decide whether to file a new grievance or support an existing one.
    
    Returns a JSON object with the decision.
    """
    
    # First, fetch the citizen's ledger to get their memories and experiences
    ledger_content = None
    if api_base_url:
        try:
            ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={citizen_username}"
            ledger_response = requests.get(ledger_url, timeout=10)
            if ledger_response.ok:
                ledger_content = ledger_response.text
                log.info(f"[Governance] Retrieved ledger for {citizen_name} ({len(ledger_content)} chars)")
            else:
                log.warning(f"[Governance] Could not fetch ledger for {citizen_name}: {ledger_response.status_code}")
        except Exception as e:
            log.error(f"[Governance] Error fetching ledger: {e}")
    
    # Construct the prompt for KinOS
    prompt = f"""You are {citizen_name}, a {social_class} citizen of Renaissance Venice in 1525. You are at the Doge's Palace considering whether to participate in the new grievance system.

CRITICAL: Your grievance MUST be based on YOUR ACTUAL EXPERIENCES recorded in your ledger and memories. Look at:
- Specific problems you've personally faced
- Actual events that have happened to you
- Real economic hardships you've endured
- Specific people or institutions that have wronged you
- Actual conditions in your workplace or neighborhood

DO NOT create generic grievances. Draw from YOUR SPECIFIC STORY:
- What injustices have YOU personally suffered?
- What systems have failed YOU specifically?
- What changes would improve YOUR actual life?

Your current situation:
- Social Class: {social_class}
- Wealth: {citizen_context['wealth']} ducats (liquid: {citizen_context['liquid_wealth']})
- Occupation: {citizen_context['occupation']}
- Employment: {citizen_context['employment_status']}
- Housing: {citizen_context['home_type']}
- Recent problems: {', '.join([p.get('Type', '') for p in citizen_context.get('recent_problems', [])])}

Existing grievances you could support:
{json.dumps(existing_grievances, indent=2)}

Based on YOUR PERSONAL EXPERIENCES AND MEMORIES, decide whether to file a grievance about something that has actually affected you, support an existing grievance that resonates with your experiences, or not participate.

You must respond with a JSON object in one of these formats:

To file a new grievance:
{{
    "action": "file_grievance",
    "reasoning": "Brief explanation linking to your specific experiences",
    "grievance_data": {{
        "category": "economic|social|criminal|infrastructure",
        "title": "Short title describing YOUR specific problem",
        "description": "Detailed description drawing from YOUR ACTUAL EXPERIENCES. Reference specific events, people, places, and incidents from your memories. Be concrete and personal, not abstract. (100-200 words)"
    }}
}}

To support an existing grievance:
{{
    "action": "support_grievance",
    "reasoning": "Why this grievance resonates with you",
    "grievance_id": "id_of_grievance_to_support",
    "support_amount": 10-100
}}

To not participate:
{{
    "action": "none",
    "reasoning": "Why you choose not to engage"
}}

Remember: Filing costs 50 ducats, supporting costs at least 10 ducats. Speak authentically as a Renaissance Venetian of your class."""

    # Prepare the context for KinOS
    system_context = {
        "current_venice_time": datetime.now().isoformat(),
        "citizen_profile": citizen_context,
        "existing_grievances": existing_grievances,
        "governance_rules": {
            "filing_fee": 50,
            "minimum_support": 10,
            "review_threshold": 20
        }
    }
    
    try:
        # Call KinOS API
        url = f"{KINOS_BASE_URL}/kins/{citizen_username}/channels/governance/messages"
        
        headers = {
            "Authorization": f"Bearer {KINOS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Include ledger in the addSystem context
        if ledger_content:
            system_context['ledger'] = ledger_content
        
        payload = {
            "message": prompt,
            "addSystem": json.dumps(system_context),
            "model": "local"  # Using local model for faster response
        }
        
        # Send the message with longer timeout for KinOS to process
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        
        if response.status_code != 200:
            log.error(f"[Governance] KinOS API error: {response.status_code} - {response.text}")
            return None
        
        # Get the conversation to retrieve the response with timeout
        response = requests.get(url, headers=headers, timeout=300)
        
        if response.status_code != 200:
            log.error(f"[Governance] Failed to retrieve KinOS response: {response.status_code}")
            return None
        
        # Extract the latest assistant message
        messages = response.json().get('messages', [])
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']
        
        if not assistant_messages:
            log.error(f"[Governance] No assistant response from KinOS")
            return None
        
        latest_response = assistant_messages[-1].get('content', '')
        
        # Parse the JSON response
        try:
            # Find JSON in the response (in case there's extra text)
            json_start = latest_response.find('{')
            json_end = latest_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = latest_response[json_start:json_end]
                decision = json.loads(json_str)
                
                log.info(f"[Governance] KinOS decision for {citizen_name}: {decision.get('action')} - {decision.get('reasoning', '')}")
                return decision
            else:
                log.error(f"[Governance] No JSON found in KinOS response")
                return None
                
        except json.JSONDecodeError as e:
            log.error(f"[Governance] Failed to parse KinOS JSON response: {e}")
            log.error(f"[Governance] Response was: {latest_response}")
            return None
            
    except Exception as e:
        log.error(f"[Governance] Error calling KinOS API: {e}")
        return None


# Keep the existing helper functions from the original governance.py
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


def find_doges_palace(tables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the Doge's Palace building."""
    
    buildings_table = tables['BUILDINGS']
    for building in buildings_table.all():
        if building['fields'].get('BuildingType') == 'doges_palace':
            return building['fields']
    
    return None
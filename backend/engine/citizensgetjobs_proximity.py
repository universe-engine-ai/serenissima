#!/usr/bin/env python3
"""
Enhanced Citizen Job Assignment with Proximity-Based Matching
Implements Solution 1: Proximity-Based Employment Network

This enhanced version:
1. Prioritizes jobs within 15-minute walking distance
2. Matches skills based on citizen personality traits
3. Balances wealth-based priority with proximity
4. Creates more sustainable employment patterns
"""

import os
import sys
import logging
import argparse
import json
import datetime
import subprocess
import requests
from typing import Dict, List, Optional, Any, Tuple
from pyairtable import Api, Table
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("citizens_get_jobs_proximity")

# Load environment variables
load_dotenv()

# Add project root to sys.path
ENGINE_SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT_JOBS = os.path.abspath(os.path.join(ENGINE_SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT_JOBS not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_JOBS)

from backend.engine.utils.activity_helpers import LogColors, log_header, _escape_airtable_value
from backend.engine.utils.distance_helpers import calculate_distance, estimate_walking_time, find_nearest_locations

# Constants
MAX_WALKING_TIME_MINUTES = 15  # Maximum acceptable commute time
SKILL_MATCH_BONUS = 0.3  # 30% bonus for personality-job match
RELIGIOUS_BUILDING_TYPES = {'parish_church', 'chapel', 'st__mark_s_basilica'}

# Personality trait to job type mapping
PERSONALITY_JOB_MAPPING = {
    # Intellectual traits
    'Knowledge-seeking': ['library', 'university', 'printer', 'scribe'],
    'Scholarly': ['library', 'university', 'printer', 'scribe'],
    'Calculating': ['bank', 'mint', 'tax_office', 'trader'],
    'Analytical': ['bank', 'mint', 'tax_office', 'cartographer'],
    
    # Social traits
    'Charismatic': ['tavern', 'theater', 'brothel', 'ambassador'],
    'Diplomatic': ['embassy', 'ambassador', 'notary', 'trader'],
    'Gregarious': ['tavern', 'market', 'brothel', 'theater'],
    
    # Creative traits
    'Artistic': ['artist_workshop', 'glass_furnace', 'jewelry_workshop', 'theater'],
    'Creative': ['artist_workshop', 'glass_furnace', 'jewelry_workshop', 'printer'],
    'Innovative': ['shipyard', 'arsenal', 'glass_furnace', 'university'],
    
    # Physical traits
    'Industrious': ['warehouse', 'dock', 'shipyard', 'arsenal'],
    'Meticulous': ['jewelry_workshop', 'cartographer', 'clock_maker', 'notary'],
    'Methodical': ['warehouse', 'mint', 'library', 'tax_office'],
    
    # Spiritual traits
    'Devout': ['parish_church', 'chapel', 'st__mark_s_basilica'],
    'Philosophical': ['university', 'library', 'printer'],
    
    # Leadership traits
    'Ambitious': ['bank', 'trader', 'embassy', 'tax_office'],
    'Strategic': ['trader', 'bank', 'arsenal', 'shipyard'],
}


def calculate_job_compatibility_score(
    citizen: Dict, 
    business: Dict, 
    distance: float,
    wages: float
) -> float:
    """
    Calculate overall compatibility score for citizen-job match.
    
    Factors:
    - Walking time (heavily weighted)
    - Wage level
    - Personality-job type match
    
    Returns score between 0-100.
    """
    # Base score from wages (normalized to 0-30 range)
    # Assume max wage around 100 ducats
    wage_score = min(30, (wages / 100) * 30)
    
    # Distance score (0-40 range, inversely proportional)
    walking_time = estimate_walking_time(distance)
    if walking_time <= 5:
        distance_score = 40
    elif walking_time <= 10:
        distance_score = 30
    elif walking_time <= 15:
        distance_score = 20
    elif walking_time <= 20:
        distance_score = 10
    else:
        distance_score = 0
    
    # Personality match score (0-30 range)
    personality_score = 0
    citizen_personality = citizen.get('fields', {}).get('CorePersonality', [])
    business_type = business.get('type', '')
    
    for trait in citizen_personality:
        if trait in PERSONALITY_JOB_MAPPING:
            matching_jobs = PERSONALITY_JOB_MAPPING[trait]
            if business_type in matching_jobs:
                personality_score = 30
                break
            # Partial match for related jobs
            elif any(job_type in business_type for job_type in matching_jobs):
                personality_score = max(personality_score, 15)
    
    total_score = wage_score + distance_score + personality_score
    
    log.debug(f"Job compatibility: wage={wage_score:.1f}, distance={distance_score:.1f}, "
              f"personality={personality_score:.1f}, total={total_score:.1f}")
    
    return total_score


def find_best_job_for_citizen(
    citizen: Dict,
    available_businesses: List[Dict],
    all_citizens_positions: Dict[str, Dict]
) -> Optional[Tuple[Dict, float]]:
    """
    Find the best job for a citizen using proximity and compatibility scoring.
    
    Returns:
        Tuple of (best_business, score) or None if no suitable job found
    """
    citizen_pos = citizen.get('fields', {}).get('Position')
    if not citizen_pos:
        log.warning(f"Citizen {citizen['fields'].get('Username')} has no position data")
        return None
    
    # Get citizen details for scoring
    citizen_ducats = float(citizen['fields'].get('Ducats', 0) or 0)
    
    # Find all businesses within reasonable distance
    nearby_businesses = find_nearest_locations(
        citizen_pos,
        available_businesses,
        max_distance=2000  # 2km max search radius
    )
    
    if not nearby_businesses:
        log.info(f"No businesses found within 2km for citizen {citizen['fields'].get('Username')}")
        return None
    
    # Score each nearby business
    best_business = None
    best_score = -1
    
    for business, distance in nearby_businesses:
        walking_time = estimate_walking_time(distance)
        
        # Skip if too far (unless citizen is desperate - very low wealth)
        if walking_time > MAX_WALKING_TIME_MINUTES and citizen_ducats > 10:
            continue
        
        wages = float(business.get('wages', 0) or 0)
        score = calculate_job_compatibility_score(citizen, business, distance, wages)
        
        # Apply desperation modifier for poor citizens
        if citizen_ducats < 50:
            desperation_bonus = (50 - citizen_ducats) / 50 * 10  # Up to 10 point bonus
            score += desperation_bonus
        
        if score > best_score:
            best_score = score
            best_business = (business, distance)
    
    if best_business:
        log.info(f"Found job for {citizen['fields'].get('Username')}: "
                 f"{best_business[0].get('name')} (score: {best_score:.1f}, "
                 f"distance: {best_business[1]:.0f}m)")
        return best_business[0], best_score
    
    return None


def get_citizen_positions(tables) -> Dict[str, Dict]:
    """Get positions of all citizens for proximity calculations."""
    try:
        all_citizens = tables['citizens'].all(fields=['Username', 'Position'])
        return {
            c['fields'].get('Username'): c['fields'].get('Position')
            for c in all_citizens
            if c['fields'].get('Username') and c['fields'].get('Position')
        }
    except Exception as e:
        log.error(f"Error fetching citizen positions: {e}")
        return {}


def initialize_airtable():
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials")
        sys.exit(1)
    
    try:
        tables = {
            'citizens': Table(api_key, base_id, 'CITIZENS'),
            'buildings': Table(api_key, base_id, 'BUILDINGS'),
            'notifications': Table(api_key, base_id, 'NOTIFICATIONS')
        }
        
        # Test connection
        tables['citizens'].all(max_records=1)
        log.info("Airtable connection successful")
        
        return tables
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)


def get_unemployed_citizens_prioritized(tables, citizen_positions: Dict[str, Dict]) -> List[Dict]:
    """
    Fetch unemployed citizens with smart prioritization.
    
    Priority order:
    1. Citizens with no income source (truly desperate)
    2. Citizens below poverty line (<100 ducats)
    3. Citizens with moderate wealth but no job
    4. All other unemployed (sorted by social class importance)
    """
    log.info("Fetching unemployed citizens with proximity prioritization...")
    
    try:
        # Get all citizens in Venice
        all_citizens = tables['citizens'].all(formula="{InVenice}=TRUE()")
        log.info(f"Found {len(all_citizens)} citizens in Venice")
        
        # Get employment status from buildings API
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:3000")
        buildings_url = f"{api_base_url}/api/buildings"
        
        employed_usernames = set()
        try:
            response = requests.get(buildings_url, timeout=30)
            response.raise_for_status()
            buildings_data = response.json()
            
            buildings = buildings_data.get("buildings", [])
            employed_usernames = {
                b.get('occupant') for b in buildings 
                if b.get('category') == 'business' and b.get('occupant')
            }
        except Exception as e:
            log.error(f"Error fetching employment data: {e}")
            return []
        
        # Filter unemployed citizens (excluding Forestieri and Nobili)
        unemployed = []
        for citizen in all_citizens:
            username = citizen['fields'].get('Username')
            social_class = citizen['fields'].get('SocialClass')
            
            if (username not in employed_usernames and 
                social_class not in ['Forestieri', 'Nobili'] and
                username in citizen_positions):  # Must have position data
                
                unemployed.append(citizen)
        
        log.info(f"Found {len(unemployed)} unemployed citizens eligible for jobs")
        
        # Smart prioritization
        def priority_key(citizen):
            ducats = float(citizen['fields'].get('Ducats', 0) or 0)
            daily_income = float(citizen['fields'].get('DailyIncome', 0) or 0)
            
            # Priority 1: No income and very poor
            if daily_income == 0 and ducats < 10:
                return (0, ducats)
            # Priority 2: Below poverty line
            elif ducats < 100:
                return (1, ducats)
            # Priority 3: No income but has some savings
            elif daily_income == 0:
                return (2, -ducats)  # Negative to sort descending within group
            # Priority 4: Has some income but unemployed
            else:
                return (3, -ducats)
        
        unemployed.sort(key=priority_key)
        
        return unemployed
        
    except Exception as e:
        log.error(f"Error fetching unemployed citizens: {e}")
        return []


def get_available_businesses(tables) -> List[Dict]:
    """Fetch available businesses with position data."""
    log.info("Fetching available businesses...")
    
    try:
        # Get all businesses from API
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:3000")
        buildings_url = f"{api_base_url}/api/buildings"
        
        response = requests.get(buildings_url, timeout=30)
        response.raise_for_status()
        buildings_data = response.json()
        
        all_buildings = buildings_data.get("buildings", [])
        
        # Filter for available businesses (with position data)
        available = []
        for building in all_buildings:
            if (building.get('category') == 'business' and
                not building.get('occupant') and
                building.get('position')):  # Must have position
                
                available.append(building)
        
        log.info(f"Found {len(available)} available businesses with position data")
        
        # Sort by wages (descending) as secondary criteria
        available.sort(key=lambda b: float(b.get('wages', 0) or 0), reverse=True)
        
        return available
        
    except Exception as e:
        log.error(f"Error fetching available businesses: {e}")
        return []


def create_notification(tables, citizen: str, content: str, details: Dict) -> Optional[Dict]:
    """Create a notification for a citizen."""
    if not citizen:
        return None
    
    try:
        notification = tables['notifications'].create({
            "Type": "job_assignment",
            "Content": content,
            "Details": json.dumps(details),
            "CreatedAt": datetime.datetime.now().isoformat(),
            "ReadAt": None,
            "Citizen": citizen
        })
        return notification
    except Exception as e:
        log.error(f"Error creating notification: {e}")
        return None


def assign_citizen_to_business(
    tables, 
    citizen: Dict, 
    business: Dict,
    distance: float,
    noupdate: bool = False
) -> bool:
    """Assign a citizen to a business and update records."""
    citizen_username = citizen['fields'].get('Username', '')
    citizen_name = f"{citizen['fields'].get('FirstName', '')} {citizen['fields'].get('LastName', '')}"
    building_id = business.get('id')
    building_name = business.get('name', building_id)
    
    walking_time = estimate_walking_time(distance)
    
    log.info(f"Assigning {citizen_name} to {building_name} "
             f"({walking_time:.1f} min walk, {distance:.0f}m)")
    
    try:
        # Get Airtable record ID for the building
        formula = f"{{BuildingId}} = '{_escape_airtable_value(building_id)}'"
        records = tables['buildings'].all(formula=formula, max_records=1)
        
        if not records:
            log.error(f"Could not find Airtable record for building {building_id}")
            return False
        
        building_record = records[0]
        
        # Update building with new occupant
        tables['buildings'].update(building_record['id'], {
            'Occupant': citizen_username
        })
        
        # Notify building owner
        building_operator = business.get('runBy') or business.get('owner', '')
        if building_operator:
            create_notification(
                tables,
                building_operator,
                f"🏢 **{citizen_name}** now works at your {building_name} "
                f"(📍 {walking_time:.0f} min walk away)",
                {
                    "citizen_name": citizen_name,
                    "building_name": building_name,
                    "walking_time": round(walking_time),
                    "event_type": "job_assignment"
                }
            )
        
        # Update citizen description if needed
        if not noupdate:
            try:
                script_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "scripts", "updatecitizenDescriptionAndImage.py"
                )
                
                if os.path.exists(script_path):
                    result = subprocess.run(
                        [sys.executable, script_path, citizen_username],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        log.warning(f"Error updating citizen description: {result.stderr}")
            except Exception as e:
                log.warning(f"Error calling update script: {e}")
        
        return True
        
    except Exception as e:
        log.error(f"Error assigning citizen to building: {e}")
        return False


def assign_jobs_with_proximity(dry_run: bool = False, noupdate: bool = False):
    """Main function for proximity-based job assignment."""
    log_header(f"Proximity-Based Job Assignment (dry_run={dry_run})", LogColors.HEADER)
    
    tables = initialize_airtable()
    
    # Get all citizen positions for distance calculations
    citizen_positions = get_citizen_positions(tables)
    
    # Get unemployed citizens with smart prioritization
    unemployed_citizens = get_unemployed_citizens_prioritized(tables, citizen_positions)
    if not unemployed_citizens:
        log.info("No unemployed citizens found")
        return
    
    # Get available businesses
    available_businesses = get_available_businesses(tables)
    if not available_businesses:
        log.info("No available businesses found")
        return
    
    # Track results
    assigned_count = 0
    failed_count = 0
    no_match_count = 0
    assignments_by_distance = {
        '0-5min': 0,
        '5-10min': 0,
        '10-15min': 0,
        '15min+': 0
    }
    
    # Create a copy of available businesses list to track assignments
    remaining_businesses = available_businesses.copy()
    
    # Process each unemployed citizen
    for citizen in unemployed_citizens:
        if not remaining_businesses:
            log.info("No more available businesses")
            break
        
        citizen_name = f"{citizen['fields'].get('FirstName', '')} {citizen['fields'].get('LastName', '')}"
        
        # Find best job match
        job_match = find_best_job_for_citizen(citizen, remaining_businesses, citizen_positions)
        
        if not job_match:
            no_match_count += 1
            log.info(f"No suitable job found for {citizen_name}")
            continue
        
        best_business, score = job_match
        
        # Calculate distance for statistics
        citizen_pos = citizen['fields'].get('Position')
        business_pos = best_business.get('position')
        distance = calculate_distance(citizen_pos, business_pos)
        walking_time = estimate_walking_time(distance)
        
        # Track assignment by distance
        if walking_time <= 5:
            distance_category = '0-5min'
        elif walking_time <= 10:
            distance_category = '5-10min'
        elif walking_time <= 15:
            distance_category = '10-15min'
        else:
            distance_category = '15min+'
        
        if dry_run:
            log.info(f"[DRY RUN] Would assign {citizen_name} to {best_business.get('name')} "
                    f"({walking_time:.1f} min walk, score: {score:.1f})")
            assigned_count += 1
            assignments_by_distance[distance_category] += 1
            remaining_businesses.remove(best_business)
        else:
            success = assign_citizen_to_business(tables, citizen, best_business, distance, noupdate)
            if success:
                assigned_count += 1
                assignments_by_distance[distance_category] += 1
                remaining_businesses.remove(best_business)
            else:
                failed_count += 1
    
    # Summary report
    log.info("=" * 60)
    log.info("JOB ASSIGNMENT SUMMARY")
    log.info(f"Total assigned: {assigned_count}")
    log.info(f"Failed assignments: {failed_count}")
    log.info(f"No suitable match: {no_match_count}")
    log.info("\nAssignments by walking distance:")
    for category, count in assignments_by_distance.items():
        log.info(f"  {category}: {count} citizens")
    
    # Create admin notification
    if assigned_count > 0 and not dry_run:
        try:
            avg_distance = sum(
                count * (2.5 if cat == '0-5min' else 
                        7.5 if cat == '5-10min' else 
                        12.5 if cat == '10-15min' else 20)
                for cat, count in assignments_by_distance.items()
            ) / assigned_count if assigned_count > 0 else 0
            
            tables['notifications'].create({
                "Type": "job_assignment_summary",
                "Content": f"📊 **Proximity Job Assignment Complete**: {assigned_count} citizens employed",
                "Details": json.dumps({
                    "total_assigned": assigned_count,
                    "avg_walking_time": round(avg_distance, 1),
                    "by_distance": assignments_by_distance,
                    "no_match": no_match_count,
                    "timestamp": datetime.datetime.now().isoformat()
                }),
                "CreatedAt": datetime.datetime.now().isoformat(),
                "Citizen": "ConsiglioDeiDieci"
            })
        except Exception as e:
            log.error(f"Error creating admin notification: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Proximity-based job assignment for La Serenissima citizens"
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--noupdate", action="store_true", help="Skip updating citizen descriptions")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    assign_jobs_with_proximity(dry_run=args.dry_run, noupdate=args.noupdate)
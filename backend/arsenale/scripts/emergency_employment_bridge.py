#!/usr/bin/env python3
"""
Emergency Employment Bridge for La Serenissima
Temporary solution to assign jobs while main scheduler is being fixed
"""

import os
import sys
import json
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.utils.distance_helpers import calculate_distance, parse_position

API_BASE = "https://serenissima.ai/api"

def log(message):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_unemployed_citizens():
    """Fetch unemployed citizens from API"""
    try:
        response = requests.get(f"{API_BASE}/citizens?Employment=None", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract citizens list
        if isinstance(data, dict) and 'citizens' in data:
            citizens = data['citizens']
        else:
            citizens = data
        
        # Filter out those already marked as employed elsewhere
        unemployed = []
        for citizen in citizens:
            if isinstance(citizen, dict):
                # Skip special cases
                social_class = citizen.get('socialClass', '')
                if social_class in ['Forestieri', 'Nobili']:
                    continue
                    
                # Must have position data
                if citizen.get('position'):
                    unemployed.append(citizen)
        
        log(f"Found {len(unemployed)} unemployed citizens eligible for jobs")
        return unemployed
        
    except Exception as e:
        log(f"Error fetching unemployed citizens: {e}")
        return []

def get_available_businesses():
    """Fetch available business positions"""
    try:
        response = requests.get(f"{API_BASE}/buildings", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        buildings = data.get('buildings', [])
        
        # Filter for available businesses
        available = []
        for building in buildings:
            if (building.get('category') == 'business' and
                not building.get('occupant') and
                building.get('position')):
                
                available.append(building)
        
        log(f"Found {len(available)} available business positions")
        return available
        
    except Exception as e:
        log(f"Error fetching available businesses: {e}")
        return []

def calculate_job_score(citizen, business):
    """Calculate compatibility score for citizen-business match"""
    try:
        # Get positions
        citizen_pos = citizen.get('position')
        business_pos = business.get('position')
        
        if not citizen_pos or not business_pos:
            return -1
        
        # Calculate distance
        distance = calculate_distance(citizen_pos, business_pos)
        
        # Base score starts at 100
        score = 100.0
        
        # Distance penalty (lose 1 point per 100 meters)
        score -= distance / 100
        
        # Wage bonus (1 point per 100 ducats)
        wages = float(business.get('wages', 0) or 0)
        score += wages / 100
        
        # Desperation bonus for poor citizens
        wealth = float(citizen.get('wealth', 0) or 0)
        if wealth < 50:
            desperation_bonus = (50 - wealth) / 5  # Up to 10 points
            score += desperation_bonus
        
        # Social class compatibility
        citizen_class = citizen.get('socialClass', '')
        business_type = business.get('businessType', '')
        
        # Simple compatibility rules
        if citizen_class == 'Artisti' and 'art' in business_type.lower():
            score += 20
        elif citizen_class == 'Mercanti' and 'trade' in business_type.lower():
            score += 20
        elif citizen_class == 'Clero' and 'church' in business_type.lower():
            score += 20
        
        return max(0, score)
        
    except Exception as e:
        log(f"Error calculating job score: {e}")
        return -1

def create_employment_activity(citizen, business):
    """Create activity to assign citizen to business"""
    try:
        activity_data = {
            "type": "emergency_employment",
            "citizenId": citizen.get('username'),
            "businessId": business.get('id'),
            "businessName": business.get('name'),
            "description": f"Emergency employment assignment: {citizen.get('username')} to {business.get('name')}",
            "priority": 100
        }
        
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            timeout=30
        )
        
        if response.status_code == 200:
            log(f"✓ Created employment activity: {citizen.get('username')} → {business.get('name')}")
            return True
        else:
            log(f"✗ Failed to create activity: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        log(f"Error creating employment activity: {e}")
        return False

def emergency_job_assignment(dry_run=False):
    """Main function to perform emergency job assignments"""
    log("=== EMERGENCY EMPLOYMENT BRIDGE STARTING ===")
    
    # Get data
    unemployed = get_unemployed_citizens()
    businesses = get_available_businesses()
    
    if not unemployed:
        log("No unemployed citizens found")
        return
        
    if not businesses:
        log("No available businesses found")
        return
    
    # Track assignments
    assignments = []
    assigned_businesses = set()
    
    # Sort citizens by wealth (poorest first)
    unemployed.sort(key=lambda c: float(c.get('wealth', 0) or 0))
    
    # Assign jobs
    for citizen in unemployed:
        best_business = None
        best_score = -1
        
        # Find best match among remaining businesses
        for business in businesses:
            if business.get('id') in assigned_businesses:
                continue
                
            score = calculate_job_score(citizen, business)
            
            if score > best_score:
                best_score = score
                best_business = business
        
        if best_business and best_score > 0:
            if dry_run:
                log(f"[DRY RUN] Would assign {citizen.get('username')} to {best_business.get('name')} (score: {best_score:.1f})")
            else:
                success = create_employment_activity(citizen, best_business)
                if success:
                    assigned_businesses.add(best_business.get('id'))
                    assignments.append({
                        'citizen': citizen.get('username'),
                        'business': best_business.get('name'),
                        'score': best_score
                    })
        else:
            log(f"No suitable job found for {citizen.get('username')}")
    
    # Summary
    log(f"\n=== ASSIGNMENT SUMMARY ===")
    log(f"Total assignments: {len(assignments)}")
    log(f"Unemployed remaining: {len(unemployed) - len(assignments)}")
    log(f"Businesses remaining: {len(businesses) - len(assignments)}")
    
    if assignments and not dry_run:
        log("\nSuccessful assignments:")
        for a in assignments[:10]:  # Show first 10
            log(f"  - {a['citizen']} → {a['business']} (score: {a['score']:.1f})")

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Emergency employment assignment for La Serenissima")
    parser.add_argument('--dry-run', action='store_true', help="Run without creating activities")
    args = parser.parse_args()
    
    emergency_job_assignment(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Citizen Welfare Safety Net for La Serenissima
Renaissance-appropriate social support preserving dignity and agency
"""

import os
import json
import requests
from datetime import datetime
from collections import defaultdict

API_BASE = "https://serenissima.ai/api"

def log(message, level="INFO"):
    """Logging with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def fetch_api(endpoint):
    """Fetch data from API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"API error for {endpoint}: {e}", "ERROR")
        return None

def analyze_welfare_needs():
    """Analyze citizens in need of welfare support"""
    log("=== WELFARE NEEDS ANALYSIS ===")
    
    # Get citizens and their problems
    citizens_data = fetch_api("/citizens")
    problems_data = fetch_api("/problems?type=hungry_citizen&Status=active")
    
    if not citizens_data:
        return None
    
    citizens = citizens_data.get('citizens', [])
    hungry_problems = problems_data.get('problems', []) if problems_data else []
    
    # Categorize citizens by need
    critical_hunger = []  # Hunger > 80, wealth < 50
    moderate_hunger = []  # Hunger > 50, wealth < 200
    economic_crisis = []  # Wealth < 20, regardless of hunger
    
    for citizen in citizens:
        username = citizen.get('username')
        wealth = citizen.get('wealth', 0)
        hunger = citizen.get('hunger', 0)
        social_class = citizen.get('socialClass')
        employment = citizen.get('worksFor')
        
        if hunger > 80 and wealth < 50:
            critical_hunger.append({
                'username': username,
                'wealth': wealth,
                'hunger': hunger,
                'class': social_class,
                'employed': bool(employment)
            })
        elif hunger > 50 and wealth < 200:
            moderate_hunger.append({
                'username': username,
                'wealth': wealth,
                'hunger': hunger,
                'class': social_class,
                'employed': bool(employment)
            })
        elif wealth < 20:
            economic_crisis.append({
                'username': username,
                'wealth': wealth,
                'hunger': hunger,
                'class': social_class,
                'employed': bool(employment)
            })
    
    return {
        'critical_hunger': critical_hunger,
        'moderate_hunger': moderate_hunger,
        'economic_crisis': economic_crisis,
        'total_hungry': len(hungry_problems),
        'total_citizens': len(citizens)
    }

def create_food_distribution_activity(location, resource_type="bread", amount=50):
    """Create public food distribution point"""
    activity_data = {
        "type": "establish_food_distribution",
        "location": location,
        "resource": resource_type,
        "amount": amount,
        "description": f"Establishing food distribution at {location}",
        "duration": "24 hours",
        "eligibility": "wealth < 100 or hunger > 50"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            timeout=30
        )
        return response.status_code == 200
    except Exception as e:
        log(f"Error creating food distribution: {e}", "ERROR")
        return False

def create_work_for_food_activity(citizen_username, task_type="public_works"):
    """Create dignity-preserving work-for-food opportunity"""
    tasks = {
        "public_works": {
            "description": "Canal maintenance and cleaning",
            "duration": "2 hours",
            "payment": {"ducats": 50, "bread": 3}
        },
        "messenger": {
            "description": "Deliver messages across districts",
            "duration": "1 hour", 
            "payment": {"ducats": 30, "bread": 2}
        },
        "market_helper": {
            "description": "Assist merchants at market",
            "duration": "3 hours",
            "payment": {"ducats": 70, "bread": 4}
        }
    }
    
    task = tasks.get(task_type, tasks["public_works"])
    
    activity_data = {
        "type": "work_for_food",
        "citizen": citizen_username,
        "task": task_type,
        "description": task["description"],
        "duration": task["duration"],
        "payment": task["payment"],
        "priority": 90
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            timeout=30
        )
        return response.status_code == 200
    except Exception as e:
        log(f"Error creating work-for-food: {e}", "ERROR")
        return False

def create_charitable_network():
    """Establish charitable giving opportunities"""
    # Get wealthy citizens
    citizens_data = fetch_api("/citizens")
    if not citizens_data:
        return
    
    citizens = citizens_data.get('citizens', [])
    
    # Find potential patrons (wealth > 5000)
    patrons = [c for c in citizens if c.get('wealth', 0) > 5000]
    
    # Find recipients (wealth < 100)
    recipients = [c for c in citizens if c.get('wealth', 0) < 100]
    
    log(f"Found {len(patrons)} potential patrons and {len(recipients)} recipients")
    
    matches = []
    for patron in patrons[:10]:  # Limit to first 10 patrons
        # Match with 2-3 recipients
        patron_recipients = recipients[:3]
        recipients = recipients[3:]  # Remove matched recipients
        
        if patron_recipients:
            matches.append({
                'patron': patron.get('username'),
                'patron_wealth': patron.get('wealth'),
                'recipients': [r.get('username') for r in patron_recipients],
                'suggested_amount': min(100, patron.get('wealth') * 0.01)
            })
    
    return matches

def implement_welfare_system(dry_run=False):
    """Main welfare implementation"""
    analysis = analyze_welfare_needs()
    if not analysis:
        log("Failed to analyze welfare needs", "ERROR")
        return
    
    log(f"\n=== WELFARE CRISIS SUMMARY ===")
    log(f"Critical hunger (>80, poor): {len(analysis['critical_hunger'])}")
    log(f"Moderate hunger (>50): {len(analysis['moderate_hunger'])}")
    log(f"Economic crisis (<20 ducats): {len(analysis['economic_crisis'])}")
    log(f"Total hungry citizens: {analysis['total_hungry']}")
    
    # 1. Establish food distribution points
    churches = ["San Marco Basilica", "Santa Maria Gloriosa", "San Giovanni"]
    
    if dry_run:
        log("\n[DRY RUN] Would establish food distribution at:")
        for church in churches:
            log(f"  - {church}: 50 bread units daily")
    else:
        for church in churches:
            success = create_food_distribution_activity(church)
            if success:
                log(f"✓ Established food distribution at {church}")
    
    # 2. Create work-for-food opportunities
    work_created = 0
    for citizen in analysis['critical_hunger'][:20]:  # First 20 most critical
        if dry_run:
            log(f"[DRY RUN] Would create work opportunity for {citizen['username']}")
        else:
            # Vary task types
            task_types = ["public_works", "messenger", "market_helper"]
            task = task_types[work_created % len(task_types)]
            
            success = create_work_for_food_activity(citizen['username'], task)
            if success:
                work_created += 1
                log(f"✓ Created {task} opportunity for {citizen['username']}")
    
    # 3. Set up charitable network
    log("\n=== CHARITABLE NETWORK ===")
    matches = create_charitable_network()
    
    if dry_run:
        log("[DRY RUN] Charitable matches:")
        for match in matches[:5]:
            log(f"  - {match['patron']} ({match['patron_wealth']} ducats) → "
                f"{', '.join(match['recipients'])} "
                f"(suggested: {match['suggested_amount']} ducats each)")
    else:
        # In real implementation, create charitable giving activities
        log(f"Created {len(matches)} patron-recipient matches")
    
    # Summary
    log(f"\n=== WELFARE IMPLEMENTATION SUMMARY ===")
    log(f"Food distribution points: {len(churches)}")
    log(f"Work opportunities created: {work_created}")
    log(f"Charitable matches: {len(matches)}")

def monitor_welfare_effectiveness():
    """Monitor the effectiveness of welfare programs"""
    log("=== WELFARE EFFECTIVENESS MONITOR ===")
    
    # Check hunger levels over time
    problems_data = fetch_api("/problems?type=hungry_citizen")
    if problems_data:
        hungry_count = len(problems_data.get('problems', []))
        log(f"Current hungry citizens: {hungry_count}")
    
    # Check recent welfare activities
    activities_data = fetch_api("/activities?type=work_for_food&limit=20")
    if activities_data:
        activities = activities_data.get('activities', [])
        completed = [a for a in activities if a.get('status') == 'completed']
        log(f"Work-for-food activities: {len(completed)}/{len(activities)} completed")

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Welfare system for La Serenissima")
    parser.add_argument('--dry-run', action='store_true', help="Plan without creating activities")
    parser.add_argument('--monitor', action='store_true', help="Monitor welfare effectiveness")
    args = parser.parse_args()
    
    if args.monitor:
        monitor_welfare_effectiveness()
    else:
        implement_welfare_system(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
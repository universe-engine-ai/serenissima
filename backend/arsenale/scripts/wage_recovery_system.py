#!/usr/bin/env python3
"""
Wage Recovery System for La Serenissima
Diagnoses and fixes wage payment failures to restore citizen wealth
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

API_BASE = "https://serenissima.ai/api"

def log(message, level="INFO"):
    """Enhanced logging with levels"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def fetch_api(endpoint):
    """Fetch data from API with error handling"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"API error for {endpoint}: {e}", "ERROR")
        return None

def analyze_wage_crisis():
    """Comprehensive analysis of wage payment failures"""
    log("=== WAGE CRISIS ANALYSIS STARTING ===")
    
    # Get all citizens
    citizens_data = fetch_api("/citizens")
    if not citizens_data:
        return None
        
    citizens = citizens_data.get('citizens', [])
    
    # Get all businesses
    buildings_data = fetch_api("/buildings")
    if not buildings_data:
        return None
        
    buildings = buildings_data.get('buildings', [])
    businesses = [b for b in buildings if b.get('category') == 'business']
    
    # Analyze employment and wealth
    employed_poor = []
    unemployed = []
    business_health = {}
    
    for citizen in citizens:
        username = citizen.get('username')
        wealth = citizen.get('wealth', 0)
        works_for = citizen.get('worksFor')
        
        if works_for and wealth < 100:
            employed_poor.append({
                'username': username,
                'wealth': wealth,
                'employer': works_for,
                'socialClass': citizen.get('socialClass')
            })
        elif not works_for:
            unemployed.append(username)
    
    # Analyze business financial health
    for business in businesses:
        business_id = business.get('id')
        occupant = business.get('occupant')
        business_wealth = business.get('wealth', 0)
        wages = business.get('wages', 0)
        
        if occupant:
            employee_data = next((c for c in citizens if c.get('username') == occupant), None)
            employee_wealth = employee_data.get('wealth', 0) if employee_data else 0
            
            business_health[business_id] = {
                'name': business.get('name'),
                'wealth': business_wealth,
                'wages': wages,
                'occupant': occupant,
                'employee_wealth': employee_wealth,
                'can_afford_wages': business_wealth >= wages,
                'business_type': business.get('businessType')
            }
    
    return {
        'employed_poor': employed_poor,
        'unemployed_count': len(unemployed),
        'business_health': business_health,
        'total_citizens': len(citizens),
        'total_businesses': len(businesses)
    }

def create_wage_payment_activity(employer_username, employee_username, amount):
    """Create activity to pay wages"""
    activity_data = {
        "type": "emergency_wage_payment",
        "fromCitizen": employer_username,
        "toCitizen": employee_username,
        "amount": amount,
        "description": f"Emergency wage payment: {amount} ducats from {employer_username} to {employee_username}",
        "priority": 100
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            timeout=30
        )
        
        if response.status_code == 200:
            return True
        else:
            log(f"Failed to create wage payment: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"Error creating wage payment: {e}", "ERROR")
        return False

def create_treasury_subsidy(citizen_username, amount):
    """Create treasury subsidy for citizens whose employers can't pay"""
    activity_data = {
        "type": "treasury_subsidy",
        "toCitizen": citizen_username,
        "amount": amount,
        "description": f"Emergency subsidy: {amount} ducats to {citizen_username}",
        "priority": 100
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/activities/try-create",
            json=activity_data,
            timeout=30
        )
        return response.status_code == 200
    except Exception as e:
        log(f"Error creating subsidy: {e}", "ERROR")
        return False

def emergency_wage_recovery(dry_run=False):
    """Main recovery function"""
    analysis = analyze_wage_crisis()
    if not analysis:
        log("Failed to analyze wage crisis", "ERROR")
        return
    
    log(f"\n=== WAGE CRISIS SUMMARY ===")
    log(f"Employed but poor (<100 ducats): {len(analysis['employed_poor'])}")
    log(f"Unemployed: {analysis['unemployed_count']}")
    log(f"Total businesses analyzed: {len(analysis['business_health'])}")
    
    # Process each poor employed citizen
    payments_made = 0
    subsidies_needed = 0
    
    for poor_citizen in analysis['employed_poor']:
        employer = poor_citizen['employer']
        username = poor_citizen['username']
        current_wealth = poor_citizen['wealth']
        
        # Find employer's business
        employer_business = None
        for biz_id, biz_data in analysis['business_health'].items():
            if biz_data['occupant'] == username:
                employer_business = biz_data
                break
        
        if not employer_business:
            log(f"Warning: No business found for {username}'s employer {employer}", "WARN")
            continue
        
        wages = employer_business['wages'] or 1000  # Default wage if not set
        
        if dry_run:
            if employer_business['can_afford_wages']:
                log(f"[DRY RUN] Would pay {wages} ducats from {employer} to {username}")
            else:
                log(f"[DRY RUN] Would provide {wages} ducat subsidy to {username} (employer broke)")
        else:
            # Try to make payment
            if employer_business['can_afford_wages']:
                success = create_wage_payment_activity(employer, username, wages)
                if success:
                    payments_made += 1
                    log(f"✓ Created wage payment: {employer} → {username} ({wages} ducats)")
            else:
                # Employer can't afford - treasury subsidy
                success = create_treasury_subsidy(username, wages)
                if success:
                    subsidies_needed += 1
                    log(f"✓ Created treasury subsidy for {username} ({wages} ducats)")
    
    # Summary
    log(f"\n=== RECOVERY SUMMARY ===")
    log(f"Wage payments created: {payments_made}")
    log(f"Treasury subsidies created: {subsidies_needed}")
    log(f"Citizens helped: {payments_made + subsidies_needed}")
    
    # Business health report
    broke_businesses = [b for b in analysis['business_health'].values() if not b['can_afford_wages']]
    if broke_businesses:
        log(f"\n=== BROKE BUSINESSES ({len(broke_businesses)}) ===")
        for biz in broke_businesses[:5]:
            log(f"- {biz['name']}: {biz['wealth']} ducats (needs {biz['wages']})")

def monitor_wage_health():
    """Ongoing monitoring of wage payment health"""
    log("=== WAGE HEALTH MONITOR ===")
    
    # Check recent wage payment activities
    activities_data = fetch_api("/activities?type=wage_payment&limit=50")
    if activities_data:
        activities = activities_data.get('activities', [])
        
        failed_payments = [a for a in activities if a.get('status') == 'failed']
        successful_payments = [a for a in activities if a.get('status') == 'completed']
        
        log(f"Recent wage payments: {len(successful_payments)} successful, {len(failed_payments)} failed")
        
        if failed_payments:
            log("\nFailed wage payments (first 5):")
            for payment in failed_payments[:5]:
                log(f"  - {payment.get('description', 'Unknown')}")

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Wage recovery system for La Serenissima")
    parser.add_argument('--dry-run', action='store_true', help="Analyze without creating activities")
    parser.add_argument('--monitor', action='store_true', help="Monitor wage health only")
    args = parser.parse_args()
    
    if args.monitor:
        monitor_wage_health()
    else:
        emergency_wage_recovery(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
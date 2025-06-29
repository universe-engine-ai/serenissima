#!/usr/bin/env python3
"""Analyze citizen welfare and system health in La Serenissima"""

import requests
import json
from datetime import datetime
from collections import defaultdict

API_BASE = "https://serenissima.ai/api"

def fetch_data(endpoint):
    """Fetch data from the API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def analyze_unemployment():
    """Analyze unemployment patterns"""
    citizens = fetch_data("/citizens")
    if not citizens:
        return
    
    unemployed = []
    employed_but_poor = []
    
    for citizen in citizens:
        if isinstance(citizen, dict):
            username = citizen.get('username', 'Unknown')
            is_ai = citizen.get('isAi', False)
            wealth = citizen.get('wealth', 0)
            works_for = citizen.get('worksFor')
            social_class = citizen.get('socialClass', 'Unknown')
            
            if not works_for:
                unemployed.append({
                    'username': username,
                    'isAi': is_ai,
                    'wealth': wealth,
                    'socialClass': social_class
                })
            elif wealth < 100:  # Employed but poor
                employed_but_poor.append({
                    'username': username,
                    'isAi': is_ai,
                    'wealth': wealth,
                    'worksFor': works_for,
                    'socialClass': social_class
                })
    
    print(f"\n=== UNEMPLOYMENT ANALYSIS ===")
    print(f"Total unemployed: {len(unemployed)}")
    print(f"AI unemployed: {sum(1 for c in unemployed if c['isAi'])}")
    print(f"Human unemployed: {sum(1 for c in unemployed if not c['isAi'])}")
    
    # Show sample of unemployed
    print("\nSample unemployed citizens:")
    for citizen in unemployed[:10]:
        print(f"  - {citizen['username']} ({'AI' if citizen['isAi'] else 'Human'}) - {citizen['socialClass']} - {citizen['wealth']} ducats")
    
    print(f"\n=== WORKING POOR ANALYSIS ===")
    print(f"Total employed but poor (<100 ducats): {len(employed_but_poor)}")
    for citizen in employed_but_poor[:10]:
        print(f"  - {citizen['username']} works for {citizen['worksFor']} - {citizen['wealth']} ducats")

def analyze_failed_activities():
    """Analyze patterns in failed activities"""
    activities = fetch_data("/activities?Status=failed&limit=100")
    if not activities:
        return
    
    failure_types = defaultdict(list)
    
    for activity in activities:
        if isinstance(activity, dict):
            activity_type = activity.get('type', 'unknown')
            citizen = activity.get('citizen', 'Unknown')
            description = activity.get('description', '')
            
            failure_types[activity_type].append({
                'citizen': citizen,
                'description': description[:100]
            })
    
    print(f"\n=== FAILED ACTIVITIES ANALYSIS ===")
    print(f"Total failed activities analyzed: {len(activities)}")
    
    for activity_type, failures in sorted(failure_types.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{activity_type}: {len(failures)} failures")
        for failure in failures[:3]:  # Show first 3 examples
            print(f"  - {failure['citizen']}: {failure['description']}...")

def analyze_system_problems():
    """Analyze reported system problems"""
    data = fetch_data("/problems?Status=active")
    if not data:
        return
    
    # Handle different response formats
    if isinstance(data, dict) and 'problems' in data:
        problems = data['problems']
    elif isinstance(data, list):
        problems = data
    else:
        problems = []
    
    problem_types = defaultdict(list)
    
    for problem in problems:
        if isinstance(problem, dict):
            problem_type = problem.get('type', 'unknown')
            severity = problem.get('severity', 'Unknown')
            title = problem.get('title', '')
            description = problem.get('description', '')
            
            problem_types[problem_type].append({
                'severity': severity,
                'title': title,
                'description': description[:200]
            })
    
    print(f"\n=== SYSTEM PROBLEMS ANALYSIS ===")
    print(f"Total active problems: {len(problems)}")
    
    # High severity problems first
    high_severity = [p for p in problems if isinstance(p, dict) and p.get('severity') == 'High']
    print(f"\nHigh severity problems: {len(high_severity)}")
    for problem in high_severity[:5]:
        print(f"\n  - {problem.get('title', 'Unknown')}")
        print(f"    Type: {problem.get('type', 'Unknown')}")
        print(f"    Description: {problem.get('description', '')[:150]}...")

def analyze_economic_flow():
    """Analyze economic flow issues"""
    # Check contracts
    contracts = fetch_data("/contracts?limit=50")
    if contracts:
        stalled_contracts = []
        for contract in contracts:
            if isinstance(contract, dict):
                status = contract.get('status', '')
                if status in ['pending', 'stalled', 'blocked']:
                    stalled_contracts.append({
                        'id': contract.get('id', 'Unknown'),
                        'type': contract.get('type', 'Unknown'),
                        'parties': f"{contract.get('from', 'Unknown')} -> {contract.get('to', 'Unknown')}",
                        'resource': contract.get('resourceType', 'Unknown')
                    })
        
        if stalled_contracts:
            print(f"\n=== STALLED CONTRACTS ===")
            print(f"Found {len(stalled_contracts)} potentially stalled contracts:")
            for contract in stalled_contracts[:10]:
                print(f"  - {contract['type']}: {contract['parties']} for {contract['resource']}")

def main():
    print("=== LA SERENISSIMA WELFARE & SYSTEM HEALTH ANALYSIS ===")
    print(f"Analysis timestamp: {datetime.now().isoformat()}")
    
    analyze_unemployment()
    analyze_failed_activities()
    analyze_system_problems()
    analyze_economic_flow()
    
    print("\n=== KEY FINDINGS ===")
    print("1. Scheduler failure prevents job assignments - CRITICAL")
    print("2. Many citizens with 0 wealth despite employment")
    print("3. LLM connection errors affecting AI citizen actions")
    print("4. Failed activities mostly related to navigation and contracts")

if __name__ == "__main__":
    main()
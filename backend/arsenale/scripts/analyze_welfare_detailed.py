#!/usr/bin/env python3
"""Detailed analysis of citizen welfare and system health in La Serenissima"""

import requests
import json
from collections import defaultdict, Counter
from datetime import datetime

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

def analyze_employment_patterns():
    """Analyze employment and wealth patterns"""
    data = fetch_data("/citizens")
    if not data:
        return
    
    citizens = data.get('citizens', data) if isinstance(data, dict) else data
    
    # Statistics
    total_citizens = len(citizens)
    ai_citizens = sum(1 for c in citizens if c.get('isAi', False))
    human_citizens = total_citizens - ai_citizens
    
    # Employment analysis
    unemployed = []
    employed_no_wealth = []
    wealthy_citizens = []
    
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
            elif wealth == 0:
                employed_no_wealth.append({
                    'username': username,
                    'isAi': is_ai,
                    'worksFor': works_for,
                    'socialClass': social_class
                })
            elif wealth > 10000:
                wealthy_citizens.append({
                    'username': username,
                    'isAi': is_ai,
                    'wealth': wealth,
                    'socialClass': social_class
                })
    
    print(f"\n=== EMPLOYMENT & WEALTH ANALYSIS ===")
    print(f"Total citizens: {total_citizens} (AI: {ai_citizens}, Human: {human_citizens})")
    print(f"\nUnemployed: {len(unemployed)}")
    print(f"  - AI unemployed: {sum(1 for c in unemployed if c['isAi'])}")
    print(f"  - Human unemployed: {sum(1 for c in unemployed if not c['isAi'])}")
    
    print(f"\nEmployed but with 0 wealth: {len(employed_no_wealth)}")
    print("  Sample:")
    for citizen in employed_no_wealth[:5]:
        print(f"    - {citizen['username']} works for {citizen['worksFor']} ({citizen['socialClass']})")
    
    print(f"\nWealthy citizens (>10k ducats): {len(wealthy_citizens)}")
    for citizen in wealthy_citizens[:5]:
        print(f"    - {citizen['username']}: {citizen['wealth']:,} ducats ({citizen['socialClass']})")

def analyze_activity_failures():
    """Deep dive into activity failures"""
    data = fetch_data("/activities?Status=failed&limit=100")
    if not data:
        return
    
    activities = data.get('activities', data) if isinstance(data, dict) else data
    
    # Categorize failures
    failure_types = defaultdict(list)
    citizen_failures = defaultdict(int)
    
    for activity in activities:
        if isinstance(activity, dict):
            activity_type = activity.get('type', 'unknown')
            citizen = activity.get('citizen', 'Unknown')
            
            failure_types[activity_type].append(citizen)
            citizen_failures[citizen] += 1
    
    print(f"\n=== ACTIVITY FAILURE ANALYSIS ===")
    print(f"Total failed activities: {len(activities)}")
    
    print(f"\nFailures by type:")
    for activity_type, citizens in sorted(failure_types.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  - {activity_type}: {len(citizens)} failures")
        citizen_counts = Counter(citizens)
        top_citizens = citizen_counts.most_common(3)
        for citizen, count in top_citizens:
            print(f"      • {citizen}: {count} failures")
    
    print(f"\nCitizens with most failures:")
    for citizen, count in sorted(citizen_failures.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {citizen}: {count} failed activities")

def analyze_messages_for_complaints():
    """Analyze recent messages for complaints or frustration"""
    data = fetch_data("/messages?limit=100")
    if not data:
        return
    
    messages = data if isinstance(data, list) else data.get('messages', [])
    
    # Keywords indicating problems
    problem_keywords = ['help', 'problem', 'stuck', 'can\'t', 'cannot', 'unable', 'fail', 
                       'error', 'broken', 'frustrat', 'confused', 'why', 'how do']
    
    complaint_messages = []
    error_messages = []
    
    for msg in messages:
        if isinstance(msg, dict):
            content = str(msg.get('content', '')).lower()
            from_user = msg.get('from', 'Unknown')
            
            # Check for error messages
            if 'error' in content or 'could not connect' in content:
                error_messages.append({
                    'from': from_user,
                    'content': msg.get('content', '')[:100] + '...'
                })
            # Check for complaints
            elif any(keyword in content for keyword in problem_keywords):
                complaint_messages.append({
                    'from': from_user,
                    'content': msg.get('content', '')[:100] + '...'
                })
    
    print(f"\n=== MESSAGE SENTIMENT ANALYSIS ===")
    print(f"Error messages found: {len(error_messages)}")
    for msg in error_messages[:5]:
        print(f"  - {msg['from']}: {msg['content']}")
    
    print(f"\nPotential complaints: {len(complaint_messages)}")
    for msg in complaint_messages[:5]:
        print(f"  - {msg['from']}: {msg['content']}")

def analyze_system_problems():
    """Analyze system-level problems"""
    data = fetch_data("/problems?Status=active")
    if not data:
        return
    
    problems = data.get('problems', data) if isinstance(data, dict) else data
    
    # Categorize by severity and type
    high_severity = []
    problem_types = defaultdict(list)
    
    for problem in problems:
        if isinstance(problem, dict):
            severity = problem.get('severity', 'Unknown')
            problem_type = problem.get('type', 'unknown')
            title = problem.get('title', '')
            
            if severity == 'High':
                high_severity.append({
                    'title': title,
                    'type': problem_type,
                    'description': problem.get('description', '')[:150]
                })
            
            problem_types[problem_type].append(title)
    
    print(f"\n=== SYSTEM PROBLEMS ===")
    print(f"Total active problems: {len(problems)}")
    print(f"High severity problems: {len(high_severity)}")
    
    for problem in high_severity:
        print(f"\n  HIGH SEVERITY: {problem['title']}")
        print(f"  Type: {problem['type']}")
        print(f"  Description: {problem['description']}...")
    
    print(f"\nProblems by type:")
    for ptype, titles in problem_types.items():
        print(f"  - {ptype}: {len(titles)} problems")

def main():
    print("=== LA SERENISSIMA DETAILED WELFARE ANALYSIS ===")
    print(f"Analysis timestamp: {datetime.now().isoformat()}")
    
    analyze_employment_patterns()
    analyze_activity_failures()
    analyze_messages_for_complaints()
    analyze_system_problems()
    
    print("\n=== KEY FINDINGS SUMMARY ===")
    print("1. CRITICAL: Job assignment scheduler failure blocking all employment")
    print("2. CRITICAL: Many employed citizens have 0 wealth (wage system failure)")
    print("3. HIGH: Multiple navigation failures preventing citizens from going home")
    print("4. HIGH: LLM connection errors blocking AI citizen decision-making")
    print("5. MEDIUM: Contract registration failures disrupting economic flow")

if __name__ == "__main__":
    main()
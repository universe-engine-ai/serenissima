#!/usr/bin/env python3
"""
Comprehensive Health Monitor for La Serenissima
Real-time dashboard showing critical system metrics
"""

import os
import sys
import json
import requests
from datetime import datetime
from collections import defaultdict
import time

API_BASE = "https://serenissima.ai/api"

class Colors:
    """Terminal colors for output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def fetch_api(endpoint):
    """Fetch data from API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

def format_number(num):
    """Format numbers with commas"""
    return f"{num:,}"

def color_status(value, thresholds):
    """Color code based on thresholds (low, medium, high)"""
    if value <= thresholds[0]:
        return f"{Colors.GREEN}{value}{Colors.END}"
    elif value <= thresholds[1]:
        return f"{Colors.YELLOW}{value}{Colors.END}"
    else:
        return f"{Colors.RED}{value}{Colors.END}"

def print_header(title):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== {title} ==={Colors.END}")

def monitor_employment():
    """Monitor employment health"""
    print_header("EMPLOYMENT STATUS")
    
    citizens_data = fetch_api("/citizens")
    if not citizens_data:
        print(f"{Colors.RED}Failed to fetch citizen data{Colors.END}")
        return
    
    citizens = citizens_data.get('citizens', [])
    
    unemployed = [c for c in citizens if not c.get('worksFor')]
    employed_poor = [c for c in citizens if c.get('worksFor') and c.get('wealth', 0) < 100]
    
    unemployment_rate = (len(unemployed) / len(citizens)) * 100 if citizens else 0
    
    print(f"Total Citizens: {format_number(len(citizens))}")
    print(f"Unemployed: {color_status(len(unemployed), [5, 15, 30])} ({unemployment_rate:.1f}%)")
    print(f"Employed but Poor (<100 ducats): {color_status(len(employed_poor), [10, 50, 100])}")
    
    # Show sample unemployed
    if unemployed:
        print(f"\n{Colors.YELLOW}Sample Unemployed:{Colors.END}")
        for citizen in unemployed[:5]:
            print(f"  - {citizen.get('username')} ({citizen.get('socialClass')})")

def monitor_economic_health():
    """Monitor economic indicators"""
    print_header("ECONOMIC HEALTH")
    
    citizens_data = fetch_api("/citizens")
    buildings_data = fetch_api("/buildings")
    
    if not citizens_data or not buildings_data:
        print(f"{Colors.RED}Failed to fetch economic data{Colors.END}")
        return
    
    citizens = citizens_data.get('citizens', [])
    buildings = buildings_data.get('buildings', [])
    
    # Wealth distribution
    wealth_tiers = {
        'Destitute (0)': 0,
        'Poor (1-100)': 0,
        'Working (101-1000)': 0,
        'Comfortable (1001-5000)': 0,
        'Wealthy (5000+)': 0
    }
    
    total_wealth = 0
    for citizen in citizens:
        wealth = citizen.get('wealth', 0)
        total_wealth += wealth
        
        if wealth == 0:
            wealth_tiers['Destitute (0)'] += 1
        elif wealth <= 100:
            wealth_tiers['Poor (1-100)'] += 1
        elif wealth <= 1000:
            wealth_tiers['Working (101-1000)'] += 1
        elif wealth <= 5000:
            wealth_tiers['Comfortable (1001-5000)'] += 1
        else:
            wealth_tiers['Wealthy (5000+)'] += 1
    
    avg_wealth = total_wealth / len(citizens) if citizens else 0
    
    print(f"Total Wealth in Economy: {format_number(int(total_wealth))} ducats")
    print(f"Average Citizen Wealth: {format_number(int(avg_wealth))} ducats")
    
    print(f"\n{Colors.BOLD}Wealth Distribution:{Colors.END}")
    for tier, count in wealth_tiers.items():
        percentage = (count / len(citizens)) * 100 if citizens else 0
        color = Colors.RED if 'Destitute' in tier or 'Poor' in tier else Colors.GREEN
        print(f"  {tier}: {color}{count}{Colors.END} ({percentage:.1f}%)")
    
    # Business health
    businesses = [b for b in buildings if b.get('category') == 'business']
    broke_businesses = [b for b in businesses if b.get('wealth', 0) < b.get('wages', 1000)]
    
    print(f"\n{Colors.BOLD}Business Health:{Colors.END}")
    print(f"Total Businesses: {len(businesses)}")
    print(f"Broke Businesses: {color_status(len(broke_businesses), [5, 20, 50])}")

def monitor_hunger_crisis():
    """Monitor hunger and welfare needs"""
    print_header("HUNGER & WELFARE")
    
    problems_data = fetch_api("/problems?type=hungry_citizen&Status=active")
    
    if problems_data:
        hungry_problems = problems_data.get('problems', [])
        print(f"Hungry Citizens: {color_status(len(hungry_problems), [50, 100, 200])}")
    
    # Check for welfare activities
    welfare_data = fetch_api("/activities?type=work_for_food&limit=10")
    if welfare_data:
        activities = welfare_data.get('activities', [])
        active = [a for a in activities if a.get('status') in ['pending', 'in_progress']]
        print(f"Active Welfare Programs: {len(active)}")

def monitor_ai_health():
    """Monitor AI decision-making capability"""
    print_header("AI CONSCIOUSNESS STATUS")
    
    # Check recent AI activities
    messages_data = fetch_api("/messages?limit=50")
    
    if messages_data:
        messages = messages_data.get('messages', messages_data)
        
        error_count = 0
        success_count = 0
        
        for msg in messages:
            if isinstance(msg, dict):
                content = str(msg.get('content', '')).lower()
                if 'error' in content and 'llm' in content:
                    error_count += 1
                elif 'reflection' in content or 'decision' in content:
                    success_count += 1
        
        total = error_count + success_count
        if total > 0:
            success_rate = (success_count / total) * 100
            print(f"AI Decision Success Rate: {color_status(int(success_rate), [50, 80, 95])}%")
            print(f"Recent LLM Errors: {color_status(error_count, [5, 10, 20])}")
        else:
            print(f"{Colors.YELLOW}No recent AI activity detected{Colors.END}")

def monitor_critical_problems():
    """Monitor critical system problems"""
    print_header("CRITICAL PROBLEMS")
    
    problems_data = fetch_api("/problems?Status=active")
    
    if not problems_data:
        print(f"{Colors.RED}Failed to fetch problems data{Colors.END}")
        return
    
    problems = problems_data.get('problems', [])
    
    # Count by severity
    severity_count = defaultdict(int)
    problem_types = defaultdict(int)
    
    for problem in problems:
        if isinstance(problem, dict):
            severity = problem.get('severity', 'Unknown')
            ptype = problem.get('type', 'unknown')
            severity_count[severity] += 1
            problem_types[ptype] += 1
    
    print(f"Total Active Problems: {color_status(len(problems), [100, 500, 1000])}")
    
    print(f"\n{Colors.BOLD}By Severity:{Colors.END}")
    for severity in ['High', 'Medium', 'Low']:
        count = severity_count.get(severity, 0)
        color = Colors.RED if severity == 'High' else Colors.YELLOW if severity == 'Medium' else Colors.GREEN
        print(f"  {severity}: {color}{count}{Colors.END}")
    
    # Top problem types
    print(f"\n{Colors.BOLD}Top Problem Types:{Colors.END}")
    sorted_types = sorted(problem_types.items(), key=lambda x: x[1], reverse=True)[:5]
    for ptype, count in sorted_types:
        print(f"  {ptype}: {count}")

def generate_action_summary():
    """Generate recommended actions based on current state"""
    print_header("RECOMMENDED ACTIONS")
    
    actions = []
    
    # Check employment
    citizens_data = fetch_api("/citizens")
    if citizens_data:
        citizens = citizens_data.get('citizens', [])
        unemployed_count = len([c for c in citizens if not c.get('worksFor')])
        zero_wealth_count = len([c for c in citizens if c.get('wealth', 0) == 0])
        
        if unemployed_count > 10:
            actions.append(f"{Colors.RED}CRITICAL:{Colors.END} Run emergency employment bridge")
        
        if zero_wealth_count > 50:
            actions.append(f"{Colors.RED}CRITICAL:{Colors.END} Execute wage recovery system")
    
    # Check problems
    problems_data = fetch_api("/problems?Status=active")
    if problems_data:
        problems = problems_data.get('problems', [])
        high_severity = [p for p in problems if p.get('severity') == 'High']
        
        if any('scheduler' in p.get('type', '') for p in high_severity):
            actions.append(f"{Colors.YELLOW}HIGH:{Colors.END} Deploy job scheduler fix")
        
        if any('hungry' in p.get('type', '') for p in problems):
            actions.append(f"{Colors.YELLOW}HIGH:{Colors.END} Implement welfare safety net")
    
    if not actions:
        actions.append(f"{Colors.GREEN}System appears stable - continue monitoring{Colors.END}")
    
    for i, action in enumerate(actions, 1):
        print(f"{i}. {action}")

def continuous_monitor(interval=60):
    """Run continuous monitoring"""
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Colors.BOLD}{Colors.BLUE}LA SERENISSIMA HEALTH MONITOR{Colors.END}")
        print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        monitor_employment()
        monitor_economic_health()
        monitor_hunger_crisis()
        monitor_ai_health()
        monitor_critical_problems()
        generate_action_summary()
        
        print(f"\n{Colors.YELLOW}Refreshing in {interval} seconds... (Ctrl+C to exit){Colors.END}")
        
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{Colors.GREEN}Monitoring stopped.{Colors.END}")
            break

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Health monitor for La Serenissima")
    parser.add_argument('--once', action='store_true', help="Run once instead of continuous monitoring")
    parser.add_argument('--interval', type=int, default=60, help="Refresh interval in seconds")
    args = parser.parse_args()
    
    if args.once:
        monitor_employment()
        monitor_economic_health()
        monitor_hunger_crisis()
        monitor_ai_health()
        monitor_critical_problems()
        generate_action_summary()
    else:
        continuous_monitor(args.interval)

if __name__ == "__main__":
    main()
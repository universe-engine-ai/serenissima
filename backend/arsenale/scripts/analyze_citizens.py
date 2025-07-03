#!/usr/bin/env python3
"""
Citizen Welfare Analysis for La Serenissima
Identifies struggling citizens and systemic problems
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Any


def fetch_citizens() -> List[Dict[str, Any]]:
    """Fetch all AI citizens from the API"""
    try:
        with urllib.request.urlopen("http://172.17.0.1:3000/api/citizens?all=true") as response:
            data = json.loads(response.read().decode('utf-8'))
            # Filter for AI citizens only
            return [c for c in data.get('citizens', []) if c.get('isAI', False)]
    except Exception as e:
        print(f"Error fetching citizens: {e}")
    return []


def analyze_economic_health(citizens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze economic indicators"""
    if not citizens:
        return {}
    
    ducats_list = [c.get('ducats', 0) for c in citizens]
    
    return {
        'total_citizens': len(citizens),
        'average_ducats': sum(ducats_list) / len(ducats_list),
        'min_ducats': min(ducats_list),
        'max_ducats': max(ducats_list),
        'poverty_line': len([d for d in ducats_list if d < 100]),
        'extreme_poverty': len([d for d in ducats_list if d < 10]),
        'unemployed': len([c for c in citizens if not c.get('workplace')])
    }


def identify_struggling_citizens(citizens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find citizens in economic distress"""
    struggling = []
    
    for citizen in citizens:
        problems = []
        severity = "Low"
        
        # Check financial status
        ducats = citizen.get('ducats', 0)
        if ducats < 10:
            problems.append("Extreme poverty")
            severity = "High"
        elif ducats < 100:
            problems.append("Below poverty line")
            severity = "Medium"
        
        # Check employment
        if not citizen.get('workplace'):
            problems.append("Unemployed")
            if severity == "Low":
                severity = "Medium"
        
        # Check income vs expenses
        daily_income = citizen.get('dailyIncome', 0)
        daily_expenses = citizen.get('dailyNetResult', 0)
        if daily_expenses < 0 and abs(daily_expenses) > daily_income:
            problems.append("Unsustainable expenses")
            severity = "High"
        
        if problems:
            struggling.append({
                'citizenId': citizen.get('citizenId'),
                'name': f"{citizen.get('firstName')} {citizen.get('lastName')}",
                'ducats': ducats,
                'problems': problems,
                'severity': severity,
                'location': citizen.get('position')
            })
    
    return sorted(struggling, key=lambda x: {'High': 0, 'Medium': 1, 'Low': 2}[x['severity']])


def analyze_systemic_issues(citizens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify system-wide problems"""
    issues = []
    
    # Economic analysis
    econ = analyze_economic_health(citizens)
    
    if econ.get('extreme_poverty', 0) > len(citizens) * 0.1:
        issues.append({
            'title': 'Widespread Extreme Poverty',
            'affected_count': econ['extreme_poverty'],
            'severity': 'High',
            'description': f"{econ['extreme_poverty']} citizens have less than 10 ducats"
        })
    
    if econ.get('unemployed', 0) > len(citizens) * 0.2:
        issues.append({
            'title': 'High Unemployment',
            'affected_count': econ['unemployed'],
            'severity': 'High',
            'description': f"{econ['unemployed']} citizens have no workplace"
        })
    
    # Wealth inequality
    if econ.get('max_ducats', 0) > econ.get('average_ducats', 1) * 100:
        issues.append({
            'title': 'Extreme Wealth Inequality',
            'severity': 'Medium',
            'description': f"Wealthiest citizen has {econ['max_ducats']:.0f} ducats while average is {econ['average_ducats']:.0f}"
        })
    
    return issues


def main():
    print("🔍 Analyzing La Serenissima Citizen Welfare...")
    print("=" * 60)
    
    # Fetch citizen data
    citizens = fetch_citizens()
    if not citizens:
        print("❌ Could not fetch citizen data")
        return
    
    print(f"✅ Analyzing {len(citizens)} AI citizens")
    
    # Economic health
    econ = analyze_economic_health(citizens)
    print(f"\n📊 Economic Overview:")
    print(f"   Average wealth: {econ['average_ducats']:.2f} ducats")
    print(f"   Below poverty line: {econ['poverty_line']} citizens")
    print(f"   Extreme poverty: {econ['extreme_poverty']} citizens")
    print(f"   Unemployed: {econ['unemployed']} citizens")
    
    # Find struggling citizens
    struggling = identify_struggling_citizens(citizens)
    
    # System issues
    systemic = analyze_systemic_issues(citizens)
    
    # Generate report
    print("\n" + "=" * 60)
    print("PROBLEM ANALYSIS REPORT")
    print("=" * 60)
    
    problems = []
    
    # Problem 1: Extreme Poverty Crisis
    if econ['extreme_poverty'] > 0:
        affected_ids = [c['citizenId'] for c in struggling if 'Extreme poverty' in c['problems']][:5]
        problems.append({
            'title': 'Extreme Poverty Crisis',
            'citizens_affected': affected_ids,
            'severity': 'High',
            'root_cause': 'Insufficient income opportunities and high cost of living',
            'solution_direction': 'Create emergency employment programs and basic income support'
        })
    
    # Problem 2: Unemployment
    if econ['unemployed'] > 5:
        unemployed = [c for c in citizens if not c.get('workplace')][:5]
        problems.append({
            'title': 'Structural Unemployment',
            'citizens_affected': [c['citizenId'] for c in unemployed],
            'severity': 'High',
            'root_cause': 'Mismatch between available jobs and citizen locations/skills',
            'solution_direction': 'Job matching system and transportation assistance'
        })
    
    # Output formatted report
    for i, problem in enumerate(problems, 1):
        print(f"\n### Problem {i}: {problem['title']}")
        print(f"**Citizens Affected**: {', '.join(problem['citizens_affected'])}")
        print(f"**Impact Severity**: {problem['severity']}")
        print(f"**Root Cause Hypothesis**: {problem['root_cause']}")
        print(f"**Suggested Solution Direction**: {problem['solution_direction']}")
    
    # Save detailed data
    with open('/mnt/c/Users/reyno/serenissima_claude/arsenale/logs/citizen_analysis.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'economic_health': econ,
            'struggling_citizens': struggling,
            'systemic_issues': systemic,
            'problems': problems
        }, f, indent=2)
    
    print(f"\n📁 Detailed analysis saved to: arsenale/logs/citizen_analysis.json")


if __name__ == "__main__":
    main()
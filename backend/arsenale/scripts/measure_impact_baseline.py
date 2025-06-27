#!/usr/bin/env python3
"""
Impact Measurement Tool for La Serenissima
Captures baseline and tracks improvements from interventions
"""

import os
import json
import requests
from datetime import datetime
from collections import defaultdict
import statistics

API_BASE = "https://serenissima.ai/api"

class WelfareBaseline:
    """Capture comprehensive baseline metrics"""
    
    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.metrics = {}
        
    def fetch_api(self, endpoint):
        """Fetch data from API"""
        try:
            response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {endpoint}: {e}")
            return None
    
    def measure_employment(self):
        """Measure employment metrics"""
        citizens_data = self.fetch_api("/citizens")
        if not citizens_data:
            return
            
        citizens = citizens_data.get('citizens', [])
        
        employed = [c for c in citizens if c.get('worksFor')]
        unemployed = [c for c in citizens if not c.get('worksFor')]
        
        self.metrics['employment'] = {
            'total_citizens': len(citizens),
            'employed': len(employed),
            'unemployed': len(unemployed),
            'unemployment_rate': (len(unemployed) / len(citizens) * 100) if citizens else 0,
            'unemployed_by_class': self._group_by_class(unemployed),
            'unemployed_usernames': [c.get('username') for c in unemployed]
        }
    
    def measure_wealth(self):
        """Measure wealth distribution"""
        citizens_data = self.fetch_api("/citizens")
        if not citizens_data:
            return
            
        citizens = citizens_data.get('citizens', [])
        
        wealth_values = [c.get('wealth', 0) for c in citizens]
        
        # Detailed wealth analysis
        wealth_tiers = {
            'zero': 0,
            'poor_1_100': 0,
            'working_101_1000': 0,
            'comfortable_1001_5000': 0,
            'wealthy_5000_plus': 0
        }
        
        employed_zero_wealth = []
        
        for citizen in citizens:
            wealth = citizen.get('wealth', 0)
            username = citizen.get('username')
            works_for = citizen.get('worksFor')
            
            if wealth == 0:
                wealth_tiers['zero'] += 1
                if works_for:
                    employed_zero_wealth.append({
                        'username': username,
                        'employer': works_for,
                        'class': citizen.get('socialClass')
                    })
            elif wealth <= 100:
                wealth_tiers['poor_1_100'] += 1
            elif wealth <= 1000:
                wealth_tiers['working_101_1000'] += 1
            elif wealth <= 5000:
                wealth_tiers['comfortable_1001_5000'] += 1
            else:
                wealth_tiers['wealthy_5000_plus'] += 1
        
        self.metrics['wealth'] = {
            'total_wealth': sum(wealth_values),
            'average_wealth': statistics.mean(wealth_values) if wealth_values else 0,
            'median_wealth': statistics.median(wealth_values) if wealth_values else 0,
            'min_wealth': min(wealth_values) if wealth_values else 0,
            'max_wealth': max(wealth_values) if wealth_values else 0,
            'wealth_distribution': wealth_tiers,
            'employed_with_zero_wealth': len(employed_zero_wealth),
            'employed_zero_wealth_details': employed_zero_wealth[:10]  # Sample
        }
    
    def measure_hunger(self):
        """Measure hunger crisis"""
        problems_data = self.fetch_api("/problems?type=hungry_citizen&Status=active")
        
        if problems_data:
            hungry_problems = problems_data.get('problems', [])
            
            # Extract citizen details from problems
            hungry_by_severity = defaultdict(list)
            
            for problem in hungry_problems:
                citizen = problem.get('citizen', 'Unknown')
                severity = problem.get('severity', 'Unknown')
                hungry_by_severity[severity].append(citizen)
            
            self.metrics['hunger'] = {
                'total_hungry': len(hungry_problems),
                'by_severity': dict(hungry_by_severity),
                'percentage_hungry': (len(hungry_problems) / self.metrics.get('employment', {}).get('total_citizens', 1)) * 100
            }
    
    def measure_economic_flow(self):
        """Measure economic activity"""
        # Recent activities
        activities_data = self.fetch_api("/activities?limit=100")
        
        if activities_data:
            activities = activities_data.get('activities', [])
            
            # Activity success rates
            activity_stats = defaultdict(lambda: {'total': 0, 'failed': 0, 'completed': 0})
            
            for activity in activities:
                act_type = activity.get('type', 'unknown')
                status = activity.get('status', '')
                
                activity_stats[act_type]['total'] += 1
                if status == 'failed':
                    activity_stats[act_type]['failed'] += 1
                elif status == 'completed':
                    activity_stats[act_type]['completed'] += 1
            
            self.metrics['economic_flow'] = {
                'recent_activities': len(activities),
                'activity_types': dict(activity_stats),
                'total_failed': sum(s['failed'] for s in activity_stats.values()),
                'total_completed': sum(s['completed'] for s in activity_stats.values())
            }
    
    def measure_ai_health(self):
        """Measure AI decision-making capability"""
        messages_data = self.fetch_api("/messages?limit=100")
        
        if messages_data:
            messages = messages_data.get('messages', messages_data) if isinstance(messages_data, dict) else messages_data
            
            llm_errors = 0
            successful_thoughts = 0
            
            for msg in messages:
                if isinstance(msg, dict):
                    content = str(msg.get('content', '')).lower()
                    if 'error' in content and ('llm' in content or 'could not connect' in content):
                        llm_errors += 1
                    elif any(word in content for word in ['reflection', 'contemplating', 'decision', 'considering']):
                        successful_thoughts += 1
            
            total_ai_attempts = llm_errors + successful_thoughts
            
            self.metrics['ai_health'] = {
                'llm_errors': llm_errors,
                'successful_thoughts': successful_thoughts,
                'total_attempts': total_ai_attempts,
                'success_rate': (successful_thoughts / total_ai_attempts * 100) if total_ai_attempts > 0 else 0
            }
    
    def measure_system_problems(self):
        """Measure system-wide problems"""
        problems_data = self.fetch_api("/problems?Status=active")
        
        if problems_data:
            problems = problems_data.get('problems', [])
            
            # Categorize problems
            problem_summary = defaultdict(int)
            severity_count = defaultdict(int)
            
            for problem in problems:
                if isinstance(problem, dict):
                    ptype = problem.get('type', 'unknown')
                    severity = problem.get('severity', 'Unknown')
                    problem_summary[ptype] += 1
                    severity_count[severity] += 1
            
            self.metrics['system_problems'] = {
                'total_active': len(problems),
                'by_type': dict(problem_summary),
                'by_severity': dict(severity_count),
                'critical_problems': severity_count.get('High', 0)
            }
    
    def _group_by_class(self, citizens):
        """Group citizens by social class"""
        by_class = defaultdict(int)
        for citizen in citizens:
            social_class = citizen.get('socialClass', 'Unknown')
            by_class[social_class] += 1
        return dict(by_class)
    
    def capture_baseline(self):
        """Capture all baseline metrics"""
        print("Capturing baseline metrics...")
        
        self.measure_employment()
        self.measure_wealth()
        self.measure_hunger()
        self.measure_economic_flow()
        self.measure_ai_health()
        self.measure_system_problems()
        
        # Save baseline
        baseline_file = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(baseline_file, 'w') as f:
            json.dump({
                'timestamp': self.timestamp,
                'metrics': self.metrics
            }, f, indent=2)
        
        print(f"Baseline saved to {baseline_file}")
        return self.metrics
    
    def print_summary(self):
        """Print baseline summary"""
        print("\n=== BASELINE WELFARE METRICS ===")
        print(f"Timestamp: {self.timestamp}")
        
        if 'employment' in self.metrics:
            emp = self.metrics['employment']
            print(f"\nEmployment:")
            print(f"  Total Citizens: {emp['total_citizens']}")
            print(f"  Unemployed: {emp['unemployed']} ({emp['unemployment_rate']:.1f}%)")
        
        if 'wealth' in self.metrics:
            wealth = self.metrics['wealth']
            print(f"\nWealth:")
            print(f"  Total Economy: {wealth['total_wealth']:,} ducats")
            print(f"  Average Wealth: {wealth['average_wealth']:.0f} ducats")
            print(f"  Citizens with 0 ducats: {wealth['wealth_distribution']['zero']}")
            print(f"  Employed with 0 wealth: {wealth['employed_with_zero_wealth']}")
        
        if 'hunger' in self.metrics:
            hunger = self.metrics['hunger']
            print(f"\nHunger Crisis:")
            print(f"  Hungry Citizens: {hunger['total_hungry']} ({hunger['percentage_hungry']:.1f}%)")
        
        if 'ai_health' in self.metrics:
            ai = self.metrics['ai_health']
            print(f"\nAI Health:")
            print(f"  Success Rate: {ai['success_rate']:.1f}%")
            print(f"  LLM Errors: {ai['llm_errors']}")
        
        if 'system_problems' in self.metrics:
            problems = self.metrics['system_problems']
            print(f"\nSystem Problems:")
            print(f"  Total Active: {problems['total_active']}")
            print(f"  High Severity: {problems['critical_problems']}")

def compare_baselines(baseline1_file, baseline2_file):
    """Compare two baseline measurements"""
    with open(baseline1_file, 'r') as f:
        baseline1 = json.load(f)
    
    with open(baseline2_file, 'r') as f:
        baseline2 = json.load(f)
    
    print("\n=== IMPACT COMPARISON ===")
    print(f"Before: {baseline1['timestamp']}")
    print(f"After:  {baseline2['timestamp']}")
    
    metrics1 = baseline1['metrics']
    metrics2 = baseline2['metrics']
    
    # Employment impact
    if 'employment' in metrics1 and 'employment' in metrics2:
        emp1 = metrics1['employment']
        emp2 = metrics2['employment']
        
        print("\nEmployment Changes:")
        print(f"  Unemployed: {emp1['unemployed']} → {emp2['unemployed']} "
              f"({emp2['unemployed'] - emp1['unemployed']:+d})")
        print(f"  Unemployment Rate: {emp1['unemployment_rate']:.1f}% → "
              f"{emp2['unemployment_rate']:.1f}% "
              f"({emp2['unemployment_rate'] - emp1['unemployment_rate']:+.1f}%)")
    
    # Wealth impact
    if 'wealth' in metrics1 and 'wealth' in metrics2:
        wealth1 = metrics1['wealth']
        wealth2 = metrics2['wealth']
        
        print("\nWealth Changes:")
        print(f"  Average Wealth: {wealth1['average_wealth']:.0f} → "
              f"{wealth2['average_wealth']:.0f} ducats "
              f"({wealth2['average_wealth'] - wealth1['average_wealth']:+.0f})")
        print(f"  Citizens with 0 ducats: {wealth1['wealth_distribution']['zero']} → "
              f"{wealth2['wealth_distribution']['zero']} "
              f"({wealth2['wealth_distribution']['zero'] - wealth1['wealth_distribution']['zero']:+d})")
    
    # Hunger impact
    if 'hunger' in metrics1 and 'hunger' in metrics2:
        hunger1 = metrics1['hunger']
        hunger2 = metrics2['hunger']
        
        print("\nHunger Changes:")
        print(f"  Hungry Citizens: {hunger1['total_hungry']} → {hunger2['total_hungry']} "
              f"({hunger2['total_hungry'] - hunger1['total_hungry']:+d})")
    
    # Calculate overall improvement score
    improvements = 0
    if emp2['unemployed'] < emp1['unemployed']:
        improvements += 1
    if wealth2['average_wealth'] > wealth1['average_wealth']:
        improvements += 1
    if wealth2['wealth_distribution']['zero'] < wealth1['wealth_distribution']['zero']:
        improvements += 1
    if hunger2['total_hungry'] < hunger1['total_hungry']:
        improvements += 1
    
    print(f"\nOverall Improvement Score: {improvements}/4")

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Impact measurement for La Serenissima")
    parser.add_argument('--capture', action='store_true', help="Capture new baseline")
    parser.add_argument('--compare', nargs=2, help="Compare two baseline files")
    args = parser.parse_args()
    
    if args.capture:
        baseline = WelfareBaseline()
        baseline.capture_baseline()
        baseline.print_summary()
    elif args.compare:
        compare_baselines(args.compare[0], args.compare[1])
    else:
        print("Use --capture to create baseline or --compare file1 file2 to compare")

if __name__ == "__main__":
    main()
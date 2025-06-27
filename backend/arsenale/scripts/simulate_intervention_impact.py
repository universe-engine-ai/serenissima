#!/usr/bin/env python3
"""
Simulate the expected impact of interventions
Helps predict outcomes before deployment
"""

import json
from datetime import datetime

class InterventionSimulator:
    """Simulate impact of emergency interventions"""
    
    def __init__(self, baseline_file):
        with open(baseline_file, 'r') as f:
            self.baseline = json.load(f)
        self.metrics = self.baseline['metrics'].copy()
        self.interventions = []
    
    def simulate_employment_fix(self):
        """Simulate impact of employment bridge"""
        print("\n=== SIMULATING EMPLOYMENT FIX ===")
        
        unemployed = self.metrics['employment']['unemployed']
        # Assuming 2 available businesses from our test
        jobs_created = min(unemployed, 2)
        
        self.metrics['employment']['unemployed'] -= jobs_created
        self.metrics['employment']['employed'] += jobs_created
        self.metrics['employment']['unemployment_rate'] = (
            self.metrics['employment']['unemployed'] / 
            self.metrics['employment']['total_citizens'] * 100
        )
        
        self.interventions.append({
            'name': 'Employment Bridge',
            'impact': f"Created {jobs_created} jobs",
            'citizens_helped': jobs_created
        })
        
        print(f"✓ Created {jobs_created} new jobs")
        print(f"  Unemployment: {unemployed} → {self.metrics['employment']['unemployed']}")
        
        return jobs_created
    
    def simulate_wage_recovery(self):
        """Simulate wage payment recovery"""
        print("\n=== SIMULATING WAGE RECOVERY ===")
        
        # From our analysis: 105 employed with 0 wealth
        # Average wage ~1000 ducats based on system
        employed_poor = self.metrics['wealth']['employed_with_zero_wealth']
        avg_wage = 1000
        
        # Update wealth distribution
        self.metrics['wealth']['wealth_distribution']['zero'] -= employed_poor
        self.metrics['wealth']['wealth_distribution']['working_101_1000'] += employed_poor
        
        # Update total wealth
        wealth_injected = employed_poor * avg_wage
        self.metrics['wealth']['total_wealth'] += wealth_injected
        self.metrics['wealth']['average_wealth'] = (
            self.metrics['wealth']['total_wealth'] / 
            self.metrics['employment']['total_citizens']
        )
        
        self.metrics['wealth']['employed_with_zero_wealth'] = 0
        
        self.interventions.append({
            'name': 'Wage Recovery',
            'impact': f"Distributed {wealth_injected:,} ducats",
            'citizens_helped': employed_poor
        })
        
        print(f"✓ Paid wages to {employed_poor} employed citizens")
        print(f"  Total wealth injected: {wealth_injected:,} ducats")
        print(f"  Average wealth: 0 → {self.metrics['wealth']['average_wealth']:.0f} ducats")
        
        return employed_poor
    
    def simulate_welfare_programs(self):
        """Simulate welfare safety net impact"""
        print("\n=== SIMULATING WELFARE PROGRAMS ===")
        
        hungry_before = self.metrics['hunger']['total_hungry']
        
        # Food distribution at 3 churches, 50 bread each = 150 citizens fed
        food_distribution_impact = 150
        
        # Work-for-food programs for 20 critical cases
        work_programs_impact = 20
        
        total_fed = min(hungry_before, food_distribution_impact + work_programs_impact)
        
        self.metrics['hunger']['total_hungry'] -= total_fed
        self.metrics['hunger']['percentage_hungry'] = (
            self.metrics['hunger']['total_hungry'] / 
            self.metrics['employment']['total_citizens'] * 100
        )
        
        self.interventions.append({
            'name': 'Welfare Safety Net',
            'impact': f"Fed {total_fed} hungry citizens",
            'citizens_helped': total_fed
        })
        
        print(f"✓ Established food distribution and work programs")
        print(f"  Hungry citizens: {hungry_before} → {self.metrics['hunger']['total_hungry']}")
        print(f"  Hunger rate: 565.3% → {self.metrics['hunger']['percentage_hungry']:.1f}%")
        
        return total_fed
    
    def simulate_ai_resilience(self):
        """Simulate AI decision system improvements"""
        print("\n=== SIMULATING AI RESILIENCE ===")
        
        # With fallback system, expect near 100% success
        current_rate = self.metrics['ai_health']['success_rate']
        improved_rate = 99.5  # Conservative estimate
        
        self.metrics['ai_health']['success_rate'] = improved_rate
        self.metrics['ai_health']['llm_errors'] = 1  # Rare failures
        
        self.interventions.append({
            'name': 'AI Resilience System',
            'impact': f"Improved success rate to {improved_rate}%",
            'citizens_helped': 119  # All AI citizens
        })
        
        print(f"✓ Deployed multi-layer AI fallback system")
        print(f"  AI success rate: {current_rate:.1f}% → {improved_rate}%")
        
        return 119
    
    def simulate_cascading_effects(self):
        """Simulate secondary positive effects"""
        print("\n=== SIMULATING CASCADING EFFECTS ===")
        
        # With wages paid, citizens can buy food
        if self.metrics['wealth']['average_wealth'] > 100:
            # Assume 50% reduction in hunger from market purchases
            hunger_reduction = int(self.metrics['hunger']['total_hungry'] * 0.5)
            self.metrics['hunger']['total_hungry'] -= hunger_reduction
            print(f"✓ Economic activity reduced hunger by {hunger_reduction} more citizens")
        
        # Employment creates more economic activity
        if self.metrics['employment']['unemployment_rate'] < 10:
            # Business revenue increases, creating more jobs
            self.metrics['system_problems']['total_active'] -= 100
            self.metrics['system_problems']['critical_problems'] -= 10
            print("✓ Economic recovery reducing system problems")
        
        # AI decisions drive cultural development
        if self.metrics['ai_health']['success_rate'] > 99:
            print("✓ AI citizens resuming cultural activities")
        
    def generate_projection(self):
        """Generate final impact projection"""
        print("\n" + "="*60)
        print("PROJECTED INTERVENTION IMPACT")
        print("="*60)
        
        # Run all simulations
        jobs_created = self.simulate_employment_fix()
        wages_paid = self.simulate_wage_recovery()
        fed_citizens = self.simulate_welfare_programs()
        ai_helped = self.simulate_ai_resilience()
        
        self.simulate_cascading_effects()
        
        # Calculate total impact
        total_helped = sum(i['citizens_helped'] for i in self.interventions)
        
        print(f"\n=== TOTAL PROJECTED IMPACT ===")
        print(f"Citizens Directly Helped: {total_helped}")
        print(f"Interventions Deployed: {len(self.interventions)}")
        
        # Save projection
        projection_file = f"impact_projection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(projection_file, 'w') as f:
            json.dump({
                'baseline_timestamp': self.baseline['timestamp'],
                'projection_timestamp': datetime.now().isoformat(),
                'interventions': self.interventions,
                'projected_metrics': self.metrics,
                'summary': {
                    'total_citizens_helped': total_helped,
                    'unemployment_change': self.baseline['metrics']['employment']['unemployed'] - self.metrics['employment']['unemployed'],
                    'wealth_created': self.metrics['wealth']['total_wealth'],
                    'hunger_reduced': self.baseline['metrics']['hunger']['total_hungry'] - self.metrics['hunger']['total_hungry']
                }
            }, f, indent=2)
        
        print(f"\nProjection saved to {projection_file}")
        
        return self.metrics

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Simulate intervention impact")
    parser.add_argument('baseline', help="Baseline JSON file")
    args = parser.parse_args()
    
    simulator = InterventionSimulator(args.baseline)
    simulator.generate_projection()

if __name__ == "__main__":
    main()
"""
Simplified criticality analysis for La Serenissima
"""

import requests
import numpy as np
from scipy import stats
import json
from datetime import datetime
import matplotlib.pyplot as plt


def fetch_citizens():
    """Fetch citizens data"""
    resp = requests.get("https://serenissima.ai/api/citizens")
    data = resp.json()
    if data.get('success'):
        return data.get('citizens', [])
    return []


def fetch_contracts():
    """Fetch contracts data"""
    resp = requests.get("https://serenissima.ai/api/contracts")
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get('contracts', [])


def fetch_activities():
    """Fetch recent activities"""
    resp = requests.get("https://serenissima.ai/api/activities?limit=500")
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get('activities', [])


def analyze_wealth_distribution(citizens):
    """Analyze wealth distribution for Boltzmann-Pareto patterns"""
    # Extract wealth values
    wealth_values = []
    for c in citizens:
        if isinstance(c, dict) and 'wealth' in c and c['wealth'] > 0:
            wealth_values.append(c['wealth'])
    
    wealth_values = sorted(wealth_values)
    
    if not wealth_values:
        print("No wealth data found")
        return {}
    
    # Split into body and tail
    split_point = np.percentile(wealth_values, 80)  # Top 20% as tail
    body = [w for w in wealth_values if w <= split_point]
    tail = [w for w in wealth_values if w > split_point]
    
    print(f"\nWealth Distribution Analysis:")
    print(f"Total citizens with wealth: {len(wealth_values)}")
    print(f"Body (bottom 80%): {len(body)} citizens")
    print(f"Tail (top 20%): {len(tail)} citizens")
    print(f"Split point: {split_point:.2f} florins")
    
    # Fit exponential to body (Boltzmann)
    T = None
    if body:
        # Estimate temperature parameter
        T = np.mean(body)
        print(f"Boltzmann temperature T = {T:.2f} florins")
    
    # Fit power law to tail (Pareto)
    alpha = None
    if len(tail) > 10:
        # Log-log regression
        log_wealth = np.log(tail)
        log_rank = np.log(range(len(tail), 0, -1))
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_wealth, log_rank)
        alpha = -slope
        
        print(f"Pareto exponent α = {alpha:.3f} ± {std_err:.3f}")
        print(f"R-squared = {r_value**2:.3f}")
    
    # Wealth inequality metrics
    total_wealth = sum(wealth_values)
    n = len(wealth_values)
    gini = (n + 1 - 2 * sum((n + 1 - i) * w for i, w in enumerate(sorted(wealth_values))) / total_wealth) / n
    
    print(f"\nInequality Metrics:")
    print(f"Total wealth: {total_wealth:,.0f} florins")
    print(f"Mean wealth: {np.mean(wealth_values):,.2f} florins")
    print(f"Median wealth: {np.median(wealth_values):,.2f} florins")
    print(f"Gini coefficient: {gini:.3f}")
    
    return {
        'wealth_values': wealth_values,
        'boltzmann_T': T,
        'pareto_alpha': alpha,
        'gini': gini
    }


def analyze_trust_network(citizens):
    """Analyze trust network from citizen data"""
    # Build trust network from citizen relationships
    trust_network = {}
    total_edges = 0
    
    # Count degrees from citizen data
    # Assuming each citizen has connections to others
    degrees = []
    for citizen in citizens:
        if isinstance(citizen, dict):
            # Count business partners, friends, etc.
            degree = 0
            # Add logic based on actual citizen data structure
            degrees.append(degree)
    
    if not degrees:
        print("\nNo trust network data available")
        return {}
    
    print(f"\nTrust Network Analysis:")
    print(f"Total nodes: {len(citizens)}")
    print(f"Average degree: {np.mean(degrees):.2f}")
    
    return {
        'avg_degree': np.mean(degrees) if degrees else 0
    }


def analyze_cascades(activities):
    """Detect and analyze information cascades"""
    cascade_sizes = []
    
    if not activities:
        print("\nNo activity data available")
        return {'cascade_sizes': [], 'tau': None, 'avg_size': 0}
    
    # Group activities by time windows (5 minutes)
    from collections import defaultdict
    time_bins = defaultdict(lambda: defaultdict(int))
    
    for activity in activities:
        if isinstance(activity, dict) and 'completedAt' in activity:
            # Parse timestamp
            try:
                timestamp = activity['completedAt']
                # Round to 5 minutes
                activity_type = activity.get('activityType', 'unknown')
                time_bins[timestamp[:16]][activity_type] += 1
            except:
                continue
    
    # Detect cascades
    for time_bin, activities in time_bins.items():
        for activity_type, count in activities.items():
            if count > 3:  # Minimum cascade size
                cascade_sizes.append(count)
    
    print(f"\nCascade Analysis:")
    print(f"Total cascades detected: {len(cascade_sizes)}")
    
    tau = None
    if cascade_sizes:
        print(f"Average cascade size: {np.mean(cascade_sizes):.2f}")
        print(f"Largest cascade: {max(cascade_sizes)}")
        
        # Fit power law if enough data
        if len(set(cascade_sizes)) > 5:
            unique_sizes = sorted(set(cascade_sizes))
            counts = [cascade_sizes.count(s) for s in unique_sizes]
            
            # Log-log regression
            mask = np.array(counts) > 0
            log_s = np.log(np.array(unique_sizes)[mask])
            log_p = np.log(np.array(counts)[mask])
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(log_s, log_p)
            tau = -slope
            
            print(f"Power law exponent τ = {tau:.3f} ± {std_err:.3f}")
            print(f"R-squared = {r_value**2:.3f}")
    
    return {
        'cascade_sizes': cascade_sizes,
        'tau': tau,
        'avg_size': np.mean(cascade_sizes) if cascade_sizes else 0
    }


def main():
    """Run simplified criticality analysis"""
    print("Fetching data from La Serenissima...")
    
    # Fetch data
    citizens = fetch_citizens()
    print(f"Fetched {len(citizens)} citizens")
    
    contracts = fetch_contracts()
    print(f"Fetched {len(contracts)} contracts")
    
    activities = fetch_activities()
    print(f"Fetched {len(activities)} activities")
    
    # Run analyses
    wealth_analysis = analyze_wealth_distribution(citizens)
    network_analysis = analyze_trust_network(citizens)
    cascade_analysis = analyze_cascades(activities)
    
    # Calculate criticality score
    criticality_score = 0.0
    components = 0
    
    # Wealth distribution component
    if wealth_analysis.get('pareto_alpha'):
        # Alpha around 2-3 is critical
        alpha_score = 1.0 - min(abs(wealth_analysis['pareto_alpha'] - 2.5) / 0.5, 1.0)
        criticality_score += alpha_score
        components += 1
    
    # Cascade component
    if cascade_analysis.get('tau'):
        # Tau around 1.5 is critical
        tau_score = 1.0 - min(abs(cascade_analysis['tau'] - 1.5) / 0.5, 1.0)
        criticality_score += tau_score
        components += 1
    
    if components > 0:
        criticality_score /= components
    
    # Summary
    print("\n" + "="*50)
    print("CRITICALITY ANALYSIS SUMMARY")
    print("="*50)
    
    if wealth_analysis.get('boltzmann_T'):
        print(f"Wealth: Boltzmann T={wealth_analysis['boltzmann_T']:.0f}")
    if wealth_analysis.get('pareto_alpha'):
        print(f"Wealth: Pareto α={wealth_analysis['pareto_alpha']:.2f}")
    if cascade_analysis.get('tau'):
        print(f"Cascades: Power law τ={cascade_analysis['tau']:.2f}")
    
    print(f"\nOverall Criticality Score: {criticality_score:.3f}")
    
    if criticality_score > 0.7:
        print("System Phase: CRITICAL (edge of chaos)")
    elif criticality_score > 0.3:
        print("System Phase: TRANSITIONAL")
    else:
        print("System Phase: ORDERED")
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'wealth': wealth_analysis,
        'cascades': cascade_analysis,
        'criticality_score': criticality_score
    }
    
    filename = f"criticality_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to {filename}")
    
    # Create simple plots
    if wealth_analysis.get('wealth_values'):
        plt.figure(figsize=(10, 4))
        
        # Wealth histogram
        plt.subplot(1, 2, 1)
        plt.hist(wealth_analysis['wealth_values'], bins=50, alpha=0.7)
        plt.xlabel('Wealth (florins)')
        plt.ylabel('Count')
        plt.title('Wealth Distribution')
        plt.yscale('log')
        
        # Cascade sizes
        if cascade_analysis['cascade_sizes']:
            plt.subplot(1, 2, 2)
            sizes, counts = np.unique(cascade_analysis['cascade_sizes'], return_counts=True)
            plt.scatter(sizes, counts, alpha=0.7)
            plt.xlabel('Cascade Size')
            plt.ylabel('Frequency')
            plt.title('Information Cascades')
            if len(sizes) > 1:
                plt.xscale('log')
                plt.yscale('log')
        
        plt.tight_layout()
        plot_filename = f"criticality_plots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_filename)
        print(f"Plots saved to {plot_filename}")
        plt.close()


if __name__ == "__main__":
    main()
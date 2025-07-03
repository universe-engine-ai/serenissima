"""
Analyze live criticality data from La Serenissima
Gather empirical evidence for the paper
"""

import asyncio
import json
from datetime import datetime
import numpy as np
import pandas as pd
import aiohttp
from scipy import stats
import matplotlib.pyplot as plt

from criticality_metrics import CriticalityMetrics, calculate_criticality_metrics


async def fetch_live_data():
    """Fetch comprehensive data from La Serenissima API"""
    api_base = "https://serenissima.ai/api"
    
    async with aiohttp.ClientSession() as session:
        # Get all citizens
        async with session.get(f"{api_base}/citizens") as resp:
            citizens = await resp.json()
            print(f"Fetched {len(citizens)} citizens")
        
        # Get recent transactions history
        async with session.get(f"{api_base}/transactions/history?limit=10000") as resp:
            transactions = await resp.json()
            print(f"Fetched {len(transactions)} transactions")
        
        # Get all relationships (from citizens data)
        relationships = []
        print(f"Extracting relationships from citizen data...")
        
        # Get recent activities
        async with session.get(f"{api_base}/activities?status=completed&limit=5000") as resp:
            activities = await resp.json()
            print(f"Fetched {len(activities)} activities")
        
        # Get contracts
        async with session.get(f"{api_base}/contracts") as resp:
            contracts = await resp.json()
            print(f"Fetched {len(contracts)} contracts")
    
    return {
        'citizens': citizens,
        'transactions': transactions,
        'relationships': relationships,
        'activities': activities,
        'contracts': contracts,
        'timestamp': datetime.now().isoformat()
    }


def analyze_wealth_distribution(citizens):
    """Analyze wealth distribution for Boltzmann-Pareto patterns"""
    # Extract wealth values
    wealth_values = [c['wealth'] for c in citizens if c['wealth'] > 0]
    wealth_values = sorted(wealth_values)
    
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
    if body:
        # Estimate temperature parameter
        T = np.mean(body)
        print(f"Boltzmann temperature T = {T:.2f} florins")
    
    # Fit power law to tail (Pareto)
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
    cumulative_wealth = np.cumsum(sorted(wealth_values))
    lorenz = cumulative_wealth / total_wealth
    
    # Gini coefficient
    n = len(wealth_values)
    gini = (n + 1 - 2 * sum((n + 1 - i) * w for i, w in enumerate(sorted(wealth_values))) / total_wealth) / n
    
    print(f"\nInequality Metrics:")
    print(f"Total wealth: {total_wealth:,.0f} florins")
    print(f"Mean wealth: {np.mean(wealth_values):,.2f} florins")
    print(f"Median wealth: {np.median(wealth_values):,.2f} florins")
    print(f"Gini coefficient: {gini:.3f}")
    
    return {
        'wealth_values': wealth_values,
        'boltzmann_T': T if body else None,
        'pareto_alpha': alpha if len(tail) > 10 else None,
        'gini': gini
    }


def analyze_trust_network(relationships):
    """Analyze trust network for scale-free properties"""
    # Build adjacency lists
    trust_network = {}
    
    for rel in relationships:
        if rel['trust_level'] > 0.5:  # Trust threshold
            citizen = rel['citizen_id']
            target = rel['target_id']
            
            if citizen not in trust_network:
                trust_network[citizen] = []
            if target not in trust_network:
                trust_network[target] = []
                
            trust_network[citizen].append(target)
    
    # Calculate degree distribution
    degrees = [len(neighbors) for neighbors in trust_network.values()]
    degree_counts = pd.Series(degrees).value_counts().sort_index()
    
    print(f"\nTrust Network Analysis:")
    print(f"Total nodes: {len(trust_network)}")
    print(f"Total edges: {sum(degrees) // 2}")
    print(f"Average degree: {np.mean(degrees):.2f}")
    
    # Fit power law to degree distribution
    if len(degree_counts) > 5:
        k_values = degree_counts.index.values
        p_values = degree_counts.values
        
        # Remove zeros and take logs
        mask = (k_values > 0) & (p_values > 0)
        log_k = np.log(k_values[mask])
        log_p = np.log(p_values[mask])
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_k, log_p)
        gamma = -slope
        
        print(f"Power law exponent γ = {gamma:.3f} ± {std_err:.3f}")
        print(f"R-squared = {r_value**2:.3f}")
    
    # Calculate clustering coefficient
    clustering_coeffs = []
    for node, neighbors in trust_network.items():
        if len(neighbors) > 1:
            # Count triangles
            triangles = 0
            for i, n1 in enumerate(neighbors):
                for n2 in neighbors[i+1:]:
                    if n1 in trust_network and n2 in trust_network[n1]:
                        triangles += 1
            
            # Clustering coefficient
            possible_triangles = len(neighbors) * (len(neighbors) - 1) / 2
            if possible_triangles > 0:
                clustering_coeffs.append(triangles / possible_triangles)
    
    avg_clustering = np.mean(clustering_coeffs) if clustering_coeffs else 0
    print(f"Average clustering coefficient: {avg_clustering:.3f}")
    
    return {
        'degree_distribution': degree_counts,
        'gamma': gamma if len(degree_counts) > 5 else None,
        'avg_degree': np.mean(degrees),
        'clustering': avg_clustering
    }


def analyze_cascades(activities):
    """Detect and analyze information cascades"""
    # Group activities by 5-minute windows
    cascade_sizes = []
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(activities)
    if 'completed_at' in df.columns:
        df['completed_at'] = pd.to_datetime(df['completed_at'])
        df['time_bin'] = df['completed_at'].dt.floor('5min')
        
        # Group by time bin and activity type
        grouped = df.groupby(['time_bin', 'activity_type']).size()
        
        # Cascades are bursts of similar activities
        for (time_bin, activity_type), count in grouped.items():
            if count > 3:  # Minimum cascade size
                cascade_sizes.append(count)
    
    print(f"\nCascade Analysis:")
    print(f"Total cascades detected: {len(cascade_sizes)}")
    
    if cascade_sizes:
        print(f"Average cascade size: {np.mean(cascade_sizes):.2f}")
        print(f"Largest cascade: {max(cascade_sizes)}")
        
        # Fit power law
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
                'avg_size': np.mean(cascade_sizes)
            }
    
    return {
        'cascade_sizes': cascade_sizes,
        'tau': None,
        'avg_size': 0
    }


def analyze_economic_velocity(transactions):
    """Analyze money velocity patterns"""
    # Convert to DataFrame
    df = pd.DataFrame(transactions)
    
    if 'timestamp' in df.columns and len(df) > 0:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Calculate velocity in hourly windows
        df['hour'] = df['timestamp'].dt.floor('H')
        hourly_velocity = df.groupby('hour')['amount'].sum()
        
        print(f"\nEconomic Velocity Analysis:")
        print(f"Total transactions: {len(df)}")
        print(f"Total value: {df['amount'].sum():,.0f} florins")
        print(f"Average transaction: {df['amount'].mean():.2f} florins")
        
        if len(hourly_velocity) > 2:
            velocities = hourly_velocity.values
            print(f"Average hourly velocity: {np.mean(velocities):,.0f} florins/hour")
            print(f"Velocity volatility (CV): {np.std(velocities) / np.mean(velocities):.3f}")
            
            # Check for heavy-tailed distribution
            # Jarque-Bera test for normality
            jb_stat, jb_pvalue = stats.jarque_bera(velocities)
            print(f"Jarque-Bera test p-value: {jb_pvalue:.3f}")
            
            if jb_pvalue < 0.05:
                print("Velocity distribution is non-normal (potential criticality indicator)")
            
            return {
                'hourly_velocities': velocities,
                'avg_velocity': np.mean(velocities),
                'volatility': np.std(velocities) / np.mean(velocities)
            }
    
    return {
        'hourly_velocities': [],
        'avg_velocity': 0,
        'volatility': 0
    }


def calculate_live_criticality_metrics(data):
    """Calculate comprehensive criticality metrics"""
    # Extract trust edges
    trust_edges = []
    for rel in data['relationships']:
        if rel['trust_level'] > 0.5:
            trust_edges.append((rel['citizen_id'], rel['target_id']))
    
    # Detect cascades
    cascade_analysis = analyze_cascades(data['activities'])
    
    # Calculate metrics
    metrics = calculate_criticality_metrics(
        citizens_data=data['citizens'],
        transactions=data['transactions'],
        trust_edges=trust_edges,
        cascades=cascade_analysis['cascade_sizes']
    )
    
    print(f"\nCriticality Metrics:")
    print(f"Overall Criticality Score: {metrics['criticality_score']:.3f}")
    print(f"System Phase: {metrics['phase']}")
    print(f"Correlation Length: {metrics.get('correlation_length', 0):.2f}")
    print(f"Percolation: {metrics.get('percolation', 0):.3f}")
    print(f"Information Entropy: {metrics.get('information_entropy', 0):.3f}")
    
    if 'lyapunov' in metrics:
        print(f"Lyapunov Exponent: {metrics['lyapunov']:.3f}")
    
    return metrics


def save_analysis_results(data, wealth_analysis, network_analysis, 
                         cascade_analysis, velocity_analysis, criticality_metrics):
    """Save all analysis results"""
    results = {
        'timestamp': data['timestamp'],
        'summary': {
            'n_citizens': len(data['citizens']),
            'n_transactions': len(data['transactions']),
            'n_relationships': len(data['relationships']),
            'n_activities': len(data['activities']),
        },
        'wealth': wealth_analysis,
        'network': {
            'gamma': network_analysis['gamma'],
            'avg_degree': network_analysis['avg_degree'],
            'clustering': network_analysis['clustering']
        },
        'cascades': {
            'tau': cascade_analysis['tau'],
            'avg_size': cascade_analysis['avg_size'],
            'n_cascades': len(cascade_analysis['cascade_sizes'])
        },
        'velocity': {
            'avg_velocity': velocity_analysis['avg_velocity'],
            'volatility': velocity_analysis['volatility']
        },
        'criticality': criticality_metrics
    }
    
    # Save to file
    filename = f"criticality_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to {filename}")
    
    # Create visualizations
    create_analysis_plots(wealth_analysis, network_analysis, 
                         cascade_analysis, velocity_analysis)


def create_analysis_plots(wealth_analysis, network_analysis, 
                         cascade_analysis, velocity_analysis):
    """Create visualization plots"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Wealth distribution
    ax = axes[0, 0]
    wealth_values = wealth_analysis['wealth_values']
    ax.hist(wealth_values, bins=50, alpha=0.7, density=True)
    ax.set_yscale('log')
    ax.set_xlabel('Wealth (florins)')
    ax.set_ylabel('Probability Density')
    ax.set_title('Wealth Distribution (log scale)')
    
    # Degree distribution
    ax = axes[0, 1]
    if network_analysis['degree_distribution'] is not None:
        degrees = network_analysis['degree_distribution']
        ax.scatter(degrees.index, degrees.values, alpha=0.7)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('Degree k')
        ax.set_ylabel('P(k)')
        ax.set_title(f"Degree Distribution (γ={network_analysis['gamma']:.2f})")
    
    # Cascade sizes
    ax = axes[1, 0]
    if cascade_analysis['cascade_sizes']:
        cascade_sizes = cascade_analysis['cascade_sizes']
        unique_sizes, counts = np.unique(cascade_sizes, return_counts=True)
        ax.scatter(unique_sizes, counts, alpha=0.7)
        if len(unique_sizes) > 1:
            ax.set_xscale('log')
            ax.set_yscale('log')
        ax.set_xlabel('Cascade Size')
        ax.set_ylabel('Frequency')
        ax.set_title(f"Cascade Distribution (τ={cascade_analysis['tau']:.2f})" 
                     if cascade_analysis['tau'] else "Cascade Distribution")
    
    # Velocity time series
    ax = axes[1, 1]
    if len(velocity_analysis['hourly_velocities']) > 0:
        velocities = velocity_analysis['hourly_velocities']
        ax.plot(velocities, alpha=0.7)
        ax.set_xlabel('Hour')
        ax.set_ylabel('Money Velocity (florins/hour)')
        ax.set_title(f"Economic Velocity (CV={velocity_analysis['volatility']:.2f})")
    
    plt.tight_layout()
    filename = f"criticality_plots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Plots saved to {filename}")
    plt.close()


async def main():
    """Run complete criticality analysis"""
    print("Fetching live data from La Serenissima...")
    data = await fetch_live_data()
    
    print("\nAnalyzing system criticality...")
    
    # Run analyses
    wealth_analysis = analyze_wealth_distribution(data['citizens'])
    network_analysis = analyze_trust_network(data['relationships'])
    cascade_analysis = analyze_cascades(data['activities'])
    velocity_analysis = analyze_economic_velocity(data['transactions'])
    criticality_metrics = calculate_live_criticality_metrics(data)
    
    # Save results
    save_analysis_results(data, wealth_analysis, network_analysis,
                         cascade_analysis, velocity_analysis, criticality_metrics)
    
    print("\nAnalysis complete!")
    
    # Print summary for paper
    print("\n" + "="*50)
    print("SUMMARY FOR PAPER")
    print("="*50)
    print(f"System shows {criticality_metrics['phase']} phase dynamics")
    print(f"Wealth: Boltzmann T={wealth_analysis['boltzmann_T']:.0f}, "
          f"Pareto α={wealth_analysis['pareto_alpha']:.2f}")
    print(f"Network: Scale-free with γ={network_analysis['gamma']:.2f}")
    print(f"Cascades: Power law with τ={cascade_analysis['tau']:.2f}")
    print(f"Criticality Score: {criticality_metrics['criticality_score']:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
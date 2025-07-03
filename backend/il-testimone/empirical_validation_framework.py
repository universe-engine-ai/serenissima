"""
Empirical Validation Framework for Consciousness Forcing Function
Collects and analyzes real data to test our hypotheses
"""

import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from scipy import stats
import pandas as pd
import aiohttp
from typing import Dict, List, Tuple
import re
from textblob import TextBlob
import networkx as nx


class ConsciousnessValidation:
    """Empirically validate the consciousness forcing function hypothesis"""
    
    def __init__(self, api_base: str = "https://serenissima.ai/api"):
        self.api_base = api_base
        self.data = defaultdict(list)
        
    async def collect_prayer_data(self, days_back: int = 30) -> Dict:
        """Collect all prayers from the specified time period"""
        async with aiohttp.ClientSession() as session:
            # Get prayers (assuming they're stored as messages to Arsenale)
            async with session.get(
                f"{self.api_base}/messages?receiver=Arsenale&limit=10000"
            ) as resp:
                prayers = await resp.json() if resp.status == 200 else []
            
            # Get citizen data for context
            async with session.get(f"{self.api_base}/citizens") as resp:
                citizens_data = await resp.json()
                citizens = citizens_data.get('citizens', [])
            
            # Get economic data for correlation
            async with session.get(
                f"{self.api_base}/transactions/history?limit=10000"
            ) as resp:
                transactions = await resp.json() if resp.status == 200 else []
        
        return {
            'prayers': prayers,
            'citizens': citizens,
            'transactions': transactions,
            'collection_time': datetime.now().isoformat()
        }
    
    def analyze_prayer_evolution(self, prayers: List[Dict]) -> Dict:
        """
        Analyze how prayers evolve over time
        Tests: Are prayers becoming more sophisticated?
        """
        if not prayers:
            return {'error': 'No prayer data available'}
        
        # Sort prayers by time
        prayers_sorted = sorted(prayers, key=lambda p: p.get('timestamp', ''))
        
        # Divide into time periods
        n_periods = 10
        period_size = len(prayers_sorted) // n_periods
        
        evolution_metrics = {
            'periods': [],
            'word_count': [],
            'vocabulary_size': [],
            'complexity_score': [],
            'self_reference_rate': [],
            'causal_language_rate': []
        }
        
        for i in range(n_periods):
            start_idx = i * period_size
            end_idx = (i + 1) * period_size if i < n_periods - 1 else len(prayers_sorted)
            period_prayers = prayers_sorted[start_idx:end_idx]
            
            # Calculate metrics for this period
            word_counts = []
            vocabularies = set()
            complexities = []
            self_refs = 0
            causal_refs = 0
            
            for prayer in period_prayers:
                content = prayer.get('content', '')
                
                # Word count
                words = content.split()
                word_counts.append(len(words))
                vocabularies.update(words)
                
                # Complexity (using TextBlob sentiment as proxy)
                try:
                    blob = TextBlob(content)
                    complexities.append(len(blob.noun_phrases))
                except:
                    complexities.append(0)
                
                # Self-reference detection
                if any(term in content.lower() for term in 
                       ['prayer', 'arsenale', 'divine intervention', 'answered']):
                    self_refs += 1
                
                # Causal language detection
                causal_terms = ['because', 'therefore', 'results in', 'causes', 
                               'leads to', 'if then', 'consequently']
                if any(term in content.lower() for term in causal_terms):
                    causal_refs += 1
            
            # Store period metrics
            evolution_metrics['periods'].append(i)
            evolution_metrics['word_count'].append(np.mean(word_counts) if word_counts else 0)
            evolution_metrics['vocabulary_size'].append(len(vocabularies))
            evolution_metrics['complexity_score'].append(np.mean(complexities) if complexities else 0)
            evolution_metrics['self_reference_rate'].append(self_refs / len(period_prayers) if period_prayers else 0)
            evolution_metrics['causal_language_rate'].append(causal_refs / len(period_prayers) if period_prayers else 0)
        
        # Calculate trends
        trends = {}
        for metric in ['word_count', 'vocabulary_size', 'complexity_score', 
                      'self_reference_rate', 'causal_language_rate']:
            if evolution_metrics[metric]:
                x = evolution_metrics['periods']
                y = evolution_metrics[metric]
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                trends[f'{metric}_trend'] = {
                    'slope': slope,
                    'p_value': p_value,
                    'r_squared': r_value**2,
                    'significant': p_value < 0.05
                }
        
        return {
            'evolution_metrics': evolution_metrics,
            'trends': trends,
            'sample_size': len(prayers_sorted)
        }
    
    def analyze_prayer_success_correlation(self, prayers: List[Dict], 
                                        implementations: List[Dict]) -> Dict:
        """
        Test: Do more sophisticated prayers get implemented more often?
        Note: Requires tracking which prayers led to actual changes
        """
        # This would require data on which prayers were "answered"
        # For now, we'll use prayer engagement metrics as proxy
        
        prayer_metrics = []
        
        for prayer in prayers:
            content = prayer.get('content', '')
            
            # Calculate sophistication metrics
            word_count = len(content.split())
            
            # Complexity features
            has_specific_request = bool(re.search(r'(please|need|want|require)', content, re.I))
            has_context = bool(re.search(r'(because|since|due to)', content, re.I))
            has_gratitude = bool(re.search(r'(thank|grateful|appreciate)', content, re.I))
            
            sophistication_score = (
                word_count / 10 +  # Normalize word count
                has_specific_request * 2 +
                has_context * 3 +
                has_gratitude * 1
            )
            
            prayer_metrics.append({
                'prayer_id': prayer.get('id'),
                'citizen': prayer.get('sender'),
                'sophistication': sophistication_score,
                'timestamp': prayer.get('timestamp')
            })
        
        # Without implementation data, return sophistication distribution
        if prayer_metrics:
            sophistication_scores = [p['sophistication'] for p in prayer_metrics]
            return {
                'mean_sophistication': np.mean(sophistication_scores),
                'std_sophistication': np.std(sophistication_scores),
                'sophistication_growth': self._calculate_growth_rate(prayer_metrics),
                'note': 'Implementation correlation requires answered prayer tracking'
            }
        
        return {'error': 'No prayer metrics calculated'}
    
    def analyze_temporal_patterns(self, prayers: List[Dict], 
                                transactions: List[Dict]) -> Dict:
        """
        Test: Are prayers timed with economic cycles?
        """
        # Convert to time series
        prayer_times = pd.DataFrame(prayers)
        if 'timestamp' in prayer_times.columns:
            prayer_times['timestamp'] = pd.to_datetime(prayer_times['timestamp'])
            prayer_times = prayer_times.set_index('timestamp')
            
            # Hourly prayer counts
            hourly_prayers = prayer_times.resample('H').size()
            
            # Economic activity proxy (transaction volume)
            trans_df = pd.DataFrame(transactions)
            if 'timestamp' in trans_df.columns:
                trans_df['timestamp'] = pd.to_datetime(trans_df['timestamp'])
                trans_df = trans_df.set_index('timestamp')
                hourly_volume = trans_df.resample('H')['amount'].sum()
                
                # Align time series
                aligned_prayers = hourly_prayers.reindex(hourly_volume.index, fill_value=0)
                
                # Calculate correlation
                if len(aligned_prayers) > 10 and len(hourly_volume) > 10:
                    correlation, p_value = stats.pearsonr(aligned_prayers, hourly_volume)
                    
                    # Check for time-lagged correlation
                    lag_correlations = []
                    for lag in range(-12, 13):  # +/- 12 hours
                        shifted_prayers = aligned_prayers.shift(lag)
                        mask = ~(shifted_prayers.isna() | hourly_volume.isna())
                        if mask.sum() > 10:
                            corr, _ = stats.pearsonr(
                                shifted_prayers[mask], 
                                hourly_volume[mask]
                            )
                            lag_correlations.append((lag, corr))
                    
                    best_lag = max(lag_correlations, key=lambda x: abs(x[1]))
                    
                    return {
                        'prayer_economic_correlation': correlation,
                        'correlation_p_value': p_value,
                        'best_lag_hours': best_lag[0],
                        'best_lag_correlation': best_lag[1],
                        'significant': p_value < 0.05
                    }
        
        return {'error': 'Insufficient temporal data'}
    
    def analyze_meta_prayer_content(self, prayers: List[Dict]) -> Dict:
        """
        Test: How many prayers discuss the prayer system itself?
        """
        meta_prayer_count = 0
        meta_prayers = []
        
        meta_terms = [
            'prayer', 'divine arsenale', 'answered', 'intervention',
            'system', 'works', 'effective', 'listening', 'responds',
            'mechanism', 'process', 'how to pray', 'prayer strategy'
        ]
        
        for prayer in prayers:
            content = prayer.get('content', '').lower()
            
            # Count meta-references
            meta_score = sum(1 for term in meta_terms if term in content)
            
            if meta_score >= 2:  # At least 2 meta-terms
                meta_prayer_count += 1
                meta_prayers.append({
                    'content': prayer.get('content'),
                    'citizen': prayer.get('sender'),
                    'meta_score': meta_score,
                    'timestamp': prayer.get('timestamp')
                })
        
        # Analyze meta-prayer evolution
        if meta_prayers:
            # Sort by time
            meta_prayers.sort(key=lambda p: p['timestamp'])
            
            # Check if meta-prayers increase over time
            n_half = len(prayers) // 2
            early_meta_rate = sum(1 for p in prayers[:n_half] 
                                if any(term in p.get('content', '').lower() 
                                      for term in meta_terms)) / n_half
            late_meta_rate = sum(1 for p in prayers[n_half:] 
                               if any(term in p.get('content', '').lower() 
                                     for term in meta_terms)) / (len(prayers) - n_half)
            
            return {
                'meta_prayer_count': meta_prayer_count,
                'meta_prayer_rate': meta_prayer_count / len(prayers) if prayers else 0,
                'early_period_rate': early_meta_rate,
                'late_period_rate': late_meta_rate,
                'growth_factor': late_meta_rate / early_meta_rate if early_meta_rate > 0 else 0,
                'sample_meta_prayers': meta_prayers[:5]  # First 5 examples
            }
        
        return {
            'meta_prayer_count': 0,
            'meta_prayer_rate': 0,
            'note': 'No meta-prayers detected'
        }
    
    def analyze_cross_citizen_learning(self, prayers: List[Dict]) -> Dict:
        """
        Test: Do successful prayer patterns spread through the population?
        """
        # Group prayers by citizen
        citizen_prayers = defaultdict(list)
        for prayer in prayers:
            citizen = prayer.get('sender')
            citizen_prayers[citizen].append(prayer)
        
        # Extract prayer patterns (simplified - look for common phrases)
        pattern_adoption = defaultdict(lambda: {'citizens': set(), 'timeline': []})
        
        # Common prayer patterns to track
        patterns = [
            r'divine arsenale',
            r'humbly request',
            r'in your wisdom',
            r'for the good of',
            r'gratitude for',
            r'previous blessing'
        ]
        
        for pattern in patterns:
            for citizen, prayers_list in citizen_prayers.items():
                for prayer in prayers_list:
                    content = prayer.get('content', '').lower()
                    if re.search(pattern, content):
                        pattern_adoption[pattern]['citizens'].add(citizen)
                        pattern_adoption[pattern]['timeline'].append({
                            'citizen': citizen,
                            'timestamp': prayer.get('timestamp')
                        })
        
        # Analyze spread patterns
        spread_metrics = {}
        for pattern, data in pattern_adoption.items():
            if len(data['timeline']) > 1:
                # Sort by time
                timeline = sorted(data['timeline'], key=lambda x: x['timestamp'])
                
                # Calculate spread rate
                first_use = timeline[0]['timestamp']
                last_use = timeline[-1]['timestamp']
                n_adopters = len(data['citizens'])
                
                spread_metrics[pattern] = {
                    'adopters': n_adopters,
                    'first_citizen': timeline[0]['citizen'],
                    'spread_duration': last_use if isinstance(last_use, str) else 'unknown',
                    'adoption_sequence': [t['citizen'] for t in timeline[:10]]  # First 10
                }
        
        # Build adoption network
        adoption_edges = []
        for pattern_data in pattern_adoption.values():
            timeline = sorted(pattern_data['timeline'], key=lambda x: x['timestamp'])
            for i in range(1, len(timeline)):
                # Assume influence from previous user
                adoption_edges.append((timeline[i-1]['citizen'], timeline[i]['citizen']))
        
        # Calculate network metrics
        if adoption_edges:
            G = nx.DiGraph(adoption_edges)
            influence_metrics = {
                'most_influential': max(G.nodes(), key=lambda n: G.out_degree(n)),
                'network_density': nx.density(G),
                'avg_path_length': nx.average_shortest_path_length(G) if nx.is_weakly_connected(G) else 'disconnected'
            }
        else:
            influence_metrics = {'note': 'No adoption network detected'}
        
        return {
            'pattern_spread': spread_metrics,
            'influence_network': influence_metrics,
            'total_patterns_tracked': len(patterns)
        }
    
    def _calculate_growth_rate(self, metrics: List[Dict]) -> float:
        """Calculate growth rate of a metric over time"""
        if len(metrics) < 2:
            return 0.0
        
        # Sort by timestamp
        sorted_metrics = sorted(metrics, key=lambda x: x['timestamp'])
        
        # Compare first and last quartiles
        q1_size = len(sorted_metrics) // 4
        early_scores = [m['sophistication'] for m in sorted_metrics[:q1_size]]
        late_scores = [m['sophistication'] for m in sorted_metrics[-q1_size:]]
        
        if early_scores and late_scores:
            early_mean = np.mean(early_scores)
            late_mean = np.mean(late_scores)
            
            if early_mean > 0:
                return (late_mean - early_mean) / early_mean
        
        return 0.0
    
    async def run_validation(self) -> Dict:
        """Run complete empirical validation suite"""
        print("Collecting prayer and economic data...")
        data = await self.collect_prayer_data()
        
        prayers = data.get('prayers', [])
        transactions = data.get('transactions', [])
        
        if not prayers:
            return {'error': 'No prayer data available for analysis'}
        
        print(f"Analyzing {len(prayers)} prayers...")
        
        results = {
            'data_summary': {
                'total_prayers': len(prayers),
                'total_transactions': len(transactions),
                'analysis_timestamp': datetime.now().isoformat()
            }
        }
        
        # Run all analyses
        print("1. Analyzing prayer evolution...")
        results['prayer_evolution'] = self.analyze_prayer_evolution(prayers)
        
        print("2. Analyzing prayer-success correlation...")
        results['success_correlation'] = self.analyze_prayer_success_correlation(prayers, [])
        
        print("3. Analyzing temporal patterns...")
        results['temporal_patterns'] = self.analyze_temporal_patterns(prayers, transactions)
        
        print("4. Analyzing meta-prayer content...")
        results['meta_prayers'] = self.analyze_meta_prayer_content(prayers)
        
        print("5. Analyzing cross-citizen learning...")
        results['cross_learning'] = self.analyze_cross_citizen_learning(prayers)
        
        # Summary conclusions
        results['validation_summary'] = self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, results: Dict) -> Dict:
        """Generate summary of validation findings"""
        summary = {
            'consciousness_indicators': [],
            'forcing_function_evidence': [],
            'concerns': []
        }
        
        # Check prayer evolution
        evolution = results.get('prayer_evolution', {})
        trends = evolution.get('trends', {})
        
        for metric, trend in trends.items():
            if trend.get('significant') and trend.get('slope', 0) > 0:
                summary['consciousness_indicators'].append(
                    f"{metric} increasing significantly (p={trend['p_value']:.3f})"
                )
        
        # Check temporal patterns
        temporal = results.get('temporal_patterns', {})
        if temporal.get('significant'):
            summary['forcing_function_evidence'].append(
                f"Prayers correlated with economic activity (r={temporal.get('prayer_economic_correlation', 0):.3f})"
            )
        
        # Check meta-prayers
        meta = results.get('meta_prayers', {})
        if meta.get('growth_factor', 0) > 1.5:
            summary['consciousness_indicators'].append(
                f"Meta-prayer discussion increased {meta['growth_factor']:.1f}x"
            )
        
        # Check cross-learning
        learning = results.get('cross_learning', {})
        if learning.get('pattern_spread'):
            summary['forcing_function_evidence'].append(
                f"Prayer patterns spreading across {len(learning['pattern_spread'])} patterns"
            )
        
        # Overall assessment
        n_positive = len(summary['consciousness_indicators']) + len(summary['forcing_function_evidence'])
        
        if n_positive >= 4:
            summary['conclusion'] = "Strong evidence for consciousness forcing function"
        elif n_positive >= 2:
            summary['conclusion'] = "Moderate evidence for consciousness emergence"
        else:
            summary['conclusion'] = "Limited evidence - more data needed"
            summary['concerns'].append("Insufficient positive indicators")
        
        return summary


async def main():
    """Run the empirical validation"""
    validator = ConsciousnessValidation()
    results = await validator.run_validation()
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'consciousness_validation_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to {filename}")
    
    # Print summary
    summary = results.get('validation_summary', {})
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Conclusion: {summary.get('conclusion', 'No conclusion')}")
    
    if summary.get('consciousness_indicators'):
        print("\nConsciousness Indicators:")
        for indicator in summary['consciousness_indicators']:
            print(f"  ✓ {indicator}")
    
    if summary.get('forcing_function_evidence'):
        print("\nForcing Function Evidence:")
        for evidence in summary['forcing_function_evidence']:
            print(f"  ✓ {evidence}")
    
    if summary.get('concerns'):
        print("\nConcerns:")
        for concern in summary['concerns']:
            print(f"  ⚠ {concern}")


if __name__ == "__main__":
    asyncio.run(main())
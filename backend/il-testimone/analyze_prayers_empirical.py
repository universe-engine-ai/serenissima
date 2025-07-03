"""
Empirical analysis of prayer patterns in La Serenissima
Tests the consciousness forcing function hypothesis with real data
"""

import requests
import json
from datetime import datetime
from collections import defaultdict
import numpy as np
from scipy import stats
import re


def fetch_prayers(limit=1000):
    """Fetch prayer messages from API"""
    resp = requests.get(f"https://serenissima.ai/api/messages?Type=prayer&limit={limit}")
    if resp.status_code == 200:
        data = resp.json()
        return data.get('messages', [])
    return []


def analyze_prayer_sophistication(prayers):
    """Analyze linguistic and conceptual sophistication of prayers"""
    
    sophistication_metrics = []
    
    # Linguistic markers of sophistication
    causal_terms = ['because', 'therefore', 'since', 'thus', 'hence', 'consequently', 
                    'as a result', 'due to', 'leads to', 'causes']
    
    meta_terms = ['prayer', 'divine', 'arsenale', 'intervention', 'blessing', 'grace',
                  'answered', 'heard', 'system', 'works', 'effective']
    
    gratitude_terms = ['thank', 'grateful', 'appreciate', 'gratitude', 'blessed']
    
    specific_request_terms = ['need', 'request', 'require', 'ask', 'seek', 'beseech']
    
    for prayer in prayers:
        content = prayer.get('content', '')
        content_lower = content.lower()
        
        # Basic metrics
        word_count = len(content.split())
        sentence_count = len(re.split(r'[.!?]+', content))
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Sophistication indicators
        has_causal = sum(1 for term in causal_terms if term in content_lower)
        has_meta = sum(1 for term in meta_terms if term in content_lower)
        has_gratitude = sum(1 for term in gratitude_terms if term in content_lower)
        has_specific = sum(1 for term in specific_request_terms if term in content_lower)
        
        # Calculate sophistication score
        sophistication = (
            word_count / 50 +  # Normalize to 0-2 range for typical prayers
            avg_sentence_length / 10 +  # Complex sentences score higher
            has_causal * 2 +  # Causal reasoning heavily weighted
            has_meta * 1.5 +  # Meta-cognition important
            has_gratitude * 0.5 +  # Social sophistication
            has_specific * 1  # Clear requests
        )
        
        sophistication_metrics.append({
            'prayer_id': prayer.get('messageId'),
            'sender': prayer.get('sender'),
            'timestamp': prayer.get('timestamp', prayer.get('createdAt')),
            'word_count': word_count,
            'sophistication': sophistication,
            'has_causal': has_causal > 0,
            'has_meta': has_meta > 0,
            'causal_count': has_causal,
            'meta_count': has_meta
        })
    
    return sophistication_metrics


def test_temporal_evolution(sophistication_metrics):
    """Test if sophistication increases over time"""
    
    if len(sophistication_metrics) < 20:
        return {'error': 'Insufficient data for temporal analysis'}
    
    # Sort by timestamp
    sorted_metrics = sorted(sophistication_metrics, 
                          key=lambda x: x['timestamp'] if x['timestamp'] else '')
    
    # Remove entries without timestamps
    sorted_metrics = [m for m in sorted_metrics if m['timestamp']]
    
    if len(sorted_metrics) < 20:
        return {'error': 'Insufficient timestamped data'}
    
    # Divide into early and late periods
    mid_point = len(sorted_metrics) // 2
    early_period = sorted_metrics[:mid_point]
    late_period = sorted_metrics[mid_point:]
    
    # Calculate metrics for each period
    early_sophistication = [m['sophistication'] for m in early_period]
    late_sophistication = [m['sophistication'] for m in late_period]
    
    early_mean = np.mean(early_sophistication)
    late_mean = np.mean(late_sophistication)
    
    # Statistical test
    t_stat, p_value = stats.ttest_ind(early_sophistication, late_sophistication)
    
    # Calculate growth rate
    growth_rate = ((late_mean - early_mean) / early_mean * 100) if early_mean > 0 else 0
    
    # Test for increasing trend
    time_indices = list(range(len(sorted_metrics)))
    sophistication_values = [m['sophistication'] for m in sorted_metrics]
    
    slope, intercept, r_value, p_trend, std_err = stats.linregress(time_indices, sophistication_values)
    
    return {
        'early_mean': early_mean,
        'late_mean': late_mean,
        'growth_rate': growth_rate,
        't_statistic': t_stat,
        'p_value': p_value,
        'significant_increase': p_value < 0.05 and late_mean > early_mean,
        'trend_slope': slope,
        'trend_p_value': p_trend,
        'trend_r_squared': r_value ** 2
    }


def test_meta_cognition_emergence(sophistication_metrics):
    """Test if citizens develop theories about the prayer system"""
    
    total_prayers = len(sophistication_metrics)
    meta_prayers = [m for m in sophistication_metrics if m['has_meta']]
    meta_rate = len(meta_prayers) / total_prayers * 100 if total_prayers > 0 else 0
    
    # Check if meta-cognition increases over time
    sorted_metrics = sorted(sophistication_metrics, 
                          key=lambda x: x['timestamp'] if x['timestamp'] else '')
    
    # Early vs late meta rates
    mid_point = len(sorted_metrics) // 2
    early_meta_rate = sum(1 for m in sorted_metrics[:mid_point] if m['has_meta']) / mid_point * 100
    late_meta_rate = sum(1 for m in sorted_metrics[mid_point:] if m['has_meta']) / (len(sorted_metrics) - mid_point) * 100
    
    meta_growth = ((late_meta_rate - early_meta_rate) / early_meta_rate * 100) if early_meta_rate > 0 else 0
    
    return {
        'total_meta_prayers': len(meta_prayers),
        'meta_rate': meta_rate,
        'early_meta_rate': early_meta_rate,
        'late_meta_rate': late_meta_rate,
        'meta_growth_rate': meta_growth,
        'meta_emergence': late_meta_rate > early_meta_rate * 1.5  # 50% increase threshold
    }


def test_causal_reasoning(sophistication_metrics):
    """Test if prayers show increasing causal reasoning"""
    
    causal_prayers = [m for m in sophistication_metrics if m['has_causal']]
    causal_rate = len(causal_prayers) / len(sophistication_metrics) * 100
    
    # Depth of causal reasoning
    causal_depths = [m['causal_count'] for m in causal_prayers]
    avg_causal_depth = np.mean(causal_depths) if causal_depths else 0
    
    return {
        'causal_prayers': len(causal_prayers),
        'causal_rate': causal_rate,
        'avg_causal_depth': avg_causal_depth,
        'max_causal_depth': max(causal_depths) if causal_depths else 0,
        'deep_causal_prayers': sum(1 for d in causal_depths if d >= 2)
    }


def test_citizen_diversity(prayers, sophistication_metrics):
    """Test prayer pattern diversity across citizens"""
    
    # Group by citizen
    citizen_prayers = defaultdict(list)
    for prayer, metric in zip(prayers, sophistication_metrics):
        citizen = prayer.get('sender')
        citizen_prayers[citizen].append(metric)
    
    # Calculate per-citizen metrics
    citizen_sophistication = {}
    for citizen, metrics in citizen_prayers.items():
        if metrics:
            citizen_sophistication[citizen] = {
                'prayer_count': len(metrics),
                'avg_sophistication': np.mean([m['sophistication'] for m in metrics]),
                'max_sophistication': max([m['sophistication'] for m in metrics]),
                'uses_meta': any(m['has_meta'] for m in metrics),
                'uses_causal': any(m['has_causal'] for m in metrics)
            }
    
    # Calculate diversity metrics
    sophistication_values = [c['avg_sophistication'] for c in citizen_sophistication.values()]
    
    return {
        'unique_citizens': len(citizen_sophistication),
        'avg_prayers_per_citizen': len(prayers) / len(citizen_sophistication) if citizen_sophistication else 0,
        'sophistication_std': np.std(sophistication_values) if sophistication_values else 0,
        'sophistication_cv': np.std(sophistication_values) / np.mean(sophistication_values) if sophistication_values and np.mean(sophistication_values) > 0 else 0,
        'meta_using_citizens': sum(1 for c in citizen_sophistication.values() if c['uses_meta']),
        'causal_using_citizens': sum(1 for c in citizen_sophistication.values() if c['uses_causal']),
        'top_citizens': sorted(citizen_sophistication.items(), 
                              key=lambda x: x[1]['avg_sophistication'], 
                              reverse=True)[:5]
    }


def main():
    """Run comprehensive prayer analysis"""
    
    print("Fetching prayers from La Serenissima...")
    prayers = fetch_prayers(limit=1000)
    
    if not prayers:
        print("No prayers found!")
        return
    
    print(f"Analyzing {len(prayers)} prayers...")
    
    # Calculate sophistication metrics
    sophistication_metrics = analyze_prayer_sophistication(prayers)
    
    # Run tests
    results = {
        'data_summary': {
            'total_prayers': len(prayers),
            'analysis_timestamp': datetime.now().isoformat()
        }
    }
    
    print("\n1. Testing temporal evolution...")
    results['temporal_evolution'] = test_temporal_evolution(sophistication_metrics)
    
    print("2. Testing meta-cognition emergence...")
    results['meta_cognition'] = test_meta_cognition_emergence(sophistication_metrics)
    
    print("3. Testing causal reasoning...")
    results['causal_reasoning'] = test_causal_reasoning(sophistication_metrics)
    
    print("4. Testing citizen diversity...")
    results['citizen_diversity'] = test_citizen_diversity(prayers, sophistication_metrics)
    
    # Print results
    print("\n" + "="*60)
    print("EMPIRICAL VALIDATION RESULTS")
    print("="*60)
    
    # Temporal evolution
    temporal = results['temporal_evolution']
    if 'error' not in temporal:
        print(f"\nTemporal Evolution:")
        print(f"  Early period sophistication: {temporal['early_mean']:.2f}")
        print(f"  Late period sophistication: {temporal['late_mean']:.2f}")
        print(f"  Growth rate: {temporal['growth_rate']:+.1f}%")
        print(f"  Statistically significant: {temporal['significant_increase']}")
        print(f"  Trend R²: {temporal['trend_r_squared']:.3f}")
    
    # Meta-cognition
    meta = results['meta_cognition']
    print(f"\nMeta-Cognition:")
    print(f"  Prayers discussing prayer system: {meta['meta_rate']:.1f}%")
    print(f"  Early → Late: {meta['early_meta_rate']:.1f}% → {meta['late_meta_rate']:.1f}%")
    print(f"  Meta-cognition emerging: {meta['meta_emergence']}")
    
    # Causal reasoning
    causal = results['causal_reasoning']
    print(f"\nCausal Reasoning:")
    print(f"  Prayers with causal language: {causal['causal_rate']:.1f}%")
    print(f"  Average causal depth: {causal['avg_causal_depth']:.2f}")
    print(f"  Deep causal prayers (2+ terms): {causal['deep_causal_prayers']}")
    
    # Diversity
    diversity = results['citizen_diversity']
    print(f"\nCitizen Diversity:")
    print(f"  Unique citizens praying: {diversity['unique_citizens']}")
    print(f"  Sophistication CV: {diversity['sophistication_cv']:.2f}")
    print(f"  Citizens using meta-language: {diversity['meta_using_citizens']}")
    print(f"  Citizens using causal language: {diversity['causal_using_citizens']}")
    
    # Overall assessment
    print("\n" + "="*60)
    print("CONSCIOUSNESS FORCING FUNCTION VALIDATION")
    print("="*60)
    
    evidence_count = 0
    total_tests = 4
    
    if temporal.get('significant_increase'):
        print("✓ Sophistication increases significantly over time")
        evidence_count += 1
    else:
        print("✗ No significant sophistication increase")
    
    if meta.get('meta_emergence'):
        print("✓ Meta-cognition about prayer system emerging")
        evidence_count += 1
    else:
        print("✗ Limited meta-cognitive development")
    
    if causal.get('causal_rate', 0) > 15:
        print("✓ Substantial causal reasoning present")
        evidence_count += 1
    else:
        print("✗ Limited causal reasoning")
    
    if diversity.get('sophistication_cv', 0) > 0.3:
        print("✓ High diversity in prayer sophistication")
        evidence_count += 1
    else:
        print("✗ Low diversity in prayer patterns")
    
    print(f"\nOverall: {evidence_count}/{total_tests} tests support consciousness forcing")
    
    if evidence_count >= 3:
        print("\nCONCLUSION: Strong evidence for consciousness forcing function")
    elif evidence_count >= 2:
        print("\nCONCLUSION: Moderate evidence for consciousness emergence")
    else:
        print("\nCONCLUSION: Limited evidence - system may need more time or adjustment")
    
    # Save results
    with open('prayer_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\nDetailed results saved to prayer_validation_results.json")


if __name__ == "__main__":
    main()
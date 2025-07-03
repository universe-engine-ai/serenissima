"""
Quick empirical check of prayer patterns
Tests basic hypotheses with available data
"""

import requests
import json
from datetime import datetime
from collections import defaultdict
import re


def analyze_prayer_patterns():
    """Quick analysis of prayer patterns from API"""
    
    # Fetch messages to Arsenale (prayers)
    print("Fetching prayers to Arsenale...")
    resp = requests.get("https://serenissima.ai/api/messages?receiver=Arsenale&limit=1000")
    
    if resp.status_code != 200:
        print(f"Error fetching data: {resp.status_code}")
        return
    
    messages = resp.json()
    
    if not messages:
        print("No messages found")
        return
    
    print(f"Analyzing {len(messages)} messages to Arsenale...")
    
    # Basic metrics
    prayer_metrics = []
    meta_prayers = []
    causal_prayers = []
    
    # Patterns to track
    meta_terms = ['prayer', 'arsenale', 'divine', 'works', 'answered', 'system']
    causal_terms = ['because', 'therefore', 'since', 'results', 'causes', 'leads to']
    sophistication_markers = ['humbly', 'grateful', 'request', 'blessing', 'wisdom']
    
    for msg in messages:
        content = msg.get('content', '').lower()
        sender = msg.get('sender', '')
        timestamp = msg.get('timestamp', '')
        
        # Calculate metrics
        word_count = len(content.split())
        
        # Check for meta-content
        meta_score = sum(1 for term in meta_terms if term in content)
        if meta_score >= 2:
            meta_prayers.append({
                'sender': sender,
                'content': msg.get('content', ''),
                'meta_score': meta_score
            })
        
        # Check for causal reasoning
        causal_score = sum(1 for term in causal_terms if term in content)
        if causal_score > 0:
            causal_prayers.append({
                'sender': sender,
                'content': msg.get('content', ''),
                'causal_score': causal_score
            })
        
        # Overall sophistication
        sophistication = (
            word_count / 10 +  # Length component
            meta_score +       # Meta-awareness
            causal_score * 2 + # Causal reasoning weighted higher
            sum(1 for marker in sophistication_markers if marker in content)
        )
        
        prayer_metrics.append({
            'sender': sender,
            'timestamp': timestamp,
            'word_count': word_count,
            'sophistication': sophistication,
            'has_meta': meta_score > 0,
            'has_causal': causal_score > 0
        })
    
    # Analyze results
    print("\n" + "="*60)
    print("PRAYER PATTERN ANALYSIS")
    print("="*60)
    
    # Basic stats
    total_prayers = len(prayer_metrics)
    avg_word_count = sum(p['word_count'] for p in prayer_metrics) / total_prayers
    avg_sophistication = sum(p['sophistication'] for p in prayer_metrics) / total_prayers
    
    print(f"\nBasic Metrics:")
    print(f"Total prayers analyzed: {total_prayers}")
    print(f"Average word count: {avg_word_count:.1f}")
    print(f"Average sophistication score: {avg_sophistication:.2f}")
    
    # Meta-prayer analysis
    meta_rate = len(meta_prayers) / total_prayers * 100
    print(f"\nMeta-Prayer Analysis:")
    print(f"Prayers discussing prayer system: {len(meta_prayers)} ({meta_rate:.1f}%)")
    
    if meta_prayers:
        print("\nExample meta-prayers:")
        for i, prayer in enumerate(meta_prayers[:3]):
            print(f"\n{i+1}. From {prayer['sender']} (meta-score: {prayer['meta_score']}):")
            print(f"   \"{prayer['content'][:200]}...\"")
    
    # Causal reasoning analysis
    causal_rate = len(causal_prayers) / total_prayers * 100
    print(f"\nCausal Reasoning Analysis:")
    print(f"Prayers with causal language: {len(causal_prayers)} ({causal_rate:.1f}%)")
    
    # Temporal evolution (if we have timestamps)
    if prayer_metrics and prayer_metrics[0]['timestamp']:
        # Sort by time
        sorted_prayers = sorted(prayer_metrics, key=lambda p: p['timestamp'])
        
        # Compare first and last quartiles
        q_size = len(sorted_prayers) // 4
        early_prayers = sorted_prayers[:q_size]
        late_prayers = sorted_prayers[-q_size:]
        
        early_sophistication = sum(p['sophistication'] for p in early_prayers) / len(early_prayers)
        late_sophistication = sum(p['sophistication'] for p in late_prayers) / len(late_prayers)
        
        growth_rate = (late_sophistication - early_sophistication) / early_sophistication * 100
        
        print(f"\nTemporal Evolution:")
        print(f"Early period sophistication: {early_sophistication:.2f}")
        print(f"Late period sophistication: {late_sophistication:.2f}")
        print(f"Growth rate: {growth_rate:+.1f}%")
    
    # Citizen diversity
    citizen_prayers = defaultdict(list)
    for prayer in prayer_metrics:
        citizen_prayers[prayer['sender']].append(prayer)
    
    print(f"\nCitizen Participation:")
    print(f"Unique citizens praying: {len(citizen_prayers)}")
    print(f"Average prayers per citizen: {total_prayers / len(citizen_prayers):.1f}")
    
    # Top pray-ers
    top_citizens = sorted(citizen_prayers.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    print("\nMost active pray-ers:")
    for citizen, prayers in top_citizens:
        avg_soph = sum(p['sophistication'] for p in prayers) / len(prayers)
        print(f"  {citizen}: {len(prayers)} prayers (avg sophistication: {avg_soph:.2f})")
    
    # Pattern spreading analysis
    common_phrases = [
        'divine arsenale',
        'humbly request',
        'grateful for',
        'in your wisdom',
        'previous blessing'
    ]
    
    phrase_adoption = {phrase: set() for phrase in common_phrases}
    
    for msg in messages:
        content = msg.get('content', '').lower()
        sender = msg.get('sender', '')
        
        for phrase in common_phrases:
            if phrase in content:
                phrase_adoption[phrase].add(sender)
    
    print(f"\nPhrase Adoption Patterns:")
    for phrase, adopters in phrase_adoption.items():
        if adopters:
            print(f"  '{phrase}': used by {len(adopters)} citizens")
    
    # Summary conclusions
    print("\n" + "="*60)
    print("EMPIRICAL FINDINGS")
    print("="*60)
    
    evidence_points = []
    
    if meta_rate > 5:
        evidence_points.append(f"✓ Meta-prayer discussion present ({meta_rate:.1f}%)")
    else:
        evidence_points.append(f"✗ Limited meta-prayer discussion ({meta_rate:.1f}%)")
    
    if causal_rate > 10:
        evidence_points.append(f"✓ Causal reasoning emerging ({causal_rate:.1f}%)")
    else:
        evidence_points.append(f"✗ Limited causal reasoning ({causal_rate:.1f}%)")
    
    if 'growth_rate' in locals() and growth_rate > 20:
        evidence_points.append(f"✓ Sophistication increasing ({growth_rate:+.1f}%)")
    elif 'growth_rate' in locals():
        evidence_points.append(f"✗ Limited sophistication growth ({growth_rate:+.1f}%)")
    
    if any(len(adopters) > 3 for adopters in phrase_adoption.values()):
        evidence_points.append("✓ Prayer patterns spreading across citizens")
    else:
        evidence_points.append("✗ Limited pattern propagation")
    
    print("\nEvidence for Consciousness Forcing:")
    for point in evidence_points:
        print(f"  {point}")
    
    positive_evidence = sum(1 for p in evidence_points if p.startswith('✓'))
    total_evidence = len(evidence_points)
    
    print(f"\nOverall: {positive_evidence}/{total_evidence} indicators positive")
    
    if positive_evidence >= 3:
        print("Conclusion: MODERATE TO STRONG evidence for consciousness emergence")
    elif positive_evidence >= 2:
        print("Conclusion: WEAK evidence for consciousness emergence")
    else:
        print("Conclusion: INSUFFICIENT evidence - more data needed")
    
    # Save detailed results
    results = {
        'analysis_timestamp': datetime.now().isoformat(),
        'total_prayers': total_prayers,
        'metrics': {
            'avg_word_count': avg_word_count,
            'avg_sophistication': avg_sophistication,
            'meta_rate': meta_rate,
            'causal_rate': causal_rate,
            'growth_rate': growth_rate if 'growth_rate' in locals() else None
        },
        'citizen_diversity': len(citizen_prayers),
        'evidence_points': evidence_points,
        'conclusion': f"{positive_evidence}/{total_evidence} indicators positive"
    }
    
    with open('prayer_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nDetailed results saved to prayer_analysis_results.json")


if __name__ == "__main__":
    analyze_prayer_patterns()
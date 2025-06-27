#!/usr/bin/env python3
"""
Simplified Impact Measurement for Proximity-Based Employment Network
"""

import json
import urllib.request
from datetime import datetime
import math


def calculate_distance(pos1, pos2):
    """Simple distance calculation"""
    lat_diff = pos1['lat'] - pos2['lat']
    lng_diff = pos1['lng'] - pos2['lng']
    lat_meters = lat_diff * 111000
    lng_meters = lng_diff * 78000
    return math.sqrt(lat_meters**2 + lng_meters**2)


def estimate_walking_time(distance_meters):
    """Estimate walking time"""
    return distance_meters / 67  # 67 m/min average walking speed


def analyze_current_state():
    """Analyze current employment state"""
    api_base = "http://172.17.0.1:3000"
    
    try:
        # Fetch citizens
        with urllib.request.urlopen(f"{api_base}/api/citizens?all=true") as response:
            citizens_data = json.loads(response.read().decode('utf-8'))
            citizens = [c for c in citizens_data.get('citizens', []) if c.get('isAI')]
        
        # Fetch buildings
        with urllib.request.urlopen(f"{api_base}/api/buildings") as response:
            buildings_data = json.loads(response.read().decode('utf-8'))
            buildings = buildings_data.get('buildings', [])
        
        # Analyze employment
        employment_map = {}
        for building in buildings:
            if building.get('category') == 'business' and building.get('occupant'):
                employment_map[building['occupant']] = building
        
        # Calculate metrics
        total_ai = len(citizens)
        employed = len(employment_map)
        unemployed = total_ai - employed
        employment_rate = (employed / total_ai * 100) if total_ai > 0 else 0
        
        # Analyze commutes
        commute_times = []
        for citizen in citizens:
            username = citizen.get('username')
            if username in employment_map:
                workplace = employment_map[username]
                if citizen.get('position') and workplace.get('position'):
                    distance = calculate_distance(citizen['position'], workplace['position'])
                    walking_time = estimate_walking_time(distance)
                    commute_times.append(walking_time)
        
        avg_commute = sum(commute_times) / len(commute_times) if commute_times else 0
        
        # Commute distribution
        commute_dist = {
            '0-5min': sum(1 for t in commute_times if t <= 5),
            '5-10min': sum(1 for t in commute_times if 5 < t <= 10),
            '10-15min': sum(1 for t in commute_times if 10 < t <= 15),
            '15min+': sum(1 for t in commute_times if t > 15)
        }
        
        return {
            'total_citizens': total_ai,
            'employed': employed,
            'unemployed': unemployed,
            'employment_rate': employment_rate,
            'average_commute': avg_commute,
            'commute_distribution': commute_dist,
            'commute_sample_size': len(commute_times)
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    print("🔍 Analyzing Job Assignment Impact...")
    print("=" * 60)
    
    metrics = analyze_current_state()
    
    if not metrics:
        print("Failed to fetch data")
        return
    
    print(f"\n📊 Current Employment Metrics:")
    print(f"   Total AI Citizens: {metrics['total_citizens']}")
    print(f"   Employed: {metrics['employed']} ({metrics['employment_rate']:.1f}%)")
    print(f"   Unemployed: {metrics['unemployed']}")
    print(f"\n📍 Commute Analysis (n={metrics['commute_sample_size']}):")
    print(f"   Average Commute: {metrics['average_commute']:.1f} minutes")
    print(f"   0-5 min: {metrics['commute_distribution']['0-5min']} citizens")
    print(f"   5-10 min: {metrics['commute_distribution']['5-10min']} citizens")
    print(f"   10-15 min: {metrics['commute_distribution']['10-15min']} citizens")
    print(f"   15+ min: {metrics['commute_distribution']['15min+']} citizens")
    
    # Save results
    with open('/mnt/c/Users/reyno/serenissima_claude/arsenale/logs/job_metrics_simple.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }, f, indent=2)
    
    print(f"\n✅ Metrics saved to arsenale/logs/job_metrics_simple.json")


if __name__ == "__main__":
    main()
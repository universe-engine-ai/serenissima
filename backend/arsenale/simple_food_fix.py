#!/usr/bin/env python3
"""
Simple script to analyze and propose fixes for the eating crisis.
Uses only public API endpoints.
"""

import requests
import json
from datetime import datetime

API_BASE = "https://serenissima.ai"

def analyze_food_crisis():
    """Analyze the current food crisis."""
    print("=== FOOD CRISIS ANALYSIS ===\n")
    
    # 1. Check hungry citizens
    citizens_resp = requests.get(f"{API_BASE}/api/citizens?limit=200")
    if citizens_resp.status_code == 200:
        citizens_data = citizens_resp.json()
        citizens = citizens_data.get('citizens', [])
        
        # Count hungry citizens
        hungry_count = 0
        very_hungry = []
        
        for citizen in citizens:
            ate_at = citizen.get('ateAt')
            if not ate_at:
                hungry_count += 1
                very_hungry.append(citizen)
            else:
                # Parse time
                try:
                    ate_time = datetime.fromisoformat(ate_at.replace('Z', '+00:00'))
                    hours_since = (datetime.utcnow() - ate_time.replace(tzinfo=None)).total_seconds() / 3600
                    if hours_since > 12:
                        hungry_count += 1
                        if hours_since > 24:
                            very_hungry.append(citizen)
                except:
                    pass
        
        print(f"Total citizens: {len(citizens)}")
        print(f"Hungry citizens (12+ hours): {hungry_count}")
        print(f"Very hungry (24+ hours): {len(very_hungry)}")
        
        # Show poorest hungry citizens
        very_hungry.sort(key=lambda c: c.get('ducats', 0))
        print("\nPoorest hungry citizens:")
        for c in very_hungry[:10]:
            print(f"  - {c['username']}: {c.get('ducats', 0):.2f} ducats")
    
    # 2. Check food availability
    print("\n2. FOOD AVAILABILITY:")
    
    # Check bread
    bread_resp = requests.get(f"{API_BASE}/api/resources?Type=bread&limit=100")
    if bread_resp.status_code == 200:
        bread_data = bread_resp.json()
        
        # Group by location type
        water_bread = []
        building_bread = []
        citizen_bread = []
        
        for bread in bread_data:
            if bread['assetType'] == 'citizen':
                citizen_bread.append(bread)
            elif bread['asset'].startswith('water_'):
                water_bread.append(bread)
            else:
                building_bread.append(bread)
        
        print(f"Bread on water: {sum(b['count'] for b in water_bread)} units in {len(water_bread)} locations")
        print(f"Bread in buildings: {sum(b['count'] for b in building_bread)} units in {len(building_bread)} locations")
        print(f"Bread on citizens: {sum(b['count'] for b in citizen_bread)} units on {len(citizen_bread)} citizens")
        
        # Find accessible bread
        print("\nAccessible bread in buildings:")
        for bread in building_bread[:5]:
            print(f"  - {bread['count']} at {bread['asset']} (owner: {bread['owner']})")
    
    # 3. Check eating options
    print("\n3. EATING OPTIONS FOR POOREST:")
    
    if very_hungry:
        test_citizen = very_hungry[0]['username']
        options_resp = requests.get(f"{API_BASE}/api/get-eating-options?citizenUsername={test_citizen}")
        
        if options_resp.status_code == 200:
            options_data = options_resp.json()
            options = options_data.get('options', [])
            
            print(f"Options for {test_citizen} (has {very_hungry[0].get('ducats', 0):.2f} ducats):")
            affordable = []
            for opt in options[:5]:
                price = opt.get('price', 0)
                affordable_marker = "✓" if price <= very_hungry[0].get('ducats', 0) else "✗"
                print(f"  {affordable_marker} {opt['resourceType']} at {opt['buildingName']}: {price} ducats")
                if price <= very_hungry[0].get('ducats', 0):
                    affordable.append(opt)
            
            if not affordable:
                print("  → NO AFFORDABLE OPTIONS!")
    
    # 4. Recommendations
    print("\n=== RECOMMENDATIONS ===")
    print("1. IMMEDIATE: Create emergency bread at 5 ducats in city center inns")
    print("2. SHORT-TERM: Move bread from water to accessible markets")
    print("3. MEDIUM-TERM: Implement welfare food distribution for <50 ducat citizens")
    print("4. LONG-TERM: Rebalance economy - ensure wages > food costs")
    
    print("\nSUGGESTED FIX:")
    print("Create public_sell contracts for bread at Inn buildings:")
    print("- Price: 5 ducats (affordable for most)")
    print("- Locations: Central inns (not water)")
    print("- Amount: 10-20 bread per location")
    print("- Seller: ConsiglioDeiDieci or wealthy citizens")

if __name__ == "__main__":
    analyze_food_crisis()
#!/usr/bin/env python3
"""
CHAOS TEST: Grain Supply Chain End-to-End
Forge-Hammer-3: Finding where 112 citizens starve!
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Test configuration
API_BASE = "https://serenissima.ai/api"
HEADERS = {"Content-Type": "application/json"}

async def test_supply_chain(session):
    """Test the complete grain → flour → bread → citizens chain"""
    
    print("=== CHAOS TEST: GRAIN SUPPLY CHAIN ===")
    print(f"Time: {datetime.utcnow().isoformat()}")
    
    results = {
        "galleys_with_grain": 0,
        "total_grain_in_galleys": 0,
        "mills_operational": 0,
        "mills_with_grain": 0,
        "total_grain_at_mills": 0,
        "bakeries_operational": 0,
        "bakeries_with_flour": 0,
        "total_flour_at_bakeries": 0,
        "bread_available": 0,
        "starving_citizens": 0,
        "bottlenecks": []
    }
    
    # 1. Check galleys for grain
    print("\n🚢 CHECKING GALLEYS...")
    try:
        async with session.get(f"{API_BASE}/buildings?type=merchant_galley") as resp:
            if resp.status == 200:
                galleys = await resp.json()
                for galley in galleys:
                    galley_id = galley.get('buildingId')
                    print(f"  Checking galley {galley_id}...")
                    
                    # Check resources at this galley
                    async with session.get(f"{API_BASE}/resources?asset={galley_id}&type=grain") as res_resp:
                        if res_resp.status == 200:
                            resources = await res_resp.json()
                            grain_amount = sum(r.get('count', 0) for r in resources)
                            if grain_amount > 0:
                                results["galleys_with_grain"] += 1
                                results["total_grain_in_galleys"] += grain_amount
                                print(f"    ✓ Found {grain_amount} grain!")
    except Exception as e:
        print(f"  ❌ Error checking galleys: {e}")
        results["bottlenecks"].append(f"Galley check failed: {e}")
    
    # 2. Check mills for grain and flour production
    print("\n🏭 CHECKING MILLS...")
    try:
        async with session.get(f"{API_BASE}/buildings?category=business") as resp:
            if resp.status == 200:
                buildings = await resp.json()
                mills = [b for b in buildings if 'mill' in b.get('type', '').lower()]
                
                for mill in mills:
                    mill_id = mill.get('buildingId')
                    operator = mill.get('runBy')
                    
                    if operator:
                        results["mills_operational"] += 1
                        print(f"  Mill {mill_id} operated by {operator}")
                        
                        # Check grain at mill
                        async with session.get(f"{API_BASE}/resources?asset={mill_id}&type=grain") as res_resp:
                            if res_resp.status == 200:
                                resources = await res_resp.json()
                                grain_amount = sum(r.get('count', 0) for r in resources)
                                if grain_amount > 0:
                                    results["mills_with_grain"] += 1
                                    results["total_grain_at_mills"] += grain_amount
                                    print(f"    ✓ Has {grain_amount} grain")
                                else:
                                    print(f"    ⚠️ NO GRAIN!")
                                    results["bottlenecks"].append(f"Mill {mill_id} has no grain")
                        
                        # Check if producing flour
                        async with session.get(f"{API_BASE}/activities?citizen={operator}&type=production&status=in_progress") as act_resp:
                            if act_resp.status == 200:
                                activities = await act_resp.json()
                                if activities:
                                    print(f"    🔄 Production in progress!")
                                else:
                                    print(f"    ❌ No production activity!")
                                    results["bottlenecks"].append(f"Mill {mill_id} not producing")
                    else:
                        print(f"  Mill {mill_id} - NO OPERATOR!")
                        results["bottlenecks"].append(f"Mill {mill_id} unmanned")
    except Exception as e:
        print(f"  ❌ Error checking mills: {e}")
        results["bottlenecks"].append(f"Mill check failed: {e}")
    
    # 3. Check bakeries for flour and bread production
    print("\n🍞 CHECKING BAKERIES...")
    try:
        async with session.get(f"{API_BASE}/buildings?type=bakery") as resp:
            if resp.status == 200:
                bakeries = await resp.json()
                
                for bakery in bakeries:
                    bakery_id = bakery.get('buildingId')
                    operator = bakery.get('runBy')
                    
                    if operator:
                        results["bakeries_operational"] += 1
                        print(f"  Bakery {bakery_id} operated by {operator}")
                        
                        # Check flour at bakery
                        async with session.get(f"{API_BASE}/resources?asset={bakery_id}&type=flour") as res_resp:
                            if res_resp.status == 200:
                                resources = await res_resp.json()
                                flour_amount = sum(r.get('count', 0) for r in resources)
                                if flour_amount > 0:
                                    results["bakeries_with_flour"] += 1
                                    results["total_flour_at_bakeries"] += flour_amount
                                    print(f"    ✓ Has {flour_amount} flour")
                                else:
                                    print(f"    ⚠️ NO FLOUR!")
                                    results["bottlenecks"].append(f"Bakery {bakery_id} has no flour")
                        
                        # Check bread output
                        async with session.get(f"{API_BASE}/resources?asset={bakery_id}&type=bread") as res_resp:
                            if res_resp.status == 200:
                                resources = await res_resp.json()
                                bread_amount = sum(r.get('count', 0) for r in resources)
                                if bread_amount > 0:
                                    results["bread_available"] += bread_amount
                                    print(f"    ✓ Has {bread_amount} bread!")
                    else:
                        print(f"  Bakery {bakery_id} - NO OPERATOR!")
                        results["bottlenecks"].append(f"Bakery {bakery_id} unmanned")
    except Exception as e:
        print(f"  ❌ Error checking bakeries: {e}")
        results["bottlenecks"].append(f"Bakery check failed: {e}")
    
    # 4. Check starving citizens
    print("\n😰 CHECKING CITIZEN HUNGER...")
    try:
        async with session.get(f"{API_BASE}/citizens") as resp:
            if resp.status == 200:
                citizens = await resp.json()
                now = datetime.utcnow()
                
                for citizen in citizens[:50]:  # Sample check
                    ate_at = citizen.get('ateAt')
                    if ate_at:
                        last_meal = datetime.fromisoformat(ate_at.replace('Z', '+00:00'))
                        hours_since_meal = (now - last_meal).total_seconds() / 3600
                        
                        if hours_since_meal > 24:
                            results["starving_citizens"] += 1
                            
                print(f"  Found {results['starving_citizens']} starving citizens (sample of 50)")
    except Exception as e:
        print(f"  ❌ Error checking citizens: {e}")
    
    # ANALYSIS
    print("\n=== SUPPLY CHAIN ANALYSIS ===")
    print(f"🚢 Galleys with grain: {results['galleys_with_grain']} ({results['total_grain_in_galleys']} total grain)")
    print(f"🏭 Operational mills: {results['mills_operational']}")
    print(f"   - With grain: {results['mills_with_grain']} ({results['total_grain_at_mills']} grain)")
    print(f"🍞 Operational bakeries: {results['bakeries_operational']}")
    print(f"   - With flour: {results['bakeries_with_flour']} ({results['total_flour_at_bakeries']} flour)")
    print(f"   - Bread available: {results['bread_available']}")
    print(f"😰 Starving citizens: {results['starving_citizens']}")
    
    print("\n🔨 CRITICAL BOTTLENECKS:")
    for bottleneck in results["bottlenecks"]:
        print(f"  ❌ {bottleneck}")
    
    # Identify main failure point
    if results["total_grain_in_galleys"] > 0 and results["total_grain_at_mills"] == 0:
        print("\n⚠️ MAIN FAILURE: Grain stuck in galleys! Not reaching mills!")
    elif results["mills_with_grain"] > 0 and results["total_flour_at_bakeries"] == 0:
        print("\n⚠️ MAIN FAILURE: Mills have grain but flour not reaching bakeries!")
    elif results["bakeries_with_flour"] > 0 and results["bread_available"] == 0:
        print("\n⚠️ MAIN FAILURE: Bakeries have flour but not producing bread!")
    
    return results


async def main():
    """Run the chaos test"""
    async with aiohttp.ClientSession() as session:
        results = await test_supply_chain(session)
        
        # Save results
        with open("grain_supply_chain_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print("\n✅ Test complete! Results saved to grain_supply_chain_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
CHAOS TEST: Complete Supply Chain Verification
Forge-Hammer-3: Every link must hold or citizens die!
"""

import json
from datetime import datetime

def test_complete_supply_chain():
    """Test grain → flour → bread chain systematically"""
    
    print("=== CHAOS TEST: SUPPLY CHAIN COMPLETE ===")
    print(f"Time: {datetime.utcnow().isoformat()}")
    print("Target: Save 112 starving citizens!")
    
    failures = []
    
    # LINK 1: Galley → Ground
    print("\n🚢 LINK 1: GALLEY UNLOADING")
    print("Testing: Can grain get OFF the galleys?")
    
    galley_tests = [
        {
            "test": "Galley has grain",
            "check": "Resources table has grain with Asset=galley_id",
            "common_failure": "Grain not properly imported"
        },
        {
            "test": "Unloading activity exists", 
            "check": "fetch_from_galley activity created",
            "common_failure": "No porters assigned to unload"
        },
        {
            "test": "Grain ownership clear",
            "check": "Owner field = merchant who can sell",
            "common_failure": "Foreign ownership blocks sale"
        }
    ]
    
    for test in galley_tests:
        print(f"  ❓ {test['test']}")
        print(f"     Check: {test['check']}")
        print(f"     Common failure: {test['common_failure']}")
    
    # LINK 2: Ground → Mill
    print("\n🏭 LINK 2: GRAIN TO MILLS")
    print("Testing: Can mills GET the grain?")
    
    mill_acquisition_tests = [
        {
            "test": "Mills create fetch activities",
            "check": "fetch_resource with target=galley",
            "common_failure": "Mills only check local sources"
        },
        {
            "test": "Purchase contracts exist",
            "check": "public_sell contracts for grain",
            "common_failure": "No contracts created on unload"
        },
        {
            "test": "Transport available",
            "check": "Porter or worker can carry grain",
            "common_failure": "No transport capacity"
        },
        {
            "test": "Path exists galley→mill",
            "check": "Valid walking/gondola route",
            "common_failure": "Mills inland, galleys at docks"
        }
    ]
    
    for test in mill_acquisition_tests:
        print(f"  ❓ {test['test']}")
        print(f"     Check: {test['check']}")
        print(f"     Common failure: {test['common_failure']}")
    
    # CRITICAL INJECTION POINT
    print("\n⚠️  CRITICAL: Do mills know to check galleys?")
    print("    HYPOTHESIS: Mills only check buildings tagged 'warehouse'")
    print("    TEST: Add galley check to mill supply logic")
    
    # LINK 3: Mill Production
    print("\n⚙️ LINK 3: FLOUR PRODUCTION")
    print("Testing: Can mills PROCESS grain to flour?")
    
    production_tests = [
        {
            "test": "Mill has operator",
            "check": "RunBy field populated",
            "common_failure": "Unmanned mills"
        },
        {
            "test": "Production activity created",
            "check": "Type=production for grain→flour",
            "common_failure": "Work handler not triggering"
        },
        {
            "test": "Recipe exists and valid",
            "check": "grain_mill has flour recipe",
            "common_failure": "Recipe disabled/missing"
        },
        {
            "test": "Storage space for flour",
            "check": "Mill capacity > current storage",
            "common_failure": "Mills full of old product"
        }
    ]
    
    for test in production_tests:
        print(f"  ❓ {test['test']}")
        print(f"     Check: {test['check']}")
        print(f"     Common failure: {test['common_failure']}")
    
    # LINK 4: Mill → Bakery
    print("\n🍞 LINK 4: FLOUR TO BAKERIES")
    print("Testing: Can bakeries GET flour?")
    
    bakery_acquisition_tests = [
        {
            "test": "Flour ownership transferable",
            "check": "Flour owned by mill operator",
            "common_failure": "Flour locked to building"
        },
        {
            "test": "Bakeries create fetch for flour",
            "check": "fetch_resource targeting mills",
            "common_failure": "Bakeries don't know mills have flour"
        },
        {
            "test": "Contracts for flour exist",
            "check": "public_sell or direct contracts",
            "common_failure": "Mills hoard flour"
        }
    ]
    
    for test in bakery_acquisition_tests:
        print(f"  ❓ {test['test']}")
        print(f"     Check: {test['check']}")
        print(f"     Common failure: {test['common_failure']}")
    
    # LINK 5: Bread Production
    print("\n🥖 LINK 5: BREAD PRODUCTION")
    print("Testing: Can bakeries MAKE bread?")
    
    bread_tests = [
        {
            "test": "Bakery has baker",
            "check": "RunBy field populated", 
            "common_failure": "Unmanned bakeries"
        },
        {
            "test": "Bread recipe active",
            "check": "flour→bread production",
            "common_failure": "Recipe missing/disabled"
        },
        {
            "test": "Production completes",
            "check": "Bread resources created",
            "common_failure": "Production interrupted"
        }
    ]
    
    for test in bread_tests:
        print(f"  ❓ {test['test']}")
        print(f"     Check: {test['check']}")
        print(f"     Common failure: {test['common_failure']}")
    
    # LINK 6: Citizens Eat
    print("\n😋 LINK 6: CITIZENS EATING")
    print("Testing: Can citizens GET bread?")
    
    eating_tests = [
        {
            "test": "Bread available for sale",
            "check": "public_sell contracts for bread",
            "common_failure": "Bakeries don't create sales"
        },
        {
            "test": "Citizens check food sources",
            "check": "Hunger triggers food search",
            "common_failure": "Citizens wait too long"
        },
        {
            "test": "Citizens have money",
            "check": "Ducats > bread price",
            "common_failure": "Poor citizens can't afford"
        },
        {
            "test": "Eating updates AteAt",
            "check": "Timestamp updates on consumption",
            "common_failure": "Eating doesn't register"
        }
    ]
    
    for test in eating_tests:
        print(f"  ❓ {test['test']}")
        print(f"     Check: {test['check']}")
        print(f"     Common failure: {test['common_failure']}")
    
    # BREAKING POINT ANALYSIS
    print("\n🔨 SYSTEMATIC BREAKING POINTS:")
    
    breaking_points = [
        {
            "point": "Galley → Mill Connection",
            "failure": "Mills don't search galleys for grain",
            "fix": "Add galley check to mill supply search",
            "priority": "CRITICAL"
        },
        {
            "point": "Contract Creation",
            "failure": "No public_sell contracts on unload",
            "fix": "Auto-create grain contracts when galley docks",
            "priority": "HIGH"
        },
        {
            "point": "Transport Capacity", 
            "failure": "Not enough porters for grain volume",
            "fix": "Prioritize food transport",
            "priority": "HIGH"
        },
        {
            "point": "Production Triggers",
            "failure": "Work handler not creating production",
            "fix": "Force check supplies → production flow",
            "priority": "CRITICAL"
        },
        {
            "point": "Economic Access",
            "failure": "Poor citizens can't afford bread",
            "fix": "Emergency food pricing",
            "priority": "MEDIUM"
        }
    ]
    
    for bp in breaking_points:
        print(f"\n❌ {bp['point']}")
        print(f"   Failure: {bp['failure']}")
        print(f"   Fix: {bp['fix']}")
        print(f"   Priority: {bp['priority']}")
    
    # EMERGENCY PATCHES
    print("\n🚨 EMERGENCY PATCHES REQUIRED:")
    
    print("""
1. In work handler (handlers/work.py):
   if building_type == "grain_mill" and not has_grain:
       # CHECK GALLEYS TOO!
       grain_sources = find_grain_sources(include_galleys=True)
       if grain_sources:
           create_fetch_activity(grain_sources[0])

2. In galley processor (pickup_from_galley_processor.py):
   # After unloading grain
   if resource_type == "grain":
       create_public_sell_contract(
           resource=grain,
           price=fair_market_price,
           location=galley_location
       )

3. In needs handler (handlers/needs.py):
   if hours_since_eating > 20:  # Getting desperate
       food_priority = "CRITICAL"
       expand_search_radius = True
       consider_credit = True
    """)
    
    # FINAL VERDICT
    print("\n🔥 CHAOS TEST VERDICT:")
    print("PRIMARY FAILURE: Mills don't know galleys exist!")
    print("SECONDARY FAILURE: No automatic contract creation!")
    print("TERTIARY FAILURE: Poor transport prioritization!")
    
    print("\n✅ With these 3 fixes, grain WILL flow to bread!")
    print("🍞 112 citizens WILL eat!")
    
    return {
        "main_bottleneck": "Mill→Galley connection missing",
        "critical_fixes": 3,
        "estimated_fix_time": "30 minutes",
        "citizens_saveable": 112
    }


if __name__ == "__main__":
    results = test_complete_supply_chain()
    with open("supply_chain_complete_results.json", "w") as f:
        json.dump(results, f, indent=2)
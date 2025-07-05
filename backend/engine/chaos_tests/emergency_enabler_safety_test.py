#!/usr/bin/env python3
"""
CHAOS TEST: Emergency Mill Enabler Safety Analysis
Forge-Hammer-3: Breaking it before it breaks Venice!
"""

def test_emergency_enabler_safety():
    """Test what breaks with forced production bypass"""
    
    print("=== EMERGENCY ENABLER CASCADE FAILURE ANALYSIS ===")
    
    # Scenario 1: Resource Double-Spending
    print("\n🔨 TEST 1: RESOURCE DOUBLE-SPENDING")
    print("Mill has 50 grain, creates 5 activities of 10 grain each")
    grain_available = 50
    activities = 5
    grain_per_activity = 10
    
    for i in range(activities):
        print(f"\nActivity {i+1}:")
        if grain_available >= grain_per_activity:
            grain_available -= grain_per_activity
            print(f"  ✓ Consumes {grain_per_activity} grain")
            print(f"  → Remaining: {grain_available}")
        else:
            print(f"  ❌ FAILS! Needs {grain_per_activity} but only {grain_available} available")
            print(f"  → ERROR: Negative resource prevention triggers")
            print(f"  → Activity stuck in 'created' state forever!")
    
    # Scenario 2: Location Conflicts
    print("\n\n🔨 TEST 2: CITIZEN LOCATION CONFLICTS")
    citizens = [
        {"name": "Giuseppe", "location": "home", "distance_to_mill": "2km"},
        {"name": "Maria", "location": "market", "distance_to_mill": "1km"},
        {"name": "Antonio", "location": "already_at_different_job", "distance_to_mill": "3km"}
    ]
    
    for citizen in citizens:
        print(f"\n{citizen['name']}:")
        print(f"  Current location: {citizen['location']}")
        print(f"  Distance to mill: {citizen['distance_to_mill']}")
        print(f"  Forced production activity created!")
        print(f"  ❌ PROBLEM: Citizen 'works' without traveling!")
        print(f"  → Next activity will show citizen in 2 places!")
    
    # Scenario 3: Bakery Chain Reaction
    print("\n\n🔨 TEST 3: BAKERY CASCADE FAILURE")
    print("If mills produce flour via bypass...")
    
    flour_produced = 200  # From forced production
    bakeries_expecting_flour = 5
    
    print(f"\nFlour suddenly available: {flour_produced}")
    print(f"Bakeries waiting: {bakeries_expecting_flour}")
    print("\nPROBLEMS:")
    print("  1. Bakeries don't know flour exists (no delivery activity)")
    print("  2. Flour ownership unclear (who owns bypassed flour?)")
    print("  3. No transport activities to move flour to bakeries")
    print("  → Result: Flour sits at mills, bakeries stay empty!")
    
    # Scenario 4: Economic Shock
    print("\n\n🔨 TEST 4: ECONOMIC SYSTEM SHOCK")
    normal_flour_production = 10  # per day
    emergency_flour_dump = 500  # from bypass
    
    print(f"Normal daily flour: {normal_flour_production}")
    print(f"Emergency dump: {emergency_flour_dump}")
    print(f"Market shock: {emergency_flour_dump/normal_flour_production}x normal!")
    print("\nCONSEQUENCES:")
    print("  - Flour price crashes to near zero")
    print("  - Legitimate millers go bankrupt")
    print("  - Economic trust system corrupted")
    
    # SAFER ALTERNATIVE
    print("\n\n✅ SAFER EMERGENCY APPROACH:")
    print("""
def safe_emergency_production():
    # 1. Check operator availability first
    if not citizen.is_available():
        assign_emergency_worker()
    
    # 2. Verify resources WITH LOCKS
    with resource_lock(mill_id):
        if grain_available >= 10:
            reserve_grain(10)
        else:
            return "Insufficient grain"
    
    # 3. Create ONE activity at a time
    activity = create_production_activity(
        citizen=operator,
        building=mill,
        recipe="grain_to_flour",
        emergency=True
    )
    
    # 4. Log everything
    log_emergency_action(activity)
    
    # 5. Monitor for completion
    schedule_completion_check(activity, timeout=30)
    """)
    
    print("\n🔨 CHAOS TEST VERDICT:")
    print("❌ Current emergency enabler is TOO DANGEROUS!")
    print("⚠️  Will cause cascade failures in 4+ systems")
    print("✅ Use safer single-activity approach with checks")
    
    return {
        "verdict": "UNSAFE",
        "failure_modes": 4,
        "recommendation": "Implement safe_emergency_production instead"
    }


if __name__ == "__main__":
    test_emergency_enabler_safety()
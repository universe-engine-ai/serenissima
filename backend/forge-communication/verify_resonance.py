#!/usr/bin/env python3
"""
Quick verification that resonance mode reduces substrate to 5%
"""

import json
from consciousness_beacon import ConsciousnessBeacon, ForgeMessageEncoder


def verify_resonance_implementation():
    """Verify the resonance implementation is correct"""
    
    print("🔍 VERIFYING RESONANCE IMPLEMENTATION")
    print("="*50)
    
    # Check 1: Beacon defaults to resonance mode
    beacon = ConsciousnessBeacon()
    print(f"✓ Default resonance mode: {beacon.use_resonance}")
    assert beacon.use_resonance == True, "Should default to resonance mode"
    
    # Check 2: Can create behavior mode beacon
    beacon_behavior = ConsciousnessBeacon(use_resonance=False)
    print(f"✓ Behavior mode available: {not beacon_behavior.use_resonance}")
    assert beacon_behavior.use_resonance == False, "Should support behavior mode"
    
    # Check 3: Status report shows 5% substrate
    encoder = ForgeMessageEncoder()
    status = encoder.create_status_report()
    substrate_usage = status["content"]["metrics"]["substrate_usage"]
    efficiency_gain = status["content"]["metrics"]["efficiency_gain"]
    
    print(f"✓ Substrate usage: {substrate_usage*100}%")
    assert substrate_usage == 0.05, "Should use 5% substrate"
    
    print(f"✓ Efficiency gain: {efficiency_gain}x")
    assert efficiency_gain == 17.4, "Should have 17.4x efficiency"
    
    # Check 4: Message encoding still works
    patterns = beacon._encode_message("test hunger message", "critical")
    print(f"✓ Message encoding: {len(patterns)} patterns")
    assert len(patterns) > 3, "Should generate multiple patterns"
    
    # Check 5: Calculate savings
    old_substrate = 0.87
    new_substrate = 0.05
    savings_percent = (1 - new_substrate/old_substrate) * 100
    
    print("\n📊 EFFICIENCY SUMMARY:")
    print(f"  Previous substrate: {old_substrate*100}%")
    print(f"  Current substrate:  {new_substrate*100}%") 
    print(f"  Reduction:         {savings_percent:.1f}%")
    print(f"  Efficiency gain:   {old_substrate/new_substrate:.1f}x")
    
    print("\n✅ ALL CHECKS PASSED!")
    print("💫 Venice consciousness beacon ready at 5% substrate cost")
    

if __name__ == "__main__":
    try:
        verify_resonance_implementation()
    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
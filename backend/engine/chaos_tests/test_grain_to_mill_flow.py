#!/usr/bin/env python3
"""
CHAOS TEST: Grain to Mill Flow Testing
Forge-Hammer-3: Why doesn't grain reach mills?!
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
import json

# This test checks if:
# 1. Mills create fetch_resource activities for grain
# 2. These activities target the right sources (galleys)
# 3. The activities are processed correctly

def test_mill_grain_fetching():
    """Test if mills are creating activities to fetch grain"""
    
    print("=== CHAOS TEST: MILL GRAIN FETCHING ===")
    
    test_cases = []
    
    # Test Case 1: Mill should create fetch_resource for grain from galley
    test_cases.append({
        "name": "Mill creates grain fetch from galley",
        "scenario": {
            "mill": {
                "buildingId": "mill_45.123_12.456",
                "runBy": "Giuseppe_Miller",
                "type": "grain_mill",
                "storage": []  # Empty, needs grain
            },
            "galley": {
                "buildingId": "merchant_galley_45.111_12.222",
                "owner": "Foreign_Merchant",
                "resources": [
                    {"type": "grain", "count": 100, "owner": "Foreign_Merchant"}
                ]
            },
            "expected_activity": {
                "type": "fetch_resource",
                "resource": "grain",
                "from": "merchant_galley_45.111_12.222",
                "to": "mill_45.123_12.456"
            }
        }
    })
    
    # Test Case 2: Porter fetches grain for mill
    test_cases.append({
        "name": "Porter delivers grain from galley to mill",
        "scenario": {
            "porter": {
                "username": "Strong_Porter",
                "location": "porter_guild_hall"
            },
            "contract": {
                "type": "logistics_service_request",
                "resource": "grain",
                "from": "merchant_galley_45.111_12.222",
                "to": "mill_45.123_12.456",
                "amount": 50
            },
            "expected_result": {
                "grain_at_mill": 50,
                "porter_trust_increase": True
            }
        }
    })
    
    # Test Case 3: Mill processes grain into flour
    test_cases.append({
        "name": "Mill production of flour from grain",
        "scenario": {
            "mill": {
                "buildingId": "mill_45.123_12.456",
                "runBy": "Giuseppe_Miller",
                "resources": [
                    {"type": "grain", "count": 50}
                ]
            },
            "production_recipe": {
                "inputs": [{"type": "grain", "amount": 10}],
                "outputs": [{"type": "flour", "amount": 8}],
                "time": 30
            },
            "expected_result": {
                "flour_produced": 40,  # 5 batches
                "grain_remaining": 0
            }
        }
    })
    
    # CRITICAL CHECKS
    print("\n🔨 CRITICAL SUPPLY CHAIN CHECKS:")
    
    print("\n1. GALLEY → MILL CONNECTION")
    print("   ❓ Do mills know where galleys are?")
    print("   ❓ Can mills create fetch activities for galleys?")
    print("   ❓ Do these activities get processed?")
    
    print("\n2. GRAIN OWNERSHIP")
    print("   ❓ Who owns grain in galleys? (Foreign_Merchant)")
    print("   ❓ Can mills buy from foreign merchants?")
    print("   ❓ Are contracts being created for grain purchase?")
    
    print("\n3. TRANSPORT LOGISTICS")
    print("   ❓ Are porters available to move grain?")
    print("   ❓ Do porters prioritize food transport?")
    print("   ❓ Is the path from galley to mill valid?")
    
    print("\n4. PRODUCTION TRIGGERS")
    print("   ❓ Do mills check for grain regularly?")
    print("   ❓ Does production activity get created when grain arrives?")
    print("   ❓ Is the grain→flour recipe active?")
    
    # HYPOTHESIS TESTING
    print("\n🔬 HYPOTHESIS TESTING:")
    
    hypotheses = [
        {
            "hypothesis": "Mills don't know galleys exist",
            "test": "Check if mills search for 'public_sell' contracts from galleys",
            "fix": "Ensure galleys create public grain contracts"
        },
        {
            "hypothesis": "Foreign ownership blocks purchase",
            "test": "Check if foreign merchants can sell to locals",
            "fix": "Allow cross-citizenship resource sales"
        },
        {
            "hypothesis": "No transport activities created",
            "test": "Check porter activity queue for grain transport",
            "fix": "Prioritize food transport in porter logic"
        },
        {
            "hypothesis": "Mills not checking for supplies",
            "test": "Check mill handler's supply checking frequency",
            "fix": "Add periodic grain check to mill operations"
        }
    ]
    
    for h in hypotheses:
        print(f"\n📊 {h['hypothesis']}")
        print(f"   Test: {h['test']}")
        print(f"   Fix: {h['fix']}")
    
    # EMERGENCY PATCHES
    print("\n🚨 EMERGENCY PATCHES NEEDED:")
    
    patches = [
        {
            "file": "handlers/work.py",
            "function": "process_work_activity",
            "patch": "Add grain sourcing check for mills before production"
        },
        {
            "file": "activity_creators/fetch_resource_activity_creator.py",
            "function": "find_resource_source",
            "patch": "Include galleys as valid sources for grain"
        },
        {
            "file": "logic/galley_activities.py",
            "function": "create_public_contracts",
            "patch": "Ensure grain contracts are created on galley arrival"
        }
    ]
    
    for p in patches:
        print(f"\n📝 {p['file']} - {p['function']}")
        print(f"   Patch: {p['patch']}")
    
    # Save test results
    results = {
        "test_time": datetime.utcnow().isoformat(),
        "test_cases": test_cases,
        "hypotheses": hypotheses,
        "patches": patches,
        "critical_finding": "Grain likely stuck due to missing mill→galley activity creation"
    }
    
    with open("grain_to_mill_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Analysis complete! See grain_to_mill_test_results.json")
    print("\n🔥 RECOMMENDATION: Check if mills are creating fetch_resource activities!")


if __name__ == "__main__":
    test_mill_grain_fetching()
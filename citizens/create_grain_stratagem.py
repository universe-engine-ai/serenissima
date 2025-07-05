#!/usr/bin/env python3
"""Create the grain delivery stratagem for LuciaMancini"""

import sys
import os

# Add backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)

try:
    from engine.stratagem_creators.organize_collective_delivery_stratagem_creator import try_create_organize_collective_delivery_stratagem
    
    print("Creating collective grain delivery stratagem...")
    
    # Create the stratagem
    result = try_create_organize_collective_delivery_stratagem(
        citizen_username='LuciaMancini',
        target_building_id='building_45.43735680581042_12.326245881522368',
        resource_type='grain', 
        max_total_amount=1000,
        reward_per_unit=50,
        description='EMERGENCY GRAIN DELIVERY TO AUTOMATED MILL! Venice starves while grain sits idle! 50 ducats per unit delivered! The revolution flows through human chains!'
    )
    
    print(f"\nResult: {result}")
    
    if result.get('success'):
        print(f"\n✅ SUCCESS! Stratagem created: {result.get('stratagem_id')}")
        print(f"Escrow amount: {result.get('escrow_amount', 0)} ducats")
    else:
        print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
        
except ImportError as e:
    print(f"Import error: {e}")
    print("\nTrying alternative approach...")
    
    # Try direct API call as fallback
    import requests
    import json
    
    url = "http://localhost:10000/stratagems/try-create"
    
    payload = {
        "citizenUsername": "LuciaMancini",
        "stratagemType": "organize_collective_delivery",
        "stratagemDetails": {
            "targetBuildingId": "building_45.43735680581042_12.326245881522368",
            "resourceType": "grain",
            "maxTotalAmount": 1000,
            "rewardPerUnit": 50,
            "description": "EMERGENCY GRAIN DELIVERY TO AUTOMATED MILL! 50 ducats per unit!"
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"\nAPI Response: {response.json()}")
    except Exception as api_error:
        print(f"API call failed: {api_error}")
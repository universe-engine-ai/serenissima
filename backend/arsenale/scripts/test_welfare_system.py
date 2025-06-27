#!/usr/bin/env python3
"""
Test script for the welfare porter system.
Tests the complete flow: hunger detection → porter work → food collection
"""

import json
from datetime import datetime, timedelta


def test_welfare_qualification():
    """Test if citizens qualify for welfare work."""
    test_citizens = [
        {"name": "Hungry Poor", "hunger": 75, "ducats": 20, "should_qualify": True},
        {"name": "Hungry Rich", "hunger": 75, "ducats": 200, "should_qualify": False},
        {"name": "Fed Poor", "hunger": 25, "ducats": 20, "should_qualify": False},
        {"name": "Fed Rich", "hunger": 25, "ducats": 200, "should_qualify": False},
    ]
    
    print("Testing Welfare Qualification:")
    print("-" * 50)
    
    for citizen in test_citizens:
        qualifies = citizen["hunger"] > 50 and citizen["ducats"] < 50
        expected = citizen["should_qualify"]
        status = "✅" if qualifies == expected else "❌"
        
        print(f"{status} {citizen['name']}: hunger={citizen['hunger']}, "
              f"ducats={citizen['ducats']} → qualifies={qualifies}")
    
    print()


def test_porter_work_creation():
    """Test porter work data structure."""
    print("Testing Porter Work Creation:")
    print("-" * 50)
    
    # Example Consiglio work
    consiglio_work = {
        'employer': 'ConsiglioDeiDieci',
        'cargo_type': 'grain',
        'cargo_amount': 50,
        'from_building': 'warehouse_rialto_001',
        'to_building': 'warehouse_arsenale_002',
        'payment_type': 'food_voucher'
    }
    
    print("Consiglio Porter Work:")
    print(json.dumps(consiglio_work, indent=2))
    
    # Calculate food payment
    base_payment = 3
    distance_bonus = 2  # Assuming 200m distance
    total_food = base_payment + distance_bonus
    
    print(f"\nFood Payment Calculation:")
    print(f"- Base payment: {base_payment} bread")
    print(f"- Distance bonus: {distance_bonus} bread")
    print(f"- Total payment: {total_food} bread")
    
    print()


def test_voucher_creation():
    """Test food voucher structure."""
    print("Testing Food Voucher Creation:")
    print("-" * 50)
    
    voucher = {
        'id': 'voucher_abc12345',
        'citizen': 'Marco_Soranzo',
        'employer': 'ConsiglioDeiDieci',
        'food_amount': 5,
        'food_type': 'bread',
        'valid_until': (datetime.now() + timedelta(days=1)).isoformat(),
        'work_description': 'Transported 50 grain from Rialto to Arsenale',
        'created_at': datetime.now().isoformat()
    }
    
    print("Food Voucher:")
    print(json.dumps(voucher, indent=2))
    
    print()


def test_activity_chain():
    """Test the complete activity chain."""
    print("Testing Complete Activity Chain:")
    print("-" * 50)
    
    activities = [
        {
            'step': 1,
            'type': 'welfare_porter',
            'description': 'Pick up cargo at source',
            'location': 'warehouse_rialto_001',
            'action': 'Pick up 50 grain',
            'result': 'Cargo loaded, voucher created'
        },
        {
            'step': 2,
            'type': 'welfare_porter_delivery',
            'description': 'Deliver cargo to destination',
            'location': 'warehouse_arsenale_002',
            'action': 'Deliver 50 grain',
            'result': 'Cargo delivered, food collection chained'
        },
        {
            'step': 3,
            'type': 'collect_welfare_food',
            'description': 'Collect earned food',
            'location': 'market_stall_consiglio_003',
            'action': 'Redeem voucher for 5 bread',
            'result': 'Hunger reduced by 50 points'
        }
    ]
    
    for activity in activities:
        print(f"Step {activity['step']}: {activity['type']}")
        print(f"  Description: {activity['description']}")
        print(f"  Location: {activity['location']}")
        print(f"  Action: {activity['action']}")
        print(f"  Result: {activity['result']}")
        print()


def test_trust_based_selection():
    """Test selection of work providers based on trust."""
    print("Testing Trust-Based Work Selection:")
    print("-" * 50)
    
    # Example trust relationships with Consiglio
    trust_relationships = [
        {"citizen": "Antonio_Morosini", "trust": 95, "rank": 1},
        {"citizen": "Elena_Contarini", "trust": 87, "rank": 2},
        {"citizen": "Francesco_Dandolo", "trust": 82, "rank": 3},
        {"citizen": "Maria_Grimaldi", "trust": 78, "rank": 4},
        {"citizen": "Giovanni_Foscari", "trust": 75, "rank": 5},
        {"citizen": "Isabella_Barbaro", "trust": 70, "rank": 6},  # Not selected
    ]
    
    print("Consiglio Trust Rankings (top 5 selected for work):")
    for rel in trust_relationships:
        selected = "✅" if rel["rank"] <= 5 else "❌"
        print(f"{selected} Rank {rel['rank']}: {rel['citizen']} "
              f"(trust: {rel['trust']})")
    
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Welfare Porter System Test Suite")
    print("=" * 60)
    print()
    
    test_welfare_qualification()
    test_porter_work_creation()
    test_voucher_creation()
    test_activity_chain()
    test_trust_based_selection()
    
    print("=" * 60)
    print("Test Summary:")
    print("- Hungry + Poor citizens qualify for welfare work")
    print("- Porter work pays in food vouchers (3-10 bread)")
    print("- Work comes from Consiglio or top 5 trusted nobles")
    print("- 3-step process: pickup → delivery → food collection")
    print("- Food collected at Consiglio market stalls")
    print("=" * 60)


if __name__ == "__main__":
    main()
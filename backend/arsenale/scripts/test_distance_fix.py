#!/usr/bin/env python3
"""Test the distance_helpers fix with various position formats"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.utils.distance_helpers import parse_position, calculate_distance

def test_position_parsing():
    """Test various position formats"""
    print("=== TESTING POSITION PARSING ===\n")
    
    test_cases = [
        # Dict format (original working format)
        {'lat': 45.4371, 'lng': 12.3326},
        
        # JSON string format
        '{"lat": 45.4371, "lng": 12.3326}',
        
        # Comma-separated format
        '45.4371,12.3326',
        
        # Comma-separated with spaces
        '45.4371, 12.3326',
        
        # Format with labels
        'lat:45.4371,lng:12.3326',
    ]
    
    for i, test_pos in enumerate(test_cases):
        print(f"Test case {i+1}: {test_pos}")
        try:
            parsed = parse_position(test_pos)
            print(f"  ✓ Parsed successfully: {parsed}")
        except Exception as e:
            print(f"  ✗ Failed to parse: {e}")
        print()

def test_distance_calculation():
    """Test distance calculation with various formats"""
    print("=== TESTING DISTANCE CALCULATION ===\n")
    
    # Test positions
    pos1_dict = {'lat': 45.4371, 'lng': 12.3326}
    pos2_dict = {'lat': 45.4380, 'lng': 12.3350}
    
    pos1_string = '{"lat": 45.4371, "lng": 12.3326}'
    pos2_comma = '45.4380,12.3350'
    
    test_pairs = [
        (pos1_dict, pos2_dict, "dict to dict"),
        (pos1_string, pos2_dict, "string to dict"),
        (pos1_dict, pos2_comma, "dict to comma string"),
        (pos1_string, pos2_comma, "JSON string to comma string"),
    ]
    
    for pos1, pos2, description in test_pairs:
        print(f"Testing {description}:")
        print(f"  Position 1: {pos1}")
        print(f"  Position 2: {pos2}")
        try:
            distance = calculate_distance(pos1, pos2)
            print(f"  ✓ Distance: {distance:.2f} meters")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        print()

def test_real_world_scenario():
    """Test with actual data format from the error"""
    print("=== TESTING REAL-WORLD SCENARIO ===\n")
    
    # Simulate the exact error scenario
    citizen_pos = "45.4371,12.3326"  # String format that was causing the error
    business_pos = {'lat': 45.4380, 'lng': 12.3350}  # Dict format
    
    print(f"Citizen position (string): {citizen_pos}")
    print(f"Business position (dict): {business_pos}")
    
    try:
        distance = calculate_distance(citizen_pos, business_pos)
        print(f"✓ SUCCESS! Distance calculated: {distance:.2f} meters")
        print(f"  Walking time: {distance / 67:.1f} minutes")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    print("Distance Helpers Fix Test Suite")
    print("=" * 50)
    print()
    
    test_position_parsing()
    test_distance_calculation()
    test_real_world_scenario()
    
    print("\n" + "=" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    main()
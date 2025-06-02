#!/usr/bin/env python3
"""
Test script for the relationship analysis functionality.
This script creates a mock relationship between two citizens and tests the analysis.
"""

import json
import os
import sys
from typing import Dict, Any

# Add the parent directory to the Python path to import the analyzeRelationship module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from relationships.analyzeRelationship import analyze_relationship_title, analyze_relationship_description

def test_relationship_title():
    """Test the relationship title generation function with various inputs."""
    test_cases = [
        {"strength": 600, "trust": 60, "expected": "Trusted Allies"},
        {"strength": 600, "trust": -50, "expected": "Necessary Partners"},
        {"strength": 600, "trust": 20, "expected": "Strong Associates"},
        {"strength": 300, "trust": 60, "expected": "Reliable Contacts"},
        {"strength": 300, "trust": -50, "expected": "Cautious Collaborators"},
        {"strength": 300, "trust": 20, "expected": "Business Associates"},
        {"strength": 100, "trust": 60, "expected": "Distant Friends"},
        {"strength": 100, "trust": -50, "expected": "Wary Acquaintances"},
        {"strength": 100, "trust": 20, "expected": "Casual Acquaintances"},
    ]
    
    for i, case in enumerate(test_cases):
        result = analyze_relationship_title(case["strength"], case["trust"])
        if result == case["expected"]:
            print(f"✅ Test case {i+1} passed: {result}")
        else:
            print(f"❌ Test case {i+1} failed: Expected '{case['expected']}', got '{result}'")

def test_relationship_description():
    """Test the relationship description generation function with various inputs."""
    test_cases = [
        {
            "strength": 600, 
            "trust": 60, 
            "relevancies": [{"Type": "economic"}], 
            "problems": [],
            "expected_contains": ["strong", "high level of trust", "economic"]
        },
        {
            "strength": 300, 
            "trust": -30, 
            "relevancies": [{"Type": "political"}], 
            "problems": [{"Title": "Housing Shortage"}],
            "expected_contains": ["moderate", "lack of trust", "politically", "common challenges"]
        },
        {
            "strength": 100, 
            "trust": 10, 
            "relevancies": [{"Type": "social"}], 
            "problems": [],
            "expected_contains": ["limited", "neutral", "social"]
        }
    ]
    
    for i, case in enumerate(test_cases):
        result = analyze_relationship_description(
            case["strength"], 
            case["trust"], 
            case["relevancies"], 
            case["problems"]
        )
        
        all_found = True
        for expected_text in case["expected_contains"]:
            if expected_text.lower() not in result.lower():
                print(f"❌ Test case {i+1} failed: Expected to contain '{expected_text}', but got: '{result}'")
                all_found = False
                break
        
        if all_found:
            print(f"✅ Test case {i+1} passed")

def main():
    """Run all tests."""
    print("Testing relationship title generation:")
    test_relationship_title()
    
    print("\nTesting relationship description generation:")
    test_relationship_description()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for the relationship evaluation functionality.
"""

import sys
import os
import json

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from relationships.evaluateRelationship import evaluate_relationship

def test_relationship_evaluation():
    """Test the relationship evaluation function with sample data."""
    # Test with two sample citizens
    citizen1 = "BarbarigoCadet"
    citizen2 = "EliteInvestor"
    
    print(f"Testing relationship evaluation between {citizen1} and {citizen2}...")
    
    result = evaluate_relationship(citizen1, citizen2)
    
    print("\nEvaluation result:")
    print(json.dumps(result, indent=2))
    
    # Verify the result has the expected structure
    assert "title" in result, "Result should have a 'title' field"
    assert "description" in result, "Result should have a 'description' field"
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_relationship_evaluation()

#!/usr/bin/env python3
"""
Test script for the relationship evaluation response functionality.
"""

import json
import sys
import os
from evaluateRelationshipResponse import evaluate_relationship

def test_evaluation():
    """Run a test evaluation with sample data."""
    # Sample data based on the system message
    mock_evaluator = {"CitizenId": "ConsiglioDeiDieci", "SocialClass": "Nobili"}
    mock_target = {"CitizenId": "meyti_tgz2", "SocialClass": "Facchini"}
    mock_relationship = {"TrustScore": 32.12, "StrengthScore": 0}
    mock_problems = [{"type": "workless_citizen", "citizen": "meyti_tgz2"}]
    
    # Evaluate the relationship
    result = evaluate_relationship(
        mock_evaluator,
        mock_target,
        mock_relationship,
        mock_problems
    )
    
    # Print the result
    print(json.dumps(result, indent=2))
    
    # Verify the result has the expected structure
    assert "title" in result, "Result should have a 'title' field"
    assert "description" in result, "Result should have a 'description' field"
    
    print("\nTest passed successfully!")

if __name__ == "__main__":
    test_evaluation()

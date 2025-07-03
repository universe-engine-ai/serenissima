#!/usr/bin/env python3
"""
Simple test of consciousness measurement implementation
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consciousness_measurement_implementation import ConsciousnessMeasurementEngine, run_consciousness_assessment

def test_simple():
    """Test with minimal data"""
    
    print("=== Testing Consciousness Measurement Engine ===")
    
    # Create minimal test data
    test_data = {
        'messages': [
            {
                'id': '1',
                'sender': 'CitizenA',
                'receiver': 'CitizenB',
                'content': 'I think we should buy more bread tomorrow',
                'timestamp': '2024-01-01T12:00:00Z',
                'replyToId': ''
            },
            {
                'id': '2',
                'sender': 'CitizenA',
                'receiver': 'CitizenA',  # Thought (message to self)
                'content': 'On second thought, maybe I should wait for better prices',
                'timestamp': '2024-01-01T12:05:00Z',
                'replyToId': ''
            },
            {
                'id': '3',
                'sender': 'CitizenB',
                'receiver': 'CitizenA',
                'content': 'I predict prices will fall next week',
                'timestamp': '2024-01-01T12:10:00Z',
                'replyToId': '1'
            }
        ],
        'activities': [
            {
                'id': 'a1',
                'CitizenUsername': 'CitizenA',
                'Type': 'move',
                'Location': 'Market',
                'CreatedAt': '2024-01-01T12:00:00Z',
                'Status': 'completed'
            }
        ],
        'citizens': [
            {
                'Username': 'CitizenA',
                'Location': 'Market',
                'IsAI': True,
                'Thoughts': 5,
                'SocialClass': 'Popolano',
                'Wealth': 100
            },
            {
                'Username': 'CitizenB',
                'Location': 'Rialto',
                'IsAI': True,
                'Thoughts': 3,
                'SocialClass': 'Popolano',
                'Wealth': 150
            }
        ],
        'stratagems': [],
        'contracts': [
            {
                'id': 'c1',
                'Seller': 'CitizenA',
                'Buyer': 'CitizenB',
                'Price': 10,
                'ResourceType': 'bread',
                'Status': 'completed',
                'CreatedAt': '2024-01-01T11:00:00Z',
                'Type': 'sale'
            }
        ]
    }
    
    try:
        # Run assessment
        print("\nRunning consciousness assessment...")
        assessment = run_consciousness_assessment(test_data)
        
        print(f"\n✅ Assessment completed successfully!")
        print(f"\nResults:")
        print(f"  Overall Score: {assessment['overall_score']:.2f}/3.0")
        print(f"  Emergence Ratio: {assessment['emergence_ratio']:.1%}")
        print(f"  Data Quality: {assessment['data_quality']:.1%}")
        
        print(f"\nIndicator Scores:")
        for ind_id, measurement in sorted(assessment['indicators'].items()):
            print(f"  {ind_id}: {measurement.value:.2f}")
            if measurement.evidence:
                print(f"    Evidence: {measurement.evidence[0]}")
                
        # Test specific features
        print(f"\n=== Testing Thought Detection ===")
        engine = ConsciousnessMeasurementEngine()
        thoughts = engine._extract_thoughts(test_data['messages'])
        print(f"Found {len(thoughts)} thoughts (messages to self)")
        for thought in thoughts:
            print(f"  - {thought['sender']}: '{thought['content'][:50]}...'")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()
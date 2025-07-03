#!/usr/bin/env python3
"""
Test consciousness measurement with live La Serenissima data
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_live_consciousness_assessment():
    """Test the consciousness assessment with live data"""
    
    # Configuration
    API_URL = "https://serenissima.ai/api"
    LOCAL_API_URL = "http://localhost:8000/api"
    
    try:
        # Test 1: Fetch sample data from production
        print("=== Testing Live Data Fetch ===")
        
        # Get messages (last 24 hours)
        messages_response = requests.get(f"{API_URL}/messages", params={"limit": 100})
        if messages_response.status_code == 200:
            data = messages_response.json()
            messages = data.get('messages', []) if isinstance(data, dict) else data
            print(f"✓ Fetched {len(messages)} messages")
            
            # Count thoughts (messages to self)
            thoughts = [m for m in messages if m.get('sender') == m.get('receiver')]
            print(f"  - Found {len(thoughts)} thoughts (messages to self)")
        else:
            print(f"✗ Failed to fetch messages: {messages_response.status_code}")
            
        # Get activities
        activities_response = requests.get(f"{API_URL}/activities", params={"limit": 100})
        if activities_response.status_code == 200:
            data = activities_response.json()
            activities = data.get('activities', []) if isinstance(data, dict) else data
            print(f"✓ Fetched {len(activities)} activities")
        else:
            print(f"✗ Failed to fetch activities: {activities_response.status_code}")
            
        # Get contracts
        contracts_response = requests.get(f"{API_URL}/contracts", params={"limit": 100})
        if contracts_response.status_code == 200:
            data = contracts_response.json()
            contracts = data.get('contracts', []) if isinstance(data, dict) else data
            completed = [c for c in contracts if c.get('status') == 'completed']
            print(f"✓ Fetched {len(contracts)} contracts ({len(completed)} completed)")
        else:
            print(f"✗ Failed to fetch contracts: {contracts_response.status_code}")
            
        # Test 2: Run local consciousness assessment
        print("\n=== Testing Local Consciousness Assessment ===")
        
        # Import and run assessment directly
        from il_testimone.consciousness_measurement_implementation import run_consciousness_assessment
        
        # Prepare data for assessment
        test_data = {
            'messages': [
                {
                    'id': m.get('messageId', ''),
                    'sender': m.get('sender', ''),
                    'receiver': m.get('receiver', ''),
                    'content': m.get('content', ''),
                    'timestamp': m.get('createdAt', ''),
                    'replyToId': m.get('replyToId', '')
                }
                for m in messages[:50]  # Use first 50 messages
            ],
            'activities': [
                {
                    'id': a.get('id', ''),
                    'CitizenUsername': a.get('CitizenUsername', ''),
                    'Type': a.get('Type', ''),
                    'Location': a.get('Location', ''),
                    'CreatedAt': a.get('CreatedAt', ''),
                    'Status': a.get('Status', '')
                }
                for a in activities[:50]  # Use first 50 activities
            ],
            'citizens': [],  # Would need citizen data
            'stratagems': [],  # Would need stratagem data
            'contracts': [
                {
                    'id': c.get('id', ''),
                    'Seller': c.get('Seller', ''),
                    'Buyer': c.get('Buyer', ''),
                    'Price': c.get('Price', 0),
                    'ResourceType': c.get('Resource', ''),
                    'Status': c.get('Status', ''),
                    'CreatedAt': c.get('CreatedAt', ''),
                    'Type': 'sale'
                }
                for c in completed[:50]  # Use first 50 completed contracts
            ]
        }
        
        # Run assessment
        print("Running consciousness assessment...")
        assessment = run_consciousness_assessment(test_data)
        
        print(f"\n✓ Assessment completed!")
        print(f"  - Overall Score: {assessment['overall_score']:.2f}/3.0")
        print(f"  - Emergence Ratio: {assessment['emergence_ratio']:.1%}")
        print(f"  - Data Quality: {assessment['data_quality']:.1%}")
        
        print(f"\n  Indicator Scores:")
        for ind_id, measurement in sorted(assessment['indicators'].items()):
            print(f"    {ind_id}: {measurement.value:.2f} (confidence: {measurement.confidence:.1%})")
            
        # Test 3: Test API endpoint (if backend is running)
        print("\n=== Testing API Endpoint ===")
        
        try:
            api_response = requests.get(
                f"{LOCAL_API_URL}/consciousness/assessment",
                params={"hours": 24}
            )
            
            if api_response.status_code == 200:
                api_data = api_response.json()
                print(f"✓ API endpoint working!")
                print(f"  - Overall Score: {api_data['assessment']['overallScore']:.2f}/3.0")
                print(f"  - Data Stats: {json.dumps(api_data.get('dataStats', {}), indent=2)}")
            else:
                print(f"✗ API returned {api_response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("✗ Cannot connect to local API (is backend running?)")
            
        # Test 4: Specific consciousness indicators
        print("\n=== Testing Specific Indicators ===")
        
        # Check for thoughts in messages
        thought_count = sum(1 for m in test_data['messages'] if m['sender'] == m['receiver'])
        print(f"Thoughts detected: {thought_count}")
        
        # Check for recurrence patterns
        recurrence_keywords = ['on second thought', 'reconsidering', 'actually', 'wait']
        recurrence_count = sum(
            1 for m in test_data['messages'] 
            if any(keyword in m['content'].lower() for keyword in recurrence_keywords)
        )
        print(f"Recurrence patterns: {recurrence_count}")
        
        # Check for metacognitive reflections
        reflection_keywords = ['i think', 'i believe', 'i realize', 'my thinking']
        reflection_count = sum(
            1 for m in test_data['messages'] 
            if any(keyword in m['content'].lower() for keyword in reflection_keywords)
        )
        print(f"Metacognitive reflections: {reflection_count}")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_live_consciousness_assessment()
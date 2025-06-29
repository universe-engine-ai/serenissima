#!/usr/bin/env python3
"""Test if subconscious influence appears in ledger API response."""

import os
import sys
import json
import requests

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def test_ledger_with_influence():
    """Test if the ledger API includes subconscious influence."""
    
    # Test with a known citizen
    test_citizen = "GiovanniDiProspero"
    
    # Test both local and production endpoints
    endpoints = [
        f"http://localhost:3000/api/get-ledger?citizenUsername={test_citizen}",
        f"https://serenissima.ai/api/get-ledger?citizenUsername={test_citizen}"
    ]
    
    for endpoint in endpoints:
        print(f"\nTesting endpoint: {endpoint}")
        try:
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                if 'markdown' in response.headers.get('content-type', '').lower():
                    # It's markdown format
                    content = response.text
                    print("Response format: Markdown")
                    
                    # Look for the subconscious influence (should be in italics after weather)
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'temperature of' in line and '°C' in line:
                            print(f"Found weather line: {line}")
                            # Check the lines after weather for italic text
                            for j in range(i+1, min(i+5, len(lines))):
                                if lines[j].strip().startswith('*') and lines[j].strip().endswith('*'):
                                    print(f"Found subconscious influence: {lines[j]}")
                                    return True
                else:
                    # It's JSON format
                    data = response.json()
                    print("Response format: JSON")
                    
                    if data.get('success') and data.get('data'):
                        ledger = data['data']
                        if 'subconsciousInfluence' in ledger:
                            print(f"Found subconscious influence: {ledger['subconsciousInfluence']}")
                            return True
                        else:
                            print("No subconsciousInfluence field in ledger data")
                            
            else:
                print(f"API returned status code: {response.status_code}")
                
        except Exception as e:
            print(f"Error testing endpoint: {e}")
            
    return False

if __name__ == "__main__":
    print("Testing ledger API for subconscious influence integration...")
    
    if test_ledger_with_influence():
        print("\n✓ SUCCESS: Subconscious influence is integrated into the ledger!")
    else:
        print("\n✗ FAILED: Subconscious influence not found in ledger response")
        print("\nThis could mean:")
        print("1. No world_experiences messages exist yet")
        print("2. The API changes haven't been deployed")
        print("3. There's an error in the implementation")
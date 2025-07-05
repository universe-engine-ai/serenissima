#!/usr/bin/env python3
"""
Test API endpoints locally
"""
import requests
import json

# Test both local and production endpoints
endpoints = [
    ("Local", "http://localhost:8001"),
    ("Production", "https://serenissima.ai")
]

test_paths = [
    "/api/governance/grievances",
    "/api/governance/stats",
    "/api/governance/proposals",
    "/api/citizens?limit=1"  # Control test
]

for env_name, base_url in endpoints:
    print(f"\n{'='*60}")
    print(f"Testing {env_name} API ({base_url})")
    print('='*60)
    
    for path in test_paths:
        url = f"{base_url}{path}"
        print(f"\nGET {path}")
        
        try:
            response = requests.get(url, timeout=5)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'grievances' in path:
                    print(f"  Success: Found {len(data.get('grievances', []))} grievances")
                elif 'stats' in path:
                    print(f"  Success: {data}")
                elif 'citizens' in path:
                    print(f"  Success: API is working")
            else:
                print(f"  Error: {response.status_code}")
                if response.headers.get('content-type', '').startswith('application/json'):
                    print(f"  Response: {response.json()}")
                    
        except requests.exceptions.ConnectionError:
            print(f"  Error: Connection refused (server not running?)")
        except requests.exceptions.Timeout:
            print(f"  Error: Request timed out")
        except Exception as e:
            print(f"  Error: {type(e).__name__}: {e}")
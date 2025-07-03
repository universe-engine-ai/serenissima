#!/usr/bin/env python3
"""Check if the Asset field in resources matches citizen username or citizenId."""

import requests
import json

# Get some citizens
citizens_resp = requests.get("https://serenissima.ai/api/citizens?limit=20")
citizens_data = citizens_resp.json()

# Check a few citizens
mismatches = []
for citizen in citizens_data.get('citizens', [])[:10]:
    username = citizen.get('username')
    citizen_id = citizen.get('citizenId')
    
    # Check if they have resources with Asset=username
    resources_resp = requests.get(f"https://serenissima.ai/api/resources?AssetType=citizen&Owner={username}&limit=5")
    resources_data = resources_resp.json()
    
    for resource in resources_data[:5]:
        asset = resource.get('asset')
        if asset != username and asset == citizen_id:
            mismatches.append({
                'username': username,
                'citizenId': citizen_id,
                'resource_asset': asset,
                'type': resource.get('type'),
                'count': resource.get('count')
            })
            break

print(f"Found {len(mismatches)} mismatches where Asset=citizenId instead of username:")
for m in mismatches[:5]:
    print(f"  - {m['username']}: Asset={m['resource_asset']} (should be username)")
    print(f"    Resource: {m['count']} {m['type']}")
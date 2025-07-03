#!/usr/bin/env python3
import json
import requests

# Get timber resources
response = requests.get("https://serenissima.ai/api/resources?Type=timber")
data = response.json()

# Find timber from sources other than myself and BasstheWhale
available_timber = [r for r in data if r.get('owner') not in ['shiren', 'BasstheWhale']]
print(f'Available timber from other sources: {len(available_timber)}')

if available_timber:
    t = available_timber[0]
    print(f"Best timber option: {t['count']} units at {t['asset']} owned by {t['owner']}")
    print(f"ResourceId: {t['resourceId']}")
    print(f"Location: {t.get('location', 'unknown')}")
else:
    print("No suitable timber found")
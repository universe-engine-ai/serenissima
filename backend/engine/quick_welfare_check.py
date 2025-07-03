#!/usr/bin/env python3
"""Quick check of welfare metrics."""

import requests
import json

API_BASE = "https://serenissima.ai/api"

print("=== Quick Welfare Check ===\n")

# Check citizens
response = requests.get(f"{API_BASE}/citizens", timeout=30)
data = response.json()
citizens = data.get('citizens', [])
print(f"Total citizens: {len(citizens)}")

# Check recent problems  
response = requests.get(f"{API_BASE}/problems?status=new&limit=10", timeout=30)
data = response.json()
problems = data.get('problems', [])
print(f"\nRecent problems: {len(problems)}")
for p in problems[:5]:
    print(f"  - {p.get('type')}: {p.get('title', 'No title')}")

# Check bread availability
response = requests.get(f"{API_BASE}/resources?Type=bread", timeout=30)
resources = response.json()
if isinstance(resources, dict):
    resources = resources.get('resources', [])
bread_total = sum(float(r.get('count', 0)) for r in resources)
print(f"\nTotal bread in city: {bread_total:.1f} units")

# Check charity resources
for charity_type in ['pane_della_carità', 'minestra_dei_poveri']:
    response = requests.get(f"{API_BASE}/resources?Type={charity_type}", timeout=30)
    resources = response.json()
    if isinstance(resources, dict):
        resources = resources.get('resources', [])
    if resources:
        total = sum(float(r.get('count', 0)) for r in resources)
        locations = len(set(r.get('location', {}).get('buildingId') for r in resources if r.get('location')))
        print(f"\n{charity_type}: {total:.1f} units at {locations} locations")
    else:
        print(f"\n{charity_type}: Not found")

# Check treasury
response = requests.get(f"{API_BASE}/citizens?username=ConsiglioDeiDieci", timeout=30)
data = response.json()
if data.get('success') and data.get('citizens'):
    treasury = data['citizens'][0].get('ducats', 0)
    print(f"\nTreasury balance: {treasury:,.2f} ducats")
#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
activities = data.get('activities', [])
print(f'Total failed activities shown: {len(activities)}')

# Group by activity type
activity_types = {}
for a in activities:
    t = a.get('type', 'unknown')
    activity_types[t] = activity_types.get(t, 0) + 1

print('\nFailed activity types:')
for k, v in sorted(activity_types.items(), key=lambda x: x[1], reverse=True):
    print(f'  {k}: {v}')

# Show details of recent failures
print('\nRecent failures:')
for a in activities[:5]:
    print(f"  Type: {a.get('type')} - Citizen: {a.get('citizen')}")
    if a.get('notes'):
        print(f"    Notes: {a.get('notes')[:100]}")
    if a.get('description'):
        print(f"    Description: {a.get('description')[:100]}")
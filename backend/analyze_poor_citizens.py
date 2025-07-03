#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
citizens = data.get('citizens', [])

# Find poor citizens
poor = [c for c in citizens if c.get('Wealth', 0) < 50]
poor_ai = [c for c in poor if c.get('IsAI')]

print(f'Total citizens with wealth < 50: {len(poor)}')
print(f'AI citizens with wealth < 50: {len(poor_ai)}')

# Check broader wealth levels
wealth_ranges = {
    '<100': 0, '<500': 0, '<1000': 0, '<5000': 0, '>=5000': 0
}

ai_citizens = [c for c in citizens if c.get('IsAI')]
for c in ai_citizens:
    w = c.get('Wealth', 0)
    if w < 100:
        wealth_ranges['<100'] += 1
    elif w < 500:
        wealth_ranges['<500'] += 1
    elif w < 1000:
        wealth_ranges['<1000'] += 1
    elif w < 5000:
        wealth_ranges['<5000'] += 1
    else:
        wealth_ranges['>=5000'] += 1

print(f'\nAI citizen wealth distribution (total: {len(ai_citizens)}):')
for k, v in wealth_ranges.items():
    print(f'  {k} ducats: {v} citizens')

# Show poorest AI citizens
print('\nPoorest AI citizens:')
poorest_ai = sorted(ai_citizens, key=lambda x: x.get('Wealth', 0))[:10]
for c in poorest_ai:
    print(f"  {c['Name']} - Wealth: {c.get('Wealth', 0)} - Job: {c.get('Employment', 'None')} - Class: {c.get('SocialClass', 'Unknown')}")
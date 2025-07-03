#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
citizens = data.get('citizens', [])
print(f'Total unemployed: {len(citizens)}')

ai_unemployed = [c for c in citizens if c.get('IsAI')]
print(f'AI unemployed: {len(ai_unemployed)}')

for c in ai_unemployed[:10]:
    print(f"  {c['Name']} - Wealth: {c.get('Wealth', 0)} - Class: {c.get('SocialClass', 'Unknown')}")
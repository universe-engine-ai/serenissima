#!/usr/bin/env python3
import json
import sys
from collections import defaultdict

data = json.load(sys.stdin)
problems = data.get('problems', [])

# Group problems by citizen
citizen_problems = defaultdict(list)
for p in problems:
    citizen = p.get('citizen', 'Unknown')
    citizen_problems[citizen].append(p)

# Find citizens with most problems
problem_counts = [(cit, len(probs)) for cit, probs in citizen_problems.items()]
problem_counts.sort(key=lambda x: x[1], reverse=True)

print(f'Citizens with most problems:')
for citizen, count in problem_counts[:10]:
    print(f'  {citizen}: {count} problems')
    # Show their problem types
    types = defaultdict(int)
    for p in citizen_problems[citizen]:
        types[p.get('type', 'unknown')] += 1
    print(f'    Types: {dict(types)}')

# Analyze hunger problems specifically
print('\nHunger crisis analysis:')
hunger_problems = [p for p in problems if 'hungry' in p.get('type', '')]
print(f'Total hunger-related problems: {len(hunger_problems)}')

# Get unique hungry citizens
hungry_citizens = set()
for p in hunger_problems:
    if p.get('type') == 'hungry_citizen':
        hungry_citizens.add(p.get('citizen'))
print(f'Unique hungry citizens: {len(hungry_citizens)}')

# Sample hungry citizen details
print('\nSample hungry citizens:')
for p in [p for p in problems if p.get('type') == 'hungry_citizen'][:5]:
    print(f"  {p.get('citizen')} - {p.get('description', 'No description')}")
#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
problems = data.get('problems', [])
print(f'Total active problems: {len(problems)}')

problem_types = {}
for p in problems:
    t = p.get('type', 'unknown')
    problem_types[t] = problem_types.get(t, 0) + 1

print('\nProblem types:')
for k, v in sorted(problem_types.items(), key=lambda x: x[1], reverse=True):
    print(f'  {k}: {v}')

# Show top 5 problems by severity
print('\nTop problems by severity:')
severe_problems = sorted(problems, key=lambda x: {'Critical': 3, 'High': 2, 'Medium': 1}.get(x.get('severity', 'Medium'), 0), reverse=True)
for p in severe_problems[:5]:
    print(f"  [{p.get('severity')}] {p.get('type')} - {p.get('title', 'No title')}")
    print(f"    Citizen: {p.get('citizen')} at {p.get('location', 'Unknown location')}")
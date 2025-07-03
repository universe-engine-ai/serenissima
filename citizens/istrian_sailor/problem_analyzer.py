#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
problems = data.get('problems', [])
problem_types = {}

for p in problems:
    desc = p.get('description', '')
    if 'delivery' in desc.lower():
        problem_types['delivery'] = problem_types.get('delivery', 0) + 1
    elif 'out of stock' in desc.lower():
        problem_types['out_of_stock'] = problem_types.get('out_of_stock', 0) + 1
    elif 'missing input' in desc.lower():
        problem_types['missing_inputs'] = problem_types.get('missing_inputs', 0) + 1
    elif 'contract' in desc.lower():
        problem_types['contracts'] = problem_types.get('contracts', 0) + 1
    else:
        problem_types['other'] = problem_types.get('other', 0) + 1

print('Problem breakdown:')
for k, v in sorted(problem_types.items(), key=lambda x: x[1], reverse=True):
    print(f'- {k}: {v}')
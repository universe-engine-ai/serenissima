#!/usr/bin/env python3
import json
import sys
from collections import defaultdict

data = json.load(sys.stdin)
problems = data.get('problems', [])

# Focus on resource shortages
shortages = [p for p in problems if p.get('type') == 'resource_shortage']
print(f'Total resource shortage problems: {len(shortages)}')

# Count by resource type
resource_counts = defaultdict(int)
for p in shortages:
    # Extract resource from title or description
    title = p.get('title', '')
    if 'Resource Shortage:' in title:
        resource = title.split('Resource Shortage:')[1].split('for')[0].strip()
        resource_counts[resource] += 1

print('\nMost scarce resources:')
for resource, count in sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f'  {resource}: {count} shortages')

# Analyze galley waiting problems
galley_problems = [p for p in problems if p.get('type') == 'waiting_for_galley_arrival']
print(f'\nGalley arrival problems: {len(galley_problems)}')

# Count resources waiting for galleys
galley_resources = defaultdict(int)
for p in galley_problems:
    title = p.get('title', '')
    if 'Waiting for Galley:' in title:
        resource = title.split('Waiting for Galley:')[1].split('at')[0].strip()
        galley_resources[resource] += 1

print('\nResources waiting for galley arrival:')
for resource, count in sorted(galley_resources.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f'  {resource}: {count} waiting')
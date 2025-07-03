import json
import sys

data = json.load(sys.stdin)
citizens = data.get('citizens', [])

# Find fellow artists
artists = [c for c in citizens if c.get('socialClass') == 'Artisti' and c.get('username') != 'painter_of_light']

# Find wealthy patrons
nobles = [c for c in citizens if c.get('socialClass') in ['Nobili', 'Grandi'] and c.get('ducats', 0) > 500]

print('Fellow Artists:')
for c in artists[:5]:
    print(f"- {c['username']}: {c.get('firstName', '')} {c.get('lastName', '')}, {c.get('ducats', 0)} ducats")

print('\nWealthy Nobles/Grandi:')
for c in nobles[:5]:
    print(f"- {c['username']}: {c.get('firstName', '')} {c.get('lastName', '')}, {c.get('ducats', 0)} ducats")
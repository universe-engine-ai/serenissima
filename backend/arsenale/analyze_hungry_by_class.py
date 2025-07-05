import json
import sys
import requests
from datetime import datetime, timezone

# Fetch citizens data
response = requests.get("https://serenissima.ai/api/citizens?inVenice=true")
data = response.json()
citizens = data['citizens']

# Filter hungry citizens
hungry_citizens = [c for c in citizens if c.get('isHungry')]

print(f'Total hungry citizens: {len(hungry_citizens)} out of {len(citizens)}')
print(f'Hunger rate: {len(hungry_citizens)/len(citizens)*100:.1f}%')

# Current Venice time
print(f'\nCurrent Venice time: 18:15 (Saturday)')
print('\nLeisure time status:')
print('- Nobili: IN LEISURE TIME (15:00-20:00)')
print('- Cittadini: IN LEISURE TIME (17:00-21:00)')
print('- Popolani: NOT YET (starts at 19:00)')
print('- Facchini: NOT YET (starts at 20:00)')
print('- Forestieri: IN LEISURE TIME (15:00-23:00)')

# Analyze hungry citizens by class
class_breakdown = {}
for c in hungry_citizens:
    social_class = c.get('socialClass', 'Unknown')
    if social_class not in class_breakdown:
        class_breakdown[social_class] = []
    class_breakdown[social_class].append(c)

print('\nHungry citizens by social class:')
for sc, citizens_list in sorted(class_breakdown.items()):
    print(f'\n{sc}: {len(citizens_list)} hungry')
    for c in citizens_list[:5]:  # Show first 5
        username = c.get('username', 'Unknown')
        ate_at = c.get('ateAt', 'Never')
        wealth = c.get('wealth', 0)
        
        # Calculate hours since meal
        hours = 'Unknown'
        if ate_at and ate_at != 'Never':
            try:
                ate_dt = datetime.fromisoformat(ate_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                hours = round((now - ate_dt).total_seconds() / 3600, 1)
            except:
                pass
        
        print(f'  - {username}: Last ate {hours} hours ago, {wealth} ducats')
    if len(citizens_list) > 5:
        print(f'  ... and {len(citizens_list) - 5} more')

# Summary of why they can't eat
print('\n' + '='*60)
print('ANALYSIS: Why are they still hungry?')
print('='*60)
print('\nPopolani (7) and Facchini (10) cannot eat until their leisure time:')
print('- Popolani: Must wait until 19:00 (45 minutes from now)')
print('- Facchini: Must wait until 20:00 (1 hour 45 minutes from now)')
print('\nThese 17 citizens are constrained by the leisure time system.')
print('The emergency eating mechanism should bypass this for citizens')
print('who haven\'t eaten in >24 hours, but let\'s check if it\'s working...')
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
from pyairtable import Api
from datetime import datetime, timezone
import pytz

# Initialize Airtable
api_key = os.environ.get('AIRTABLE_API_KEY')
base_id = os.environ.get('AIRTABLE_BASE_ID')
api = Api(api_key)
citizens_table = api.table(base_id, 'CITIZENS')
activities_table = api.table(base_id, 'ACTIVITIES')

# Check current time
now_utc = datetime.now(timezone.utc)
venice_tz = pytz.timezone('Europe/Rome')
now_venice = now_utc.astimezone(venice_tz)
print(f'Current Venice time: {now_venice.strftime("%H:%M")} ({now_venice.strftime("%A, %B %d, %Y")})')

# Get hungry citizens
hungry_citizens = citizens_table.all(formula="{IsHungry}=TRUE()")
print(f'\nTotal hungry citizens: {len(hungry_citizens)}')

# Analyze each hungry citizen
print('\nDetailed analysis of hungry citizens:')
print('=' * 100)

for citizen in hungry_citizens:
    fields = citizen['fields']
    username = fields.get('Username', 'Unknown')
    social_class = fields.get('SocialClass', 'Unknown')
    ate_at = fields.get('AteAt', 'Never')
    wealth = fields.get('Wealth', 0)
    
    # Calculate hours since last meal
    hours_since_meal = 'Unknown'
    if ate_at and ate_at != 'Never':
        try:
            ate_dt = datetime.fromisoformat(ate_at.replace('Z', '+00:00'))
            hours_since_meal = round((now_utc - ate_dt).total_seconds() / 3600, 1)
        except:
            pass
    
    # Check current activities
    activity_formula = f"AND({{CitizenId}}='{fields.get('CitizenId')}', OR({{Status}}='created', {{Status}}='in_progress', {{Status}}='pending'))"
    current_activities = activities_table.all(formula=activity_formula)
    
    print(f'\n{username} ({social_class}):')
    print(f'  Last ate: {ate_at} ({hours_since_meal} hours ago)')
    print(f'  Wealth: {wealth} ducats')
    print(f'  Current activities: {len(current_activities)}')
    
    if current_activities:
        for act in current_activities:
            act_fields = act['fields']
            print(f"    - {act_fields.get('Type')} (Status: {act_fields.get('Status')})")

# Check leisure time windows
print('\n\nLeisure time windows by social class:')
print('=' * 50)
print('Nobili: 15:00-20:00 (3:00 PM - 8:00 PM)')
print('Cittadini: 17:00-21:00 (5:00 PM - 9:00 PM)')
print('Popolani: 19:00-22:00 (7:00 PM - 10:00 PM)')
print('Facchini: 20:00-22:00 (8:00 PM - 10:00 PM)')
print('Forestieri: 15:00-23:00 (3:00 PM - 11:00 PM)')

# Check if it's currently leisure time for any class
current_hour = now_venice.hour
print(f'\nCurrent hour: {current_hour}:00')
if 15 <= current_hour < 20:
    print('  - Leisure time for: Nobili, Forestieri')
if 17 <= current_hour < 21:
    print('  - Leisure time for: Cittadini')
if 19 <= current_hour < 22:
    print('  - Leisure time for: Popolani')
if 20 <= current_hour < 22:
    print('  - Leisure time for: Facchini')
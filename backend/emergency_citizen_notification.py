#!/usr/bin/env python3
"""
Emergency notification to alert all hungry citizens about free food locations
"""

import os
import sys
from datetime import datetime
import pytz
from pyairtable import Table
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to sys.path
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def send_emergency_notifications():
    """Send urgent notifications to all hungry citizens about free food"""
    
    # Initialize tables
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = 'appMs6MLXbdAYE8wW'
    
    citizens_table = Table(api_key, base_id, 'CITIZENS')
    notifications_table = Table(api_key, base_id, 'NOTIFICATIONS')
    
    # Venice timezone
    venice_tz = pytz.timezone('Europe/Rome')
    now_venice = datetime.now(venice_tz)
    
    # Get all hungry citizens
    hungry_citizens = citizens_table.all(formula="{LastAte} < DATEADD(NOW(), -6, 'hours')")
    
    print(f"Found {len(hungry_citizens)} hungry citizens")
    
    # Message about free food
    urgent_message = """🚨 URGENT: FREE FOOD AVAILABLE NOW! 🍞

La Mensa del Doge provides FREE FOOD at:
• land_45.425015_12.329460 (grain)
• building_45.429640_12.360838 (meat, grain, vegetables)  
• land_45.441394_12.321051 (meat, grain)

Go immediately! First come, first served. 
Look for 'charity_food' contracts - they cost NOTHING!

Your survival matters. Eat first, philosophize later."""

    # Create notifications for each hungry citizen
    created = 0
    for citizen in hungry_citizens:
        try:
            notification = {
                'citizenId': citizen['id'],
                'Type': 'emergency',
                'Title': '🚨 FREE FOOD AVAILABLE - GO NOW!',
                'Content': urgent_message,
                'Timestamp': now_venice.isoformat(),
                'IsRead': False,
                'Priority': 10  # Highest priority
            }
            
            notifications_table.create(notification)
            created += 1
            
        except Exception as e:
            print(f"Error notifying {citizen['fields'].get('Username', 'Unknown')}: {e}")
    
    print(f"Created {created} emergency notifications")
    
    # Also create a public notification
    public_notification = {
        'Type': 'public',
        'Title': '🚨 LA MENSA DEL DOGE - FREE FOOD FOR ALL HUNGRY CITIZENS',
        'Content': urgent_message + "\n\nSpread the word! Save your neighbors!",
        'Timestamp': now_venice.isoformat(),
        'IsRead': False,
        'Priority': 10
    }
    
    notifications_table.create(public_notification)
    print("Created public emergency notification")

if __name__ == "__main__":
    send_emergency_notifications()
#!/usr/bin/env python3
"""
Check the current hunger status of citizens
"""

import requests
import json
from datetime import datetime, timezone
import pytz

# Venice timezone
VENICE_TIMEZONE = pytz.timezone('Europe/Rome')

# API endpoints
API_BASE = "https://serenissima.ai/api"

def main():
    print("=== Checking Citizen Hunger Status ===")
    print(f"Time: {datetime.now(VENICE_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} Venice Time")
    
    try:
        # Get all citizens
        response = requests.get(f"{API_BASE}/citizens")
        citizens_data = response.json()
        
        # Handle API response format
        if isinstance(citizens_data, dict) and 'citizens' in citizens_data:
            citizens_data = citizens_data['citizens']
        
        print(f"\nTotal citizens: {len(citizens_data)}")
        
        hungry_count = 0
        ai_hungry_count = 0
        severely_hungry = []
        now_utc = datetime.now(timezone.utc)
        
        for citizen in citizens_data:
            if citizen.get('IsHungry'):
                hungry_count += 1
                if citizen.get('IsAI'):
                    ai_hungry_count += 1
                
                # Check hours since last meal
                ate_at_str = citizen.get('AteAt')
                hours_since_meal = None
                if ate_at_str:
                    try:
                        ate_at_dt = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
                        if ate_at_dt.tzinfo is None:
                            ate_at_dt = pytz.UTC.localize(ate_at_dt)
                        hours_since_meal = (now_utc - ate_at_dt).total_seconds() / 3600
                    except:
                        pass
                
                if hours_since_meal is None or hours_since_meal > 24:
                    severely_hungry.append({
                        'name': citizen.get('Name', citizen.get('Username')),
                        'username': citizen.get('Username'),
                        'is_ai': citizen.get('IsAI'),
                        'hours': hours_since_meal if hours_since_meal else 999,
                        'ducats': citizen.get('Ducats', 0),
                        'social_class': citizen.get('SocialClass', 'Unknown')
                    })
        
        print(f"Hungry citizens: {hungry_count}")
        print(f"Hungry AI citizens: {ai_hungry_count}")
        print(f"Severely hungry (>24h): {len(severely_hungry)}")
        
        if severely_hungry:
            # Sort by hours without food
            severely_hungry.sort(key=lambda x: x['hours'], reverse=True)
            
            print("\nSeverely Hungry Citizens (>24 hours without food):")
            for i, citizen in enumerate(severely_hungry[:20]):  # Show top 20
                ai_str = "[AI]" if citizen['is_ai'] else "[Human]"
                print(f"  {i+1}. {ai_str} {citizen['name']} ({citizen['social_class']}): "
                      f"{citizen['hours']:.1f}h without food, {citizen['ducats']:.0f} ducats")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
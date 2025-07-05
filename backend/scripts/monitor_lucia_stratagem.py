#!/usr/bin/env python3
"""
Monitor LuciaMancini's collective grain delivery stratagem in real-time.
Shows current status, recent activities, and helps debug any issues.
"""
import os
import sys
import logging
import json
from datetime import datetime, timedelta
import pytz
import time

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_stratagem_summary(tables, stratagem_id):
    """Get a summary of the stratagem status."""
    formula = f"{{StratagemId}}='{stratagem_id}'"
    stratagems = list(tables['stratagems'].all(formula=formula))
    
    if not stratagems:
        return None
    
    stratagem = stratagems[0]
    details = json.loads(stratagem['fields'].get('Notes', '{}'))
    
    summary = {
        'name': stratagem['fields'].get('Name', 'Unknown'),
        'status': stratagem['fields'].get('Status'),
        'collected': details.get('collected_amount', 0),
        'max_amount': details.get('max_total_amount', 0),
        'participants': len(details.get('participants', [])),
        'deliveries': len(details.get('deliveries', [])),
        'rewards_paid': details.get('total_rewards_paid', 0),
        'reward_per_unit': details.get('reward_per_unit', 0),
        'expires_at': stratagem['fields'].get('ExpiresAt'),
        'target_building': details.get('target', {}).get('building_name', 'Unknown'),
        'last_update': stratagem['fields'].get('UpdatedDate')
    }
    
    return summary

def get_recent_activities(tables, building_id, minutes=30):
    """Get recent delivery activities to the target building."""
    time_ago = datetime.now(pytz.utc) - timedelta(minutes=minutes)
    
    formula = (
        f"AND("
        f"  {{ToBuilding}}='{building_id}',"
        f"  OR("
        f"    {{Type}}='deliver_to_storage',"
        f"    {{Type}}='deliver'"
        f"  ),"
        f"  IS_AFTER({{CreatedDate}}, '{time_ago.isoformat()}')"
        f")"
    )
    
    activities = list(tables['activities'].all(formula=formula))
    
    activity_summary = []
    for activity in activities:
        try:
            notes = json.loads(activity['fields'].get('Notes', '{}'))
            resource_type = notes.get('resource_type', 'Unknown')
            amount = notes.get('amount', 0)
        except:
            resource_type = 'Unknown'
            amount = 0
        
        activity_summary.append({
            'id': activity['id'],
            'citizen': activity['fields'].get('Citizen', 'Unknown'),
            'status': activity['fields'].get('Status'),
            'resource': resource_type,
            'amount': amount,
            'created': activity['fields'].get('CreatedDate'),
            'start': activity['fields'].get('StartDate'),
            'end': activity['fields'].get('EndDate')
        })
    
    return activity_summary

def get_grain_holders(tables, limit=5):
    """Get citizens with the most grain."""
    grain_resources = list(tables['resources'].all(
        formula=f"AND({{ResourceType}}='grain', {{Amount}}>0)",
        sort=['-Amount'],
        max_records=limit
    ))
    
    holders = []
    for resource in grain_resources:
        holders.append({
            'owner': resource['fields'].get('Owner', 'Unknown'),
            'amount': resource['fields'].get('Amount', 0),
            'building': resource['fields'].get('Building', 'Unknown')
        })
    
    return holders

def display_dashboard(stratagem_summary, recent_activities, grain_holders):
    """Display a dashboard with current status."""
    clear_screen()
    
    print("╔" + "═" * 78 + "╗")
    print("║" + " LUCIA MANCINI'S GRAIN DELIVERY STRATAGEM MONITOR".center(78) + "║")
    print("╠" + "═" * 78 + "╣")
    
    if not stratagem_summary:
        print("║" + " STRATAGEM NOT FOUND!".center(78) + "║")
        print("╚" + "═" * 78 + "╝")
        return
    
    # Status section
    status_color = "\033[92m" if stratagem_summary['status'] == 'active' else "\033[91m"
    print(f"║ Status: {status_color}{stratagem_summary['status'].upper()}\033[0m".ljust(87) + "║")
    
    # Progress bar
    progress = (stratagem_summary['collected'] / stratagem_summary['max_amount']) * 100 if stratagem_summary['max_amount'] > 0 else 0
    bar_length = 50
    filled = int(bar_length * progress / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    print(f"║ Progress: [{bar}] {progress:.1f}%".ljust(79) + "║")
    print(f"║ Collected: {stratagem_summary['collected']}/{stratagem_summary['max_amount']} grain".ljust(79) + "║")
    
    # Stats
    print("╠" + "═" * 78 + "╣")
    print(f"║ Participants: {stratagem_summary['participants']}".ljust(39) + "│" + f" Total Deliveries: {stratagem_summary['deliveries']}".ljust(39) + "║")
    print(f"║ Reward/Unit: {stratagem_summary['reward_per_unit']} ducats".ljust(39) + "│" + f" Total Paid: {stratagem_summary['rewards_paid']} ducats".ljust(39) + "║")
    print(f"║ Target: {stratagem_summary['target_building']}".ljust(79) + "║")
    
    # Expiration
    if stratagem_summary['expires_at']:
        expires_dt = datetime.fromisoformat(stratagem_summary['expires_at'].replace('Z', '+00:00'))
        time_left = expires_dt - datetime.now(pytz.utc)
        hours_left = int(time_left.total_seconds() / 3600)
        minutes_left = int((time_left.total_seconds() % 3600) / 60)
        
        if time_left.total_seconds() > 0:
            print(f"║ Time Remaining: {hours_left}h {minutes_left}m".ljust(79) + "║")
        else:
            print(f"║ \033[91mEXPIRED!\033[0m".ljust(88) + "║")
    
    # Recent Activities
    print("╠" + "═" * 78 + "╣")
    print("║" + " RECENT ACTIVITIES (Last 30 min)".center(78) + "║")
    print("╠" + "═" * 78 + "╣")
    
    if recent_activities:
        for act in recent_activities[:5]:
            status_icon = "✓" if act['status'] == 'completed' else "→" if act['status'] == 'in_progress' else "✗"
            line = f"║ {status_icon} {act['citizen']}: {act['amount']} {act['resource']} - {act['status']}".ljust(79) + "║"
            print(line)
    else:
        print("║" + " No recent delivery activities".center(78) + "║")
    
    # Top Grain Holders
    print("╠" + "═" * 78 + "╣")
    print("║" + " TOP GRAIN HOLDERS IN VENICE".center(78) + "║")
    print("╠" + "═" * 78 + "╣")
    
    if grain_holders:
        for holder in grain_holders:
            line = f"║ {holder['owner']}: {holder['amount']} grain".ljust(79) + "║"
            print(line)
    else:
        print("║" + " No grain found in Venice!".center(78) + "║")
    
    # Footer
    print("╚" + "═" * 78 + "╝")
    
    # Last update
    if stratagem_summary['last_update']:
        print(f"\nLast Update: {stratagem_summary['last_update']}")
    
    print(f"Current Time: {datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("\nPress Ctrl+C to exit. Refreshing every 10 seconds...")

def main():
    """Main monitoring loop."""
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    tables = {
        'stratagems': api.table(base_id, 'STRATAGEMS'),
        'citizens': api.table(base_id, 'CITIZENS'),
        'buildings': api.table(base_id, 'BUILDINGS'),
        'resources': api.table(base_id, 'RESOURCES'),
        'activities': api.table(base_id, 'ACTIVITIES')
    }
    
    # The stratagem details
    stratagem_id = "collective_delivery_LuciaMancini_1751720658"
    target_building_id = "building_45.43735680581042_12.326245881522368"  # Automated Mill
    
    try:
        while True:
            # Get current data
            stratagem_summary = get_stratagem_summary(tables, stratagem_id)
            recent_activities = get_recent_activities(tables, target_building_id)
            grain_holders = get_grain_holders(tables)
            
            # Display dashboard
            display_dashboard(stratagem_summary, recent_activities, grain_holders)
            
            # Wait before refreshing
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()
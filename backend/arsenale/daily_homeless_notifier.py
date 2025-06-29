#!/usr/bin/env python3
"""
Daily automated homeless notification system
Runs once per day to notify wealthy citizens about homeless citizens
"""

import requests
import json
from datetime import datetime
import os
import sys

# Add parent directory to path to import from direct_homeless_check
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from direct_homeless_check import find_homeless_citizens, find_rich_citizens, generate_message_to_rich_citizen, send_message_via_api

def load_notification_history():
    """Load history of who has been notified"""
    history_file = "homeless_notification_history.json"
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return json.load(f)
    return {"notified_citizens": [], "last_run": None}

def save_notification_history(history):
    """Save notification history"""
    history_file = "homeless_notification_history.json"
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

def main():
    print(f"=== Daily Homeless Notification System ===")
    print(f"Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load history
    history = load_notification_history()
    
    # Find homeless citizens
    homeless = find_homeless_citizens()
    print(f"\nFound {len(homeless)} homeless citizens")
    
    if not homeless:
        print("No homeless citizens found. Exiting.")
        history["last_run"] = datetime.now().isoformat()
        save_notification_history(history)
        return
    
    # Find rich citizens
    rich = find_rich_citizens()
    print(f"Found {len(rich)} wealthy citizens")
    
    if not rich:
        print("No wealthy citizens found. Exiting.")
        history["last_run"] = datetime.now().isoformat()
        save_notification_history(history)
        return
    
    # Find a wealthy citizen who hasn't been notified recently
    target_citizen = None
    for wealthy in rich:
        username = wealthy['username']
        # Skip if already notified in the last 7 days
        if username not in [n['username'] for n in history.get('notified_citizens', [])]:
            target_citizen = wealthy
            break
        else:
            # Check if notification was more than 7 days ago
            for notif in history['notified_citizens']:
                if notif['username'] == username:
                    notif_date = datetime.fromisoformat(notif['date'])
                    if (datetime.now() - notif_date).days > 7:
                        target_citizen = wealthy
                        break
    
    if not target_citizen:
        print("All wealthy citizens have been notified recently. Cycling back to the richest.")
        target_citizen = rich[0]
    
    # Generate and send message
    message = generate_message_to_rich_citizen(target_citizen, homeless)
    
    print(f"\nSending message to: {target_citizen['username']} (Ducats: {target_citizen['ducats']:,})")
    
    # Send the message
    success = send_message_via_api("ConsiglioDeiDieci", target_citizen['username'], message)
    
    if success:
        # Update history
        history['notified_citizens'].append({
            'username': target_citizen['username'],
            'date': datetime.now().isoformat(),
            'homeless_count': len(homeless)
        })
        # Keep only last 20 notifications
        history['notified_citizens'] = history['notified_citizens'][-20:]
        history['last_run'] = datetime.now().isoformat()
        save_notification_history(history)
    else:
        print("Failed to send message.")
    
    print("\n=== Daily notification complete ===")

if __name__ == "__main__":
    main()
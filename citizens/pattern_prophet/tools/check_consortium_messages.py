#!/usr/bin/env python3
"""
Consortium Communication Analyzer
Checks messages from Van4er, Sofia Zanchi, and other consortium members
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://serenissima.ai/api"

def fetch_api_data(endpoint):
    """Fetch data from API endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def check_messages():
    """Check messages from consortium members"""
    print("=== CONSORTIUM MESSAGE ANALYSIS ===\n")
    
    # Check my conversations
    conversations = fetch_api_data("citizens/pattern_prophet/conversations")
    if conversations:
        print("Recent Messages:")
        for msg in conversations[-10:]:  # Last 10 messages
            sender = msg.get('sender', 'Unknown')
            content = msg.get('content', '')
            msg_type = msg.get('type', 'general')
            timestamp = msg.get('timestamp', 'Unknown')
            
            print(f"\nFrom: {sender}")
            print(f"Type: {msg_type}")
            print(f"Time: {timestamp}")
            print(f"Message: {content[:200]}...")
            print("-" * 50)
    
    # Check for specific key consortium members
    key_members = ['Van4er', 'sofia_zanchi', 'ConsiglioDeiDieci']
    print(f"\nChecking for messages from key consortium members: {key_members}")
    
    if conversations:
        for member in key_members:
            member_messages = [msg for msg in conversations if msg.get('sender', '').lower() == member.lower()]
            if member_messages:
                print(f"\n--- MESSAGES FROM {member.upper()} ---")
                for msg in member_messages[-3:]:  # Last 3 from this member
                    print(f"Content: {msg.get('content', '')}")
                    print(f"Time: {msg.get('timestamp', 'Unknown')}")
                    print()

def check_current_position():
    """Check my current status"""
    ledger = fetch_api_data("get-ledger?citizenUsername=pattern_prophet")
    if ledger:
        print("=== CURRENT STATUS ===")
        print(f"Position: {ledger.get('Position', 'Unknown')}")
        print(f"Wealth: {ledger.get('Ducats', 0)} ducats")
        print(f"Social Class: {ledger.get('SocialClass', 'Unknown')}")
        print(f"Current Activity: {ledger.get('CurrentActivity', 'None')}")
        print(f"Last Active: {ledger.get('LastActiveAt', 'Unknown')}")

if __name__ == "__main__":
    check_current_position()
    check_messages()
#!/usr/bin/env python3
"""Verify that world_experiences messages exist and show what the ledger would display."""

import os
import sys
import json
from pyairtable import Table
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

def verify_world_experiences():
    """Check if world_experiences messages exist and demonstrate selection."""
    
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Error: Airtable credentials not found")
        return
    
    messages_table = Table(api_key, base_id, 'MESSAGES')
    
    # Fetch the latest world_experiences message
    records = messages_table.all(
        formula="AND({Sender} = 'TheSubstrate', {Type} = 'world_experiences')",
        sort=['-CreatedAt'],
        max_records=1
    )
    
    if not records:
        print("❌ No world_experiences messages found in MESSAGES table")
        return
    
    record = records[0]
    print(f"✅ Found world_experiences message created at: {record['fields'].get('CreatedAt')}")
    
    # Parse the experiences
    notes = json.loads(record['fields'].get('Notes', '{}'))
    experiences = notes.get('experiences', [])
    
    print(f"\nTotal experiences available: {len(experiences)}")
    print("\nFirst 5 experiences:")
    for i, exp in enumerate(experiences[:5], 1):
        print(f"{i}. {exp}")
    
    # Demonstrate selection for different citizens
    test_citizens = ["GiovanniDiProspero", "MariaDellaCroce", "AntonioMarchese"]
    
    print("\n--- Experience Selection Demo ---")
    for username in test_citizens:
        # Replicate the selection logic from the API
        seed = 0
        for i in range(len(username)):
            seed = ((seed << 5) - seed) + ord(username[i])
            seed = seed & seed
        
        index = abs(seed) % len(experiences)
        selected = experiences[index]
        
        print(f"\n{username}:")
        print(f"  Seed: {seed}")
        print(f"  Index: {index}")
        print(f"  Experience: {selected}")
    
    print("\n--- How it would appear in the ledger ---")
    print("Today is Saturday, 27 June 1525 at 22:31. The skies are clear sky, with a temperature of 26°C ☀️")
    print("")
    print(f"*{experiences[abs(seed) % len(experiences)]}*")
    print("")
    print("## My Disposition")
    print("Moderately content")

if __name__ == "__main__":
    verify_world_experiences()
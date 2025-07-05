#!/usr/bin/env python3
"""
Emergency script to deliver grain to the automated mill
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Table
from dotenv import load_dotenv
import json
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Airtable setup
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Tables
resources_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "RESOURCES")
buildings_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "BUILDINGS")

def main():
    print("🌾 Emergency Grain Delivery to Automated Mill")
    
    # Find the automated mill
    mill_id = "building_45.43735680581042_12.326245881522368"
    
    # Get all grain resources
    all_resources = resources_table.all()
    grain_resources = [r for r in all_resources if r['fields'].get('Type', '').lower() == 'grain']
    
    print(f"Found {len(grain_resources)} grain units")
    
    if not grain_resources:
        print("❌ No grain found!")
        return
    
    # Move up to 10 grain units to the mill
    moved_count = 0
    for grain in grain_resources[:10]:
        try:
            # Update the grain's container to the mill
            resources_table.update(grain['id'], {
                'Asset': mill_id,
                'Notes': f"Emergency delivery to automated mill at {datetime.now(timezone.utc).isoformat()}"
            })
            moved_count += 1
            print(f"✅ Moved grain {grain['id']} to mill")
        except Exception as e:
            print(f"❌ Failed to move grain {grain['id']}: {e}")
    
    print(f"\n📊 Summary: Moved {moved_count} grain units to automated mill")
    print("The mill should now be able to produce bread on the next automation cycle!")

if __name__ == "__main__":
    main()
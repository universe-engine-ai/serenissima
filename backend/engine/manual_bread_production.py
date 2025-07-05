#!/usr/bin/env python3
"""
Manual bread production for the automated mill
Creates bread directly from grain at the mill
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Table
from dotenv import load_dotenv
import json
from datetime import datetime, timezone
import uuid

# Load environment variables
load_dotenv()

# Airtable setup
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Tables
resources_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "RESOURCES")

def main():
    print("🍞 Manual Bread Production at Automated Mill")
    
    # Mill info
    mill_id = "building_45.43735680581042_12.326245881522368"
    mill_position = {"lat": 45.43735680581042, "lng": 12.326245881522368}
    
    # Get grain at mill
    all_resources = resources_table.all()
    grain_at_mill = [r for r in all_resources 
                     if r['fields'].get('Type', '').lower() == 'grain' 
                     and r['fields'].get('Asset') == mill_id]
    
    print(f"Found {len(grain_at_mill)} grain units at mill")
    
    if not grain_at_mill:
        print("❌ No grain at mill!")
        return
    
    # Calculate bread production (with 1.09x efficiency)
    total_grain = sum(r['fields'].get('Count', 1) for r in grain_at_mill)
    bread_to_produce = int(total_grain * 1.09)  # 1.09x efficiency multiplier
    
    print(f"Converting {total_grain} grain → {bread_to_produce} bread (1.09x efficiency)")
    
    # Create bread resource directly in Airtable
    try:
        bread_payload = {
            'ResourceId': f"resource-bread-{uuid.uuid4()}",
            'Type': 'bread',
            'Name': 'Bread',
            'Count': bread_to_produce,
            'Asset': mill_id,
            'AssetType': 'building',
            'Owner': 'ConsiglioDeiDieci',
            'CreatedAt': datetime.now(timezone.utc).isoformat(),
            'Notes': json.dumps({
                "production": f"Automated mill production with 1.09x efficiency",
                "grainConsumed": total_grain
            })
        }
        
        new_bread = resources_table.create(bread_payload)
        print(f"✅ Created {bread_to_produce} bread at mill!")
        
        # Mark grain as consumed
        for grain in grain_at_mill:
            try:
                resources_table.update(grain['id'], {
                    'DecayedAt': datetime.now(timezone.utc).isoformat(),
                    'Notes': json.dumps({"consumed": "Used in bread production"})
                })
            except Exception as e:
                print(f"Warning: Failed to mark grain {grain['id']} as consumed: {e}")
        
        print(f"✅ Marked {len(grain_at_mill)} grain units as consumed")
        
    except Exception as e:
        print(f"❌ Failed to create bread: {e}")

if __name__ == "__main__":
    main()
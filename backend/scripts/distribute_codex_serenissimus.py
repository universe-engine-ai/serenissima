#!/usr/bin/env python3
"""
Distributes copies of the Codex Serenissimus to homes across Venice.
Following historical patterns, religious texts would be distributed primarily to:
- Noble and wealthy merchant homes (higher chance)
- Clergy residences (guaranteed)
- Some middle-class homes (moderate chance)
- Rarely to working class homes (low chance)

This script creates book resources in homes with special metadata identifying them as the Codex.
"""

import os
import sys
import logging
import argparse
import json
import random
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pyairtable import Api, Table
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("distribute_codex")

# Load environment variables
load_dotenv()

# Constants
BOOK_RESOURCE_TYPE = "books"
CODEX_TITLE = "Codex Serenissimus"
CODEX_PATH = "public/books/Codex Serenissimus.md"

# Distribution chances by home type
DISTRIBUTION_CHANCES = {
    "nobili_palazzo": 0.8,        # 80% chance for noble palaces
    "grand_canal_palace": 0.9,    # 90% chance for grand palaces
    "merchant_s_house": 0.6,      # 60% chance for merchant houses
    "canal_house": 0.5,           # 50% chance for canal houses
    "artisan_s_house": 0.3,       # 30% chance for artisan homes
    "fisherman_s_cottage": 0.1,   # 10% chance for fisherman cottages
    "parish_church": 1.0,         # 100% chance for churches (if they have Occupant)
    "chapel": 1.0,                # 100% chance for chapels
}

def initialize_airtable():
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials.")
        sys.exit(1)
    
    try:
        tables = {
            'buildings': Table(api_key, base_id, 'BUILDINGS'),
            'resources': Table(api_key, base_id, 'RESOURCES'),
            'citizens': Table(api_key, base_id, 'CITIZENS'),
            'notifications': Table(api_key, base_id, 'NOTIFICATIONS')
        }
        return tables
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)

def get_eligible_homes(tables) -> List[Dict]:
    """Get all homes that could receive the Codex."""
    log.info("Fetching eligible homes...")
    
    try:
        # Get all buildings with occupants and active status
        # We'll filter by type in Python to avoid complex formulas
        formula = "AND(NOT({Occupant}=''), {Status}='active')"
        
        all_buildings = tables['buildings'].all(formula=formula)
        
        # Filter for eligible building types
        eligible_types = set(DISTRIBUTION_CHANCES.keys())
        buildings = [b for b in all_buildings if b['fields'].get('Type') in eligible_types]
        
        log.info(f"Found {len(buildings)} eligible homes/religious buildings")
        return buildings
    except Exception as e:
        log.error(f"Error fetching buildings: {e}")
        return []

def check_existing_codex(tables, building_id: str, owner: str) -> bool:
    """Check if a building already has a Codex."""
    try:
        formula = (f"AND({{Asset}}='{building_id}', {{AssetType}}='building', "
                   f"{{Type}}='{BOOK_RESOURCE_TYPE}', {{Owner}}='{owner}', "
                   f"FIND('{CODEX_TITLE}', {{Notes}})>0)")
        
        existing = tables['resources'].all(formula=formula, max_records=1)
        return len(existing) > 0
    except Exception as e:
        log.error(f"Error checking existing Codex: {e}")
        return False

def create_codex_resource(tables, building: Dict) -> bool:
    """Create a Codex Serenissimus resource in a building."""
    building_id = building['fields'].get('BuildingId')
    building_name = building['fields'].get('Name', building_id)
    building_type = building['fields'].get('Type')
    occupant = building['fields'].get('Occupant')
    
    if not building_id or not occupant:
        return False
    
    # Check if already has Codex
    if check_existing_codex(tables, building_id, occupant):
        log.info(f"  Building {building_name} already has a Codex")
        return False
    
    # Check distribution chance
    chance = DISTRIBUTION_CHANCES.get(building_type, 0.1)
    if random.random() > chance:
        log.info(f"  Building {building_name} ({building_type}) not selected (chance: {chance:.0%})")
        return False
    
    try:
        # Create the book resource
        resource_data = {
            "ResourceId": f"resource-{uuid.uuid4().hex[:12]}",
            "Type": BOOK_RESOURCE_TYPE,
            "Name": "Books",
            "Asset": building_id,
            "AssetType": "building",
            "Owner": occupant,
            "Count": 1.0,
            "CreatedAt": datetime.now().isoformat(),
            "Notes": json.dumps({
                "title": CODEX_TITLE,
                "content_path": CODEX_PATH,
                "description": "The sacred texts of Venice, containing creation myths, theological teachings, and prayers for citizens",
                "distributed_by": "Church Authority",
                "distribution_date": datetime.now().isoformat()
            })
        }
        
        # Get the building position if available
        position = building['fields'].get('Position')
        if position:
            resource_data['Position'] = position
        
        created = tables['resources'].create(resource_data)
        log.info(f"  ✓ Created Codex in {building_name} ({building_type}) for {occupant}")
        
        # Create notification for the occupant
        notification_data = {
            "Type": "codex_distribution",
            "Content": f"📖 A copy of the Codex Serenissimus has been placed in your home at {building_name}. This sacred text contains the wisdom and teachings of Venice.",
            "Details": json.dumps({
                "event_type": "codex_received",
                "building_id": building_id,
                "building_name": building_name,
                "resource_id": created['id']
            }),
            "CreatedAt": datetime.now().isoformat(),
            "Citizen": occupant
        }
        
        tables['notifications'].create(notification_data)
        return True
        
    except Exception as e:
        log.error(f"  ✗ Error creating Codex in {building_name}: {e}")
        return False

def distribute_codex(tables, limit: Optional[int] = None) -> Dict:
    """Main distribution process."""
    log.info("Starting Codex Serenissimus distribution...")
    
    # Get eligible homes
    homes = get_eligible_homes(tables)
    if not homes:
        log.warning("No eligible homes found")
        return {"total": 0, "by_type": {}}
    
    # Shuffle for random distribution order
    random.shuffle(homes)
    
    # Apply limit if specified
    if limit:
        homes = homes[:limit]
        log.info(f"Limited to {limit} homes")
    
    # Track statistics
    stats = {
        "total": 0,
        "by_type": {}
    }
    
    # Distribute to each home
    for home in homes:
        building_type = home['fields'].get('Type', 'unknown')
        
        if building_type not in stats["by_type"]:
            stats["by_type"][building_type] = {"attempted": 0, "distributed": 0}
        
        stats["by_type"][building_type]["attempted"] += 1
        
        if create_codex_resource(tables, home):
            stats["total"] += 1
            stats["by_type"][building_type]["distributed"] += 1
    
    return stats

def create_summary_notification(tables, stats: Dict):
    """Create an admin notification with distribution summary."""
    try:
        # Format statistics for display
        type_stats = []
        for building_type, counts in stats["by_type"].items():
            distributed = counts["distributed"]
            attempted = counts["attempted"]
            percentage = (distributed / attempted * 100) if attempted > 0 else 0
            type_stats.append(f"{building_type}: {distributed}/{attempted} ({percentage:.0f}%)")
        
        content = (f"📖 **Codex Serenissimus Distribution Complete**\n\n"
                   f"Total copies distributed: **{stats['total']}**\n\n"
                   f"Distribution by home type:\n" + "\n".join(type_stats))
        
        notification_data = {
            "Type": "codex_distribution_summary",
            "Content": content,
            "Details": json.dumps(stats),
            "CreatedAt": datetime.now().isoformat(),
            "Citizen": "ConsiglioDeiDieci"
        }
        
        tables['notifications'].create(notification_data)
        log.info("Created admin summary notification")
    except Exception as e:
        log.error(f"Error creating summary notification: {e}")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Distribute Codex Serenissimus to Venetian homes")
    parser.add_argument("--limit", type=int, help="Limit number of homes to distribute to")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be distributed without creating resources")
    
    args = parser.parse_args()
    
    # Initialize Airtable
    tables = initialize_airtable()
    
    if args.dry_run:
        log.info("DRY RUN MODE - No resources will be created")
        homes = get_eligible_homes(tables)
        
        # Calculate expected distribution
        expected = {"total": 0, "by_type": {}}
        for home in homes:
            building_type = home['fields'].get('Type', 'unknown')
            if building_type not in expected["by_type"]:
                expected["by_type"][building_type] = {"count": 0, "expected": 0}
            
            expected["by_type"][building_type]["count"] += 1
            chance = DISTRIBUTION_CHANCES.get(building_type, 0.1)
            expected["by_type"][building_type]["expected"] += chance
        
        log.info("\nExpected distribution:")
        for building_type, data in expected["by_type"].items():
            count = data["count"]
            expected_dist = data["expected"]
            log.info(f"  {building_type}: ~{expected_dist:.0f} of {count} homes")
        
        total_expected = sum(data["expected"] for data in expected["by_type"].values())
        log.info(f"\nTotal expected: ~{total_expected:.0f} copies")
    else:
        # Perform actual distribution
        stats = distribute_codex(tables, limit=args.limit)
        
        # Log summary
        log.info("\n=== Distribution Summary ===")
        log.info(f"Total copies distributed: {stats['total']}")
        for building_type, counts in stats["by_type"].items():
            log.info(f"  {building_type}: {counts['distributed']}/{counts['attempted']}")
        
        # Create admin notification
        if stats['total'] > 0:
            create_summary_notification(tables, stats)

if __name__ == "__main__":
    main()
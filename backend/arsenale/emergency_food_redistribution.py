#!/usr/bin/env python3
"""
Emergency script to redistribute food from water locations to accessible markets.
This will create import activities to move bread from mariners to market buildings.
"""

import os
import sys
import asyncio
import aiohttp
from datetime import datetime, timezone
import json
from typing import Dict, List, Any

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

API_BASE_URL = "https://serenissima.ai"

async def fetch_json(session: aiohttp.ClientSession, url: str) -> Any:
    """Fetch JSON from URL."""
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        else:
            print(f"Error fetching {url}: {response.status}")
            return None

async def create_food_redistribution():
    """Create activities to redistribute food from water to markets."""
    async with aiohttp.ClientSession() as session:
        print("=== EMERGENCY FOOD REDISTRIBUTION ===\n")
        
        # 1. Find bread on water
        print("1. Finding bread on water locations...")
        bread_url = f"{API_BASE_URL}/api/resources?Type=bread&AssetType=building&limit=100"
        bread_data = await fetch_json(session, bread_url)
        
        if not bread_data:
            print("Failed to fetch bread data")
            return
        
        # Filter for water locations
        water_bread = []
        for bread in bread_data:
            if bread.get('asset', '').startswith('water_'):
                water_bread.append(bread)
        
        print(f"Found {len(water_bread)} bread resources on water")
        total_bread = sum(b.get('count', 0) for b in water_bread)
        print(f"Total bread units on water: {total_bread}")
        
        # 2. Find suitable market buildings
        print("\n2. Finding market buildings...")
        buildings_url = f"{API_BASE_URL}/api/buildings?limit=200"
        buildings_data = await fetch_json(session, buildings_url)
        
        if not buildings_data or not buildings_data.get('success'):
            print("Failed to fetch buildings")
            return
        
        buildings = buildings_data.get('buildings', [])
        
        # Find inns and markets
        market_buildings = []
        for building in buildings:
            if building.get('type') in ['inn', 'market', 'warehouse']:
                # Check if it's in a central location
                coords = building.get('coordinates', {})
                if coords.get('x') and coords.get('y'):
                    market_buildings.append(building)
        
        print(f"Found {len(market_buildings)} suitable market buildings")
        
        if not market_buildings:
            print("No suitable market buildings found!")
            return
        
        # 3. Create redistribution plan
        print("\n3. Creating redistribution plan...")
        
        # Group bread by owner
        bread_by_owner = {}
        for bread in water_bread:
            owner = bread.get('owner')
            if owner not in bread_by_owner:
                bread_by_owner[owner] = []
            bread_by_owner[owner].append(bread)
        
        print(f"Bread is owned by {len(bread_by_owner)} different mariners")
        
        # Create transfer activities
        transfers_created = 0
        
        for owner, breads in bread_by_owner.items():
            # Pick a market building
            target_market = market_buildings[transfers_created % len(market_buildings)]
            
            # Calculate total bread from this owner
            owner_total = sum(b.get('count', 0) for b in breads)
            
            print(f"\nTransferring {owner_total} bread from {owner} to {target_market['name']}")
            
            # Create public sell contract at the market
            contract_data = {
                "type": "public_sell",
                "resource": "bread",
                "price": 10.0,  # Affordable price
                "amount": owner_total,
                "building": target_market['buildingId'],
                "seller": owner
            }
            
            create_url = f"{API_BASE_URL}/api/contracts/public-sell"
            
            async with session.post(create_url, json=contract_data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        print(f"  ✓ Created public sell contract for {owner_total} bread at {target_market['name']}")
                        transfers_created += 1
                    else:
                        print(f"  ✗ Failed to create contract: {result.get('error')}")
                else:
                    print(f"  ✗ Failed to create contract: HTTP {response.status}")
            
            # Only do first 5 transfers as a test
            if transfers_created >= 5:
                break
        
        print(f"\n=== REDISTRIBUTION COMPLETE ===")
        print(f"Created {transfers_created} transfer contracts")
        print("\nNext steps:")
        print("1. Mariners will deliver bread to markets")
        print("2. Citizens can buy bread at affordable prices")
        print("3. Monitor eating activity recovery")

if __name__ == "__main__":
    asyncio.run(create_food_redistribution())
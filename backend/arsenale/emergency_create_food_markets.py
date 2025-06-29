#!/usr/bin/env python3
"""
Emergency script to create affordable food markets in La Serenissima.
Creates public_sell contracts for bread at low prices in accessible locations.
"""

import os
import sys
import asyncio
import aiohttp
from datetime import datetime
import json

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

API_BASE_URL = "https://serenissima.ai"
AIRTABLE_PAT = os.getenv('AIRTABLE_PAT')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')

async def create_emergency_food_markets():
    """Create emergency food markets with affordable bread."""
    print("=== EMERGENCY FOOD MARKET CREATION ===\n")
    
    headers = {
        'Authorization': f'Bearer {AIRTABLE_PAT}',
        'Content-Type': 'application/json'
    }
    
    async with aiohttp.ClientSession() as session:
        # 1. Find Consiglio dei Dieci buildings with bread
        print("1. Finding Consiglio bread supplies...")
        
        # Get Consiglio buildings
        buildings_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/BUILDINGS"
        params = {
            'filterByFormula': "OR({Owner}='ConsiglioDeiDieci', {RunBy}='ConsiglioDeiDieci')",
            'maxRecords': 50
        }
        
        async with session.get(buildings_url, headers=headers, params=params) as resp:
            if resp.status != 200:
                print(f"Failed to fetch buildings: {resp.status}")
                return
            buildings_data = await resp.json()
        
        consiglio_buildings = buildings_data.get('records', [])
        print(f"Found {len(consiglio_buildings)} Consiglio buildings")
        
        # 2. Find bread in these buildings
        bread_found = []
        for building in consiglio_buildings:
            building_id = building['fields'].get('BuildingId')
            if not building_id:
                continue
            
            # Check for bread
            resources_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/RESOURCES"
            params = {
                'filterByFormula': f"AND({{Asset}}='{building_id}', {{Type}}='bread', {{AssetType}}='building')",
                'maxRecords': 10
            }
            
            async with session.get(resources_url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    resources_data = await resp.json()
                    for resource in resources_data.get('records', []):
                        count = resource['fields'].get('Count', 0)
                        if count > 0:
                            bread_found.append({
                                'building': building,
                                'resource': resource,
                                'count': count
                            })
        
        print(f"\nFound bread in {len(bread_found)} Consiglio buildings")
        total_bread = sum(b['count'] for b in bread_found)
        print(f"Total Consiglio bread available: {total_bread} units")
        
        if not bread_found:
            print("No bread found in Consiglio buildings! Checking water locations...")
            
            # Alternative: Get bread from water locations
            params = {
                'filterByFormula': "AND({Type}='bread', {AssetType}='building', FIND('water_', {Asset}))",
                'maxRecords': 20
            }
            
            async with session.get(resources_url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    water_data = await resp.json()
                    water_bread = water_data.get('records', [])
                    print(f"Found {len(water_bread)} bread resources on water")
                    
                    # Use first 5 water bread sources
                    for resource in water_bread[:5]:
                        bread_found.append({
                            'building': None,  # Water location
                            'resource': resource,
                            'count': resource['fields'].get('Count', 0)
                        })
        
        if not bread_found:
            print("No bread found anywhere! Crisis!")
            return
        
        # 3. Find suitable market locations (inns, markets in city center)
        print("\n2. Finding suitable market locations...")
        
        # Get inns and markets
        params = {
            'filterByFormula': "OR({Type}='inn', {Type}='market')",
            'maxRecords': 20
        }
        
        async with session.get(buildings_url, headers=headers, params=params) as resp:
            if resp.status != 200:
                print(f"Failed to fetch market buildings: {resp.status}")
                return
            market_data = await resp.json()
        
        markets = market_data.get('records', [])
        suitable_markets = []
        
        for market in markets:
            # Check if it's in a central location (not on water)
            building_id = market['fields'].get('BuildingId', '')
            if not building_id.startswith('water_'):
                suitable_markets.append(market)
        
        print(f"Found {len(suitable_markets)} suitable market locations")
        
        if not suitable_markets:
            print("No suitable markets found!")
            return
        
        # 4. Create public_sell contracts
        print("\n3. Creating affordable bread contracts...")
        
        contracts_created = 0
        contracts_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/CONTRACTS"
        
        # Distribute bread across markets
        for i, bread_info in enumerate(bread_found[:10]):  # Limit to 10 sources
            market = suitable_markets[i % len(suitable_markets)]
            market_id = market['fields'].get('BuildingId')
            market_name = market['fields'].get('Name', market_id)
            
            resource = bread_info['resource']
            owner = resource['fields'].get('Owner')
            amount = min(resource['fields'].get('Count', 0), 50)  # Max 50 per contract
            
            if amount <= 0:
                continue
            
            # Create affordable public_sell contract
            contract_data = {
                "fields": {
                    "ContractId": f"emergency_bread_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                    "Type": "public_sell",
                    "ResourceType": "bread",
                    "TargetAmount": amount,
                    "PricePerUnit": 5.0,  # Very affordable - 5 ducats per bread
                    "Seller": owner,
                    "SellerType": "building",
                    "SellerId": resource['fields'].get('Asset'),
                    "Status": "active",
                    "Notes": f"Emergency food distribution at {market_name}",
                    "DeliveryBuildingId": market_id,
                    "CreatedAt": datetime.now().isoformat() + "Z"
                }
            }
            
            async with session.post(contracts_url, headers=headers, json=contract_data) as resp:
                if resp.status == 200:
                    print(f"✓ Created contract: {amount} bread at {market_name} for 5 ducats each (seller: {owner})")
                    contracts_created += 1
                else:
                    error_text = await resp.text()
                    print(f"✗ Failed to create contract: {resp.status} - {error_text}")
        
        print(f"\n=== EMERGENCY RESPONSE COMPLETE ===")
        print(f"Created {contracts_created} affordable bread contracts")
        print("\nCitizens can now:")
        print("1. Go to inns/markets to buy bread for 5 ducats")
        print("2. Eat the bread during leisure time")
        print("3. Survive the hunger crisis!")
        
        # 5. Optional: Create direct food aid for the poorest
        print("\n4. Creating direct food aid for the poorest citizens...")
        
        # Get very poor citizens
        citizens_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/CITIZENS"
        params = {
            'filterByFormula': "AND({Ducats}<10, NOT({Username}='ConsiglioDeiDieci'))",
            'maxRecords': 20,
            'sort': [{'field': 'Ducats', 'direction': 'asc'}]
        }
        
        async with session.get(citizens_url, headers=headers, params=params) as resp:
            if resp.status == 200:
                poor_data = await resp.json()
                poor_citizens = poor_data.get('records', [])
                print(f"Found {len(poor_citizens)} citizens with less than 10 ducats")
                
                # Give each poor citizen 1 bread directly
                resources_created = 0
                for citizen in poor_citizens[:10]:  # Help first 10
                    username = citizen['fields'].get('Username')
                    citizen_id = citizen['fields'].get('CitizenId', username)
                    
                    resource_data = {
                        "fields": {
                            "Type": "bread",
                            "Count": 1,
                            "Owner": username,
                            "Asset": citizen_id,
                            "AssetType": "citizen",
                            "Notes": "Emergency food aid from Consiglio dei Dieci"
                        }
                    }
                    
                    async with session.post(resources_url, headers=headers, json=resource_data) as resp:
                        if resp.status == 200:
                            print(f"✓ Gave 1 bread to {username} (emergency aid)")
                            resources_created += 1
                
                print(f"\nProvided direct food aid to {resources_created} citizens")

if __name__ == "__main__":
    asyncio.run(create_emergency_food_markets())
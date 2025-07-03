"""
Quick test to check API structure
"""

import asyncio
import aiohttp
import json


async def test_endpoints():
    """Test various API endpoints to understand structure"""
    api_base = "https://serenissima.ai/api"
    
    async with aiohttp.ClientSession() as session:
        # Test citizens endpoint
        print("Testing /api/citizens...")
        try:
            async with session.get(f"{api_base}/citizens") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Citizens: {len(data)} records")
                    if data:
                        print(f"Sample citizen keys: {list(data[0].keys())[:10]}")
                else:
                    print(f"Citizens endpoint returned: {resp.status}")
        except Exception as e:
            print(f"Citizens error: {e}")
        
        # Test transactions/history
        print("\nTesting /api/transactions/history...")
        try:
            async with session.get(f"{api_base}/transactions/history?limit=10") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Transactions: {len(data)} records")
                    if data:
                        print(f"Sample transaction keys: {list(data[0].keys())}")
                else:
                    print(f"Transactions endpoint returned: {resp.status}")
        except Exception as e:
            print(f"Transactions error: {e}")
        
        # Test activities
        print("\nTesting /api/activities...")
        try:
            async with session.get(f"{api_base}/activities?limit=10") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Activities: {len(data)} records")
                    if data:
                        print(f"Sample activity keys: {list(data[0].keys())[:10]}")
                else:
                    print(f"Activities endpoint returned: {resp.status}")
        except Exception as e:
            print(f"Activities error: {e}")
        
        # Test contracts
        print("\nTesting /api/contracts...")
        try:
            async with session.get(f"{api_base}/contracts?limit=10") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Contracts: {len(data)} records")
                    if data:
                        print(f"Sample contract keys: {list(data[0].keys())[:10]}")
                else:
                    print(f"Contracts endpoint returned: {resp.status}")
        except Exception as e:
            print(f"Contracts error: {e}")


if __name__ == "__main__":
    asyncio.run(test_endpoints())
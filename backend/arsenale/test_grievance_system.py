#!/usr/bin/env python3
"""
Test script to verify grievance system functionality
"""
import os
import sys
import requests

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_grievance_tables():
    """Test if grievance tables exist in Airtable"""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("❌ Missing Airtable credentials")
        return False
    
    try:
        api = Api(api_key)
        
        # Test GRIEVANCES table
        print("Testing GRIEVANCES table...")
        try:
            grievances_table = api.table(base_id, 'GRIEVANCES')
            records = grievances_table.all(max_records=1)
            print(f"✅ GRIEVANCES table exists (found {len(records)} records)")
        except Exception as e:
            print(f"❌ GRIEVANCES table error: {e}")
            return False
        
        # Test GRIEVANCE_SUPPORT table
        print("\nTesting GRIEVANCE_SUPPORT table...")
        try:
            support_table = api.table(base_id, 'GRIEVANCE_SUPPORT')
            records = support_table.all(max_records=1)
            print(f"✅ GRIEVANCE_SUPPORT table exists (found {len(records)} records)")
        except Exception as e:
            print(f"❌ GRIEVANCE_SUPPORT table error: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints"""
    base_url = "https://serenissima.ai/api"
    
    print("\n\nTesting API endpoints...")
    
    # Test grievances endpoint
    print("\nTesting GET /api/governance/grievances...")
    try:
        response = requests.get(f"{base_url}/governance/grievances", timeout=10)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint works! Found {data.get('total', 0)} grievances")
        else:
            print(f"❌ Endpoint returned {response.status_code}")
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=== Testing La Serenissima Grievance System ===\n")
    
    # Test Airtable tables
    tables_ok = test_grievance_tables()
    
    # Test API endpoints
    test_api_endpoints()
    
    print("\n=== Test Complete ===")
    if tables_ok:
        print("✅ Airtable tables are properly configured")
    else:
        print("❌ Airtable table issues detected")
"""
Test script to verify the hunger crisis fix is working.
Checks if citizens who haven't eaten in >24 hours get emergency eating priority.
"""

import os
import sys
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arsenale.fix_hunger_crisis import is_severely_hungry

def test_is_severely_hungry():
    """Test the is_severely_hungry function with various scenarios."""
    
    # Current time
    now_utc = datetime.now(pytz.UTC)
    
    # Test cases
    test_cases = [
        {
            "name": "No AteAt field",
            "citizen_record": {"fields": {}},
            "expected": True,
            "description": "Citizen with no eating history should be severely hungry"
        },
        {
            "name": "Ate 6 hours ago",
            "citizen_record": {"fields": {"AteAt": (now_utc - timedelta(hours=6)).isoformat()}},
            "expected": False,
            "description": "Citizen who ate 6 hours ago should NOT be severely hungry"
        },
        {
            "name": "Ate 13 hours ago",
            "citizen_record": {"fields": {"AteAt": (now_utc - timedelta(hours=13)).isoformat()}},
            "expected": False,
            "description": "Citizen who ate 13 hours ago should NOT be severely hungry (but is hungry)"
        },
        {
            "name": "Ate 25 hours ago",
            "citizen_record": {"fields": {"AteAt": (now_utc - timedelta(hours=25)).isoformat()}},
            "expected": True,
            "description": "Citizen who ate 25 hours ago SHOULD be severely hungry"
        },
        {
            "name": "Ate 48 hours ago",
            "citizen_record": {"fields": {"AteAt": (now_utc - timedelta(hours=48)).isoformat()}},
            "expected": True,
            "description": "Citizen who ate 48 hours ago SHOULD be severely hungry"
        },
        {
            "name": "Invalid AteAt date",
            "citizen_record": {"fields": {"AteAt": "invalid-date"}},
            "expected": True,
            "description": "Citizen with invalid AteAt should be treated as severely hungry"
        }
    ]
    
    print("Testing is_severely_hungry function:")
    print("=" * 60)
    
    all_passed = True
    for test in test_cases:
        result = is_severely_hungry(test["citizen_record"], now_utc, hours_threshold=24.0)
        passed = result == test["expected"]
        status = "✓ PASS" if passed else "✗ FAIL"
        
        print(f"\n{status} - {test['name']}")
        print(f"   Description: {test['description']}")
        print(f"   Expected: {test['expected']}, Got: {result}")
        
        if not passed:
            all_passed = False
            ate_at = test["citizen_record"]["fields"].get("AteAt", "None")
            print(f"   AteAt value: {ate_at}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    
    return all_passed


def check_current_hunger_situation():
    """Check current hunger situation via the API."""
    import requests
    
    print("\nChecking current hunger situation...")
    print("=" * 60)
    
    try:
        # This would normally call the production API
        # For testing, we'll just print what we would check
        print("To check real hunger data, run:")
        print('curl -s "https://serenissima.ai/api/citizens" | python3 -c "')
        print('import json, sys')
        print('from datetime import datetime, timezone')
        print('data = json.load(sys.stdin)')
        print('citizens = data.get(\\"citizens\\", [])')
        print('now = datetime.now(timezone.utc)')
        print('hungry_24h = [c for c in citizens if c.get(\\"AteAt\\") and (now - datetime.fromisoformat(c[\\"AteAt\\"].replace(\\"Z\\", \\"+00:00\\"))).total_seconds() > 86400]')
        print('print(f\\"Citizens who haven\\'t eaten in >24h: {len(hungry_24h)}\\")')
        print('for c in hungry_24h[:5]: print(f\\"  {c.get(\\'Name\\')}: Last ate {c.get(\\'AteAt\\')}\\")"')
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("Hunger Crisis Fix - Test Suite")
    print("=" * 60)
    
    # Run tests
    test_passed = test_is_severely_hungry()
    
    # Check current situation
    check_current_hunger_situation()
    
    print("\n" + "=" * 60)
    print("IMPLEMENTATION NOTES:")
    print("1. The fix has been applied to needs.py")
    print("2. Citizens who haven't eaten in >24 hours will bypass leisure time restrictions")
    print("3. Emergency eating activities will be logged with [EMERGENCY] tag")
    print("4. Monitor logs for emergency eating patterns")
    print("\nTo verify the fix is working:")
    print("- Check engine logs for [EMERGENCY] eating activities")
    print("- Monitor AteAt timestamps via the API")
    print("- Ensure emergency eaters get food within the next activity cycle")
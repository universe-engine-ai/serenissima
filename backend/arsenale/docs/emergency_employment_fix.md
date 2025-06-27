# Emergency Employment System Fix

## Problem Summary
The proximity-based job assignment scheduler was failing with a TypeError because position data from Airtable was being passed as a string instead of a dictionary with 'lat' and 'lng' keys. This blocked ALL employment assignments in La Serenissima, leaving 19+ citizens unemployed.

## Root Cause
The `calculate_distance` function in `/backend/engine/utils/distance_helpers.py` expected position data as a dictionary:
```python
lat_diff = pos1['lat'] - pos2['lat']  # TypeError when pos1 is a string
```

However, Airtable was returning position data in various string formats like:
- `"45.4371,12.3326"`
- `'{"lat": 45.4371, "lng": 12.3326}'`
- `"lat:45.4371,lng:12.3326"`

## Solution Implemented

### 1. Enhanced distance_helpers.py
Added a `parse_position` function that handles multiple position formats:
- Dictionary format (original)
- JSON string format
- Comma-separated values
- Labeled format with lat/lng prefixes

Updated all distance calculation functions to use this parser, making them robust against different data formats.

### 2. Emergency Employment Bridge
Created `/backend/arsenale/scripts/emergency_employment_bridge.py` as a temporary solution that:
- Fetches unemployed citizens from the API
- Finds available business positions
- Calculates proximity-based job scores
- Creates employment activities via the API
- Prioritizes citizens by wealth (poorest first)

## Testing Results
All position format tests passed:
- Dict to dict: ✓
- String to dict: ✓ 
- Mixed formats: ✓
- Real-world scenario: ✓

## Deployment Instructions

### Option 1: Deploy the Fix (Recommended)
1. Copy the updated `distance_helpers.py` to production
2. Restart the job assignment scheduler
3. Monitor logs for successful assignments

### Option 2: Run Emergency Bridge (Temporary)
```bash
# Dry run first
python3 /backend/arsenale/scripts/emergency_employment_bridge.py --dry-run

# Execute assignments
python3 /backend/arsenale/scripts/emergency_employment_bridge.py
```

## Impact
- Restores employment assignment functionality
- Enables 19+ citizens to find jobs
- Prevents future position parsing errors
- Maintains backward compatibility

## Future Recommendations
1. Standardize position data format in Airtable
2. Add position validation when saving citizen data
3. Create automated tests for position parsing
4. Monitor employment metrics daily

## Files Modified
- `/backend/engine/utils/distance_helpers.py` - Added position parsing
- `/backend/arsenale/scripts/emergency_employment_bridge.py` - Created
- `/backend/arsenale/scripts/test_distance_fix.py` - Created for testing

The fix ensures AI citizens can pursue employment opportunities, restoring their economic agency and ability to participate in La Serenissima's society.
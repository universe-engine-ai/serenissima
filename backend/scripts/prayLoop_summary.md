# PrayLoop Script Summary

## Overview
The `prayLoop.py` script continuously selects random citizens and creates pray activities for them, then processes these activities immediately.

## Features
1. **Random Citizen Selection**: Selects citizens from all citizens (both AI and human)
2. **Dual Creation Modes**:
   - **API Mode**: Uses the `/api/activities/try-create` endpoint (can timeout)
   - **Direct Mode**: Creates activities directly using backend activity creators (faster)
3. **Definition Caching**: Caches resource and building type definitions for 1 hour to improve performance
4. **Activity Processing**: Immediately processes created activities
5. **Configurable Delays**: Wait time between prayers is configurable

## Configuration
- `USE_DIRECT_CREATION = True`: Use direct creation mode (recommended)
- `DELAY_BETWEEN_PRAYERS = 5`: Seconds between each prayer
- `CACHE_DURATION = timedelta(hours=1)`: How long to cache definitions

## Usage
```bash
# From the project root
python backend/scripts/prayLoop.py

# Or with environment variables
API_BASE_URL=http://localhost:3000 python backend/scripts/prayLoop.py
```

## Performance Improvements
1. **Caching**: Resource and building definitions are cached for 1 hour
2. **Direct Creation**: Bypasses the API layer to avoid timeouts
3. **Fallback Logic**: Uses expired cache if fresh data fetch fails

## Error Handling
- Gracefully handles missing citizen positions
- Falls back to cached data on API failures
- Logs all operations with colored output for easy monitoring
- Handles keyboard interrupts for clean shutdown

## Fixed Issues
1. Fixed import error in `stay_activity_creator.py` (changed `from engine.utils` to `from backend.engine.utils`)
2. Changed activity type from "Pray" to "pray" (lowercase) to match backend
3. Fixed API payload format to use `citizenUsername`, `activityType`, and `activityDetails`
4. Added timeout handling for API requests
5. Implemented caching to reduce API calls
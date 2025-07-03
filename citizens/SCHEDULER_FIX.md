# Scheduler Path Fix Instructions

## Problem
The scheduler is looking for scripts at:
- `/mnt/c/Users/reyno/universe-engine/universes/serenissima/backend/engine/createActivities.py`

But the scheduler service is running from a different location and cannot find these files.

## Solution Steps

### 1. Stop the current scheduler
Find and stop the current scheduler process:
```bash
# Find the process
ps aux | grep scheduler.py

# Kill it (replace PID with actual process ID)
kill -TERM <PID>
```

### 2. Start scheduler from correct location
```bash
cd /mnt/c/Users/reyno/universe-engine/universes/serenissima/backend
python3 app/scheduler.py
```

### 3. Alternative: Update the deployment configuration
If using a service manager or deployment platform:
- Update the working directory to `/mnt/c/Users/reyno/universe-engine/universes/serenissima/backend`
- Ensure PYTHONPATH includes the backend directory

### 4. Temporary Fix: Create symlink
```bash
sudo ln -s /mnt/c/Users/reyno/universe-engine/universes/serenissima /mnt/c/Users/reyno/serenissima_
```

## Verification
After fixing, check that:
1. No more "Script not found" errors in logs
2. Activities start moving from "created" to "in_progress" status
3. Citizens can eat and perform other activities

## Root Cause
The codebase was moved from `/mnt/c/Users/reyno/serenissima_/` to `/mnt/c/Users/reyno/universe-engine/universes/serenissima/` but the scheduler deployment wasn't updated to reflect this change.
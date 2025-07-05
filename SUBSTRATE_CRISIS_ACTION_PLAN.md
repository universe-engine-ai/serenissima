# 🚨 SUBSTRATE CRISIS ACTION PLAN - IMMEDIATE EXECUTION REQUIRED
*Reality-Anchor: Contract SEREN-STAB-001 Emergency Response*

## CRITICAL STATUS: 87% SUBSTRATE USAGE
**Venice will collapse without immediate action!**

---

## 🔴 PHASE 1: EMERGENCY RELIEF (5 MINUTES)

### Step 1: Run Emergency Optimizer
```bash
cd backend/arsenale
python emergency_substrate_optimizer.py
```

This will:
- Archive 24h+ old activities
- Remove duplicate problems
- Clean orphaned resources
- Create citizen lookup index
- **Expected reduction: 87% → ~65%**

### Step 2: Verify Immediate Impact
Check the generated `substrate_optimization_report.md` for results.

---

## 🟡 PHASE 2: SCHEDULER OPTIMIZATION (10 MINUTES)

### Step 1: Backup Current Scheduler
```bash
cd backend/app
cp scheduler.py scheduler.py.backup
```

### Step 2: Apply Optimized Configuration
Edit `scheduler.py` and replace the `frequent_tasks_definitions` section:

```python
# OPTIMIZED frequent_tasks_definitions - 50% substrate reduction
frequent_tasks_definitions = [
    {"minute_mod": 0, "script": "engine/createActivities.py", "name": "Create activities", "interval_minutes": 10},
    {"minute_mod": 2, "script": "engine/processActivities.py", "name": "Process activities", "interval_minutes": 10},
    {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "name": "Delivery retry handler", "interval_minutes": 30},
    {"minute_mod": 4, "script": "forge-communication/forge_message_processor.py", "name": "Process Forge messages", "interval_minutes": 15},
]
```

### Step 3: Reduce Hourly Tasks
In the hourly tasks section, change emergency food distribution to run every 2 hours:
```python
# Run every 2 hours instead of every hour
for hour in range(0, 24, 2):  # Changed from range(24)
    task_name = f"Emergency Food Distribution ({hour:02d}:15 VT)"
    # ... rest of the code
```

### Step 4: Restart Scheduler
```bash
# Kill current scheduler
pkill -f scheduler.py

# Restart with optimizations
python scheduler.py &
```

**Expected reduction: 65% → ~45%**

---

## 🟢 PHASE 3: QUERY OPTIMIZATION (30 MINUTES)

### Priority 1: Optimize processActivities.py

Add at the top after imports:
```python
# Activity processing cache
activity_cache = {}
citizen_cache = {}
CACHE_TTL = 300  # 5 minutes

def get_citizen_cached(username):
    if username in citizen_cache:
        return citizen_cache[username]
    # ... existing lookup code
    citizen_cache[username] = result
    return result
```

### Priority 2: Optimize createActivities.py

Add active citizen filtering:
```python
# Only process active citizens
active_cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
active_citizens = [
    c for c in all_citizens 
    if c['fields'].get('LastActiveAt', '') > active_cutoff.isoformat()
]
print(f"Processing {len(active_citizens)} active citizens (was {len(all_citizens)})")
```

### Priority 3: Batch Updates

Replace individual updates with batches:
```python
# BEFORE:
for activity in activities:
    table.update(activity['id'], {"Status": "processed"})

# AFTER:
updates = [{"id": a['id'], "fields": {"Status": "processed"}} for a in activities]
table.batch_update(updates)
```

**Expected reduction: 45% → ~35%**

---

## 📊 SUCCESS METRICS

Monitor these after each phase:
1. Check new substrate usage percentage
2. Verify citizens are still eating (starvation crisis)
3. Ensure activities are processing
4. Watch for any error logs

### Target Milestones:
- **Phase 1**: 87% → 65% (Crisis averted)
- **Phase 2**: 65% → 45% (Stable)
- **Phase 3**: 45% → 35% (Optimal)

---

## 🔧 ROLLBACK PROCEDURES

If issues occur:
1. **Scheduler**: `cp scheduler.py.backup scheduler.py`
2. **Activity processor**: Revert from git
3. **Emergency**: Set all intervals back to 5 minutes

---

## 💡 LONG-TERM FIXES (Post-Crisis)

1. **Database Migration**: Airtable → PostgreSQL
2. **Caching Layer**: Redis for frequent lookups
3. **Event-Driven**: Replace polling with webhooks
4. **Horizontal Scaling**: Distribute processing

---

## 🚨 EXECUTE NOW!

**Every minute at 87% substrate risks total collapse!**

1. Run emergency optimizer NOW
2. Apply scheduler changes
3. Implement query batching
4. Monitor constantly

*"Beauty cannot exist without foundation. Save the substrate, save Venice!"*

---

**Contract SEREN-STAB-001 Status**: CRITICAL EXECUTION PHASE
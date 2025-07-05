# Galley Unloading Tools Documentation
## Contract: SEREN-STAB-001

### Overview

These tools were created to address the critical Venice starvation crisis where merchant galleys arrive with cargo (especially grain) but don't automatically unload, leading to citizens starving while food sits in ships.

### The Problem

1. **No Automatic Unloading**: Merchant galleys require manual citizen activities to unload
2. **Starvation Crisis**: 87% of citizens are hungry while grain sits in galleys  
3. **Activity Bottleneck**: Citizens are too busy/weak to create unloading activities
4. **System Design Flaw**: The import system assumes citizens will fetch resources

### Available Tools

#### 1. `galley_status_report.py`
Quick diagnostic tool to assess the current galley situation.

```bash
python galley_status_report.py
```

**Features:**
- Shows total galleys and their status (arrived vs in transit)
- Lists cargo inventory by type
- Identifies galleys with grain
- Reports hunger statistics
- Provides recommendations

#### 2. `emergency_galley_unloader.py`
Direct transfer tool that bypasses the activity system for emergency situations.

```bash
# Dry run to see what would happen
python emergency_galley_unloader.py --dry-run

# Execute emergency unloading
python emergency_galley_unloader.py

# Limit to first 10 galleys
python emergency_galley_unloader.py --limit 10
```

**Features:**
- Directly transfers grain from galleys to mills/warehouses
- Prioritizes automated_mills for immediate processing
- Creates audit trail activities
- Notifies galley owners
- Preserves resource ownership

**When to Use:**
- Extreme starvation (>80% hungry)
- No citizens available to unload
- Need immediate relief

#### 3. `galley_unloading_orchestrator.py`
Creates proper citizen activities to unload galleys through the normal system.

```bash
# Dry run
python galley_unloading_orchestrator.py --dry-run

# Create unloading activities
python galley_unloading_orchestrator.py

# Prioritize grain only
python galley_unloading_orchestrator.py --grain-only

# Limit citizens assigned
python galley_unloading_orchestrator.py --limit-citizens 20
```

**Features:**
- Finds available healthy citizens
- Creates pickup_from_galley activities
- Assigns nearest citizens to galleys
- Balances workload (max 3 activities per citizen)
- Creates proper import contracts
- Maintains system integrity

**When to Use:**
- Normal operations
- When citizens are available
- To maintain proper game mechanics

### Implementation Details

#### Resource Transfer Logic
1. Resources maintain ownership through transfer
2. Grain owned by merchant remains merchant's until sold
3. Transfer respects building storage capacity
4. Creates proper audit trails

#### Activity Creation
1. Uses standard activity types (pickup_from_galley)
2. Respects citizen carrying capacity (20 units)
3. Creates import contracts for proper tracking
4. Sets high priority (8-9) for urgent tasks

#### Safety Features
- Dry run mode for testing
- Validates building positions
- Checks citizen health (>30 required)
- Prevents citizen overload
- Maintains data integrity

### Emergency Response Workflow

1. **Assess Situation**
   ```bash
   python galley_status_report.py
   ```

2. **If Critical (>80% starving)**
   ```bash
   python emergency_galley_unloader.py --dry-run
   python emergency_galley_unloader.py
   ```

3. **For Normal Operations**
   ```bash
   python galley_unloading_orchestrator.py --grain-only
   ```

4. **Monitor Progress**
   ```bash
   python galley_status_report.py
   ```

### Future Improvements

1. **Automatic Unloading**: Modify galley arrival to auto-unload to docks
2. **Dock Workers**: Create specialized dock worker role
3. **Import Queues**: Better queue management for imports
4. **Push Notifications**: Alert citizens when galleys arrive
5. **Galley Schedules**: Predictable arrival times

### Notes

- These are emergency tools for crisis management
- The underlying issue is a game design problem
- Long-term solution requires modifying the import/galley system
- Always run status report first to assess situation
- Use dry-run mode to preview changes

### Related Files
- `/backend/engine/activity_processors/pickup_from_galley_processor.py` - Handles the actual pickup
- `/backend/engine/createmarketgalley.py` - Creates market galleys
- `/backend/engine/activity_processors/manage_public_dock_processor.py` - Dock management

---

*Created by Reality-Anchor as part of emergency substrate optimization efforts*
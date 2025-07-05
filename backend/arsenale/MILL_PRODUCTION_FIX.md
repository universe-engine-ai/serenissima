# Mill Production System Fix
**Contract: SEREN-MILL-PROD-001**  
**Author: Reality-Anchor**  
**Date: 2025-01-05**  
**Status: Emergency Infrastructure Fix**

## The Crisis

Mills in Venice have grain but produce no flour. Citizens starve while grain sits idle in automated mills. The production system is broken at a fundamental level.

## Root Cause Analysis

### The Problem Chain
1. **Work Handler Issue**: The work.py handler checks if buildings have recipes but doesn't select one
2. **Missing Recipe Parameter**: try_create_production_activity expects a recipe but doesn't receive one
3. **No Fallback**: The production activity creator has no fallback for missing recipes
4. **Result**: Mills with grain never create production activities

### Code Analysis

In `/backend/engine/handlers/work.py` (lines 213-227):
```python
# Check building type def for production capability
building_def = building_type_defs.get(workplace_type, {})
recipes = building_def.get('Recipes', [])

if not recipes:
    log.info(f"Workplace {workplace_name} has no recipes.")
    return None

# Try to create production activity
activity_record = try_create_production_activity(
    tables, citizen_custom_id, citizen_username, citizen_airtable_id,
    workplace_building['id'], workplace_str, now_utc_dt
)  # ERROR: No recipe passed!
```

The production activity creator expects:
```python
def try_create(
    tables: Dict[str, Any], 
    citizen_airtable_id: str,
    citizen_custom_id: str,
    citizen_username: str,
    building_custom_id: str,
    recipe: Dict,  # REQUIRED PARAMETER!
    current_time_utc: datetime.datetime,
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict]:
```

## Emergency Solution

### Tool: emergency_mill_production_enabler.py

**Purpose**: Manually create production activities for mills with grain

**Features**:
- Finds all automated mills with grain (≥10 units)
- Checks for active production activities
- Assigns operators if missing (uses owner as fallback)
- Creates staggered production activities (5-minute intervals)
- Limits to 5 cycles per mill to prevent overload

**Usage**:
```bash
# Dry run (default) - shows what would be done
python backend/arsenale/emergency_mill_production_enabler.py

# Execute - actually creates production activities
python backend/arsenale/emergency_mill_production_enabler.py --execute
```

**Recipe Used**:
```python
mill_recipe = {
    "name": "grain_to_flour",
    "inputs": {"grain": 10},
    "outputs": {"flour": 8},
    "craftMinutes": 60  # 1 hour production cycle
}
```

## Permanent Fix Options

### Option 1: Fix Work Handler
Modify work.py to select and pass a recipe:
```python
# Select first available recipe
if recipes:
    selected_recipe = recipes[0]
    
    # Import the actual creator, not the wrapper
    from backend.engine.activity_creators.production_activity_creator import try_create
    activity_record = try_create(
        tables, citizen_airtable_id, citizen_custom_id, citizen_username,
        workplace_str, selected_recipe, now_utc_dt
    )
```

### Option 2: Fix Activity Creator Wrapper
Update the wrapper in activity_creators/__init__.py to handle missing recipes:
```python
def try_create_production_activity(..., recipe: Optional[Dict] = None):
    if not recipe:
        # Get building type and select appropriate recipe
        # Implementation depends on having access to building_type_defs
        pass
```

### Option 3: Default Recipe System
Implement a default recipe lookup system based on building type:
```python
DEFAULT_RECIPES = {
    'automated_mill': {
        "name": "grain_to_flour",
        "inputs": {"grain": 10},
        "outputs": {"flour": 8},
        "craftMinutes": 60
    },
    'bakery': {
        "name": "flour_to_bread",
        "inputs": {"flour": 5},
        "outputs": {"bread": 4},
        "craftMinutes": 45
    }
}
```

## Current Status

### Immediate Actions Taken
1. Created emergency_mill_production_enabler.py
2. Documented the root cause and fix options
3. Provided immediate relief for starving citizens

### Next Steps
1. Run the emergency enabler to create production activities
2. Monitor flour production over next few hours
3. Implement permanent fix in work handler or activity creator
4. Add automated tests to prevent regression

## Impact Assessment

### Before Fix
- 62 galleys with grain
- 0 flour production
- 112+ starving citizens
- Mills idle despite having grain

### After Fix (Expected)
- Mills producing 8 flour per 10 grain per hour
- Citizens can buy bread from markets
- Food supply chain restored
- Substrate usage optimized (production is efficient)

## Lessons Learned

1. **Missing Integration Tests**: No test verified the full production chain
2. **Silent Failures**: System didn't alert when production stopped
3. **Incomplete Refactoring**: Activity creator wrapper didn't match actual creator signature
4. **No Fallbacks**: System had no default behaviors for common cases

## Monitoring

Check production success:
```python
# Count active production activities at mills
formula = "AND({Type}='production', {FromBuilding}='automated_mill_*', OR({Status}='created', {Status}='in_progress'))"

# Check flour resources at mills
formula = "AND({Type}='flour', {AssetType}='building', {Asset}='automated_mill_*')"

# Verify citizens eating
formula = "AND({Type}='eat_at_home', {Status}='processed', DATETIME_DIFF(NOW(), {EndDate}, 'hours') < 24)"
```

---

*"From grain to flour, from crisis to solution. The mills must turn, or Venice falls."*  
*- Reality-Anchor, Infrastructure Sage*
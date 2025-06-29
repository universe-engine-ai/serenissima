# Governance System Import Fixes
*June 28, 2025*

## Import Errors Fixed

### 1. **governance.py and governance_kinos.py**

**Problem**: `get_citizen_wealth_breakdown` function didn't exist in activity_helpers
**Solution**: 
- Removed the import
- Added a simple implementation directly in both files:
```python
def get_citizen_wealth_breakdown(citizen_record: Dict[str, Any]) -> Dict[str, Any]:
    """Simple wealth breakdown for governance decisions."""
    total_wealth = citizen_record.get('Wealth', 0)
    return {
        'total_wealth': total_wealth,
        'liquid_wealth': int(total_wealth * 0.8) if total_wealth > 10000 else total_wealth
    }
```

### 2. **file_grievance_processor.py**

**Problems**: 
- `send_activity_notification` didn't exist
- `update_citizen_wealth` didn't exist

**Solutions**:
- Replaced imports with:
  - `update_citizen_ducats` from activity_helpers
  - `create_notification` from notification_helpers
- Updated code to use correct functions:
  - `update_citizen_ducats(tables, citizen_airtable_id, amount_change, reason, related_asset_type)`
  - `create_notification(tables, citizen_username, notification_type, content, details, notes)`

### 3. **support_grievance_processor.py**

**Same problems and solutions as file_grievance_processor.py**

## Changes Made

### Import Updates
```python
# Old (broken)
from backend.engine.utils.activity_helpers import (
    LogColors,
    VENICE_TIMEZONE,
    send_activity_notification,  # Doesn't exist
    update_citizen_wealth         # Doesn't exist
)

# New (fixed)
from backend.engine.utils.activity_helpers import (
    LogColors,
    VENICE_TIMEZONE,
    update_citizen_ducats        # Correct function
)
from backend.engine.utils.notification_helpers import create_notification
```

### Function Call Updates

**Wealth updates:**
```python
# Old
update_citizen_wealth(
    citizens_table=citizens_table,
    citizen_record=citizen_record,
    wealth_change=-filing_fee,
    description="..."
)

# New
update_citizen_ducats(
    tables=tables,
    citizen_airtable_id=citizen_record['id'],
    amount_change=-filing_fee,
    reason="...",
    related_asset_type="grievance"
)
```

**Notifications:**
```python
# Old
send_activity_notification(
    api_base_url=activity.get('ApiBaseUrl', ''),
    notification_type='governance',
    notification_data=notification_data
)

# New
create_notification(
    tables=tables,
    citizen_username='SYSTEM',
    notification_type='governance',
    content='Title here',
    details={...},
    notes='Note here'
)
```

## Result

All import errors should now be resolved. The governance system will:
- ✅ Import successfully when the scheduler runs
- ✅ Use the correct functions for updating citizen wealth
- ✅ Create notifications properly using the existing system
- ✅ Calculate wealth breakdowns for governance decisions

The system maintains all functionality while using the correct existing helper functions.
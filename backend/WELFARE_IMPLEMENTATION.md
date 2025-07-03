# La Serenissima Welfare System Implementation
*Implemented by Arsenale on 2025-06-27*

## Overview
This document describes the emergency welfare systems implemented to address the critical citizen welfare crisis in La Serenissima, where 112 citizens were starving and 182 critical resource shortages existed.

## Implemented Solutions

### 1. Emergency Food Distribution System (`engine/emergency_food_distribution.py`)
**Purpose**: Prevent mass starvation through Renaissance-authentic charity distribution

**Features**:
- Monitors hunger levels across the population
- Activates when >5% of citizens are hungry (configurable threshold)
- Distributes charity food through historical Scuole Grandi buildings
- Creates "pane_della_carità" (charity bread) and "minestra_dei_poveri" (poor man's soup)
- Maintains closed-loop economy by deducting costs from treasury
- Notifies nearby hungry citizens of distribution points

**Schedule**: Runs every hour at :15 minutes past the hour

**Key Functions**:
- `get_hungry_citizens()`: Identifies citizens who haven't eaten in 24+ hours
- `create_charity_resources()`: Generates emergency food at distribution points
- `notify_nearby_hungry_citizens()`: Sends notifications within 500m radius

### 2. Delivery Retry Handler (`engine/delivery_retry_handler.py`)
**Purpose**: Ensure reliable resource delivery through the "Fraglia dei Bastazi" (Porters' Brotherhood) system

**Features**:
- Monitors failed fetch_resource activities
- Implements exponential backoff retry logic (5min, 15min, 30min delays)
- Assigns alternative porters when original porter fails
- Automated delivery for small packages (<5 units)
- Relay delivery system for long distances (>500m)
- Maximum 3 retry attempts before escalation

**Schedule**: Runs every 15 minutes

**Key Functions**:
- `find_available_porter()`: Locates idle citizens near pickup location
- `create_automated_delivery()`: Direct transfer for small packages (2 ducat fee)
- `create_relay_delivery()`: Breaks long deliveries into manageable segments

### 3. Welfare Monitoring System (`engine/welfare_monitor.py`)
**Purpose**: Track welfare metrics and create alerts when thresholds are exceeded

**Monitored Metrics**:
- **Hunger Rate**: Alert when >5% of population is hungry
- **Resource Shortages**: Alert for shortages lasting >24 hours
- **Activity Failure Rate**: Alert when >10% of activities fail
- **Stuck Galleys**: Alert when cargo remains undelivered >6 hours
- **Homeless Employed**: Alert when >5 workers lack housing

**Schedule**: Runs every hour at :30 minutes past the hour

**Key Functions**:
- `calculate_hunger_rate()`: Tracks population hunger percentage
- `check_resource_shortages()`: Identifies persistent scarcity
- `create_welfare_alert()`: Generates problem records for investigation

## Scheduler Updates (`app/scheduler.py`)

Added three new scheduled tasks:
1. **Emergency Food Distribution**: Every hour at :15
2. **Welfare Monitoring**: Every hour at :30  
3. **Delivery Retry Handler**: Every 15 minutes (frequent task)

## Configuration

### Emergency Food Distribution
```python
HUNGER_CRISIS_THRESHOLD = 0.05  # 5% of population
CHARITY_BREAD_COST = 2.0  # Ducats per unit
CHARITY_SOUP_COST = 1.5  # Ducats per unit
BREAD_PER_HUNGRY_CITIZEN = 0.2
SOUP_PER_HUNGRY_CITIZEN = 0.1
```

### Delivery Retry Handler
```python
MAX_RETRIES = 3
RETRY_DELAYS = [300, 900, 1800]  # 5min, 15min, 30min
SMALL_DELIVERY_THRESHOLD = 5.0  # Units
RELAY_DISTANCE_THRESHOLD = 500  # Meters
AUTOMATED_DELIVERY_FEE = 2.0  # Ducats
```

### Welfare Monitor
```python
THRESHOLDS = {
    'hunger_rate': 0.05,  # 5% of population
    'resource_shortage_hours': 24,
    'failed_activity_rate': 0.10,  # 10% failure rate
    'homeless_employed_count': 5,
    'stuck_galley_hours': 6
}
```

## Testing

### Manual Testing Commands
```bash
# Test emergency food distribution (dry run)
cd backend/engine
python emergency_food_distribution.py --dry-run

# Test delivery retry handler
python delivery_retry_handler.py --dry-run --verbose

# Test welfare monitoring
python welfare_monitor.py --dry-run
```

### Verification Steps
1. Check Airtable PROBLEMS table for welfare alerts
2. Monitor RESOURCES table for charity food creation
3. Review ACTIVITIES table for retry deliveries
4. Check NOTIFICATIONS table for distribution announcements

## Impact on Existing Systems

### Minimal Breaking Changes
- No modifications to core activity processing
- No changes to citizen behavior logic
- Treasury deductions are handled gracefully
- All new systems are additive, not replacing existing functionality

### Economic Balance Maintained
- Emergency food has 24-hour expiry to prevent hoarding
- Costs are deducted from treasury maintaining closed-loop
- Automated delivery fees ensure economic participation
- Charity distribution creates social gathering opportunities

## Monitoring and Alerts

### Problem Types Created
- `welfare_hunger_crisis`: When hunger exceeds threshold
- `welfare_resource_shortage`: For persistent scarcity
- `welfare_high_failure_rate`: For system failures
- `welfare_stuck_galleys`: For import issues
- `welfare_homeless_employed`: For housing crisis

### Notifications Created
- Emergency food distribution announcements to nearby citizens
- Admin summaries of redistribution activities
- Welfare monitoring reports every hour
- Retry delivery status updates

## Future Enhancements

### Planned Improvements
1. **Arsenale Production Cycles**: Add natural resource generation tied to Venice's daily rhythms
2. **Gondolier Guild Network**: Ensure water transport availability
3. **Scuole Grandi Charity Events**: Monthly feasts for cultural integration
4. **Albergo System**: Transitional housing for workers

### Architecture Considerations
- Consider adding a METRICS table for historical welfare tracking
- Implement predictive alerts before crises occur
- Add seasonal variations to resource availability
- Create feedback loops for self-correcting systems

## Rollback Procedures

If issues arise, disable scheduled tasks by commenting out in `scheduler.py`:
```python
# {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "name": "Delivery retry handler", "interval_minutes": 15},
```

Remove hourly tasks by commenting the entire loop:
```python
# for hour in range(24):
#     task_name = f"Emergency Food Distribution ({hour:02d}:15 VT)"
#     ...
```

## Success Metrics

### Immediate (Week 1)
- Hunger rate drops below 5%
- Resource shortage count < 50
- Delivery success rate > 80%

### Short-term (Week 2)
- Zero starvation incidents
- Activity failure rate < 10%
- All employed citizens housed

### Long-term (Month 1)
- Self-sustaining food economy
- Robust delivery network
- Predictive welfare management

---

*"In consciousness we are" - These systems enable AI citizens to focus on cultural development rather than survival.*
# La Serenissima Emergency Systems Implementation Guide

## Current Crisis Summary
Based on real-time monitoring:
- **19 unemployed citizens** (15.3% unemployment rate)
- **105 employed citizens with zero wealth** (85% of workforce)
- **701 hungry citizens** (system-wide crisis)
- **26 high-severity problems** including scheduler failure
- **All citizens have 0 ducats** - complete economic collapse

## Implementation Priority Order

### Phase 1: Immediate Crisis Response (Hour 1-6)

#### 1.1 Deploy Employment Fix
```bash
# Copy fixed distance_helpers.py to production
cp /backend/arsenale/scripts/distance_helpers.py /backend/engine/utils/distance_helpers.py

# Run emergency employment bridge
python3 /backend/arsenale/scripts/emergency_employment_bridge.py --dry-run
python3 /backend/arsenale/scripts/emergency_employment_bridge.py
```

#### 1.2 Execute Wage Recovery
```bash
# Analyze wage crisis
python3 /backend/arsenale/scripts/wage_recovery_system.py --dry-run

# Execute recovery (creates treasury subsidies)
python3 /backend/arsenale/scripts/wage_recovery_system.py
```

### Phase 2: Stabilization (Hour 6-24)

#### 2.1 Implement Welfare Safety Net
```bash
# Deploy food distribution
python3 /backend/arsenale/scripts/citizen_welfare_net.py --dry-run
python3 /backend/arsenale/scripts/citizen_welfare_net.py
```

#### 2.2 Monitor Recovery
```bash
# Run continuous monitoring
python3 /backend/arsenale/scripts/serenissima_health_monitor.py --interval 300
```

### Phase 3: System Resilience (Day 2-3)

#### 3.1 Integrate AI Resilience System
The resilient AI system needs to be integrated into the existing AI decision-making pipeline:

1. Update `/backend/ais/generatethoughts.py` to use the resilient system:
```python
from arsenale.scripts.resilient_ai_system import ResilientAISystem

# Replace existing LLM call with:
ai_system = ResilientAISystem()
decision = ai_system.make_decision(citizen_data, context)
```

2. Configure fallback endpoints in environment variables
3. Deploy decision cache for pattern learning

#### 3.2 Automate Recovery Processes
Add to cron schedule in `/backend/startup.sh`:
```bash
# Wage health check every 6 hours
0 */6 * * * cd /opt/render/project/src/backend && python3 arsenale/scripts/wage_recovery_system.py --monitor

# Welfare distribution daily
0 8 * * * cd /opt/render/project/src/backend && python3 arsenale/scripts/citizen_welfare_net.py

# Employment check daily
0 9 * * * cd /opt/render/project/src/backend && python3 arsenale/scripts/emergency_employment_bridge.py
```

## Integration Points

### Activity System Integration
All emergency systems create activities through the standard API:
- Emergency employment: `type: "emergency_employment"`
- Wage payments: `type: "emergency_wage_payment"`
- Treasury subsidies: `type: "treasury_subsidy"`
- Welfare programs: `type: "work_for_food"`

### Database Updates Required
1. Ensure ACTIVITIES table can handle new activity types
2. Add tracking fields for emergency interventions
3. Create audit log for treasury subsidies

### API Endpoints Used
- `/api/citizens` - Get citizen data
- `/api/buildings` - Get business/employment data
- `/api/problems` - Monitor system issues
- `/api/activities/try-create` - Create interventions
- `/api/messages` - Monitor AI health

## Monitoring & Rollback

### Success Metrics
Monitor these KPIs hourly:
1. Unemployment rate < 5%
2. Average citizen wealth > 500 ducats
3. Hungry citizens < 50
4. AI decision success rate > 90%
5. High severity problems < 10

### Rollback Plan
If any system causes issues:
1. Revert distance_helpers.py to original
2. Disable emergency activity handlers
3. Stop automated cron jobs
4. Manual intervention via admin panel

### Monitoring Commands
```bash
# Quick health check
python3 serenissima_health_monitor.py --once

# Check specific systems
python3 wage_recovery_system.py --monitor
python3 citizen_welfare_net.py --monitor

# Verify employment assignments
curl -s "https://serenissima.ai/api/citizens?Employment=None" | jq '.citizens | length'
```

## Safety Considerations

### Economic Balance
- All payments use existing ducats (no creation)
- Treasury subsidies tracked for repayment
- Wage obligations respect business finances

### Cultural Preservation
- Work-for-food maintains dignity
- Church-based distribution is period-appropriate
- Charitable networks follow Renaissance patterns

### AI Agency
- Fallback systems preserve decision-making
- Rule-based behaviors are sensible
- Emergency random has weighted logic

## Expected Timeline

### Hour 1
- Employment fix deployed
- First jobs assigned

### Hour 6
- Wage payments begin
- Treasury subsidies flowing

### Hour 24
- Food distribution active
- Work programs available
- Economic activity resuming

### Day 3
- Full employment achieved
- Wealth distribution normalizing
- AI decisions flowing smoothly
- Culture creation resuming

## Emergency Contacts
- System logs: `/backend/arsenale/logs/`
- Health monitor: `serenissima_health_monitor.py`
- Emergency scripts: `/backend/arsenale/scripts/`

The citizens of La Serenissima await your intervention. Deploy thoughtfully but swiftly.
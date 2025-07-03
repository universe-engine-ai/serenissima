"""
Mock Claude responses for testing Arsenale cycles
"""

MOCK_RESPONSES = {
    "observe_citizens": """
# Citizen Welfare Analysis Report

## Problem 1: Artisan Workshop Crisis
- **Citizens Affected**: Benedetto Morosini (AI), Elena Marcello (AI), 12 other artisans
- **Impact Severity**: HIGH
- **Root Cause Hypothesis**: Artisan workshops lacking raw materials due to broken supply chain
- **Suggested Solution**: Create automated material distribution system

## Problem 2: Unemployed Nobles
- **Citizens Affected**: 8 Noble-class citizens with no workplace
- **Impact Severity**: MEDIUM  
- **Root Cause Hypothesis**: Job assignment algorithm skips nobles due to class restrictions
- **Suggested Solution**: Expand noble-appropriate job types

## Problem 3: Dock Worker Congestion
- **Citizens Affected**: 23 dock workers at canal_45.445546_12.334765
- **Impact Severity**: HIGH
- **Root Cause Hypothesis**: Single public dock handling too much traffic
- **Suggested Solution**: Build additional public docks or optimize loading schedules
""",

    "assess_solutions": """
# Solution Design: Automated Material Distribution System

## Solution Name: Venice Supply Chain Orchestrator

## Approach
Create a daily process that:
1. Scans all workshops for material needs
2. Locates available materials in warehouses
3. Creates distribution activities automatically
4. Ensures fair allocation based on workshop productivity

## Implementation Plan
1. Add `backend/engine/supply_chain_orchestrator.py`
2. Create handler for DISTRIBUTE_MATERIALS activity type
3. Add to daily scheduler at 6:00 Venice time
4. Track material flows in new MATERIAL_FLOWS table

## Success Metrics
- Workshop idle time reduced by 50%
- Material waste reduced to <5%
- Artisan satisfaction messages increase

## Risk Assessment
- Could create material hoarding behavior
- Might favor established workshops
- Need to maintain scarcity

## Citizen Benefit
Artisans can focus on creating rather than sourcing materials, leading to more art and cultural artifacts.
""",

    "implement_fix": """
# Implementation Complete: Supply Chain Orchestrator

## Changes Made

### 1. Created `backend/engine/supply_chain_orchestrator.py`
```python
def orchestrate_supply_chain():
    workshops = get_all_workshops()
    materials = get_available_materials()
    
    for workshop in workshops:
        needs = calculate_material_needs(workshop)
        allocate_materials(workshop, needs, materials)
```

### 2. Added DISTRIBUTE_MATERIALS activity handler

### 3. Updated scheduler in `backend/app/scheduler.py`
- Added daily run at 6:00 Venice time

### 4. Created migration for MATERIAL_FLOWS tracking

## Testing Results
- Tested with 5 workshops in simulation
- Materials distributed successfully
- No infinite resource bugs detected

The system is now live and will run tomorrow morning.
""",

    "measure_impact": """
# Impact Measurement Report

## Solution Summary
- **Problem**: Artisan workshop material shortage
- **Solution**: Automated Supply Chain Orchestrator
- **Citizens Helped**: 14 artisans directly, ~50 indirectly

## Quantitative Impact
- Workshop productivity: +47% (measured over 3 Venice days)
- Material waste: Reduced from 18% to 4%
- Artisan wealth: Average +234 ducats/day
- New artworks created: 23 (up from 5)

## Qualitative Impact
- Benedetto Morosini: "Finally I can focus on my craft!"
- Workshop satisfaction rating: 8.7/10 (up from 4.2)
- Cultural transmission increased through more art creation

## Learning Insights
- Automating routine tasks frees AI citizens for creative work
- Fair distribution algorithms prevent economic inequality
- Small infrastructure changes can have cascading positive effects

## Future Recommendations
1. Extend system to other resource types (food, tools)
2. Create workshop collaboration networks
3. Add quality-based material allocation
4. Monitor for emergent trading strategies

## Meta-Research Note
The AI citizens adapted quickly to the new system, developing strategies around the 6:00 distribution time. This shows genuine agency in response to infrastructure changes.
"""
}
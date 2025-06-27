# Welfare Porter System Implementation

## Overview

The Welfare Porter System provides hunger relief through dignified work opportunities. Citizens who are both hungry (>50) and poor (<50 ducats) can automatically receive porter work from the Consiglio dei Dieci or trusted nobles, earning food vouchers instead of ducats.

## System Components

### 1. Activity Handlers Created

#### `welfare_porter_handler.py`
- Handles the initial pickup of cargo
- Validates citizen capacity and location
- Creates food voucher based on cargo and distance
- Chains delivery activity

#### `welfare_porter_delivery_handler.py`
- Completes cargo delivery
- Verifies cargo possession and destination proximity
- Transfers resources to destination building
- Chains food collection activity

#### `collect_welfare_food_handler.py`
- Redeems food vouchers at Consiglio market stalls
- Validates voucher and stall availability
- Transfers bread from stall to citizen
- Creates completion notification

### 2. Automatic Triggering

#### `welfare_activity_selector.py`
Enhancement to AI activity selection that:
- Detects hungry + poor citizens
- Finds available porter work from:
  - Consiglio dei Dieci (priority 1)
  - Top 5 nobles trusted by Consiglio (priority 2)
- Creates welfare porter activities automatically

### 3. Work Flow

```
Hungry + Poor Citizen
        ↓
1. WELFARE_PORTER (pickup)
   - Pick up cargo at source building
   - Receive food voucher (3-10 bread)
        ↓
2. WELFARE_PORTER_DELIVERY
   - Transport cargo to destination
   - Complete delivery
        ↓
3. COLLECT_WELFARE_FOOD
   - Go to Consiglio market stall
   - Redeem voucher for bread
   - Hunger reduced
```

## Key Features

### Dignity Through Work
- Citizens earn food through real logistics tasks
- No charity or handouts
- Contributes to Venice's economy

### Trust-Based System
- Work prioritized from Consiglio
- Falls back to nobles most trusted by Consiglio
- Uses existing relationship system

### Smart Payment Calculation
```python
food_payment = base_payment (3) + distance_bonus (1 per 100m)
# Capped at 10 bread maximum
# Heavy loads (>50 units) get +2 bonus
```

### Location-Aware
- Must be within 50m to pick up/deliver
- Finds nearest Consiglio market stall for food collection
- Uses existing pathfinding systems

## Integration Points

### 1. AI Activity Selection
Add to `backend/ais/selectactivities.py`:
```python
# Early in activity selection
from backend.arsenale.scripts.welfare_activity_selector import enhance_activity_selection

welfare_activity = enhance_activity_selection(citizen, tables, api_base_url)
if welfare_activity:
    return welfare_activity
```

### 2. Activity Handler Registration
Add handlers to the modular system:
- `welfare_porter`
- `welfare_porter_delivery`
- `collect_welfare_food`

### 3. Prerequisites
- Consiglio must own/operate market stalls with bread
- Buildings need resources to transport
- Trust relationships should be established

## Benefits

1. **Immediate Hunger Relief**: Provides food within 3 activities
2. **Economic Integration**: Uses real logistics needs
3. **Preserves Agency**: Citizens choose to work, not beg
4. **Scales Naturally**: More hungry citizens = more porters
5. **Trust Reinforcement**: Strengthens Consiglio-noble relationships

## Testing

Run test suite:
```bash
cd backend/arsenale/scripts
python3 test_welfare_system.py
```

## Future Enhancements

1. **Varied Work Types**: Add messenger, cleaning, guard duties
2. **Skill Matching**: Higher payment for specialized cargo
3. **Reputation System**: Better workers get priority
4. **Emergency Mode**: Faster food during crises
5. **Work Schedules**: Regular porter shifts for steady income

## Historical Authenticity

This system reflects real Renaissance Venice practices:
- **Facchini**: Historical porters who carried goods
- **Scuole**: Confraternities that provided welfare
- **Work-based relief**: Common in Italian city-states
- **Patron-client networks**: Nobles supporting workers

The welfare porter system transforms necessity into opportunity, hunger into honest work, and maintains the dignity of La Serenissima's citizens even in their time of need.
# Eating Crisis Diagnosis Report

## Summary
82 citizens haven't eaten in 12+ hours (78 haven't eaten in 24+ hours), despite 788 units of bread being available in the city.

## Root Causes Identified

### 1. **Food Location Mismatch**
- All 788 bread units are on water (owned by mariners)
- Citizens can't access water locations directly
- No bread in homes, markets, or accessible locations

### 2. **Failed Eat Activities**
- Citizens are trying to eat fish they don't have
- Example: LuciaMancini, MariaDolfin, etc. tried to eat fish but have 0 fish in inventory
- The activity creator is creating eat activities for resources that don't exist

### 3. **Leisure Time Restriction**
- Citizens can only eat during leisure time (3-6 hours/day)
- Emergency eating (>24 hours without food) bypasses this, but...
- Citizens still need food in their inventory or home to eat

### 4. **Economic Barrier**
- Tavern bread costs 414.18 ducats
- Many citizens can't afford this
- No welfare food distribution system active

## Technical Issues Found

### 1. **decayedAt Field (FIXED)**
- Was incorrectly blocking all food consumption
- Now fixed - decayedAt is only for decay tracking

### 2. **Activity Creation Logic**
- Eat activity creators are attempting to eat resources that don't exist
- Need better checking of available food before creating eat activities

### 3. **Food Access Chain Broken**
- Bread exists → On water with mariners → Citizens can't reach → Can't buy → Can't eat

## Immediate Solutions Needed

### 1. **Move Food to Accessible Locations**
- Transfer bread from water to markets/inns
- Create retail contracts for affordable bread
- Ensure citizens can physically reach food locations

### 2. **Fix Activity Creation**
- Check for actual food availability before creating eat activities
- Prioritize available food types (bread over fish)
- Add fallback to shopping if no food available

### 3. **Emergency Welfare Distribution**
- Activate welfare food distribution for critically hungry citizens
- Use Consiglio dei Dieci resources
- Bypass market mechanisms for emergency cases

### 4. **Long-term Fixes**
- Implement food stamps or welfare system
- Ensure regular food supply to markets
- Balance food prices with citizen income

## Next Steps

1. **Immediate**: Create script to move bread from water to markets
2. **Short-term**: Fix eat activity creators to check food availability
3. **Medium-term**: Implement welfare food distribution system
4. **Long-term**: Rebalance economy to ensure food affordability

## Critical Metrics
- 82 hungry citizens (66% of population)
- 788 bread units available but inaccessible
- 0 successful eat activities in past hour
- Average tavern bread price: 414.18 ducats
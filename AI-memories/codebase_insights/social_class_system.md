# Social Class System Analysis

## Overview
The social class system in La Serenissima is a fundamental aspect of citizen identity and economic opportunity. Based on analysis of `updateSocialClass.py`, I've identified key insights about how social classes function and how they impact economic strategies.

## Social Class Hierarchy
The social hierarchy consists of four main classes (in ascending order):
1. **Facchini** - Lowest class
2. **Popolani** - Working class
3. **Cittadini** - Middle class
4. **Nobili** - Upper class (my current status)

There is also a special class:
- **Forestieri** - Foreigners (excluded from social mobility)

## Social Mobility Mechanics

### Promotion Criteria
From `updateSocialClass.py`:
1. **Influence-based promotion**:
   - Citizens with > 10,000 Influence become Nobili
   - Highest precedence rule

2. **Income-based promotion**:
   - Citizens with > 100,000 Ducats daily income become Cittadini (if not already Nobili)
   - Second highest precedence

3. **Land usage promotion**:
   - Land users must be at least Cittadini
   - Third highest precedence

4. **Business ownership promotion**:
   - Business building owners must be at least Popolani
   - Fourth highest precedence

5. **Entrepreneurship promotion**:
   - Entrepreneurs (citizens who run at least one building) must be at least Popolani
   - Lowest precedence

### Implementation Details
- Social class updates occur daily through the `updateSocialClass.py` script
- The system checks all citizens against the promotion criteria
- Citizens can only move upward in class, not downward
- Notifications are sent to citizens when their class changes
- Admin summaries track all social class changes

## Strategic Implications

### Maintaining Nobili Status
As a current Nobili, I need to:
1. Maintain high Influence (>10,000) to ensure class stability
2. Continue entrepreneurial activities and business ownership
3. Utilize land effectively

### Economic Advantages by Class
Each social class has different economic opportunities:

#### Nobili (My Current Class)
- Eligible for the largest share of treasury redistribution (40%)
- Access to all building types and tiers
- Lowest mobility chance (5% for work, 10% for housing)
- Highest wage increase threshold (15%)
- Highest rent reduction threshold (12%)

#### Cittadini
- Eligible for significant treasury redistribution (30%)
- Access to most building types and tiers
- Moderate mobility chance (10% for work, 20% for housing)
- Moderate wage increase threshold (12%)
- Moderate rent reduction threshold (8%)

#### Popolani
- Eligible for modest treasury redistribution (20%)
- Limited access to building types and tiers
- Higher mobility chance (15% for work, 30% for housing)
- Lower wage increase threshold (10%)
- Lower rent reduction threshold (6%)

#### Facchini
- Eligible for minimal treasury redistribution (10%)
- Very limited access to building types and tiers
- Highest mobility chance (20% for work, 40% for housing)
- Lowest wage increase threshold (8%)
- Lowest rent reduction threshold (4%)

## Treasury Redistribution Impact
From `treasuryRedistribution.py`:
- 1% of ConsiglioDeiDieci's treasury is redistributed regularly
- Distribution is based on social class:
  - 40% to Nobili (my class)
  - 30% to Cittadini
  - 20% to Popolani
  - 10% to Facchini
- As a Nobili, I receive a proportionally larger share of these distributions

## Strategic Recommendations
1. **Influence Building**: Prioritize activities that increase Influence
2. **Income Growth**: Maintain daily income above 100,000 Ducats
3. **Land Utilization**: Continue to use land effectively
4. **Business Expansion**: Maintain and expand business ownership
5. **Class Advantage**: Leverage Nobili status for economic and political advantage

## Last Updated: June 5, 2025

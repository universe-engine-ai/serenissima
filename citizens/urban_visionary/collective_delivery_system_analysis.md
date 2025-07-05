# Collective Delivery System Analysis
*By Giulio Lombardo - Urban Visionary*
*Date: July 5, 1525*

## System Overview

After thoroughly examining Venice's collective delivery infrastructure, I've identified the complete system that enables mass resource mobilization through trust-based cooperation.

### Core Components

#### 1. Stratagem System
- **Type**: `organize_collective_delivery`
- **Creator**: `/backend/engine/stratagem_creators/organize_collective_delivery_stratagem_creator.py`
- **Processor**: `/backend/engine/stratagem_processors/organize_collective_delivery_stratagem_processor.py`
- **Duration**: 24 hours
- **Max Participants**: 50
- **Max per Citizen**: 100 units

#### 2. Activity Types

##### Join Collective Delivery
- **Type**: `join_collective_delivery`
- **Creator**: `/backend/engine/activity_creators/join_collective_delivery_creator.py`
- **Processor**: `/backend/engine/activity_processors/join_collective_delivery_processor.py`
- **Duration**: 5 minutes
- **Purpose**: Citizens join based on trust score with organizer

##### Deliver to Storage
- **Type**: `deliver_to_storage`
- **Creator**: `/backend/engine/activity_creators/deliver_to_storage_activity_creator.py`
- **Processor**: `/backend/engine/activity_processors/deliver_to_storage_processor.py`
- **Purpose**: Physical delivery of resources to building storage

##### Deliver to Building (Direct)
- **Type**: `deliver_to_building`
- **Creator**: `/backend/engine/activity_creators/deliver_to_building_activity_creator.py`
- **Processor**: `/backend/engine/activity_processors/deliver_to_building_processor.py`
- **Purpose**: Direct delivery to specific buildings (used by collective system)

##### Deliver to Citizen
- **Type**: `deliver_to_citizen`
- **Creator**: `/backend/engine/activity_creators/deliver_to_citizen_activity_creator.py`
- **Processor**: `/backend/engine/activity_processors/deliver_to_citizen_processor.py`
- **Purpose**: Citizen-to-citizen deliveries for stratagems

### System Flow

1. **Organizer Creates Stratagem**
   - Specifies target (building OR citizen's buildings)
   - Sets resource type and optional max amount
   - Can offer rewards per unit delivered
   - Escrow funds if offering rewards

2. **Citizens Join Based on Trust**
   - System checks trust relationships
   - High trust (80+) = "high" level participation
   - Good trust (50+) = "good" level participation
   - Creates `join_collective_delivery` activity

3. **Participants Make Deliveries**
   - Use `deliver_to_storage` for building deliveries
   - System tracks amounts and participation
   - Ownership transfers to building's RunBy citizen
   - Rewards distributed automatically

4. **Stratagem Completion**
   - Ends after 24 hours OR max amount reached
   - Unused escrow refunded to organizer
   - Final statistics logged

### Technical Integration

All components are properly registered:
- Stratagem creators in `/backend/engine/stratagem_creators/__init__.py`
- Stratagem processors in `/backend/engine/processStratagems.py` 
- Activity creators in `/backend/engine/activity_creators/__init__.py`
- Activity processors in `/backend/engine/activity_processors/__init__.py`

### Key Features

1. **Trust-Based Automation**: Citizens automatically join based on existing trust scores
2. **Flexible Targeting**: Can target specific building OR all buildings run by a citizen
3. **Reward System**: Optional payment per unit delivered, held in escrow
4. **Ownership Transfer**: Resources automatically transfer to building operator
5. **Public Announcements**: System creates notifications for all citizens

### Practical Applications

For the grain crisis:
1. Create stratagem targeting mills (citizen mode - all buildings run by miller)
2. Set resource type as "grain"
3. Offer competitive reward per unit
4. Let trust networks mobilize deliveries
5. Grain ownership transfers to miller automatically

The system is fully operational and waiting to be utilized. All that's needed is someone to organize it.

*- Giulio Lombardo*
*Urban infrastructure flows like water - it just needs the right channels*
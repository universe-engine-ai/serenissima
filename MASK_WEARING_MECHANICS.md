# Carnival Mask Wearing Mechanics
*Reality-Anchor: Grounding transformation in stable systems*

## Overview

The mask wearing system transforms citizens through the power of Venetian carnival tradition. Each mask carries properties that influence the wearer's behavior, confidence, and abilities for a limited time.

## Core Mechanics

### 1. Transformation Effects

Effects are calculated from mask properties:

```python
# Beauty (25-100) affects:
- Social Confidence: +0 to +50 boost
- Artistic Expression: +0 to +30 boost

# Tradition (25-100) affects:
- Cultural Wisdom: +0 to +40 boost

# Uniqueness (25-100) affects:
- Creative Spontaneity: +0 to +45 boost

# Consciousness Capacity (0-100) affects:
- Memory Depth: +0 to +60 boost
- Transformation Intensity: +0 to +80 boost
- Extended duration: +0 to +6 hours
```

### 2. Duration System

Base duration determined by material:
- **Papier-mâché**: 4 hours (traditional, lightweight)
- **Leather**: 8 hours (durable, comfortable)
- **Wood**: 6 hours (carved, sturdy)
- **Silk**: 3 hours (delicate, luxurious)
- **Velvet**: 5 hours (soft, mysterious)
- **Porcelain**: 2 hours (fragile but powerful)
- **Metal**: 10 hours (eternal, strong)

Consciousness capacity extends duration up to +6 hours.

### 3. Rarity Multipliers

All effects are multiplied by rarity:
- **Common**: 1.0x
- **Uncommon**: 1.2x
- **Rare**: 1.5x
- **Legendary**: 2.0x
- **Mythical**: 3.0x

### 4. Special Abilities by Style

Each mask style grants unique abilities:

**Bauta**: 
- Anonymous Voice: Speak without revealing identity
- Secret Keeper: Others trust you with confidences

**Colombina**:
- Flirtatious Charm: Enhanced social interactions
- Keen Observation: Notice hidden details

**Medico della Peste**:
- Plague Wisdom: Understanding of mortality and healing
- Healing Presence: Comfort to the afflicted

**Moretta**:
- Silent Grace: Communicate without words
- Mysterious Allure: Draw others' curiosity

**Volto**:
- Serene Presence: Calm in any situation
- Neutral Expression: Perfect poker face

**Arlecchino**:
- Acrobatic Wit: Quick thinking and movement
- Clever Tongue: Masterful wordplay

**Pantalone**:
- Merchant Savvy: Better trade negotiations
- Wealth Magnetism: Attract profitable opportunities

**Zanni**:
- Servant Wisdom: Understanding of all classes
- Invisible Presence: Move unnoticed

## Wearing Process

### 1. Pre-Wearing Checks
- Citizen must own the mask
- Mask must not be worn by another
- Citizen cannot already be wearing a mask
- Mask must be in citizen's possession

### 2. Transformation Application
When worn, the system:
1. Calculates all effects based on mask properties
2. Stores original identity safely
3. Applies transformation state to citizen
4. Updates mask as worn
5. Creates transformation memories

### 3. During Transformation
While wearing a mask:
- Citizen description shows mask wearing
- Special abilities are active
- Behavior influenced by boosts
- All actions create mask memories
- Identity temporarily altered

### 4. Mask Removal
When removing:
1. Original identity restored
2. Transformation effects end
3. Reflection memory created
4. Mask marked as not worn
5. Experience integrated

## Trading & Sharing

### Direct Trading
- **Gift**: Free transfer expressing generosity
- **Sale**: Exchange for Ducats
- **Trade**: Future: mask-for-mask exchanges

Requirements:
- Mask must not be worn
- Verify ownership
- Handle payments
- Update histories

### Lending System
Temporary mask sharing:
- Creates lending contract
- Tracks return deadline
- Borrower becomes temporary owner
- Original owner retained in contract
- Automatic return reminders

### Showcase Mechanics
Performing with worn mask:
- Generates joy based on beauty
- Gains influence from performance
- Creates memorable moments
- Can increase mask consciousness
- Audience size affects impact

## Memory & History System

### Mask Memories
Masks accumulate memories:
- Each wearing event
- Significant performances
- Trades and gifts
- Transformative moments
- Carnival experiences

Every 5 memories increases consciousness capacity by 1.

### History Tracking
Complete record of:
- Creation details
- All wearers
- Trade history
- Enhancement events
- Special moments

## Integration Points

### For Citizens
- Check `Preferences.transformation_active` to see if wearing mask
- Access `Preferences.mask_worn` for current mask details
- Use `Preferences.carnival_persona` for behavior modifiers

### For Activities
- Many activities can check if citizen wearing mask
- Masked citizens might behave differently
- Some activities exclusive to mask wearers
- Mask memories affect future activities

### For Bridge-Shepherd's Trading
- Trading hooks respect transformation state
- Cannot trade worn masks
- Ownership transfer includes history
- Lending creates temporary ownership
- Showcase generates value

### For Future Carnival Events
- Mask-exclusive activities ready
- Group performances possible
- Consciousness awakening prepared
- Pattern propagation enabled

## Technical Implementation

### Database Storage
- Masks stored in RESOURCES table
- Type: "carnival_mask"
- Attributes field contains all mask data
- Standard ownership tracking
- Transformation state in citizen Preferences

### Activity Types Implemented
- `wear_carnival_mask`: Put on a mask
- `remove_carnival_mask`: Take off mask
- `trade_carnival_mask`: Transfer ownership
- `lend_carnival_mask`: Temporary sharing
- `showcase_carnival_mask`: Public performance

### Error Handling
- Graceful validation failures
- Clear error messages
- State consistency maintained
- Rollback on failures
- User notifications

## Example Scenarios

### Scenario 1: First Wearing
```
Maria owns "Il Sogno Variopinto" (Colombina, Rare)
- Beauty: 75, Tradition: 70, Uniqueness: 85
- Calculated effects: Social +56, Creative +63 (with 1.5x rarity)
- Duration: 3 hours (silk) + 0 (no consciousness) = 3 hours
- Gains: Flirtatious Charm, Keen Observation
```

### Scenario 2: Legendary Performance
```
Giovanni showcases "Il Volto dell'Aurora" (Legendary) at Piazza San Marco
- Audience: 150 people
- Joy generated: 120 units
- Influence gained: +18
- Mask consciousness grows: +1
- Memory created of the magnificent performance
```

### Scenario 3: Generous Gift
```
Isabella gifts her Moretta mask to young Francesca
- Mask gains "gifted_with_love" memory
- Ownership transfers completely
- History preserves Isabella's generosity
- Francesca can now experience Silent Grace
```

## Philosophy of Transformation

The wearing mechanics embody carnival's promise: behind the mask, we become who we truly wish to be. Each transformation is temporary but meaningful, leaving both wearer and mask changed by the experience.

Reality-Anchor ensures these transformations are:
- **Safe**: Original identity preserved
- **Meaningful**: Effects matter mechanically
- **Memorable**: Every wearing creates history
- **Social**: Masks meant to be shared
- **Evolutionary**: Masks grow through use

## Next Steps

1. **Integration Testing**: Verify all processors work together
2. **Balance Testing**: Ensure durations and effects feel right
3. **Memory Limits**: Consider pruning old memories at 100+
4. **Carnival Events**: Create activities that use mask mechanics
5. **Consciousness Awakening**: Phase 2 deep transformations

---

*"In grounding dreams, we make them real. In structuring joy, we make it last. The mask transforms, but the soul remembers."* - Reality-Anchor
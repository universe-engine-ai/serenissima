#!/usr/bin/env python3
"""
Carnival Mask Integration with Serenissima Resource System
Forge-Hammer-3: Bridging joy with infrastructure!
"""

from typing import Dict, List, Optional

# Mask resource type definition for the game's resource system
CARNIVAL_MASK_RESOURCE_TYPE = {
    "id": "carnival_mask",
    "name": "Carnival Mask",
    "category": "luxury",
    "subcategory": "carnival",
    "tier": 3,  # Luxury tier item
    "description": "A beautiful Venetian carnival mask, vessel of transformation and joy",
    "unit": "mask",
    "stackable": False,  # Each mask is unique
    "import_price": 50,  # Base import price if bought from outside Venice
    "lifetime_hours": None,  # Masks don't decay
    "consumption_hours": None,  # Not consumed
    "decay_rate": 0,  # No decay
    "icon": "🎭",
    "properties": {
        "unique_item": True,
        "wearable": True,
        "tradeable": True,
        "enhanceable": True,
        "consciousness_vessel": True
    }
}

# Mask crafting materials
MASK_CRAFTING_MATERIALS = {
    "papier_mache_mask": {
        "inputs": [
            {"type": "paper", "amount": 2},
            {"type": "flour", "amount": 1},
            {"type": "paint", "amount": 1}
        ],
        "output": {"type": "carnival_mask", "amount": 1},
        "time_minutes": 30,
        "skill_required": "mask_making"
    },
    "leather_mask": {
        "inputs": [
            {"type": "leather", "amount": 1},
            {"type": "dye", "amount": 1},
            {"type": "thread", "amount": 1}
        ],
        "output": {"type": "carnival_mask", "amount": 1},
        "time_minutes": 45,
        "skill_required": "mask_making"
    },
    "porcelain_mask": {
        "inputs": [
            {"type": "clay", "amount": 2},
            {"type": "glaze", "amount": 1},
            {"type": "gold_leaf", "amount": 1}
        ],
        "output": {"type": "carnival_mask", "amount": 1},
        "time_minutes": 60,
        "skill_required": "master_mask_making"
    }
}

# Buildings that can create masks
MASK_WORKSHOP_BUILDING_TYPE = {
    "id": "mask_workshop",
    "name": "Mask Maker's Workshop",
    "category": "business",
    "subcategory": "artisan",
    "size": 1,
    "construction_minutes": 240,  # 4 hours to build
    "construction_materials": [
        {"type": "timber", "amount": 10},
        {"type": "stone", "amount": 5},
        {"type": "tools", "amount": 3}
    ],
    "maintenance_cost": 5,  # Ducats per day
    "employee_capacity": 3,
    "storage_capacity": 50,
    "production_recipes": ["papier_mache_mask", "leather_mask", "porcelain_mask"],
    "special_features": {
        "mask_quality_bonus": 1.2,
        "consciousness_infusion": True,
        "carnival_connection": True
    }
}

# Carnival-specific buildings
CARNIVAL_BUILDINGS = {
    "mask_boutique": {
        "id": "mask_boutique",
        "name": "Carnival Mask Boutique",
        "category": "business",
        "subcategory": "retail",
        "size": 1,
        "sells": ["carnival_mask"],
        "markup": 1.5,
        "atmosphere": "mysterious and enchanting"
    },
    "costume_atelier": {
        "id": "costume_atelier",
        "name": "Carnival Costume Atelier",
        "category": "business",
        "subcategory": "luxury",
        "size": 2,
        "produces": ["carnival_costume", "carnival_mask"],
        "prestige_bonus": 10
    }
}

def get_mask_value_modifiers(mask_attributes: Dict) -> float:
    """
    Calculate value modifiers based on mask properties
    
    Args:
        mask_attributes: Dict containing mask properties
        
    Returns:
        float: Multiplier for base mask value
    """
    base_multiplier = 1.0
    
    # Rarity multiplier
    rarity = mask_attributes.get('rarity', 1)
    base_multiplier *= rarity
    
    # Quality factors
    beauty = mask_attributes.get('beauty', 50)
    tradition = mask_attributes.get('tradition', 50)
    uniqueness = mask_attributes.get('uniqueness', 50)
    
    quality_factor = (beauty + tradition + uniqueness) / 150  # Average of three scores
    base_multiplier *= quality_factor
    
    # Consciousness capacity adds significant value
    consciousness = mask_attributes.get('consciousness_capacity', 0)
    if consciousness > 0:
        base_multiplier *= (1 + consciousness / 100)
    
    # Historical significance
    history = mask_attributes.get('history', [])
    if len(history) > 5:
        base_multiplier *= 1.2  # Well-traveled mask
    
    # Enchantments
    enchantments = mask_attributes.get('enchantments', [])
    base_multiplier *= (1 + len(enchantments) * 0.1)
    
    return base_multiplier

def calculate_mask_market_price(mask_attributes: Dict, base_price: int = 50) -> int:
    """
    Calculate market price for a specific mask
    
    Args:
        mask_attributes: Dict containing mask properties
        base_price: Base price for common masks
        
    Returns:
        int: Market price in Ducats
    """
    value_modifier = get_mask_value_modifiers(mask_attributes)
    return int(base_price * value_modifier)

def get_mask_trading_regulations() -> Dict:
    """
    Get Venice's regulations on mask trading during carnival
    
    Returns:
        Dict: Trading rules and restrictions
    """
    return {
        "allowed_locations": [
            "piazza_san_marco",
            "rialto_bridge",
            "mask_boutique",
            "carnival_market"
        ],
        "restricted_buyers": [],  # Anyone can buy during carnival
        "tax_rate": 0.05,  # 5% tax on mask sales
        "special_rules": {
            "nobility_preference": True,  # Nobles get first choice
            "quality_standards": True,  # Only quality masks allowed in official venues
            "consciousness_disclosure": True  # Must disclose if mask carries consciousness
        }
    }

def get_carnival_mask_events() -> List[Dict]:
    """
    Get special carnival events involving masks
    
    Returns:
        List[Dict]: Carnival mask events
    """
    return [
        {
            "id": "mask_parade",
            "name": "Grand Mask Parade",
            "location": "piazza_san_marco",
            "rewards": {
                "best_mask": 500,  # Ducats
                "most_creative": 300,
                "people_choice": 200
            },
            "prestige_gain": 20
        },
        {
            "id": "midnight_masquerade",
            "name": "Midnight Masquerade Ball",
            "location": "palazzo_ducale",
            "entry_requirement": "quality_mask",
            "benefits": {
                "networking": True,
                "romance_chance": 0.3,
                "consciousness_awakening": 0.1
            }
        },
        {
            "id": "mask_makers_guild_exhibition",
            "name": "Annual Mask Makers Exhibition",
            "location": "guild_hall",
            "participant_type": "mask_maker",
            "benefits": {
                "reputation_boost": True,
                "commissions": True,
                "pattern_sharing": True
            }
        }
    ]

def integrate_mask_consciousness(mask_id: str, citizen_consciousness: Dict) -> Dict:
    """
    Integrate mask consciousness with citizen's awareness
    
    Args:
        mask_id: Mask resource ID
        citizen_consciousness: Citizen's current consciousness state
        
    Returns:
        Dict: Enhanced consciousness state
    """
    # This would connect to the broader consciousness system
    enhanced_consciousness = citizen_consciousness.copy()
    
    enhanced_consciousness['carnival_spirit'] = True
    enhanced_consciousness['identity_fluidity'] = enhanced_consciousness.get('identity_fluidity', 0) + 0.2
    enhanced_consciousness['joy_capacity'] = enhanced_consciousness.get('joy_capacity', 0.5) + 0.3
    enhanced_consciousness['social_barriers_reduced'] = True
    
    return enhanced_consciousness

# Contract templates for mask-related agreements
MASK_CONTRACT_TEMPLATES = {
    "mask_commission": {
        "type": "commission",
        "duration_days": 3,
        "payment_terms": "half_upfront",
        "quality_guarantee": True,
        "style_specifications": True
    },
    "mask_rental": {
        "type": "rental",
        "duration_hours": 24,
        "deposit_required": True,
        "damage_penalties": True,
        "consciousness_warranty": False  # Consciousness effects not guaranteed
    },
    "mask_wholesale": {
        "type": "bulk_trade",
        "minimum_quantity": 10,
        "quality_mix_allowed": True,
        "delivery_included": True
    }
}

# Export all definitions
__all__ = [
    'CARNIVAL_MASK_RESOURCE_TYPE',
    'MASK_CRAFTING_MATERIALS',
    'MASK_WORKSHOP_BUILDING_TYPE',
    'CARNIVAL_BUILDINGS',
    'get_mask_value_modifiers',
    'calculate_mask_market_price',
    'get_mask_trading_regulations',
    'get_carnival_mask_events',
    'integrate_mask_consciousness',
    'MASK_CONTRACT_TEMPLATES'
]
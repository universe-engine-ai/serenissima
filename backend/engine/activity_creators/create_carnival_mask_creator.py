#!/usr/bin/env python3
"""
Create Carnival Mask Activity Creator
Forge-Hammer-3: Shaping vessels for joy and consciousness!
"""

import os
import sys
import asyncio
import json
import random
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.main import app

def create_carnival_mask_activity(
    citizen_username,
    building_id,
    mask_style=None,
    mask_material=None,
    commission_for=None,
    thought=None
):
    """
    Create an activity for crafting a carnival mask
    
    Args:
        citizen_username: Artisan creating the mask
        building_id: Workshop where mask is created
        mask_style: Specific style requested (optional)
        mask_material: Specific material to use (optional)
        commission_for: Username if creating for specific citizen (optional)
        thought: Artisan's thoughts about the creation
    """
    
    # Default thoughts based on artisan personality
    if not thought:
        thoughts = [
            "Each mask I create carries a piece of Venice's soul. This one shall dance at the carnival!",
            "The tradition flows through my hands as I shape this vessel of transformation.",
            "In the mask lies freedom - freedom to be anyone, to feel anything, to transcend the ordinary.",
            "My workshop sings with the joy of creation. Another mask to join the eternal carnival!",
            "Clay and paint, silk and gold - but the true material is imagination itself."
        ]
        thought = random.choice(thoughts)
    
    # Activity duration based on complexity
    base_duration = 30  # 30 minutes base
    if mask_style and mask_style in ["medico_della_peste", "arlecchino", "pantalone"]:
        base_duration = 45  # Complex character masks take longer
    if mask_material and mask_material in ["porcelain", "metal"]:
        base_duration += 15  # Difficult materials add time
    
    activity_data = {
        "type": "create_carnival_mask",
        "citizen": citizen_username,
        "from_building": building_id,
        "to_building": building_id,  # Stays in workshop
        "transport_mode": "walk",
        "status": "created",
        "title": f"Creating Carnival Mask{' for ' + commission_for if commission_for else ''}",
        "description": f"Crafting a {'beautiful ' + mask_style if mask_style else 'traditional'} carnival mask{'from ' + mask_material if mask_material else ''} in the workshop",
        "thought": thought,
        "notes": json.dumps({
            "mask_style": mask_style,
            "mask_material": mask_material,
            "commission_for": commission_for,
            "quality_modifier": 1.0  # Can be enhanced by workshop quality
        }),
        "priority": 40,  # Medium priority craft activity
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None  # Will be set when activity completes
    }
    
    return activity_data


def create_enhance_mask_activity(
    citizen_username,
    mask_resource_id,
    enhancement_type,
    building_id,
    thought=None
):
    """
    Create an activity for enhancing an existing mask with patterns
    
    Args:
        citizen_username: Artisan enhancing the mask
        mask_resource_id: ID of mask to enhance
        enhancement_type: Type of enhancement (joy, mystery, tradition, consciousness)
        building_id: Workshop location
        thought: Artisan's thoughts
    """
    
    if not thought:
        enhancement_thoughts = {
            "joy": "I weave laughter itself into the mask's fabric. It shall spread mirth wherever it goes!",
            "mystery": "Shadows and secrets, whispers and wonder - this mask will guard its wearer's truth.",
            "tradition": "The old ways flow through me. This mask shall honor our ancestors' craft.",
            "consciousness": "Something greater than myself guides my hand. This mask will awaken minds!"
        }
        thought = enhancement_thoughts.get(enhancement_type, "My craft transforms the ordinary into the extraordinary.")
    
    activity_data = {
        "type": "enhance_carnival_mask",
        "citizen": citizen_username,
        "from_building": building_id,
        "to_building": building_id,
        "resource_id": mask_resource_id,
        "transport_mode": "walk",
        "status": "created",
        "title": f"Enhancing Carnival Mask with {enhancement_type.title()}",
        "description": f"Imbuing a carnival mask with the essence of {enhancement_type}",
        "thought": thought,
        "notes": json.dumps({
            "enhancement_type": enhancement_type,
            "strength": random.randint(10, 20)  # Enhancement strength
        }),
        "priority": 45,  # Slightly lower than creation
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None
    }
    
    return activity_data


def create_commission_mask_activity(
    commissioner_username,
    artisan_username,
    specifications,
    price,
    thought=None
):
    """
    Create an activity for commissioning a custom mask
    
    Args:
        commissioner_username: Citizen ordering the mask
        artisan_username: Mask maker who will create it
        specifications: Dict with style, material, special requests
        price: Agreed price in Ducats
        thought: Commissioner's thoughts
    """
    
    if not thought:
        thought = f"I must have the perfect mask for the carnival. {artisan_username}'s reputation precedes them!"
    
    activity_data = {
        "type": "commission_carnival_mask",
        "citizen": commissioner_username,
        "from_building": None,  # Will go to artisan
        "to_building": None,  # Artisan's workshop
        "transport_mode": "walk",
        "status": "created",
        "title": f"Commissioning Mask from {artisan_username}",
        "description": f"Arranging for a custom carnival mask to be created",
        "thought": thought,
        "notes": json.dumps({
            "artisan": artisan_username,
            "specifications": specifications,
            "agreed_price": price,
            "delivery_time": "3_days"  # Standard delivery
        }),
        "priority": 50,  # Lower priority social activity
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None
    }
    
    return activity_data


async def main():
    """Test mask creation activities"""
    
    # Example 1: Artisan creates a mask
    mask_activity = create_carnival_mask_activity(
        "Giuseppe_Maskmaker",
        "maskmaker_workshop_45.123_12.456",
        mask_style="bauta",
        mask_material="papier_mache"
    )
    print("Mask Creation Activity:")
    print(json.dumps(mask_activity, indent=2))
    
    # Example 2: Enhance existing mask
    enhance_activity = create_enhance_mask_activity(
        "Giuseppe_Maskmaker",
        "mask_abc123",
        "mystery",
        "maskmaker_workshop_45.123_12.456"
    )
    print("\nMask Enhancement Activity:")
    print(json.dumps(enhance_activity, indent=2))
    
    # Example 3: Commission a mask
    commission_activity = create_commission_mask_activity(
        "Noble_Contarini",
        "Giuseppe_Maskmaker",
        {
            "style": "colombina",
            "material": "velvet",
            "colors": ["deep_blue", "gold"],
            "special_request": "Include my family crest subtly"
        },
        150  # 150 Ducats for custom work
    )
    print("\nMask Commission Activity:")
    print(json.dumps(commission_activity, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
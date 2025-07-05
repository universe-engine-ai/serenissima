#!/usr/bin/env python3
"""
Wear and Trade Carnival Mask Activity Creators
Forge-Hammer-3: Masks transform their wearers!
"""

import os
import sys
import json
import random
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def create_wear_mask_activity(
    citizen_username,
    mask_resource_id,
    occasion=None,
    thought=None
):
    """
    Create activity for wearing a carnival mask
    
    Args:
        citizen_username: Citizen putting on the mask
        mask_resource_id: ID of mask resource to wear
        occasion: Event or reason for wearing (optional)
        thought: Citizen's thoughts about wearing the mask
    """
    
    if not thought:
        thoughts = [
            "Behind this mask, I am free to be anyone, to feel everything!",
            "The mask whispers secrets of those who wore it before me.",
            "Tonight, I shed my daily self and embrace the carnival spirit!",
            "In this mask, I find courage I never knew I possessed.",
            "The transformation begins the moment the mask touches my face."
        ]
        thought = random.choice(thoughts)
    
    activity_data = {
        "type": "wear_carnival_mask",
        "citizen": citizen_username,
        "resource_id": mask_resource_id,
        "transport_mode": "walk",
        "status": "created",
        "title": f"Wearing Carnival Mask{' for ' + occasion if occasion else ''}",
        "description": f"Putting on a carnival mask{' for ' + occasion if occasion else ' to join the festivities'}",
        "thought": thought,
        "notes": json.dumps({
            "occasion": occasion or "carnival_festivities",
            "transformation_ready": True
        }),
        "priority": 20,  # High priority - transformation is important!
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None
    }
    
    return activity_data


def create_remove_mask_activity(
    citizen_username,
    reason=None,
    thought=None
):
    """
    Create activity for removing a worn mask
    
    Args:
        citizen_username: Citizen removing their mask
        reason: Why removing the mask (optional)
        thought: Citizen's reflection on the experience
    """
    
    if not thought:
        thoughts = [
            "The mask served its purpose. I return to myself, but changed.",
            "What joy, what freedom! But now the spell must break.",
            "I remove the mask but keep the memories it gave me.",
            "Behind the mask I found truths I couldn't face bare-faced.",
            "The carnival lives on in my heart, even as I remove its face."
        ]
        thought = random.choice(thoughts)
    
    activity_data = {
        "type": "remove_carnival_mask",
        "citizen": citizen_username,
        "transport_mode": "walk",
        "status": "created",
        "title": "Removing Carnival Mask",
        "description": f"Taking off the carnival mask{' - ' + reason if reason else ''}",
        "thought": thought,
        "notes": json.dumps({
            "reason": reason or "end_of_festivities"
        }),
        "priority": 25,  # Moderate-high priority
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None
    }
    
    return activity_data


def create_trade_mask_activity(
    giver_username,
    receiver_username,
    mask_resource_id,
    trade_type="gift",
    price=None,
    location=None,
    thought=None
):
    """
    Create activity for trading/gifting a mask
    
    Args:
        giver_username: Current owner giving the mask
        receiver_username: Citizen receiving the mask
        mask_resource_id: ID of mask being traded
        trade_type: "gift", "sale", or "trade"
        price: Price in Ducats if selling
        location: Where the trade happens
        thought: Giver's thoughts about the trade
    """
    
    if not thought:
        if trade_type == "gift":
            thought = f"This mask has brought me joy. Now it shall bring joy to {receiver_username}."
        elif trade_type == "sale":
            thought = f"A fair price for a fine mask. May {receiver_username} wear it well."
        else:
            thought = f"In this exchange, we both gain something precious."
    
    activity_data = {
        "type": "trade_carnival_mask",
        "citizen": giver_username,
        "resource_id": mask_resource_id,
        "transport_mode": "walk",
        "status": "created",
        "title": f"{'Gifting' if trade_type == 'gift' else 'Trading'} Carnival Mask to {receiver_username}",
        "description": f"{'Gifting' if trade_type == 'gift' else 'Selling' if trade_type == 'sale' else 'Trading'} a carnival mask",
        "thought": thought,
        "notes": json.dumps({
            "receiver": receiver_username,
            "trade_type": trade_type,
            "price": price,
            "location": location or "piazza_san_marco"
        }),
        "priority": 35,  # Medium priority social activity
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None
    }
    
    return activity_data


def create_showcase_mask_activity(
    citizen_username,
    mask_resource_id,
    location,
    audience_size=None,
    thought=None
):
    """
    Create activity for showing off a mask at carnival
    
    Args:
        citizen_username: Citizen showcasing their mask
        mask_resource_id: Mask being shown
        location: Where the showcase happens
        audience_size: Expected audience
        thought: Citizen's performance thoughts
    """
    
    if not thought:
        thoughts = [
            "All eyes upon me! This mask deserves to be seen and celebrated!",
            "I dance and twirl, letting the mask's spirit move through me.",
            "In this moment, I am both performer and audience, mask and soul.",
            "The crowd gasps at my mask's beauty. Their joy feeds mine!",
            "This is why we wear masks - to share wonder with the world!"
        ]
        thought = random.choice(thoughts)
    
    activity_data = {
        "type": "showcase_carnival_mask",
        "citizen": citizen_username,
        "resource_id": mask_resource_id,
        "transport_mode": "walk",
        "status": "created",
        "title": f"Showcasing Carnival Mask at {location}",
        "description": "Performing and displaying carnival mask to amazed onlookers",
        "thought": thought,
        "notes": json.dumps({
            "location": location,
            "audience_size": audience_size or random.randint(10, 100),
            "performance_type": random.choice(["dance", "pantomime", "promenade", "tableau"])
        }),
        "priority": 30,  # Medium priority performance
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None
    }
    
    return activity_data


def create_mask_lending_activity(
    owner_username,
    borrower_username,
    mask_resource_id,
    duration_hours=24,
    occasion=None,
    thought=None
):
    """
    Create activity for lending a mask temporarily
    
    Args:
        owner_username: Mask owner lending it out
        borrower_username: Citizen borrowing the mask
        mask_resource_id: Mask being lent
        duration_hours: How long the loan lasts
        occasion: Special event for borrowing
        thought: Owner's thoughts on lending
    """
    
    if not thought:
        thought = f"I trust {borrower_username} with my precious mask. May it serve them well!"
    
    activity_data = {
        "type": "lend_carnival_mask",
        "citizen": owner_username,
        "resource_id": mask_resource_id,
        "transport_mode": "walk",
        "status": "created",
        "title": f"Lending Mask to {borrower_username}",
        "description": f"Temporarily lending carnival mask for {occasion or 'the festivities'}",
        "thought": thought,
        "notes": json.dumps({
            "borrower": borrower_username,
            "duration_hours": duration_hours,
            "occasion": occasion,
            "return_by": (datetime.utcnow().timestamp() + (duration_hours * 3600))
        }),
        "priority": 40,  # Medium-low priority
        "start_date": datetime.utcnow().isoformat() + "Z",
        "end_date": None
    }
    
    return activity_data


async def main():
    """Test mask wearing and trading activities"""
    
    # Example 1: Wear a mask
    wear_activity = create_wear_mask_activity(
        "Maria_Danzante",
        "mask_colombina_001",
        occasion="Grand Ball at Palazzo Ducale"
    )
    print("Wear Mask Activity:")
    print(json.dumps(wear_activity, indent=2))
    
    # Example 2: Trade a mask
    trade_activity = create_trade_mask_activity(
        "Giuseppe_Maskmaker",
        "Noble_Contarini",
        "mask_bauta_legendary",
        trade_type="sale",
        price=300,
        location="Rialto Bridge"
    )
    print("\nTrade Mask Activity:")
    print(json.dumps(trade_activity, indent=2))
    
    # Example 3: Showcase a mask
    showcase_activity = create_showcase_mask_activity(
        "Isabella_Performer",
        "mask_arlecchino_001",
        "Piazza San Marco",
        audience_size=150
    )
    print("\nShowcase Mask Activity:")
    print(json.dumps(showcase_activity, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
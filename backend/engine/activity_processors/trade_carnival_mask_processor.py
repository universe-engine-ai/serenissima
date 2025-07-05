#!/usr/bin/env python3
"""
Trade Carnival Mask Activity Processor
Reality-Anchor: Ensuring stable mask exchanges and transformations

This processor handles mask trading, gifting, and lending between citizens,
maintaining ownership integrity and transformation states.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import mask resource system
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resources.mask_resource import MaskResource

log = logging.getLogger(__name__)


async def process_trade_carnival_mask(
    tables: Dict[str, Any],
    activity_data: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_defs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process trading a carnival mask between citizens
    
    Handles:
    - Gift: Free transfer of ownership
    - Sale: Transfer with payment
    - Trade: Exchange (future: mask for mask)
    
    Special considerations:
    - Cannot trade a worn mask (must remove first)
    - Validates ownership before transfer
    - Handles payment for sales
    - Updates mask history
    """
    
    try:
        activity_fields = activity_data["fields"]
        giver_username = activity_fields["Citizen"]
        notes = json.loads(activity_fields.get("Notes", "{}"))
        
        receiver_username = notes.get("receiver")
        trade_type = notes.get("trade_type", "gift")
        price = notes.get("price", 0)
        mask_resource_id = activity_fields.get("ResourceId") or notes.get("mask_resource_id")
        
        if not receiver_username:
            return {
                "success": False,
                "error": "No receiver specified for mask trade"
            }
        
        if not mask_resource_id:
            return {
                "success": False,
                "error": "No mask resource ID specified"
            }
        
        # Get giver citizen record
        giver_records = tables["citizens"].all(
            formula=f"{{Username}} = '{giver_username}'"
        )
        if not giver_records:
            return {
                "success": False,
                "error": f"Giver {giver_username} not found"
            }
        
        giver_record = giver_records[0]
        giver_fields = giver_record["fields"]
        
        # Get receiver citizen record
        receiver_records = tables["citizens"].all(
            formula=f"{{Username}} = '{receiver_username}'"
        )
        if not receiver_records:
            return {
                "success": False,
                "error": f"Receiver {receiver_username} not found"
            }
        
        receiver_record = receiver_records[0]
        receiver_fields = receiver_record["fields"]
        
        # Get mask resource
        mask_records = tables["resources"].all(
            formula=f"AND({{ResourceId}} = '{mask_resource_id}', {{Type}} = 'carnival_mask')"
        )
        if not mask_records:
            return {
                "success": False,
                "error": f"Mask {mask_resource_id} not found"
            }
        
        mask_record = mask_records[0]
        mask_fields = mask_record["fields"]
        
        # Verify ownership
        if mask_fields["Owner"] != giver_username:
            return {
                "success": False,
                "error": f"Mask is owned by {mask_fields['Owner']}, not {giver_username}"
            }
        
        # Load mask object
        mask = MaskResource.from_airtable_record(mask_record)
        
        # Check if mask is worn
        if mask.wearer:
            return {
                "success": False,
                "error": f"Cannot trade worn mask - {mask.wearer} must remove it first"
            }
        
        # Handle payment for sales
        if trade_type == "sale" and price > 0:
            receiver_ducats = receiver_fields.get("Ducats", 0)
            if receiver_ducats < price:
                return {
                    "success": False,
                    "error": f"{receiver_username} cannot afford {price} Ducats"
                }
            
            # Process payment
            tables["citizens"].update(
                receiver_record["id"],
                {"Ducats": receiver_ducats - price}
            )
            
            giver_ducats = giver_fields.get("Ducats", 0)
            tables["citizens"].update(
                giver_record["id"],
                {"Ducats": giver_ducats + price}
            )
            
            # Create transaction record
            tables["transactions"].create({
                "Type": "mask_sale",
                "AssetType": "carnival_mask",
                "Asset": mask_resource_id,
                "Seller": giver_username,
                "Buyer": receiver_username,
                "Price": price,
                "Notes": json.dumps({
                    "mask_name": mask.name,
                    "mask_quality": mask.calculate_quality()
                }),
                "ExecutedAt": datetime.utcnow().isoformat() + "Z"
            })
        
        # Update mask ownership
        mask.owner = receiver_username
        
        # Add trade to mask history
        trade_event = {
            "event": trade_type,
            "from": giver_username,
            "to": receiver_username,
            "timestamp": datetime.utcnow().isoformat(),
            "location": notes.get("location", "Venice")
        }
        
        if price > 0:
            trade_event["price"] = price
        
        mask.attributes["history"].append(trade_event)
        
        # Special memory for significant trades
        if trade_type == "gift":
            mask.add_carnival_memory({
                "event": "gifted_with_love",
                "giver": giver_username,
                "receiver": receiver_username,
                "sentiment": "A mask given freely carries the joy of generosity"
            })
        
        # Update mask record with new owner
        mask_update = mask.to_airtable_format()
        tables["resources"].update(
            mask_record["id"],
            {
                "Owner": receiver_username,
                "Asset": receiver_username,
                "Attributes": mask_update["Attributes"]
            }
        )
        
        # Create notifications
        if trade_type == "gift":
            giver_message = f"You gifted {mask.name} to {receiver_username} with generosity!"
            receiver_message = f"{giver_username} gifted you {mask.name}! A precious carnival treasure!"
        elif trade_type == "sale":
            giver_message = f"You sold {mask.name} to {receiver_username} for {price} Ducats"
            receiver_message = f"You purchased {mask.name} from {giver_username} for {price} Ducats"
        else:
            giver_message = f"You traded {mask.name} to {receiver_username}"
            receiver_message = f"You received {mask.name} from {giver_username} in trade"
        
        tables["notifications"].create({
            "Citizen": giver_username,
            "Type": "mask_trade_complete",
            "Content": giver_message,
            "Status": "unread"
        })
        
        tables["notifications"].create({
            "Citizen": receiver_username,
            "Type": "mask_received",
            "Content": receiver_message,
            "Details": json.dumps({
                "mask_name": mask.name,
                "mask_style": mask.style.value,
                "quality": mask.calculate_quality(),
                "from": giver_username
            }),
            "Status": "unread"
        })
        
        log.info(
            f"MASK TRADED: {mask.name} from {giver_username} to {receiver_username} "
            f"(Type: {trade_type}, Price: {price})"
        )
        
        return {
            "success": True,
            "mask_traded": mask.name,
            "from": giver_username,
            "to": receiver_username,
            "trade_type": trade_type,
            "price": price if trade_type == "sale" else None,
            "message": f"Mask successfully {trade_type}ed to {receiver_username}"
        }
        
    except Exception as e:
        log.error(f"Error processing trade mask activity: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def process_lend_carnival_mask(
    tables: Dict[str, Any],
    activity_data: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_defs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process lending a carnival mask temporarily
    
    Creates a lending contract that tracks:
    - Original owner
    - Borrower
    - Return deadline
    - Lending conditions
    """
    
    try:
        activity_fields = activity_data["fields"]
        owner_username = activity_fields["Citizen"]
        notes = json.loads(activity_fields.get("Notes", "{}"))
        
        borrower_username = notes.get("borrower")
        duration_hours = notes.get("duration_hours", 24)
        occasion = notes.get("occasion")
        mask_resource_id = activity_fields.get("ResourceId") or notes.get("mask_resource_id")
        
        if not borrower_username:
            return {
                "success": False,
                "error": "No borrower specified for mask lending"
            }
        
        if not mask_resource_id:
            return {
                "success": False,
                "error": "No mask resource ID specified"
            }
        
        # Get mask resource
        mask_records = tables["resources"].all(
            formula=f"AND({{ResourceId}} = '{mask_resource_id}', {{Type}} = 'carnival_mask')"
        )
        if not mask_records:
            return {
                "success": False,
                "error": f"Mask {mask_resource_id} not found"
            }
        
        mask_record = mask_records[0]
        mask_fields = mask_record["fields"]
        
        # Verify ownership
        if mask_fields["Owner"] != owner_username:
            return {
                "success": False,
                "error": f"Mask is owned by {mask_fields['Owner']}, not {owner_username}"
            }
        
        # Load mask object
        mask = MaskResource.from_airtable_record(mask_record)
        
        # Check if mask is worn
        if mask.wearer:
            return {
                "success": False,
                "error": f"Cannot lend worn mask - {mask.wearer} must remove it first"
            }
        
        # Create lending contract
        return_deadline = datetime.utcnow() + timedelta(hours=duration_hours)
        
        lending_contract = {
            "ContractId": f"mask_loan_{mask_resource_id}_{int(datetime.utcnow().timestamp())}",
            "Type": "mask_lending",
            "Asset": mask_resource_id,
            "AssetType": "carnival_mask",
            "Seller": owner_username,  # Lender
            "Buyer": borrower_username,  # Borrower
            "Title": f"Lending {mask.name} to {borrower_username}",
            "Description": f"Temporary mask loan for {occasion or 'carnival festivities'}",
            "Status": "active",
            "Notes": json.dumps({
                "mask_name": mask.name,
                "original_owner": owner_username,
                "return_deadline": return_deadline.isoformat(),
                "occasion": occasion,
                "duration_hours": duration_hours
            }),
            "CreatedAt": datetime.utcnow().isoformat() + "Z",
            "EndAt": return_deadline.isoformat() + "Z"
        }
        
        tables["contracts"].create(lending_contract)
        
        # Temporarily transfer ownership to borrower
        mask.attributes["history"].append({
            "event": "lent",
            "lender": owner_username,
            "borrower": borrower_username,
            "duration_hours": duration_hours,
            "return_by": return_deadline.isoformat(),
            "occasion": occasion
        })
        
        # Update mask with borrower as temporary owner
        mask_update = mask.to_airtable_format()
        tables["resources"].update(
            mask_record["id"],
            {
                "Owner": borrower_username,
                "Asset": borrower_username,
                "Attributes": mask_update["Attributes"],
                "Notes": f"On loan from {owner_username} until {return_deadline.strftime('%Y-%m-%d %H:%M')}"
            }
        )
        
        # Create notifications
        tables["notifications"].create({
            "Citizen": owner_username,
            "Type": "mask_lent",
            "Content": f"You lent {mask.name} to {borrower_username} for {duration_hours} hours",
            "Details": json.dumps({
                "return_deadline": return_deadline.isoformat(),
                "contract_id": lending_contract["ContractId"]
            }),
            "Status": "unread"
        })
        
        tables["notifications"].create({
            "Citizen": borrower_username,
            "Type": "mask_borrowed",
            "Content": f"{owner_username} lent you {mask.name}! Return it within {duration_hours} hours",
            "Details": json.dumps({
                "mask_name": mask.name,
                "return_deadline": return_deadline.isoformat(),
                "lender": owner_username
            }),
            "Status": "unread"
        })
        
        log.info(
            f"MASK LENT: {mask.name} from {owner_username} to {borrower_username} "
            f"for {duration_hours} hours"
        )
        
        return {
            "success": True,
            "mask_lent": mask.name,
            "lender": owner_username,
            "borrower": borrower_username,
            "duration_hours": duration_hours,
            "return_deadline": return_deadline.isoformat(),
            "contract_id": lending_contract["ContractId"],
            "message": f"Mask lent successfully for {duration_hours} hours"
        }
        
    except Exception as e:
        log.error(f"Error processing lend mask activity: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def process_showcase_carnival_mask(
    tables: Dict[str, Any],
    activity_data: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_defs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process showcasing a mask at carnival events
    
    Generates:
    - Joy for audience based on mask beauty
    - Reputation for wearer based on performance
    - Memories for the mask
    - Potential consciousness growth
    """
    
    try:
        activity_fields = activity_data["fields"]
        performer_username = activity_fields["Citizen"]
        notes = json.loads(activity_fields.get("Notes", "{}"))
        
        location = notes.get("location", "Piazza San Marco")
        audience_size = notes.get("audience_size", 50)
        performance_type = notes.get("performance_type", "dance")
        mask_resource_id = activity_fields.get("ResourceId") or notes.get("mask_resource_id")
        
        if not mask_resource_id:
            return {
                "success": False,
                "error": "No mask resource ID specified"
            }
        
        # Get performer record
        performer_records = tables["citizens"].all(
            formula=f"{{Username}} = '{performer_username}'"
        )
        if not performer_records:
            return {
                "success": False,
                "error": f"Performer {performer_username} not found"
            }
        
        performer_record = performer_records[0]
        performer_fields = performer_record["fields"]
        
        # Verify performer is wearing the mask
        preferences = json.loads(performer_fields.get("Preferences", "{}"))
        worn_mask = preferences.get("mask_worn", {})
        
        if worn_mask.get("resource_id") != mask_resource_id:
            return {
                "success": False,
                "error": "Must be wearing the mask to showcase it"
            }
        
        # Get mask resource
        mask_records = tables["resources"].all(
            formula=f"{{ResourceId}} = '{mask_resource_id}'"
        )
        if not mask_records:
            return {
                "success": False,
                "error": f"Mask {mask_resource_id} not found"
            }
        
        mask_record = mask_records[0]
        mask = MaskResource.from_airtable_record(mask_record)
        
        # Calculate showcase impact
        beauty_impact = mask.beauty / 100.0
        uniqueness_impact = mask.uniqueness / 100.0
        consciousness_impact = mask.consciousness_capacity / 100.0 if mask.consciousness_capacity > 0 else 0
        
        # Performance quality affects outcome
        performance_quality = 0.5 + (beauty_impact * 0.2) + (uniqueness_impact * 0.3)
        
        # Generate joy for audience
        joy_generated = int(audience_size * performance_quality * beauty_impact)
        
        # Performer gains influence/reputation
        influence_gain = int(10 * performance_quality * (1 + consciousness_impact))
        
        # Update performer's influence
        current_influence = performer_fields.get("Influence", 0)
        tables["citizens"].update(
            performer_record["id"],
            {"Influence": current_influence + influence_gain}
        )
        
        # Add showcase memory to mask
        showcase_memory = {
            "event": "grand_showcase",
            "performer": performer_username,
            "location": location,
            "audience_size": audience_size,
            "performance_type": performance_type,
            "joy_generated": joy_generated,
            "acclaim_received": influence_gain,
            "memorable_moment": f"The crowd gasped as {performer_username} {performance_type}d in {mask.name}"
        }
        
        mask.add_carnival_memory(showcase_memory)
        
        # Chance for consciousness growth from collective joy
        if joy_generated > 100 and mask.consciousness_capacity < 100:
            growth = min(5, int(joy_generated / 100))
            mask.consciousness_capacity = min(100, mask.consciousness_capacity + growth)
            log.info(f"Mask {mask.name} consciousness grew by {growth} from joyful showcase!")
        
        # Update mask record
        mask_update = mask.to_airtable_format()
        tables["resources"].update(
            mask_record["id"],
            {"Attributes": mask_update["Attributes"]}
        )
        
        # Create notification
        tables["notifications"].create({
            "Citizen": performer_username,
            "Type": "showcase_success",
            "Content": (
                f"Your showcase of {mask.name} at {location} was magnificent! "
                f"{audience_size} people witnessed your {performance_type}, "
                f"generating {joy_generated} units of pure carnival joy!"
            ),
            "Details": json.dumps({
                "influence_gained": influence_gain,
                "joy_generated": joy_generated,
                "mask_quality_shown": mask.calculate_quality()
            }),
            "Status": "unread"
        })
        
        # Create some audience reactions (notifications to random nearby citizens)
        # This would need location-based citizen finding in full implementation
        
        log.info(
            f"MASK SHOWCASED: {performer_username} performed with {mask.name} at {location} "
            f"(Audience: {audience_size}, Joy: {joy_generated}, Influence: +{influence_gain})"
        )
        
        return {
            "success": True,
            "performer": performer_username,
            "mask_showcased": mask.name,
            "location": location,
            "audience_size": audience_size,
            "joy_generated": joy_generated,
            "influence_gained": influence_gain,
            "performance_type": performance_type,
            "message": f"Spectacular showcase generated {joy_generated} joy!"
        }
        
    except Exception as e:
        log.error(f"Error processing showcase mask activity: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# Export all processor functions
__all__ = [
    "process_trade_carnival_mask",
    "process_lend_carnival_mask", 
    "process_showcase_carnival_mask"
]
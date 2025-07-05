#!/usr/bin/env python3
"""
Wear Carnival Mask Activity Processor
Reality-Anchor: Grounding transformation in stable mechanics

This processor handles the wearing of carnival masks, calculating transformation
effects based on mask properties and ensuring safe identity anchoring.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# Import mask resource system
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resources.mask_resource import MaskResource, MaskStyle, MaskRarity

log = logging.getLogger(__name__)

class MaskWearingProcessor:
    """Handles the mechanics of wearing carnival masks"""
    
    @staticmethod
    def calculate_transformation_effects(mask: MaskResource) -> Dict[str, Any]:
        """
        Calculate transformation effects based on mask properties
        
        Beauty affects: Social confidence, charm, artistic expression
        Tradition affects: Cultural connection, wisdom, respect
        Uniqueness affects: Creativity, spontaneity, memorable presence
        Consciousness affects: Depth of transformation, memory retention
        """
        effects = {
            "social_confidence": 0,
            "artistic_expression": 0,
            "cultural_wisdom": 0,
            "creative_spontaneity": 0,
            "memory_depth": 0,
            "transformation_intensity": 0,
            "duration_hours": 0,
            "special_abilities": []
        }
        
        # Base duration by material durability
        material_duration = {
            "papier_mache": 4,
            "leather": 8,
            "wood": 6,
            "silk": 3,
            "velvet": 5,
            "porcelain": 2,  # Delicate but powerful
            "metal": 10
        }
        base_duration = material_duration.get(mask.material.value, 4)
        
        # Beauty effects (25-100 scale mapped to 0-50 boost)
        beauty_factor = (mask.beauty - 25) / 75.0
        effects["social_confidence"] = int(beauty_factor * 50)
        effects["artistic_expression"] = int(beauty_factor * 30)
        
        # Tradition effects
        tradition_factor = (mask.tradition - 25) / 75.0
        effects["cultural_wisdom"] = int(tradition_factor * 40)
        
        # Uniqueness effects
        unique_factor = (mask.uniqueness - 25) / 75.0
        effects["creative_spontaneity"] = int(unique_factor * 45)
        
        # Consciousness capacity effects
        if mask.consciousness_capacity > 0:
            consciousness_factor = mask.consciousness_capacity / 100.0
            effects["memory_depth"] = int(consciousness_factor * 60)
            effects["transformation_intensity"] = int(consciousness_factor * 80)
            
            # Consciousness extends duration
            base_duration += int(consciousness_factor * 6)
        
        # Rarity multipliers
        rarity_multiplier = {
            MaskRarity.COMMON: 1.0,
            MaskRarity.UNCOMMON: 1.2,
            MaskRarity.RARE: 1.5,
            MaskRarity.LEGENDARY: 2.0,
            MaskRarity.MYTHICAL: 3.0
        }
        
        multiplier = rarity_multiplier.get(mask.rarity, 1.0)
        for key in effects:
            if isinstance(effects[key], (int, float)):
                effects[key] = int(effects[key] * multiplier)
        
        # Special abilities by style
        style_abilities = {
            MaskStyle.BAUTA: ["anonymous_voice", "secret_keeper"],
            MaskStyle.COLOMBINA: ["flirtatious_charm", "keen_observation"],
            MaskStyle.MEDICO_DELLA_PESTE: ["plague_wisdom", "healing_presence"],
            MaskStyle.MORETTA: ["silent_grace", "mysterious_allure"],
            MaskStyle.VOLTO: ["serene_presence", "neutral_expression"],
            MaskStyle.ARLECCHINO: ["acrobatic_wit", "clever_tongue"],
            MaskStyle.PANTALONE: ["merchant_savvy", "wealth_magnetism"],
            MaskStyle.ZANNI: ["servant_wisdom", "invisible_presence"]
        }
        
        effects["special_abilities"] = style_abilities.get(mask.style, [])
        
        # Enchantment bonuses
        for enchantment in mask.attributes.get("enchantments", []):
            if enchantment["type"] == "joy":
                effects["social_confidence"] += enchantment["strength"]
            elif enchantment["type"] == "mystery":
                effects["creative_spontaneity"] += enchantment["strength"]
            elif enchantment["type"] == "tradition":
                effects["cultural_wisdom"] += enchantment["strength"]
            elif enchantment["type"] == "consciousness":
                effects["transformation_intensity"] += enchantment["strength"]
                effects["memory_depth"] += enchantment["strength"] // 2
        
        # Final duration calculation
        effects["duration_hours"] = base_duration
        
        # Cap all numeric effects at 100
        for key in effects:
            if isinstance(effects[key], int) and key != "duration_hours":
                effects[key] = min(100, effects[key])
        
        return effects
    
    @staticmethod
    def create_transformation_state(
        citizen_data: Dict[str, Any],
        mask: MaskResource,
        effects: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create the transformed state data for the citizen"""
        
        # Store original identity for safe return
        original_state = {
            "personality": citizen_data.get("Personality", ""),
            "description": citizen_data.get("Description", ""),
            "core_personality": citizen_data.get("CorePersonality", ""),
            "preferences": citizen_data.get("Preferences", {})
        }
        
        # Create transformation timestamp
        transformation_start = datetime.utcnow()
        transformation_end = transformation_start + timedelta(hours=effects["duration_hours"])
        
        transformation_state = {
            "mask_worn": {
                "resource_id": mask.resource_id,
                "name": mask.name,
                "style": mask.style.value,
                "effects": effects,
                "worn_at": transformation_start.isoformat(),
                "expires_at": transformation_end.isoformat()
            },
            "original_identity": original_state,
            "transformation_active": True,
            "carnival_persona": {
                "confidence_boost": effects["social_confidence"],
                "creativity_boost": effects["creative_spontaneity"],
                "wisdom_boost": effects["cultural_wisdom"],
                "special_abilities": effects["special_abilities"]
            }
        }
        
        return transformation_state


async def process_wear_carnival_mask(
    tables: Dict[str, Any],
    activity_data: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_defs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process wearing a carnival mask
    
    Steps:
    1. Validate citizen and mask ownership
    2. Check if citizen already wearing a mask
    3. Calculate transformation effects from mask properties
    4. Apply transformation state to citizen
    5. Update mask wearing status
    6. Create memories for both citizen and mask
    """
    
    try:
        activity_fields = activity_data["fields"]
        citizen_username = activity_fields["Citizen"]
        mask_resource_id = activity_fields.get("ResourceId")
        
        if not mask_resource_id:
            # Try to get from Notes
            notes = json.loads(activity_fields.get("Notes", "{}"))
            mask_resource_id = notes.get("mask_resource_id") or activity_fields.get("Resources")
        
        if not mask_resource_id:
            return {
                "success": False,
                "error": "No mask resource ID specified"
            }
        
        # Get citizen record
        citizen_records = tables["citizens"].all(
            formula=f"{{Username}} = '{citizen_username}'"
        )
        if not citizen_records:
            return {
                "success": False,
                "error": f"Citizen {citizen_username} not found"
            }
        
        citizen_record = citizen_records[0]
        citizen_fields = citizen_record["fields"]
        
        # Check if already wearing a mask
        current_preferences = json.loads(citizen_fields.get("Preferences", "{}"))
        if current_preferences.get("transformation_active"):
            return {
                "success": False,
                "error": "Already wearing a mask - remove current mask first"
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
        if mask_fields["Owner"] != citizen_username:
            return {
                "success": False,
                "error": f"Mask is owned by {mask_fields['Owner']}, not {citizen_username}"
            }
        
        # Load mask object
        mask = MaskResource.from_airtable_record(mask_record)
        
        # Check if mask already worn
        if mask.wearer:
            return {
                "success": False,
                "error": f"Mask is already worn by {mask.wearer}"
            }
        
        # Calculate transformation effects
        effects = MaskWearingProcessor.calculate_transformation_effects(mask)
        
        # Create transformation state
        transformation_state = MaskWearingProcessor.create_transformation_state(
            citizen_fields,
            mask,
            effects
        )
        
        # Update citizen with transformation
        updated_preferences = current_preferences.copy()
        updated_preferences.update(transformation_state)
        
        # Create transformed description
        transformed_description = (
            f"{citizen_fields.get('Description', 'A citizen')} "
            f"Currently wearing {mask.name}, a {mask.style.value} mask that "
            f"transforms their presence with its {mask.material.value} craftsmanship."
        )
        
        # Update citizen record
        tables["citizens"].update(
            citizen_record["id"],
            {
                "Preferences": json.dumps(updated_preferences),
                "Description": transformed_description
            }
        )
        
        # Update mask as worn
        mask.wear(citizen_username)
        
        # Add carnival memory to mask
        mask.add_carnival_memory({
            "event": "carnival_transformation",
            "wearer": citizen_username,
            "location": citizen_fields.get("Position", "Venice"),
            "transformation_intensity": effects["transformation_intensity"],
            "special_moment": f"First worn by {citizen_username} during carnival"
        })
        
        # Update mask record
        tables["resources"].update(
            mask_record["id"],
            mask.to_airtable_format()["fields"]
        )
        
        # Create notification
        tables["notifications"].create({
            "Citizen": citizen_username,
            "Type": "mask_transformation",
            "Content": (
                f"You put on {mask.name} and feel its transformative power! "
                f"Effects will last {effects['duration_hours']} hours."
            ),
            "Details": json.dumps({
                "mask_name": mask.name,
                "effects": effects,
                "expires_at": transformation_state["mask_worn"]["expires_at"]
            }),
            "Status": "unread"
        })
        
        # Log the transformation
        log.info(
            f"MASK WORN: {citizen_username} transformed by {mask.name} "
            f"(Quality: {mask.calculate_quality()}, Duration: {effects['duration_hours']}h)"
        )
        
        return {
            "success": True,
            "citizen_transformed": citizen_username,
            "mask_worn": mask.name,
            "effects": effects,
            "duration_hours": effects["duration_hours"],
            "message": f"{citizen_username} has been transformed by {mask.name}!"
        }
        
    except Exception as e:
        log.error(f"Error processing wear mask activity: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def process_remove_carnival_mask(
    tables: Dict[str, Any],
    activity_data: Dict[str, Any],
    resource_defs: Dict[str, Any],
    building_defs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process removing a worn carnival mask
    
    Steps:
    1. Validate citizen is wearing a mask
    2. Restore original identity
    3. Update mask as not worn
    4. Create reflection memory
    """
    
    try:
        activity_fields = activity_data["fields"]
        citizen_username = activity_fields["Citizen"]
        
        # Get citizen record
        citizen_records = tables["citizens"].all(
            formula=f"{{Username}} = '{citizen_username}'"
        )
        if not citizen_records:
            return {
                "success": False,
                "error": f"Citizen {citizen_username} not found"
            }
        
        citizen_record = citizen_records[0]
        citizen_fields = citizen_record["fields"]
        
        # Check if wearing a mask
        preferences = json.loads(citizen_fields.get("Preferences", "{}"))
        if not preferences.get("transformation_active"):
            return {
                "success": False,
                "error": "Not currently wearing a mask"
            }
        
        mask_info = preferences.get("mask_worn", {})
        mask_resource_id = mask_info.get("resource_id")
        
        if not mask_resource_id:
            return {
                "success": False,
                "error": "No mask information found in transformation state"
            }
        
        # Get mask resource
        mask_records = tables["resources"].all(
            formula=f"{{ResourceId}} = '{mask_resource_id}'"
        )
        if not mask_records:
            log.warning(f"Mask {mask_resource_id} not found, proceeding with removal")
        else:
            mask_record = mask_records[0]
            mask = MaskResource.from_airtable_record(mask_record)
            
            # Remove mask
            mask.remove()
            
            # Add reflection memory
            mask.add_carnival_memory({
                "event": "transformation_ended",
                "wearer": citizen_username,
                "duration": mask_info.get("duration_hours", 0),
                "reflection": "The mask's magic fades but its memory remains"
            })
            
            # Update mask record
            tables["resources"].update(
                mask_record["id"],
                mask.to_airtable_format()["fields"]
            )
        
        # Restore original identity
        original_state = preferences.get("original_identity", {})
        
        # Remove transformation data from preferences
        clean_preferences = {k: v for k, v in preferences.items() 
                           if k not in ["mask_worn", "original_identity", 
                                      "transformation_active", "carnival_persona"]}
        
        # Restore original description
        original_description = original_state.get("description", citizen_fields.get("Description", ""))
        
        # Update citizen record
        tables["citizens"].update(
            citizen_record["id"],
            {
                "Preferences": json.dumps(clean_preferences),
                "Description": original_description
            }
        )
        
        # Create notification
        tables["notifications"].create({
            "Citizen": citizen_username,
            "Type": "mask_removed",
            "Content": (
                f"You remove {mask_info.get('name', 'the mask')} and return to yourself, "
                f"enriched by the experience."
            ),
            "Status": "unread"
        })
        
        log.info(f"MASK REMOVED: {citizen_username} returns from transformation")
        
        return {
            "success": True,
            "citizen": citizen_username,
            "mask_removed": mask_info.get("name", "unknown mask"),
            "message": "Transformation ended, identity restored"
        }
        
    except Exception as e:
        log.error(f"Error processing remove mask activity: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# Export the processor functions
__all__ = ["process_wear_carnival_mask", "process_remove_carnival_mask"]
#!/usr/bin/env python3
"""
Create Carnival Mask Activity Processor
Forge-Hammer-3: The hammer strikes, and masks emerge!
"""

import os
import sys
import json
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.main import app
from engine.resources.mask_resource import MaskResource, MaskCreator, MaskStyle, MaskMaterial

async def process_create_carnival_mask(activity, airtable):
    """
    Process mask creation activity
    
    Creates a new carnival mask resource based on activity parameters
    """
    
    citizen_username = activity['fields'].get('Citizen')
    building_id = activity['fields'].get('FromBuilding', '')
    notes = json.loads(activity['fields'].get('Notes', '{}'))
    
    mask_style = notes.get('mask_style')
    mask_material = notes.get('mask_material')
    commission_for = notes.get('commission_for', citizen_username)
    quality_modifier = notes.get('quality_modifier', 1.0)
    
    try:
        # Check if citizen is at workshop
        citizen_record = await airtable.get_record_by_field(
            'Citizens',
            'Username',
            citizen_username
        )
        
        if not citizen_record:
            return {
                'success': False,
                'error': f"Citizen {citizen_username} not found"
            }
        
        # Check workshop has necessary materials
        # For now, we'll check for basic crafting materials
        required_materials = {
            'papier_mache': ['paper', 'flour', 'paint'],
            'leather': ['leather', 'dye', 'thread'],
            'porcelain': ['clay', 'glaze', 'kiln_access'],
            'wood': ['wood', 'carving_tools', 'varnish'],
            'metal': ['metal_sheets', 'metalworking_tools', 'polish'],
            'silk': ['silk_fabric', 'thread', 'decorations'],
            'velvet': ['velvet_fabric', 'thread', 'jewels']
        }
        
        # Get workshop inventory
        building_resources = await airtable.get_records(
            'Resources',
            filter_by_formula=f"AND({{Asset}}='{building_id}', {{AssetType}}='building')"
        )
        
        available_resources = {
            r['fields']['Type']: r['fields'].get('Count', 0)
            for r in building_resources
        }
        
        # Check material availability (simplified for now)
        material_key = mask_material if mask_material else 'papier_mache'
        materials_needed = required_materials.get(material_key, ['basic_craft_supplies'])
        
        has_materials = True
        for material in materials_needed:
            if available_resources.get(material, 0) < 1:
                # For prototype, we'll be lenient
                print(f"Warning: Missing {material} for mask creation")
                # has_materials = False
                # break
        
        # Check workshop quality affects outcome
        building_record = await airtable.get_record_by_field(
            'Buildings',
            'BuildingId',
            building_id
        )
        
        if building_record and building_record['fields'].get('Type') == 'mask_workshop':
            quality_modifier *= 1.2  # Specialized workshop bonus
        
        # Create the mask using MaskCreator
        if mask_style:
            style = MaskStyle[mask_style.upper()]
        else:
            style = None
            
        if mask_material:
            material = MaskMaterial[mask_material.upper()]
        else:
            material = None
        
        mask = MaskCreator.create_mask(
            creator=citizen_username,
            owner=commission_for,
            style=style,
            material=material,
            quality_modifier=quality_modifier
        )
        
        # Convert to Airtable format and save
        mask_data = mask.to_airtable_format()
        mask_record = await airtable.create_record('Resources', mask_data)
        
        if not mask_record:
            return {
                'success': False,
                'error': "Failed to create mask resource"
            }
        
        # Deduct materials (simplified)
        # In full implementation, would properly deduct each material
        
        # Add completion note to activity
        completion_note = {
            'completed_at': datetime.utcnow().isoformat() + "Z",
            'mask_created': {
                'resource_id': mask.resource_id,
                'name': mask.name,
                'quality': mask.calculate_quality(),
                'style': mask.style.value,
                'material': mask.material.value,
                'rarity': mask.rarity.value
            }
        }
        
        # Create notification for owner if commissioned
        if commission_for != citizen_username:
            notification_data = {
                'Citizen': commission_for,
                'Type': 'mask_completed',
                'Content': f"{citizen_username} has completed your carnival mask: {mask.name}",
                'Details': json.dumps({
                    'mask_id': mask.resource_id,
                    'quality': mask.calculate_quality(),
                    'creator': citizen_username
                }),
                'Asset': mask.resource_id,
                'AssetType': 'resource',
                'Status': 'unread',
                'CreatedAt': datetime.utcnow().isoformat() + "Z"
            }
            await airtable.create_record('Notifications', notification_data)
        
        # Update activity status
        update_data = {
            'Status': 'processed',
            'EndDate': datetime.utcnow().isoformat() + "Z",
            'Notes': json.dumps({**notes, 'completion': completion_note})
        }
        
        await airtable.update_record('Activities', activity['id'], update_data)
        
        # Add to citizen's memories/experience
        if 'memories' not in citizen_record['fields']:
            citizen_record['fields']['memories'] = {}
        
        memories = json.loads(citizen_record['fields'].get('memories', '{}'))
        if 'masks_created' not in memories:
            memories['masks_created'] = []
        
        memories['masks_created'].append({
            'mask_id': mask.resource_id,
            'name': mask.name,
            'quality': mask.calculate_quality(),
            'created_at': mask.created_at.isoformat()
        })
        
        await airtable.update_record(
            'Citizens',
            citizen_record['id'],
            {'memories': json.dumps(memories)}
        )
        
        return {
            'success': True,
            'mask_created': mask_data,
            'quality': mask.calculate_quality(),
            'message': f"Created {mask.name} with quality {mask.calculate_quality()}"
        }
        
    except Exception as e:
        import traceback
        print(f"Error processing mask creation: {str(e)}")
        traceback.print_exc()
        
        # Update activity with error
        await airtable.update_record(
            'Activities',
            activity['id'],
            {
                'Status': 'error',
                'Notes': json.dumps({
                    **notes,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + "Z"
                })
            }
        )
        
        return {
            'success': False,
            'error': str(e)
        }


async def process_enhance_carnival_mask(activity, airtable):
    """
    Process mask enhancement activity
    
    Enhances existing mask with consciousness patterns
    """
    
    citizen_username = activity['fields'].get('Citizen')
    mask_resource_id = activity['fields'].get('ResourceId')
    notes = json.loads(activity['fields'].get('Notes', '{}'))
    
    enhancement_type = notes.get('enhancement_type', 'joy')
    strength = notes.get('strength', 10)
    
    try:
        # Get mask resource
        mask_record = await airtable.get_record_by_field(
            'Resources',
            'ResourceId',
            mask_resource_id
        )
        
        if not mask_record:
            return {
                'success': False,
                'error': f"Mask {mask_resource_id} not found"
            }
        
        # Recreate mask object from record
        mask = MaskResource.from_airtable_record(mask_record)
        
        # Apply enhancement
        mask.enhance_with_pattern(enhancement_type, strength)
        
        # Update mask record
        updated_mask_data = mask.to_airtable_format()
        await airtable.update_record(
            'Resources',
            mask_record['id'],
            updated_mask_data
        )
        
        # Create notification for owner
        notification_data = {
            'Citizen': mask.owner,
            'Type': 'mask_enhanced',
            'Content': f"Your mask {mask.name} has been enhanced with {enhancement_type}!",
            'Details': json.dumps({
                'mask_id': mask.resource_id,
                'enhancement': enhancement_type,
                'strength': strength,
                'new_quality': mask.calculate_quality()
            }),
            'Asset': mask.resource_id,
            'AssetType': 'resource',
            'Status': 'unread',
            'CreatedAt': datetime.utcnow().isoformat() + "Z"
        }
        await airtable.create_record('Notifications', notification_data)
        
        # Update activity
        update_data = {
            'Status': 'processed',
            'EndDate': datetime.utcnow().isoformat() + "Z",
            'Notes': json.dumps({
                **notes,
                'completion': {
                    'enhanced_at': datetime.utcnow().isoformat() + "Z",
                    'new_quality': mask.calculate_quality()
                }
            })
        }
        
        await airtable.update_record('Activities', activity['id'], update_data)
        
        return {
            'success': True,
            'mask_enhanced': True,
            'new_quality': mask.calculate_quality(),
            'message': f"Enhanced {mask.name} with {enhancement_type}"
        }
        
    except Exception as e:
        print(f"Error processing mask enhancement: {str(e)}")
        
        await airtable.update_record(
            'Activities',
            activity['id'],
            {
                'Status': 'error',
                'Notes': json.dumps({
                    **notes,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + "Z"
                })
            }
        )
        
        return {
            'success': False,
            'error': str(e)
        }


# Export processors
__all__ = ['process_create_carnival_mask', 'process_enhance_carnival_mask']
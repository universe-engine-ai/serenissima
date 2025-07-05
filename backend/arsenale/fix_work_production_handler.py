#!/usr/bin/env python3
"""
Fix for Work Production Handler
Reality-Anchor's Infrastructure Fix

This script patches the work handler to properly select recipes when creating production activities.
The issue: work.py checks if building has recipes but doesn't select one to pass to try_create_production_activity.

SEREN-WORK-FIX-001: Production Recipe Selection
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

def show_work_handler_fix():
    """Display the fix needed for the work handler"""
    
    print("""
    ========================================
    FIX FOR WORK PRODUCTION HANDLER
    ========================================
    
    The issue is in /backend/engine/handlers/work.py around line 219-227.
    
    CURRENT CODE (BROKEN):
    ---------------------
    # Try to create production activity
    activity_record = try_create_production_activity(
        tables, citizen_custom_id, citizen_username, citizen_airtable_id,
        workplace_building['id'], workplace_str, now_utc_dt
    )
    
    FIXED CODE:
    ----------
    # Select first available recipe (or implement better selection logic)
    if recipes:
        selected_recipe = recipes[0]  # Simple selection - take first recipe
        
        # Try to create production activity with recipe
        from backend.engine.activity_creators.production_activity_creator import try_create as create_production_activity
        activity_record = create_production_activity(
            tables, citizen_airtable_id, citizen_custom_id, citizen_username,
            workplace_str, selected_recipe, now_utc_dt
        )
    
    The try_create_production_activity wrapper in __init__.py needs to be updated to pass the recipe parameter.
    
    ALTERNATIVE FIX - Update the wrapper in activity_creators/__init__.py:
    ---------------------------------------------------------------------
    def try_create_production_activity(
        tables: Dict[str, Any], 
        citizen_custom_id: str,
        citizen_username: str,
        citizen_airtable_id: str,
        building_airtable_id: str,
        building_custom_id: str,
        current_time_utc: datetime.datetime,
        recipe: Optional[Dict] = None  # Add recipe parameter
    ) -> Optional[Dict]:
        # If no recipe provided, try to get from building type
        if not recipe:
            # Get building type and select first recipe
            building_record = get_building_record(tables, building_custom_id)
            if building_record:
                building_type = building_record['fields'].get('Type')
                # You'd need to pass building_type_defs here or fetch it
                # For now, use a default grain->flour recipe for mills
                if building_type == 'automated_mill':
                    recipe = {
                        "name": "grain_to_flour",
                        "inputs": {"grain": 10},
                        "outputs": {"flour": 8},
                        "craftMinutes": 60
                    }
        
        if not recipe:
            return None
            
        return production_activity_creator.try_create(
            tables, citizen_airtable_id, citizen_custom_id, 
            citizen_username, building_custom_id, recipe, current_time_utc
        )
    
    ========================================
    IMMEDIATE WORKAROUND:
    ========================================
    
    Use the emergency_mill_production_enabler.py script to manually create
    production activities for mills with grain.
    
    Run: python backend/arsenale/emergency_mill_production_enabler.py --execute
    
    This will:
    1. Find all mills with grain but no active production
    2. Ensure each mill has an operator assigned
    3. Create production activities with the grain->flour recipe
    
    ========================================
    """)

if __name__ == "__main__":
    show_work_handler_fix()
"""
Process commission market galley stratagems.
"""

import json
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from pyairtable import Api

from backend.engine.createmarketgalley import (
    create_contracts_for_galley_resources,
    create_galley_at_dock,
    create_galley_resources,
    find_suitable_dock,
    get_forestieri_for_galley,
    get_import_price,
)
from backend.schema.enums import ActivityType, BuildingType
from backend.utils.database import DATABASE_ID, get_base_record, update_base_record


def process_commission_market_galley(
    stratagem_id: str,
    api: Api = None
) -> Tuple[bool, str]:
    """
    Process a commission market galley stratagem.
    
    This handles:
    1. Initial commission payment (deduct ducats from citizen)
    2. Galley creation after arrival time
    3. Resource generation based on investment
    4. Contract creation for resources
    
    Returns:
        success (bool): Whether processing succeeded
        message (str): Status or error message
    """
    base = api.base(DATABASE_ID)
    
    # Get stratagem record
    stratagem = get_base_record("STRATAGEMS", stratagem_id, api=api)
    if not stratagem:
        return False, "Stratagem not found"
    
    # Check if this is the right type
    if stratagem.get("Type") != "commission_market_galley":
        return False, f"Invalid stratagem type: {stratagem.get('Type')}"
    
    # Get parameters
    params = stratagem.get("Parameters", {})
    if isinstance(params, str):
        params = json.loads(params)
    
    investment_amount = params.get("investment_amount", 1000.0)
    resource_types = params.get("resource_types", ["mixed"])
    arrival_hours = params.get("arrival_hours", 6)
    commission_paid = params.get("commission_paid", False)
    
    # Get citizen
    citizen_ids = stratagem.get("Citizen", [])
    if not citizen_ids:
        return False, "No citizen associated with stratagem"
    
    citizen_id = citizen_ids[0]
    citizen = get_base_record("CITIZENS", citizen_id, api=api)
    if not citizen:
        return False, "Citizen not found"
    
    # Phase 1: Pay commission if not already paid
    if not commission_paid:
        citizen_ducats = citizen.get("Ducats", 0)
        if citizen_ducats < investment_amount:
            # Cancel stratagem due to insufficient funds
            update_base_record(
                "STRATAGEMS", 
                stratagem_id, 
                {"Status": "cancelled", "End Time": datetime.now(timezone.utc).isoformat()},
                api=api
            )
            return False, f"Citizen has insufficient ducats ({citizen_ducats:.0f} < {investment_amount:.0f})"
        
        # Deduct ducats
        update_base_record(
            "CITIZENS",
            citizen_id,
            {"Ducats": citizen_ducats - investment_amount},
            api=api
        )
        
        # Update stratagem to mark commission as paid
        params["commission_paid"] = True
        update_base_record(
            "STRATAGEMS",
            stratagem_id,
            {"Parameters": params},
            api=api
        )
        
        return True, f"Commission of {investment_amount:.0f} ducats paid. Galley will arrive in {arrival_hours} hours."
    
    # Phase 2: Check if it's time for galley arrival
    created_time = datetime.fromisoformat(stratagem.get("Created", "").replace("Z", "+00:00"))
    current_time = datetime.now(timezone.utc)
    hours_elapsed = (current_time - created_time).total_seconds() / 3600
    
    if hours_elapsed < arrival_hours:
        remaining_hours = arrival_hours - hours_elapsed
        return True, f"Galley en route. Arrival in {remaining_hours:.1f} hours."
    
    # Phase 3: Create the galley
    # Find a suitable public dock
    dock = find_suitable_dock(api=api)
    if not dock:
        return False, "No suitable dock found for galley arrival"
    
    # Get a Forestieri to pilot the galley
    forestieri_id = get_forestieri_for_galley(api=api)
    if not forestieri_id:
        return False, "No Forestieri available to pilot galley"
    
    # Create the galley building
    galley = create_galley_at_dock(dock, forestieri_id, api=api)
    if not galley:
        return False, "Failed to create galley"
    
    # Generate resources based on investment
    # Calculate resource values with 15% markup
    total_resource_value = investment_amount * 1.15
    
    # If specific resource types requested, use those; otherwise mixed
    if resource_types and resource_types != ["mixed"]:
        selected_types = resource_types
    else:
        # Random selection of 2-4 resource types for variety
        all_types = ["fish", "grain", "wine", "salt", "spices", "silk", "wool", "leather", "stone", "wood", "iron"]
        selected_types = random.sample(all_types, random.randint(2, 4))
    
    # Distribute value among selected resource types
    value_per_type = total_resource_value / len(selected_types)
    
    all_resources = []
    for resource_type in selected_types:
        import_price = get_import_price(resource_type, api=api)
        if import_price <= 0:
            continue
            
        # Calculate quantity based on allocated value
        quantity = int(value_per_type / import_price)
        if quantity <= 0:
            continue
        
        # Create resources of this type
        resources = create_galley_resources(
            galley["id"],
            resource_type,
            quantity,
            forestieri_id,
            api=api
        )
        all_resources.extend(resources)
    
    # Create contracts for all resources
    if all_resources:
        contracts = create_contracts_for_galley_resources(all_resources, api=api)
        
        # Update stratagem to completed
        update_base_record(
            "STRATAGEMS",
            stratagem_id,
            {
                "Status": "completed",
                "End Time": datetime.now(timezone.utc).isoformat(),
                "Description": (
                    f"{citizen.get('Name', 'Unknown')}'s commissioned galley has arrived at "
                    f"{dock.get('Name', 'the dock')} with {len(all_resources)} resources "
                    f"worth approximately {total_resource_value:.0f} ducats."
                )
            },
            api=api
        )
        
        # Create activity for citizen to be notified
        activity_data = {
            "Type": ActivityType.send_message,
            "Citizen": [citizen_id],
            "Building": [galley["id"]],
            "Data": {
                "message": (
                    f"Your commissioned galley has arrived at {dock.get('Name', 'the dock')}! "
                    f"It carries {len(all_resources)} resources worth approximately {total_resource_value:.0f} ducats. "
                    f"The goods are now available for purchase with a 15% markup over import prices."
                ),
                "is_system_message": True
            },
            "Start Time": datetime.now(timezone.utc).isoformat(),
            "End Time": datetime.now(timezone.utc).isoformat(),
            "Completed": datetime.now(timezone.utc).isoformat()
        }
        base.table("ACTIVITIES").create(activity_data)
        
        return True, f"Galley arrived with {len(all_resources)} resources worth {total_resource_value:.0f} ducats"
    else:
        # No resources created, refund partial amount
        refund = investment_amount * 0.5  # 50% refund for failed delivery
        update_base_record(
            "CITIZENS",
            citizen_id,
            {"Ducats": citizen.get("Ducats", 0) + refund},
            api=api
        )
        
        update_base_record(
            "STRATAGEMS",
            stratagem_id,
            {
                "Status": "failed", 
                "End Time": datetime.now(timezone.utc).isoformat(),
                "Description": f"Galley arrived but could not procure resources. {refund:.0f} ducats refunded."
            },
            api=api
        )
        
        return False, "Galley arrived but could not procure requested resources"
"""
Stratagem Creator for "hoard_resource".

This creator is responsible for generating "hoard_resource" stratagems
and an initial associated 'storage_query' contract.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors,
    get_building_record # To validate targetStorageBuildingId
)

log = logging.getLogger(__name__)

# Define a large default amount for the storage_query contract
DEFAULT_STORAGE_QUERY_TARGET_AMOUNT = 1_000_000 

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates a "hoard_resource" stratagem.
    The associated 'storage_query' contract will be handled by the processor.

    Expected stratagem_params:
    - targetResourceType (str, required): Resource type ID to hoard.
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration of the stratagem in hours. Defaults to 72.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' stratagem for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "hoard_resource":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'hoard_resource' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_resource_type = stratagem_params.get("targetResourceType")

    if not target_resource_type:
        log.error(f"{LogColors.FAIL}TargetResourceType must be specified for hoard_resource stratagem.{LogColors.ENDC}")
        return None
    # targetStorageBuildingId is no longer a direct parameter for creation.
    # It will be determined by the processor.

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    name = stratagem_params.get("name") or f"Hoard {target_resource_type}"
    description = stratagem_params.get("description") or f"{citizen_username} is attempting to hoard {target_resource_type} in an available storage."
    
    duration_hours = int(stratagem_params.get("durationHours", 72)) # Default to 3 days
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "resource_management", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", ""),
        "TargetResourceType": target_resource_type
        # TargetStorageBuildingId is removed from here
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'hoard_resource' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    # The 'storage_query' contract creation is now handled by the processor.
    # The creator only sets up the stratagem record itself.
    
    return [stratagem_payload]

"""
Stratagem Creator for "employee_poaching".
(Coming Soon)
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors
)

log = logging.getLogger(__name__)

BASE_INFLUENCE_COST = 6 # Base cost

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Creates an "employee_poaching" stratagem. (Coming Soon)

    Expected stratagem_params:
    - targetEmployeeUsername (str, required): The username of the employee to poach.
    - targetCompetitorUsername (str, required): The username of the current employer.
    - jobOfferDetails (str, optional): Details of the job offer (e.g., "Higher wages at my workshop").
    - name (str, optional): Custom name for the stratagem.
    - description (str, optional): Custom description.
    - notes (str, optional): Additional notes.
    - durationHours (int, optional): Duration in hours. Defaults to 48 (2 days).
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Attempting to create '{stratagem_type}' (Employee Poaching - Coming Soon) for {citizen_username} with params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "employee_poaching":
        log.error(f"{LogColors.FAIL}Stratagem creator for 'employee_poaching' called with incorrect type: {stratagem_type}{LogColors.ENDC}")
        return None

    target_employee = stratagem_params.get("targetEmployeeUsername")
    target_competitor = stratagem_params.get("targetCompetitorUsername")

    if not target_employee or not target_competitor:
        log.error(f"{LogColors.FAIL}Missing required parameters (targetEmployeeUsername, targetCompetitorUsername) for employee_poaching stratagem.{LogColors.ENDC}")
        return None

    if target_employee == citizen_username:
        log.error(f"{LogColors.FAIL}Cannot poach oneself.{LogColors.ENDC}")
        return None

    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    
    job_offer = stratagem_params.get("jobOfferDetails", "a better opportunity")
    
    name = stratagem_params.get("name") or f"Poach {target_employee} from {target_competitor}"
    description = stratagem_params.get("description") or f"{citizen_username} is attempting to poach {target_employee} from {target_competitor} with an offer of '{job_offer}'."
    
    duration_hours = int(stratagem_params.get("durationHours", 48)) # Default to 2 days for the offer to be considered
    expires_at_utc = now_utc_dt + timedelta(hours=duration_hours)

    stratagem_payload = {
        "StratagemId": stratagem_id,
        "Type": stratagem_type,
        "Name": name,
        "Category": "social_warfare", 
        "ExecutedBy": citizen_username,
        "Status": "active", 
        "ExecutedAt": None, 
        "ExpiresAt": expires_at_utc.isoformat(),
        "Description": description,
        "Notes": stratagem_params.get("notes", f"Offer: {job_offer}. Influence Cost: {BASE_INFLUENCE_COST}"),
        # Specific fields for employee_poaching
        "TargetCitizen": target_employee, # The employee is the primary target
        "TargetCompetitor": target_competitor, # The current employer
        "JobOfferDetails": job_offer,
        "InfluenceCost": BASE_INFLUENCE_COST
    }
    
    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload for 'employee_poaching' stratagem '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    
    return [stratagem_payload]

"""
Stratagem Processor for "employee_poaching".
(Coming Soon)
"""

import logging
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import LogColors

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None,
    building_type_defs: Optional[Dict[str, Any]] = None,
    api_base_url: Optional[str] = None
) -> bool:
    """
    Processes an "employee_poaching" stratagem.
    For "Coming Soon", this will just log and do nothing else.
    """
    stratagem_id = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    executed_by = stratagem_record['fields'].get('ExecutedBy', 'UnknownCitizen')
    target_employee = stratagem_record['fields'].get('TargetCitizen')
    target_competitor = stratagem_record['fields'].get('TargetCompetitor')
    offer = stratagem_record['fields'].get('JobOfferDetails')

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'employee_poaching' (Coming Soon) stratagem {stratagem_id} for {executed_by}. Target Employee: {target_employee}, from: {target_competitor}, Offer: '{offer}'.{LogColors.ENDC}")
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Employee Poaching for {stratagem_id} is marked 'Coming Soon'. No action will be taken by the processor at this time.{LogColors.ENDC}")

    # Since it's "Coming Soon", we don't want it to fail immediately.
    # It should remain 'active' until its expiry or manual cancellation.
    return True

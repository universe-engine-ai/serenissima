"""
Stratagem Processor for "maritime_blockade".
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
    Processes a "maritime_blockade" stratagem.
    For "Coming Soon", this will just log and do nothing else.
    """
    stratagem_id = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    executed_by = stratagem_record['fields'].get('ExecutedBy', 'UnknownCitizen')
    target_building = stratagem_record['fields'].get('TargetBuilding')
    target_citizen = stratagem_record['fields'].get('TargetCitizen')

    target_display_parts = []
    if target_building:
        target_display_parts.append(f"building: {target_building}")
    if target_citizen:
        target_display_parts.append(f"citizen: {target_citizen}")
    target_display = "; ".join(target_display_parts) or "unspecified target"


    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'maritime_blockade' (Coming Soon) stratagem {stratagem_id} for {executed_by}. Targets: {target_display}.{LogColors.ENDC}")
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Maritime Blockade for {stratagem_id} is marked 'Coming Soon'. No action will be taken by the processor at this time.{LogColors.ENDC}")

    # Since it's "Coming Soon", we don't want it to fail immediately.
    # It should remain 'active' until its expiry or manual cancellation.
    return True

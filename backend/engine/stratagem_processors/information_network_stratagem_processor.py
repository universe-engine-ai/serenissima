"""
Stratagem Processor for "information_network".
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
    Processes an "information_network" stratagem.
    For "Coming Soon", this will just log and do nothing else.
    """
    stratagem_id = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    executed_by = stratagem_record['fields'].get('ExecutedBy', 'UnknownCitizen')
    target_citizens_str = stratagem_record['fields'].get('TargetCitizens', '[]')
    target_sectors_str = stratagem_record['fields'].get('TargetSectors', '[]')

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'information_network' (Coming Soon) stratagem {stratagem_id} for {executed_by}. Targets: Citizens: {target_citizens_str}, Sectors: {target_sectors_str}.{LogColors.ENDC}")
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Information Network for {stratagem_id} is marked 'Coming Soon'. No action will be taken by the processor at this time.{LogColors.ENDC}")

    # Since it's "Coming Soon", we don't want it to fail immediately.
    # It should remain 'active' until its expiry or manual cancellation.
    return True

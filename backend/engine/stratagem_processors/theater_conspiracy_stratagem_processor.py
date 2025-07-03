"""
Stratagem Processor for "theater_conspiracy".
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
    Processes a "theater_conspiracy" stratagem.
    For "Coming Soon", this will just log and do nothing else.
    """
    stratagem_id = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    executed_by = stratagem_record['fields'].get('ExecutedBy', 'UnknownCitizen')
    target_theater = stratagem_record['fields'].get('TargetBuilding')
    theme = stratagem_record['fields'].get('PoliticalTheme')

    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Processing 'theater_conspiracy' (Coming Soon) stratagem {stratagem_id} for {executed_by}. Target Theater: {target_theater}, Theme: {theme}.{LogColors.ENDC}")
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Theater Conspiracy for {stratagem_id} is marked 'Coming Soon'. No action will be taken by the processor at this time.{LogColors.ENDC}")

    # Since it's "Coming Soon", we don't want it to fail immediately.
    # It should remain 'active' until its expiry or manual cancellation.
    return True

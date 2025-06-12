import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone # Ajout pour ExecutedAt

from backend.engine.utils.activity_helpers import LogColors

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None, # Non utilisé directement
    building_type_defs: Optional[Dict[str, Any]] = None, # Non utilisé directement
    api_base_url: Optional[str] = None # Non utilisé directement
) -> bool:
    """
    Traite un stratagème "marketplace_gossip".
    Le créateur de stratagème a déjà configuré les activités `goto_location` et `spread_rumor`.
    Ce processeur marque simplement le stratagème comme exécuté.
    """
    stratagem_id_custom = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    stratagem_airtable_id = stratagem_record['id']
    executed_by = stratagem_record['fields'].get('ExecutedBy', 'UnknownCitizen')
    target_citizen = stratagem_record['fields'].get('TargetCitizen') # Cible principale du stratagème
    
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Traitement du stratagème 'marketplace_gossip' {stratagem_id_custom} par {executed_by} contre {target_citizen}.{LogColors.ENDC}")

    # Les activités de propagation de rumeurs sont créées par le stratagem_creator.
    # Ce processeur n'a plus besoin de les créer.
    # Il s'assure juste que le stratagème est marqué comme exécuté.
    
    current_notes = stratagem_record['fields'].get('Notes', "")
    updated_notes = f"{current_notes}\n[Processor] Stratagem processed. Activities for rumor spreading should have been created by the stratagem creator."
    
    update_payload = {
        'Status': 'executed',
        'Notes': updated_notes.strip()
    }
    
    # Mettre à jour ExecutedAt si ce n'est pas déjà fait
    if not stratagem_record['fields'].get('ExecutedAt'):
        update_payload['ExecutedAt'] = datetime.now(timezone.utc).isoformat()

    try:
        tables['stratagems'].update(stratagem_airtable_id, update_payload)
        log.info(f"{LogColors.OKGREEN}Stratagème 'marketplace_gossip' {stratagem_id_custom} marqué comme 'executed'.{LogColors.ENDC}")
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Échec de la mise à jour du statut du stratagème {stratagem_id_custom}: {e}{LogColors.ENDC}")
        return False

"""
Processor for 'deliver_resource_to_buyer' activities.
Handles a citizen delivering resources (previously picked up, e.g., from a galley)
to the ultimate buyer's specified destination building.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from backend.engine.utils.activity_helpers import (
    get_citizen_record,
    get_building_record,
    _escape_airtable_value,
    LogColors,
    VENICE_TIMEZONE,
    update_resource_count # Import the helper
)
from backend.engine.utils.relationship_helpers import update_trust_score_for_activity, TRUST_SCORE_SUCCESS_SIMPLE, TRUST_SCORE_FAILURE_SIMPLE


log = logging.getLogger(__name__)

def _fail_activity_with_note(
    tables: Dict[str, Any], 
    activity_airtable_id: str, 
    activity_guid: str, 
    original_notes: str, 
    reason_message: str
) -> bool:
    error_note = f"ÉCHEC: {reason_message}"
    updated_notes = f"{original_notes}\n{error_note}" if original_notes else error_note
    log.error(f"Activité {activity_guid} échouée: {reason_message}")
    try:
        tables['activities'].update(activity_airtable_id, {'Notes': updated_notes})
    except Exception as e_update_notes:
        log.error(f"Erreur MAJ notes pour activité échouée {activity_guid}: {e_update_notes}")
    return False

def process(
    tables: Dict[str, Any], 
    activity_record: Dict[str, Any], 
    building_type_defs: Dict, 
    resource_defs: Dict,
    api_base_url: Optional[str] = None # Added for signature consistency
) -> bool:
    activity_id_airtable = activity_record['id']
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_id_airtable)
    log.info(f"Processing 'deliver_resource_to_buyer' activity: {activity_guid}")

    carrier_username = activity_fields.get('Citizen')
    destination_building_custom_id = activity_fields.get('ToBuilding') # Destination
    original_contract_custom_id = activity_fields.get('ContractId') # Original import contract

    resources_json_str = activity_fields.get('Resources')
    resources_to_deliver: List[Dict[str, Any]] = []
    if resources_json_str:
        try:
            resources_to_deliver = json.loads(resources_json_str)
            if not isinstance(resources_to_deliver, list) or not resources_to_deliver:
                raise ValueError("Resources JSON n'est pas une liste valide ou est vide.")
        except (json.JSONDecodeError, ValueError) as e:
            reason = f"JSON invalide ou vide dans le champ Resources: {resources_json_str}. Erreur: {e}"
            return _fail_activity_with_note(tables, activity_id_airtable, activity_guid, activity_fields.get('Notes', ''), reason)

    if not all([carrier_username, destination_building_custom_id, original_contract_custom_id, resources_to_deliver]):
        reason = "Données cruciales manquantes (Citizen, ToBuilding, ContractId, ou Resources)."
        return _fail_activity_with_note(tables, activity_id_airtable, activity_guid, activity_fields.get('Notes', ''), reason)

    carrier_citizen_record = get_citizen_record(tables, carrier_username)
    if not carrier_citizen_record:
        reason = f"Citoyen transporteur {carrier_username} non trouvé."
        return _fail_activity_with_note(tables, activity_id_airtable, activity_guid, activity_fields.get('Notes', ''), reason)

    destination_building_record = get_building_record(tables, destination_building_custom_id)
    if not destination_building_record:
        reason = f"Bâtiment de destination {destination_building_custom_id} non trouvé."
        return _fail_activity_with_note(tables, activity_id_airtable, activity_guid, activity_fields.get('Notes', ''), reason)
    
    destination_building_pos_str = destination_building_record['fields'].get('Position', '{}')

    original_contract_record = tables['contracts'].all(formula=f"{{ContractId}}='{_escape_airtable_value(original_contract_custom_id)}'", max_records=1)
    if not original_contract_record:
        reason = f"Contrat original {original_contract_custom_id} non trouvé."
        return _fail_activity_with_note(tables, activity_id_airtable, activity_guid, activity_fields.get('Notes', ''), reason)
    
    ultimate_buyer_username = original_contract_record[0]['fields'].get('Buyer')
    if not ultimate_buyer_username:
        reason = f"Contrat original {original_contract_custom_id} manque l'Acheteur (Buyer)."
        return _fail_activity_with_note(tables, activity_id_airtable, activity_guid, activity_fields.get('Notes', ''), reason)

    now_iso = datetime.now(VENICE_TIMEZONE).isoformat()
    all_deliveries_successful = True

    for item in resources_to_deliver:
        resource_id = item.get('ResourceId')
        amount_to_deliver = float(item.get('Amount', 0))

        if not resource_id or amount_to_deliver <= 0:
            log.warning(f"Item invalide dans Resources pour livraison: {item}")
            all_deliveries_successful = False
            continue

        # 1. Remove from carrier's inventory (owned by ultimate_buyer_username)
        carrier_removed = update_resource_count(
            tables, carrier_username, 'citizen', ultimate_buyer_username,
            resource_id, -amount_to_deliver, resource_defs, now_iso,
            notes=f"Livré à {destination_building_custom_id} pour contrat {original_contract_custom_id}"
        )
        if not carrier_removed:
            log.error(f"Échec du retrait de {amount_to_deliver} de {resource_id} de l'inventaire de {carrier_username} (pour {ultimate_buyer_username}).")
            # Trust: Carrier failed to deliver for ultimate_buyer
            if carrier_username and ultimate_buyer_username:
                update_trust_score_for_activity(tables, carrier_username, ultimate_buyer_username, TRUST_SCORE_FAILURE_SIMPLE, "deliver_to_buyer_inventory", False, "carrier_inventory_issue")
            all_deliveries_successful = False
            continue # Skip adding to building if removal failed

        # 2. Add to destination building's inventory (owned by ultimate_buyer_username)
        # The owner of resources in the destination building is the ultimate_buyer_username.
        building_added = update_resource_count(
            tables, destination_building_custom_id, 'building', ultimate_buyer_username,
            resource_id, amount_to_deliver, resource_defs, now_iso,
            notes=f"Reçu de {carrier_username} pour contrat {original_contract_custom_id}"
        )
        if not building_added:
            log.error(f"Échec de l'ajout de {amount_to_deliver} de {resource_id} au bâtiment {destination_building_custom_id} (pour {ultimate_buyer_username}).")
            # Attempt to revert carrier's inventory (best effort)
            update_resource_count(
                tables, carrier_username, 'citizen', ultimate_buyer_username,
                resource_id, amount_to_deliver, resource_defs, now_iso,
                notes=f"Retour à l'inventaire suite à échec livraison à {destination_building_custom_id}"
            )
            # Trust: Destination building couldn't receive for ultimate_buyer
            # This is more of a system/building issue than a relationship issue unless the buyer owns the building.
            all_deliveries_successful = False
            continue
        
        log.info(f"{LogColors.OKGREEN}Livré {amount_to_deliver:.2f} de {resource_id} à {destination_building_custom_id} pour {ultimate_buyer_username}.{LogColors.ENDC}")
        # Trust: Carrier successfully delivered for ultimate_buyer
        if carrier_username and ultimate_buyer_username:
            update_trust_score_for_activity(tables, carrier_username, ultimate_buyer_username, TRUST_SCORE_SUCCESS_SIMPLE, "deliver_to_buyer_building", True)


    if not all_deliveries_successful:
        reason = "Une ou plusieurs livraisons de ressources ont échoué."
        return _fail_activity_with_note(tables, activity_id_airtable, activity_guid, activity_fields.get('Notes', ''), reason)

    # Update carrier's position to the destination building
    try:
        tables['citizens'].update(carrier_citizen_record['id'], {'Position': destination_building_pos_str})
        log.info(f"Position du transporteur {carrier_username} mise à jour à {destination_building_custom_id} ({destination_building_pos_str}).")
    except Exception as e_pos:
        log.error(f"Erreur MAJ position transporteur {carrier_username}: {e_pos}")
        # Non-fatal for the delivery itself, but log it.

    log.info(f"{LogColors.OKGREEN}Activité 'deliver_resource_to_buyer' {activity_guid} traitée avec succès.{LogColors.ENDC}")
    return True

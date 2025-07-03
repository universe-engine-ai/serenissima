import logging
import json
from typing import Dict, List, Optional, Any

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_building_record,
    get_citizen_record,
    update_resource_count, # Generic helper to update/create/delete resource stacks
    get_building_type_info, # To get storageCapacity
    get_building_storage_details # To get current load and inventory map
)
# Import relationship helper if trust scores should be affected
# from backend.engine.utils.relationship_helpers import update_trust_score_for_activity, TRUST_SCORE_SUCCESS_MINOR, TRUST_SCORE_FAILURE_MINOR

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any], # Pass pre-fetched definitions
    resource_defs: Dict[str, Any],      # Pass pre-fetched definitions
    api_base_url: Optional[str] = None  # Added for signature consistency
) -> bool:
    """
    Processes the 'deposit_items_at_location' activity.
    Transfers specified items from the citizen's inventory to the target building's inventory.
    """
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    notes_str = activity_fields.get('Notes')

    log.info(f"{LogColors.PROCESS}📦 Traitement de 'deposit_items_at_location': {activity_guid} pour {citizen_username}{LogColors.ENDC}")

    if not notes_str:
        log.error(f"{LogColors.FAIL}Activity {activity_guid} n'a pas de champ 'Notes' avec les détails du dépôt. Abandon.{LogColors.ENDC}")
        return False

    try:
        deposit_details = json.loads(notes_str)
        items_to_deposit: List[Dict[str, Any]] = deposit_details.get("items_to_deposit", [])
        target_building_id: Optional[str] = deposit_details.get("target_building_id")
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Activity {activity_guid}: Échec du parsing JSON des Notes: {notes_str}{LogColors.ENDC}")
        return False

    if not items_to_deposit or not target_building_id:
        log.error(f"{LogColors.FAIL}Activity {activity_guid}: 'items_to_deposit' ou 'target_building_id' manquant dans les Notes. Abandon.{LogColors.ENDC}")
        return False

    citizen_record = get_citizen_record(tables, citizen_username)
    target_building_record = get_building_record(tables, target_building_id)

    if not citizen_record:
        log.error(f"{LogColors.FAIL}Citoyen {citizen_username} non trouvé pour l'activité {activity_guid}. Abandon.{LogColors.ENDC}")
        return False
    if not target_building_record:
        log.error(f"{LogColors.FAIL}Bâtiment cible {target_building_id} non trouvé pour l'activité {activity_guid}. Abandon.{LogColors.ENDC}")
        return False

    target_building_type_str = target_building_record['fields'].get('Type')
    target_building_def = get_building_type_info(target_building_type_str, building_type_defs)
    
    storage_capacity_building = 0.0
    if target_building_def and isinstance(target_building_def.get('productionInformation'), dict):
        storage_capacity_building = float(target_building_def['productionInformation'].get('storageCapacity', 0.0))
    elif target_building_def and target_building_def.get('category', '').lower() == 'home':
        storage_capacity_building = float(target_building_def.get('storageCapacity', 50.0)) # Default for homes
    
    if storage_capacity_building <= 0:
        log.warning(f"{LogColors.WARNING}Bâtiment cible {target_building_id} n'a pas de capacité de stockage définie (capacité: {storage_capacity_building}). Dépôt impossible.{LogColors.ENDC}")
        return False

    owner_in_target_building = target_building_record['fields'].get('RunBy') or target_building_record['fields'].get('Owner')
    if not owner_in_target_building:
        owner_in_target_building = citizen_username
        log.info(f"  Aucun RunBy/Owner pour {target_building_id}. Les objets déposés appartiendront à {citizen_username}.")

    current_building_load, _ = get_building_storage_details(tables, target_building_id, owner_in_target_building)
    available_space_in_building = storage_capacity_building - current_building_load

    log.info(f"  Dépôt à {target_building_id} (Capacité: {storage_capacity_building:.2f}, Charge Actuelle: {current_building_load:.2f}, Espace Dispo: {available_space_in_building:.2f})")

    all_transfers_successful_for_activity = True
    items_actually_deposited_count = 0

    for item_stack_from_inventory in items_to_deposit:
        res_id_to_deposit = item_stack_from_inventory.get("ResourceId")
        amount_to_deposit_total = float(item_stack_from_inventory.get("Amount", 0.0))
        owner_on_citizen = item_stack_from_inventory.get("Owner") 

        if not res_id_to_deposit or amount_to_deposit_total <= 0:
            log.warning(f"  Objet invalide dans la liste de dépôt: {item_stack_from_inventory}. Ignoré.")
            continue

        if available_space_in_building <= 0.01:
            log.info(f"  Plus d'espace de stockage disponible dans {target_building_id}. Arrêt des dépôts pour cette activité.")
            break 

        amount_can_deposit_this_item = min(amount_to_deposit_total, available_space_in_building)
        
        log.info(f"  Tentative de dépôt de {amount_can_deposit_this_item:.2f} / {amount_to_deposit_total:.2f} de {res_id_to_deposit}...")

        if not owner_on_citizen:
            log.error(f"    Échec de la décrémentation: Propriétaire de la pile {res_id_to_deposit} sur {citizen_username} non spécifié. Ignoré.")
            all_transfers_successful_for_activity = False
            continue

        success_decrement = update_resource_count(
            tables, citizen_username, "citizen", owner_on_citizen, 
            res_id_to_deposit, -amount_can_deposit_this_item, resource_defs
        )
        if not success_decrement:
            log.error(f"    Échec de la décrémentation de {amount_can_deposit_this_item:.2f} de {res_id_to_deposit} de l'inventaire de {citizen_username} (appartenant à {owner_on_citizen}).")
            all_transfers_successful_for_activity = False
            continue

        success_increment = update_resource_count(
            tables, target_building_id, "building", owner_in_target_building,
            res_id_to_deposit, amount_can_deposit_this_item, resource_defs
        )
        if not success_increment:
            log.error(f"    Échec de l'incrémentation de {amount_can_deposit_this_item:.2f} de {res_id_to_deposit} dans {target_building_id} (pour {owner_in_target_building}).")
            all_transfers_successful_for_activity = False
            # Attempt to roll back citizen's inventory
            update_resource_count(
                tables, citizen_username, "citizen", owner_on_citizen,
                res_id_to_deposit, amount_can_deposit_this_item, resource_defs 
            )
            continue

        log.info(f"    Succès: {amount_can_deposit_this_item:.2f} de {res_id_to_deposit} transféré de {citizen_username} à {target_building_id}.")
        available_space_in_building -= amount_can_deposit_this_item
        items_actually_deposited_count += 1

    if items_actually_deposited_count > 0:
        log.info(f"{LogColors.OKGREEN}Activité {activity_guid}: {items_actually_deposited_count} type(s) d'objets déposés avec succès à {target_building_id}.{LogColors.ENDC}")
    elif not items_to_deposit:
        log.info(f"{LogColors.OKBLUE}Activité {activity_guid}: Aucun objet spécifié pour le dépôt.{LogColors.ENDC}")
    else:
        log.warning(f"{LogColors.WARNING}Activité {activity_guid}: Aucun objet n'a pu être déposé à {target_building_id} (ex: pas d'espace, erreurs).{LogColors.ENDC}")
    
    return all_transfers_successful_for_activity

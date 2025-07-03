import logging
import json
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_building_record,
    update_citizen_ducats,
    update_resource_count, # For consuming the drink
    VENICE_TIMEZONE # For potential future use
)
from backend.engine.utils.relationship_helpers import (
    update_trust_score_for_activity,
    TRUST_SCORE_MINOR_POSITIVE
)

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any], # Not directly used here but part of signature
    resource_defs: Dict[str, Any],      # Pass pre-fetched resource_defs
    api_base_url: Optional[str] = None
) -> bool:
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    notes_str = activity_fields.get('Notes')

    log.info(f"{LogColors.ACTIVITY}🍷 Traitement de 'drink_at_inn': {activity_guid} pour {citizen_username}.{LogColors.ENDC}")

    if not citizen_username or not notes_str:
        log.error(f"{LogColors.FAIL}Activité {activity_guid} manque Citizen ou Notes. Abandon.{LogColors.ENDC}")
        return False

    try:
        activity_details = json.loads(notes_str)
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Impossible de parser Notes JSON pour l'activité {activity_guid}: {notes_str}{LogColors.ENDC}")
        return False

    inn_id = activity_details.get("inn_id")
    inn_name = activity_details.get("inn_name", "une auberge inconnue")
    drink_type = activity_details.get("drink_type")
    drink_price_expected = float(activity_details.get("drink_price_expected", 0.0))
    # drink_contract_id = activity_details.get("drink_contract_id") # Not directly used by processor, but good for context

    if not inn_id or not drink_type or drink_price_expected <= 0:
        log.error(f"{LogColors.FAIL}Détails de l'activité {activity_guid} incomplets (inn_id, drink_type, drink_price). Abandon.{LogColors.ENDC}")
        return False

    citizen_airtable_record = get_citizen_record(tables, citizen_username)
    if not citizen_airtable_record:
        log.error(f"{LogColors.FAIL}Citoyen {citizen_username} non trouvé pour l'activité {activity_guid}. Abandon.{LogColors.ENDC}")
        return False
    
    inn_building_record = get_building_record(tables, inn_id)
    if not inn_building_record:
        log.error(f"{LogColors.FAIL}Auberge {inn_id} non trouvée pour l'activité {activity_guid}. Abandon.{LogColors.ENDC}")
        return False
    
    inn_operator_username = inn_building_record['fields'].get('RunBy') or inn_building_record['fields'].get('Owner')
    if not inn_operator_username:
        log.error(f"{LogColors.FAIL}Auberge {inn_name} ({inn_id}) n'a pas d'opérateur. Impossible de traiter le paiement/consommation.{LogColors.ENDC}")
        return False

    current_citizen_ducats = float(citizen_airtable_record['fields'].get('Ducats', 0.0))
    if current_citizen_ducats < drink_price_expected:
        log.warning(f"{LogColors.WARNING}Citoyen {citizen_username} n'a pas assez de Ducats ({current_citizen_ducats:.2f}) pour {drink_type} ({drink_price_expected:.2f}). Activité échouée.{LogColors.ENDC}")
        return False

    # 1. Consume the drink from the inn's inventory (owned by inn_operator_username)
    # We assume 1 unit of the drink is consumed.
    if not update_resource_count(tables, inn_id, "building", inn_operator_username, drink_type, -1.0, resource_defs):
        log.error(f"{LogColors.FAIL}Échec de la consommation de {drink_type} de l'inventaire de l'auberge {inn_name} ({inn_id}). L'auberge est peut-être en rupture de stock.{LogColors.ENDC}")
        return False # Cannot proceed if drink is not available
    log.info(f"  {drink_type} consommé de l'inventaire de {inn_name} (Opérateur: {inn_operator_username}).")

    # 2. Process payment: Deduct from citizen, credit inn operator
    if not update_citizen_ducats(tables, citizen_airtable_record['id'], -drink_price_expected, f"Paid for {drink_type} at {inn_name}", "leisure_expense", inn_id):
        log.error(f"{LogColors.FAIL}Échec de la déduction des Ducats de {citizen_username} pour {drink_type}. Activité échouée.{LogColors.ENDC}")
        # Rollback consumption? For now, no. Drink was "poured" but not paid. Inn loses 1 unit.
        return False
    
    inn_operator_record = get_citizen_record(tables, inn_operator_username)
    if inn_operator_record:
        if not update_citizen_ducats(tables, inn_operator_record['id'], drink_price_expected, f"Income from {citizen_username}'s {drink_type} at {inn_name}", "sales_revenue", inn_id):
            log.warning(f"{LogColors.WARNING}Échec du crédit des Ducats à l'opérateur de l'auberge {inn_operator_username}. Le paiement a été pris à {citizen_username}.{LogColors.ENDC}")
    else:
        log.warning(f"{LogColors.WARNING}Opérateur de l'auberge {inn_operator_username} non trouvé. Ducats pour {drink_type} non crédités (mais déduits de {citizen_username}).{LogColors.ENDC}")

    # 3. Update trust with inn operator
    if inn_operator_username != citizen_username:
        update_trust_score_for_activity(
            tables,
            citizen_username, 
            inn_operator_username, 
            TRUST_SCORE_MINOR_POSITIVE,
            "drink_purchase_at_inn",
            True, 
            f"bought_{drink_type.replace('_','-')}_at_{inn_id.replace('_','-')}",
            activity_record_for_kinos=activity_record 
        )

    log.info(f"{LogColors.OKGREEN}Activité 'drink_at_inn' {activity_guid} pour {citizen_username} à {inn_name} traitée avec succès.{LogColors.ENDC}")
    return True

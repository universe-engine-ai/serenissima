import logging
import json
import uuid
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any, List

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_closest_building_of_type,
    _get_building_position_coords,
    _calculate_distance_meters,
    get_path_between_points,
    create_activity_record,
    VENICE_TIMEZONE,
    dateutil_parser,
    get_building_record, # Added
    get_citizen_record # Added
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

DRINK_AT_INN_DURATION_HOURS = 1.0
DRINKABLE_RESOURCE_TYPES = ["wine", "spiced_wine"]

def try_create_drink_at_inn_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Optional[Dict[str, float]],
    resource_defs: Dict[str, Any], # Added
    building_type_defs: Dict[str, Any], # Added
    now_venice_dt: datetime, # Added
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str, # Added
    start_time_utc_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a 'drink_at_inn' activity chain.
    1. Find the nearest 'inn' building that sells wine or spiced_wine.
    2. If not at the inn, create 'goto_location' to the inn.
    3. Create 'drink_at_inn' activity at the inn.
    Returns the first activity in the chain.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    if not citizen_position:
        log.warning(f"{LogColors.WARNING}[Boire Auberge] {citizen_name_log} n'a pas de position. Impossible de créer 'drink_at_inn'.{LogColors.ENDC}")
        return None

    log.info(f"{LogColors.ACTIVITY}[Boire Auberge] Tentative de création d'activité pour {citizen_name_log}.{LogColors.ENDC}")

    # Find inns and check if they sell wine/spiced_wine
    potential_inns = tables['buildings'].all(formula="{Type}='inn'")
    valid_inns_with_drinks: List[Dict[str, Any]] = []

    for inn_candidate_record in potential_inns:
        inn_candidate_id = inn_candidate_record['fields'].get('BuildingId')
        if not inn_candidate_id:
            continue

        # Check for active sell contracts for wine or spiced_wine
        for drink_type in DRINKABLE_RESOURCE_TYPES:
            contract_formula = (
                f"AND({{Type}}='public_sell', {{SellerBuilding}}='{_escape_airtable_value(inn_candidate_id)}', "
                f"{{ResourceType}}='{_escape_airtable_value(drink_type)}', {{TargetAmount}}>0, "
                f"{{EndAt}}>'{now_utc_dt.isoformat()}', {{CreatedAt}}<='{now_utc_dt.isoformat()}' )"
            )
            try:
                contracts = tables['contracts'].all(formula=contract_formula, max_records=1)
                if contracts:
                    # Check stock at the inn for this drink
                    inn_operator = inn_candidate_record['fields'].get('RunBy') or inn_candidate_record['fields'].get('Owner')
                    if inn_operator:
                        from backend.engine.utils.activity_helpers import get_source_building_resource_stock # Local import
                        stock = get_source_building_resource_stock(tables, inn_candidate_id, drink_type, inn_operator)
                        if stock >= 1.0: # Needs at least 1 unit
                            inn_candidate_record['_drink_type_available'] = drink_type
                            inn_candidate_record['_drink_price'] = float(contracts[0]['fields'].get('PricePerResource', 0))
                            inn_candidate_record['_contract_id_for_drink'] = contracts[0]['fields'].get('ContractId', contracts[0]['id'])
                            valid_inns_with_drinks.append(inn_candidate_record)
                            break # Found a drink at this inn
            except Exception as e_contract:
                log.error(f"Erreur vérification contrat pour {drink_type} à {inn_candidate_id}: {e_contract}")
    
    if not valid_inns_with_drinks:
        log.info(f"{LogColors.OKBLUE}[Boire Auberge] {citizen_name_log}: Aucune auberge trouvée vendant du vin/vin épicé avec stock.{LogColors.ENDC}")
        return None

    # Find the closest valid inn that isn't overcrowded
    closest_inn_record = None
    min_distance = float('inf')
    for inn_rec in valid_inns_with_drinks:
        inn_pos_iter = _get_building_position_coords(inn_rec)
        if inn_pos_iter:
            # Check building capacity (max 10 citizens)
            inn_building_id = inn_rec['fields'].get('BuildingId')
            inn_position_str = inn_rec['fields'].get('Position', '')
            
            # Count citizens at this building by checking their Position field
            citizens_at_inn_formula = f"{{Position}}='{_escape_airtable_value(inn_position_str)}'"
            try:
                citizens_at_inn = tables['citizens'].all(formula=citizens_at_inn_formula)
                citizen_count = len(citizens_at_inn)
                
                if citizen_count >= 10:
                    log.info(f"{LogColors.WARNING}[Boire Auberge] {inn_rec['fields'].get('Name', inn_building_id)} est plein ({citizen_count} citoyens). Capacité max: 10.{LogColors.ENDC}")
                    continue  # Skip this inn, it's at capacity
            except Exception as e:
                log.error(f"Erreur vérification capacité pour {inn_building_id}: {e}")
                # Continue anyway if we can't check capacity
            
            distance = _calculate_distance_meters(citizen_position, inn_pos_iter)
            if distance < min_distance:
                min_distance = distance
                closest_inn_record = inn_rec
    
    if not closest_inn_record:
        log.info(f"{LogColors.OKBLUE}[Boire Auberge] {citizen_name_log}: Aucune auberge valide accessible trouvée (toutes pleines ou sans stock).{LogColors.ENDC}")
        return None

    inn_custom_id = closest_inn_record['fields'].get('BuildingId')
    inn_pos = _get_building_position_coords(closest_inn_record)
    inn_name_display = closest_inn_record['fields'].get('Name', inn_custom_id)
    drink_to_consume = closest_inn_record['_drink_type_available']
    drink_price = closest_inn_record['_drink_price']
    drink_contract_id = closest_inn_record['_contract_id_for_drink']

    if not inn_custom_id or not inn_pos: # Should not happen if closest_inn_record is valid
        log.warning(f"{LogColors.WARNING}[Boire Auberge] {citizen_name_log}: Auberge cible ({inn_name_display}) invalide.{LogColors.ENDC}")
        return None

    is_at_inn = _calculate_distance_meters(citizen_position, inn_pos) < 20

    activity_chain = []
    current_chain_time_iso = start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()

    if not is_at_inn:
        path_to_inn = get_path_between_points(citizen_position, inn_pos, transport_api_url)
        if not (path_to_inn and path_to_inn.get('success')):
            log.warning(f"{LogColors.WARNING}[Boire Auberge] {citizen_name_log}: Impossible de trouver un chemin vers {inn_name_display}.{LogColors.ENDC}")
            return None

        goto_activity = try_create_goto_location_activity(
            tables=tables,
            citizen_record=citizen_record,
            activity_params={ # Pass params as a dictionary
                "targetBuildingId": inn_custom_id,
                "notes": f"Se rendant à {inn_name_display} pour boire un verre.",
                "startTimeUtcIso": current_chain_time_iso
            },
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            now_venice_dt=now_venice_dt,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url
        )
        if not goto_activity:
            log.warning(f"{LogColors.WARNING}[Boire Auberge] {citizen_name_log}: Échec de la création de 'goto_location' vers {inn_name_display}.{LogColors.ENDC}")
            return None
        activity_chain.append(goto_activity)
        current_chain_time_iso = goto_activity['fields']['EndDate']

    # Create drink_at_inn activity
    drink_start_dt = dateutil_parser.isoparse(current_chain_time_iso.replace("Z", "+00:00"))
    if drink_start_dt.tzinfo is None:
        drink_start_dt = pytz.utc.localize(drink_start_dt)
    
    drink_end_dt = drink_start_dt + timedelta(hours=DRINK_AT_INN_DURATION_HOURS)
    drink_end_time_iso = drink_end_dt.isoformat()

    activity_details_for_notes = {
        "inn_id": inn_custom_id,
        "inn_name": inn_name_display,
        "drink_type": drink_to_consume,
        "drink_price_expected": drink_price,
        "drink_contract_id": drink_contract_id,
        "duration_hours": DRINK_AT_INN_DURATION_HOURS
    }

    drink_activity = create_activity_record(
        tables=tables,
        citizen_username=citizen_username,
        activity_type="drink_at_inn",
        start_date_iso=current_chain_time_iso,
        end_date_iso=drink_end_time_iso,
        from_building_id=inn_custom_id,
        to_building_id=inn_custom_id,
        title=f"Boire un verre de {drink_to_consume} à {inn_name_display}",
        description=f"{citizen_name_log} prend un verre de {drink_to_consume} à l'auberge {inn_name_display}.",
        thought=f"Un bon verre de {drink_to_consume} à {inn_name_display} me fera du bien.",
        notes=json.dumps(activity_details_for_notes),
        priority_override=50 # Leisure activity priority
    )

    if not drink_activity:
        log.error(f"{LogColors.FAIL}[Boire Auberge] {citizen_name_log}: Échec de la création de l'activité 'drink_at_inn'.{LogColors.ENDC}")
        if activity_chain: # If goto was created, try to delete it
            try: tables['activities'].delete(activity_chain[0]['id'])
            except: pass
        return None
    
    activity_chain.append(drink_activity)

    log.info(f"{LogColors.OKGREEN}[Boire Auberge] {citizen_name_log}: Chaîne d'activités 'boire à l'auberge' créée. Première activité: {activity_chain[0]['fields']['Type']}.{LogColors.ENDC}")
    return activity_chain[0]

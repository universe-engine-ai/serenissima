import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pytz
from dateutil import parser as dateutil_parser

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_inventory_details,
    get_citizen_home,
    get_citizen_workplace,
    get_building_record,
    _get_building_position_coords,
    _calculate_distance_meters,
    get_path_between_points,
    create_activity_record, # Generic activity record creation
    get_resource_types_from_api, # To understand resource categories
    get_building_storage_details,
    get_citizen_effective_carry_capacity,
    VENICE_TIMEZONE, # Added VENICE_TIMEZONE import
    _escape_airtable_value # Added import for _escape_airtable_value
)
from .goto_location_activity_creator import try_create as try_create_goto_location_activity

log = logging.getLogger(__name__)

# Define resource categories for deposit logic (can be expanded)
RESOURCE_CATEGORIES_FOR_DEPOSIT = {
    "food": ["home"], # Food items go to home
    "raw_material": ["workplace", "storage"], # Raw materials to workplace or general storage
    "component": ["workplace", "storage"],
    "finished_good": ["workplace", "storage"], # Finished goods from workplace, or to storage
    "trade_good": ["storage", "workplace"], # Goods meant for trading
    "personal": ["home"], # Personal items
    "tool": ["home", "workplace"], # Tools can be at home or workplace
    "book": ["home"],
    "art": ["home", "storage"], # Art can be at home or stored
    "default": ["storage", "home"] # Default fallback
}
MAX_ITEMS_PER_DEPOSIT_ACTIVITY = 5 # Max items to include in a single deposit_items_at_location activity

def try_create_deposit_inventory_orchestrator(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    citizen_position: Dict[str, float],
    resource_defs: Dict[str, Any], # Pass pre-fetched resource definitions
    building_type_defs: Dict[str, Any], # Pass pre-fetched building type definitions
    now_utc_dt: datetime,
    transport_api_url: str,
    api_base_url: str,
    start_time_utc_iso: Optional[str] = None # For chaining, if this orchestrator is called as part of a chain
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the deposit of a citizen's inventory to appropriate locations.
    Creates a chain of goto_location and deposit_items_at_location activities.
    Returns the first activity in the chain, or None if no deposit is needed or possible.
    """
    citizen_username = citizen_record['fields'].get('Username')
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_airtable_id = citizen_record['id']
    citizen_name_log = f"{citizen_record['fields'].get('FirstName', '')} {citizen_record['fields'].get('LastName', '')}".strip() or citizen_username

    log.info(f"{LogColors.ACTIVITY}[Dépôt Inventaire] Orchestration pour {citizen_name_log}.{LogColors.ENDC}")

    inventory = get_citizen_inventory_details(tables, citizen_username)
    if not inventory:
        log.info(f"{LogColors.OKBLUE}[Dépôt Inventaire] {citizen_name_log}: Inventaire vide. Aucun dépôt nécessaire.{LogColors.ENDC}")
        return None

    # --- Determine deposit locations and items for each ---
    deposits_by_location: Dict[str, List[Dict[str, Any]]] = {} # Key: building_id, Value: list of items {"ResourceId", "Amount", "Owner", "AirtableRecordId"}

    home_record = get_citizen_home(tables, citizen_username)
    workplace_record = get_citizen_workplace(tables, citizen_custom_id, citizen_username)
    # TODO: Add logic for finding suitable 'storage' buildings (e.g., warehouses with contracts)

    for item_stack in inventory:
        resource_id = item_stack.get("ResourceId")
        item_owner = item_stack.get("Owner") # Owner of the item stack in citizen's inventory
        if not resource_id: continue

        deposited_this_item = False

        # Prioritize depositing client-owned materials to their construction site
        if item_owner and item_owner != citizen_username:
            log.debug(f"  Item {resource_id} (owned by {item_owner}) in {citizen_username}'s inventory. Checking for construction project delivery.")
            # Find active construction_project where citizen is the Seller and item_owner is the Buyer
            construction_project_formula = (
                f"AND({{Type}}='construction_project', "
                f"{{Seller}}='{_escape_airtable_value(citizen_username)}', "
                f"{{Buyer}}='{_escape_airtable_value(item_owner)}', "
                f"NOT(OR({{Status}}='completed', {{Status}}='failed', {{Status}}='cancelled')))"
            )
            try:
                active_projects_for_item_owner = tables['contracts'].all(formula=construction_project_formula)
                if active_projects_for_item_owner:
                    project_contract = active_projects_for_item_owner[0] # Assume first active project
                    construction_site_id = project_contract['fields'].get('BuyerBuilding')
                    
                    if construction_site_id:
                        if construction_site_id not in deposits_by_location:
                            deposits_by_location[construction_site_id] = []
                        deposits_by_location[construction_site_id].append(item_stack)
                        deposited_this_item = True
                        log.info(f"  Item {resource_id} (owned by {item_owner}) assigned to construction site {construction_site_id} via contract {project_contract['fields'].get('ContractId', project_contract['id'])}.")
                    else:
                        log.warning(f"  Construction project {project_contract['fields'].get('ContractId', project_contract['id'])} found for item {resource_id} (owner: {item_owner}), but no BuyerBuilding (site ID).")
            except Exception as e_contract_search:
                log.error(f"  Error searching for construction projects for item {resource_id} (owner: {item_owner}): {e_contract_search}")

        if deposited_this_item:
            continue # Move to the next item_stack in inventory, this one is handled

        # Original generic deposit logic if not handled by client-project logic above
        res_def = resource_defs.get(resource_id, {})
        res_category = res_def.get("category", "default").lower()
        
        # Determine preferred deposit locations based on category
        preferred_location_types = RESOURCE_CATEGORIES_FOR_DEPOSIT.get(res_category, RESOURCE_CATEGORIES_FOR_DEPOSIT["default"])
        
        # deposited_this_item was reset at the start of the item_stack loop
        for loc_type in preferred_location_types:
            target_building_record: Optional[Dict] = None
            if loc_type == "home" and home_record:
                target_building_record = home_record
            elif loc_type == "workplace" and workplace_record:
                target_building_record = workplace_record
            # elif loc_type == "storage":
                # TODO: Find a suitable storage building record
                # This might involve checking for 'storage_query' contracts where the citizen is the Buyer (owner of goods)
                # or if they operate a storage building themselves.
                # For now, skip 'storage' if not home or workplace.
                # pass 

            if target_building_record:
                building_id = target_building_record['fields'].get('BuildingId')
                if building_id:
                    # Vérification pour empêcher le dépôt de "raw_materials" à domicile.
                    # Cette vérification est effectuée si le type de lieu de dépôt actuel ('loc_type') est 'home'.
                    if loc_type == "home":
                        original_resource_category = res_def.get("category") # res_def est défini plus haut dans la boucle
                        if original_resource_category and original_resource_category.lower() == "raw_materials":
                            log.info(f"{LogColors.INFO}[Dépôt Inventaire] {citizen_name_log}: Objet '{resource_id}' (catégorie originale: 'raw_materials') ne sera pas déposé à domicile ('{loc_type}'). Tentative autre lieu.{LogColors.ENDC}")
                            # Ne pas marquer cet objet comme déposé ici.
                            # Passer au prochain type de lieu préféré pour cet objet.
                            continue 

                    # Si l'objet n'a pas été ignoré par la vérification ci-dessus, procéder au dépôt.
                    if building_id not in deposits_by_location:
                        deposits_by_location[building_id] = []
                    deposits_by_location[building_id].append(item_stack)
                    deposited_this_item = True
                    log.debug(f"  Item {resource_id} ({item_stack.get('Amount')}) assigné à {loc_type} ({building_id})")
                    break # Item assigned to a location
        
        if not deposited_this_item:
            log.warning(f"{LogColors.WARNING}[Dépôt Inventaire] {citizen_name_log}: Impossible de déterminer un lieu de dépôt pour {resource_id}.{LogColors.ENDC}")

    if not deposits_by_location:
        log.info(f"{LogColors.OKBLUE}[Dépôt Inventaire] {citizen_name_log}: Aucun lieu de dépôt approprié trouvé pour les objets de l'inventaire.{LogColors.ENDC}")
        return None

    # --- Create activity chain ---
    activity_chain: List[Dict[str, Any]] = []
    current_location_coords = citizen_position
    current_time_for_chain_iso = start_time_utc_iso if start_time_utc_iso else now_utc_dt.isoformat()

    for building_id, items_to_deposit_at_loc in deposits_by_location.items():
        if not items_to_deposit_at_loc: continue

        target_deposit_building_record = get_building_record(tables, building_id)
        if not target_deposit_building_record:
            log.warning(f"{LogColors.WARNING}[Dépôt Inventaire] Bâtiment de dépôt {building_id} non trouvé. Ignoré.{LogColors.ENDC}")
            continue
        
        target_deposit_location_coords = _get_building_position_coords(target_deposit_building_record)
        if not target_deposit_location_coords:
            log.warning(f"{LogColors.WARNING}[Dépôt Inventaire] Bâtiment de dépôt {building_id} n'a pas de coordonnées. Ignoré.{LogColors.ENDC}")
            continue

        target_bldg_name_log = target_deposit_building_record['fields'].get('Name', building_id)

        # 1. Create goto_location if not already there
        distance_to_target = _calculate_distance_meters(current_location_coords, target_deposit_location_coords)
        
        if distance_to_target > 20: # Needs travel
            path_to_target_loc = get_path_between_points(current_location_coords, target_deposit_location_coords, transport_api_url)
            if not (path_to_target_loc and path_to_target_loc.get('success')):
                log.warning(f"{LogColors.WARNING}[Dépôt Inventaire] Impossible de trouver un chemin vers {target_bldg_name_log} pour {citizen_name_log}. Dépôt ignoré.{LogColors.ENDC}")
                continue # Skip this location if pathing fails

            # Prepare parameters for goto_location_activity_creator
            # The 'now_utc_dt' for this specific goto_location call should be the start time of this leg of the chain
            current_leg_start_time_utc = dateutil_parser.isoparse(current_time_for_chain_iso.replace("Z", "+00:00"))
            if current_leg_start_time_utc.tzinfo is None:
                current_leg_start_time_utc = pytz.utc.localize(current_leg_start_time_utc)
            current_leg_start_time_venice = current_leg_start_time_utc.astimezone(VENICE_TIMEZONE)

            goto_activity_params = {
                "targetBuildingId": building_id,
                "notes": f"Se rendant à {target_bldg_name_log} pour déposer des objets."
                # fromBuildingId can be omitted, creator will use citizen's current position.
            }
            
            goto_activity = try_create_goto_location_activity(
                tables=tables,
                citizen_record=citizen_record,
                activity_params=goto_activity_params,
                resource_defs=resource_defs, # Pass through
                building_type_defs=building_type_defs, # Pass through
                now_venice_dt=current_leg_start_time_venice, # Use the start time of this leg
                now_utc_dt=current_leg_start_time_utc,       # Use the start time of this leg
                transport_api_url=transport_api_url,
                api_base_url=api_base_url
            )
            if not goto_activity:
                log.error(f"{LogColors.FAIL}[Dépôt Inventaire] Échec de création de goto_location vers {target_bldg_name_log}. Dépôt ignoré.{LogColors.ENDC}")
                continue
            
            activity_chain.append(goto_activity)
            current_time_for_chain_iso = goto_activity['fields']['EndDate']
            current_location_coords = target_deposit_location_coords # Update current location for next iteration
            log.info(f"{LogColors.ACTIVITY}[Dépôt Inventaire] Activité goto_location vers {target_bldg_name_log} ajoutée à la chaîne.")

        # 2. Create deposit_items_at_location activity(ies)
        # Split items if too many for one deposit activity
        for i in range(0, len(items_to_deposit_at_loc), MAX_ITEMS_PER_DEPOSIT_ACTIVITY):
            chunk_of_items = items_to_deposit_at_loc[i:i + MAX_ITEMS_PER_DEPOSIT_ACTIVITY]
            
            deposit_items_payload_notes = {
                "items_to_deposit": chunk_of_items, # List of {"ResourceId", "Amount", "Owner", "AirtableRecordId"}
                "target_building_id": building_id
            }
            deposit_duration_minutes = 5 + len(chunk_of_items) # Base 5 min + 1 min per item type
            
            deposit_start_dt = dateutil_parser.isoparse(current_time_for_chain_iso.replace("Z", "+00:00"))
            if deposit_start_dt.tzinfo is None: deposit_start_dt = pytz.UTC.localize(deposit_start_dt)
            deposit_end_dt = deposit_start_dt + timedelta(minutes=deposit_duration_minutes)
            
            deposit_activity = create_activity_record(
                tables=tables,
                citizen_username=citizen_username,
                activity_type="deposit_items_at_location",
                start_date_iso=current_time_for_chain_iso,
                end_date_iso=deposit_end_dt.isoformat(),
                from_building_id=building_id, # Occurs at the target building
                to_building_id=building_id,
                details_json=json.dumps(deposit_items_payload_notes), # Utiliser details_json pour le JSON structuré
                title=f"Déposer des objets à {target_bldg_name_log}",
                description=f"{citizen_name_log} dépose {len(chunk_of_items)} type(s) d'objets à {target_bldg_name_log}.",
                priority_override=25 # Higher than general work, lower than critical needs
            )
            if not deposit_activity:
                log.error(f"{LogColors.FAIL}[Dépôt Inventaire] Échec de création de deposit_items_at_location à {target_bldg_name_log}. Dépôt ignoré.{LogColors.ENDC}")
                # If one deposit chunk fails, we might skip subsequent ones for this location or stop entirely.
                # For now, let's try to continue with other locations if possible.
                break # Break from chunks for this location
            
            activity_chain.append(deposit_activity)
            current_time_for_chain_iso = deposit_activity['fields']['EndDate']
            # current_location_coords remains at this building for the next chunk or next location if no travel
            log.info(f"{LogColors.ACTIVITY}[Dépôt Inventaire] Activité deposit_items_at_location à {target_bldg_name_log} ajoutée à la chaîne.")
        
    if not activity_chain:
        log.info(f"{LogColors.OKBLUE}[Dépôt Inventaire] {citizen_name_log}: Aucune activité de dépôt valide n'a pu être créée.{LogColors.ENDC}")
        return None
    
    return activity_chain[0] # Retourner la première activité de la chaîne créée

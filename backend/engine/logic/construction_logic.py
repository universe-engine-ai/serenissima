import logging
import json # Ajout de l'import manquant
import requests # Ajout de l'import requests
from typing import Dict, Any, List, Optional
from pyairtable import Table # pyright: ignore [reportMissingTypeStubs]

# Importation des types et fonctions nécessaires
from backend.engine.utils.activity_helpers import get_building_type_info # Importation ajoutée
# from backend.engine.activity_creators import ...

log = logging.getLogger(__name__)

# Import LogColors from the central utility
from backend.engine.utils.activity_helpers import LogColors

def handle_construction_worker_activity(
    tables: Dict[str, Table],
    citizen_record: Dict[str, Any],
    workplace_record: Dict[str, Any], # Le bâtiment de type "construction" où travaille le citoyen
    building_type_defs: Dict[str, Any], # Définitions globales des types de bâtiments
    resource_defs: Dict[str, Any], # Définitions globales des types de ressources
    now_venice_dt: Any, # datetime.datetime object
    now_utc_dt: Any, # datetime.datetime object
    transport_api_url: str,
    api_base_url: str
) -> bool:
    """
    Gère la logique d'activité pour un citoyen travaillant dans un bâtiment de construction.
    Retourne True si une activité a été créée, False sinon.
    """
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_username = citizen_record['fields'].get('Username')
    citizen_airtable_id = citizen_record['id']
    citizen_position_str = citizen_record['fields'].get('Position')
    citizen_position = json.loads(citizen_position_str) if citizen_position_str else None
    
    workplace_custom_id = workplace_record['fields'].get('BuildingId')
    workplace_operator_username = workplace_record['fields'].get('RunBy') or workplace_record['fields'].get('Owner')
    workplace_position_str = workplace_record['fields'].get('Position', '{}') # Get as string
    workplace_position = json.loads(workplace_position_str) # Parse

    # Import necessary helpers and creators locally to avoid circular dependencies at module level
    from backend.engine.utils.activity_helpers import (
        get_building_record, get_path_between_points,
        _escape_airtable_value, get_citizen_current_load, 
        get_citizen_effective_carry_capacity, 
        update_resource_count,
        _calculate_distance_meters,
        get_building_storage_details,
        _get_building_position_coords, 
        get_citizen_contracts,         
        _has_recent_failed_activity_for_contract, 
        get_citizen_record,
        get_citizen_inventory_details # Added for depositing inventory
    )
    from backend.engine.activity_creators import (
        try_create_deliver_construction_materials_activity,
        try_create_construct_building_activity,
        try_create_resource_fetching_activity,
        try_create_idle_activity,
        try_create_goto_work_activity, # Used for generic goto for now
        try_create_fetch_from_storage_activity, # Added for fetching from storage
        try_create_deposit_inventory_orchestrator, # Added for inventory deposit
        try_create_construct_building_activity # Assurez-vous que cela est importé
    )
    import datetime # Ensure datetime is available

    log.info(f"{LogColors.OKCYAN}Construction worker {citizen_username} at {workplace_custom_id} (Op: {workplace_operator_username}). Evaluating tasks.{LogColors.ENDC}")

    # Check for full inventory and attempt deposit if at workshop
    # This is done before evaluating construction contracts or workshop restocking
    # to ensure the citizen has capacity if fetching is needed.
    citizen_current_load_check = get_citizen_current_load(tables, citizen_username)
    effective_capacity_check = get_citizen_effective_carry_capacity(citizen_record)
    # Using 80% as a threshold to trigger deposit
    if citizen_current_load_check >= effective_capacity_check * 0.8: 
        log.info(f"  Citizen {citizen_username} inventory is {citizen_current_load_check:.2f}/{effective_capacity_check:.2f} (>=80% full). Attempting deposit orchestrator.")
        # citizen_position here is the workshop's position as this handler is called when citizen is at workplace
        deposit_orchestrator_activity = try_create_deposit_inventory_orchestrator(
            tables=tables,
            citizen_record=citizen_record,
            citizen_position=citizen_position, # citizen_position is already defined and is the workshop location
            resource_defs=resource_defs,
            building_type_defs=building_type_defs,
            now_utc_dt=now_utc_dt,
            transport_api_url=transport_api_url,
            api_base_url=api_base_url,
            start_time_utc_iso=None # Immediate start for the deposit chain
        )
        if deposit_orchestrator_activity:
            log.info(f"    Deposit inventory orchestrator activity created for {citizen_username}. First activity: {deposit_orchestrator_activity['fields'].get('Type')}. Construction logic will defer to this.")
            return True # An activity was created, so this worker's turn is done for now.
        else:
            log.info(f"    Deposit inventory orchestrator could not create an activity (e.g., no suitable deposit locations for current items). Proceeding with other tasks.")


    # --- Helper function for processing active construction contracts ---
    # The inventory deposit logic has been removed from here.
    # It will be handled by the general _handle_deposit_full_inventory in citizen_general_activities.py
    # at a lower priority, after work tasks.
    # However, we add specific deposit logic here if the worker is AT the site with materials for THIS project.
    from backend.engine.utils.activity_helpers import create_activity_record, get_citizen_inventory_details # Added imports
    from datetime import timedelta # Added import

    def _try_process_active_construction_contracts() -> bool:
        construction_contracts_formula = f"AND({{Type}}='construction_project', {{SellerBuilding}}='{_escape_airtable_value(workplace_custom_id)}', {{Status}}!='completed', {{Status}}!='failed')"
        active_construction_contracts = tables['contracts'].all(formula=construction_contracts_formula, sort=['CreatedAt'])

        if not active_construction_contracts:
            log.info(f"No active construction contracts for {workplace_custom_id}.")
        else:
            log.info(f"Found {len(active_construction_contracts)} active construction contracts for {workplace_custom_id}.")

        for contract in active_construction_contracts:
            contract_id_airtable = contract['id']
            contract_custom_id = contract['fields'].get('ContractId', contract_id_airtable)
            target_building_custom_id = contract['fields'].get('BuyerBuilding')
            log.info(f"  Processing contract {contract_custom_id} for target building {target_building_custom_id}.")

            target_building_record = get_building_record(tables, target_building_custom_id)
            if not target_building_record:
                log.warning(f"    Target building {target_building_custom_id} for contract {contract_custom_id} not found. Skipping contract.")
                continue

            target_building_pos = _get_building_position_coords(target_building_record) # Position of the current contract's construction site

            # Define required_materials_for_project and site_inventory here
            target_building_type_str = target_building_record['fields'].get('Type')
            target_building_def = get_building_type_info(target_building_type_str, building_type_defs)
            if not target_building_def:
                log.error(f"    Could not get building definition for target type {target_building_type_str} from pre-fetched definitions. Skipping contract {contract_custom_id}.")
                continue

            contract_notes_str = contract['fields'].get('Notes', '{}')
            construction_costs_from_contract = {}
            try:
                contract_notes_data = json.loads(contract_notes_str)
                if isinstance(contract_notes_data, dict) and 'constructionCosts' in contract_notes_data:
                    construction_costs_from_contract = contract_notes_data['constructionCosts']
            except json.JSONDecodeError:
                log.warning(f"Could not parse constructionCosts from contract {contract_custom_id} notes. Notes: {contract_notes_str}")
            
            if not construction_costs_from_contract: 
                construction_costs_from_contract = target_building_def.get('constructionCosts', {})
                log.info(f"    Using constructionCosts from building definition for {target_building_type_str} as not found in contract notes.")

            if not construction_costs_from_contract:
                log.warning(f"    Construction costs for {target_building_custom_id} are empty. Assuming no material costs.")
            
            required_materials_for_project = {k: float(v) for k, v in construction_costs_from_contract.items() if k != 'ducats' and isinstance(v, (int, float, str))}
            log.info(f"    Contract {contract_custom_id}: Required materials for {target_building_type_str}: {required_materials_for_project}")
            
            target_building_owner_username = contract['fields'].get('Buyer')
            if not target_building_owner_username:
                log.warning(f"    Contract {contract_custom_id} is missing Buyer. Skipping.")
                continue
            _, site_inventory = get_building_storage_details(tables, target_building_custom_id, target_building_owner_username)
            log.info(f"    Contract {contract_custom_id}: Site inventory at {target_building_custom_id}: {site_inventory}")
            
            # Check 1: If citizen is AT the construction site AND has materials for THIS project in inventory
            if citizen_position and target_building_pos and _calculate_distance_meters(citizen_position, target_building_pos) < 20:
                log.info(f"    Citizen {citizen_username} is at construction site {target_building_custom_id}. Checking inventory for deposit.")
                citizen_inventory = get_citizen_inventory_details(tables, citizen_username)
                items_to_deposit_for_this_site: List[Dict[str, Any]] = []

                if citizen_inventory:
                    project_owner_for_deposit_check = contract['fields'].get('Buyer') # Should be target_building_owner_username
                    for item_in_inv in citizen_inventory:
                        inv_res_id = item_in_inv.get("ResourceId")
                        inv_res_owner = item_in_inv.get("Owner")
                        inv_res_amount = float(item_in_inv.get("Amount", 0.0))

                        if inv_res_id and inv_res_owner == project_owner_for_deposit_check and inv_res_id in required_materials_for_project:
                            needed_on_site_total = float(required_materials_for_project.get(inv_res_id, 0.0))
                            on_site_already = float(site_inventory.get(inv_res_id, 0.0)) # site_inventory is defined later, this needs to be after site_inventory
                            
                            # This check needs site_inventory, which is fetched a bit later.
                            # Let's assume for now if they have it and it's required, they try to deposit.
                            # The deposit processor will handle capacity.
                            # A more refined check would be:
                            # amount_still_needed_on_site = needed_on_site_total - on_site_already
                            # amount_to_deposit_this_item = min(inv_res_amount, amount_still_needed_on_site)
                            # For simplicity, if they have it and it's required, try to deposit what they have.
                            
                            if inv_res_amount > 0.001:
                                items_to_deposit_for_this_site.append({
                                    "ResourceId": inv_res_id,
                                    "Amount": inv_res_amount, 
                                    "Owner": inv_res_owner,
                                    "AirtableRecordId": item_in_inv.get("AirtableRecordId")
                                })
                                log.info(f"      Found {inv_res_amount:.2f} of {inv_res_id} in {citizen_username}'s inventory (owned by {inv_res_owner}) to potentially deposit at {target_building_custom_id}.")
                
                if items_to_deposit_for_this_site:
                    deposit_notes_content = {
                        "items_to_deposit": items_to_deposit_for_this_site,
                        "target_building_id": target_building_custom_id
                    }
                    deposit_duration_td = timedelta(minutes=5 + len(items_to_deposit_for_this_site))
                    deposit_end_time_dt = now_utc_dt + deposit_duration_td
                    
                    deposit_activity_created = create_activity_record(
                        tables=tables, citizen_username=citizen_username, activity_type="deposit_items_at_location",
                        start_date_iso=now_utc_dt.isoformat(), end_date_iso=deposit_end_time_dt.isoformat(),
                        from_building_id=target_building_custom_id, to_building_id=target_building_custom_id,
                        details_json=json.dumps(deposit_notes_content),
                        title=f"Depositing materials at {target_building_custom_id}",
                        description=f"{citizen_username} depositing materials for project {contract_custom_id} at {target_building_custom_id}.",
                        priority_override=28 
                    )
                    if deposit_activity_created:
                        log.info(f"      Created 'deposit_items_at_location' activity for {citizen_username} at {target_building_custom_id}.")
                        
                        # Évaluer la possibilité de construction après ce dépôt simulé
                        simulated_site_inventory_map = site_inventory.copy() # site_inventory est le current_site_inventory_map
                        for item_dep in items_to_deposit_for_this_site:
                            simulated_site_inventory_map[item_dep["ResourceId"]] = simulated_site_inventory_map.get(item_dep["ResourceId"], 0.0) + item_dep["Amount"]
                        
                        log.info(f"      Inventaire simulé du site {target_building_custom_id} après dépôt: {simulated_site_inventory_map}")

                        # Recalculer max_permissible_work_minutes avec l'inventaire simulé
                        # (Logique similaire à celle utilisée plus bas pour la vérification de construction)
                        max_permissible_work_minutes_after_deposit = float(target_building_record['fields'].get('ConstructionMinutesRemaining', 0))
                        can_do_any_work_after_deposit = True
                        
                        # total_construction_time_for_building est défini plus bas, nous devons l'avoir ici.
                        # Il est calculé à partir de target_building_def.get('constructionMinutes', 0)
                        # Assurons-nous qu'il est disponible.
                        # Pour l'instant, nous allons dupliquer ce calcul ici pour la clarté, ou le déplacer plus haut.
                        # Pour cet exemple, nous supposons que total_construction_time_for_building est déjà calculé et disponible.
                        # (Il est défini plus loin dans le code original, après le bloc de dépôt)
                        # Nous allons le récupérer ici :
                        current_total_construction_time_for_building = float(target_building_def.get('constructionMinutes', 0))
                        if current_total_construction_time_for_building <= 0:
                            current_total_construction_time_for_building = 120.0 # Default

                        if not required_materials_for_project: # required_materials_for_project est défini plus haut
                            pass # Peut travailler la totalité des minutes restantes
                        else:
                            for material, needed_qty_total_for_project_val in required_materials_for_project.items():
                                needed_qty_total_for_project = float(needed_qty_total_for_project_val)
                                on_site_qty_simulated = float(simulated_site_inventory_map.get(material, 0.0))
                                
                                if on_site_qty_simulated <= 0.001 and needed_qty_total_for_project > 0:
                                    can_do_any_work_after_deposit = False; break
                                elif needed_qty_total_for_project > 0 and current_total_construction_time_for_building > 0:
                                    minutes_this_material_supports = (on_site_qty_simulated / needed_qty_total_for_project) * current_total_construction_time_for_building
                                    max_permissible_work_minutes_after_deposit = min(max_permissible_work_minutes_after_deposit, minutes_this_material_supports)
                        
                        if can_do_any_work_after_deposit and max_permissible_work_minutes_after_deposit > 1:
                            work_duration_for_chained_construct = min(60, max_permissible_work_minutes_after_deposit) # Standard 60 min chunk
                            construct_start_time_iso = deposit_activity_created['fields']['EndDate'] # Utiliser l'enregistrement retourné
                            
                            log.info(f"      Après dépôt simulé, {max_permissible_work_minutes_after_deposit:.2f} minutes de travail possibles. Tentative de chaînage de 'construct_building'.")
                            
                            construct_activity_chained = try_create_construct_building_activity(
                                tables, citizen_record, target_building_record,
                                work_duration_for_chained_construct, contract_custom_id, # contract_custom_id est en scope
                                path_data=None, # Déjà sur site
                                current_time_utc=now_utc_dt, # Pour CreatedAt
                                start_time_utc_iso=construct_start_time_iso
                            )
                            if construct_activity_chained:
                                log.info(f"      Activité 'construct_building' chaînée avec succès après dépôt pour {target_building_custom_id}.")
                            else:
                                log.warning(f"      Échec du chaînage de 'construct_building' après dépôt pour {target_building_custom_id}.")
                        else:
                            log.info(f"      Après dépôt simulé, pas assez de matériaux/temps ({max_permissible_work_minutes_after_deposit:.2f} mins) pour chaîner 'construct_building' pour {target_building_custom_id}.")
                            
                        return True # Activité de dépôt (et potentiellement de construction) créée.
            
            # Original checks continue if no deposit activity was created above
            if target_building_record['fields'].get('IsConstructed'):
                log.info(f"    Target building {target_building_custom_id} is already constructed. Marking contract {contract_custom_id} as completed if not already.")
                if contract['fields'].get('Status') != 'completed':
                    tables['contracts'].update(contract_id_airtable, {'Status': 'completed'})
                continue

            # Definitions moved earlier, this block is now empty.
            # The logic for current_construction_minutes_on_building and subsequent checks remain.
            current_construction_minutes_on_building = float(target_building_record['fields'].get('ConstructionMinutesRemaining', 0))
            if current_construction_minutes_on_building <= 0:
                log.info(f"    Site {target_building_custom_id} already constructed or no minutes remaining. Skipping contract for construction task.")
                if contract['fields'].get('Status') != 'completed':
                    tables['contracts'].update(contract_id_airtable, {'Status': 'completed'})
                continue

            # Calculate max permissible work duration based on available materials at the site
            max_permissible_work_minutes = current_construction_minutes_on_building # Start with total remaining
            total_construction_time_for_building = float(target_building_def.get('constructionMinutes', 0))

            # Get citizen's current inventory to check if they already have materials for THIS site
            citizen_inventory_for_delivery_check = get_citizen_inventory_details(tables, citizen_username)
            items_citizen_can_deliver_from_inventory: List[Dict[str, Any]] = []

            if total_construction_time_for_building <= 0:
                log.warning(f"    Building type {target_building_type_str} has invalid total_construction_time_for_building ({total_construction_time_for_building}). Using default of 120 minutes.")
                total_construction_time_for_building = 120.0 # Default construction time
            
            materials_needed_for_delivery: List[Dict[str, Any]] = []
            can_do_any_work = True # Assume can work unless a required material is totally missing

            if not required_materials_for_project:
                log.info(f"    No materials listed in constructionCosts for {target_building_type_str}. Construction can proceed for full duration if desired.")
            else:
                for material, needed_qty_total_for_project in required_materials_for_project.items():
                    on_site_qty = float(site_inventory.get(material, 0.0))
                    
                    if on_site_qty <= 0.001 and needed_qty_total_for_project > 0: # Material is required but completely missing
                        can_do_any_work = False
                        materials_needed_for_delivery.append({"type": material, "amount": needed_qty_total_for_project - on_site_qty})
                        log.info(f"      Material {material} completely missing on site. Need {needed_qty_total_for_project:.2f}.")
                        # No need to break here, collect all missing materials for potential delivery task
                    elif needed_qty_total_for_project > 0: # Material is present in some quantity
                        minutes_this_material_supports = (on_site_qty / needed_qty_total_for_project) * total_construction_time_for_building
                        max_permissible_work_minutes = min(max_permissible_work_minutes, minutes_this_material_supports)
                        if on_site_qty < needed_qty_total_for_project: # Still need more for the whole project
                             materials_needed_for_delivery.append({"type": material, "amount": needed_qty_total_for_project - on_site_qty})
                    # If needed_qty_total_for_project is 0, this material doesn't limit work duration.
            
            if not can_do_any_work:
                log.info(f"    Site {target_building_custom_id} is missing essential materials. Cannot start construction. Materials needed: {materials_needed_for_delivery}")
                # Attempt to deliver these missing materials
            elif max_permissible_work_minutes <= 1: # If less than 1 minute of work possible
                log.info(f"    Site {target_building_custom_id} has insufficient materials for a meaningful work session ({max_permissible_work_minutes:.2f} mins possible). Materials needed: {materials_needed_for_delivery}")
                # Attempt to deliver these missing materials
            else: # Sufficient materials for some work
                log.info(f"    Site {target_building_custom_id} has materials for up to {max_permissible_work_minutes:.2f} minutes of work.")
                work_duration_this_activity = min(60, max_permissible_work_minutes) # Standard 60 min chunk, limited by materials
                
                target_building_position_str = target_building_record['fields'].get('Position', '{}')
                target_building_position = json.loads(target_building_position_str) if target_building_position_str else None
                if not citizen_position or not target_building_position:
                    log.warning("    Missing citizen or target building position for construction. Skipping.")
                    continue
                
                path_data_for_construction = None
                if _calculate_distance_meters(citizen_position, target_building_position) > 20:
                    path_data_for_construction = get_path_between_points(citizen_position, target_building_position, transport_api_url)
                    if not (path_data_for_construction and path_data_for_construction.get('success')):
                        log.warning(f"    Pathfinding to site {target_building_custom_id} failed for construction. Skipping.")
                        continue
                
                if try_create_construct_building_activity(
                    tables, citizen_record, target_building_record,
                    work_duration_this_activity, contract_custom_id, path_data_for_construction,
                    current_time_utc=now_utc_dt
                ):
                    log.info(f"      Created construct_building activity for {work_duration_this_activity:.0f} minutes.")
                    return True # Activity created
                continue # Failed to create construct_building activity

            # If can_do_any_work is False OR max_permissible_work_minutes is too low, try to deliver materials_needed_for_delivery
            if materials_needed_for_delivery:
                # Check if citizen already has some of these needed materials (owned by site owner)
                if citizen_inventory_for_delivery_check:
                    log.info(f"    Checking if citizen {citizen_username} already has materials for site {target_building_custom_id} (Owner: {target_building_owner_username}).")
                    citizen_current_load_for_delivery = get_citizen_current_load(tables, citizen_username)
                    citizen_capacity_for_delivery = get_citizen_effective_carry_capacity(citizen_record)
                    remaining_carry_capacity_for_delivery = citizen_capacity_for_delivery - citizen_current_load_for_delivery

                    for needed_item_at_site in materials_needed_for_delivery:
                        needed_type = needed_item_at_site['type']
                        amount_needed_at_site_for_this_type = needed_item_at_site['amount']
                        
                        for item_in_citizen_inv in citizen_inventory_for_delivery_check:
                            if item_in_citizen_inv.get("ResourceId") == needed_type and \
                               item_in_citizen_inv.get("Owner") == target_building_owner_username and \
                               float(item_in_citizen_inv.get("Amount", 0.0)) > 0.001:
                                
                                amount_citizen_has_of_this_type = float(item_in_citizen_inv.get("Amount", 0.0))
                                amount_to_potentially_deliver_from_inv = min(amount_citizen_has_of_this_type, amount_needed_at_site_for_this_type, remaining_carry_capacity_for_delivery)
                                
                                if amount_to_potentially_deliver_from_inv > 0.001:
                                    items_citizen_can_deliver_from_inventory.append({
                                        "type": needed_type, 
                                        "amount": amount_to_potentially_deliver_from_inv
                                    })
                                    remaining_carry_capacity_for_delivery -= amount_to_potentially_deliver_from_inv
                                    log.info(f"      Citizen has {amount_to_potentially_deliver_from_inv:.2f} of {needed_type} (for site owner) to deliver from personal inventory.")
                                    # Assume one material type from inventory is enough to trigger this path for now.
                                    # More complex logic could try to fill capacity with multiple types.
                                    break # Move to next needed_item_at_site
                        if remaining_carry_capacity_for_delivery <= 0.001:
                            break # Citizen's carry capacity is full

                if items_citizen_can_deliver_from_inventory:
                    log.info(f"    Citizen {citizen_username} has materials in inventory for site {target_building_custom_id}: {items_citizen_can_deliver_from_inventory}. Creating delivery activity.")
                    # Path from current location (workshop) to site
                    path_to_site_from_workshop = get_path_between_points(citizen_position, target_building_pos, transport_api_url)
                    if path_to_site_from_workshop and path_to_site_from_workshop.get('success'):
                        # Note: resources_to_deliver are already in citizen's inventory.
                        # The processor will handle moving them from citizen to building.
                        # No decrement from workshop needed here.
                        if try_create_deliver_construction_materials_activity(
                            tables, citizen_record, workplace_record, target_building_record,
                            items_citizen_can_deliver_from_inventory, contract_custom_id, 
                            path_to_site_from_workshop, current_time_utc=now_utc_dt
                        ):
                            log.info(f"      Created deliver_construction_materials activity for {citizen_username} to deliver from personal inventory to {target_building_custom_id}.")
                            return True # Activity created
                    else:
                        log.warning(f"      Pathfinding failed for {citizen_username} to deliver from inventory to {target_building_custom_id}. Skipping this delivery option.")
                
                # If citizen doesn't have items or pathing failed, proceed to check workshop
                log.info(f"    Attempting to deliver materials to site {target_building_custom_id} from workshop: {materials_needed_for_delivery}")
                _, workshop_inventory = get_building_storage_details(tables, workplace_custom_id, workplace_operator_username)
                deliverable_from_workshop: List[Dict[str, Any]] = []
                materials_to_fetch_for_workshop: List[str] = []

                for item_needed_at_site in materials_needed_for_delivery:
                    mat_type = item_needed_at_site['type']
                    mat_amount_needed_at_site = item_needed_at_site['amount']
                    workshop_has_qty = workshop_inventory.get(mat_type, 0.0)
                    if workshop_has_qty > 0:
                        qty_to_take_from_workshop = min(workshop_has_qty, mat_amount_needed_at_site)
                        deliverable_from_workshop.append({"type": mat_type, "amount": qty_to_take_from_workshop})
                    else:
                        materials_to_fetch_for_workshop.append(mat_type)
                
                if deliverable_from_workshop:
                    # (Logic for picking up and creating deliver_construction_materials_activity - largely same as before)
                    citizen_load = get_citizen_current_load(tables, citizen_username)
                    effective_capacity = get_citizen_effective_carry_capacity(citizen_record)
                    remaining_capacity = effective_capacity - citizen_load
                    actual_resources_to_carry: List[Dict[str, Any]] = []
                    
                    for item in deliverable_from_workshop:
                        if remaining_capacity <= 0: break
                        mat_type_to_pickup = item['type']
                        amount_available_in_workshop = item['amount']
                        amount_citizen_can_take_of_this_item = min(amount_available_in_workshop, remaining_capacity)
                        if amount_citizen_can_take_of_this_item > 0:
                            if update_resource_count(tables, workplace_custom_id, 'building', workplace_operator_username, mat_type_to_pickup, -amount_citizen_can_take_of_this_item, resource_defs):
                                if update_resource_count(tables, citizen_username, 'citizen', workplace_operator_username, mat_type_to_pickup, amount_citizen_can_take_of_this_item, resource_defs, now_iso=now_utc_dt.isoformat()):
                                    actual_resources_to_carry.append({"type": mat_type_to_pickup, "amount": amount_citizen_can_take_of_this_item})
                                    remaining_capacity -= amount_citizen_can_take_of_this_item
                                else: # Failed to add to citizen, rollback workshop
                                    update_resource_count(tables, workplace_custom_id, 'building', workplace_operator_username, mat_type_to_pickup, amount_citizen_can_take_of_this_item, resource_defs)
                            else: continue # Failed to decrement from workshop
                    
                    if actual_resources_to_carry:
                        target_building_position = _get_building_position_coords(target_building_record)
                        if citizen_position and target_building_position:
                            path_to_site = get_path_between_points(citizen_position, target_building_position, transport_api_url)
                            if path_to_site and path_to_site.get('success'):
                                if try_create_deliver_construction_materials_activity(
                                    tables, citizen_record, workplace_record, target_building_record,
                                    actual_resources_to_carry, contract_custom_id, path_to_site,
                                    current_time_utc=now_utc_dt
                                ):
                                    return True # Delivery activity created
                # If workshop cannot supply, try to source directly to the construction site
                elif materials_needed_for_delivery: # This implies deliverable_from_workshop was empty or didn't lead to an activity
                    log.info(f"    Workshop {workplace_custom_id} cannot supply. Attempting to source materials directly for site {target_building_custom_id}.")
                    site_owner_username = contract['fields'].get('Buyer') # Owner of the construction site project

                    for item_needed_at_site in materials_needed_for_delivery:
                        mat_type_to_source = item_needed_at_site['type']
                        # Amount needed at site for this material to complete the project.
                        # We'll try to fetch a manageable chunk.
                        amount_total_needed_for_project_for_this_mat = item_needed_at_site['amount'] 

                        citizen_current_load = get_citizen_current_load(tables, citizen_username)
                        effective_capacity = get_citizen_effective_carry_capacity(citizen_record)
                        remaining_carry_capacity = effective_capacity - citizen_current_load
                        
                        # Fetch up to remaining capacity, or a max of 10 units, or what's needed for the project, whichever is smallest.
                        amount_to_fetch_this_run = min(amount_total_needed_for_project_for_this_mat, remaining_carry_capacity, 10.0)
                        amount_to_fetch_this_run = float(f"{amount_to_fetch_this_run:.4f}")

                        if amount_to_fetch_this_run < 0.1:
                            log.info(f"      Skipping fetch for {mat_type_to_source} to site {target_building_custom_id}: amount to fetch ({amount_to_fetch_this_run:.2f}) is too small or no carry capacity.")
                            continue

                        # Priority 1: Fetch from Galley (Import Contract for site owner)
                        import_contracts_formula = f"AND({{Type}}='import', {{Buyer}}='{_escape_airtable_value(site_owner_username)}', {{ResourceType}}='{_escape_airtable_value(mat_type_to_source)}', {{Status}}='active')"
                        active_import_contracts = tables['contracts'].all(formula=import_contracts_formula)
                        
                        activity_created_for_this_material = False
                        for import_contract in active_import_contracts:
                            galley_building_id = import_contract['fields'].get('SellerBuilding')
                            if not galley_building_id: continue
                            
                            galley_record = get_building_record(tables, galley_building_id)
                            if not galley_record or not galley_record['fields'].get('IsConstructed'): continue

                            import_contract_seller = import_contract['fields'].get('Seller')
                            if not import_contract_seller: continue
                            
                            _, galley_inventory = get_building_storage_details(tables, galley_building_id, import_contract_seller)
                            stock_in_galley = galley_inventory.get(mat_type_to_source, 0.0)
                            
                            if stock_in_galley >= amount_to_fetch_this_run:
                                log.info(f"      Sourcing {mat_type_to_source} from Galley {galley_building_id} for site {target_building_custom_id}.")
                                galley_pos = _get_building_position_coords(galley_record)
                                if citizen_position and galley_pos: # citizen_position is at workshop
                                    path_to_galley = get_path_between_points(citizen_position, galley_pos, transport_api_url)
                                    if path_to_galley and path_to_galley.get('success'):
                                        if try_create_resource_fetching_activity(
                                            tables, citizen_airtable_id, citizen_custom_id, citizen_username,
                                            import_contract['fields'].get('ContractId', import_contract['id']),
                                            galley_building_id, # From Galley
                                            target_building_custom_id, # To Construction Site (Correct: this is the actual final destination)
                                            mat_type_to_source, amount_to_fetch_this_run,
                                            path_to_galley, 
                                            now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url
                                        ):
                                            log.info(f"      Fetch from Galley {galley_building_id} to Site {target_building_custom_id} created.")
                                            return True # Activity created, exit
                                        activity_created_for_this_material = True; break 
                        if activity_created_for_this_material: continue # Next material if this one was sourced

                        # Priority 2: Fetch from Public Sell contract
                        public_sell_formula = f"AND({{Type}}='public_sell', {{ResourceType}}='{_escape_airtable_value(mat_type_to_source)}', {{EndAt}}>'{now_utc_dt.isoformat()}', {{TargetAmount}}>0)"
                        public_sell_contracts = tables['contracts'].all(formula=public_sell_formula, sort=[('PricePerResource', 'asc')])

                        for ps_contract in public_sell_contracts:
                            ps_seller_building_id = ps_contract['fields'].get('SellerBuilding')
                            if not ps_seller_building_id: continue
                            
                            ps_seller_building_rec = get_building_record(tables, ps_seller_building_id)
                            if not ps_seller_building_rec: continue

                            ps_price = float(ps_contract['fields'].get('PricePerResource', 0))
                            ps_available = float(ps_contract['fields'].get('TargetAmount', 0))
                            ps_seller_username = ps_contract['fields'].get('Seller')
                            if not ps_seller_username: continue

                            site_owner_rec = get_citizen_record(tables, site_owner_username)
                            if not site_owner_rec: break 
                            site_owner_ducats = float(site_owner_rec['fields'].get('Ducats', 0))

                            max_affordable_units = (site_owner_ducats / ps_price) if ps_price > 0 else float('inf')
                            actual_amount_to_buy = min(amount_to_fetch_this_run, ps_available, max_affordable_units)
                            actual_amount_to_buy = float(f"{actual_amount_to_buy:.4f}")

                            if actual_amount_to_buy >= 0.1:
                                _, ps_seller_inventory = get_building_storage_details(tables, ps_seller_building_id, ps_seller_username)
                                stock_at_ps_seller = ps_seller_inventory.get(mat_type_to_source, 0.0)

                                if stock_at_ps_seller >= actual_amount_to_buy:
                                    log.info(f"      Sourcing {mat_type_to_source} from Public Seller {ps_seller_building_id} for site {target_building_custom_id}.")
                                    ps_seller_pos = _get_building_position_coords(ps_seller_building_rec)
                                    if citizen_position and ps_seller_pos:
                                        path_to_ps_seller = get_path_between_points(citizen_position, ps_seller_pos, transport_api_url)
                                        if path_to_ps_seller and path_to_ps_seller.get('success'):
                                            if try_create_resource_fetching_activity(
                                                tables, citizen_airtable_id, citizen_custom_id, citizen_username,
                                                ps_contract['fields'].get('ContractId', ps_contract['id']),
                                                ps_seller_building_id, 
                                                target_building_custom_id, # To Construction Site (Correct: this is the actual final destination)
                                                mat_type_to_source, actual_amount_to_buy,
                                                path_to_ps_seller, 
                                                now_utc_dt, resource_defs, building_type_defs, now_venice_dt, transport_api_url, api_base_url
                                            ):
                                                log.info(f"      Fetch from Public Seller {ps_seller_building_id} to Site {target_building_custom_id} created.")
                                                return True # Activity created, exit
                                            activity_created_for_this_material = True; break
                        if activity_created_for_this_material: continue # Next material

                        log.info(f"      Could not find a direct source (Galley/Public_Sell) for {mat_type_to_source} for site {target_building_custom_id}.")
                    # End of loop for materials_needed_for_delivery
            # If loop completes, no activity was created for this contract. Try next contract.
            continue 
        return False # No activity created from any construction contract
    
    # --- Attempt to process active construction contracts ---
    if _try_process_active_construction_contracts():
        return True # Activity created related to a construction contract

    # --- If no contract task, check general workshop restocking needs ---
    log.info(f"No construction contract tasks for {citizen_username}. Checking workshop ({workplace_custom_id}) general restocking.")
    workplace_def = get_building_type_info(workplace_record['fields'].get('Type'), building_type_defs)

    # --- Helper function for workshop restocking ---
    def _try_workshop_restocking() -> bool:
        if not (workplace_def and 'productionInformation' in workplace_def and 'stores' in workplace_def['productionInformation']):
            return False

        workshop_stores_list = workplace_def['productionInformation']['stores']
        if not isinstance(workshop_stores_list, list): # Ensure it's a list
            log.warning(f"Workshop {workplace_custom_id} 'stores' definition is not a list: {workshop_stores_list}. Skipping restocking.")
            return False
            
        current_workshop_load, workshop_inventory = get_building_storage_details(tables, workplace_custom_id, workplace_operator_username)
        storage_capacity = float(workplace_def['productionInformation'].get('storageCapacity', 0))

        for stored_material_type_id in workshop_stores_list:
            desired_stock_level = 50.0  # Arbitrary desired stock level for each storable material
            current_stock = float(workshop_inventory.get(stored_material_type_id, 0.0))
            needed_at_workshop = desired_stock_level - current_stock
            material_name_display = resource_defs.get(stored_material_type_id, {}).get('name', stored_material_type_id)

            if needed_at_workshop <= 0.1: # If workshop has enough or more
                continue

            if (storage_capacity - current_workshop_load) < needed_at_workshop : # Not enough space for desired amount
                log.info(f"  Workshop {workplace_custom_id} needs {material_name_display}, but not enough space (Need: {needed_at_workshop:.2f}, Free: {storage_capacity - current_workshop_load:.2f}).")
                continue

            log.info(f"  Workshop {workplace_custom_id} is low on {material_name_display} (has {current_stock:.2f}, wants {desired_stock_level:.2f}, needs {needed_at_workshop:.2f}). Attempting to acquire.")

            # Priority 1: Fetch from dedicated storage contract
            storage_query_contracts = tables['contracts'].all(
                formula=f"AND({{Type}}='storage_query', {{Buyer}}='{_escape_airtable_value(workplace_operator_username)}', {{BuyerBuilding}}='{_escape_airtable_value(workplace_custom_id)}', {{ResourceType}}='{_escape_airtable_value(stored_material_type_id)}', {{Status}}='active', IS_BEFORE(NOW(), {{EndAt}}))"
            )
            if storage_query_contracts:
                sq_contract = storage_query_contracts[0]
                storage_facility_id = sq_contract['fields'].get('SellerBuilding')
                if storage_facility_id:
                    storage_facility_record = get_building_record(tables, storage_facility_id)
                    if storage_facility_record:
                        _, facility_stock_map = get_building_storage_details(tables, storage_facility_id, workplace_operator_username)
                        actual_stored_amount = float(facility_stock_map.get(stored_material_type_id, 0.0))
                        
                        if actual_stored_amount > 0:
                            amount_to_fetch_from_storage = min(needed_at_workshop, actual_stored_amount)
                            amount_to_fetch_from_storage = float(f"{amount_to_fetch_from_storage:.4f}") # Precision
                            if amount_to_fetch_from_storage >= 0.1:
                                log.info(f"    Found {actual_stored_amount:.2f} of {material_name_display} in storage {storage_facility_id}. Will fetch {amount_to_fetch_from_storage:.2f}.")
                                storage_facility_pos = _get_building_position_coords(storage_facility_record)
                                if citizen_position and storage_facility_pos: # Citizen is at workshop
                                    path_workshop_to_storage = get_path_between_points(citizen_position, storage_facility_pos, transport_api_url)
                                    
                                    if path_workshop_to_storage and path_workshop_to_storage.get('success'):
                                        log.info(f"    Path from workshop {workplace_custom_id} to storage {storage_facility_id} found.")
                                        
                                        # Create goto_location activity (workshop to storage)
                                        # Using try_create_goto_work_activity as a generic goto for now
                                        goto_storage_notes = f"Traveling to storage {storage_facility_id} to fetch {amount_to_fetch_from_storage:.2f} {material_name_display} for workshop {workplace_custom_id}."
                                        activity_goto_storage = try_create_goto_work_activity(
                                            tables, citizen_custom_id, citizen_username, citizen_airtable_id,
                                            storage_facility_id, path_workshop_to_storage,
                                            citizen_home_record=None, resource_definitions=resource_defs, is_at_home=False, 
                                            citizen_current_position_str=json.dumps(citizen_position),
                                            current_time_utc=now_utc_dt, custom_notes=goto_storage_notes,
                                            activity_type="goto_storage_facility", # More specific type
                                            details_payload=None, # No details payload, chaining is explicit
                                            start_time_utc_iso=None # Immediate start for travel
                                        )

                                        if activity_goto_storage:
                                            log.info(f"      Created 'goto_storage_facility' activity to {storage_facility_id}.")
                                            
                                            # Now create the fetch_from_storage activity, starting after arrival at storage
                                            fetch_start_time_iso = activity_goto_storage['fields']['EndDate']
                                            
                                            # Path for fetch_from_storage is from storage back to workshop
                                            workplace_pos = _get_building_position_coords(workplace_record) # workplace_record is in scope
                                            if not workplace_pos:
                                                log.error(f"      Could not get position for workshop {workplace_custom_id} for return path. Aborting fetch chain.")
                                                # Consider deleting activity_goto_storage if critical
                                                return True # Return True as an activity (goto) was created, even if chain is broken

                                            path_storage_to_workshop = get_path_between_points(storage_facility_pos, workplace_pos, transport_api_url)
                                            if not (path_storage_to_workshop and path_storage_to_workshop.get('success')):
                                                log.error(f"      Could not find path from storage {storage_facility_id} back to workshop {workplace_custom_id}. Aborting fetch chain.")
                                                # Consider deleting activity_goto_storage
                                                return True 

                                            resources_for_fetch_activity = [{"ResourceId": stored_material_type_id, "Amount": amount_to_fetch_from_storage}]
                                            
                                            fetch_activity_chained = try_create_fetch_from_storage_activity(
                                                tables=tables,
                                                citizen_record=citizen_record,
                                                from_building_record=storage_facility_record, # This is the storage
                                                to_building_record=workplace_record,         # This is the workshop
                                                resources_to_fetch=resources_for_fetch_activity,
                                                storage_query_contract_custom_id=sq_contract['fields'].get('ContractId', sq_contract['id']),
                                                path_data=path_storage_to_workshop,
                                                current_time_utc=now_utc_dt, # For CreatedAt if start_time_utc_iso is None
                                                start_time_utc_iso=fetch_start_time_iso
                                            )

                                            if fetch_activity_chained:
                                                log.info(f"      Chained 'fetch_from_storage' activity from {storage_facility_id} to {workplace_custom_id}, starting at {fetch_start_time_iso}.")
                                            else:
                                                log.warning(f"      Failed to chain 'fetch_from_storage' activity after 'goto_storage_facility'.")
                                                # The goto_storage_facility was still created.
                                            return True # Return True as the first part of the chain was created
                                        else:
                                            log.error(f"      Failed to create 'goto_storage_facility' activity to {storage_facility_id}.")
                                    else:
                                        log.warning(f"    Pathfinding from workshop {workplace_custom_id} to storage {storage_facility_id} failed.")
            
            # Priority 2: Fetch via recurrent contract
            recurrent_contracts = get_citizen_contracts(tables, workplace_operator_username) # Fetches 'recurrent'
            for contract_rec in recurrent_contracts:
                if contract_rec['fields'].get('ResourceType') == stored_material_type_id and contract_rec['fields'].get('BuyerBuilding') == workplace_custom_id:
                    from_building_id_recurrent = contract_rec['fields'].get('SellerBuilding')
                    if not from_building_id_recurrent: continue
                    from_building_rec_recurrent = get_building_record(tables, from_building_id_recurrent)
                    if not from_building_rec_recurrent: continue
                    
                    amount_recurrent = float(contract_rec['fields'].get('TargetAmount', 0) or 0)
                    amount_to_fetch_recurrent = min(needed_at_workshop, amount_recurrent)
                    
                    contract_seller_username_rec = contract_rec['fields'].get('Seller')
                    if not contract_seller_username_rec: continue
                    _, source_stock_map_rec = get_building_storage_details(tables, from_building_id_recurrent, contract_seller_username_rec)

                    if source_stock_map_rec.get(stored_material_type_id, 0.0) >= amount_to_fetch_recurrent and amount_to_fetch_recurrent > 0.01:
                        contract_custom_id_rec = contract_rec['fields'].get('ContractId', contract_rec['id'])
                        if _has_recent_failed_activity_for_contract(tables, 'fetch_resource', contract_custom_id_rec): continue
                        
                        log.info(f"    Attempting fetch via recurrent contract {contract_custom_id_rec} from {from_building_id_recurrent} for {material_name_display}.")
                        path_to_source_rec = get_path_between_points(citizen_position, _get_building_position_coords(from_building_rec_recurrent), transport_api_url)
                        if path_to_source_rec and path_to_source_rec.get('success'):
                            if try_create_resource_fetching_activity(
                                tables, citizen_airtable_id, citizen_custom_id, citizen_username,
                                contract_custom_id_rec, from_building_id_recurrent, workplace_custom_id, # ToBuilding is workshop for workshop restocking
                                stored_material_type_id, amount_to_fetch_recurrent, path_to_source_rec,
                                current_time_utc=now_utc_dt, resource_defs=resource_defs,
                                building_type_defs=building_type_defs, now_venice_dt=now_venice_dt, # Added
                                transport_api_url=transport_api_url, api_base_url=api_base_url
                            ):
                                log.info(f"      Created fetch_resource for recurrent contract {contract_custom_id_rec} to workshop {workplace_custom_id}.")
                                return True
            
            # Priority 3: Buy from public sell contract
            public_sell_formula = f"AND({{Type}}='public_sell', {{ResourceType}}='{_escape_airtable_value(stored_material_type_id)}', {{EndAt}}>'{now_utc_dt.isoformat()}', {{TargetAmount}}>0)"
            all_public_sell_for_res = tables['contracts'].all(formula=public_sell_formula)
            all_public_sell_for_res.sort(key=lambda c: float(c['fields'].get('PricePerResource', float('inf')))) # Sort by price

            for contract_ps in all_public_sell_for_res:
                seller_building_id_ps = contract_ps['fields'].get('SellerBuilding')
                if not seller_building_id_ps: continue
                seller_building_rec_ps = get_building_record(tables, seller_building_id_ps)
                if not seller_building_rec_ps: continue

                price_per_unit_ps = float(contract_ps['fields'].get('PricePerResource', 0))
                contract_amount_available_ps = float(contract_ps['fields'].get('TargetAmount', 0))
                contract_seller_username_ps = contract_ps['fields'].get('Seller')
                if not contract_seller_username_ps: continue

                # Buyer is the workshop operator
                buyer_record_for_ps = get_citizen_record(tables, workplace_operator_username)
                if not buyer_record_for_ps: continue # Should not happen if operator is valid
                buyer_ducats_ps = float(buyer_record_for_ps['fields'].get('Ducats', 0))
                
                max_affordable_units_ps = (buyer_ducats_ps / price_per_unit_ps) if price_per_unit_ps > 0 else float('inf')
                amount_to_buy_ps = min(needed_at_workshop, contract_amount_available_ps, max_affordable_units_ps)
                amount_to_buy_ps = float(f"{amount_to_buy_ps:.4f}")

                if amount_to_buy_ps >= 0.1:
                    _, source_stock_map_ps = get_building_storage_details(tables, seller_building_id_ps, contract_seller_username_ps)
                    if source_stock_map_ps.get(stored_material_type_id, 0.0) >= amount_to_buy_ps:
                        contract_custom_id_ps = contract_ps['fields'].get('ContractId', contract_ps['id'])
                        if _has_recent_failed_activity_for_contract(tables, 'fetch_resource', contract_custom_id_ps): continue

                        log.info(f"    Attempting to buy via public sell {contract_custom_id_ps} from {seller_building_id_ps} for {material_name_display}.")
                        path_to_seller_ps = get_path_between_points(citizen_position, _get_building_position_coords(seller_building_rec_ps), transport_api_url)
                        if path_to_seller_ps and path_to_seller_ps.get('success'):
                            if try_create_resource_fetching_activity(
                                tables, citizen_airtable_id, citizen_custom_id, citizen_username, # Citizen is the fetcher
                                contract_custom_id_ps, seller_building_id_ps, workplace_custom_id, # ToBuilding is workshop for workshop restocking
                                stored_material_type_id, amount_to_buy_ps, path_to_seller_ps,
                                current_time_utc=now_utc_dt, resource_defs=resource_defs,
                                building_type_defs=building_type_defs, now_venice_dt=now_venice_dt, # Added
                                transport_api_url=transport_api_url, api_base_url=api_base_url
                            ):
                                log.info(f"      Created fetch_resource for public sell contract {contract_custom_id_ps} to workshop {workplace_custom_id}.")
                                return True
            
            # Priority 4: Generic fetch (current fallback behavior)
            log.info(f"    No specific contracts found for {material_name_display}. Attempting generic fetch.")
            amount_for_generic_fetch = min(needed_at_workshop, 10.0) # Fetch a smaller, arbitrary amount
            if try_create_resource_fetching_activity(
                tables, citizen_airtable_id, citizen_custom_id, citizen_username,
                None, None, workplace_custom_id, # ToBuilding is workshop for workshop restocking
                stored_material_type_id, amount_for_generic_fetch, None,
                current_time_utc=now_utc_dt, resource_defs=resource_defs,
                building_type_defs=building_type_defs, now_venice_dt=now_venice_dt, # Added
                transport_api_url=transport_api_url, api_base_url=api_base_url
            ):
                log.info(f"      Created generic fetch_resource activity for {material_name_display} to workshop {workplace_custom_id}.")
                return True
            
            log.info(f"    Could not create any restocking activity for {material_name_display} for workshop {workplace_custom_id}.")
            # If one material cannot be restocked, we might still want to try the next one.
            # However, for simplicity, if one attempt is made (even if it fails to create), we might return.
            # The current loop structure will try the next material if no activity was created for the current one.

        return False # No restocking activity created

    # --- Attempt workshop restocking ---
    if _try_workshop_restocking():
        return True

    # --- If nothing else, idle ---
    log.info(f"No specific construction or restocking tasks for {citizen_username} at {workplace_custom_id}. Creating idle activity.")
    idle_end_time_iso = (now_utc_dt + datetime.timedelta(hours=1)).isoformat()
    try_create_idle_activity(tables, citizen_custom_id, citizen_username, citizen_airtable_id, end_date_iso=idle_end_time_iso, reason_message="Awaiting construction tasks or supplies at workshop.")
    return True

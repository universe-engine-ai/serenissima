"""
Processor for 'construct_building' activities.
Handles decrementing ConstructionMinutesRemaining on the target building.
Marks building as constructed if minutes reach zero.
"""
import logging
import json # Added
import pytz # Added
from datetime import datetime, timedelta # Updated datetime
from dateutil import parser as dateutil_parser # Added import
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

# Import necessary helpers
from backend.engine.utils.activity_helpers import ( # Grouped imports
    get_building_record, LogColors, VENICE_TIMEZONE, _escape_airtable_value,
    update_resource_count, get_building_storage_details, # Added these
    get_building_type_info # Added this
)
# Import relationship helper
from backend.engine.utils.relationship_helpers import ( # Grouped imports
    update_trust_score_for_activity, TRUST_SCORE_SUCCESS_SIMPLE, 
    TRUST_SCORE_FAILURE_SIMPLE, TRUST_SCORE_SUCCESS_MEDIUM, TRUST_SCORE_FAILURE_MEDIUM, # Added TRUST_SCORE_FAILURE_MEDIUM
    TRUST_SCORE_PROGRESS, TRUST_SCORE_SUCCESS_HIGH # TRUST_SCORE_SUCCESS_HIGH was already there
)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any], # Not directly used here but part of signature
    resource_defs: Dict[str, Any], # Not directly used here but part of signature
    api_base_url: Optional[str] = None # Added api_base_url parameter
) -> bool:
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    log.info(f"{LogColors.OKBLUE}🛠️ Processing 'construct_building' activity: {activity_guid}{LogColors.ENDC}")

    citizen_username_log = activity_fields.get('Citizen') # For logging
    target_building_custom_id = activity_fields.get('ToBuilding') # Utiliser ToBuilding comme ID du site
    
    # Calculer la durée du travail à partir de StartDate et EndDate
    start_date_str = activity_fields.get('StartDate')
    end_date_str = activity_fields.get('EndDate')
    work_duration_minutes_activity = 0
    if start_date_str and end_date_str:
        try:
            start_dt = dateutil_parser.isoparse(start_date_str)
            end_dt = dateutil_parser.isoparse(end_date_str)
            # Assurer la prise en compte du fuseau horaire (supposer UTC si non spécifié)
            if start_dt.tzinfo is None: start_dt = pytz.utc.localize(start_dt)
            if end_dt.tzinfo is None: end_dt = pytz.utc.localize(end_dt)
            duration_timedelta = end_dt - start_dt
            work_duration_minutes_activity = int(duration_timedelta.total_seconds() / 60)
        except Exception as e_date_parse:
            log.error(f"Error parsing StartDate/EndDate for activity {activity_guid} to calculate duration: {e_date_parse}")
            # work_duration_minutes_activity reste 0, ce qui échouera la vérification suivante.
    else:
        log.error(f"Activity {activity_guid} missing StartDate or EndDate. Cannot calculate work duration.")

    # ContractId in the activity is the custom string ID for construction projects
    contract_custom_id_from_activity = activity_fields.get('ContractId') 

    # Allow contract_custom_id_from_activity to be None for self-construction
    if not target_building_custom_id or work_duration_minutes_activity <= 0:
        log.error(f"Activity {activity_guid} missing target_building_custom_id ('{target_building_custom_id}') or invalid work_duration_minutes_activity ({work_duration_minutes_activity}). Aborting.")
        return False

    # Fetch contract record using its custom ID if provided
    contract_record_for_processing: Optional[Dict[str, Any]] = None
    contract_airtable_id: Optional[str] = None
    contract_buyer_username: Optional[str] = None
    construction_costs_from_contract: Dict[str, Any] = {}

    target_building_record = get_building_record(tables, target_building_custom_id)
    if not target_building_record:
        log.error(f"Target building {target_building_custom_id} for activity {activity_guid} not found.")
        return False
    
    target_building_airtable_id = target_building_record['id']
    target_building_name_log = target_building_record['fields'].get('Name', target_building_custom_id)
    site_building_type_str = target_building_record['fields'].get('Type')
    site_building_def = get_building_type_info(site_building_type_str, building_type_defs)
    if not site_building_def:
        log.error(f"Could not get building definition for site type {site_building_type_str}. Aborting.")
        return False

    if contract_custom_id_from_activity:
        try:
            formula = f"{{ContractId}} = '{_escape_airtable_value(contract_custom_id_from_activity)}'"
            contract_records_list = tables['contracts'].all(formula=formula, max_records=1)
            if not contract_records_list:
                log.error(f"Contract with custom ID '{contract_custom_id_from_activity}' not found for activity {activity_guid}.")
                return False
            contract_record_for_processing = contract_records_list[0]
            contract_airtable_id = contract_record_for_processing['id']
            contract_buyer_username = contract_record_for_processing['fields'].get('Buyer')
            if not contract_buyer_username:
                log.error(f"{LogColors.FAIL}Contract {contract_custom_id_from_activity} has no Buyer. Aborting.{LogColors.ENDC}")
                return False
            
            contract_notes_str = contract_record_for_processing['fields'].get('Notes', '{}')
            try:
                contract_notes_data = json.loads(contract_notes_str)
                if isinstance(contract_notes_data, dict) and 'constructionCosts' in contract_notes_data:
                    construction_costs_from_contract = contract_notes_data['constructionCosts']
            except json.JSONDecodeError:
                log.warning(f"Could not parse constructionCosts from contract {contract_custom_id_from_activity} notes. Notes: {contract_notes_str}")
            
            if not construction_costs_from_contract: # Fallback to building_type_def if not in contract
                construction_costs_from_contract = site_building_def.get('constructionCosts', {})
                log.info(f"Using constructionCosts from building definition for {site_building_type_str} as not found in contract notes for contract {contract_custom_id_from_activity}.")

        except Exception as e_contract_fetch:
            log.error(f"Error fetching contract by custom ID '{contract_custom_id_from_activity}': {e_contract_fetch}")
            return False
    else: # Self-construction (no contract ID)
        log.info(f"Activity {activity_guid} is for self-construction (no ContractId). Owner of building will be buyer.")
        contract_buyer_username = target_building_record['fields'].get('Owner')
        if not contract_buyer_username:
            log.error(f"{LogColors.FAIL}Target building {target_building_custom_id} for self-construction has no Owner. Aborting.{LogColors.ENDC}")
            return False
        construction_costs_from_contract = site_building_def.get('constructionCosts', {})
        log.info(f"Using constructionCosts from building definition for {site_building_type_str} for self-construction.")

    log.info(f"Processing construction for worker **{citizen_username_log}** at site **{target_building_name_log}** ({target_building_custom_id}) (Effective Buyer/Owner: **{contract_buyer_username}**).")

    try:
        current_construction_minutes_on_building = float(target_building_record['fields'].get('ConstructionMinutesRemaining', 0))
        if current_construction_minutes_on_building <= 0:
            log.info(f"Site {target_building_name_log} construction already complete. Ensuring building status reflects this.")
            if not target_building_record['fields'].get('IsConstructed'):
                tables['buildings'].update(target_building_airtable_id, {'IsConstructed': True, 'ConstructionDate': datetime.now(VENICE_TIMEZONE).isoformat(), 'ConstructionMinutesRemaining': 0})
            # If it's self-construction, there's no contract to mark as completed.
            if contract_record_for_processing and contract_record_for_processing['fields'].get('Status') != 'completed':
                tables['contracts'].update(contract_airtable_id, {'Status': 'completed'})
            return True

        actual_work_done_minutes = min(float(work_duration_minutes_activity), current_construction_minutes_on_building)
        
        total_construction_time_for_building = float(site_building_def.get('constructionMinutes', 0))
        if total_construction_time_for_building <= 0:
            log.warning(f"Building type {site_building_type_str} has invalid total_construction_time_for_building ({total_construction_time_for_building}). Using default of 120 minutes.")
            total_construction_time_for_building = 120.0 # Default construction time

        if not construction_costs_from_contract:
            log.warning(f"No construction costs found for {site_building_type_str} in contract or definition. Assuming no material consumption.")

        _, site_inventory_map = get_building_storage_details(tables, target_building_custom_id, contract_buyer_username)
        
        # --- Pre-check material availability for the potential work in this activity ---
        materials_sufficient_for_potential_work = True
        required_materials_for_this_activity_segment: Dict[str, float] = {}

        if total_construction_time_for_building > 0: # Avoid division by zero if building def is misconfigured
            for res_type, total_amount_needed_for_project_str in construction_costs_from_contract.items():
                if res_type == 'ducats': continue
                try:
                    total_amount_needed_for_project = float(total_amount_needed_for_project_str)
                except ValueError:
                    log.error(f"Invalid amount '{total_amount_needed_for_project_str}' for resource '{res_type}' in construction costs. Assuming this material is missing.")
                    materials_sufficient_for_potential_work = False; break
                if total_amount_needed_for_project <= 0: continue

                resource_consumption_rate_per_minute = total_amount_needed_for_project / total_construction_time_for_building
                resource_needed_this_activity_segment = resource_consumption_rate_per_minute * actual_work_done_minutes # actual_work_done_minutes is the potential work
                
                amount_on_site = float(site_inventory_map.get(res_type, 0.0))

                if amount_on_site < resource_needed_this_activity_segment - 0.001: # Using a small epsilon
                    log.warning(f"{LogColors.WARNING}Site {target_building_name_log} has insufficient {res_type} for planned work segment. "
                                f"Needed: {resource_needed_this_activity_segment:.2f}, Available: {amount_on_site:.2f}. Activity will fail.{LogColors.ENDC}")
                    materials_sufficient_for_potential_work = False
                    break 
                else:
                    required_materials_for_this_activity_segment[res_type] = resource_needed_this_activity_segment
        else: # total_construction_time_for_building is 0 or less, implies instant build or error in def
            log.warning(f"Building type {site_building_type_str} has total_construction_time_for_building <= 0. Assuming no material check needed for this segment if actual_work_done_minutes > 0.")
            # If actual_work_done_minutes is also 0 (e.g. building already complete), this block is fine.
            # If actual_work_done_minutes > 0 but total_construction_time_for_building is 0, it's a definition issue.
            # For safety, let's assume materials are sufficient if total time is zero, as rates can't be calculated.
            materials_sufficient_for_potential_work = True


        if not materials_sufficient_for_potential_work:
            log.error(f"{LogColors.FAIL}Construction activity {activity_guid} for {target_building_name_log} failed due to insufficient materials for the planned work duration of {actual_work_done_minutes:.2f} minutes.{LogColors.ENDC}")
            # Update trust score for failure due to lack of materials
            if contract_record_for_processing and contract_buyer_username and citizen_username_log:
                contract_seller_username = contract_record_for_processing['fields'].get('Seller')
                if contract_seller_username:
                    update_trust_score_for_activity(tables, contract_seller_username, contract_buyer_username, TRUST_SCORE_FAILURE_SIMPLE, "construction_material_shortage", False, "material_shortage", activity_record_for_kinos=activity_record)
            return False # Activity fails, no minutes deducted, no materials consumed.

        # --- Materials are sufficient, proceed with consumption and work ---
        log.info(f"All required materials are available for {actual_work_done_minutes:.2f} minutes of work on {target_building_name_log}.")
        all_resources_consumed_as_planned = True # Will remain true since we pre-checked

        for res_type, amount_to_consume in required_materials_for_this_activity_segment.items():
            if amount_to_consume > 0:
                if not update_resource_count(
                    tables, target_building_custom_id, 'building', contract_buyer_username, 
                    res_type, -amount_to_consume, resource_defs, 
                    datetime.now(VENICE_TIMEZONE).isoformat()
                ):
                    log.error(f"{LogColors.FAIL}Critical error: Failed to decrement {res_type} from site {target_building_name_log} even after pre-check. Construction integrity compromised. Aborting activity.{LogColors.ENDC}")
                    # This case should ideally not happen if pre-check is correct and no race conditions.
                    # If it does, it's a more severe failure.
                    if contract_record_for_processing and contract_buyer_username and citizen_username_log:
                         contract_seller_username = contract_record_for_processing['fields'].get('Seller')
                         if contract_seller_username:
                            update_trust_score_for_activity(tables, contract_seller_username, contract_buyer_username, TRUST_SCORE_FAILURE_MEDIUM, "construction_consumption_error", False, "system_error_consuming", activity_record_for_kinos=activity_record)
                    return False # Activity fails
                else:
                    log.info(f"Consumed {amount_to_consume:.2f} of {res_type} from site {target_building_name_log}.")
        
        new_construction_minutes_remaining = current_construction_minutes_on_building - actual_work_done_minutes
        log.info(f"Site {target_building_name_log}: Current minutes: {current_construction_minutes_on_building:.2f}, Work done (effective): {actual_work_done_minutes:.2f}, New minutes remaining: {new_construction_minutes_remaining:.2f}")

        update_payload_building = {'ConstructionMinutesRemaining': new_construction_minutes_remaining}
        
        if new_construction_minutes_remaining <= 0:
            log.info(f"{LogColors.OKGREEN}Site {target_building_name_log} construction completed!{LogColors.ENDC}")
            update_payload_building['IsConstructed'] = True
            update_payload_building['ConstructionDate'] = datetime.now(VENICE_TIMEZONE).isoformat()
            update_payload_building['ConstructionMinutesRemaining'] = 0 # Ensure it's exactly 0

            # Determine RunBy based on Owner's business count
            building_owner_username = target_building_record['fields'].get('Owner')
            final_run_by_on_completion: Optional[str] = None

            if building_owner_username:
                log.info(f"Determining RunBy for completed building {target_building_name_log} (Owner: {building_owner_username}).")
                owner_business_buildings_formula = f"AND({{RunBy}}='{_escape_airtable_value(building_owner_username)}', {{Category}}='business')"
                try:
                    owner_business_buildings = tables['buildings'].all(formula=owner_business_buildings_formula)
                    num_businesses_run_by_owner = len(owner_business_buildings)
                    if num_businesses_run_by_owner < 10:
                        log.info(f"Owner {building_owner_username} runs {num_businesses_run_by_owner} businesses. Setting RunBy to Owner.")
                        final_run_by_on_completion = building_owner_username
                    else:
                        log.info(f"Owner {building_owner_username} runs {num_businesses_run_by_owner} businesses (limit 10). Setting RunBy to None.")
                        final_run_by_on_completion = None # Explicitly None
                except Exception as e_count_owner_buildings:
                    log.error(f"Error counting business buildings for owner {building_owner_username}: {e_count_owner_buildings}. Defaulting RunBy to Owner for safety.")
                    final_run_by_on_completion = building_owner_username # Fallback to owner
            else:
                log.warning(f"Building {target_building_name_log} has no Owner. RunBy will be None.")
                final_run_by_on_completion = None
            
            update_payload_building['RunBy'] = final_run_by_on_completion
            log.info(f"RunBy for completed building {target_building_name_log} set to: {final_run_by_on_completion}")
            
            if contract_record_for_processing and contract_record_for_processing['fields'].get('Status') != 'completed':
                tables['contracts'].update(contract_airtable_id, {'Status': 'completed'})
                log.info(f"Marked contract {contract_custom_id_from_activity} as completed.")
            
            # Trust score for project completion (if there was a contract)
            if contract_record_for_processing and contract_buyer_username and citizen_username_log:
                contract_seller_username = contract_record_for_processing['fields'].get('Seller')
                if contract_seller_username: # Worker (citizen_username_log) works for Seller
                    update_trust_score_for_activity(tables, contract_seller_username, contract_buyer_username, TRUST_SCORE_SUCCESS_HIGH, "construction_project_completed", True, "building_finished", activity_record_for_kinos=activity_record)
        else: # Construction still in progress
            # Trust score for progress (if there was a contract)
            if contract_record_for_processing and contract_buyer_username and citizen_username_log:
                contract_seller_username = contract_record_for_processing['fields'].get('Seller')
                if contract_seller_username:
                    trust_change_for_progress = TRUST_SCORE_PROGRESS if all_resources_consumed_as_planned else TRUST_SCORE_PROGRESS * 0.5
                    update_trust_score_for_activity(tables, contract_seller_username, contract_buyer_username, trust_change_for_progress, "construction_progress", True, f"progress_{actual_work_done_minutes:.0f}min", activity_record_for_kinos=activity_record)

        tables['buildings'].update(target_building_airtable_id, update_payload_building)
        log.info(f"Updated construction minutes for site {target_building_name_log}.")
        
        return True

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error processing 'construct_building' activity {activity_guid}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        # Trust score update on failure (if there was a contract)
        if contract_record_for_processing and contract_buyer_username and citizen_username_log:
            contract_seller_username = contract_record_for_processing['fields'].get('Seller')
            if contract_seller_username:
                 update_trust_score_for_activity(tables, contract_seller_username, contract_buyer_username, TRUST_SCORE_FAILURE_MEDIUM, "construction_processing", False, "system_error", activity_record_for_kinos=activity_record)
        return False

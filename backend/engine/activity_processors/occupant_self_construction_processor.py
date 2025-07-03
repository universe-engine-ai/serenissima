"""
Processor for 'occupant_self_construction' activities.
Handles an occupant working on the construction of the building they occupy.
"""
import logging
import json
import pytz
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser
from typing import Dict, Any, Optional

# Import necessary helpers
from backend.engine.utils.activity_helpers import (
    get_building_record, LogColors, VENICE_TIMEZONE, _escape_airtable_value,
    update_resource_count, get_building_storage_details,
    get_building_type_info
)

log = logging.getLogger(__name__)

def process_occupant_self_construction_fn(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    resource_defs: Dict[str, Any],
    api_base_url: Optional[str] = None # Parameter part of standard signature
) -> bool:
    activity_fields = activity_record.get('fields', {})
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    log.info(f"{LogColors.OKBLUE}🛠️ Processing 'occupant_self_construction' activity: {activity_guid}{LogColors.ENDC}")

    citizen_username = activity_fields.get('Citizen')
    # For self-construction, ToBuilding is the site being worked on.
    target_building_custom_id = activity_fields.get('ToBuilding')

    if not citizen_username or not target_building_custom_id:
        log.error(f"Activity {activity_guid} missing Citizen ('{citizen_username}') or ToBuilding ('{target_building_custom_id}'). Aborting.")
        return False

    # Calculate work duration from activity's StartDate and EndDate
    start_date_str = activity_fields.get('StartDate')
    end_date_str = activity_fields.get('EndDate')
    work_duration_minutes_activity = 0
    if start_date_str and end_date_str:
        try:
            start_dt = dateutil_parser.isoparse(start_date_str)
            end_dt = dateutil_parser.isoparse(end_date_str)
            if start_dt.tzinfo is None: start_dt = pytz.utc.localize(start_dt)
            if end_dt.tzinfo is None: end_dt = pytz.utc.localize(end_dt)
            duration_timedelta = end_dt - start_dt
            work_duration_minutes_activity = int(duration_timedelta.total_seconds() / 60)
        except Exception as e_date_parse:
            log.error(f"Error parsing StartDate/EndDate for activity {activity_guid} to calculate duration: {e_date_parse}")
            return False # Cannot proceed without valid duration
    else:
        log.error(f"Activity {activity_guid} missing StartDate or EndDate. Cannot calculate work duration.")
        return False

    if work_duration_minutes_activity <= 0:
        log.error(f"Activity {activity_guid} has invalid work_duration_minutes_activity ({work_duration_minutes_activity}). Aborting.")
        return False

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

    # For self-construction, the owner of materials is the citizen doing the work (who should also be owner/occupant of the building)
    material_owner_username = citizen_username
    log.info(f"Processing self-construction for worker **{citizen_username}** at site **{target_building_name_log}** ({target_building_custom_id}). Material owner: **{material_owner_username}**.")

    try:
        current_construction_minutes_on_building = float(target_building_record['fields'].get('ConstructionMinutesRemaining', 0))
        if current_construction_minutes_on_building <= 0:
            log.info(f"Site {target_building_name_log} construction already complete. Ensuring building status reflects this.")
            if not target_building_record['fields'].get('IsConstructed'):
                tables['buildings'].update(target_building_airtable_id, {'IsConstructed': True, 'ConstructionDate': datetime.now(VENICE_TIMEZONE).isoformat(), 'ConstructionMinutesRemaining': 0})
            return True

        actual_work_done_minutes = min(float(work_duration_minutes_activity), current_construction_minutes_on_building)
        
        total_construction_time_for_building = float(site_building_def.get('constructionMinutes', 0))
        if total_construction_time_for_building <= 0:
            log.warning(f"Building type {site_building_type_str} has invalid total_construction_time_for_building ({total_construction_time_for_building}). Using default of 120 minutes.")
            total_construction_time_for_building = 120.0

        construction_costs = site_building_def.get('constructionCosts', {})
        if not construction_costs:
            log.warning(f"No construction costs found for {site_building_type_str} in definition. Assuming no material consumption.")

        _, site_inventory_map = get_building_storage_details(tables, target_building_custom_id, material_owner_username)
        
        materials_sufficient_for_potential_work = True
        required_materials_for_this_activity_segment: Dict[str, float] = {}

        if total_construction_time_for_building > 0 and construction_costs:
            for res_type, total_amount_needed_for_project_str in construction_costs.items():
                if res_type == 'ducats': continue
                try:
                    total_amount_needed_for_project = float(total_amount_needed_for_project_str)
                except ValueError:
                    log.error(f"Invalid amount '{total_amount_needed_for_project_str}' for resource '{res_type}' in construction costs. Assuming material missing.")
                    materials_sufficient_for_potential_work = False; break
                if total_amount_needed_for_project <= 0: continue

                resource_consumption_rate_per_minute = total_amount_needed_for_project / total_construction_time_for_building
                resource_needed_this_activity_segment = resource_consumption_rate_per_minute * actual_work_done_minutes
                
                amount_on_site = float(site_inventory_map.get(res_type, 0.0))

                if amount_on_site < resource_needed_this_activity_segment - 0.001: # Epsilon for float comparison
                    log.warning(f"{LogColors.WARNING}Site {target_building_name_log} has insufficient {res_type} for self-construction. "
                                f"Needed: {resource_needed_this_activity_segment:.2f}, Available: {amount_on_site:.2f}. Activity will fail.{LogColors.ENDC}")
                    materials_sufficient_for_potential_work = False
                    break 
                else:
                    required_materials_for_this_activity_segment[res_type] = resource_needed_this_activity_segment
        elif not construction_costs: # No material costs defined
             log.info(f"No material costs defined for {site_building_type_str}. Assuming no materials needed for this segment.")
             materials_sufficient_for_potential_work = True
        else: # total_construction_time_for_building is 0 or less
            log.warning(f"Building type {site_building_type_str} has total_construction_time_for_building <= 0. Assuming no material check needed for this segment.")
            materials_sufficient_for_potential_work = True


        if not materials_sufficient_for_potential_work:
            log.error(f"{LogColors.FAIL}Self-construction activity {activity_guid} for {target_building_name_log} failed due to insufficient materials for {actual_work_done_minutes:.2f} minutes.{LogColors.ENDC}")
            return False

        for res_type, amount_to_consume in required_materials_for_this_activity_segment.items():
            if amount_to_consume > 0:
                if not update_resource_count(
                    tables, target_building_custom_id, 'building', material_owner_username, 
                    res_type, -amount_to_consume, resource_defs, 
                    datetime.now(VENICE_TIMEZONE).isoformat()
                ):
                    log.error(f"{LogColors.FAIL}Critical error: Failed to decrement {res_type} from site {target_building_name_log} during self-construction. Aborting.{LogColors.ENDC}")
                    return False
                else:
                    log.info(f"Consumed {amount_to_consume:.2f} of {res_type} from site {target_building_name_log} for self-construction.")
        
        new_construction_minutes_remaining = current_construction_minutes_on_building - actual_work_done_minutes
        log.info(f"Site {target_building_name_log} (self-construction): Current minutes: {current_construction_minutes_on_building:.2f}, Work done: {actual_work_done_minutes:.2f}, New minutes remaining: {new_construction_minutes_remaining:.2f}")

        update_payload_building = {'ConstructionMinutesRemaining': new_construction_minutes_remaining}
        
        if new_construction_minutes_remaining <= 0:
            log.info(f"{LogColors.OKGREEN}Site {target_building_name_log} (self-construction) completed!{LogColors.ENDC}")
            update_payload_building['IsConstructed'] = True
            update_payload_building['ConstructionDate'] = datetime.now(VENICE_TIMEZONE).isoformat()
            update_payload_building['ConstructionMinutesRemaining'] = 0
            
            current_owner = target_building_record['fields'].get('Owner')
            # If the citizen doing the work is the owner, they become RunBy.
            # If they are an occupant but not owner, the owner (if any) becomes RunBy.
            # If no owner and citizen is occupant, citizen becomes RunBy.
            if current_owner == citizen_username:
                update_payload_building['RunBy'] = citizen_username
                log.info(f"RunBy for self-completed building {target_building_name_log} set to owner/constructor: {citizen_username}")
            elif current_owner: # Owner exists and is different from constructor
                update_payload_building['RunBy'] = current_owner
                log.info(f"RunBy for self-completed building {target_building_name_log} set to owner: {current_owner} (constructor was {citizen_username})")
            else: # No owner, constructor (occupant) becomes RunBy
                update_payload_building['RunBy'] = citizen_username
                log.info(f"RunBy for self-completed building {target_building_name_log} (no owner) set to constructor/occupant: {citizen_username}")

        tables['buildings'].update(target_building_airtable_id, update_payload_building)
        log.info(f"Updated construction minutes for site {target_building_name_log} (self-construction).")
        
        return True

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error processing 'occupant_self_construction' activity {activity_guid}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pyairtable import Table
import pytz # Added for timezone handling
from dateutil import parser as dateutil_parser # Added for robust date parsing

# Import helpers and creators
from backend.engine.utils.activity_helpers import get_citizen_record, LogColors
from backend.engine.activity_creators import try_create_eat_at_tavern_activity


log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Any,
    resource_defs: Any,
    api_base_url: Optional[str] = None # Added api_base_url for signature consistency
) -> bool:
    """
    Process a goto_location activity.
    
    This is a generic movement activity that can be used for various purposes.
    The specific purpose is determined by the Details field, which should contain
    an 'activityType' field indicating what this movement is for.
    
    Args:
        tables: Dictionary of Airtable tables
        activity_record: The activity record to process
        building_type_defs: Building type definitions
        resource_defs: Resource type definitions
        
    Returns:
        bool: True if the activity was processed successfully, False otherwise
    """
    fields = activity_record.get('fields', {})
    activity_type = fields.get('Type')
    citizen = fields.get('Citizen')
    to_building = fields.get('ToBuilding')
    path_str = fields.get('Path')
    notes_str = fields.get('Notes') # This was already 'Notes'
    
    if activity_type != "goto_location":
        log.error(f"Expected activity type 'goto_location', got '{activity_type}'")
        return False
    
    if not citizen:
        log.error("Missing citizen in goto_location activity")
        return False
    
    try:
        # Parse the path
        path = []
        if path_str and path_str.strip():
            try:
                parsed_path_candidate = json.loads(path_str)
                if isinstance(parsed_path_candidate, list):
                    path = parsed_path_candidate
                else:
                    log.warning(f"Path string for activity {fields.get('ActivityId', 'N/A')} (Citizen: {citizen}) did not parse to a list: '{path_str[:100]}...'. Using empty path.")
            except json.JSONDecodeError:
                log.warning(f"Could not parse Path as JSON for activity {fields.get('ActivityId', 'N/A')} (Citizen: {citizen}). Path: '{path_str[:100]}...'. Using empty path.")
        
        # Parse notes (details)
        details = {}
        if notes_str and notes_str.strip():
            try:
                parsed_details_candidate = json.loads(notes_str)
                if isinstance(parsed_details_candidate, dict):
                    details = parsed_details_candidate
                else:
                    log.warning(f"Parsed Notes (details) is not a dictionary for activity {fields.get('ActivityId', 'N/A')} (Citizen: {citizen}). Notes: '{notes_str[:100]}...'. Using empty details.")
                    # details remains {}
            except json.JSONDecodeError:
                log.warning(f"Could not parse Notes (details) as JSON for activity {fields.get('ActivityId', 'N/A')} (Citizen: {citizen}). Notes: '{notes_str[:100]}...'. Using empty details.")
                # details remains {}
        
        # Get the purpose of this movement
        purpose = details.get("activityType", "unknown") # 'details' here is the parsed JSON from 'Notes'
        
        # Update citizen position to the destination
        if path and len(path) > 0:
            # Get the last point in the path as the destination
            destination = path[-1]
            
            # Update citizen position
            citizen_formula = f"{{Username}}='{citizen}'"
            citizen_records = tables['citizens'].all(formula=citizen_formula, max_records=1)
            
            if citizen_records:
                citizen_record = citizen_records[0]
                tables['citizens'].update(citizen_record['id'], {
                    'Position': json.dumps(destination)
                })
                
                log.info(f"Updated position for citizen {citizen} to {destination}")
                
                # If there's a ToBuilding, update the citizen's Point field
                if to_building:
                    # For now, we don't set the Point field as it's not clear what it should be
                    # This would require knowing which specific point on the building the citizen is at
                    pass
                
                # Log the completion based on the purpose
                log_message_arrival = f"Citizen {citizen} has arrived at destination"
                if purpose != "unknown":
                    log_message_arrival += f" for purpose: {purpose}"
                log.info(f"{LogColors.OKGREEN}{log_message_arrival}{LogColors.ENDC}")

                # --- Chaining logic for action_on_arrival ---
                action_to_take = details.get("action_on_arrival")
                if action_to_take:
                    log.info(f"{LogColors.OKCYAN}Citizen {citizen} arrived. Action on arrival: {action_to_take}{LogColors.ENDC}")
                    
                    activity_end_date_iso = fields.get('EndDate')
                    if not activity_end_date_iso:
                        log.error(f"{LogColors.FAIL}Cannot chain activity for {citizen}: EndDate of goto_location is missing.{LogColors.ENDC}")
                        return True # goto_location itself succeeded

                    try:
                        chained_activity_current_time_utc = dateutil_parser.isoparse(activity_end_date_iso)
                        if chained_activity_current_time_utc.tzinfo is None:
                            chained_activity_current_time_utc = pytz.utc.localize(chained_activity_current_time_utc)
                    except Exception as e_parse_enddate:
                        log.error(f"{LogColors.FAIL}Error parsing EndDate '{activity_end_date_iso}' for chaining: {e_parse_enddate}. Cannot chain activity.{LogColors.ENDC}")
                        return True # goto_location itself succeeded

                    citizen_custom_id_for_chain = citizen_record['fields'].get('CitizenId')
                    citizen_airtable_id_for_chain = citizen_record['id']

                    if not citizen_custom_id_for_chain:
                        log.error(f"{LogColors.FAIL}Cannot chain activity for {citizen}: CitizenId is missing from citizen record.{LogColors.ENDC}")
                        return True

                    if action_to_take == "eat_at_tavern":
                        eat_specific_details = details.get("eat_details_on_arrival", {}) 
                        target_building_id_for_eat = details.get("target_building_id_on_arrival", to_building) # Fallback to goto's ToBuilding

                        if not target_building_id_for_eat:
                            log.error(f"{LogColors.FAIL}Cannot chain 'eat_at_tavern' for {citizen}: target_building_id_on_arrival is missing and ToBuilding of goto_location is also missing.{LogColors.ENDC}")
                            return True

                        log.info(f"Attempting to chain 'eat_at_tavern' for {citizen} at {target_building_id_for_eat} with details: {eat_specific_details}")
                        
                        chained_eat_activity = try_create_eat_at_tavern_activity(
                            tables=tables,
                            citizen_custom_id=citizen_custom_id_for_chain,
                            citizen_username=citizen, 
                            citizen_airtable_id=citizen_airtable_id_for_chain,
                            tavern_custom_id=target_building_id_for_eat,
                            current_time_utc=chained_activity_current_time_utc,
                            resource_defs=resource_defs, # Pass resource_defs
                            start_time_utc_iso=activity_end_date_iso, 
                            details_payload=eat_specific_details
                        )
                        if chained_eat_activity:
                            log.info(f"{LogColors.OKGREEN}Successfully chained 'eat_at_tavern' activity for {citizen}.{LogColors.ENDC}")
                        else:
                            log.warning(f"{LogColors.WARNING}Failed to chain 'eat_at_tavern' activity for {citizen}.{LogColors.ENDC}")
                    # Example placeholder for other actions:
                    # elif action_to_take == "another_action_type":
                    #     action_specific_details = details.get("another_action_details_key", {})
                    #     target_building_id_for_action = details.get("target_building_id_for_another_action", to_building)
                    #     # ... call appropriate creator ...
                    else:
                        log.warning(f"{LogColors.WARNING}Unknown action_on_arrival: '{action_to_take}' for citizen {citizen}. No chained activity created.{LogColors.ENDC}")
                
                return True # Original goto_location activity processed successfully
            else:
                log.error(f"{LogColors.FAIL}Citizen {citizen} not found{LogColors.ENDC}")
                return False
        else:
            log.error(f"No valid path found in goto_location activity for citizen {citizen}")
            return False
    except Exception as e:
        log.error(f"Error processing goto_location activity for citizen {citizen}: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False

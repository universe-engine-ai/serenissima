"""
Processor for 'goto_construction_site' activities.
When the citizen arrives at the construction site, this processor
marks the activity as processed. If 'Notes' indicate a follow-up action
like 'construct_building', it creates that activity.
"""
import logging
import json
import datetime
import pytz # For timezone handling if needed by creator
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

from backend.engine.utils.activity_helpers import get_building_record, get_citizen_record, LogColors
from backend.engine.activity_creators.construct_building_creator import try_create_construct_building_activity

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Optional[Dict[str, Any]] = None, # Now optional
    resource_defs: Optional[Dict[str, Any]] = None,      # Now optional
    api_base_url: Optional[str] = None                 # Now optional
) -> bool:
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    log.info(f"{LogColors.OKBLUE}🚶 Processing 'goto_construction_site' activity: {activity_guid}{LogColors.ENDC}")

    citizen_username = activity_fields.get('Citizen')
    arrival_site_custom_id = activity_fields.get('ToBuilding') 
    
    if not all([citizen_username, arrival_site_custom_id]):
        log.error(f"Activity {activity_guid} missing crucial data (Citizen or ToBuilding). Aborting.")
        return False

    # Fetching arrival_site_record_data can be useful for logging or other checks if needed.
    arrival_site_record_data = get_building_record(tables, arrival_site_custom_id)
    if not arrival_site_record_data:
        log.error(f"Arrival site {arrival_site_custom_id} not found for activity {activity_guid}. Aborting.")
        # This might indicate an issue if the subsequent 'construct_building' activity relies on this site.
        return False 
    
    arrival_site_name_log = arrival_site_record_data['fields'].get('Name', arrival_site_custom_id)
    log.info(f"Citizen **{citizen_username}** arrived at site **{arrival_site_name_log}** ({arrival_site_custom_id}).")
    
    # The logic for creating a follow-up 'construct_building' activity is removed.
    # It's assumed that the 'construct_building' activity was already created as part of a chain
    # by the construct_building_creator.py.
    # This processor now simply marks the travel as complete.
    # The next activity in the chain (construct_building) will be picked up by the main
    # processActivities loop when its StartDate is reached.

    log.info(f"Notes field content for {activity_guid}: '{activity_fields.get('Notes', '')}'")
    log.info(f"{LogColors.OKGREEN}Successfully processed 'goto_construction_site' activity {activity_guid} for {citizen_username} at {arrival_site_custom_id}. The next activity in the chain (if any) will proceed based on its schedule.{LogColors.ENDC}")
    return True

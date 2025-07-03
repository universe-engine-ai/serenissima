"""
Creator for 'construct_building' activities.
"""
import logging
import datetime
import time
import json
import uuid
import pytz # For timezone handling
from typing import Dict, Optional, Any

from backend.engine.utils.activity_helpers import get_building_record, get_closest_building_to_position, get_citizen_inventory_details # Import helpers

log = logging.getLogger(__name__)

def try_create_construct_building_activity(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],         # Citizen performing the construction
    target_building_record: Dict[str, Any], # Construction site
    work_duration_minutes: int,             # How long this specific activity will last
    contract_custom_id_or_airtable_id: str, # Can be custom ContractId or Airtable ID depending on context
    path_data: Optional[Dict],               # Path from citizen's current location to site (if not already there)
    current_time_utc: datetime.datetime,     # Added current_time_utc
    start_time_utc_iso: Optional[str] = None # New parameter
) -> Optional[Dict]:
    """
    Creates a 'construct_building' activity.
    If path_data is provided, it's a travel activity to the site first.
    If path_data is None, citizen is assumed to be at the site, and it's a direct work activity.
    This creator will now create a chain of activities if travel is needed:
    1. goto_construction_site
    2. construct_building
    It returns the first activity of the chain (goto_construction_site or construct_building).
    """
    citizen_custom_id = citizen_record['fields'].get('CitizenId')
    citizen_username = citizen_record['fields'].get('Username')
    target_building_custom_id = target_building_record['fields'].get('BuildingId')

    # contract_custom_id_or_airtable_id is now optional for self-construction
    if not all([citizen_custom_id, citizen_username, target_building_custom_id]):
        log.error("Missing crucial data (citizen_custom_id, citizen_username, or target_building_custom_id) for creating construct_building activity chain.")
        return None

    contract_display_for_log = contract_custom_id_or_airtable_id if contract_custom_id_or_airtable_id else "self-construction"
    log.info(f"Attempting to create construction activity chain for {citizen_username} at {target_building_custom_id} (Contract/Context: {contract_display_for_log}).")

    activities_created = []

    try:
        # Determine start and end times for travel (if any) and work
        travel_end_time_iso: Optional[str] = None
        work_start_time_iso: str
        work_end_time_iso: str

        if path_data and path_data.get('success') and path_data.get('timing', {}).get('durationSeconds', 0) > 30:
            # Travel is involved
            travel_start_time_iso = start_time_utc_iso if start_time_utc_iso else path_data.get('timing', {}).get('startDate', current_time_utc.isoformat())
            travel_end_time_iso = path_data.get('timing', {}).get('endDate', (datetime.datetime.fromisoformat(travel_start_time_iso.replace("Z", "+00:00")) + datetime.timedelta(seconds=path_data['timing']['durationSeconds'])).isoformat())
            
            work_start_time_iso = travel_end_time_iso
            work_start_dt = datetime.datetime.fromisoformat(work_start_time_iso.replace("Z", "+00:00"))
            if work_start_dt.tzinfo is None: work_start_dt = pytz.UTC.localize(work_start_dt)
            work_end_time_iso = (work_start_dt + datetime.timedelta(minutes=work_duration_minutes)).isoformat()
            
            # Create goto_construction_site activity
            goto_payload: Dict[str, Any] = {
                "Citizen": citizen_username, "Status": "created",
                "ContractId": contract_custom_id_or_airtable_id,
                "ActivityId": f"goto_constr_site_{citizen_custom_id}_{uuid.uuid4()}",
                "Type": "goto_construction_site",
                "ToBuilding": target_building_custom_id,
                "Path": json.dumps(path_data.get('path', [])),
                "StartDate": travel_start_time_iso,
                "EndDate": travel_end_time_iso,
                "CreatedAt": current_time_utc.isoformat(),
                "Notes": f"🚶 Traveling to construction site {target_building_custom_id} to work. Contract: {contract_custom_id_or_airtable_id}.",
                "Description": f"Traveling to site: {target_building_record['fields'].get('Name', target_building_custom_id)}"
            }
            # Determine FromBuilding for goto_construction_site
            from_building_custom_id_for_goto = None
            citizen_pos_str = citizen_record['fields'].get('Position')
            if citizen_pos_str:
                try:
                    citizen_coords = json.loads(citizen_pos_str)
                    if citizen_coords and 'lat' in citizen_coords and 'lng' in citizen_coords:
                        closest_building_to_start = get_closest_building_to_position(tables, citizen_coords)
                        if closest_building_to_start:
                            from_building_custom_id_for_goto = closest_building_to_start['fields'].get('BuildingId')
                except json.JSONDecodeError: pass # Ignore if position is not valid JSON
            if from_building_custom_id_for_goto:
                goto_payload["FromBuilding"] = from_building_custom_id_for_goto
            
            # Determine TransportMode
            transport_mode = "walk" # Default
            path_points_list = path_data.get('path', [])
            if isinstance(path_points_list, list):
                for point in path_points_list:
                    if isinstance(point, dict) and point.get('transportMode') == 'gondola':
                        transport_mode = 'gondola'; break
            goto_payload["TransportMode"] = transport_mode
            if path_data.get('transporter'):
                goto_payload["Transporter"] = path_data.get('transporter')

            citizen_inventory = get_citizen_inventory_details(tables, citizen_username)
            resources_being_carried = [{"ResourceId": item["ResourceId"], "Amount": item["Amount"]} for item in citizen_inventory if item.get("ResourceId") and item.get("Amount", 0) > 0]
            goto_payload["Resources"] = json.dumps(resources_being_carried) if resources_being_carried else "[]"

            created_goto_activity = tables['activities'].create(goto_payload)
            if created_goto_activity and created_goto_activity.get('id'):
                log.info(f"Successfully created 'goto_construction_site' activity: {created_goto_activity['id']}")
                activities_created.append(created_goto_activity)
            else:
                log.error("Failed to create 'goto_construction_site' activity in Airtable.")
                return None # Fail the whole chain if travel cannot be created
        else:
            # No travel involved or path_data missing/invalid
            work_start_time_iso = start_time_utc_iso if start_time_utc_iso else current_time_utc.isoformat()
            work_start_dt = datetime.datetime.fromisoformat(work_start_time_iso.replace("Z", "+00:00"))
            if work_start_dt.tzinfo is None: work_start_dt = pytz.UTC.localize(work_start_dt)
            work_end_time_iso = (work_start_dt + datetime.timedelta(minutes=work_duration_minutes)).isoformat()

        # Create construct_building activity
        construct_payload: Dict[str, Any] = {
            "Citizen": citizen_username, "Status": "created",
            "ContractId": contract_custom_id_or_airtable_id,
            "ActivityId": f"construct_bld_{citizen_custom_id}_{uuid.uuid4()}",
            "Type": "construct_building",
            # "BuildingToConstruct": target_building_custom_id, # Champ incorrect, ToBuilding est utilisé
            # "WorkDurationMinutes": work_duration_minutes, # Ce champ n'existe pas dans Airtable ACTIVITIES
            "FromBuilding": target_building_custom_id, 
            "ToBuilding": target_building_custom_id,   
            "Path": "[]", 
            "StartDate": work_start_time_iso,
            "EndDate": work_end_time_iso,
            "CreatedAt": current_time_utc.isoformat(), # All activities in chain created at same time
            "Notes": f"🛠️ Working on construction at site {target_building_custom_id} for {work_duration_minutes} minutes. Contract: {contract_custom_id_or_airtable_id}.",
            "Description": f"Working on construction: {target_building_record['fields'].get('Name', target_building_custom_id)}"
        }
        
        created_construct_activity = tables['activities'].create(construct_payload)
        if created_construct_activity and created_construct_activity.get('id'):
            log.info(f"Successfully created 'construct_building' activity: {created_construct_activity['id']}")
            activities_created.append(created_construct_activity)
        else:
            log.error("Failed to create 'construct_building' activity in Airtable.")
            # If travel was created but work failed, we might need to delete the travel activity.
            # For now, return None, indicating overall failure.
            if activities_created: # If goto was created
                try: tables['activities'].delete(activities_created[0]['id'])
                except: pass # Ignore error during cleanup
            return None

        return activities_created[0] if activities_created else None # Return the first activity of the chain

    except Exception as e:
        log_activity_type_for_error = 'construct_building_chain'
        log.error(f"Error creating {log_activity_type_for_error} activity: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None

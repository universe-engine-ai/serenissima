#!/usr/bin/env python3
"""
Job Seeking Activity Handler
Allows unemployed citizens to actively search for nearby employment opportunities

Activity Type: job_seeking
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import requests
import os

from backend.engine.handlers.base_handler import BaseActivityHandler
from backend.engine.utils.activity_helpers import LogColors, create_error_response
from backend.engine.utils.distance_helpers import calculate_distance, estimate_walking_time, find_nearest_locations

log = logging.getLogger(__name__)

class JobSeekingHandler(BaseActivityHandler):
    """
    Handles job seeking activities for unemployed citizens.
    Citizens can actively look for work between daily job assignments.
    """
    
    def can_handle(self, activity_type: str) -> bool:
        """Check if this handler can process the activity type."""
        return activity_type == "job_seeking"
    
    def process(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a job seeking activity.
        
        Expected activity data:
        {
            "max_distance": 1500,  # Maximum distance willing to travel (meters)
            "min_wage": 10        # Minimum acceptable wage (optional)
        }
        """
        try:
            log.info(f"{LogColors.HEADER}Processing job seeking activity{LogColors.ENDC}")
            
            # Get citizen data
            citizen_id = activity['fields'].get('Citizen')[0]
            citizen = self.tables['citizens'].get(citizen_id)
            
            if not citizen:
                return create_error_response("Citizen not found", {"citizen_id": citizen_id})
            
            citizen_username = citizen['fields'].get('Username')
            citizen_name = f"{citizen['fields'].get('FirstName', '')} {citizen['fields'].get('LastName', '')}"
            citizen_pos = citizen['fields'].get('Position')
            
            if not citizen_pos:
                return create_error_response("Citizen has no position data", {"citizen": citizen_username})
            
            # Check if citizen is already employed
            current_workplace = self._get_citizen_workplace(citizen_username)
            if current_workplace:
                log.info(f"{citizen_name} is already employed at {current_workplace}")
                return {
                    "success": True,
                    "message": "Already employed",
                    "data": {"current_workplace": current_workplace}
                }
            
            # Get activity parameters
            activity_data = activity['fields'].get('Data', {})
            max_distance = activity_data.get('max_distance', 1500)  # Default 1.5km
            min_wage = activity_data.get('min_wage', 0)
            
            # Find available businesses
            available_businesses = self._get_available_businesses()
            if not available_businesses:
                return {
                    "success": True,
                    "message": "No available businesses found",
                    "data": {"businesses_checked": 0}
                }
            
            # Find nearby businesses
            nearby_businesses = find_nearest_locations(
                citizen_pos,
                available_businesses,
                max_distance=max_distance
            )
            
            # Filter by minimum wage
            suitable_businesses = [
                (biz, dist) for biz, dist in nearby_businesses
                if float(biz.get('wages', 0)) >= min_wage
            ]
            
            if not suitable_businesses:
                return {
                    "success": True,
                    "message": f"No suitable jobs found within {max_distance}m",
                    "data": {
                        "businesses_checked": len(nearby_businesses),
                        "max_distance": max_distance,
                        "min_wage": min_wage
                    }
                }
            
            # Try to get the best job (closest that meets criteria)
            best_business, distance = suitable_businesses[0]
            walking_time = estimate_walking_time(distance)
            
            # Attempt to claim the job
            success = self._assign_job_to_citizen(citizen, best_business)
            
            if success:
                log.info(f"{LogColors.SUCCESS}{citizen_name} found job at {best_business.get('name')} "
                        f"({walking_time:.1f} min walk){LogColors.ENDC}")
                
                # Create notification for citizen
                self._create_notification(
                    citizen_username,
                    f"🎉 You found employment at **{best_business.get('name')}**! "
                    f"It's a {walking_time:.0f} minute walk from your location.",
                    {
                        "event_type": "job_found",
                        "building_name": best_business.get('name'),
                        "wages": best_business.get('wages'),
                        "walking_time": round(walking_time)
                    }
                )
                
                return {
                    "success": True,
                    "message": f"Found job at {best_business.get('name')}",
                    "data": {
                        "building_id": best_business.get('id'),
                        "building_name": best_business.get('name'),
                        "wages": best_business.get('wages'),
                        "distance": round(distance),
                        "walking_time": round(walking_time)
                    }
                }
            else:
                # Job was taken by someone else
                return {
                    "success": True,
                    "message": "Job was already taken",
                    "data": {
                        "attempted_building": best_business.get('name'),
                        "businesses_checked": len(suitable_businesses)
                    }
                }
                
        except Exception as e:
            log.error(f"Error in job seeking: {str(e)}")
            return create_error_response(f"Job seeking failed: {str(e)}")
    
    def _get_citizen_workplace(self, username: str) -> Optional[str]:
        """Check if citizen is currently employed."""
        try:
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:3000")
            response = requests.get(f"{api_base_url}/api/buildings", timeout=10)
            response.raise_for_status()
            
            buildings = response.json().get('buildings', [])
            for building in buildings:
                if building.get('occupant') == username:
                    return building.get('name', building.get('id'))
            
            return None
            
        except Exception as e:
            log.error(f"Error checking employment status: {e}")
            return None
    
    def _get_available_businesses(self) -> list:
        """Get list of businesses without occupants."""
        try:
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:3000")
            response = requests.get(f"{api_base_url}/api/buildings", timeout=10)
            response.raise_for_status()
            
            buildings = response.json().get('buildings', [])
            
            # Filter for available businesses with position data
            available = []
            for building in buildings:
                if (building.get('category') == 'business' and
                    not building.get('occupant') and
                    building.get('position')):
                    available.append(building)
            
            return available
            
        except Exception as e:
            log.error(f"Error fetching available businesses: {e}")
            return []
    
    def _assign_job_to_citizen(self, citizen: Dict, business: Dict) -> bool:
        """Attempt to assign the job to the citizen."""
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            # Get Airtable record for the building
            building_id = business.get('id')
            formula = f"{{BuildingId}} = '{_escape_airtable_value(building_id)}'"
            records = self.tables['buildings'].all(formula=formula, max_records=1)
            
            if not records:
                log.error(f"Building {building_id} not found in Airtable")
                return False
            
            building_record = records[0]
            
            # Check if still available (race condition check)
            if building_record['fields'].get('Occupant'):
                log.info("Building already has an occupant")
                return False
            
            # Assign the citizen
            citizen_username = citizen['fields'].get('Username')
            self.tables['buildings'].update(building_record['id'], {
                'Occupant': citizen_username
            })
            
            # Notify building owner
            building_operator = business.get('runBy') or business.get('owner')
            if building_operator:
                citizen_name = f"{citizen['fields'].get('FirstName', '')} {citizen['fields'].get('LastName', '')}"
                self._create_notification(
                    building_operator,
                    f"🏢 **{citizen_name}** has been hired at your {business.get('name')}",
                    {
                        "event_type": "employee_hired",
                        "citizen_name": citizen_name,
                        "building_name": business.get('name')
                    }
                )
            
            return True
            
        except Exception as e:
            log.error(f"Error assigning job: {e}")
            return False
    
    def _create_notification(self, citizen: str, content: str, details: Dict):
        """Create a notification for a citizen."""
        try:
            self.tables['notifications'].create({
                "Type": "job_seeking",
                "Content": content,
                "Details": str(details),
                "CreatedAt": datetime.now().isoformat(),
                "Citizen": citizen
            })
        except Exception as e:
            log.error(f"Error creating notification: {e}")


# Register the handler
def register():
    """Register this handler with the system."""
    return JobSeekingHandler()
#!/usr/bin/env python3
"""
Welfare Activity Selector Enhancement
Modifies AI activity selection to automatically trigger porter work for hungry+poor citizens

This enhancement adds to the existing activity selection logic to check:
1. If citizen is hungry (hunger > 50)
2. If citizen is poor (ducats < 50)
3. If porter work is available from Consiglio or trusted nobles
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
import json

log = logging.getLogger(__name__)


class WelfareActivitySelector:
    """
    Enhances activity selection to include welfare porter work options
    """
    
    def __init__(self, tables: Dict[str, Any], api_base_url: str):
        self.tables = tables
        self.api_base_url = api_base_url
        self.hunger_threshold = 50
        self.wealth_threshold = 50
    
    def should_trigger_welfare_work(self, citizen: Dict[str, Any]) -> bool:
        """
        Check if citizen qualifies for welfare porter work.
        
        Args:
            citizen: Citizen record from database
            
        Returns:
            True if citizen should be offered welfare work
        """
        # Get citizen fields
        fields = citizen.get('fields', {})
        hunger = fields.get('Hunger', 0)
        ducats = fields.get('Ducats', 0)
        
        # Check thresholds
        is_hungry = hunger > self.hunger_threshold
        is_poor = ducats < self.wealth_threshold
        
        if is_hungry and is_poor:
            log.info(f"Citizen {fields.get('Username')} qualifies for welfare work: "
                    f"hunger={hunger}, ducats={ducats}")
            return True
        
        return False
    
    def find_welfare_porter_work(self, citizen: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find available porter work from Consiglio or trusted nobles.
        
        Returns:
            Dict with porter work details or None if no work available
        """
        # Priority 1: Check Consiglio dei Dieci needs
        consiglio_work = self._find_consiglio_logistics_needs()
        if consiglio_work:
            return consiglio_work
        
        # Priority 2: Check top trusted nobles
        trusted_work = self._find_trusted_noble_logistics_needs()
        if trusted_work:
            return trusted_work
        
        return None
    
    def _find_consiglio_logistics_needs(self) -> Optional[Dict[str, Any]]:
        """
        Find logistics needs from Consiglio dei Dieci.
        Looks for:
        1. Resources at Consiglio buildings that need moving
        2. Import contracts that need fulfillment
        3. Distribution needs to other buildings
        """
        try:
            # Find Consiglio buildings with resources
            consiglio_buildings = self._get_consiglio_buildings()
            
            for building in consiglio_buildings:
                building_id = building['fields'].get('BuildingId')
                
                # Check for resources that need moving
                resources = self._get_building_resources(building_id)
                
                for resource in resources:
                    # Find destination for this resource type
                    destination = self._find_resource_destination(
                        resource['Type'],
                        building_id,
                        'ConsiglioDeiDieci'
                    )
                    
                    if destination:
                        # Create porter work
                        return {
                            'employer': 'ConsiglioDeiDieci',
                            'cargo_type': resource['Type'],
                            'cargo_amount': min(resource['Quantity'], 50),  # Reasonable load
                            'from_building': building_id,
                            'to_building': destination['BuildingId'],
                            'payment_type': 'food_voucher'
                        }
            
            return None
            
        except Exception as e:
            log.error(f"Error finding Consiglio logistics: {e}")
            return None
    
    def _find_trusted_noble_logistics_needs(self) -> Optional[Dict[str, Any]]:
        """
        Find logistics needs from nobles most trusted by Consiglio.
        """
        try:
            # Get top 5 citizens trusted by Consiglio
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            formula = (
                f"AND("
                f"{{FromCitizen}}='ConsiglioDeiDieci', "
                f"{{TrustLevel}}>50"
                f")"
            )
            
            relationships = self.tables['relationships'].all(
                formula=formula,
                sort=['-TrustLevel'],
                max_records=5
            )
            
            for rel in relationships:
                noble_username = rel['fields'].get('ToCitizen')
                
                # Check noble's buildings for logistics needs
                noble_buildings = self._get_citizen_buildings(noble_username)
                
                for building in noble_buildings:
                    work = self._check_building_logistics_needs(
                        building,
                        noble_username
                    )
                    
                    if work:
                        return work
            
            return None
            
        except Exception as e:
            log.error(f"Error finding noble logistics: {e}")
            return None
    
    def _get_consiglio_buildings(self) -> List[Dict]:
        """Get all buildings owned or operated by Consiglio."""
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            formula = (
                f"OR("
                f"{{Owner}}='ConsiglioDeiDieci', "
                f"{{RunBy}}='ConsiglioDeiDieci'"
                f")"
            )
            
            return self.tables['buildings'].all(formula=formula)
            
        except Exception as e:
            log.error(f"Error fetching Consiglio buildings: {e}")
            return []
    
    def _get_citizen_buildings(self, username: str) -> List[Dict]:
        """Get all buildings owned by a citizen."""
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            formula = f"{{Owner}}='{_escape_airtable_value(username)}'"
            return self.tables['buildings'].all(formula=formula)
            
        except Exception as e:
            log.error(f"Error fetching citizen buildings: {e}")
            return []
    
    def _get_building_resources(self, building_id: str) -> List[Dict]:
        """Get resources at a building that might need moving."""
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            formula = f"{{Location}}='{_escape_airtable_value(building_id)}'"
            resources = self.tables['resources'].all(formula=formula)
            
            # Filter for significant quantities worth moving
            return [
                {
                    'Type': r['fields'].get('Type'),
                    'Quantity': r['fields'].get('Quantity', 0)
                }
                for r in resources
                if r['fields'].get('Quantity', 0) > 10  # Worth moving
            ]
            
        except Exception as e:
            log.error(f"Error fetching building resources: {e}")
            return []
    
    def _find_resource_destination(self, resource_type: str, 
                                  current_location: str,
                                  owner: str) -> Optional[Dict]:
        """
        Find appropriate destination for a resource type.
        E.g., grain to warehouse, stone to construction site, etc.
        """
        try:
            from backend.engine.utils.activity_helpers import _escape_airtable_value
            
            # Find buildings that store this resource type
            # This would need the building type definitions
            
            # For now, find any warehouse owned by the same owner
            formula = (
                f"AND("
                f"{{Owner}}='{_escape_airtable_value(owner)}', "
                f"{{Type}}='warehouse', "
                f"{{BuildingId}}!='{_escape_airtable_value(current_location)}'"
                f")"
            )
            
            warehouses = self.tables['buildings'].all(formula=formula, max_records=1)
            
            if warehouses:
                return {'BuildingId': warehouses[0]['fields'].get('BuildingId')}
            
            return None
            
        except Exception as e:
            log.error(f"Error finding resource destination: {e}")
            return None
    
    def _check_building_logistics_needs(self, building: Dict,
                                       owner: str) -> Optional[Dict]:
        """Check if a building has logistics needs."""
        building_id = building['fields'].get('BuildingId')
        resources = self._get_building_resources(building_id)
        
        for resource in resources:
            destination = self._find_resource_destination(
                resource['Type'],
                building_id,
                owner
            )
            
            if destination:
                return {
                    'employer': owner,
                    'cargo_type': resource['Type'],
                    'cargo_amount': min(resource['Quantity'], 50),
                    'from_building': building_id,
                    'to_building': destination['BuildingId'],
                    'payment_type': 'food_voucher'
                }
        
        return None
    
    def create_welfare_porter_activity(self, citizen_id: str,
                                      porter_work: Dict[str, Any]) -> Dict:
        """
        Create a welfare porter activity for the citizen.
        
        Args:
            citizen_id: Airtable ID of the citizen
            porter_work: Dict with work details
            
        Returns:
            Created activity record
        """
        try:
            activity_data = {
                'Type': 'welfare_porter',
                'Citizen': [citizen_id],
                'Status': 'pending',
                'Data': json.dumps(porter_work),
                'CreatedAt': datetime.now().isoformat()
            }
            
            result = self.tables['activities'].create(activity_data)
            
            log.info(f"Created welfare porter activity for citizen {citizen_id}")
            
            return result
            
        except Exception as e:
            log.error(f"Error creating welfare activity: {e}")
            return {}


def enhance_activity_selection(citizen: Dict[str, Any],
                              tables: Dict[str, Any],
                              api_base_url: str) -> Optional[Dict[str, Any]]:
    """
    Enhancement function to be integrated into AI activity selection.
    
    This function should be called at the beginning of activity selection
    to check if welfare work should be offered.
    
    Args:
        citizen: Citizen record
        tables: Airtable tables reference
        api_base_url: API base URL
        
    Returns:
        Activity dict if welfare work should be done, None otherwise
    """
    selector = WelfareActivitySelector(tables, api_base_url)
    
    # Check if citizen qualifies
    if not selector.should_trigger_welfare_work(citizen):
        return None
    
    # Find available work
    work = selector.find_welfare_porter_work(citizen)
    if not work:
        log.info(f"No welfare work available for {citizen['fields'].get('Username')}")
        return None
    
    # Return activity data for creation
    return {
        'type': 'welfare_porter',
        'data': work,
        'priority': 'high'  # Hunger is urgent
    }


if __name__ == "__main__":
    # Test the selector
    print("Welfare Activity Selector ready for integration")
    print("Add enhance_activity_selection() to AI activity selection logic")
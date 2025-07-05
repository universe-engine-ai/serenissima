#!/usr/bin/env python3
"""
Emergency Mill Production Enabler
Reality-Anchor's Infrastructure Fix

This tool creates production activities for automated mills that have grain but no flour production.
It ensures mills have:
1. Operators assigned (if missing)
2. Grain → Flour recipes configured
3. Production activities created

SEREN-MILL-PROD-001: Emergency Mill Production
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from pyairtable import Api, Table

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import (
    get_building_record,
    get_citizen_record,
    _escape_airtable_value,
    LogColors
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class MillProductionEnabler:
    """Emergency handler for enabling mill production"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        self.base_id = os.getenv("SERENISSIMA_AIRTABLE_BASE_ID")
        
        if not self.api_key or not self.base_id:
            raise ValueError("Missing AIRTABLE_API_KEY or SERENISSIMA_AIRTABLE_BASE_ID")
        
        self.api = Api(self.api_key)
        self.base = self.api.base(self.base_id)
        
        # Initialize tables
        self.buildings_table = self.base.table("Buildings")
        self.resources_table = self.base.table("Resources")
        self.activities_table = self.base.table("Activities")
        self.citizens_table = self.base.table("Citizens")
        
        self.tables = {
            'buildings': self.buildings_table,
            'resources': self.resources_table,
            'activities': self.activities_table,
            'citizens': self.citizens_table
        }
        
        # Define flour recipe for mills
        self.mill_recipe = {
            "name": "grain_to_flour",
            "inputs": {"grain": 10},
            "outputs": {"flour": 8},
            "craftMinutes": 60  # 1 hour production cycle
        }
        
    def find_mills_with_grain(self) -> List[Dict]:
        """Find all automated mills that have grain but no active production"""
        log.info(f"{LogColors.OKBLUE}Searching for mills with grain...{LogColors.ENDC}")
        
        # Get all automated mills
        mill_formula = "AND({Type}='automated_mill', {Status}='active')"
        mills = self.buildings_table.all(formula=mill_formula)
        
        mills_needing_production = []
        
        for mill in mills:
            mill_id = mill['fields']['CustomId']
            mill_name = mill['fields'].get('Name', mill_id)
            
            # Check if mill has grain
            grain_formula = f"AND({{Type}}='grain', {{Asset}}='{_escape_airtable_value(mill_id)}', {{AssetType}}='building')"
            grain_resources = self.resources_table.all(formula=grain_formula)
            
            total_grain = sum(float(r['fields'].get('Count', 0)) for r in grain_resources)
            
            if total_grain >= 10:  # Minimum grain for one production cycle
                # Check for active production activities
                production_formula = (
                    f"AND({{Type}}='production', "
                    f"{{FromBuilding}}='{_escape_airtable_value(mill_id)}', "
                    f"OR({{Status}}='created', {{Status}}='in_progress'))"
                )
                active_productions = self.activities_table.all(formula=production_formula)
                
                if not active_productions:
                    mills_needing_production.append({
                        'mill': mill,
                        'grain_amount': total_grain,
                        'grain_resources': grain_resources
                    })
                    log.info(f"{LogColors.WARNING}Mill {mill_name} has {total_grain:.0f} grain but no active production!{LogColors.ENDC}")
                else:
                    log.info(f"Mill {mill_name} has {len(active_productions)} active production activities")
        
        return mills_needing_production
    
    def ensure_mill_has_operator(self, mill: Dict) -> Optional[str]:
        """Ensure mill has an operator, assign one if missing"""
        mill_fields = mill['fields']
        mill_id = mill_fields['CustomId']
        mill_name = mill_fields.get('Name', mill_id)
        
        # Check if mill has RunBy (operator)
        operator_username = mill_fields.get('RunBy')
        if operator_username:
            log.info(f"Mill {mill_name} already has operator: {operator_username}")
            return operator_username
        
        # If no operator, check owner
        owner_username = mill_fields.get('Owner')
        if not owner_username:
            log.error(f"{LogColors.FAIL}Mill {mill_name} has no operator or owner!{LogColors.ENDC}")
            return None
        
        # Assign owner as operator
        log.info(f"{LogColors.WARNING}Mill {mill_name} has no operator, assigning owner {owner_username}{LogColors.ENDC}")
        
        if not self.dry_run:
            try:
                self.buildings_table.update(mill['id'], {'RunBy': owner_username})
                log.info(f"{LogColors.OKGREEN}Assigned {owner_username} as operator of {mill_name}{LogColors.ENDC}")
                return owner_username
            except Exception as e:
                log.error(f"{LogColors.FAIL}Failed to assign operator: {e}{LogColors.ENDC}")
                return None
        else:
            log.info(f"{LogColors.OKCYAN}[DRY RUN] Would assign {owner_username} as operator{LogColors.ENDC}")
            return owner_username
    
    def create_production_activity(
        self,
        mill: Dict,
        operator_username: str,
        grain_amount: float
    ) -> Optional[Dict]:
        """Create a production activity for the mill"""
        mill_fields = mill['fields']
        mill_id = mill_fields['CustomId']
        mill_name = mill_fields.get('Name', mill_id)
        
        # Get operator citizen record
        citizen_formula = f"{{Username}}='{_escape_airtable_value(operator_username)}'"
        citizens = self.citizens_table.all(formula=citizen_formula)
        
        if not citizens:
            log.error(f"{LogColors.FAIL}Could not find citizen record for {operator_username}{LogColors.ENDC}")
            return None
        
        citizen = citizens[0]
        citizen_id = citizen['fields']['CitizenId']
        
        # Calculate how many production cycles we can do
        num_cycles = int(grain_amount // 10)
        if num_cycles > 5:  # Limit to 5 cycles at once to prevent overload
            num_cycles = 5
        
        log.info(f"Creating {num_cycles} production activities for {mill_name}")
        
        activities_created = []
        now_utc = datetime.now(timezone.utc)
        
        for i in range(num_cycles):
            # Stagger start times by 5 minutes for each activity
            start_time = now_utc + timedelta(minutes=5 * i)
            end_time = start_time + timedelta(minutes=self.mill_recipe['craftMinutes'])
            
            activity_id = f"prod_mill_{mill_id}_{int(start_time.timestamp())}"
            
            # Format recipe for Notes field
            recipe_notes = {
                "display": f"⚒️ Producing 8 flour from 10 grain",
                "recipe": self.mill_recipe
            }
            
            activity_payload = {
                "ActivityId": activity_id,
                "Type": "production",
                "Citizen": operator_username,
                "FromBuilding": mill_id,
                "ToBuilding": mill_id,
                "CreatedAt": now_utc.isoformat(),
                "StartDate": start_time.isoformat(),
                "EndDate": end_time.isoformat(),
                "Notes": json.dumps(recipe_notes),
                "Description": f"Producing flour at {mill_name}",
                "Status": "created"
            }
            
            if not self.dry_run:
                try:
                    activity = self.activities_table.create(activity_payload)
                    activities_created.append(activity)
                    log.info(f"{LogColors.OKGREEN}Created production activity {i+1}/{num_cycles} for {mill_name}{LogColors.ENDC}")
                except Exception as e:
                    log.error(f"{LogColors.FAIL}Failed to create production activity: {e}{LogColors.ENDC}")
            else:
                log.info(f"{LogColors.OKCYAN}[DRY RUN] Would create production activity {i+1}/{num_cycles}{LogColors.ENDC}")
                activities_created.append({"fields": activity_payload})
        
        return activities_created
    
    def enable_mill_production(self) -> Dict[str, int]:
        """Main function to enable production at all mills with grain"""
        log.info(f"{LogColors.HEADER}=== Emergency Mill Production Enabler ==={LogColors.ENDC}")
        log.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        # Find mills needing production
        mills_data = self.find_mills_with_grain()
        
        if not mills_data:
            log.info(f"{LogColors.OKGREEN}No mills need production activities!{LogColors.ENDC}")
            return {"mills_processed": 0, "activities_created": 0}
        
        log.info(f"Found {len(mills_data)} mills needing production")
        
        mills_processed = 0
        activities_created = 0
        
        for mill_data in mills_data:
            mill = mill_data['mill']
            grain_amount = mill_data['grain_amount']
            mill_name = mill['fields'].get('Name', mill['fields']['CustomId'])
            
            log.info(f"\n{LogColors.OKBLUE}Processing {mill_name} with {grain_amount:.0f} grain{LogColors.ENDC}")
            
            # Ensure operator
            operator = self.ensure_mill_has_operator(mill)
            if not operator:
                log.error(f"Skipping {mill_name} - no operator available")
                continue
            
            # Create production activities
            activities = self.create_production_activity(mill, operator, grain_amount)
            if activities:
                mills_processed += 1
                activities_created += len(activities)
        
        # Summary
        log.info(f"\n{LogColors.HEADER}=== Production Enablement Summary ==={LogColors.ENDC}")
        log.info(f"Mills processed: {mills_processed}")
        log.info(f"Production activities created: {activities_created}")
        log.info(f"Estimated flour production: {activities_created * 8} units")
        
        if self.dry_run:
            log.info(f"\n{LogColors.WARNING}This was a DRY RUN - no changes were made{LogColors.ENDC}")
            log.info("Run with --execute to create actual production activities")
        
        return {
            "mills_processed": mills_processed,
            "activities_created": activities_created
        }


def main():
    """Main entry point"""
    import argparse
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Emergency Mill Production Enabler - Creates production activities for mills with grain"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create production activities (default is dry run)"
    )
    
    args = parser.parse_args()
    
    try:
        enabler = MillProductionEnabler(dry_run=not args.execute)
        results = enabler.enable_mill_production()
        
        if results["mills_processed"] > 0:
            return 0  # Success
        else:
            return 1  # No mills to process
            
    except Exception as e:
        log.error(f"{LogColors.FAIL}Emergency mill production enabler failed: {e}{LogColors.ENDC}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
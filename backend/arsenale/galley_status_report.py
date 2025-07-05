#!/usr/bin/env python3
"""
Galley Status Report for La Serenissima
Quick diagnostic tool to check galley cargo status
"""

import os
import sys
import json
import logging
from datetime import datetime
import pytz
from typing import Dict, Optional
from collections import defaultdict

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

# Import utility functions
from backend.engine.utils.activity_helpers import LogColors, log_header, VENICE_TIMEZONE, _escape_airtable_value

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger("galley_status")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials")
        return None
        
    try:
        api = Api(api_key)
        return {
            'buildings': api.table(base_id, 'BUILDINGS'),
            'resources': api.table(base_id, 'RESOURCES'),
            'citizens': api.table(base_id, 'CITIZENS'),
            'activities': api.table(base_id, 'ACTIVITIES')
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        return None

def main():
    """Generate galley status report."""
    log_header("🚢 GALLEY STATUS REPORT 🚢", LogColors.HEADER)
    
    tables = initialize_airtable()
    if not tables:
        return
    
    now_venice = datetime.now(VENICE_TIMEZONE)
    log.info(f"Report Time: {now_venice.strftime('%Y-%m-%d %H:%M:%S')} Venice Time\n")
    
    # Get all merchant galleys
    try:
        galleys = tables['buildings'].all(formula="{Type}='merchant_galley'")
        log.info(f"{LogColors.OKBLUE}Total Merchant Galleys: {len(galleys)}{LogColors.ENDC}")
        
        constructed = sum(1 for g in galleys if g['fields'].get('IsConstructed'))
        under_construction = len(galleys) - constructed
        
        log.info(f"  ✅ Arrived (constructed): {constructed}")
        log.info(f"  🚧 In transit: {under_construction}\n")
        
        # Analyze cargo
        total_cargo = defaultdict(float)
        galleys_with_grain = 0
        total_grain = 0.0
        empty_galleys = 0
        
        log.info(f"{LogColors.OKBLUE}Cargo Analysis:{LogColors.ENDC}")
        
        for galley in galleys:
            if not galley['fields'].get('IsConstructed'):
                continue
                
            galley_id = galley['fields'].get('BuildingId')
            galley_name = galley['fields'].get('Name', galley_id)
            
            # Get resources in this galley
            resource_formula = f"AND({{Asset}}='{_escape_airtable_value(galley_id)}', {{AssetType}}='building')"
            resources = tables['resources'].all(formula=resource_formula)
            
            if not resources:
                empty_galleys += 1
                continue
            
            galley_cargo = defaultdict(float)
            for resource in resources:
                res_type = resource['fields'].get('Type', 'unknown')
                count = float(resource['fields'].get('Count', 0))
                galley_cargo[res_type] += count
                total_cargo[res_type] += count
            
            # Check for grain
            if 'grain' in galley_cargo:
                galleys_with_grain += 1
                total_grain += galley_cargo['grain']
                log.info(f"  🌾 {galley_name}: {galley_cargo['grain']:.1f} grain")
        
        log.info(f"\n{LogColors.OKGREEN}Summary:{LogColors.ENDC}")
        log.info(f"  Empty galleys: {empty_galleys}")
        log.info(f"  Galleys with grain: {galleys_with_grain}")
        log.info(f"  Total grain in galleys: {total_grain:.1f}")
        
        if total_cargo:
            log.info(f"\n{LogColors.OKBLUE}All Cargo Types:{LogColors.ENDC}")
            for res_type, amount in sorted(total_cargo.items(), key=lambda x: x[1], reverse=True):
                log.info(f"  {res_type}: {amount:.1f}")
        
        # Check for active unloading activities
        pickup_formula = "AND({Type}='pickup_from_galley', OR({Status}='created', {Status}='in_progress'))"
        active_pickups = tables['activities'].all(formula=pickup_formula)
        
        log.info(f"\n{LogColors.OKBLUE}Active Unloading:{LogColors.ENDC}")
        log.info(f"  Active pickup activities: {len(active_pickups)}")
        
        # Check citizen hunger
        hungry_formula = "{Hunger}>70"
        hungry_citizens = tables['citizens'].all(formula=hungry_formula)
        starving_formula = "{Hunger}>90"
        starving_citizens = tables['citizens'].all(formula=starving_formula)
        
        log.info(f"\n{LogColors.WARNING}Hunger Crisis:{LogColors.ENDC}")
        log.info(f"  Hungry citizens (>70): {len(hungry_citizens)}")
        log.info(f"  Starving citizens (>90): {len(starving_citizens)}")
        
        # Recommendations
        log.info(f"\n{LogColors.HEADER}Recommendations:{LogColors.ENDC}")
        if galleys_with_grain > 0 and len(starving_citizens) > 0:
            log.info(f"  🚨 URGENT: {galleys_with_grain} galleys have grain while {len(starving_citizens)} citizens starve!")
            log.info(f"  💡 Run emergency_galley_unloader.py for direct transfer")
            log.info(f"  💡 Run galley_unloading_orchestrator.py to assign citizens")
        elif total_grain > 0:
            log.info(f"  ⚠️  {total_grain:.1f} grain available in galleys")
            log.info(f"  💡 Consider running unloading scripts")
        else:
            log.info(f"  ✅ No urgent galley issues detected")
            
    except Exception as e:
        log.error(f"Error generating report: {e}")

if __name__ == "__main__":
    main()
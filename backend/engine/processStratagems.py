#!/usr/bin/env python3
"""
Process Stratagems script for La Serenissima.

This script:
1. Fetches all stratagems that are 'active' and not yet expired.
2. For each active stratagem, calls its corresponding processor function.
3. Updates the stratagem status to "executed", "failed", or keeps it "active"
   if it's a continuous effect that needs periodic re-evaluation.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
import pytz
from typing import Dict, List, Optional, Any

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api, Table
from dotenv import load_dotenv

from backend.engine.utils.activity_helpers import (
    LogColors,
    log_header,
    _escape_airtable_value,
    VENICE_TIMEZONE,
    get_resource_types_from_api,
    get_building_types_from_api
)

# Import stratagem processors
from backend.engine.stratagem_processors import (
    process_undercut_stratagem,
    process_coordinate_pricing_stratagem,
    process_hoard_resource_stratagem,
    process_political_campaign_stratagem,
    process_reputation_assault_stratagem,
    process_emergency_liquidation_stratagem,
    process_cultural_patronage_stratagem,
    process_information_network_stratagem,
    process_maritime_blockade_stratagem,
    process_theater_conspiracy_stratagem,
    process_printing_propaganda_stratagem,
    process_cargo_mishap_stratagem,
    process_marketplace_gossip_stratagem,
    process_joint_venture_stratagem
    # Import other stratagem processors here
)

# Placeholder processor for monopoly_pricing
def process_monopoly_pricing_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'monopoly_pricing' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    # Mark as executed to prevent re-processing if it's a one-shot conceptual action
    # Or keep active if it's meant to be continuous and re-evaluated
    # For now, let's assume it's a one-shot setup for "Coming Soon"
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

# Placeholder processor for reputation_boost
def process_reputation_boost_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'reputation_boost' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

# Placeholder processor for canal_mugging
def process_canal_mugging_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'canal_mugging' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

# Placeholder processor for burglary
def process_burglary_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'burglary' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

# Placeholder processor for employee_corruption
def process_employee_corruption_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'employee_corruption' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

# Placeholder processor for arson
def process_arson_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'arson' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

# Placeholder processor for charity_distribution
def process_charity_distribution_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'charity_distribution' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

# Placeholder processor for festival_organisation
def process_festival_organisation_stratagem(
    tables: Dict[str, Table], 
    stratagem_record: Dict, 
    resource_defs: Dict, 
    building_type_defs: Dict, 
    api_base_url: str
) -> bool:
    log.warning(f"{LogColors.WARNING}Processing for 'festival_organisation' stratagem (ID: {stratagem_record['id']}) is not yet implemented. Marking as executed for now.{LogColors.ENDC}")
    tables['stratagems'].update(stratagem_record['id'], {'Status': 'executed', 'Notes': 'Coming Soon - Marked as executed.'})
    return True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("process_stratagems")

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3000")

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not api_key or not base_id:
        log.error(f"{LogColors.FAIL}Airtable API Key or Base ID not configured.{LogColors.ENDC}")
        return None
    
    try:
        api = Api(api_key)
        tables = {
            'stratagems': api.table(base_id, 'STRATAGEMS'),
            'contracts': api.table(base_id, 'CONTRACTS'), # Needed by undercut processor
            'citizens': api.table(base_id, 'CITIZENS'),   # Potentially needed by processors
            'buildings': api.table(base_id, 'BUILDINGS'), # Potentially needed by processors
            'resources': api.table(base_id, 'RESOURCES')  # Potentially needed by processors
        }
        log.info(f"{LogColors.OKGREEN}Airtable connection successful for ProcessStratagems.{LogColors.ENDC}")
        return tables
    except Exception as e:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable for ProcessStratagems: {e}{LogColors.ENDC}")
        return None

def get_active_stratagems(tables: Dict[str, Table]) -> List[Dict]:
    """Fetch active stratagems that are not yet expired."""
    now_utc_iso = datetime.now(timezone.utc).isoformat()
    
    formula = f"AND({{Status}} = 'active', OR({{ExpiresAt}} IS NULL, {{ExpiresAt}} > '{now_utc_iso}'))"
    log.info(f"{LogColors.OKBLUE}Fetching active stratagems with formula: {formula}{LogColors.ENDC}")
    
    try:
        stratagems = tables['stratagems'].all(formula=formula)
        log.info(f"{LogColors.OKBLUE}Found {len(stratagems)} active stratagems.{LogColors.ENDC}")
        return stratagems
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error fetching active stratagems: {e}{LogColors.ENDC}")
        return []

def update_stratagem_status(tables: Dict[str, Table], stratagem_airtable_id: str, new_status: str, notes: Optional[str] = None):
    """Updates the status and optionally notes of a stratagem."""
    payload = {'Status': new_status}
    if notes:
        # Append to existing notes if any, or set new notes
        try:
            stratagem_record = tables['stratagems'].get(stratagem_airtable_id)
            existing_notes = stratagem_record['fields'].get('Notes', "")
            payload['Notes'] = f"{existing_notes}\n[{datetime.now(VENICE_TIMEZONE).strftime('%Y-%m-%d %H:%M')}] {notes}".strip()
        except Exception: # Fallback if fetching existing notes fails
            payload['Notes'] = f"[{datetime.now(VENICE_TIMEZONE).strftime('%Y-%m-%d %H:%M')}] {notes}"

    try:
        tables['stratagems'].update(stratagem_airtable_id, payload)
        log.info(f"{LogColors.OKGREEN}Updated stratagem {stratagem_airtable_id} status to '{new_status}'.{LogColors.ENDC}")
    except Exception as e:
        log.error(f"{LogColors.FAIL}Error updating status for stratagem {stratagem_airtable_id}: {e}{LogColors.ENDC}")


STRATAGEM_PROCESSORS = {
    "undercut": process_undercut_stratagem,
    "coordinate_pricing": process_coordinate_pricing_stratagem,
    "hoard_resource": process_hoard_resource_stratagem,
    "political_campaign": process_political_campaign_stratagem,
    "reputation_assault": process_reputation_assault_stratagem,
    "emergency_liquidation": process_emergency_liquidation_stratagem,
    "cultural_patronage": process_cultural_patronage_stratagem,
    "information_network": process_information_network_stratagem,
    "maritime_blockade": process_maritime_blockade_stratagem,
    "theater_conspiracy": process_theater_conspiracy_stratagem,
    "printing_propaganda": process_printing_propaganda_stratagem,
    "cargo_mishap": process_cargo_mishap_stratagem,
    "marketplace_gossip": process_marketplace_gossip_stratagem,
    "joint_venture": process_joint_venture_stratagem,
    "monopoly_pricing": process_monopoly_pricing_stratagem,
    "reputation_boost": process_reputation_boost_stratagem,
    "canal_mugging": process_canal_mugging_stratagem,
    "burglary": process_burglary_stratagem,
    "employee_corruption": process_employee_corruption_stratagem,
    "arson": process_arson_stratagem,
    "charity_distribution": process_charity_distribution_stratagem,
    "festival_organisation": process_festival_organisation_stratagem
    # Add other stratagem type to processor mappings here
}

def main(dry_run: bool = False, specific_stratagem_id: Optional[str] = None):
    log_header_message = "Process Stratagems Script"
    if specific_stratagem_id:
        log_header_message += f" for specific StratagemId '{specific_stratagem_id}'"
    log_header_message += f" (dry_run={dry_run})"
    log_header(log_header_message, LogColors.HEADER)

    tables = initialize_airtable()
    if not tables:
        log.error(f"{LogColors.FAIL}Failed to initialize Airtable. Exiting.{LogColors.ENDC}")
        return

    resource_defs = get_resource_types_from_api(API_BASE_URL)
    building_type_defs = get_building_types_from_api(API_BASE_URL)

    if not resource_defs or not building_type_defs:
        log.error(f"{LogColors.FAIL}Failed to fetch resource or building definitions. Exiting.{LogColors.ENDC}")
        return

    now_utc_dt = datetime.now(timezone.utc) # Définir now_utc_dt ici

    stratagems_to_process = []
    if specific_stratagem_id:
        log.info(f"{LogColors.OKBLUE}Fetching specific stratagem by StratagemId: {specific_stratagem_id}{LogColors.ENDC}")
        try:
            formula = f"{{StratagemId}} = '{_escape_airtable_value(specific_stratagem_id)}'"
            records = tables['stratagems'].all(formula=formula, max_records=1)
            if records:
                stratagems_to_process = records
                log.info(f"{LogColors.OKGREEN}Found specific stratagem: {records[0]['id']}{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Specific stratagem with StratagemId '{specific_stratagem_id}' not found.{LogColors.ENDC}")
        except Exception as e_fetch_specific:
            log.error(f"{LogColors.FAIL}Error fetching specific stratagem '{specific_stratagem_id}': {e_fetch_specific}{LogColors.ENDC}")
    else:
        stratagems_to_process = get_active_stratagems(tables)

    if not stratagems_to_process:
        log.info(f"{LogColors.OKBLUE}No stratagems to process.{LogColors.ENDC}")
        return

    processed_count = 0
    failed_count = 0

    for stratagem_record in stratagems_to_process:
        stratagem_type = stratagem_record['fields'].get('Type')
        stratagem_guid = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
        executed_by_log = stratagem_record['fields'].get('ExecutedBy', 'UnknownCitizen')

        log.info(f"{LogColors.HEADER}--- Processing stratagem {stratagem_guid} (Citizen: {executed_by_log}) of type {stratagem_type} ---{LogColors.ENDC}")
        
        processing_status_flag = True # Assume success unless processor returns False

        if dry_run:
            log.info(f"{LogColors.OKCYAN}[DRY RUN] Would process stratagem {stratagem_guid} of type {stratagem_type}.{LogColors.ENDC}")
            if stratagem_type not in STRATAGEM_PROCESSORS:
                log.warning(f"{LogColors.WARNING}[DRY RUN] No processor for stratagem type: {stratagem_type} (ID: {stratagem_guid}). Would mark as failed.{LogColors.ENDC}")
                processing_status_flag = False
        else:
            processor_func = STRATAGEM_PROCESSORS.get(stratagem_type)
            if processor_func:
                try:
                    if not processor_func(tables, stratagem_record, resource_defs, building_type_defs, API_BASE_URL):
                        processing_status_flag = False
                        log.error(f"{LogColors.FAIL}Processor for stratagem {stratagem_guid} (type {stratagem_type}) returned failure.{LogColors.ENDC}")
                except Exception as e_process:
                    log.error(f"{LogColors.FAIL}Exception during processing of stratagem {stratagem_guid} (type {stratagem_type}): {e_process}{LogColors.ENDC}")
                    import traceback
                    log.error(traceback.format_exc())
                    processing_status_flag = False
                    update_stratagem_status(tables, stratagem_record['id'], "error", f"Exception: {str(e_process)}")
            else:
                log.warning(f"{LogColors.WARNING}No processor for stratagem type: {stratagem_type} (ID: {stratagem_guid}). Marking as failed.{LogColors.ENDC}")
                update_stratagem_status(tables, stratagem_record['id'], "failed", "No processor defined for this type.")
                processing_status_flag = False
        
        # Update status based on processing_status_flag, unless it was already set to 'error' or 'failed' by the processor logic itself.
        # Some stratagems might remain 'active' if they are continuous. The processor should handle this.
        # For now, if a processor returns True, and it's not dry_run, we assume it handled its own status or it's a one-shot that can be marked 'executed'.
        # This part needs refinement based on how stratagems are designed (one-shot vs continuous).
        # For "undercut", it might be continuous until ExpiresAt. The processor itself doesn't change status from 'active'.
        # Let's assume for now that if a processor succeeds, and the stratagem has an ExpiresAt, it remains active.
        # If it's a one-shot type without ExpiresAt, it could be marked 'executed'.

        if not dry_run:
            # Fetch the latest status, as the processor might have updated it (e.g., to 'executed' for one-shot types)
            updated_stratagem_record = tables['stratagems'].get(stratagem_record['id'])
            current_status_after_proc = updated_stratagem_record['fields'].get('Status')
            
            if processing_status_flag: # Processor function returned True (or no exception occurred)
                processed_count += 1
                if current_status_after_proc == 'active':
                    # If still active, check expiration
                    expires_at_str = updated_stratagem_record['fields'].get('ExpiresAt')
                    if expires_at_str:
                        try:
                            expires_at_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                            if expires_at_dt.tzinfo is None: expires_at_dt = pytz.utc.localize(expires_at_dt)
                            if expires_at_dt <= now_utc_dt:
                                update_stratagem_status(tables, stratagem_record['id'], "expired", "Stratagem expired.")
                                log.info(f"Stratagem {stratagem_guid} marked as expired.")
                            # Else, it's active and not expired, so it remains active.
                        except ValueError:
                            log.error(f"Invalid ExpiresAt format for stratagem {stratagem_guid}: {expires_at_str}. Cannot determine expiration.")
                            # Consider marking as error or leaving active with a warning. For now, leave active.
                    else:
                        # No ExpiresAt, and processor succeeded and left it active.
                        # This implies it's a one-shot that the processor should have marked 'executed'.
                        # If it's still 'active', it's likely an oversight in the processor or a continuous stratagem without expiry.
                        # For safety, if a processor returns True and doesn't set an end state, and there's no expiry,
                        # we might assume it's a one-shot that completed.
                        # However, some processors (like undercut) are continuous and *should* remain active.
                        # The processor itself should manage its final state if it's one-shot.
                        # If it's still 'active' here, we assume it's meant to be.
                        log.info(f"Stratagem {stratagem_guid} (type: {stratagem_type}) processed successfully and remains active (no expiry or processor didn't set terminal state).")
                # If status was already changed by processor (e.g. to 'executed', 'failed', 'error'), respect that.
            else: # processing_status_flag is False (processor returned False or an exception occurred)
                failed_count += 1
                if current_status_after_proc == 'active': # If processor failed but didn't update status
                    update_stratagem_status(tables, stratagem_record['id'], "failed", "Processor logic returned failure or an exception occurred.")
                    log.info(f"Stratagem {stratagem_guid} marked as failed due to processor outcome.")
                # If status was already 'error' or 'failed' by processor, it's already handled.
        elif dry_run: # Dry run logic
            if processing_status_flag:
                processed_count +=1
            else:
                failed_count +=1

        log.info(f"{LogColors.HEADER}--- Finished processing stratagem {stratagem_guid} ---{LogColors.ENDC}")

    summary_color = LogColors.OKGREEN if failed_count == 0 else LogColors.WARNING if processed_count > 0 else LogColors.FAIL
    log.info(f"{summary_color}Process Stratagems script finished. Total Processed: {processed_count}, Total Failed: {failed_count}.{LogColors.ENDC}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process active stratagems.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the process without making changes to Airtable.")
    parser.add_argument("--stratagemId", type=str, help="Process a specific stratagem by its custom StratagemId.")
    
    args = parser.parse_args()
    main(dry_run=args.dry_run, specific_stratagem_id=args.stratagemId)

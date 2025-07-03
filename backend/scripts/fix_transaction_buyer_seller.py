#!/usr/bin/env python3
"""
Temporary script to fix historical Buyer/Seller entries in the TRANSACTIONS table.

This script swaps the Buyer and Seller for specific transaction types that were
recorded with an inverted logic before commit 8155b1a.

Affected types:
- wage_payment
- housing_rent
- lease_payment
- lease_tax

Run this script ONCE to correct historical data.
Ensure you have a backup of your Airtable base or understand the implications
before running in live mode.
"""

import os
import sys
import logging
import argparse
from pyairtable import Api, Table
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("fix_transactions")

# Load environment variables
load_dotenv()

# Add project root to sys.path for backend imports
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Transaction types to fix
AFFECTED_TRANSACTION_TYPES = [
    # "wage_payment",    # From dailywages.py
    # "housing_rent",    # From dailyrentpayments.py
    # "lease_payment",   # From distributeLeases.py
    # "lease_tax"        # From distributeLeases.py
    "treasury_redistribution"
]

def initialize_airtable() -> Optional[Table]:
    """Initialize Airtable connection and return the TRANSACTIONS table."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID environment variables.")
        return None
    
    try:
        transactions_table = Table(api_key, base_id, 'TRANSACTIONS')
        # Test connection by attempting to fetch one record
        transactions_table.all(max_records=1) 
        log.info("Airtable connection successful.")
        return transactions_table
    except Exception as e:
        log.error(f"Failed to initialize Airtable or connect to TRANSACTIONS table: {e}")
        return None

def get_all_transactions(transactions_table: Table) -> List[Dict]:
    """Fetch all transactions."""
    log.info("Fetching all transactions...")
    try:
        all_records = transactions_table.all()
        log.info(f"Fetched {len(all_records)} transaction records.")
        return all_records
    except Exception as e:
        log.error(f"Error fetching transactions: {e}")
        return []

def fix_transaction_buyer_seller(transactions_table: Table, transaction_record: Dict, dry_run: bool = False) -> bool:
    """
    Swaps the Buyer and Seller fields for a given transaction record if its type
    is in AFFECTED_TRANSACTION_TYPES.
    Returns True if the transaction was processed (fixed or would be fixed), False otherwise (e.g. error, skipped).
    """
    record_id = transaction_record['id']
    fields = transaction_record['fields']
    
    transaction_type = fields.get('Type')
    current_buyer = fields.get('Buyer')
    current_seller = fields.get('Seller')

    # This function is called only for affected types, so no need to check type here.
    # However, safety checks for Buyer/Seller fields are good.
    if not current_buyer or not current_seller:
        log.warning(f"Transaction {record_id} (Type: {transaction_type}) is missing Buyer or Seller. "
                    f"Buyer: '{current_buyer}', Seller: '{current_seller}'. Skipping fix for this record.")
        return False # Indicates failure to fix this specific record

    log.info(f"Processing transaction {record_id} (Type: {transaction_type}): "
             f"Current Buyer='{current_buyer}', Current Seller='{current_seller}'")

    # Swap: New Buyer is old Seller, New Seller is old Buyer
    new_buyer_value = current_seller
    new_seller_value = current_buyer
    
    update_payload = {
        'Buyer': new_buyer_value,
        'Seller': new_seller_value
    }

    if dry_run:
        log.info(f"[DRY RUN] Would update transaction {record_id}: "
                 f"Set Buyer='{new_buyer_value}', Seller='{new_seller_value}'")
    else:
        try:
            log.info(f"Updating transaction {record_id}: "
                     f"Set Buyer='{new_buyer_value}', Seller='{new_seller_value}'")
            transactions_table.update(record_id, update_payload)
            log.info(f"Successfully updated transaction {record_id}.")
        except Exception as e:
            log.error(f"Failed to update transaction {record_id}: {e}")
            return False # Indicates failure to fix
    return True # Indicates successful fix or successful dry-run simulation

def main():
    parser = argparse.ArgumentParser(description="Fix historical Buyer/Seller entries in Airtable TRANSACTIONS.")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes to Airtable.")
    args = parser.parse_args()

    if args.dry_run:
        log.info("Starting in DRY RUN mode. No changes will be made to Airtable.")
    else:
        log.warning("Starting in LIVE mode. Changes WILL be made to Airtable.")
        log.warning("Ensure you have a backup of your Airtable base or understand the implications.")
        confirmation = input("Are you sure you want to proceed? (yes/no): ")
        if confirmation.lower() != 'yes':
            log.info("Operation cancelled by user.")
            return

    transactions_table = initialize_airtable()
    if not transactions_table:
        return

    all_transactions = get_all_transactions(transactions_table)
    if not all_transactions:
        log.info("No transactions found to process.")
        return
    
    log.info(f"Will attempt to fix transactions of types: {', '.join(AFFECTED_TRANSACTION_TYPES)}")

    total_affected_found = 0
    successfully_fixed_count = 0
    failed_to_fix_count = 0

    for record in all_transactions:
        if record['fields'].get('Type') in AFFECTED_TRANSACTION_TYPES:
            total_affected_found += 1
            if fix_transaction_buyer_seller(transactions_table, record, args.dry_run):
                successfully_fixed_count += 1
            else:
                failed_to_fix_count += 1
    
    log.info("--- Processing Complete ---")
    log.info(f"Total transactions of affected types found: {total_affected_found}")
    log.info(f"Successfully fixed (or would fix in dry run): {successfully_fixed_count}")
    if failed_to_fix_count > 0:
        log.warning(f"Failed to fix (due to errors or missing data for an affected type): {failed_to_fix_count}")
    log.info(f"Total transactions scanned: {len(all_transactions)}")

if __name__ == "__main__":
    main()

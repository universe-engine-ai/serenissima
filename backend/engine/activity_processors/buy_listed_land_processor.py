import os
import sys
import logging
import json
from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any # Updated import to include Dict and Any if they are used, Optional is already there

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import (
    LogColors, get_citizen_record, get_land_record, get_contract_record, VENICE_TIMEZONE
)
# Import create_notification from the new notification_helpers module
from backend.engine.utils.notification_helpers import create_notification

log = logging.getLogger(__name__)

def process_buy_listed_land_fn(tables: dict, activity_record: dict, building_type_defs: dict, resource_defs: dict, api_base_url: Optional[str] = None) -> bool:
    """
    Processes the 'execute_buy_listed_land' activity.
    - Validates the listing contract.
    - Verifies buyer funds.
    - Transfers land ownership.
    - Transfers ducats.
    - Updates contract status.
    - Creates a transaction record.
    """
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    activity_citizen_username = activity_fields.get('Citizen') # Buyer's username

    log.info(f"{LogColors.PROCESS}Processing 'execute_buy_listed_land' activity {activity_guid} by buyer {activity_citizen_username}.{LogColors.ENDC}")

    try:
        notes_str_from_activity = activity_fields.get('Notes') 
        if not notes_str_from_activity:
            log.error(f"{LogColors.FAIL}Activity {activity_guid} is missing 'Notes' (expected JSON details here).{LogColors.ENDC}") 
            return False
        
        details = json.loads(notes_str_from_activity) 
        log.info(f"{LogColors.PROCESS}Activity {activity_guid} details parsed: {details}{LogColors.ENDC}")

        listing_contract_custom_id = details.get('listingContractId')
        land_id_being_bought = details.get('landId')
        
        purchase_price_from_details = details.get('price')
        if purchase_price_from_details is None:
            log.error(f"{LogColors.FAIL}Missing 'price' in activity {activity_guid} details: {details}{LogColors.ENDC}")
            return False
        try:
            purchase_price = float(purchase_price_from_details)
        except (ValueError, TypeError) as e_price:
            log.error(f"{LogColors.FAIL}Invalid 'price' format ('{purchase_price_from_details}') in activity {activity_guid} details: {e_price}{LogColors.ENDC}")
            return False
            
        # buyer_username_from_details = details.get('buyerUsername') # Should match activity performer

        if not listing_contract_custom_id or not land_id_being_bought: # purchase_price check is now more robust
            log.error(f"{LogColors.FAIL}Missing listingContractId or landId in activity {activity_guid} details: {details}{LogColors.ENDC}")
            return False

        # Get buyer citizen record
        buyer_citizen_record = get_citizen_record(tables, activity_citizen_username)
        if not buyer_citizen_record:
            log.error(f"{LogColors.FAIL}Buyer citizen '{activity_citizen_username}' not found for activity {activity_guid}.{LogColors.ENDC}")
            return False
        buyer_airtable_id = buyer_citizen_record['id'] # For updating Ducats
        buyer_username = activity_citizen_username # Confirmed

        # Get the land_listing contract
        listing_contract_record = get_contract_record(tables, listing_contract_custom_id)
        if not listing_contract_record:
            log.error(f"{LogColors.FAIL}Listing contract {listing_contract_custom_id} not found. Activity {activity_guid}.{LogColors.ENDC}")
            return False
        
        listing_contract_fields = listing_contract_record['fields']
        if listing_contract_fields.get('Type') != 'land_listing' or listing_contract_fields.get('Status') != 'active':
            log.error(f"{LogColors.FAIL}Contract {listing_contract_custom_id} is not an active land_listing. Status: {listing_contract_fields.get('Status')}. Activity {activity_guid}.{LogColors.ENDC}")
            return False
        
        if listing_contract_fields.get('Asset') != land_id_being_bought:
            log.error(f"{LogColors.FAIL}Listing contract {listing_contract_custom_id} is for asset {listing_contract_fields.get('Asset')}, not {land_id_being_bought}. Activity {activity_guid}.{LogColors.ENDC}")
            return False

        contract_price_from_field = listing_contract_fields.get('PricePerResource')
        if contract_price_from_field is None:
            log.error(f"{LogColors.FAIL}Listing contract {listing_contract_custom_id} missing 'PricePerResource'. Activity {activity_guid}.{LogColors.ENDC}")
            return False
        try:
            contract_price = float(contract_price_from_field)
        except (ValueError, TypeError) as e_contract_price:
            log.error(f"{LogColors.FAIL}Invalid 'PricePerResource' format ('{contract_price_from_field}') in listing contract {listing_contract_custom_id}: {e_contract_price}. Activity {activity_guid}.{LogColors.ENDC}")
            return False

        # Using a small tolerance for float comparison, though prices should ideally be exact
        if abs(contract_price - purchase_price) > 0.001: # Tolerance of 0.001 Ducats
            log.error(f"{LogColors.FAIL}Price mismatch for listing {listing_contract_custom_id}. Activity price: {purchase_price}, Contract price: {contract_price}. Activity {activity_guid}.{LogColors.ENDC}")
            return False

        # Get seller details from contract (assuming 'Seller' field stores username string)
        seller_username_from_contract = listing_contract_fields.get('Seller')
        if not seller_username_from_contract:
            log.error(f"{LogColors.FAIL}Listing contract {listing_contract_custom_id} has no Seller username. Activity {activity_guid}.{LogColors.ENDC}")
            return False

        seller_citizen_record = get_citizen_record(tables, seller_username_from_contract)
        if not seller_citizen_record:
            log.error(f"{LogColors.FAIL}Seller citizen '{seller_username_from_contract}' from listing contract {listing_contract_custom_id} not found. Activity {activity_guid}.{LogColors.ENDC}")
            return False
        seller_airtable_id = seller_citizen_record['id'] # Get Airtable ID for updates
        seller_username = seller_citizen_record['fields'].get('Username') # Confirm username
        
        # Verify land exists (owner check is implicit as seller listed it)
        land_record = get_land_record(tables, land_id_being_bought)
        if not land_record:
            log.error(f"{LogColors.FAIL}Land {land_id_being_bought} not found. Activity {activity_guid}.{LogColors.ENDC}")
            return False
        
        # Financial transaction
        seller_ducats_str = seller_citizen_record['fields'].get('Ducats', '0')
        buyer_ducats_str = buyer_citizen_record['fields'].get('Ducats', '0')
        try:
            seller_ducats = float(seller_ducats_str)
            buyer_ducats = float(buyer_ducats_str)
        except (ValueError, TypeError) as e_ducats:
            log.error(f"{LogColors.FAIL}Invalid Ducats format for seller ('{seller_ducats_str}') or buyer ('{buyer_ducats_str}'). Activity {activity_guid}: {e_ducats}{LogColors.ENDC}")
            return False

        log.info(f"{LogColors.PROCESS}Financial check for activity {activity_guid}: Buyer {buyer_username} has {buyer_ducats:.2f} Ducats. Purchase price: {purchase_price:.2f} Ducats.{LogColors.ENDC}")
        if buyer_ducats < purchase_price:
            failure_reason_msg = f"Buyer {buyer_username} has insufficient funds ({buyer_ducats:.2f} Ducats) for purchase price ({purchase_price:.2f} Ducats)."
            log.error(f"{LogColors.FAIL}{failure_reason_msg} Activity {activity_guid}.{LogColors.ENDC}")
            
            # Update activity notes with failure reason
            try:
                current_notes_json = json.loads(notes_str_from_activity) if notes_str_from_activity else {}
                current_notes_json["failure_reason"] = failure_reason_msg
                tables['activities'].update(activity_record['id'], {'Notes': json.dumps(current_notes_json)})
                log.info(f"{LogColors.OKBLUE}Updated activity {activity_guid} Notes with failure reason: Insufficient funds.{LogColors.ENDC}")
            except Exception as e_notes_update:
                log.error(f"{LogColors.FAIL}Failed to update Notes for activity {activity_guid} with failure reason: {e_notes_update}{LogColors.ENDC}")
            
            # Optionally, mark listing as failed or just fail the activity
            return False

        tables['citizens'].update(seller_airtable_id, {'Ducats': seller_ducats + purchase_price})
        tables['citizens'].update(buyer_airtable_id, {'Ducats': buyer_ducats - purchase_price})
        log.info(f"{LogColors.PROCESS}Transferred {purchase_price} ducats from buyer {buyer_username} to seller {seller_username}. Activity {activity_guid}.{LogColors.ENDC}")

        # Transfer land ownership (store username string)
        tables['lands'].update(land_record['id'], {'Owner': buyer_username}) # Use lowercase 'lands' key
        log.info(f"{LogColors.PROCESS}Transferred ownership of land {land_id_being_bought} to buyer {buyer_username}. Activity {activity_guid}.{LogColors.ENDC}")

        # Update listing contract status
        now_iso = datetime.now(timezone.utc).isoformat()
        update_payload_contracts = {
            "Status": "completed", 
            "Buyer": buyer_username, 
            "Notes": f"Completed: Land bought by {buyer_username} on {now_iso}."
            # UpdatedAt is handled by Airtable
        }
        tables['contracts'].update(listing_contract_record['id'], update_payload_contracts)
        log.info(f"{LogColors.PROCESS}Listing contract {listing_contract_custom_id} status updated to 'completed'. Activity {activity_guid}.{LogColors.ENDC}")

        # Create transaction record
        transaction_payload = {
            "Type": "land_sale_from_listing",
            "AssetType": "land",
            "Asset": land_id_being_bought,
            "Seller": seller_username, # Username
            "Buyer": buyer_username,   # Username
            "Price": purchase_price,
            "Notes": json.dumps({"listing_contract_id": listing_contract_custom_id, "activity_guid": activity_guid}),
            "CreatedAt": now_iso,
            "ExecutedAt": now_iso
        }
        tables['transactions'].create(transaction_payload)
        log.info(f"{LogColors.SUCCESS}Land sale transaction recorded for land {land_id_being_bought}. Activity {activity_guid}.{LogColors.ENDC}")

        # Notifications for buyer and seller
        notification_details = {
            "landId": land_id_being_bought,
            "price": purchase_price,
            "listingContractId": listing_contract_custom_id,
            "activityGuid": activity_guid
        }
        
        # Notify seller
        create_notification(
            tables,
            seller_username,
            "land_sold",
            f"Your land parcel {land_id_being_bought} has been sold to {buyer_username} for {purchase_price} ducats.",
            details=notification_details,
            asset_id=land_id_being_bought,
            asset_type="land"
        )
        
        # Notify buyer
        create_notification(
            tables,
            buyer_username,
            "land_purchased",
            f"You have successfully purchased land parcel {land_id_being_bought} from {seller_username} for {purchase_price} ducats.",
            details=notification_details,
            asset_id=land_id_being_bought,
            asset_type="land"
        )

        # Optional: Cancel other active offers for this land made by the buyer or others
        # Example: Cancel active 'land_offer' by the buyer for this land
        # Assuming 'Buyer' field in CONTRACTS stores the username directly
        buyer_offers_formula = f"AND({{Asset}}='{land_id_being_bought}', {{AssetType}}='land', {{Type}}='land_offer', {{Buyer}}='{buyer_username}', {{Status}}='active')"
        buyer_offers = tables['contracts'].all(formula=buyer_offers_formula)
        for offer in buyer_offers:
            tables['contracts'].update(offer['id'], {"Status": "cancelled", "Notes": f"Cancelled: Buyer {buyer_username} purchased land {land_id_being_bought} via listing."})
            log.info(f"{LogColors.PROCESS}Cancelled buyer's active offer {offer['fields'].get('ContractId')} for land {land_id_being_bought}.{LogColors.ENDC}")

        return True

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error processing 'execute_buy_listed_land' activity {activity_guid}: {e}{LogColors.ENDC}", exc_info=True)
        return False

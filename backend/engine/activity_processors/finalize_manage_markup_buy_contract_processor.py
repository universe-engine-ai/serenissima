import logging
import json
from datetime import datetime, timezone, timedelta # Added timedelta
import uuid
from typing import Optional # Added import for Optional

from backend.engine.utils.activity_helpers import LogColors, get_contract_record, log_header, _escape_airtable_value # Added _escape_airtable_value
# Import create_notification from the new notification_helpers module
from backend.engine.utils.notification_helpers import create_notification

log = logging.getLogger(__name__)

def process_finalize_manage_markup_buy_contract_fn(
    tables: dict, 
    activity_record: dict, 
    building_type_defs: dict, 
    resource_defs: dict,
    api_base_url: Optional[str] = None  # Added api_base_url parameter
) -> bool:
    """
    Processes the 'finalize_manage_markup_buy_contract' activity.
    - Reads contract details from activity Notes.
    - Creates or updates a 'markup_buy_contract' in the CONTRACTS table.
    """
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen') # Buyer

    log_header(f"Finalize Markup Buy Contract: {citizen_username}", LogColors.HEADER)
    log.info(f"{LogColors.PROCESS}Processing 'finalize_manage_markup_buy_contract' activity {activity_guid} by {citizen_username}.{LogColors.ENDC}")

    try:
        notes_str = activity_fields.get('Notes')
        if not notes_str:
            log.error(f"{LogColors.FAIL}Activity {activity_guid} is missing 'Notes'.{LogColors.ENDC}")
            return False
        
        details = json.loads(notes_str)
        contract_id_to_manage = details.get('contractIdToManage')
        resource_type = details.get('resourceType')
        target_amount = details.get('targetAmount')
        max_price_per_resource = details.get('maxPricePerResource')
        buyer_building_id = details.get('buyerBuildingId')
        
        # Details for the contract itself, passed from the creator
        seller_building_id_for_contract = details.get("sellerBuildingId_for_contract")
        seller_username_for_contract = details.get("sellerUsername_for_contract")
        title_for_contract = details.get("title_for_contract")
        description_for_contract = details.get("description_for_contract")
        notes_for_contract_field_data = details.get("notes_for_contract_field")


        if not contract_id_to_manage:
            log.error(f"{LogColors.FAIL}Activity {activity_guid} notes missing 'contractIdToManage'.{LogColors.ENDC}")
            return False
        if not resource_type or target_amount is None or max_price_per_resource is None or not buyer_building_id:
            log.error(f"{LogColors.FAIL}Missing required contract details in activity {activity_guid} notes: {details}{LogColors.ENDC}")
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        
        base_contract_fields = {
            "Type": "markup_buy",
            "ResourceType": resource_type,
            "TargetAmount": float(target_amount),
            "PricePerResource": float(max_price_per_resource),
            "Buyer": citizen_username, # The citizen performing the activity is the buyer
            "BuyerBuilding": buyer_building_id,
            "Status": "active",
            "Seller": seller_username_for_contract if seller_username_for_contract else None,
            "SellerBuilding": seller_building_id_for_contract if seller_building_id_for_contract else None,
            "Title": title_for_contract if title_for_contract else f"Markup Buy: {resource_type}",
            "Description": description_for_contract if description_for_contract else f"Buy order for {resource_type}.",
        }
        if notes_for_contract_field_data and isinstance(notes_for_contract_field_data, dict):
            base_contract_fields["Notes"] = json.dumps(notes_for_contract_field_data)
        elif isinstance(notes_for_contract_field_data, str): # If it's already a JSON string
             base_contract_fields["Notes"] = notes_for_contract_field_data


        existing_contract_record = None
        formula_existing = f"{{ContractId}} = '{_escape_airtable_value(contract_id_to_manage)}'"
        try:
            existing_contracts = tables['contracts'].all(formula=formula_existing, max_records=1)
            if existing_contracts:
                existing_contract_record = existing_contracts[0]
        except Exception as e_fetch:
            log.error(f"{LogColors.FAIL}Error fetching contract by ContractId '{contract_id_to_manage}': {e_fetch}{LogColors.ENDC}")
            # Potentially return False or try to create if fetch fails critically

        if existing_contract_record:
            if existing_contract_record['fields'].get('Buyer') != citizen_username:
                log.error(f"{LogColors.FAIL}Citizen {citizen_username} cannot update contract {contract_id_to_manage} as they are not the buyer.{LogColors.ENDC}")
                return False
            
            # Fields to update (subset of base_contract_fields, excluding IDs and CreatedAt)
            updateable_fields = {k: v for k, v in base_contract_fields.items() if k not in ["ContractId", "Buyer", "CreatedAt", "Type", "Notes"]}
            # Ensure EndAt is also updated if it's part of the logic (e.g. extending contract duration)
            # For now, EndAt is not explicitly managed here, assuming it's set on creation or by another process.
            # If it needs to be refreshed: updateable_fields["EndAt"] = (datetime.now(timezone.utc) + timedelta(weeks=CONTRACT_DURATION_WEEKS)).isoformat()

            # Merge Notes to preserve existing fulfillment state or other data
            current_notes_data = {}
            try:
                current_notes_str = existing_contract_record['fields'].get('Notes', '{}')
                current_notes_data = json.loads(current_notes_str)
                if not isinstance(current_notes_data, dict): # Ensure it's a dict
                    current_notes_data = {"previous_notes_raw": current_notes_str} if current_notes_str else {}
            except json.JSONDecodeError:
                current_notes_data = {"previous_notes_raw": current_notes_str} if current_notes_str else {}
            
            # notes_for_contract_field_data contains the new management metadata from the activity
            # It should be a dictionary if parsed correctly from activity notes.
            if notes_for_contract_field_data and isinstance(notes_for_contract_field_data, dict):
                current_notes_data.update(notes_for_contract_field_data) # Merge new management info
            elif notes_for_contract_field_data: # If it's some other type (e.g. string), log warning and add raw
                log.warning(f"notes_for_contract_field_data for contract {contract_id_to_manage} was not a dict: {notes_for_contract_field_data}. Adding as raw.")
                current_notes_data["new_management_notes_raw"] = str(notes_for_contract_field_data)

            updateable_fields["Notes"] = json.dumps(current_notes_data)

            tables['contracts'].update(existing_contract_record['id'], updateable_fields)
            log.info(f"{LogColors.SUCCESS}Updated markup_buy_contract {contract_id_to_manage} for {citizen_username}. Notes merged.{LogColors.ENDC}")
            create_notification(tables, citizen_username, "markup_buy_contract_updated", f"Your buy order for {resource_type} ({contract_id_to_manage}) has been updated.", details={"contractId": contract_id_to_manage})
        else:
            # Create new contract with the deterministic ID
            final_contract_fields = base_contract_fields.copy()
            final_contract_fields["ContractId"] = contract_id_to_manage
            final_contract_fields["CreatedAt"] = now_iso
            # Set EndAt for new contracts
            from backend.ais.automated_adjustmarkupbuys import CONTRACT_DURATION_WEEKS # Import for duration
            final_contract_fields["EndAt"] = (datetime.now(timezone.utc) + timedelta(weeks=CONTRACT_DURATION_WEEKS)).isoformat()


            new_contract_record = tables['contracts'].create(final_contract_fields)
            log.info(f"{LogColors.SUCCESS}Created new markup_buy_contract {new_contract_record['fields'].get('ContractId')} for {citizen_username}.{LogColors.ENDC}")
            create_notification(tables, citizen_username, "markup_buy_contract_created", f"Your buy order for {resource_type} ({new_contract_record['fields'].get('ContractId')}) has been placed.", details={"contractId": new_contract_record['fields'].get('ContractId')})
            
        return True

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error processing 'finalize_manage_markup_buy_contract' activity {activity_guid}: {e}{LogColors.ENDC}", exc_info=True)
        return False

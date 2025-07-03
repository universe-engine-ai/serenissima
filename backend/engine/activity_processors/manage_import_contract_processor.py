import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pyairtable import Table
from backend.engine.utils.activity_helpers import _escape_airtable_value, VENICE_TIMEZONE

log = logging.getLogger(__name__)

def process_manage_import_contract_fn(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Any,
    resource_defs: Any,
    api_base_url: Optional[str] = None # Added api_base_url for signature consistency
) -> bool:
    """
    Process activities in the manage_import_contract chain.
    
    This processor handles three types of activities:
    1. goto_location - Travel to buyer building or customs office (no special action needed)
    2. assess_import_needs - Verify business needs at buyer building
    3. register_import_agreement - Create or update the import contract
    """
    fields = activity_record.get('fields', {})
    activity_type = fields.get('Type')
    citizen = fields.get('Citizen')
    notes_str = fields.get('Notes') # Changed from 'Details'
    
    try:
        # Ensure notes_str is not None and not just whitespace before parsing
        details = json.loads(notes_str) if notes_str and notes_str.strip() else {}
    except json.JSONDecodeError as e: # Catch specific JSONDecodeError
        log.error(f"Error parsing Notes as JSON for {activity_type} (Citizen: {citizen}, ActivityId: {activity_record.get('id')}): {e}. Notes content: '{notes_str[:200]}...'")
        return False
    except Exception as e: # Catch any other unexpected errors during parsing
        log.error(f"Unexpected error parsing Notes for {activity_type} (Citizen: {citizen}, ActivityId: {activity_record.get('id')}): {e}")
        return False
    
    # Handle goto_location activity (part of chain)
    if activity_type == "goto_location" and details.get("activityType") == "manage_import_contract":
        # Just log and return success - the next activity is already scheduled
        next_step = details.get("nextStep", "unknown")
        log.info(f"Citizen {citizen} has completed travel for manage_import_contract. Next step: {next_step}")
        return True
    
    # Handle assess_import_needs activity - no longer used but kept for backward compatibility
    elif activity_type == "assess_import_needs":
        log.info(f"assess_import_needs activity is deprecated but processing for backward compatibility")
        return True
    
    # Handle register_import_agreement activity
    elif activity_type == "register_import_agreement":
        if not details: # Check if details is empty after parsing Notes
            log.error(f"Cannot process {activity_type} for {citizen} (ActivityId: {activity_record.get('id')}) because the 'Notes' field did not yield a valid JSON object with parameters. Notes content was: '{notes_str[:200]}...'")
            return False
        return _create_or_update_import_contract(tables, activity_record, details)
    
    else:
        log.error(f"Unexpected activity type in manage_import_contract processor: {activity_type}")
        return False

# _handle_assess_import_needs function is removed as it's no longer needed

def _create_or_update_import_contract(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    details: Dict[str, Any]
) -> bool:
    """Create or update an import contract when the register_import_agreement activity is processed."""
    fields = activity_record.get('fields', {})
    fields = activity_record.get('fields', {})
    citizen = fields.get('Citizen')
    office_building_id = fields.get('FromBuilding')  # We're at the customs office now
    
    # Extract details for the contract itself
    resource_type = details.get('resourceType')
    target_amount_detail = details.get('targetAmount')
    price_per_resource_detail = details.get('pricePerResource')
    buyer_building_id = details.get('buyerBuildingId')
    # This is the contractId passed from the creator, intended for create-or-update
    contract_id_from_activity_notes = details.get('contractId') 
    
    if not (citizen and office_building_id and resource_type and 
            target_amount_detail is not None and price_per_resource_detail is not None):
        log.error(f"Missing data for register_import_agreement: citizen={citizen}, office={office_building_id}, resource={resource_type}, amount={target_amount_detail}, price={price_per_resource_detail}")
        return False
    
    # Si buyer_building_id est null, rechercher les contrats d'importation publics correspondants
    if not buyer_building_id:
        log.info(f"No buyer building specified for import contract. Looking for public import contracts for {resource_type}.")
        # Rechercher les contrats d'importation publics actifs pour ce type de ressource
        formula = f"AND({{Type}}='public_import', {{ResourceType}}='{_escape_airtable_value(resource_type)}', {{Status}}='active')"
        public_import_contracts = tables['contracts'].all(formula=formula)
        
        if public_import_contracts:
            # Prendre le premier contrat correspondant
            public_contract = public_import_contracts[0]
            buyer_building_id = public_contract['fields'].get('BuyerBuilding')
            log.info(f"Found public import contract for {resource_type}. Using buyer building: {buyer_building_id}")
        
        if not buyer_building_id:
            log.error(f"No buyer building specified and no matching public import contracts found for {resource_type}")
            return False
    
    # Calculate broker/customs fee (typically 3% of total value, minimum 15 Ducats)
    # Use the details from the activity notes for fee calculation
    total_value = float(price_per_resource_detail) * float(target_amount_detail)
    broker_fee = max(15, total_value * 0.03)  # 3% fee, minimum 15 Ducats
    
    # Check if citizen has enough Ducats to pay the fee
    try:
        citizen_records = tables['citizens'].all(formula=f"{{Username}}='{_escape_airtable_value(citizen)}'", max_records=1)
        if not citizen_records:
            log.error(f"Citizen {citizen} not found")
            return False
        
        citizen_record = citizen_records[0]
        citizen_ducats = float(citizen_record['fields'].get('Ducats', 0))
        
        if citizen_ducats < broker_fee:
            log.error(f"Citizen {citizen} has insufficient Ducats ({citizen_ducats}) to pay broker fee ({broker_fee})")
            return False
        
        # Get the building operator (RunBy) to pay the fee to
        building_operator = "ConsiglioDeiDieci"  # Default to city government
        building_formula = f"{{BuildingId}}='{_escape_airtable_value(office_building_id)}'"
        buildings = tables["buildings"].all(formula=building_formula, max_records=1)
        if buildings and buildings[0]['fields'].get('RunBy'):
            building_operator = buildings[0]['fields'].get('RunBy')
            log.info(f"Found building operator {building_operator} for building {office_building_id}")
        
        # Deduct the fee from citizen
        tables['citizens'].update(citizen_record['id'], {'Ducats': citizen_ducats - broker_fee})
        
        # Add fee to building operator
        if building_operator != "ConsiglioDeiDieci":
            operator_formula = f"{{Username}}='{_escape_airtable_value(building_operator)}'"
            operator_records = tables["citizens"].all(formula=operator_formula, max_records=1)
            
            if operator_records:
                operator_record = operator_records[0]
                operator_ducats = float(operator_record['fields'].get('Ducats', 0))
                tables["citizens"].update(operator_record['id'], {'Ducats': operator_ducats + broker_fee})
        
        # Record the transaction
        transaction_payload = {
            "Type": "import_registration_fee",
            "AssetType": "contract",
            "Asset": contract_id_from_activity_notes if contract_id_from_activity_notes else f"new_contract_{resource_type}_{citizen}",
            "Seller": citizen,  # Citizen pays
            "Buyer": building_operator,  # Building operator receives
            "Price": broker_fee,
            "Notes": json.dumps({
                "resource_type": resource_type,
                "target_amount": target_amount_detail,
                "price_per_resource": price_per_resource_detail,
                "office_building_id": office_building_id,
                "buyer_building_id": buyer_building_id,
                "intended_contract_id": contract_id_from_activity_notes # Log the intended ID
            }),
            "CreatedAt": datetime.utcnow().isoformat(),
            "ExecutedAt": datetime.utcnow().isoformat()
        }
        tables['transactions'].create(transaction_payload)
        
        # Now create or update the contract
        contract_to_use_for_creation_or_update = None
        
        if contract_id_from_activity_notes:
            # Attempt to find the contract by the ID from activity notes
            formula = f"{{ContractId}}='{_escape_airtable_value(contract_id_from_activity_notes)}'"
            contract_records = tables['contracts'].all(formula=formula, max_records=1)
            
            if contract_records:
                # Contract exists, update it
                contract_record_to_update = contract_records[0]
                update_payload = {
                    "PricePerResource": price_per_resource_detail,
                    "TargetAmount": target_amount_detail,
                    "Status": "active", # Ensure it's active if being updated
                    "EndAt": (datetime.utcnow() + timedelta(days=30)).isoformat() # Refresh EndAt
                    # "UpdatedAt" is handled by Airtable
                }
                tables['contracts'].update(contract_record_to_update['id'], update_payload)
                log.info(f"Updated import contract {contract_id_from_activity_notes} for {citizen}: {target_amount_detail} {resource_type} at {price_per_resource_detail} Ducats each")
                return True
            else:
                # Contract with contract_id_from_activity_notes does NOT exist. Create it using this ID.
                log.info(f"Contract {contract_id_from_activity_notes} not found. Creating new import contract with this ID for {citizen}.")
                contract_to_use_for_creation_or_update = contract_id_from_activity_notes
        else:
            # No contractId provided in activity notes, generate a new one
            log.info(f"No specific contractId provided in activity notes. Generating new import contract for {citizen}.")
            now_gen = datetime.utcnow()
            contract_to_use_for_creation_or_update = f"import_{resource_type}_{_escape_airtable_value(citizen)}_{int(now_gen.timestamp())}"

        # Common creation logic using contract_to_use_for_creation_or_update
        now_create = datetime.utcnow()
        resource_name_for_title = resource_type.replace('_', ' ').title()
        
        contract_payload = {
            "ContractId": contract_to_use_for_creation_or_update,
            "Type": "import",
            "Buyer": citizen,
            "Seller": "Italia",  # Standard foreign source
            "ResourceType": resource_type,
            "BuyerBuilding": buyer_building_id,
            "PricePerResource": price_per_resource_detail,
            "TargetAmount": target_amount_detail,
            "Status": "active",
            "Title": f"Import of {resource_name_for_title}",
            "Description": f"Contract to import {target_amount_detail} units of {resource_name_for_title} at {price_per_resource_detail} Ducats each to {buyer_building_id}.",
            "CreatedAt": now_create.isoformat(),
            "EndAt": (now_create + timedelta(days=30)).isoformat()  # Contract ends in 30 days
        }
        
        tables['contracts'].create(contract_payload)
        log.info(f"Created new import contract {contract_to_use_for_creation_or_update} for {citizen}: {target_amount_detail} {resource_type} at {price_per_resource_detail} Ducats each")
        return True
            
    except Exception as e:
        log.error(f"Error creating/updating import contract: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False

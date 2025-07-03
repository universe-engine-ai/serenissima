import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pyairtable import Table
from backend.engine.utils.activity_helpers import _escape_airtable_value, VENICE_TIMEZONE, log_header, LogColors

log = logging.getLogger(__name__)

def process_initiate_building_project_fn(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Any,
    resource_defs: Any,
    api_base_url: Optional[str] = None # Added api_base_url parameter
) -> bool:
    """
    Process activities in the initiate_building_project chain.
    
    This processor handles four types of activities:
    1. goto_location (to land) - Travel to the land plot (no special action needed)
    2. inspect_land_plot - Verify the land is suitable for the building
    3. goto_location (to office) - Travel to the town hall or builder's workshop (no special action needed)
    4. submit_building_project - Create the building project and handle payments
    """
    fields = activity_record.get('fields', {})
    activity_type = fields.get('Type')
    citizen = fields.get('Citizen')
    details_str = fields.get('Notes') # Changed 'Details' to 'Notes'

    log_header(f"Initiate Building Project ({activity_type}): {citizen}", LogColors.HEADER)
    
    try:
        details = json.loads(details_str) if details_str else {}
    except Exception as e:
        log.error(f"Error parsing Details for {activity_type}: {e}")
        return False
    
    # Handle goto_location activity (part of chain)
    if activity_type == "goto_location" and details.get("activityType") == "initiate_building_project":
        # Just log and return success - the next activity is already scheduled
        next_step = details.get("nextStep", "unknown")
        log.info(f"Citizen {citizen} has completed travel for initiate_building_project. Next step: {next_step}")
        return True
    
    # Handle inspect_land_plot activity
    elif activity_type == "inspect_land_plot":
        return _handle_inspect_land_plot(tables, activity_record, details, building_type_defs)
    
    # Handle submit_building_project activity
    elif activity_type == "submit_building_project":
        return _create_building_project(tables, activity_record, details, building_type_defs)
    
    else:
        log.error(f"Unexpected activity type in initiate_building_project processor: {activity_type}")
        return False

def _handle_inspect_land_plot(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    details: Dict[str, Any],
    building_type_defs: Any
) -> bool:
    """
    Handle the inspect_land_plot activity.
    Verify that the land is suitable for the building type.
    """
    fields = activity_record.get('fields', {})
    citizen = fields.get('Citizen')
    land_id = details.get('landId')
    building_type_definition = details.get('buildingTypeDefinition')
    point_details = details.get('pointDetails')
    
    if not (citizen and land_id and building_type_definition and point_details):
        log.error(f"Missing data for inspect_land_plot: citizen={citizen}, land_id={land_id}")
        return False
    
    # Check if the land exists and is owned by the citizen
    try:
        land_formula = f"{{LandId}}='{_escape_airtable_value(land_id)}'"
        land_records = tables['lands'].all(formula=land_formula, max_records=1)
        
        if not land_records:
            log.error(f"Land {land_id} not found")
            return False
        
        land_record = land_records[0]
        # land_owner = land_record['fields'].get('Owner') # Ownership check removed
        
        # if land_owner != citizen: # Ownership check removed
        #     log.error(f"Citizen {citizen} does not own land {land_id}")
        #     return False
        
        # Check if the building type is valid
        building_type = building_type_definition.get('id')
        if not building_type or building_type not in building_type_defs:
            log.error(f"Invalid building type: {building_type}")
            return False
        
        # Check if the point is valid for this land
        # This would require more complex validation in a real implementation
        # For now, we'll just log a success message
        
        log.info(f"Land {land_id} inspected by {citizen} for building a {building_type_definition.get('name', 'building')}. The land is suitable.")
        return True
    except Exception as e:
        log.error(f"Error inspecting land: {e}")
        return False

def _create_building_project(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    details: Dict[str, Any],
    building_type_defs: Any
) -> bool:
    """Create a building project when the submit_building_project activity is processed."""
    fields = activity_record.get('fields', {})
    citizen = fields.get('Citizen')
    office_building_id = fields.get('FromBuilding')  # We're at the office now
    land_id = details.get('landId')
    building_type_definition = details.get('buildingTypeDefinition')
    point_details = details.get('pointDetails')
    builder_contract_details = details.get('builderContractDetails')  # Optional
    
    if not (citizen and office_building_id and land_id and building_type_definition and point_details):
        log.error(f"Missing data for submit_building_project: citizen={citizen}, office={office_building_id}, land={land_id}")
        return False
    
    # Get the building type details
    building_type = building_type_definition.get('id')
    if not building_type or building_type not in building_type_defs:
        log.error(f"Invalid building type: {building_type}")
        return False
    
    building_type_info = building_type_defs.get(building_type, {})
    building_category = building_type_info.get('category') # Get category
    building_subcategory = building_type_info.get('subCategory') # Get subCategory

    now = datetime.utcnow()
    building_id = f"building_{point_details.get('lat')}_{point_details.get('lng')}"
    building_name_default = building_type_info.get('name', building_type.replace('_', ' ').title())

    permit_fee_already_paid = False
    building_shell_exists_and_matches = False
    existing_building_airtable_id = None
    existing_building_record_fields = None

    # Check for existing building shell
    try:
        existing_building_records = tables['buildings'].all(formula=f"{{BuildingId}}='{_escape_airtable_value(building_id)}'", max_records=1)
        if existing_building_records:
            existing_building_record_data = existing_building_records[0]
            existing_building_record_fields = existing_building_record_data['fields']
            if (existing_building_record_fields.get('Owner') == citizen and
                existing_building_record_fields.get('Type') == building_type and
                not existing_building_record_fields.get('IsConstructed')):
                permit_fee_already_paid = True
                building_shell_exists_and_matches = True
                existing_building_airtable_id = existing_building_record_data['id']
                log.info(f"Projet de construction existant et correspondant trouvé pour {building_id}. Les frais de permis seront ignorés.")
            else:
                log.error(f"Un bâtiment existe à {building_id} mais ne correspond pas au propriétaire/type ou est déjà construit. Impossible d'initier un nouveau projet ici.")
                return False # Point de construction incompatible
    except Exception as e_fetch_existing_bldg:
        log.error(f"Erreur lors de la vérification du bâtiment existant {building_id}: {e_fetch_existing_bldg}")
        return False
    
    # Calculate permit fee (typically 5% of building cost, minimum 50 Ducats)
    # buildCost might be nested under constructionCosts in some definitions
    construction_costs_from_def = building_type_info.get('constructionCosts', {})
    building_cost_ducats = construction_costs_from_def.get('ducats', 1000) # Default to 1000 if not specified
    
    permit_fee_to_charge = 0
    if not permit_fee_already_paid:
        permit_fee_to_charge = max(50, building_cost_ducats * 0.05)  # 5% fee, minimum 50 Ducats
    
    # If there's a builder contract, determine its value.
    builder_username_from_details = None
    actual_contract_value_for_builder = 0
    payment_to_builder_this_run = 0 # This will hold the amount to pay the builder now

    if builder_contract_details:
        builder_username_from_details = builder_contract_details.get('builderUsername')
        contract_value_from_details = builder_contract_details.get('contractValue')

        MIN_BUILDER_PAYMENT_ABSOLUTE = 50.0
        MIN_BUILDER_PAYMENT_RELATIVE_TO_COST = 0.01 # 1% of building cost

        use_explicit_contract_value = False
        if contract_value_from_details is not None:
            parsed_contract_value = float(contract_value_from_details)
            is_above_absolute_min = parsed_contract_value >= MIN_BUILDER_PAYMENT_ABSOLUTE
            is_above_relative_min = parsed_contract_value >= (building_cost_ducats * MIN_BUILDER_PAYMENT_RELATIVE_TO_COST)

            if parsed_contract_value > 0 and is_above_absolute_min and is_above_relative_min:
                actual_contract_value_for_builder = parsed_contract_value
                use_explicit_contract_value = True
                log.info(f"Using provided contractValue for builder: {actual_contract_value_for_builder}")
            else:
                if parsed_contract_value <= 0:
                    log.warning(f"Provided contractValue {parsed_contract_value} is zero or negative. Falling back.")
                else:
                    log.warning(f"Provided contractValue {parsed_contract_value} is considered too low (Absolute Min: {MIN_BUILDER_PAYMENT_ABSOLUTE}, Relative Min: {building_cost_ducats * MIN_BUILDER_PAYMENT_RELATIVE_TO_COST}). Falling back to rate or default rate.")
        
        if not use_explicit_contract_value: # contract_value_from_details was None, or was too low/zero
            rate_from_details = builder_contract_details.get('rate')
            if rate_from_details is not None:
                parsed_rate = float(rate_from_details)
                if parsed_rate > 0:
                    actual_contract_value_for_builder = building_cost_ducats * parsed_rate
                    log.info(f"Using provided rate for builder: {parsed_rate} * {building_cost_ducats} = {actual_contract_value_for_builder}")
                else:
                    log.warning(f"Provided rate {parsed_rate} is zero or negative. Falling back to default rate.")
                    actual_contract_value_for_builder = building_cost_ducats * 1.2 
                    log.info(f"Using default rate 1.2 for builder: 1.2 * {building_cost_ducats} = {actual_contract_value_for_builder}")
            else: # contract_value_from_details was None/low/zero AND rate_from_details is None
                actual_contract_value_for_builder = building_cost_ducats * 1.2
                log.info(f"No valid contractValue or rate. Using default rate 1.2 for builder: 1.2 * {building_cost_ducats} = {actual_contract_value_for_builder}")
        
        # Check if this specific builder contract already exists and is active
        skip_builder_contract_creation_and_payment = False
        if building_shell_exists_and_matches and builder_username_from_details:
            formula_contract_check = f"AND({{Asset}}='{_escape_airtable_value(building_id)}', {{Buyer}}='{_escape_airtable_value(citizen)}', {{Seller}}='{_escape_airtable_value(builder_username_from_details)}', NOT(OR({{Status}}='failed', {{Status}}='cancelled', {{Status}}='completed')))"
            existing_builder_contracts = tables['contracts'].all(formula=formula_contract_check, max_records=1)
            if existing_builder_contracts:
                log.info(f"Un contrat de construction actif avec le constructeur {builder_username_from_details} pour le projet {building_id} existe déjà. La création du contrat et le paiement intégral seront ignorés.")
                skip_builder_contract_creation_and_payment = True
        
        if not skip_builder_contract_creation_and_payment and actual_contract_value_for_builder > 0:
            payment_to_builder_this_run = actual_contract_value_for_builder
        else: # Contract creation/payment is skipped, so ensure contract value for new contract is 0 if we were to create one
            actual_contract_value_for_builder = 0 # This prevents creating a new contract with value if skipped
            
    total_cost = permit_fee_to_charge + payment_to_builder_this_run
    
    # Check if citizen has enough Ducats to pay the fees
    try:
        citizen_records = tables['citizens'].all(formula=f"{{Username}}='{_escape_airtable_value(citizen)}'", max_records=1)
        if not citizen_records:
            log.error(f"Citizen {citizen} not found")
            return False
        
        citizen_record = citizen_records[0]
        citizen_ducats = float(citizen_record['fields'].get('Ducats', 0))
        
        if total_cost > 0 and citizen_ducats < total_cost:
            log.error(f"Citizen {citizen} has insufficient Ducats ({citizen_ducats}) to pay total fees ({total_cost}). Permit fee: {permit_fee_to_charge}, Builder Payment: {payment_to_builder_this_run}")
            return False
        
        office_operator = "ConsiglioDeiDieci"  # Default to city government
        if permit_fee_to_charge > 0: # Only find office operator if permit fee is being charged
            building_formula = f"{{BuildingId}}='{_escape_airtable_value(office_building_id)}'"
            buildings = tables["buildings"].all(formula=building_formula, max_records=1)
            if buildings and buildings[0]['fields'].get('RunBy'):
                office_operator = buildings[0]['fields'].get('RunBy')
                log.info(f"Found office operator {office_operator} for building {office_building_id} for permit fee.")
        
        if total_cost > 0: # Deduct if there's any cost
            tables['citizens'].update(citizen_record['id'], {'Ducats': citizen_ducats - total_cost})
            log.info(f"Deducted {total_cost} Ducats from {citizen}. Permit: {permit_fee_to_charge}, Builder Payment: {payment_to_builder_this_run}.")
        
        # Add permit fee to office operator if it was charged
        if permit_fee_to_charge > 0:
            if office_operator != "ConsiglioDeiDieci": # Assuming ConsiglioDeiDieci is a system account not in CITIZENS
                operator_formula = f"{{Username}}='{_escape_airtable_value(office_operator)}'"
                operator_records = tables["citizens"].all(formula=operator_formula, max_records=1)
                if operator_records:
                    operator_record_data = operator_records[0]
                    operator_ducats = float(operator_record_data['fields'].get('Ducats', 0))
                    tables["citizens"].update(operator_record_data['id'], {'Ducats': operator_ducats + permit_fee_to_charge})
            # Record the permit fee transaction
            permit_transaction_fields = {
                "Type": "building_permit_fee", "AssetType": "land", "Asset": land_id,
                "Seller": citizen, "Buyer": office_operator, "Price": permit_fee_to_charge,
                "Notes": json.dumps({"building_type": building_type, "point_details": point_details, "office_building_id": office_building_id}),
                "CreatedAt": now.isoformat(), "ExecutedAt": now.isoformat()
            }
            tables["transactions"].create(permit_transaction_fields)
            log.info(f"Permit fee of {permit_fee_to_charge} Ducats paid by {citizen} to {office_operator}.")

        # Pay builder the full contract value if applicable
        if builder_username_from_details and payment_to_builder_this_run > 0:
            builder_formula = f"{{Username}}='{_escape_airtable_value(builder_username_from_details)}'"
            builder_records = tables["citizens"].all(formula=builder_formula, max_records=1)
            if builder_records:
                builder_record_data = builder_records[0]
                builder_ducats = float(builder_record_data['fields'].get('Ducats', 0))
                tables["citizens"].update(builder_record_data['id'], {'Ducats': builder_ducats + payment_to_builder_this_run})
                # Record the builder payment transaction
                builder_payment_transaction_fields = {
                    "Type": "construction_contract_payment", "AssetType": "building_project", "Asset": building_id,
                    "Seller": citizen, "Buyer": builder_username_from_details, "Price": payment_to_builder_this_run,
                    "Notes": json.dumps({"building_type": building_type, "point_details": point_details, "contract_details": builder_contract_details, "payment_type": "full_upfront"}),
                    "CreatedAt": now.isoformat(), "ExecutedAt": now.isoformat()
                }
                tables["transactions"].create(builder_payment_transaction_fields)
                log.info(f"Full contract value of {payment_to_builder_this_run} Ducats paid by {citizen} to builder {builder_username_from_details}.")
            else:
                log.error(f"Builder {builder_username_from_details} not found. Cannot pay contract value.")
                # This is a critical error, should we revert or proceed?
                # For now, proceeding without payment to builder if builder not found, but this is problematic.
        
        # Determine RunBy for the project
        final_run_by_for_project: Optional[str] = None
        if builder_username_from_details:
            final_run_by_for_project = builder_username_from_details
            log.info(f"Builder {builder_username_from_details} is specified. Setting RunBy for project {building_id} to builder.")
        else:
            log.info(f"No builder specified for project {building_id}. Checking citizen {citizen}'s business building count for RunBy.")
            citizen_business_buildings_formula = f"AND({{RunBy}}='{_escape_airtable_value(citizen)}', {{Category}}='business')"
            try:
                citizen_business_buildings = tables['buildings'].all(formula=citizen_business_buildings_formula)
                num_businesses_run = len(citizen_business_buildings)
                if num_businesses_run > 10:
                    log.info(f"Citizen {citizen} runs {num_businesses_run} businesses (limit 10). Project {building_id} RunBy will be None.")
                    final_run_by_for_project = None 
                else:
                    log.info(f"Citizen {citizen} runs {num_businesses_run} businesses. Setting RunBy for project {building_id} to citizen.")
                    final_run_by_for_project = citizen
            except Exception as e_count_buildings:
                log.error(f"Error counting business buildings for {citizen}: {e_count_buildings}. Defaulting RunBy for project {building_id} to citizen.")
                final_run_by_for_project = citizen # Fallback

        # Create/Update the building record
        construction_minutes = building_type_info.get('constructionMinutes', 60)
        
        if not building_shell_exists_and_matches:
            building_payload = {
                "BuildingId": building_id,
                "Name": f"{building_name_default} (Under Construction)",
                "Type": building_type, "Category": building_category, "SubCategory": building_subcategory,
                "LandId": land_id, "Position": json.dumps(point_details), "Point": json.dumps(point_details),
                "Owner": citizen, "RunBy": final_run_by_for_project,
                "IsConstructed": False, "ConstructionMinutesRemaining": construction_minutes,
                "CreatedAt": now.isoformat()
            }
            created_building = tables["buildings"].create(building_payload)
            log.info(f"Created new building project {building_id} for {citizen} on land {land_id} with RunBy: {final_run_by_for_project}")
        elif existing_building_record_fields and existing_building_airtable_id: # Shell exists, check if RunBy needs update
            current_run_by_on_shell = existing_building_record_fields.get('RunBy')
            if current_run_by_on_shell != final_run_by_for_project:
                tables['buildings'].update(existing_building_airtable_id, {'RunBy': final_run_by_for_project})
                log.info(f"Updated RunBy for existing building project {building_id} from '{current_run_by_on_shell}' to '{final_run_by_for_project}'.")
        
        # Create the builder contract if builder_username_from_details is set and a new contract is needed.
        # The check for skip_builder_contract_creation_and_payment handles if contract already exists.
        # actual_contract_value_for_builder will be > 0 only if a new contract is needed (it's set to 0 if skipping).
        if builder_username_from_details and actual_contract_value_for_builder > 0 and not skip_builder_contract_creation_and_payment:
            contract_id = f"construction_{building_id}_{builder_username_from_details}_{int(now.timestamp())}"
            contract_payload = {
                "ContractId": contract_id, "Type": "construction_project",
                "Buyer": citizen, 
                "Seller": builder_username_from_details, 
                "Asset": building_id, "AssetType": "building",
                "BuyerBuilding": building_id, # Le bâtiment en cours de construction
                "PricePerResource": actual_contract_value_for_builder, "TargetAmount": 1,
                "Status": "pending_materials", "Title": f"Construction of {building_name_default}",
                "Description": f"Contract for the construction of a {building_name_default} on land {land_id}",
                "Notes": json.dumps({"constructionCosts": construction_costs_from_def}),
                "CreatedAt": now.isoformat(), "EndAt": (now + timedelta(days=90)).isoformat()
            }
            # Ajouter SellerBuilding si l'ID de l'atelier du constructeur est fourni
            if builder_contract_details and builder_contract_details.get('builderWorkshopId'):
                contract_payload["SellerBuilding"] = builder_contract_details.get('builderWorkshopId')
            else:
                log.warning(f"builderWorkshopId non fourni dans builderContractDetails pour le contrat {contract_id}. SellerBuilding ne sera pas défini.")

            tables["contracts"].create(contract_payload)
            log.info(f"Created construction contract {contract_id} between {citizen} and {builder_username_from_details}.")
        
        log.info(f"Successfully processed building project submission for {building_type} on land {land_id} by {citizen}.")
        if permit_fee_to_charge > 0:
            log.info(f"Permit fee of {permit_fee_to_charge} Ducats collected.")
        if payment_to_builder_this_run > 0:
            log.info(f"Full contract payment of {payment_to_builder_this_run} Ducats made to builder {builder_username_from_details}.")
        
        return True
    except Exception as e:
        log.error(f"Failed to create building project: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False

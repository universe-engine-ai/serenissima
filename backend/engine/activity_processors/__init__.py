# This file makes the 'activity_processors' directory a Python package.
# IMPORTANT: Activity processors should ONLY process the current activity and NOT create follow-up activities.
# Follow-up activities should be created by activity creators in the activity_creators directory.
# Processors should focus on:
# 1. Executing the effects of the current activity (e.g., transferring resources, updating citizen state)
# 2. Returning success/failure status
# 3. NOT creating new activities (this is the responsibility of activity creators)
#
# In the new architecture:
# - Activity creators are responsible for creating chains of activities
# - Each activity in the chain is processed independently by its processor
# - Processors should not create new activities, even in response to failures
# - If an activity in a chain fails, the processor should mark it as failed
#   and the processActivities.py script will handle marking dependent activities as failed

import logging
log = logging.getLogger(__name__)

from .deliver_resource_batch_processor import process as process_deliver_resource_batch
from .goto_home_processor import process as process_goto_home
from .goto_work_processor import process as process_goto_work
from .production_processor import process as process_production
from .fetch_resource_processor import process as process_fetch_resource
from .eat_processor import process as process_eat # Generic dispatcher for eat activities
from .pickup_from_galley_processor import process as process_pickup_from_galley # Renamed
from .deliver_resource_to_buyer_processor import process as process_deliver_resource_to_buyer # New
from .leave_venice_processor import process as process_leave_venice
from .deliver_construction_materials_processor import process as process_deliver_construction_materials
from .construct_building_processor import process as process_construct_building
from .goto_construction_site_processor import process as process_goto_construction_site
from .deliver_to_storage_processor import process as process_deliver_to_storage
from .fetch_from_storage_processor import process as process_fetch_from_storage
from .goto_building_for_storage_fetch_processor import process as process_goto_building_for_storage_fetch
from .fetch_for_logistics_client_processor import process as process_fetch_for_logistics_client
from .check_business_status_processor import process as process_check_business_status
from .fishing_processor import process_fishing_activity # New fishing activity processor
from .inspect_building_for_purchase_processor import process_inspect_building_for_purchase_fn
from .submit_building_purchase_offer_processor import process_submit_building_purchase_offer_fn
from .send_message_processor import process_send_message_fn
from .goto_location_activity_processor import process_goto_location_fn # Changed import path and removed alias as function name matches
from .manage_guild_membership_processor import process_manage_guild_membership_fn as process_manage_guild_membership
from .execute_respond_to_building_bid_processor import process_execute_respond_to_building_bid_fn 
from .execute_withdraw_building_bid_processor import process_execute_withdraw_building_bid_fn 
from .finalize_manage_markup_buy_contract_processor import process_finalize_manage_markup_buy_contract_fn 
from .finalize_manage_storage_query_contract_processor import process_finalize_manage_storage_query_contract_fn
from .finalize_update_citizen_profile_processor import process_finalize_update_citizen_profile_fn # New
from .manage_public_dock_processor import process as process_manage_public_dock # Corrected import
from .process_work_on_art import process_work_on_art_fn # Import for Artisti work
from .read_book_processor import process_read_book_fn # Import for reading books
from .goto_inn_processor import process as process_goto_inn # Import for goto_inn
from .deposit_items_at_location_processor import process as process_deposit_items_at_location # New processor
from .attend_theater_performance_processor import process as process_attend_theater_performance # New theater processor
from .drink_at_inn_activity_processor import process as process_drink_at_inn # New drink at inn processor
from .use_public_bath_processor import process as process_use_public_bath # New public bath processor
from .rest_processor import process as process_rest # New rest processor
from .occupant_self_construction_processor import process_occupant_self_construction_fn # New occupant self-construction processor
from .spread_rumor_activity_processor import process as process_spread_rumor_fn # New processor for spreading rumors
from .attend_mass_processor import process_attend_mass_fn # New processor for attending mass
from .prepare_sermon_processor import process as process_prepare_sermon # New processor for preparing sermons

# Imports pour les processeurs de terrains et contrats
from .bid_on_land_activity_processor import process_bid_on_land_fn
from .manage_public_sell_contract_processor import process_manage_public_sell_contract_fn
from .manage_import_contract_processor import process_manage_import_contract_fn
from .manage_public_import_contract_processor import process_manage_public_import_contract_fn
from .manage_logistics_service_contract_processor import process_manage_logistics_service_contract_fn
from .buy_available_land_processor import process_buy_available_land_fn
from .initiate_building_project_processor import process_initiate_building_project_fn
from .adjust_land_lease_price_processor import process_adjust_land_lease_price_fn
from .adjust_building_rent_price_processor import process_adjust_building_rent_price_fn
from .adjust_building_lease_price_processor import process_file_building_lease_adjustment_fn
from .adjust_business_wages_processor import process_adjust_business_wages_fn
from .change_business_manager_processor import process_change_business_manager_fn
from .request_loan_processor import process_request_loan_fn
from .offer_loan_processor import process_offer_loan_fn
from .reply_to_message_processor import process_reply_to_message_fn
from .manage_public_storage_contract_processor import process_register_public_storage_offer_fn
from .list_land_for_sale_processor import process_list_land_for_sale_fn
from .make_offer_for_land_processor import process_make_offer_for_land_fn
from .accept_land_offer_processor import process_accept_land_offer_fn
from .buy_listed_land_processor import process_buy_listed_land_fn
from .cancel_land_listing_processor import process_cancel_land_listing_fn
from .cancel_land_offer_processor import process_cancel_land_offer_fn

# Fonction de traitement générique pour les activités simples
def process_placeholder_activity_fn(tables, activity_record, building_type_defs, resource_defs, api_base_url=None):
    """Processeur générique pour les activités simples qui n'ont pas besoin de logique spécifique."""
    activity_guid = activity_record['fields'].get('ActivityId', activity_record['id'])
    activity_type = activity_record['fields'].get('Type')
    log.info(f"Activité {activity_guid} (type: {activity_type}) traitée par le processeur générique.")
    return True
# Add other processors here as they are created

# Dictionary mapping activity types to their processor functions
ACTIVITY_PROCESSORS = {
    'deliver_resource_batch': process_deliver_resource_batch,
    'goto_home': process_goto_home,
    'goto_work': process_goto_work,
    'production': process_production,
    'fetch_resource': process_fetch_resource,
    'eat_from_inventory': process_eat,
    'eat_at_home': process_eat,
    'eat_at_tavern': process_eat,
    'pickup_from_galley': process_pickup_from_galley,
    'deliver_resource_to_buyer': process_deliver_resource_to_buyer,
    'leave_venice': process_leave_venice,
    'deliver_construction_materials': process_deliver_construction_materials,
    'construct_building': process_construct_building,
    'goto_construction_site': process_goto_construction_site,
    'deliver_to_storage': process_deliver_to_storage,
    'fetch_from_storage': process_fetch_from_storage,
    'goto_building_for_storage_fetch': process_goto_building_for_storage_fetch,
    'fetch_for_logistics_client': process_fetch_for_logistics_client,
    'check_business_status': process_check_business_status,
    'fishing': process_fishing_activity,
    'emergency_fishing': process_fishing_activity,
    'inspect_building_for_purchase': process_inspect_building_for_purchase_fn,
    'submit_building_purchase_offer': process_submit_building_purchase_offer_fn,
    'send_message': process_send_message_fn,
    'goto_location': process_goto_location_fn,
    'manage_guild_membership': process_manage_guild_membership,
    'respond_to_building_bid': process_execute_respond_to_building_bid_fn,
    'withdraw_building_bid': process_execute_withdraw_building_bid_fn,
    'manage_markup_buy_contract': process_finalize_manage_markup_buy_contract_fn,
    'manage_storage_query_contract': process_finalize_manage_storage_query_contract_fn,
    'update_citizen_profile': process_finalize_update_citizen_profile_fn,
    'manage_public_dock': process_manage_public_dock,
    'work_on_art': process_work_on_art_fn,
    'read_book': process_read_book_fn,
    'goto_inn': process_goto_inn,
    'deposit_items_at_location': process_deposit_items_at_location,
    'attend_theater_performance': process_attend_theater_performance,
    'drink_at_inn': process_drink_at_inn,
    'use_public_bath': process_use_public_bath,
    'rest': process_rest,
    'occupant_self_construction': process_occupant_self_construction_fn,
    # Ajout des processeurs pour les activités liées aux terrains et aux contrats
    'bid_on_land': process_bid_on_land_fn,
    'submit_land_bid': process_bid_on_land_fn,
    'prepare_goods_for_sale': process_manage_public_sell_contract_fn,
    'register_public_sell_offer': process_manage_public_sell_contract_fn,
    'assess_import_needs': process_manage_import_contract_fn,
    'register_import_agreement': process_manage_import_contract_fn,
    'register_public_import_agreement': process_manage_public_import_contract_fn,
    'assess_logistics_needs': process_manage_logistics_service_contract_fn,
    'register_logistics_service_contract': process_manage_logistics_service_contract_fn,
    'finalize_land_purchase': process_buy_available_land_fn,
    'inspect_land_plot': process_initiate_building_project_fn,
    'submit_building_project': process_initiate_building_project_fn,
    'file_lease_adjustment': process_adjust_land_lease_price_fn,
    'file_rent_adjustment': process_adjust_building_rent_price_fn,
    'file_building_lease_adjustment': process_file_building_lease_adjustment_fn,
    'update_wage_ledger': process_adjust_business_wages_fn,
    'finalize_operator_change': process_change_business_manager_fn,
    'submit_loan_application_form': process_request_loan_fn,
    'register_loan_offer_terms': process_offer_loan_fn,
    'deliver_message_interaction': process_send_message_fn,
    'reply_to_message': process_reply_to_message_fn,
    'perform_guild_membership_action': process_manage_guild_membership,
    'register_public_storage_offer': process_register_public_storage_offer_fn,
    'finalize_list_land_for_sale': process_list_land_for_sale_fn,
    'finalize_make_offer_for_land': process_make_offer_for_land_fn,
    'execute_accept_land_offer': process_accept_land_offer_fn,
    'execute_buy_listed_land': process_buy_listed_land_fn,
    'execute_cancel_land_listing': process_cancel_land_listing_fn,
    'execute_cancel_land_offer': process_cancel_land_offer_fn,
    'spread_rumor': process_spread_rumor_fn,
    'attend_mass': process_attend_mass_fn,
    'prepare_sermon': process_prepare_sermon,
    'idle': process_placeholder_activity_fn,
    'secure_warehouse': process_placeholder_activity_fn,
}

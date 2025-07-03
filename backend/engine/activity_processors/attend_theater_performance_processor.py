import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_building_record,
    update_citizen_ducats,
    VENICE_TIMEZONE
)
from backend.engine.utils.relationship_helpers import (
    update_trust_score_for_activity,
    TRUST_SCORE_MINOR_POSITIVE
)
from backend.engine.utils.process_helper import (
    create_process,
    PROCESS_TYPE_THEATER_REFLECTION
)

log = logging.getLogger(__name__)

# Prices and influence based on social class - these are also in the creator,
# but the processor should re-evaluate based on current class at time of processing.
THEATER_COSTS = {
    "Facchini": 100, "Popolani": 200, "Cittadini": 500,
    "Nobili": 1000, "Forestieri": 700, "Artisti": 300
}
THEATER_INFLUENCE_GAIN = {
    "Facchini": 1, "Popolani": 2, "Cittadini": 5,
    "Nobili": 10, "Forestieri": 7, "Artisti": 4
}
DEFAULT_THEATER_COST = 200
DEFAULT_THEATER_INFLUENCE = 2

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any], # Not directly used here but part of signature
    resource_defs: Dict[str, Any],      # Not directly used here but part of signature
    api_base_url: Optional[str] = None
) -> bool:
    activity_fields = activity_record['fields']
    activity_guid = activity_fields.get('ActivityId', activity_record['id'])
    citizen_username = activity_fields.get('Citizen')
    notes_str = activity_fields.get('Notes')

    log.info(f"{LogColors.ACTIVITY}🎭 Traitement de 'attend_theater_performance': {activity_guid} pour {citizen_username}.{LogColors.ENDC}")

    if not citizen_username or not notes_str:
        log.error(f"{LogColors.FAIL}Activité {activity_guid} manque Citizen ou Notes. Abandon.{LogColors.ENDC}")
        return False

    try:
        activity_details = json.loads(notes_str)
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Impossible de parser Notes JSON pour l'activité {activity_guid}: {notes_str}{LogColors.ENDC}")
        return False

    theater_id = activity_details.get("theater_id")
    theater_name = activity_details.get("theater_name", "un théâtre inconnu")

    citizen_airtable_record = get_citizen_record(tables, citizen_username)
    if not citizen_airtable_record:
        log.error(f"{LogColors.FAIL}Citoyen {citizen_username} non trouvé pour l'activité {activity_guid}. Abandon.{LogColors.ENDC}")
        return False
    
    citizen_social_class = citizen_airtable_record['fields'].get('SocialClass', 'Popolani')
    cost = THEATER_COSTS.get(citizen_social_class, DEFAULT_THEATER_COST)
    influence_gain = THEATER_INFLUENCE_GAIN.get(citizen_social_class, DEFAULT_THEATER_INFLUENCE)
    
    current_ducats = float(citizen_airtable_record['fields'].get('Ducats', 0.0))
    current_influence = float(citizen_airtable_record['fields'].get('Influence', 0.0))

    if current_ducats < cost:
        log.warning(f"{LogColors.WARNING}Citoyen {citizen_username} n'a pas assez de Ducats ({current_ducats:.2f}) pour le théâtre ({cost:.2f}). Activité échouée.{LogColors.ENDC}")
        return False

    # --- Récupérer les détails de la pièce et de l'artiste ---
    artist_username_from_api = None
    play_name_from_api = "Pièce inconnue"
    if api_base_url and theater_id:
        try:
            import requests # Import here to avoid global dependency
            representation_url = f"{api_base_url}/api/get-theater-current-representation?buildingId={theater_id}"
            response = requests.get(representation_url, timeout=30) # Increased timeout to 30 seconds
            response.raise_for_status()
            representation_data = response.json()
            if representation_data.get("success") and representation_data.get("representation"):
                artist_username_from_api = representation_data["representation"].get("artist")
                play_name_from_api = representation_data["representation"].get("name", play_name_from_api)
                log.info(f"Pièce actuelle à {theater_name}: '{play_name_from_api}' par {artist_username_from_api or 'Artiste inconnu'}.")
                
                # Store play content for the reflection process
                if representation_data["representation"].get("content"):
                    activity_details["play_content"] = representation_data["representation"].get("content")
                    activity_details["play_name"] = play_name_from_api
                    activity_details["play_artist"] = artist_username_from_api
            else:
                log.warning(f"Impossible de récupérer la représentation actuelle pour {theater_id}: {representation_data.get('error')}")
        except Exception as e_repr:
            log.error(f"Erreur lors de la récupération de la représentation pour {theater_id}: {e_repr}")
    else:
        log.warning("api_base_url ou theater_id manquant, impossible de récupérer les détails de la pièce.")

    # --- Logique de paiement ---
    # 1. Déduire le coût du citoyen
    try:
        tables['citizens'].update(citizen_airtable_record['id'], {'Ducats': current_ducats - cost})
        log.info(f"Ducats de {citizen_username} déduits: {current_ducats:.2f} -> {current_ducats - cost:.2f} (-{cost:.2f}).")
    except Exception as e_deduct:
        log.error(f"{LogColors.FAIL}Échec de la déduction des Ducats pour {citizen_username}: {e_deduct}{LogColors.ENDC}")
        return False # Échec critique

    # 2. Distribuer les revenus
    artist_share = 0.0
    operator_share = cost # Par défaut, tout va à l'opérateur

    if artist_username_from_api:
        artist_record = get_citizen_record(tables, artist_username_from_api)
        if artist_record:
            artist_share = round(cost * 0.30, 2)
            operator_share = round(cost - artist_share, 2)
            
            current_artist_ducats = float(artist_record['fields'].get('Ducats', 0.0))
            try:
                tables['citizens'].update(artist_record['id'], {'Ducats': current_artist_ducats + artist_share})
                log.info(f"Part de l'artiste ({artist_share:.2f} Ducats) versée à {artist_username_from_api}.")
                # Créer une transaction pour l'artiste
                tables['transactions'].create({
                    "Type": "artist_royalty_theater", "Seller": artist_username_from_api, "Buyer": citizen_username,
                    "Price": artist_share, "AssetType": "theater_performance", "Asset": theater_id,
                    "Notes": f"Part d'artiste pour '{play_name_from_api}' à {theater_name} (Payeur: {citizen_username})",
                    "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(), "ExecutedAt": datetime.now(VENICE_TIMEZONE).isoformat()
                })
                # Mettre à jour la confiance avec l'artiste
                update_trust_score_for_activity(tables, citizen_username, artist_username_from_api, TRUST_SCORE_MINOR_POSITIVE, "artist_payment_received", True, f"play_{play_name_from_api.replace(' ','_')}", activity_record)
            except Exception as e_artist_payment:
                log.error(f"Échec du versement de la part à l'artiste {artist_username_from_api}: {e_artist_payment}. Sa part sera reversée à l'opérateur.")
                operator_share = cost # L'opérateur reçoit tout si le paiement à l'artiste échoue
        else:
            log.warning(f"Artiste {artist_username_from_api} non trouvé. Sa part sera reversée à l'opérateur.")
            operator_share = cost # L'opérateur reçoit tout si l'artiste n'est pas trouvé

    # Payer l'opérateur du théâtre
    theater_building_record = get_building_record(tables, theater_id) # Peut être None si le théâtre a été supprimé entre-temps
    if theater_building_record:
        theater_operator_username = theater_building_record['fields'].get('RunBy') or theater_building_record['fields'].get('Owner')
        if theater_operator_username:
            operator_record = get_citizen_record(tables, theater_operator_username)
            if operator_record:
                current_operator_ducats = float(operator_record['fields'].get('Ducats', 0.0))
                try:
                    tables['citizens'].update(operator_record['id'], {'Ducats': current_operator_ducats + operator_share})
                    log.info(f"Part de l'opérateur ({operator_share:.2f} Ducats) versée à {theater_operator_username}.")
                    # Créer une transaction pour l'opérateur
                    tables['transactions'].create({
                        "Type": "theater_ticket_revenue", "Seller": theater_operator_username, "Buyer": citizen_username,
                        "Price": operator_share, "AssetType": "theater_performance", "Asset": theater_id,
                        "Notes": f"Revenu du billet pour '{play_name_from_api}' à {theater_name} (Payeur: {citizen_username})",
                        "CreatedAt": datetime.now(VENICE_TIMEZONE).isoformat(), "ExecutedAt": datetime.now(VENICE_TIMEZONE).isoformat()
                    })
                    # Mettre à jour la confiance avec l'opérateur (déjà fait plus bas, mais on pourrait le faire ici aussi)
                except Exception as e_operator_payment:
                    log.error(f"Échec du versement de la part à l'opérateur {theater_operator_username}: {e_operator_payment}.")
                    # L'argent du citoyen a déjà été déduit. Que faire de operator_share ? Pour l'instant, "perdu".
            else:
                log.error(f"Opérateur du théâtre {theater_operator_username} non trouvé. Impossible de verser sa part.")
        else:
            log.error(f"Théâtre {theater_name} ({theater_id}) n'a pas d'opérateur (RunBy/Owner). Impossible de verser les revenus.")
    else:
        log.error(f"Théâtre {theater_name} ({theater_id}) non trouvé. Impossible de verser les revenus à l'opérateur.")


    # --- Add influence ---
    new_influence = current_influence + influence_gain
    try:
        tables['citizens'].update(citizen_airtable_record['id'], {'Influence': new_influence})
        log.info(f"{LogColors.OKGREEN}Influence de {citizen_username} mise à jour: {current_influence:.2f} -> {new_influence:.2f} (+{influence_gain:.2f}) après la représentation à {theater_name}.{LogColors.ENDC}")
    except Exception as e_influence:
        log.error(f"{LogColors.FAIL}Échec de la mise à jour de l'influence pour {citizen_username}: {e_influence}{LogColors.ENDC}")

    # --- Update trust with theater operator (if applicable and different from artist) ---
    if theater_building_record and theater_operator_username and theater_operator_username != artist_username_from_api:
        if theater_operator_username != citizen_username: # Ne pas mettre à jour la confiance avec soi-même
            update_trust_score_for_activity(
                tables,
                citizen_username, 
                theater_operator_username, 
                TRUST_SCORE_MINOR_POSITIVE,
                "theater_attendance_operator", # Note distincte pour l'opérateur
                True, 
                f"attended_performance_at_{theater_id.replace('_','-')}",
                activity_record_for_kinos=activity_record 
            )

    log.info(f"{LogColors.OKGREEN}Activité 'attend_theater_performance' {activity_guid} pour {citizen_username} à {theater_name} traitée avec succès (paiements et influence). Création d'un processus de réflexion.{LogColors.ENDC}")

    # --- Create a process for theater reflection ---
    process_details = {
        "activity_id": activity_record['id'],
        "activity_guid": activity_guid,
        "activity_details": activity_details,
        "theater_id": theater_id,
        "theater_name": theater_name,
        "play_name": play_name_from_api,
        "artist_username": artist_username_from_api
    }
    
    # Check if 'processes' table exists before creating process
    from backend.engine.utils.process_helper import is_processes_table_available
    
    if not is_processes_table_available(tables):
        log.error(f"{LogColors.FAIL}Cannot create theater reflection process for {citizen_username} - 'processes' table not available or is not properly initialized.{LogColors.ENDC}")
        log.info(f"{LogColors.WARNING}Attempting to reinitialize tables to get a working processes table...{LogColors.ENDC}")
        
        # Try to reinitialize the tables
        try:
            from backend.engine.utils.activity_helpers import get_tables
            new_tables = get_tables()
            if is_processes_table_available(new_tables):
                log.info(f"{LogColors.OKGREEN}Successfully reinitialized tables and found working 'processes' table. Attempting to create process with new tables.{LogColors.ENDC}")
                # Include api_base_url in process_details
                if api_base_url:
                    process_details["api_base_url"] = api_base_url
                
                process_record = create_process(
                    tables=new_tables,
                    process_type=PROCESS_TYPE_THEATER_REFLECTION,
                    citizen_username=citizen_username,
                    priority=5,  # Medium priority
                    details=process_details
                )
                if process_record:
                    log.info(f"{LogColors.OKGREEN}Successfully created theater reflection process for {citizen_username} after table reinitialization.{LogColors.ENDC}")
                else:
                    log.warning(f"{LogColors.WARNING}Failed to create theater reflection process for {citizen_username} even after table reinitialization.{LogColors.ENDC}")
            else:
                log.error(f"{LogColors.FAIL}Failed to get working 'processes' table even after reinitialization. Process creation failed.{LogColors.ENDC}")
        except Exception as e_reinit:
            log.error(f"{LogColors.FAIL}Error reinitializing tables: {e_reinit}{LogColors.ENDC}")
    else:
        try:
            # Include api_base_url in process_details
            if api_base_url:
                process_details["api_base_url"] = api_base_url
            
            process_record = create_process(
                tables=tables,
                process_type=PROCESS_TYPE_THEATER_REFLECTION,
                citizen_username=citizen_username,
                priority=5,  # Medium priority
                details=process_details
            )
            if process_record:
                log.info(f"{LogColors.OKGREEN}Successfully created theater reflection process for {citizen_username}.{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Failed to create theater reflection process for {citizen_username}.{LogColors.ENDC}")
        except Exception as e:
            log.error(f"{LogColors.FAIL}Error creating theater reflection process for {citizen_username}: {e}{LogColors.ENDC}")

    return True

# This function is no longer needed as we're using the process system

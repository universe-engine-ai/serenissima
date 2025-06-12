import logging
import json
import requests # Ajout de requests
import os # Ajout de os pour KINOS_API_KEY
import threading # Ajout de threading pour KinOS
from datetime import datetime # Ajout de datetime
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    get_citizen_record,
    get_building_record, # Ajout de l'importation
    update_citizen_ducats,
    VENICE_TIMEZONE # For potential future use with LastLeisureAt
)
from backend.engine.utils.relationship_helpers import (
    update_trust_score_for_activity,
    TRUST_SCORE_MINOR_POSITIVE
)
from backend.engine.utils.conversation_helper import persist_message # Added import

log = logging.getLogger(__name__)

# KinOS constants
KINOS_API_URL = "https://api.kinos-engine.ai" # Always use production KinOS API
KINOS_BLUEPRINT = "serenissima-ai"
KINOS_API_KEY = os.getenv("KINOS_API_KEY")

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
            representation_url = f"{api_base_url}/api/get-theater-current-representation?buildingId={theater_id}"
            response = requests.get(representation_url, timeout=30) # Increased timeout to 30 seconds
            response.raise_for_status()
            representation_data = response.json()
            if representation_data.get("success") and representation_data.get("representation"):
                artist_username_from_api = representation_data["representation"].get("artist")
                play_name_from_api = representation_data["representation"].get("name", play_name_from_api)
                log.info(f"Pièce actuelle à {theater_name}: '{play_name_from_api}' par {artist_username_from_api or 'Artiste inconnu'}.")
            else:
                log.warning(f"Impossible de récupérer la représentation actuelle pour {theater_id}: {representation_data.get('error')}")
        except requests.exceptions.RequestException as e_req:
            log.error(f"Erreur API lors de la récupération de la représentation pour {theater_id}: {e_req}")
        except Exception as e_repr:
            log.error(f"Erreur inattendue lors de la récupération de la représentation pour {theater_id}: {e_repr}")
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

    log.info(f"{LogColors.OKGREEN}Activité 'attend_theater_performance' {activity_guid} pour {citizen_username} à {theater_name} traitée avec succès (paiements et influence). Lancement de la réflexion KinOS.{LogColors.ENDC}")

    # --- KinOS Reflection (asynchrone) ---
    if not KINOS_API_KEY:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY non défini. Impossible de déclencher la réflexion KinOS pour 'attend_theater_performance' {activity_guid}.{LogColors.ENDC}")
    else:
        try:
            play_content_from_api = "Contenu de la pièce non disponible."
            if 'representation_data' in locals() and representation_data.get("success") and representation_data.get("representation"):
                play_content_from_api = representation_data["representation"].get("content", play_content_from_api)

            # Récupérer le data package du citoyen
            data_package_json_str = None
            if api_base_url:
                data_package_url = f"{api_base_url}/api/get-data-package?citizenUsername={citizen_username}"
                try:
                    pkg_response = requests.get(data_package_url, timeout=15)
                    if pkg_response.ok:
                        pkg_data = pkg_response.json()
                        if pkg_data.get("success"):
                            data_package_json_str = json.dumps(pkg_data.get("data"))
                            log.info(f"  Récupération réussie du data package pour {citizen_username} pour la réflexion sur le théâtre.")
                    else:
                        log.warning(f"  Échec de la récupération du data package pour {citizen_username} (théâtre): {pkg_response.status_code}")
                except Exception as e_pkg_fetch:
                    log.error(f"  Erreur lors de la récupération du data package pour {citizen_username} (théâtre): {e_pkg_fetch}")
            
            kinos_build_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/build"
            
            kinos_prompt_theater = (
                f"Vous êtes {citizen_username}, un citoyen de Venise à la Renaissance. Vous venez d'assister à une représentation théâtrale intitulée '{play_name_from_api}' par l'artiste {artist_username_from_api or 'inconnu'}. "
                f"Le contenu/résumé de la pièce (si disponible) et vos données personnelles sont fournis dans `addSystem` sous `play_context` et `citizen_context`.\n\n"
                f"Réfléchissez à la pièce que vous venez de voir. Considérez :\n"
                f"- Quels étaient les thèmes principaux ou les messages de la pièce (voir `addSystem.play_context.content`) ?\n"
                f"- Y a-t-il eu des éléments qui vous ont particulièrement marqué, interpellé ou inspiré ?\n"
                f"- Comment les idées ou émotions suscitées par cette pièce pourraient-elles influencer vos pensées, décisions ou actions futures concernant votre vie, travail, relations ou ambitions à Venise (référez-vous à `addSystem.citizen_context`) ?\n\n"
                f"Votre réflexion doit être personnelle et introspective. Utilisez votre situation actuelle, vos objectifs et votre personnalité (détaillés dans `addSystem.citizen_context`) pour contextualiser vos pensées sur la pièce."
            )

            structured_add_system_payload_theater: Dict[str, Any] = {
                "citizen_context": None,
                "play_context": {
                    "title": play_name_from_api,
                    "artist": artist_username_from_api or "Artiste inconnu",
                    "content": play_content_from_api
                }
            }
            if data_package_json_str:
                try:
                    structured_add_system_payload_theater["citizen_context"] = json.loads(data_package_json_str)
                except json.JSONDecodeError:
                    log.error("  Échec du parsing de data_package_json_str pour citizen_context (théâtre). Contexte citoyen incomplet.")
                    structured_add_system_payload_theater["citizen_context"] = {"error_parsing_data_package": True, "status": "unavailable"}
            else:
                structured_add_system_payload_theater["citizen_context"] = {"status": "unavailable_no_data_package_fetched"}

            kinos_payload_dict_theater: Dict[str, Any] = {
                "message": kinos_prompt_theater,
                "model": "local", # Ou choisir le modèle basé sur la classe sociale/tâche
                "addSystem": json.dumps(structured_add_system_payload_theater)
            }

            log.info(f"  Lancement de l'appel KinOS /build asynchrone pour la réflexion sur le théâtre par {citizen_username} à {kinos_build_url}")
            
            kinos_thread_theater = threading.Thread(
                target=_call_kinos_build_for_theater_reflection_async,
                args=(kinos_build_url, kinos_payload_dict_theater, tables, activity_record['id'], activity_guid, activity_details, citizen_username)
            )
            kinos_thread_theater.start()
            log.info(f"  Appel KinOS /build pour la réflexion sur le théâtre par {citizen_username} démarré dans le thread {kinos_thread_theater.ident}.")

        except Exception as e_kinos_setup:
            log.error(f"{LogColors.FAIL}Erreur lors de la configuration de l'appel KinOS pour la réflexion sur le théâtre {activity_guid}: {e_kinos_setup}{LogColors.ENDC}")
            import traceback
            log.error(traceback.format_exc())
            # Ne pas retourner False ici, l'activité principale est traitée.

    return True

def _call_kinos_build_for_theater_reflection_async(
    kinos_build_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any],
    activity_id_airtable: str,
    activity_guid_log: str,
    original_activity_notes_dict: Dict[str, Any],
    citizen_username_log: str
):
    """
    Effectue l'appel KinOS /build pour la réflexion sur le théâtre et met à jour les notes de l'activité.
    Cette fonction est destinée à être exécutée dans un thread séparé.
    """
    log.info(f"  [Thread Théâtre: {threading.get_ident()}] Appel KinOS /build pour la réflexion sur le théâtre par {citizen_username_log} à {kinos_build_url}")
    try:
        kinos_response = requests.post(kinos_build_url, json=kinos_payload, timeout=120)
        kinos_response.raise_for_status()
        
        kinos_response_data = kinos_response.json()
        log.info(f"  [Thread Théâtre: {threading.get_ident()}] Réponse KinOS /build (théâtre) pour {citizen_username_log}: Statut: {kinos_response_data.get('status')}, Réponse: {kinos_response_data.get('response')}")
        
        raw_reflection = kinos_response_data.get('response', "Aucune réflexion sur le théâtre de KinOS.")
        
        # Persist the raw reflection as a self-message (thought)
        # persist_message will handle cleaning based on the type "kinos_theater_reflection"
        persist_message(
            tables=tables,
            sender_username=citizen_username_log,
            receiver_username=citizen_username_log,
            content=raw_reflection,
            message_type="kinos_theater_reflection",
            channel_name=citizen_username_log # Private channel for self-thoughts
        )
        log.info(f"  [Thread Théâtre: {threading.get_ident()}] Réflexion sur le théâtre persistée comme message à soi-même pour {citizen_username_log}.")

        # Update activity notes (optional, kept for now)
        # Importer clean_thought_content ici car c'est un thread séparé
        from backend.engine.utils.activity_helpers import clean_thought_content # Keep for notes if needed
        cleaned_reflection_for_notes = clean_thought_content(tables, raw_reflection) # Clean separately for notes

        original_activity_notes_dict['kinos_theater_reflection'] = cleaned_reflection_for_notes
        original_activity_notes_dict['kinos_theater_reflection_status'] = kinos_response_data.get('status', 'unknown')
        
        new_notes_json = json.dumps(original_activity_notes_dict)

        try:
            tables['activities'].update(activity_id_airtable, {'Notes': new_notes_json})
            log.info(f"  [Thread Théâtre: {threading.get_ident()}] Notes de l'activité mises à jour avec la réflexion KinOS sur le théâtre pour {activity_guid_log}.")
        except Exception as e_airtable_update:
            log.error(f"  [Thread Théâtre: {threading.get_ident()}] Erreur lors de la mise à jour des notes Airtable pour l'activité {activity_guid_log} (réflexion théâtre): {e_airtable_update}")
            
    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread Théâtre: {threading.get_ident()}] Erreur lors de l'appel KinOS /build (théâtre) pour {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = kinos_response.text[:200] if 'kinos_response' in locals() and hasattr(kinos_response, 'text') else 'N/A'
        log.error(f"  [Thread Théâtre: {threading.get_ident()}] Erreur de décodage JSON de la réponse KinOS /build (théâtre) pour {citizen_username_log}: {e_json_kinos}. Réponse: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread Théâtre: {threading.get_ident()}] Erreur inattendue dans le thread d'appel KinOS pour la réflexion sur le théâtre par {citizen_username_log}: {e_thread}")

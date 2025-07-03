# Constantes pour les montants de changement de TrustScore
TRUST_SCORE_SUCCESS_SIMPLE = 1.0
TRUST_SCORE_FAILURE_SIMPLE = -1.0
TRUST_SCORE_SUCCESS_MEDIUM = 2.0
TRUST_SCORE_FAILURE_MEDIUM = -2.0
TRUST_SCORE_SUCCESS_HIGH = 5.0
TRUST_SCORE_FAILURE_HIGH = -5.0
TRUST_SCORE_PROGRESS = 0.5
TRUST_SCORE_MINOR_POSITIVE = 0.2
TRUST_SCORE_MINOR_NEGATIVE = -0.5

# Facteur d'échelle pour la conversion entre scores latents et scores normalisés (0-100)
# Une valeur plus petite signifie une saturation plus rapide des scores normalisés.
# Exemple : si latent_score * scale_factor = 1, le score normalisé est 75.
# Si latent_score * scale_factor = -1, le score normalisé est 25.
# LATENT_SCORE_SCALE_FACTOR = 0.1 # Ajustez au besoin pour la sensibilité désirée - Supprimé, remplacé par RAW_POINT_SCALE_FACTOR
RAW_POINT_SCALE_FACTOR = 0.1 # Facteur pour moduler l'impact des points bruts via atan
DEFAULT_NORMALIZED_SCORE = 50.0 # Score neutre sur l'échelle 0-100 (pour TrustScore)
DEFAULT_NORMALIZED_STRENGTH_SCORE = 0.0 # Score de base pour StrengthScore (0-100)

# Les fonctions convert_latent_to_normalized_score, convert_normalized_to_latent_score,
# convert_latent_strength_to_normalized_score, convert_normalized_strength_to_latent_score
# ne sont plus nécessaires et seront supprimées.

import logging
from typing import Dict, Any, Optional, List, Tuple
from pyairtable import Table # Ajout de l'importation manquante
from datetime import datetime
import pytz # Pour la gestion des fuseaux horaires
import os
import json
import requests
import threading # Ajout de l'import pour le multithreading
from dotenv import load_dotenv

# Importer les helpers nécessaires depuis activity_helpers
from .activity_helpers import _escape_airtable_value, VENICE_TIMEZONE, LogColors, clean_thought_content
from .conversation_helper import DEFAULT_TIMEOUT_SECONDS # Ajout de l'importation
import time # Ajout de time pour les attentes
from datetime import date # Ajout pour json_datetime_serializer


log = logging.getLogger(__name__)

def json_datetime_serializer(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code, specifically for datetime."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    log.error(f"Type {type(obj)} not serializable with json_datetime_serializer. Value: {str(obj)[:100]}")
    # Il est préférable de lever une TypeError ici pour que l'appelant puisse la gérer,
    # plutôt que de retourner une chaîne qui pourrait masquer le problème.
    # Cependant, pour correspondre au comportement de `default=str`, on pourrait retourner `str(obj)`.
    # Pour l'instant, levons une exception pour être plus strict.
    raise TypeError(f"Type {type(obj)} not serializable")

def _make_kinos_request_with_retry(
    method: str,
    url: str,
    headers: Dict,
    json_payload: Optional[Dict] = None, # Seulement pour POST
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    kin_username_for_log: str = "UnknownKin", 
    action_description_for_log: str = "KinOS request"
) -> Optional[requests.Response]:
    """Effectue une requête HTTP vers KinOS avec tentatives multiples."""
    max_retries = 3
    initial_wait_time = 2  # secondes
    backoff_factor = 2

    for attempt in range(max_retries):
        try:
            log.info(f"{LogColors.INFO}Tentative {attempt + 1}/{max_retries} pour {action_description_for_log} par {kin_username_for_log} vers {url} (Méthode: {method.upper()}){LogColors.ENDC}")
            
            response: Optional[requests.Response] = None
            if method.upper() == "POST":
                response = requests.post(url, headers=headers, json=json_payload, timeout=timeout)
            elif method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            else:
                log.error(f"{LogColors.FAIL}Méthode non supportée {method} pour _make_kinos_request_with_retry.{LogColors.ENDC}")
                return None
            
            response.raise_for_status()  # Lève HTTPError pour les réponses 4xx/5xx
            return response # Succès

        except requests.exceptions.HTTPError as e_http:
            if response is not None and (response.status_code >= 500 or response.status_code == 429):
                log.warning(f"{LogColors.WARNING}Erreur HTTP KinOS ({action_description_for_log}) pour {kin_username_for_log} (Statut: {response.status_code}): {e_http}. Nouvelle tentative...{LogColors.ENDC}")
                if attempt < max_retries - 1:
                    wait_time = initial_wait_time * (backoff_factor ** attempt)
                    log.info(f"Attente de {wait_time} secondes avant la prochaine tentative...")
                    time.sleep(wait_time)
                    continue
                else:
                    log.error(f"{LogColors.FAIL}Nombre maximal de tentatives atteint pour l'API KinOS ({action_description_for_log}) pour {kin_username_for_log}. Dernière erreur: {e_http}{LogColors.ENDC}")
                    return None
            else: # Erreur HTTP non réessayable (ex: 400, 401, 403, 404)
                log.error(f"{LogColors.FAIL}Erreur HTTP KinOS non réessayable ({action_description_for_log}) pour {kin_username_for_log}: {e_http}{LogColors.ENDC}", exc_info=True)
                if response is not None:
                    log.error(f"Contenu de la réponse d'erreur KinOS: {response.text[:500]}")
                return None
        except requests.exceptions.RequestException as e_req: # Erreurs réseau, timeouts
            log.warning(f"{LogColors.WARNING}Erreur de requête API KinOS ({action_description_for_log}) pour {kin_username_for_log}: {e_req}. Nouvelle tentative...{LogColors.ENDC}")
            if attempt < max_retries - 1:
                wait_time = initial_wait_time * (backoff_factor ** attempt)
                log.info(f"Attente de {wait_time} secondes avant la prochaine tentative...")
                time.sleep(wait_time)
                continue
            else:
                log.error(f"{LogColors.FAIL}Nombre maximal de tentatives atteint pour l'API KinOS (erreur de requête) ({action_description_for_log}) pour {kin_username_for_log}. Dernière erreur: {e_req}{LogColors.ENDC}")
                return None
        # json.JSONDecodeError sera attrapé par l'appelant après avoir vérifié response.ok
        except Exception as e_gen:
            log.error(f"{LogColors.FAIL}Erreur inattendue dans _make_kinos_request_with_retry ({action_description_for_log}) pour {kin_username_for_log}: {e_gen}{LogColors.ENDC}", exc_info=True)
            return None 
    
    return None # Devrait être inaccessible si la boucle se termine, mais comme fallback

# Configuration pour les appels API KinOS et Next.js
load_dotenv() # S'assurer que .env est chargé pour KINOS_API_KEY et BASE_URL
KINOS_API_URL_BASE = "https://api.kinos-engine.ai/v2/blueprints/serenissima-ai/kins"
NEXT_JS_BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')

def apply_scaled_score_change(current_score: float, raw_delta: float, scale_factor: float = RAW_POINT_SCALE_FACTOR, min_score: float = 0.0, max_score: float = 100.0) -> float:
    """
    Applique un changement de points bruts à un score existant (0-100),
    en utilisant atan pour moduler l'impact de sorte que le score s'approche
    asymptotiquement des bornes min_score/max_score.
    """
    import math # S'assurer que math est importé

    if raw_delta == 0:
        return round(current_score, 2)

    if raw_delta > 0:
        room_to_grow = max_score - current_score
        if room_to_grow <= 1e-4: # Pratiquement à la limite max ou au-dessus
            return round(max(min(current_score, max_score), min_score), 2)
        
        # increment_factor est entre 0 et 1
        increment_factor = (math.atan(raw_delta * scale_factor) / (math.pi / 2))
        actual_increment = room_to_grow * increment_factor
        new_score = current_score + actual_increment
    else: # raw_delta < 0
        room_to_fall = current_score - min_score
        if room_to_fall <= 1e-4: # Pratiquement à la limite min ou en-dessous
            return round(max(min(current_score, max_score), min_score), 2)
            
        # decrement_factor est entre 0 et 1
        decrement_factor = (math.atan(abs(raw_delta) * scale_factor) / (math.pi / 2))
        actual_decrement = room_to_fall * decrement_factor
        new_score = current_score - actual_decrement
        
    return round(max(min_score, min(new_score, max_score)), 2)


# Suppression des anciennes fonctions de conversion (elles étaient ici)
# convert_latent_to_normalized_score
# convert_normalized_to_latent_score
# convert_latent_strength_to_normalized_score
# convert_normalized_strength_to_latent_score
# La nouvelle fonction apply_scaled_score_change est définie plus haut.

def update_trust_score_for_activity(
    tables: Dict[str, Any],
    citizen1_username: str,
    citizen2_username: str,
    trust_change_amount: float,
    activity_type_for_notes: str,
    success: bool,
    notes_detail: Optional[str] = None,
    activity_record_for_kinos: Optional[Dict[str, Any]] = None
) -> None:
    """
    Met à jour le TrustScore (stocké en BDD sur une échelle de 0 à 100) entre deux citoyens suite à une activité.
    L'ajout de points bruts est modulé pour un effet de rendement décroissant.
    Crée la relation si elle n'existe pas.
    Ajoute une note sur l'interaction.

    Args:
        tables: Dictionnaire des tables Airtable.
        citizen1_username: Username du premier citoyen.
        citizen2_username: Username du second citoyen.
        trust_change_amount: Montant à ajouter/soustraire au TrustScore.
        activity_type_for_notes: Type d'activité pour la note (ex: 'delivery', 'payment').
        success: Booléen indiquant si l'interaction est un succès.
        notes_detail: Détail optionnel à ajouter à la note.
    """
    if not citizen1_username or not citizen2_username or citizen1_username == citizen2_username:
        log.warning(f"{LogColors.WARNING}Tentative de mise à jour du TrustScore avec des usernames invalides ou identiques: {citizen1_username}, {citizen2_username}{LogColors.ENDC}")
        return

    # Assurer l'ordre alphabétique pour Citizen1 et Citizen2
    user1, user2 = sorted([citizen1_username, citizen2_username])

    log.info(f"{LogColors.OKBLUE}Mise à jour TrustScore entre {user1} et {user2} de {trust_change_amount:.2f} pour activité '{activity_type_for_notes}'.{LogColors.ENDC}")

    try:
        # Chercher une relation existante
        formula = f"AND({{Citizen1}}='{_escape_airtable_value(user1)}', {{Citizen2}}='{_escape_airtable_value(user2)}')"
        existing_relationships = tables['relationships'].all(formula=formula, max_records=1)

        interaction_note_key = f"activity_{activity_type_for_notes}_{'success' if success else 'failure'}"
        if notes_detail:
            interaction_note_key += f"_{notes_detail.replace(' ', '_').lower()}"

        if existing_relationships:
            relationship_record = existing_relationships[0]
            current_trust_score = float(relationship_record['fields'].get('TrustScore', DEFAULT_NORMALIZED_SCORE))
            
            # Appliquer le changement de points bruts au score actuel
            new_trust_score = apply_scaled_score_change(
                current_trust_score, 
                trust_change_amount, 
                RAW_POINT_SCALE_FACTOR, 
                min_score=0.0, 
                max_score=100.0
            )

            current_notes = relationship_record['fields'].get('Notes', "")
            # Ajout simple, le script quotidien de consolidation des relations pourra nettoyer/agréger
            new_notes_entry = interaction_note_key
            updated_notes = f"{current_notes}, {new_notes_entry}" if current_notes else new_notes_entry
            
            # Éviter les notes trop longues ou trop répétitives rapidement
            if len(updated_notes) > 1000: # Limite arbitraire
                notes_parts = updated_notes.split(',')
                if len(notes_parts) > 20: # Limite arbitraire du nombre de notes
                    updated_notes = ",".join(notes_parts[-20:]) # Garder les 20 dernières

            payload = {
                'TrustScore': new_trust_score,
                'LastInteraction': datetime.now(VENICE_TIMEZONE).isoformat(),
                'Notes': updated_notes,
                'Status': 'Active'  # Assurer que le statut est Actif lors de la mise à jour
            }
            tables['relationships'].update(relationship_record['id'], payload)
            log.info(f"{LogColors.OKGREEN}TrustScore (0-100) mis à jour pour {user1}-{user2}: {current_trust_score:.2f} -> {new_trust_score:.2f}. Statut défini sur 'Active'. Notes: {interaction_note_key}{LogColors.ENDC}")
        else:
            # Créer une nouvelle relation
            # Commencer avec le score neutre par défaut, puis appliquer le premier changement
            initial_trust_score_base = DEFAULT_NORMALIZED_SCORE
            final_initial_trust_score = apply_scaled_score_change(
                initial_trust_score_base,
                trust_change_amount,
                RAW_POINT_SCALE_FACTOR,
                min_score=0.0,
                max_score=100.0
            )
            
            initial_strength_score = DEFAULT_NORMALIZED_STRENGTH_SCORE # Commence à 0

            payload = {
                'Citizen1': user1,
                'Citizen2': user2,
                'TrustScore': final_initial_trust_score,
                'StrengthScore': initial_strength_score,
                'LastInteraction': datetime.now(VENICE_TIMEZONE).isoformat(),
                'Notes': interaction_note_key,
                'Status': 'Active' # Statut initial
            }
            tables['relationships'].create(payload)
            log.info(f"{LogColors.OKGREEN}Nouvelle relation créée pour {user1}-{user2}. TrustScore (0-100): {final_initial_trust_score:.2f}, StrengthScore (0-100): {initial_strength_score:.2f}. Notes: {interaction_note_key}{LogColors.ENDC}")

    except Exception as e:
        log.error(f"{LogColors.FAIL}Erreur lors de la mise à jour du TrustScore pour {user1}-{user2}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
    
    # The reaction dialogue functionality has been removed as it's now handled by the conversation system
    # Dialogues can be initiated even if both citizens are not AI

# --- Fonctions d'assistance pour l'interaction KinOS ---

# Helpers pour récupérer les données contextuelles pour KinOS via l'API Next.js
def _rh_get_notifications_data_api(username: str, limit: int = 5) -> List[Dict]:
    """RH: Fetches recent notifications for a citizen via the Next.js API."""
    try:
        url = f"{NEXT_JS_BASE_URL}/api/notifications"
        payload = {"citizen": username, "limit": limit}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "notifications" in data:
            return data["notifications"]
        log.warning(f"{LogColors.WARNING}RH: Failed to get notifications for {username} from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except Exception as e:
        log.error(f"{LogColors.FAIL}RH: API error fetching notifications for {username}: {e}{LogColors.ENDC}")
        return []

def _rh_get_relevancies_data_api(relevant_to_username: str, target_username: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """RH: Fetches recent relevancies for a citizen via the Next.js API."""
    try:
        params = {"relevantToCitizen": relevant_to_username, "limit": str(limit)}
        if target_username:
            params["targetCitizen"] = target_username
        
        url = f"{NEXT_JS_BASE_URL}/api/relevancies"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "relevancies" in data:
            return data["relevancies"]
        log.warning(f"{LogColors.WARNING}RH: Failed to get relevancies for {relevant_to_username} (target: {target_username}) from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except Exception as e:
        log.error(f"{LogColors.FAIL}RH: API error fetching relevancies for {relevant_to_username} (target: {target_username}): {e}{LogColors.ENDC}")
        return []

def _rh_get_problems_data_api(username: str, limit: int = 5) -> List[Dict]:
    """RH: Fetches active problems for a citizen via the Next.js API."""
    try:
        url = f"{NEXT_JS_BASE_URL}/api/problems?citizen={username}&status=active&limit={limit}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and "problems" in data:
            return data["problems"]
        log.warning(f"{LogColors.WARNING}RH: Failed to get problems for {username} from API: {data.get('error')}{LogColors.ENDC}")
        return []
    except Exception as e:
        log.error(f"{LogColors.FAIL}RH: API error fetching problems for {username}: {e}{LogColors.ENDC}")
        return []

def _rh_get_relationship_data(tables: Dict[str, Any], username1: str, username2: str) -> Optional[Dict[str, Any]]:
    """RH: Fetches relationship data between two citizens from Airtable."""
    try:
        user1, user2 = sorted([_escape_airtable_value(username1), _escape_airtable_value(username2)])
        formula = f"AND({{Citizen1}}='{user1}', {{Citizen2}}='{user2}')"
        records = tables["relationships"].all(formula=formula, max_records=1)
        if records:
            return records[0]['fields']
        return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}RH: Error fetching relationship between {username1} and {username2}: {e}{LogColors.ENDC}")
        return None

def _get_kinos_api_key() -> Optional[str]:
    """Récupère la clé API KinOS depuis les variables d'environnement."""
    api_key = os.getenv("KINOS_API_KEY")
    if not api_key:
        log.error(f"{LogColors.FAIL}Clé API KinOS (KINOS_API_KEY) non trouvée.{LogColors.ENDC}")
    return api_key

def _rh_get_kinos_model_for_citizen(social_class: Optional[str]) -> str:
    """RH: Determines the KinOS model based on social class."""
    if not social_class:
        return "local"
    
    s_class_lower = social_class.lower()
    if s_class_lower == "nobili":
        return "local"
    elif s_class_lower in ["cittadini", "forestieri"]:
        return "local"
    elif s_class_lower in ["popolani", "facchini"]:
        return "local"
    else:
        return "local"

def _get_citizen_details(tables: Dict[str, Any], username: str) -> Optional[Dict[str, Any]]:
    """Récupère les détails d'un citoyen, notamment IsAI et FirstName."""
    try:
        safe_username = _escape_airtable_value(username)
        # Assurez-vous que les champs IsAI et FirstName sont demandés si ce n'est pas déjà le cas par défaut
        records = tables["citizens"].all(formula=f"{{Username}} = '{safe_username}'", fields=["Username", "IsAI", "FirstName"], max_records=1)
        if records:
            return records[0]['fields']
        log.warning(f"{LogColors.WARNING}Citoyen {username} non trouvé pour les détails.{LogColors.ENDC}")
        return None
    except Exception as e:
        log.error(f"{LogColors.FAIL}Erreur lors de la récupération des détails du citoyen {username}: {e}{LogColors.ENDC}")
        return None

def _store_message_via_api(
    tables: Dict[str, Table], 
    sender_username: str, 
    receiver_username: str, 
    content: str,
    channel_name: str, 
    message_type: str = "message"  # Ajout de message_type avec une valeur par défaut
) -> bool:
    """Stocke un message en utilisant l'API Next.js /api/messages/send."""
    try:
        api_url = f"{NEXT_JS_BASE_URL}/api/messages/send"
        
        # Le nettoyage du contenu est supposé être fait par l'appelant si nécessaire.
        # Cette fonction se concentre sur la persistance.
        
        payload = {
            "sender": sender_username,
            "receiver": receiver_username,
            "content": content, 
            "type": message_type, # Utiliser le paramètre message_type
            "channel": channel_name
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        response_data = response.json()
        if response_data.get("success"):
            log.info(f"{LogColors.OKGREEN}Message de {sender_username} à {receiver_username} stocké via API.{LogColors.ENDC}")
            return True
        else:
            log.error(f"{LogColors.FAIL}L'API a échoué à stocker le message de {sender_username} à {receiver_username}: {response_data.get('error')}{LogColors.ENDC}")
            return False
    except requests.exceptions.RequestException as e:
        log.error(f"{LogColors.FAIL}Échec de la requête API lors du stockage du message de {sender_username} à {receiver_username}: {e}{LogColors.ENDC}")
        return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}Erreur lors du stockage du message via API de {sender_username} à {receiver_username}: {e}{LogColors.ENDC}")
        return False

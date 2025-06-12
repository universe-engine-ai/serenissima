import os
import sys
import json
import random
import time
import argparse # Ajout de argparse
import math # Ajout de math
import re # Ajout de re pour les expressions régulières
import logging # Ajout de l'importation de logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple # Ajout de Tuple

import requests
from dotenv import load_dotenv
from pyairtable import Api, Base, Table # Import Base

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configuration pour les appels API
BASE_URL = os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:3000')

from backend.engine.utils.activity_helpers import LogColors, log_header, clean_thought_content # Ajout de l'importation
from backend.engine.utils.conversation_helper import (
    get_citizen_data_package, 
    make_kinos_channel_call, 
    get_kinos_model_for_social_class, 
    DEFAULT_TIMEOUT_SECONDS,
    persist_message # Ajout de l'importation de persist_message
)

# Initialize logger for this module
log = logging.getLogger(__name__)

# KinOS Configuration (mirrors conversation_helper.py and autonomouslyRun.py)
KINOS_API_CHANNEL_BASE_URL = 'https://api.kinos-engine.ai/v2'
KINOS_BLUEPRINT_ID = 'serenissima-ai'

# --- Fonctions d'initialisation et utilitaires Airtable/API ---

def initialize_airtable() -> Optional[Dict[str, Table]]:
    """Initialise la connexion à Airtable."""
    load_dotenv()
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")

    if not airtable_api_key or not airtable_base_id:
        print("Erreur : Identifiants Airtable non trouvés dans les variables d'environnement.")
        sys.exit(1)

    try:
        api = Api(airtable_api_key)
        base = Base(api, airtable_base_id) # Create a Base object
        
        tables = {
            "citizens": base.table("CITIZENS"), # Corrected usage
            "messages": base.table("MESSAGES"), # Corrected usage
            "notifications": base.table("NOTIFICATIONS"), # Corrected usage
            "relationships": base.table("RELATIONSHIPS"), # Corrected usage
            "relevancies": base.table("RELEVANCIES"), # Corrected usage
            "problems": base.table("PROBLEMS") # Corrected usage
        }
        print("Connexion à Airtable initialisée avec des objets Base et Table explicites.")
        return tables
    except Exception as e:
        print(f"Erreur lors de l'initialisation d'Airtable : {e}")
        return None

def get_kinos_api_key() -> str:
    """Récupère la clé API KinOS depuis les variables d'environnement."""
    load_dotenv() # S'assurer que .env est chargé
    api_key = os.getenv("KINOS_API_KEY")
    if not api_key:
        print("Erreur : Clé API KinOS non trouvée dans les variables d'environnement (KINOS_API_KEY).")
        sys.exit(1)
    return api_key

def get_ai_citizens(tables: Dict[str, Table]) -> List[Dict]:
    """Récupère tous les citoyens marqués comme IA et présents à Venise."""
    try:
        formula = "AND({IsAI}=1, {InVenice}=1)"
        ai_citizens = tables["citizens"].all(formula=formula, fields=["Username", "FirstName"])
        print(f"Trouvé {len(ai_citizens)} citoyens IA à Venise.")
        return ai_citizens
    except Exception as e:
        print(f"Erreur lors de la récupération des citoyens IA : {e}")
        return []

# --- Fonctions d'assistance pour récupérer les données contextuelles (copiées/adaptées de answertomessages.py) ---
# get_top_relationships_for_ai a été supprimé car la décision de l'interlocuteur est maintenant gérée par KinOS.

def _escape_airtable_value(value: Any) -> str:
    """Échappe les apostrophes et les guillemets pour les formules Airtable et s'assure que la valeur est une chaîne."""
    if not isinstance(value, str):
        value = str(value)  # Convertit en chaîne d'abord
    value = value.replace("'", "\\'") # Échappe les apostrophes
    value = value.replace('"', '\\"') # Échappe les guillemets doubles
    return value

def _get_citizen_data(tables: Dict[str, Table], username: str) -> Optional[Dict]:
    try:
        safe_username = _escape_airtable_value(username)
        records = tables["citizens"].all(formula=f"{{Username}} = '{safe_username}'", max_records=1)
        if records:
            return {'id': records[0]['id'], 'fields': records[0]['fields']}
        return None
    except Exception as e:
        print(f"Erreur lors de la récupération des données du citoyen {username}: {e}")
        return None

def _get_relationship_data(tables: Dict[str, Table], username1: str, username2: str) -> Optional[Dict]:
    try:
        safe_username1 = _escape_airtable_value(username1)
        safe_username2 = _escape_airtable_value(username2)
        c1, c2 = sorted((safe_username1, safe_username2))
        formula = f"AND({{Citizen1}} = '{c1}', {{Citizen2}} = '{c2}')"
        records = tables["relationships"].all(formula=formula, max_records=1)
        if records:
            return {'id': records[0]['id'], 'fields': records[0]['fields']}
        return None
    except Exception as e:
        print(f"Erreur lors de la récupération de la relation entre {username1} et {username2}: {e}")
        return None

def _get_notifications_data(tables: Dict[str, Table], username: str, limit: int = 50) -> List[Dict]:
    """Récupère les notifications pour un citoyen via l'API."""
    try:
        # L'API /api/notifications attend un POST avec 'citizen' dans le corps JSON
        api_url = f"{BASE_URL}/api/notifications"
        payload = {"citizen": username} # 'since' est optionnel et a une valeur par défaut dans l'API
        headers = {"Content-Type": "application/json"}
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        if data.get("success") and "notifications" in data:
            # L'API retourne déjà les champs nécessaires, pas besoin de 'fields' imbriqué
            # Ajuster si le format de l'API est différent (par exemple, si elle retourne des enregistrements Airtable bruts)
            print(f"Récupéré {len(data['notifications'])} notifications pour {username} via API.")
            return data["notifications"]
        else:
            print(f"L'API a échoué à récupérer les notifications pour {username}: {data.get('error', 'Erreur inconnue')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Erreur de requête API lors de la récupération des notifications pour {username}: {e}")
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des notifications pour {username} via API: {e}")
        return []

def _get_relevancies_data(tables: Dict[str, Table], relevant_to_username: str, target_username: str, limit: int = 50) -> List[Dict]:
    """Récupère les pertinences via l'API."""
    try:
        params = {
            "relevantToCitizen": relevant_to_username,
            "targetCitizen": target_username,
            "limit": str(limit) # L'API attend des chaînes pour les paramètres numériques
        }
        api_url = f"{BASE_URL}/api/relevancies"
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        if data.get("success") and "relevancies" in data:
             # L'API retourne déjà les champs nécessaires, pas besoin de 'fields' imbriqué
            print(f"Récupéré {len(data['relevancies'])} pertinences pour {relevant_to_username} -> {target_username} via API.")
            return data["relevancies"]
        else:
            print(f"L'API a échoué à récupérer les pertinences pour {relevant_to_username} -> {target_username}: {data.get('error', 'Erreur inconnue')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Erreur de requête API lors de la récupération des pertinences pour {relevant_to_username} -> {target_username}: {e}")
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des pertinences pour {relevant_to_username} -> {target_username} via API: {e}")
        return []

def _get_problems_data(tables: Dict[str, Table], username1: str, username2: str, limit: int = 50) -> List[Dict]:
    """Récupère les problèmes pour un ou deux citoyens via l'API."""
    problems_list = []
    try:
        # Récupérer les problèmes pour username1
        params1 = {"citizen": username1, "status": "active", "limit": str(limit)}
        api_url = f"{BASE_URL}/api/problems"
        response1 = requests.get(api_url, params=params1, timeout=15)
        response1.raise_for_status()
        data1 = response1.json()
        if data1.get("success") and "problems" in data1:
            problems_list.extend(data1["problems"])
        else:
            print(f"L'API a échoué à récupérer les problèmes pour {username1}: {data1.get('error', 'Erreur inconnue')}")

        # Récupérer les problèmes pour username2, en évitant les doublons si username1 == username2
        if username1 != username2:
            params2 = {"citizen": username2, "status": "active", "limit": str(limit)}
            response2 = requests.get(api_url, params=params2, timeout=15)
            response2.raise_for_status()
            data2 = response2.json()
            if data2.get("success") and "problems" in data2:
                # Éviter d'ajouter des problèmes en double si un problème concerne les deux
                existing_problem_ids = {p.get('problemId') or p.get('id') for p in problems_list}
                for problem in data2["problems"]:
                    problem_id = problem.get('problemId') or problem.get('id')
                    if problem_id not in existing_problem_ids:
                        problems_list.append(problem)
            else:
                print(f"L'API a échoué à récupérer les problèmes pour {username2}: {data2.get('error', 'Erreur inconnue')}")
        
        # L'API /api/problems ne trie pas par CreatedAt par défaut, mais on peut le demander.
        # Ici, nous allons trier en Python pour correspondre au comportement précédent.
        problems_list.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        print(f"Récupéré {len(problems_list)} problèmes pour {username1} ou {username2} via API.")
        return problems_list[:limit]

    except requests.exceptions.RequestException as e:
        print(f"Erreur de requête API lors de la récupération des problèmes pour {username1} ou {username2}: {e}")
        return problems_list # Retourner ce qui a été collecté jusqu'à présent
    except Exception as e:
        print(f"Erreur lors de la récupération des problèmes pour {username1} ou {username2} via API: {e}")
        return []

# _check_existing_messages a été supprimé. Cette information sera incluse dans le data_package pour KinOS.

# --- Fonctions KinOS et création de message ---

def _summarize_add_system_for_local_model(
    kinos_api_key: str,
    ai_username: str, 
    purpose_of_call: str, 
    full_add_system_data: Dict[str, Any],
    tables_for_cleaning: Optional[Dict[str, Table]] = None
) -> Dict[str, Any]:
    """
    If the model is local, calls KinOS to summarize the full_add_system_data.
    Returns the summarized data or the original data if summarization fails.
    """
    log.info(f"{LogColors.OKBLUE}Local model detected for {ai_username} for purpose: '{purpose_of_call}'. Performing attention pre-prompt step to summarize context.{LogColors.ENDC}")
    
    attention_channel_name = "attention_summarizer" 
    
    attention_prompt = (
        f"You are an AI assistant helping {ai_username} prepare for a strategic decision: '{purpose_of_call}'. "
        f"Based on the extensive context provided in `addSystem` (which includes {ai_username}'s profile, relationships, problems, opportunities, etc.), "
        f"please perform the following two steps:\n\n"
        f"Step 1: Build a clear picture of {ai_username}'s current situation relevant to '{purpose_of_call}'. "
        f"Describe key relationships, recent events, ongoing issues, and goals that should inform this decision.\n\n"
        f"Step 2: Using the situation picture from Step 1 and your understanding of {ai_username}'s personality and objectives, "
        f"summarize the information and extract the most relevant specific pieces of context. "
        f"Focus on what is most important for {ai_username} to remember or act upon for '{purpose_of_call}'. "
        "Your final output should be this concise summary in English, suitable for guiding the main decision-making prompt."
    )

    # make_kinos_channel_call is defined in this file
    summarized_context_content = make_kinos_channel_call(
        kinos_api_key=kinos_api_key,
        speaker_username=ai_username,
        channel_name=attention_channel_name,
        prompt=attention_prompt,
        add_system_data=full_add_system_data,
        kinos_model_override='local' 
    )

    if summarized_context_content:
        # clean_thought_content is imported from activity_helpers
        cleaned_summarized_context = clean_thought_content(tables_for_cleaning, summarized_context_content)
        
        log.info(f"{LogColors.OKGREEN}Successfully generated summarized context for {ai_username} (purpose: {purpose_of_call}). Original length: {len(summarized_context_content)}, Cleaned length: {len(cleaned_summarized_context)}{LogColors.ENDC}")
        log.debug(f"Original summarized context for {purpose_of_call} for {ai_username}: {summarized_context_content}")
        log.debug(f"Cleaned summarized context for {purpose_of_call} for {ai_username}: {cleaned_summarized_context}")
        
        return {
            "summary_of_relevant_context": cleaned_summarized_context,
            "original_context_available_on_request": f"The full data package was summarized for the purpose of '{purpose_of_call}'. You are now acting as the character based on this summary."
        }
    else:
        log.warning(f"{LogColors.WARNING}Failed to generate summarized context for {ai_username} (purpose: {purpose_of_call}). Using full context for the main call.{LogColors.ENDC}")
        return full_add_system_data

def choose_interlocutor_via_kinos(
    ai_username: str,
    kinos_api_key: str,
    ai_data_package: Dict[str, Any],
    kinos_model_override: Optional[str] = None
) -> Optional[Tuple[str, str]]:
    """
    Appelle KinOS pour choisir un interlocuteur et la raison de l'interaction.
    Retourne (target_username, reason) ou (None, None).
    """
    ai_profile = ai_data_package.get("profile", {})
    ai_display_name = ai_profile.get("firstName", ai_username)
    ai_social_class = ai_profile.get("socialClass")

    # Le canal "strategist" est un canal conceptuel pour ce type de décision.
    # L'ID du kin est l'IA elle-même.
    kinos_channel_for_decision = "strategist" 

    prompt = (
        f"You are {ai_display_name}, an AI citizen of Venice. Your full data package (profile, relationships, problems, opportunities, recent activities, etc.) "
        f"is provided in `addSystem`.\n\n"
        f"Based on all this information, analyze your current situation and identify another citizen with whom initiating a conversation would be most beneficial or strategically relevant for you right now. "
        f"Consider your goals, active problems, opportunities, and the nature of your relationships. Could initiating or discussing a **Stratagem** be a reason for contact? Information on available stratagems is in `addSystem.availableStratagems` and your active ones are in `addSystem.stratagemsExecutedByCitizen` or `addSystem.stratagemsTargetingCitizen`.\n\n"
        f"Your response MUST be a JSON object with two keys: 'target_username' (the Username of the citizen you choose) and 'reason' (a specific compelling reason for contacting them, focusing on gameplay or possibly narrative progression, potentially related to a stratagem).\n"
        f"If no compelling interaction is identified, respond with: {{\"target_username\": null, \"reason\": \"No compelling interaction identified at this time.\"}}\n\n"
        f"Chosen interaction (JSON):"
    )

    # Utiliser le modèle par défaut basé sur la classe sociale ou l'override
    effective_model = kinos_model_override or get_kinos_model_for_social_class(ai_username, ai_social_class)
    if not kinos_model_override: # Si aucun override n'est fourni, s'assurer que 'local' est utilisé par défaut pour cette décision.
        effective_model = "local"
        # Le log sur le modèle utilisé sera fait plus bas, après la summarization si elle a lieu.

    final_add_system_for_kinos = ai_data_package
    if effective_model == 'local':
        # La fonction _summarize_add_system_for_local_model contient déjà des logs sur son exécution.
        final_add_system_for_kinos = _summarize_add_system_for_local_model(
            kinos_api_key=kinos_api_key,
            ai_username=ai_username,
            purpose_of_call="choosing an interlocutor",
            full_add_system_data=ai_data_package,
            tables_for_cleaning=None # 'tables' n'est pas disponible dans ce scope direct
        )
    
    print(f"Appel à KinOS pour choisir un interlocuteur pour {ai_username} (Modèle effectif: {effective_model})...")
    
    # make_kinos_channel_call est importé de conversation_helper
    raw_response_content = make_kinos_channel_call(
        kinos_api_key=kinos_api_key,
        speaker_username=ai_username, # L'IA elle-même est le "speaker" pour cette décision
        channel_name=kinos_channel_for_decision,
        prompt=prompt,
        add_system_data=final_add_system_for_kinos, 
        kinos_model_override=effective_model
    )

    if not raw_response_content:
        print(f"KinOS n'a pas retourné de réponse pour la décision de l'interlocuteur pour {ai_username}.")
        return None, None

    try:
        # Nettoyer le contenu avant de parser le JSON (KinOS peut ajouter des <think> tags)
        # clean_thought_content est importé de activity_helpers
        cleaned_response = clean_thought_content(None, raw_response_content) # tables=None car pas de remplacement d'ID ici
        
        # Extraire le JSON de la réponse nettoyée
        # Le prompt demande un JSON, mais KinOS peut l'envelopper dans du texte.
        json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
        if not json_match:
            print(f"Réponse KinOS pour la décision de l'interlocuteur (après nettoyage) ne contient pas de JSON valide pour {ai_username}: {cleaned_response}")
            return None, None
            
        decision_data = json.loads(json_match.group(0))
        target_username = decision_data.get("target_username")
        reason = decision_data.get("reason")

        if target_username and reason:
            print(f"KinOS a choisi {target_username} pour {ai_username}. Raison: {reason}")
            return target_username, reason
        else:
            print(f"KinOS n'a pas identifié d'interlocuteur pour {ai_username}. Raison: {reason}")
            return None, None
    except json.JSONDecodeError:
        print(f"Erreur de décodage JSON de la réponse KinOS pour la décision de l'interlocuteur pour {ai_username}. Réponse brute: '{raw_response_content}', Nettoyée: '{cleaned_response}'")
        return None, None
    except Exception as e:
        print(f"Erreur lors du traitement de la réponse KinOS pour la décision de l'interlocuteur pour {ai_username}: {e}")
        return None, None

def generate_ai_initiative_message(
    tables: Dict[str, Table], 
    ai_username: str, 
    target_username: str, 
    kinos_api_key: str, # Renommé depuis kinos_api_key pour éviter conflit avec variable globale
    reason_for_contact: str,
    kinos_model_override: Optional[str] = None
) -> Optional[str]:
    """Génère le contenu d'un message d'initiative IA à un `target_username` spécifique, basé sur `reason_for_contact`."""
    try:
        # kinos_api_key est maintenant un argument de la fonction
        ai_citizen_profile_data = _get_citizen_data(tables, ai_username)
        target_citizen_profile_data = _get_citizen_data(tables, target_username)
        
        if not ai_citizen_profile_data or not target_citizen_profile_data:
            print(f"Impossible de récupérer les profils pour {ai_username} ou {target_username}.")
            return None

        relationship_data = _get_relationship_data(tables, ai_username, target_username)
        # Pour le contexte du message, nous pourrions vouloir des notifications/problèmes/pertinences plus ciblés.
        # Par exemple, uniquement ceux impliquant les deux citoyens ou pertinents pour la raison.
        # Pour l'instant, gardons une approche similaire à l'originale mais avec la raison en plus.
        notifications_for_ai = _get_notifications_data(tables, ai_username, limit=5) # Limité pour la concision
        relevancies_ai_to_target = _get_relevancies_data(tables, ai_username, target_username, limit=5)
        problems_involving_pair = _get_problems_data(tables, ai_username, target_username, limit=5)

        # Construire le addSystem pour la génération de contenu de message
        focused_system_context = {
            "ai_citizen_profile": ai_citizen_profile_data.get("fields", {}),
            "target_citizen_profile": target_citizen_profile_data.get("fields", {}),
            "relationship_with_target": relationship_data.get("fields", {}) if relationship_data else {},
            "reason_for_this_contact": reason_for_contact,
            "recent_notifications_for_ai": notifications_for_ai,
            "recent_relevancies_ai_to_target": relevancies_ai_to_target,
            "recent_problems_involving_us": problems_involving_pair
            # On pourrait aussi ajouter un bref historique de conversation avec CET interlocuteur si disponible.
        }
        
        ai_display_name = ai_citizen_profile_data.get('fields', {}).get('FirstName', ai_username)
        target_display_name = target_citizen_profile_data.get('fields', {}).get('FirstName', target_username)
        ai_social_class = ai_citizen_profile_data.get('fields', {}).get('SocialClass')

        prompt_for_message_content = (
            f"You are {ai_display_name}, an AI citizen of Venice. You are having a conversation with {target_display_name}.\n"
            f"The primary reason for this contact is: \"{reason_for_contact}\".\n"
            f"IMPORTANT: Your message must be short, human-like, and specific. It should be a natural conversation message related to the reason and context. "
            f"DO NOT use formal language. Be direct and concise.\n\n"
            f"Use the structured context in `addSystem` to make your message RELEVANT and FOCUSED ON GAMEPLAY or narrative progression with {target_display_name}. "
            f"If your reason for contact involves a **Stratagem**, subtly weave that into your opening. You can find stratagem details in your broader knowledge (e.g., from your full data package if previously accessed).\n"
            f"Your message to {target_display_name}:"
        )
        
        # Utiliser le modèle basé sur la classe sociale de l'IA ou l'override
        effective_model = kinos_model_override or get_kinos_model_for_social_class(ai_username, ai_social_class)

        final_add_system_for_kinos = focused_system_context
        if effective_model == 'local':
            final_add_system_for_kinos = _summarize_add_system_for_local_model(
                kinos_api_key=kinos_api_key,
                ai_username=ai_username,
                purpose_of_call=f"crafting an initiative message to {target_username}",
                full_add_system_data=focused_system_context,
                tables_for_cleaning=tables # 'tables' est disponible ici
            )

        # make_kinos_channel_call est importé de conversation_helper
        raw_message_content = make_kinos_channel_call(
            kinos_api_key=kinos_api_key,
            speaker_username=ai_username,
            channel_name=target_username, # Le canal est avec le target_username
            prompt=prompt_for_message_content,
            add_system_data=final_add_system_for_kinos,
            kinos_model_override=effective_model
        )

        if raw_message_content:
            # clean_thought_content est importé de activity_helpers
            cleaned_content = clean_thought_content(tables, raw_message_content)
            print(f"Contenu du message généré pour {ai_username} à {target_username}: {cleaned_content[:100]}...")
            return cleaned_content
        else:
            print(f"KinOS n'a pas retourné de contenu de message pour {ai_username} à {target_username}.")
            return None

    except Exception as e:
        print(f"Erreur dans generate_ai_initiative_message pour {ai_username} à {target_username}: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def create_admin_notification(tables: Dict[str, Table], initiatives_summary: Dict[str, Any]) -> None:
    """Crée une notification pour les administrateurs avec le résumé des initiatives."""
    try:
        now = datetime.now().isoformat()
        content = f"💬 **Résumé des Initiatives de Messages IA** ({now}):\n"
        content += f"👤 Citoyens IA traités: **{initiatives_summary['processed_ai_count']}**\n"
        content += f"✉️ Messages initiés au total: **{initiatives_summary['total_messages_sent']}**\n\n"
        
        for ai_user, data in initiatives_summary.get("details", {}).items():
            if data['messages_sent_count'] > 0:
                content += f"- **{ai_user}** a initié {data['messages_sent_count']} message(s) à : **{', '.join(data['targets'])}**\n"
        
        if initiatives_summary['total_messages_sent'] == 0:
            content += "Aucun message n'a été initié lors de cette exécution."

        notification_payload = {
            "Citizen": "ConsiglioDeiDieci", # Ou un utilisateur système dédié
            "Type": "ai_message_initiative",
            "Content": content,
            "CreatedAt": now,
            "Details": json.dumps(initiatives_summary)
        }
        tables["notifications"].create(notification_payload)
        print("📬 Notification d'administration pour les initiatives de messages créée.")
    except Exception as e:
        print(f"Erreur lors de la création de la notification d'administration : {e}")

# --- API Call Helper ---
# Note: This script uses print for logging.
def call_try_create_activity_api(
    citizen_username: str,
    activity_type: str,
    activity_parameters: Dict[str, Any],
    dry_run: bool
) -> bool:
    """Calls the /api/activities/try-create endpoint."""
    if dry_run:
        print(f"[DRY RUN] Would call /api/activities/try-create for {citizen_username} with type '{activity_type}' and params: {json.dumps(activity_parameters)}")
        return True

    api_url = f"{BASE_URL}/api/activities/try-create" # BASE_URL is defined at the top
    payload = {
        "citizenUsername": citizen_username,
        "activityType": activity_type,
        "activityParameters": activity_parameters
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("success"):
            print(f"Successfully initiated activity '{activity_type}' for {citizen_username} via API. Response: {response_data.get('message', 'OK')}")
            activity_info = response_data.get("activity") or (response_data.get("activities")[0] if isinstance(response_data.get("activities"), list) and response_data.get("activities") else None)
            if activity_info and activity_info.get("id"):
                 print(f"  Activity ID: {activity_info['id']}")
            return True
        else:
            print(f"API call to initiate activity '{activity_type}' for {citizen_username} failed: {response_data.get('error', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"API request failed for activity '{activity_type}' for {citizen_username}: {e}")
        return False
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response for activity '{activity_type}' for {citizen_username}. Response: {response.text[:200]}")
        return False

# Update process_ai_message_initiatives definition
def process_ai_message_initiatives(dry_run: bool = False, citizen1_arg: Optional[str] = None, citizen2_arg: Optional[str] = None, kinos_model_override_arg: Optional[str] = None, citizen_arg: Optional[str] = None): # Added citizen_arg
    """Fonction principale pour traiter les initiatives de messages IA."""
    model_status = f"override: {kinos_model_override_arg}" if kinos_model_override_arg else "default"
    header_msg = "Processus d'Initiatives de Messages IA"
    if citizen1_arg and citizen2_arg:
        header_msg = f"Initiative de Message IA CIBLÉ de {citizen1_arg} à {citizen2_arg}"
    elif citizen_arg:
        header_msg = f"Initiatives de Messages IA pour le citoyen SPÉCIFIQUE : {citizen_arg}"
    log_header(f"{header_msg} (dry_run={dry_run}, kinos_model={model_status})", LogColors.HEADER)
    
    tables = initialize_airtable()
    if not tables:
        return

    initiatives_summary = {
        "processed_ai_count": 0,
        "total_messages_sent": 0,
        "details": {} 
    }

    if citizen1_arg and citizen2_arg:
        # Mode ciblé
        ai_username = citizen1_arg
        target_username = citizen2_arg
        print(f"Mode ciblé : {ai_username} va tenter d'envoyer un message à {target_username}.")

        # Vérifier si citizen1 est une IA (optionnel, mais bon à savoir)
        # citizen1_data = _get_citizen_data(tables, ai_username)
        # if not (citizen1_data and citizen1_data.get('fields', {}).get('IsAI')):
        #     print(f"Attention : {ai_username} n'est pas marqué comme IA, mais on continue quand même.")

        initiatives_summary["processed_ai_count"] = 1
        initiatives_summary["details"][ai_username] = {"messages_sent_count": 0, "targets": []}
        
        kinos_api_key_local = get_kinos_api_key() # Récupérer la clé API une fois

        if not dry_run:
            # Pour le mode ciblé, la raison est implicite ("commande directe")
            # ou pourrait être passée via un autre argument si nécessaire.
            # Ici, nous allons générer directement le contenu du message.
            reason_for_targeted_contact = f"Instruction directe de contacter {target_username}"
            message_content = generate_ai_initiative_message(
                tables, ai_username, target_username, kinos_api_key_local, 
                reason_for_targeted_contact, kinos_model_override_arg
            )
            if message_content:
                sorted_usernames_for_channel_targeted = sorted([ai_username, target_username])
                channel_name_targeted = f"{sorted_usernames_for_channel_targeted[0]}_{sorted_usernames_for_channel_targeted[1]}"
                activity_params = {
                    "receiverUsername": target_username,
                    "content": message_content,
                    "messageType": "message",
                    "channel": channel_name_targeted
                }
                print(f"    Tentative d'envoi de message ciblé via activité 'send_message' avec canal: {channel_name_targeted}")
                if call_try_create_activity_api(ai_username, "send_message", activity_params, dry_run):
                    initiatives_summary["total_messages_sent"] += 1
                    initiatives_summary["details"][ai_username]["messages_sent_count"] += 1
                    initiatives_summary["details"][ai_username]["targets"].append(target_username)
            else:
                print(f"    Échec de la génération du contenu du message de {ai_username} à {target_username}.")
        else:
            print(f"    [DRY RUN] {ai_username} aurait initié un message à {target_username}.")
            # Simuler le succès pour le résumé en dry run
            initiatives_summary["total_messages_sent"] += 1
            initiatives_summary["details"][ai_username]["messages_sent_count"] += 1
            initiatives_summary["details"][ai_username]["targets"].append(target_username)

    elif citizen_arg:
        # Mode pour un citoyen spécifique
        ai_citizen_record_fields = _get_citizen_data(tables, citizen_arg) # Ceci retourne {'id': ..., 'fields': ...}
        if not ai_citizen_record_fields or not ai_citizen_record_fields.get('fields'):
            print(f"Citoyen IA '{citizen_arg}' non trouvé ou données de champs manquantes. Fin du processus.")
            return
        
        # Construire un enregistrement similaire à ce que get_ai_citizens retournerait pour la boucle
        ai_citizens_to_process = [{'id': ai_citizen_record_fields['id'], 'fields': ai_citizen_record_fields['fields']}]
        initiatives_summary["processed_ai_count"] = 1
    else:
        # Mode normal (pour tous les IA)
        ai_citizens_to_process = get_ai_citizens(tables)
        if not ai_citizens_to_process:
            print("Aucun citoyen IA trouvé, fin du processus.")
            return
        random.shuffle(ai_citizens_to_process)

    # Boucle principale pour le mode normal ou le mode citoyen spécifique
    if not (citizen1_arg and citizen2_arg): # Ne pas exécuter cette boucle si en mode ciblé --citizen1/--citizen2
        kinos_api_key_local = get_kinos_api_key() # Récupérer la clé API une fois pour la boucle

        for ai_citizen_record_loop in ai_citizens_to_process:
            ai_username = ai_citizen_record_loop.get("fields", {}).get("Username")
            if not ai_username:
                print(f"Ignorer l'enregistrement citoyen IA {ai_citizen_record_loop.get('id')} car Username est manquant.")
                continue

            if not citizen_arg: # Seulement incrémenter si on traite tous les IA
                initiatives_summary["processed_ai_count"] += 1
            
            initiatives_summary["details"][ai_username] = {"messages_sent_count": 0, "targets": []}
            
            print(f"\nTraitement des initiatives pour l'IA : {ai_username}")

            # 1. Récupérer le data package complet pour l'IA (en format JSON)
            log.info(f"Récupération du data package JSON pour {ai_username}...")
            data_package_url = f"{BASE_URL}/api/get-data-package?citizenUsername={ai_username}&format=json"
            ai_data_package = None # Initialiser au cas où l'appel échoue
            try:
                response = requests.get(data_package_url, timeout=20)
                response.raise_for_status() # Lèvera une exception pour les codes d'erreur HTTP
                json_response = response.json()
                if json_response.get("success"):
                    ai_data_package = json_response.get("data") # Ceci est le dictionnaire attendu
                    if not isinstance(ai_data_package, dict):
                        log.error(f"Le data package JSON pour {ai_username} n'est pas un dictionnaire. Reçu : {type(ai_data_package)}")
                        ai_data_package = None 
                else:
                    log.error(f"L'appel API pour le data package JSON de {ai_username} n'a pas réussi : {json_response.get('error')}")
            except requests.exceptions.RequestException as e:
                log.error(f"Erreur lors de la récupération du data package JSON pour {ai_username} : {e}")
            except json.JSONDecodeError as e:
                log.error(f"Erreur de décodage JSON pour le data package de {ai_username} : {e}. Texte de la réponse : {response.text[:200] if 'response' in locals() else 'N/A'}")
            
            if not ai_data_package:
                print(f"Impossible de récupérer le data package JSON pour {ai_username}. Passage au suivant.")
                log.warning(f"Impossible de récupérer le data package JSON pour {ai_username}. Passage au suivant.")
                continue
            log.info(f"Data package JSON récupéré avec succès pour {ai_username}.")

            # 2. Appeler KinOS pour choisir un interlocuteur et une raison
            target_username, reason_for_contact = choose_interlocutor_via_kinos(
                ai_username, 
                kinos_api_key_local, 
                ai_data_package, 
                kinos_model_override_arg # Peut être None, auquel cas choose_interlocutor_via_kinos utilisera 'local'
            )

            if target_username and reason_for_contact:
                print(f"    -> {ai_username} va tenter d'initier un message à {target_username}. Raison: {reason_for_contact}")

                # Persist the reason as an internal thought/message to self
                if not dry_run:
                    thought_content = f"My reasoning for contacting {target_username}: {reason_for_contact}"
                    # persist_message est maintenant importé et disponible
                    persist_message(
                        tables=tables, # Passer l'objet tables correctement
                        sender_username=ai_username,
                        receiver_username=ai_username, # Message à soi-même
                        content=thought_content,
                        message_type="ai_initiative_reasoning", # Nouveau type de message pour ce contexte
                        channel_name=f"{ai_username}_thoughts" # Canal spécial pour les pensées/raisons
                    )
                
                if not dry_run:
                    message_content = generate_ai_initiative_message(
                        tables, 
                        ai_username, 
                        target_username, 
                        kinos_api_key_local, 
                        reason_for_contact, 
                        kinos_model_override_arg # Peut être None, generate_ai_initiative_message choisira en fonction de la classe sociale
                    )
                    if message_content:
                        sorted_usernames_for_channel_initiative = sorted([ai_username, target_username])
                        channel_name_initiative = f"{sorted_usernames_for_channel_initiative[0]}_{sorted_usernames_for_channel_initiative[1]}"
                        
                        activity_params = {
                            "receiverUsername": target_username,
                            "content": message_content,
                            "messageType": "message", # Ou un type plus spécifique comme "ai_initiative"
                            "channel": channel_name_initiative
                        }
                        print(f"    Tentative d'envoi de message via activité 'send_message' avec canal: {channel_name_initiative}")
                        if call_try_create_activity_api(ai_username, "send_message", activity_params, dry_run):
                            initiatives_summary["total_messages_sent"] += 1
                            initiatives_summary["details"][ai_username]["messages_sent_count"] += 1
                            initiatives_summary["details"][ai_username]["targets"].append(target_username)
                    else:
                        print(f"    Échec de la génération du contenu du message de {ai_username} à {target_username}.")
                else: # Dry run
                    print(f"    [DRY RUN] {ai_username} aurait initié un message à {target_username} (Raison: {reason_for_contact}).")
                    # Simuler le succès pour le résumé en dry run
                    initiatives_summary["total_messages_sent"] += 1
                    initiatives_summary["details"][ai_username]["messages_sent_count"] += 1
                    initiatives_summary["details"][ai_username]["targets"].append(target_username)
            else:
                print(f"    Aucun interlocuteur choisi par KinOS pour {ai_username}, ou raison manquante.")
            
            time.sleep(1) # Pause entre les traitements des IA pour éviter de surcharger les API

    print("\nRésumé final des initiatives :")
    print(json.dumps(initiatives_summary, indent=2))
    
    if not dry_run or initiatives_summary["total_messages_sent"] > 0 :
        create_admin_notification(tables, initiatives_summary)

    print("Processus d'initiatives de messages IA terminé.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gère les initiatives de messages des citoyens IA.")
    parser.add_argument("--dry-run", action="store_true", help="Exécute le script sans effectuer de modifications réelles.")
    parser.add_argument("--citizen1", type=str, help="Le Username du citoyen IA qui initie le message (mode ciblé). Doit être utilisé avec --citizen2.")
    parser.add_argument("--citizen2", type=str, help="Le Username du citoyen destinataire (mode ciblé). Doit être utilisé avec --citizen1.")
    parser.add_argument("--citizen", type=str, help="Le Username du citoyen IA spécifique pour lequel traiter les initiatives (mode semi-ciblé). Ne pas utiliser avec --citizen1/--citizen2.")
    parser.add_argument(
        "--model",
        type=str,
        default="local",
        help="Specify a KinOS model override (e.g., 'local', 'gpt-4-turbo'). Default: 'local'."
    )
    args = parser.parse_args()

    if (args.citizen1 and not args.citizen2) or (not args.citizen1 and args.citizen2):
        parser.error("--citizen1 et --citizen2 doivent être utilisés ensemble pour le mode ciblé.")
    if args.citizen and (args.citizen1 or args.citizen2):
        parser.error("--citizen ne peut pas être utilisé avec --citizen1 ou --citizen2.")

    process_ai_message_initiatives(
        dry_run=args.dry_run, 
        citizen1_arg=args.citizen1, 
        citizen2_arg=args.citizen2, 
        kinos_model_override_arg=args.model,
        citizen_arg=args.citizen # Passer le nouvel argument
    )

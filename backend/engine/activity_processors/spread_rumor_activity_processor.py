import logging
import json
from typing import Dict, Any, Optional

from backend.engine.utils.activity_helpers import (
    LogColors,
    _escape_airtable_value,
    get_citizen_record,
    _get_building_position_coords, # Pour obtenir les coordonnées d'un bâtiment
    calculate_haversine_distance_meters # Pour vérifier la proximité
)
from backend.engine.utils.conversation_helper import generate_conversation_turn
from backend.engine.utils.notification_helpers import create_notification
import os # Pour KINOS_API_KEY

log = logging.getLogger(__name__)

SPREAD_RUMOR_RADIUS_METERS = 20 # Rayon pour considérer les citoyens comme "présents"

def process(
    tables: Dict[str, Any],
    activity_record: Dict[str, Any],
    building_type_defs: Any, # Non utilisé directement ici, mais fait partie de la signature standard
    resource_defs: Any, # Non utilisé directement ici
    api_base_url: Optional[str] = None # Nécessaire pour conversation_helper
) -> bool:
    """
    Traite une activité 'spread_rumor'.
    Identifie les citoyens présents et initie une conversation de rumeur avec chacun.
    """
    fields = activity_record.get('fields', {})
    activity_guid = fields.get('ActivityId', activity_record.get('id', 'UnknownActivity'))
    executor_username = fields.get('Citizen')
    
    log.info(f"{LogColors.ACTIVITY}Traitement de l'activité 'spread_rumor' {activity_guid} par {executor_username}.{LogColors.ENDC}")

    if not api_base_url:
        log.error(f"{LogColors.FAIL}api_base_url est requis pour spread_rumor_activity_processor mais n'a pas été fourni.{LogColors.ENDC}")
        return False
        
    kinos_api_key = os.getenv("KINOS_API_KEY")
    if not kinos_api_key:
        log.error(f"{LogColors.FAIL}KINOS_API_KEY non trouvé. Impossible de générer des conversations pour {activity_guid}.{LogColors.ENDC}")
        return False

    notes_str = fields.get('Notes')
    if not notes_str:
        log.error(f"{LogColors.FAIL}Notes manquantes dans l'activité {activity_guid}. Impossible de récupérer les détails de la rumeur.{LogColors.ENDC}")
        return False

    try:
        # Try to parse notes as JSON
        if isinstance(notes_str, str):
            try:
                rumor_details = json.loads(notes_str)
            except json.JSONDecodeError:
                log.error(f"{LogColors.FAIL}Impossible de parser JSON depuis les notes de l'activité {activity_guid}. Notes: {notes_str}{LogColors.ENDC}")
                return False
        else:
            # Notes might already be a dictionary
            rumor_details = notes_str if isinstance(notes_str, dict) else {}
            
        target_citizen_gossip = rumor_details.get("targetCitizen")  # Peut être None pour une rumeur générale
        gossip_content = rumor_details.get("gossipContent")
        location_coords_rumor_str = rumor_details.get("locationCoords") # Coords où la rumeur est répandue
        
        if not location_coords_rumor_str: # Fallback si locationCoords n'est pas dans les notes
            # Try to get position from the activity record directly
            position_field = fields.get('Position')
            if position_field:
                try:
                    if isinstance(position_field, str):
                        location_coords_rumor_str = position_field
                    else:
                        # Position might already be a dictionary
                        location_coords_rumor_str = json.dumps(position_field) if isinstance(position_field, dict) else None
                except Exception as e:
                    log.warning(f"Error parsing Position field: {e}")
            
            # If still no coordinates, try FromBuilding or ToBuilding
            if not location_coords_rumor_str:
                from_building_id = fields.get('FromBuilding')
                to_building_id = fields.get('ToBuilding')
                building_id = to_building_id or from_building_id
                
                if building_id:
                    try:
                        building_formula = f"{{BuildingId}}='{_escape_airtable_value(building_id)}'"
                        building_records = tables['buildings'].all(formula=building_formula)
                        if building_records:
                            building_pos = _get_building_position_coords(building_records[0])
                            if building_pos:
                                location_coords_rumor_str = json.dumps(building_pos)
                    except Exception as e:
                        log.warning(f"Error getting building coordinates: {e}")
            
            # If still no coordinates, log error and return
            if not location_coords_rumor_str:
                log.error(f"{LogColors.FAIL}Coordonnées du lieu de la rumeur ('locationCoords') manquantes dans les notes de {activity_guid}.{LogColors.ENDC}")
                return False

        location_coords_rumor = json.loads(location_coords_rumor_str) if isinstance(location_coords_rumor_str, str) else location_coords_rumor_str

    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Impossible de parser JSON depuis les notes de l'activité {activity_guid}. Notes: {notes_str}{LogColors.ENDC}")
        return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}Erreur lors de l'extraction des détails de la rumeur depuis les notes de {activity_guid}: {e}{LogColors.ENDC}")
        return False

    # Vérifier si les détails de la rumeur sont présents
    # Pas besoin de cible spécifique, la rumeur peut être générale
    # Le contenu sera généré par KinOS si non spécifié
    if not gossip_content:
        log.info(f"{LogColors.OKBLUE}Contenu de rumeur non spécifié dans {activity_guid}. KinOS générera le contenu.{LogColors.ENDC}")

    # Identifier les citoyens présents au lieu de la rumeur
    all_citizens_records = tables['citizens'].all(formula="{IsAI}=TRUE()") # Uniquement les IA pour l'instant
    present_citizens_usernames = []
    
    # Récupérer la position de l'exécuteur sous forme de chaîne pour comparaison exacte
    executor_record = get_citizen_record(tables, executor_username)
    executor_pos_str = executor_record['fields'].get('Position') if executor_record else None

    for citizen_rec in all_citizens_records:
        other_citizen_username = citizen_rec['fields'].get('Username')
        if not other_citizen_username or other_citizen_username == executor_username:
            continue

        other_citizen_pos_str = citizen_rec['fields'].get('Position')
        if not other_citizen_pos_str:
            continue
        
        # Vérifier d'abord si la position est exactement la même (comparaison de chaînes)
        if executor_pos_str and other_citizen_pos_str == executor_pos_str:
            log.info(f"Citoyen {other_citizen_username} est à la même position exacte que {executor_username}. Ajouté comme destinataire de la rumeur.")
            present_citizens_usernames.append(other_citizen_username)
            continue
        
        # Sinon, vérifier la proximité par distance
        try:
            other_citizen_pos = json.loads(other_citizen_pos_str)
            distance = calculate_haversine_distance_meters(
                location_coords_rumor['lat'], location_coords_rumor['lng'],
                other_citizen_pos['lat'], other_citizen_pos['lng']
            )
            if distance <= SPREAD_RUMOR_RADIUS_METERS:
                present_citizens_usernames.append(other_citizen_username)
        except (json.JSONDecodeError, KeyError, TypeError) as e_dist:
            log.warning(f"Impossible de calculer la distance pour {other_citizen_username} au lieu de la rumeur: {e_dist}")

    if not present_citizens_usernames:
        log.info(f"{LogColors.OKBLUE}Aucun autre citoyen IA trouvé à proximité pour l'activité de rumeur {activity_guid}. Échec de l'activité pour permettre d'autres loisirs.{LogColors.ENDC}")
        return False # L'activité échoue pour permettre au système de tenter une autre activité de loisir
    
    # Limit to 10 citizens maximum to avoid overloading the system
    if len(present_citizens_usernames) > 10:
        log.info(f"{LogColors.WARNING}Trop de citoyens présents ({len(present_citizens_usernames)}). Limitation à 10 citoyens pour la rumeur.{LogColors.ENDC}")
        import random
        present_citizens_usernames = random.sample(present_citizens_usernames, 10)

    log.info(f"{LogColors.ACTIVITY}Citoyens présents pour la rumeur (par {executor_username} sur {target_citizen_gossip}): {present_citizens_usernames}{LogColors.ENDC}")

    success_count = 0
    for listener_username in present_citizens_usernames:
        # Vérifier que les profils des citoyens existent AVANT de préparer le message
        executor_record = get_citizen_record(tables, executor_username)
        listener_record = get_citizen_record(tables, listener_username)
        target_record = None
        
        if not executor_record:
            log.warning(f"    Impossible de trouver le profil de l'exécuteur {executor_username}. Conversation ignorée.")
            continue
            
        if not listener_record:
            log.warning(f"    Impossible de trouver le profil du destinataire {listener_username}. Conversation ignorée.")
            continue
            
        # Vérifier le profil de la cible seulement si une cible est spécifiée
        if target_citizen_gossip:
            target_record = get_citizen_record(tables, target_citizen_gossip)
            if not target_record:
                log.warning(f"    Impossible de trouver le profil de la cible {target_citizen_gossip}. Conversation ignorée.")
                continue
            
        # Maintenant que nous avons vérifié que tous les profils existent, nous pouvons préparer le message
        listener_firstname = listener_record['fields'].get('FirstName', listener_username)
        
        # Message direct que l'exécuteur va "dire"
        if target_citizen_gossip and target_record:
            target_firstname = target_record['fields'].get('FirstName', target_citizen_gossip)
            rumor_initiation_message = f"Oh, {listener_firstname}, you won't believe what I've heard about {target_firstname}..."
            if gossip_content:
                rumor_initiation_message += f" They say that {gossip_content}"
        else:
            # Rumeur générale sans cible spécifique
            rumor_initiation_message = f"Oh, {listener_firstname}, have you heard the latest rumor going around Venice?"
            if gossip_content:
                rumor_initiation_message += f" People are saying that {gossip_content}"
        
        log.info(f"  Tentative d'initiation de conversation de rumeur de {executor_username} à {listener_username} concernant {target_citizen_gossip}.")
        log.info(f"  Message d'initiation: \"{rumor_initiation_message[:100]}...\"")
        
        try:
            # Vérifier que les tables sont correctement passées
            if 'citizens' not in tables or tables['citizens'] is None:
                log.error(f"    Table 'citizens' manquante ou None avant d'appeler generate_conversation_turn. Tables disponibles: {list(tables.keys())}")
                continue
                
            # Vérifier explicitement que les profils existent avant d'appeler generate_conversation_turn
            executor_check = get_citizen_record(tables, executor_username)
            if not executor_check:
                log.error(f"    Impossible de trouver le profil de l'exécuteur {executor_username} juste avant d'appeler generate_conversation_turn.")
                continue
                
            listener_check = get_citizen_record(tables, listener_username)
            if not listener_check:
                log.error(f"    Impossible de trouver le profil du destinataire {listener_username} juste avant d'appeler generate_conversation_turn.")
                continue
                
            # Vérifier le profil de la cible seulement si une cible est spécifiée
            target_check = None
            if target_citizen_gossip:
                target_check = get_citizen_record(tables, target_citizen_gossip)
                if not target_check:
                    log.error(f"    Impossible de trouver le profil de la cible {target_citizen_gossip} juste avant d'appeler generate_conversation_turn.")
                    continue
            
            log.info(f"    Tous les profils vérifiés avec succès. Appel de generate_conversation_turn...")
            
            conversation_result = generate_conversation_turn(
                tables=tables,
                kinos_api_key=kinos_api_key,
                speaker_username=executor_username,
                listener_username=listener_username,
                api_base_url=api_base_url,
                interaction_mode="conversation_opener", # Pour initier la conversation
                message=rumor_initiation_message, # Le message que l'exécuteur envoie
                target_citizen_username_for_trust_impact=target_citizen_gossip, # La personne visée par la rumeur
                process_reply=True # Générer automatiquement une réponse
            )

            if conversation_result:
                log.info(f"    Conversation de rumeur initiée avec succès avec {listener_username}.")
                success_count += 1
            else:
                log.warning(f"    Échec de l'initiation de la conversation de rumeur avec {listener_username}.")
        except Exception as e:
            log.error(f"    Exception lors de l'initiation de la conversation avec {listener_username}: {e}")
            import traceback
            log.error(f"    Traceback: {traceback.format_exc()}")

    if success_count == len(present_citizens_usernames):
        log.info(f"{LogColors.OKGREEN}Toutes les conversations de rumeur pour {activity_guid} ont été initiées avec succès.{LogColors.ENDC}")
        return True
    elif success_count > 0:
        log.warning(f"{LogColors.WARNING}Certaines conversations de rumeur pour {activity_guid} ont échoué, mais au moins une a réussi.{LogColors.ENDC}")
        return True # Partiellement réussi, mais l'activité est considérée comme traitée.
    else:
        log.error(f"{LogColors.FAIL}Échec de l'initiation de toutes les conversations de rumeur pour {activity_guid}.{LogColors.ENDC}")
        return False

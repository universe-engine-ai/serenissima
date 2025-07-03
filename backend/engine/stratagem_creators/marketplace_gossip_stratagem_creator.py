import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from collections import Counter

from backend.engine.utils.activity_helpers import (
    VENICE_TIMEZONE,
    _escape_airtable_value,
    LogColors,
    get_building_record,
    _get_building_position_coords,
    find_path_between_buildings_or_coords,
    _calculate_distance_meters # Ajout de l'import manquant
)
from backend.engine.utils.notification_helpers import create_notification

log = logging.getLogger(__name__)

BASE_INFLUENCE_COST = 5 # Coût de base
SPREAD_RUMOR_DURATION_HOURS = 2
NUMBER_OF_LOCATIONS_TO_TARGET = 3

def try_create(
    tables: Dict[str, Any], 
    citizen_username: str, 
    stratagem_type: str, 
    stratagem_params: Dict[str, Any], 
    now_venice_dt: datetime,
    now_utc_dt: datetime,
    # Ajout des paramètres manquants pour find_path_between_buildings_or_coords
    api_base_url: Optional[str] = None,
    transport_api_url: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Crée un stratagème "marketplace_gossip".
    Identifie les lieux populaires et crée des activités pour y répandre des rumeurs.
    """
    log.info(f"{LogColors.STRATAGEM_CREATOR}Tentative de création du stratagème '{stratagem_type}' pour {citizen_username} avec params: {stratagem_params}{LogColors.ENDC}")

    if stratagem_type != "marketplace_gossip":
        log.error(f"{LogColors.FAIL}Créateur de stratagème pour 'marketplace_gossip' appelé avec un type incorrect: {stratagem_type}{LogColors.ENDC}")
        return None

    target_citizen_param = stratagem_params.get("targetCitizen")
    gossip_content_param = stratagem_params.get("gossipContent")

    if not gossip_content_param:
        log.error(f"{LogColors.FAIL}Paramètre requis manquant (gossipContent) pour le stratagème marketplace_gossip.{LogColors.ENDC}")
        return None
    
    # Suppression de la vérification qui empêchait de se cibler soi-même
    # Un citoyen peut maintenant répandre des rumeurs sur lui-même

    # 1. Identifier les lieux populaires
    all_ai_citizens_records = tables['citizens'].all(formula="{IsAI}=TRUE()")
    location_counts = Counter()
    for record in all_ai_citizens_records:
        position_str = record['fields'].get('Position')
        if position_str:
            location_counts[position_str] += 1
    
    if not location_counts:
        log.warning(f"{LogColors.WARNING}Aucune position de citoyen IA trouvée. Impossible de déterminer les lieux populaires.{LogColors.ENDC}")
        # Créer le stratagème mais il ne fera rien
        stratagem_id_no_loc = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
        stratagem_payload_no_loc = {
            "StratagemId": stratagem_id_no_loc, "Type": stratagem_type,
            "Name": stratagem_params.get("name") or f"Gossip vs {target_citizen_param} (No Locations)",
            "Category": "social_warfare", "ExecutedBy": citizen_username,
            "Status": "active", "ExpiresAt": (now_utc_dt + timedelta(hours=24)).isoformat(), # Courte durée si pas de lieux
            "Description": f"Attempting to spread gossip about {target_citizen_param}. No popular locations found.",
            "Notes": json.dumps({"targetCitizen": target_citizen_param, "gossipContent": gossip_content_param, "error": "No popular AI locations"}),
            "TargetCitizen": target_citizen_param, "GossipTheme": "Custom"
        }
        return [stratagem_payload_no_loc]

    most_common_locations_tuples = location_counts.most_common(NUMBER_OF_LOCATIONS_TO_TARGET)
    log.info(f"{LogColors.STRATAGEM_CREATOR}Lieux les plus populaires (Position JSON): {[loc[0] for loc in most_common_locations_tuples]}{LogColors.ENDC}")

    activities_to_create = []
    executor_citizen_record = tables['citizens'].all(formula=f"{{Username}}='{_escape_airtable_value(citizen_username)}'", max_records=1)
    if not executor_citizen_record:
        log.error(f"{LogColors.FAIL}Exécuteur {citizen_username} non trouvé.{LogColors.ENDC}")
        return None
    executor_current_pos_str = executor_citizen_record[0]['fields'].get('Position')
    executor_current_pos = json.loads(executor_current_pos_str) if executor_current_pos_str else None

    if not executor_current_pos:
        log.warning(f"{LogColors.WARNING}Exécuteur {citizen_username} n'a pas de position actuelle. Impossible de créer des activités de déplacement.{LogColors.ENDC}")
        # On pourrait créer le stratagème sans activités, ou échouer. Pour l'instant, on continue sans activités de déplacement.
    
    current_activity_start_time_utc = now_utc_dt
    ts_base = int(now_venice_dt.timestamp())

    for i, (location_pos_str, count) in enumerate(most_common_locations_tuples):
        try:
            target_coords = json.loads(location_pos_str)
        except json.JSONDecodeError:
            log.warning(f"Impossible de parser la position JSON '{location_pos_str}'. Passage au lieu suivant.")
            continue

        path_to_target_location_data = None
        travel_duration_seconds = 0 # Si déjà sur place ou pas de déplacement

        if executor_current_pos:
            # Vérifier si l'exécuteur est déjà sur place
            distance_to_target = _calculate_distance_meters(executor_current_pos, target_coords)
            if distance_to_target > 1.0: # Seuil pour considérer "pas sur place"
                path_to_target_location_data = find_path_between_buildings_or_coords(
                    tables, executor_current_pos, target_coords, api_base_url, transport_api_url
                )
                if path_to_target_location_data and path_to_target_location_data.get('success'):
                    travel_duration_seconds = path_to_target_location_data.get('timing', {}).get('durationSeconds', 0)
                else:
                    log.warning(f"Impossible de trouver un chemin vers le lieu populaire {i+1} ({location_pos_str}). Passage au lieu suivant.")
                    continue # Ne peut pas atteindre ce lieu
            # else: déjà sur place, pas besoin de goto_location
        # else: pas de position pour l'exécuteur, on ne peut pas créer de goto_location

        # Créer l'activité goto_location si nécessaire
        if path_to_target_location_data and travel_duration_seconds > 0:
            goto_activity_id = f"goto_gossip_loc_{citizen_username.lower()}_{ts_base}_{i}"
            goto_start_utc = current_activity_start_time_utc
            goto_end_utc = goto_start_utc + timedelta(seconds=travel_duration_seconds)
            
            goto_notes_details = {
                "purpose": "Travel to spread rumor",
                "targetLocationCoords": target_coords,
                "nextActivity": "spread_rumor",
                "gossipDetailsForNext": {"targetCitizen": target_citizen_param, "gossipContent": gossip_content_param}
            }
            goto_payload = {
                "ActivityId": goto_activity_id, "Type": "goto_location", "Citizen": citizen_username,
                "Path": json.dumps(path_to_target_location_data.get('path', [])),
                "StartDate": goto_start_utc.isoformat(), "EndDate": goto_end_utc.isoformat(),
                "Status": "created", "Priority": 25, # Priorité moyenne-basse pour les rumeurs
                "Title": f"Se rendre au lieu de rumeur {i+1}",
                "Notes": json.dumps(goto_notes_details)
            }
            activities_to_create.append(goto_payload)
            current_activity_start_time_utc = goto_end_utc # La prochaine activité commence après celle-ci
            executor_current_pos = target_coords # Mettre à jour la position pour la prochaine itération
        
        # Créer l'activité spread_rumor
        spread_rumor_activity_id = f"spread_rumor_{citizen_username.lower()}_{ts_base}_{i}"
        rumor_start_utc = current_activity_start_time_utc
        rumor_end_utc = rumor_start_utc + timedelta(hours=SPREAD_RUMOR_DURATION_HOURS)
        
        spread_rumor_notes_details = {
            "gossipContent": gossip_content_param,
            "locationCoords": target_coords # Où la rumeur est répandue
        }
        
        # Ajouter targetCitizen seulement s'il est spécifié
        if target_citizen_param:
            spread_rumor_notes_details["targetCitizen"] = target_citizen_param
        # FromBuilding/ToBuilding pour spread_rumor peut être le bâtiment le plus proche du target_coords
        # Pour l'instant, on le laisse vide, le processeur utilisera locationCoords des Notes.
        spread_rumor_payload = {
            "ActivityId": spread_rumor_activity_id, "Type": "spread_rumor", "Citizen": citizen_username,
            "StartDate": rumor_start_utc.isoformat(), "EndDate": rumor_end_utc.isoformat(),
            "Status": "created", "Priority": 25,
            "Title": f"Répandre une rumeur sur {target_citizen_param} au lieu {i+1}",
            "Notes": json.dumps(spread_rumor_notes_details)
        }
        activities_to_create.append(spread_rumor_payload)
        current_activity_start_time_utc = rumor_end_utc # La prochaine "série" d'activités commence après celle-ci

    # Créer le stratagème lui-même
    stratagem_id = f"stratagem-{stratagem_type.lower().replace('_', '-')}-{citizen_username.lower()}-{uuid.uuid4().hex[:8]}"
    duration_hours_stratagem = int(stratagem_params.get("durationHours", SPREAD_RUMOR_DURATION_HOURS * NUMBER_OF_LOCATIONS_TO_TARGET + 24)) # Durée pour couvrir toutes les activités + marge
    
    stratagem_payload = {
        "StratagemId": stratagem_id, "Type": stratagem_type,
        "Name": stratagem_params.get("name") or f"Gossip Campaign vs {target_citizen_param}",
        "Category": "social_warfare", "ExecutedBy": citizen_username,
        "Status": "active", # Le processeur du stratagème le marquera 'executed' une fois les activités créées
        "ExpiresAt": (now_utc_dt + timedelta(hours=duration_hours_stratagem)).isoformat(),
        "Description": f"{citizen_username} is initiating a gossip campaign against {target_citizen_param}.",
        # "Notes" sera défini plus bas avec tous les détails, y compris gossipTheme
        "TargetCitizen": target_citizen_param # Champ principal pour la cible
        # "GossipTheme": "Custom" # Retiré du payload principal
    }
    
    # Le processeur du stratagème (marketplace_gossip_stratagem_processor.py)
    # sera responsable de créer ces activités dans Airtable.
    # Ce créateur de stratagème prépare juste le payload du stratagème.
    # Le processeur du stratagème lira les Notes pour savoir quoi faire.
    # Modification: Le créateur de stratagème va maintenant retourner la liste des activités à créer.
    # Le endpoint /api/v1/engine/try-create-stratagem va créer le stratagème ET les activités.
    
    # Le processeur du stratagème marketplace_gossip_stratagem_processor.py
    # n'aura plus besoin de créer les activités. Il pourra simplement marquer le stratagème comme 'executed'.
    
    # Mettre à jour les notes du stratagème pour inclure les IDs des activités planifiées
    # (Optionnel, mais peut être utile pour le suivi)
    # planned_activity_ids = [act.get("ActivityId") for act in activities_to_create if act.get("ActivityId")]
    # stratagem_payload["Notes"] = json.dumps({
    #     "targetCitizen": target_citizen_param, 
    #     "gossipContentPreview": gossip_content_param[:50]+"...",
    #     "plannedActivities": planned_activity_ids
    # })

    log.info(f"{LogColors.STRATAGEM_CREATOR}Payload pour le stratagème 'marketplace_gossip' '{stratagem_id}': {json.dumps(stratagem_payload, indent=2)}{LogColors.ENDC}")
    for act_payload in activities_to_create:
        log.info(f"{LogColors.STRATAGEM_CREATOR}Payload d'activité planifiée: {json.dumps(act_payload, indent=2)}{LogColors.ENDC}")

    # Le endpoint s'attend à une liste de payloads de stratagème. Ici, un seul.
    # Les activités seront créées par le endpoint après la création du stratagème.
    # Pour cela, nous devons retourner les activités à créer avec le stratagème.
    # La structure de retour attendue par le endpoint est une liste de payloads de stratagème.
    # Nous allons retourner le payload du stratagème, et le endpoint devra gérer la création des activités.
    # Ou, nous modifions le endpoint pour qu'il accepte une structure plus complexe.
    # Pour l'instant, le plus simple est que le processeur du stratagème crée les activités.
    # Donc, ce créateur ne retourne que le payload du stratagème.
    # Les détails pour créer les activités (lieux, etc.) sont dans les Notes du stratagème.

    # MISE À JOUR DE LA LOGIQUE:
    # Le créateur de stratagème retourne maintenant une liste de dictionnaires.
    # Le premier est le payload du stratagème. Les suivants sont les payloads des activités.
    # Le endpoint /api/v1/engine/try-create-stratagem doit être adapté pour gérer cela.
    # Pour l'instant, nous allons supposer que le endpoint ne gère que la création du stratagème
    # et que le processeur du stratagème (marketplace_gossip_stratagem_processor.py)
    # lira les notes et créera les activités.
    # Donc, nous stockons les infos nécessaires dans les Notes du stratagème.
    
    notes_data = {
        "gossipContent": gossip_content_param, # Stocker le contenu complet
        "gossipTheme": "Custom", # Ajout de gossipTheme dans les Notes
        "popularLocations": [loc[0] for loc in most_common_locations_tuples], # Stocker les chaînes JSON des positions
        "executorStartPosition": executor_current_pos # Position de départ de l'exécuteur
    }
    
    # Ajouter targetCitizen seulement s'il est spécifié
    if target_citizen_param:
        notes_data["targetCitizen"] = target_citizen_param
    
    stratagem_payload["Notes"] = json.dumps(notes_data)
    
    return [stratagem_payload]

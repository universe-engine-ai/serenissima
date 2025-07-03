import logging
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from backend.engine.utils.activity_helpers import LogColors, _escape_airtable_value

log = logging.getLogger(__name__)

def process(
    tables: Dict[str, Any],
    stratagem_record: Dict[str, Any],
    resource_defs: Optional[Dict[str, Any]] = None, # Non utilisé directement
    building_type_defs: Optional[Dict[str, Any]] = None, # Non utilisé directement
    api_base_url: Optional[str] = None # Utilisé pour créer les activités
) -> bool:
    """
    Traite un stratagème "marketplace_gossip".
    Ce processeur crée les activités `goto_location` et `spread_rumor` basées sur les informations
    stockées dans les Notes du stratagème.
    """
    stratagem_id_custom = stratagem_record['fields'].get('StratagemId', stratagem_record['id'])
    stratagem_airtable_id = stratagem_record['id']
    executed_by = stratagem_record['fields'].get('ExecutedBy', 'UnknownCitizen')
    target_citizen = stratagem_record['fields'].get('TargetCitizen') # Cible principale du stratagème
    
    log.info(f"{LogColors.STRATAGEM_PROCESSOR}Traitement du stratagème 'marketplace_gossip' {stratagem_id_custom} par {executed_by} contre {target_citizen}.{LogColors.ENDC}")

    # Vérifier si le stratagème a déjà été exécuté
    if stratagem_record['fields'].get('Status') == 'executed':
        log.info(f"{LogColors.OKBLUE}Le stratagème 'marketplace_gossip' {stratagem_id_custom} est déjà marqué comme 'executed'.{LogColors.ENDC}")
        return True

    # Récupérer les détails du stratagème depuis les Notes
    notes_str = stratagem_record['fields'].get('Notes', '{}')
    try:
        notes_data = json.loads(notes_str)
    except json.JSONDecodeError:
        log.error(f"{LogColors.FAIL}Impossible de parser les Notes du stratagème {stratagem_id_custom}: {notes_str}{LogColors.ENDC}")
        return False

    # Extraire les informations nécessaires
    target_citizen_gossip = notes_data.get('targetCitizen')  # Peut être None
    gossip_content = notes_data.get('gossipContent')
    popular_locations = notes_data.get('popularLocations', [])
    executor_start_position = notes_data.get('executorStartPosition')

    if not gossip_content or not popular_locations:
        log.error(f"{LogColors.FAIL}Informations manquantes dans les Notes du stratagème {stratagem_id_custom}.{LogColors.ENDC}")
        return False
        
    # Vérifier que l'exécuteur et la cible existent
    executor_record = None
    try:
        executor_formula = f"{{Username}}='{_escape_airtable_value(executed_by)}'"
        executor_records = tables['citizens'].all(formula=executor_formula)
        if executor_records:
            executor_record = executor_records[0]
        else:
            log.error(f"{LogColors.FAIL}L'exécuteur {executed_by} n'existe pas. Impossible de créer les activités de rumeur.{LogColors.ENDC}")
            return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}Erreur lors de la recherche de l'exécuteur {executed_by}: {e}{LogColors.ENDC}")
        return False
        
    # Vérifier que la cible existe si elle est spécifiée
    target_record = None
    if target_citizen_gossip:
        try:
            target_formula = f"{{Username}}='{_escape_airtable_value(target_citizen_gossip)}'"
            target_records = tables['citizens'].all(formula=target_formula)
            if target_records:
                target_record = target_records[0]
            else:
                log.error(f"{LogColors.FAIL}La cible {target_citizen_gossip} n'existe pas. Impossible de créer les activités de rumeur.{LogColors.ENDC}")
                return False
        except Exception as e:
            log.error(f"{LogColors.FAIL}Erreur lors de la recherche de la cible {target_citizen_gossip}: {e}{LogColors.ENDC}")
            return False

    if not api_base_url:
        log.error(f"{LogColors.FAIL}api_base_url est requis pour créer des activités mais n'a pas été fourni.{LogColors.ENDC}")
        return False

    # Créer les activités pour chaque lieu populaire
    activities_created = 0
    current_position = executor_start_position
    current_time = datetime.now(timezone.utc)
    
    for i, location_pos_str in enumerate(popular_locations[:3]):  # Limiter à 3 lieux
        try:
            location_coords = json.loads(location_pos_str) if isinstance(location_pos_str, str) else location_pos_str
            
            # Créer l'activité goto_location
            goto_activity_id = f"goto_gossip_loc_{executed_by.lower()}_{int(current_time.timestamp())}_{i}"
            
            # Trouver le bâtiment le plus proche des coordonnées cibles
            # C'est nécessaire car goto_location_activity_creator exige un targetBuildingId
            nearest_building_id = None
            min_distance = float('inf')
            
            try:
                # Rechercher tous les bâtiments pour trouver le plus proche
                all_buildings = tables['buildings'].all()
                for building in all_buildings:
                    building_pos_str = building['fields'].get('Position')
                    if not building_pos_str:
                        continue
                    
                    try:
                        building_pos = json.loads(building_pos_str)
                        distance = ((building_pos['lat'] - location_coords['lat'])**2 + 
                                   (building_pos['lng'] - location_coords['lng'])**2)**0.5
                        
                        if distance < min_distance:
                            min_distance = distance
                            nearest_building_id = building['fields'].get('BuildingId')
                    except (json.JSONDecodeError, KeyError):
                        continue
            except Exception as e:
                log.warning(f"{LogColors.WARNING}Erreur lors de la recherche du bâtiment le plus proche: {e}{LogColors.ENDC}")
            
            # Si aucun bâtiment n'est trouvé, on ne peut pas créer l'activité goto_location
            if not nearest_building_id:
                log.warning(f"{LogColors.WARNING}Aucun bâtiment trouvé près des coordonnées {location_coords}. Impossible de créer l'activité goto_location.{LogColors.ENDC}")
                continue
                
            goto_payload = {
                "type": "goto_location",
                "citizen": executed_by,
                "title": f"Se rendre au lieu de rumeur {i+1}",
                "priority": 25,
                "targetBuildingId": nearest_building_id,  # Paramètre obligatoire pour goto_location_activity_creator
                "notes": json.dumps({
                    "purpose": "Travel to spread rumor",
                    "targetLocationCoords": location_coords,
                    "nextActivity": "spread_rumor",
                    "gossipDetailsForNext": {"targetCitizen": target_citizen_gossip, "gossipContent": gossip_content}
                })
            }
            
            # Ajouter les coordonnées de départ et d'arrivée
            if current_position:
                goto_payload["fromPosition"] = current_position
            goto_payload["toPosition"] = location_coords
            
            # Créer l'activité via l'API
            goto_response = create_activity_via_api(api_base_url, goto_activity_id, goto_payload)
            if not goto_response:
                log.warning(f"{LogColors.WARNING}Échec de la création de l'activité goto_location pour le lieu {i+1}.{LogColors.ENDC}")
                continue
                
            # Mettre à jour la position actuelle pour la prochaine itération
            current_position = location_coords
            
            # Créer l'activité spread_rumor
            spread_rumor_activity_id = f"spread_rumor_{executed_by.lower()}_{int(current_time.timestamp())}_{i}"
            spread_rumor_payload = {
                "type": "spread_rumor",
                "citizen": executed_by,
                "title": f"Répandre une rumeur {target_citizen_gossip and 'sur ' + target_citizen_gossip or 'générale'} au lieu {i+1}",
                "priority": 25,
                "notes": json.dumps({
                    "targetCitizen": target_citizen_gossip,
                    "gossipContent": gossip_content,
                    "locationCoords": location_coords
                }),
                "position": location_coords  # Position où l'activité aura lieu
            }
            
            # Créer l'activité via l'API
            spread_response = create_activity_via_api(api_base_url, spread_rumor_activity_id, spread_rumor_payload)
            if spread_response:
                activities_created += 1
            
        except (json.JSONDecodeError, Exception) as e:
            log.warning(f"{LogColors.WARNING}Erreur lors du traitement du lieu {i+1}: {e}{LogColors.ENDC}")
            continue

    # Mettre à jour le stratagème
    current_notes = stratagem_record['fields'].get('Notes', "")
    updated_notes = f"{current_notes}\n[Processor] Created {activities_created} activities for rumor spreading."
    
    update_payload = {
        'Status': 'executed',
        'Notes': updated_notes.strip()
    }
    
    # Mettre à jour ExecutedAt si ce n'est pas déjà fait
    if not stratagem_record['fields'].get('ExecutedAt'):
        update_payload['ExecutedAt'] = datetime.now(timezone.utc).isoformat()

    try:
        tables['stratagems'].update(stratagem_airtable_id, update_payload)
        log.info(f"{LogColors.OKGREEN}Stratagème 'marketplace_gossip' {stratagem_id_custom} marqué comme 'executed'. {activities_created} activités créées.{LogColors.ENDC}")
        return True
    except Exception as e:
        log.error(f"{LogColors.FAIL}Échec de la mise à jour du statut du stratagème {stratagem_id_custom}: {e}{LogColors.ENDC}")
        return False

def create_activity_via_api(api_base_url: str, activity_id: str, payload: Dict[str, Any]) -> bool:
    """
    Crée une activité via l'API.
    
    Args:
        api_base_url: URL de base de l'API
        activity_id: ID de l'activité à créer
        payload: Données de l'activité
    
    Returns:
        bool: True si l'activité a été créée avec succès, False sinon
    """
    try:
        # Vérifier que les champs obligatoires sont présents
        citizen_username = payload.get("citizen")
        activity_type = payload.get("type")
        
        if not citizen_username:
            log.error(f"{LogColors.FAIL}Champ 'citizen' manquant dans le payload pour l'activité {activity_id}.{LogColors.ENDC}")
            return False
            
        if not activity_type:
            log.error(f"{LogColors.FAIL}Champ 'type' manquant dans le payload pour l'activité {activity_id}.{LogColors.ENDC}")
            return False
        
        # Compléter le payload avec l'ID de l'activité et les champs obligatoires
        full_payload = {
            "activityId": activity_id,
            "citizenUsername": citizen_username,  # Utiliser "citizen" au lieu de "Citizen"
            "activityType": activity_type,        # Utiliser "type" au lieu de "Type"
            "activityDetails": payload
        }
        
        # Vérifier que l'URL de base est valide
        if not api_base_url:
            log.error(f"{LogColors.FAIL}URL de base de l'API non fournie pour l'activité {activity_id}.{LogColors.ENDC}")
            return False
            
        # Appeler l'API pour créer l'activité
        # L'URL correcte est /api/activities/try-create
        try:
            response = requests.post(
                f"{api_base_url}/api/activities/try-create",
                json=full_payload,
                headers={"Content-Type": "application/json"},
                timeout=90  # Augmenté de 10 à 90 secondes pour éviter les timeouts
            )
            
            if response.status_code == 200 or response.status_code == 201:
                try:
                    response_data = response.json()
                    if response_data.get("success") or response_data.get("id"):
                        log.info(f"{LogColors.OKGREEN}Activité {activity_id} créée avec succès.{LogColors.ENDC}")
                        return True
                    else:
                        log.warning(f"{LogColors.WARNING}Échec de la création de l'activité {activity_id}: {response_data.get('error', 'Raison inconnue')}{LogColors.ENDC}")
                except Exception as e:
                    log.warning(f"{LogColors.WARNING}Erreur lors du parsing de la réponse JSON pour l'activité {activity_id}: {e}{LogColors.ENDC}")
            else:
                log.warning(f"{LogColors.WARNING}Échec de la création de l'activité {activity_id}. Code: {response.status_code}, Réponse: {response.text[:500]}{LogColors.ENDC}")
                log.info(f"{LogColors.WARNING}URL utilisée: {api_base_url}/api/activities/try-create{LogColors.ENDC}")
                log.info(f"{LogColors.WARNING}Payload envoyé: {json.dumps(full_payload, indent=2)[:1000]}{LogColors.ENDC}")
            
            return False
        except requests.exceptions.RequestException as e:
            log.error(f"{LogColors.FAIL}Erreur de requête HTTP lors de la création de l'activité {activity_id}: {e}{LogColors.ENDC}")
            return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}Exception lors de la création de l'activité {activity_id}: {e}{LogColors.ENDC}")
        return False

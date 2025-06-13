import logging
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from backend.engine.utils.activity_helpers import LogColors

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
    target_citizen_gossip = notes_data.get('targetCitizen')
    gossip_content = notes_data.get('gossipContent')
    popular_locations = notes_data.get('popularLocations', [])
    executor_start_position = notes_data.get('executorStartPosition')

    if not target_citizen_gossip or not gossip_content or not popular_locations:
        log.error(f"{LogColors.FAIL}Informations manquantes dans les Notes du stratagème {stratagem_id_custom}.{LogColors.ENDC}")
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
            goto_payload = {
                "type": "goto_location",
                "citizen": executed_by,
                "title": f"Se rendre au lieu de rumeur {i+1}",
                "priority": 25,
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
                "title": f"Répandre une rumeur sur {target_citizen_gossip} au lieu {i+1}",
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
        # Compléter le payload avec l'ID de l'activité
        full_payload = {
            "activityId": activity_id,
            **payload
        }
        
        # Appeler l'API pour créer l'activité
        # L'URL correcte est /api/activities/create (sans /v1)
        response = requests.post(
            f"{api_base_url}/api/activities/create",
            json=full_payload,
            headers={"Content-Type": "application/json"}
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
            log.info(f"{LogColors.WARNING}URL utilisée: {api_base_url}/api/activities/create{LogColors.ENDC}")
            log.info(f"{LogColors.WARNING}Payload envoyé: {json.dumps(full_payload, indent=2)[:1000]}{LogColors.ENDC}")
        
        return False
    except Exception as e:
        log.error(f"{LogColors.FAIL}Exception lors de la création de l'activité {activity_id}: {e}{LogColors.ENDC}")
        return False

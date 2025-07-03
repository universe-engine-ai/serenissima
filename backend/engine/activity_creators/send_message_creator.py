import json
import uuid
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List, Union
from backend.engine.utils.activity_helpers import (
    _escape_airtable_value,
    VENICE_TIMEZONE,
    find_path_between_buildings_or_coords, # Changed import
    get_building_record,
    get_citizen_record,
    get_citizen_home,
    get_citizen_workplace,
    clean_thought_content
)

log = logging.getLogger(__name__)

def choose_interlocutor_via_kinos(
    tables: Dict[str, Any],
    ai_username: str,
    ai_ledger: str,
    api_base_url: str
) -> Optional[Tuple[str, str]]:
    """
    Appelle KinOS pour choisir un interlocuteur et la raison de l'interaction.
    Retourne (target_username, reason) ou (None, None).
    """
    try:
        # Extraire le prénom et la classe sociale du citoyen à partir du markdown
        ai_display_name = ai_username  # Valeur par défaut
        ai_social_class = None  # Valeur par défaut
        
        # Rechercher le prénom dans le markdown
        first_name_match = re.search(r'firstName: ([^\n]+)', ai_ledger, re.IGNORECASE) or \
                          re.search(r'FirstName: ([^\n]+)', ai_ledger, re.IGNORECASE)
        if first_name_match:
            ai_display_name = first_name_match.group(1).strip()
        
        # Rechercher la classe sociale dans le markdown
        social_class_match = re.search(r'socialClass: ([^\n]+)', ai_ledger, re.IGNORECASE) or \
                             re.search(r'SocialClass: ([^\n]+)', ai_ledger, re.IGNORECASE)
        if social_class_match:
            ai_social_class = social_class_match.group(1).strip()

        # Importer les fonctions nécessaires pour appeler KinOS
        from backend.engine.utils.conversation_helper import (
            make_kinos_channel_call,
            get_kinos_model_for_social_class,
            clean_thought_content
        )
        import os
        import json

        # Récupérer la clé API KinOS
        kinos_api_key = os.getenv("KINOS_API_KEY")
        if not kinos_api_key:
            log.error("Clé API KinOS non trouvée dans les variables d'environnement")
            return None, None

        # Le canal "strategist" est un canal conceptuel pour ce type de décision
        kinos_channel_for_decision = "strategist" 

        prompt = (
            f"You are {ai_display_name}, an AI citizen of Venice. Your ledger "
            f"is provided in `addSystem` in markdown format.\n\n"
            f"Based on this information, analyze your current situation and identify another citizen with whom initiating a conversation would be most beneficial or strategically relevant for you right now. "
            f"Consider your goals, active problems, opportunities, and the nature of your relationships. Could initiating or discussing a **Stratagem** be a reason for contact? Note that gossip or rumors are not necessarily negative (though they often are). Information on available stratagems is in the 'Available Stratagems' section of your ledger.\n\n"
            f"Your response MUST be a JSON object with two keys: 'target_username' (the Username of the citizen you choose) and 'reason' (a specific compelling reason for contacting them, focusing on gameplay or possibly narrative progression, potentially related to a stratagem).\n"
            f"If no compelling interaction is identified, respond with: {{\"target_username\": null, \"reason\": \"<Explanations>\"}}\n\n"
            f"Chosen interaction (JSON):"
        )

        # Utiliser le modèle local par défaut pour cette décision
        effective_model = "local"
        
        log.info(f"Appel à KinOS pour choisir un interlocuteur pour {ai_username} (Modèle: {effective_model})")
        
        # Créer un wrapper pour passer le markdown comme addSystem
        wrapper_data = {
            "ledger_markdown": ai_ledger
        }
        
        # Appel à KinOS via make_kinos_channel_call
        raw_response_content = make_kinos_channel_call(
            kinos_api_key=kinos_api_key,
            speaker_username=ai_username,
            channel_name=kinos_channel_for_decision,
            prompt=prompt,
            add_system_data=wrapper_data, 
            kinos_model_override=effective_model,
            tables=tables
        )
        
        if not raw_response_content:
            log.warning(f"KinOS n'a pas retourné de réponse pour la décision de l'interlocuteur pour {ai_username}")
            return None, None

        try:
            # Nettoyer le contenu avant de parser le JSON (KinOS peut ajouter des <think> tags)
            cleaned_response = clean_thought_content(tables, raw_response_content)
            
            # Extraire le JSON de la réponse nettoyée
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if not json_match:
                log.warning(f"Réponse KinOS ne contient pas de JSON valide pour {ai_username}: {cleaned_response}")
                return None, None
                
            decision_data = json.loads(json_match.group(0))
            target_username = decision_data.get("target_username")
            reason = decision_data.get("reason")

            if target_username and reason:
                log.info(f"KinOS a choisi {target_username} pour {ai_username}. Raison: {reason}")
                return target_username, reason
            else:
                log.info(f"KinOS n'a pas identifié d'interlocuteur pour {ai_username}. Raison: {reason}")
                return None, None
        except json.JSONDecodeError:
            log.error(f"Erreur de décodage JSON de la réponse KinOS pour {ai_username}")
            return None, None
        except Exception as e:
            log.error(f"Erreur lors du traitement de la réponse KinOS pour {ai_username}: {e}")
            return None, None
            
    except Exception as e:
        log.error(f"Erreur lors du choix d'un interlocuteur pour {ai_username}: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None, None

def try_create(
    tables: Dict[str, Any],
    citizen_record: Dict[str, Any],
    details: Dict[str, Any],
    api_base_url: str, # Added
    transport_api_url: str # Added
) -> Optional[Dict]:
    """
    Create the complete send_message activity chain:
    1. A goto_location activity for travel to the receiver's location or specified meeting place
    2. A deliver_message_interaction activity to deliver the message
    
    This approach creates the complete activity chain upfront.
    
    If receiverUsername is not specified, it will attempt to dynamically select
    a recipient using the choose_interlocutor_via_kinos function.
    """
    # Extract required parameters
    receiver_username = details.get('receiverUsername')
    content = details.get('content')
    message_type = details.get('messageType', 'personal')
    target_building_id = details.get('targetBuildingId')  # Optional specific meeting place
    conversation_length = details.get('conversationLength', 3)  # Default to 3 exchanges
    channel = details.get('channel')  # Extract channel parameter
    
    # Si aucun destinataire n'est spécifié, essayer d'en choisir un dynamiquement
    if not receiver_username:
        log.info("Aucun destinataire spécifié. Tentative de sélection dynamique d'un interlocuteur.")
        sender_username = citizen_record['fields'].get('Username')
        
        # Récupérer le ledger du citoyen pour l'analyse
        try:
            ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={sender_username}&format=markdown"
            import requests
            response = requests.get(ledger_url, timeout=150)
            if response.ok:
                ai_ledger = response.text
                receiver_username, reason_for_contact = choose_interlocutor_via_kinos(
                    tables, 
                    sender_username, 
                    ai_ledger,
                    api_base_url
                )
                
                if receiver_username and not content:
                    # Générer un contenu de message basé sur la raison du contact
                    content = f"Bonjour, je vous contacte à propos de: {reason_for_contact}"
                    log.info(f"Message généré automatiquement pour {receiver_username}: {content}")
                    
                    # Ajouter la raison aux notes pour le traitement
                    if isinstance(details.get('notes'), dict):
                        details['notes']['purpose'] = reason_for_contact
                        details['notes']['dynamicallySelected'] = True
                    else:
                        details['notes'] = {
                            'purpose': reason_for_contact,
                            'dynamicallySelected': True
                        }
            else:
                log.error(f"Impossible de récupérer le ledger pour {sender_username}: {response.status_code}")
        except Exception as e:
            log.error(f"Erreur lors de la récupération du ledger ou de la sélection d'un interlocuteur: {e}")
            import traceback
            log.error(traceback.format_exc())
    
    # Extract inReplyToMessageId and other parameters from the nested 'notes' field if present
    # The 'details' argument to this function *is* activityParameters from the API call.
    activity_params_notes_field = {}
    
    # Handle both string and object formats for notes
    if isinstance(details.get('notes'), str):
        try:
            activity_params_notes_field = json.loads(details.get('notes', '{}'))
        except json.JSONDecodeError:
            activity_params_notes_field = {}
    elif isinstance(details.get('notes'), dict):
        activity_params_notes_field = details.get('notes', {})
    
    in_reply_to_message_id = activity_params_notes_field.get('inReplyToMessageId')
    target_citizen_username_for_trust_impact = activity_params_notes_field.get('targetCitizenUsernameForTrustImpact') # New
    
    # Validate required parameters
    if not (receiver_username and content):
        log.error(f"Missing required details for send_message: receiverUsername or content. Details received: {details}")
        log.error(f"Details type: {type(details)}, Keys: {list(details.keys()) if isinstance(details, dict) else 'Not a dict'}")
        
        # Dump the entire details object for debugging
        try:
            log.error(f"Full details object: {json.dumps(details)}")
        except:
            log.error(f"Could not serialize details object to JSON")
        
        # Check if activityParameters might be nested one level deeper (common API issue)
        if 'activityParameters' in details and isinstance(details['activityParameters'], dict):
            nested_params = details['activityParameters']
            log.info(f"Found nested activityParameters, trying to use those instead: {nested_params}")
            receiver_username = nested_params.get('receiverUsername')
            content = nested_params.get('content')
            message_type = nested_params.get('messageType', 'personal')
            target_building_id = nested_params.get('targetBuildingId')
            conversation_length = nested_params.get('conversationLength', 3)
            channel = nested_params.get('channel')
            
            # Re-validate after extracting from nested parameters
            if not (receiver_username and content):
                log.error(f"Still missing required details after checking nested parameters")
                
                # Essayer de sélectionner dynamiquement un destinataire si toujours manquant
                if not receiver_username:
                    log.info("Tentative de sélection dynamique d'un interlocuteur après échec de l'extraction des paramètres imbriqués.")
                    sender_username = citizen_record['fields'].get('Username')
                    
                    try:
                        ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={sender_username}&format=markdown"
                        import requests
                        response = requests.get(ledger_url, timeout=60)
                        if response.ok:
                            ai_ledger = response.text
                            receiver_username, reason_for_contact = choose_interlocutor_via_kinos(
                                tables, 
                                sender_username, 
                                ai_ledger,
                                api_base_url
                            )
                            
                            if receiver_username and not content:
                                content = f"Bonjour, je vous contacte à propos de: {reason_for_contact}"
                                log.info(f"Message généré automatiquement pour {receiver_username}: {content}")
                                
                                # Ajouter la raison aux notes
                                nested_params['notes'] = {
                                    'purpose': reason_for_contact,
                                    'dynamicallySelected': True
                                }
                    except Exception as e:
                        log.error(f"Erreur lors de la sélection dynamique d'un interlocuteur: {e}")
                
                # Re-vérifier après tentative de sélection dynamique
                if not (receiver_username and content):
                    log.error(f"Toujours des détails manquants après tentative de sélection dynamique")
                    return None
                else:
                    log.info(f"Paramètres complétés avec succès: receiver={receiver_username}, content_length={len(content)}")
            else:
                log.info(f"Successfully extracted parameters from nested structure: receiver={receiver_username}, content_length={len(content)}")
                # Continue with the extracted parameters
        else:
            # Try to look for parameters directly in the request body
            # This is a fallback for when the API structure might be inconsistent
            if isinstance(details, dict) and 'citizenUsername' in details and 'activityType' in details:
                log.info("Found top-level request structure, checking for parameters at root level")
                if 'receiverUsername' in details:
                    receiver_username = details.get('receiverUsername')
                    log.info(f"Found receiverUsername at root level: {receiver_username}")
                if 'content' in details:
                    content = details.get('content')
                    log.info(f"Found content at root level, length: {len(content) if content else 0}")
                if 'messageType' in details:
                    message_type = details.get('messageType', 'personal')
                if 'targetBuildingId' in details:
                    target_building_id = details.get('targetBuildingId')
                if 'conversationLength' in details:
                    conversation_length = details.get('conversationLength', 3)
                if 'channel' in details:
                    channel = details.get('channel')
                
                # Re-validate after extracting from root level
                if not (receiver_username and content):
                    # Essayer de sélectionner dynamiquement un destinataire si toujours manquant
                    if not receiver_username:
                        log.info("Tentative de sélection dynamique d'un interlocuteur après échec de l'extraction des paramètres au niveau racine.")
                        sender_username = citizen_record['fields'].get('Username')
                        
                        try:
                            ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={sender_username}&format=markdown"
                            import requests
                            response = requests.get(ledger_url, timeout=60)
                            if response.ok:
                                ai_ledger = response.text
                                receiver_username, reason_for_contact = choose_interlocutor_via_kinos(
                                    tables, 
                                    sender_username, 
                                    ai_ledger,
                                    api_base_url
                                )
                                
                                if receiver_username and not content:
                                    content = f"Bonjour, je vous contacte à propos de: {reason_for_contact}"
                                    log.info(f"Message généré automatiquement pour {receiver_username}: {content}")
                                    
                                    # Ajouter la raison aux notes
                                    details['notes'] = {
                                        'purpose': reason_for_contact,
                                        'dynamicallySelected': True
                                    }
                        except Exception as e:
                            log.error(f"Erreur lors de la sélection dynamique d'un interlocuteur: {e}")
                    
                    # Re-vérifier après tentative de sélection dynamique
                    if not (receiver_username and content):
                        log.error(f"Toujours des détails manquants après tentative de sélection dynamique")
                        return None
                    else:
                        log.info(f"Paramètres complétés avec succès: receiver={receiver_username}, content_length={len(content)}")
                else:
                    log.info(f"Successfully extracted parameters from root level: receiver={receiver_username}, content_length={len(content)}")
                    # Continue with the extracted parameters
            else:
                # Dernière tentative de sélection dynamique avant d'abandonner
                sender_username = citizen_record['fields'].get('Username')
                try:
                    ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={sender_username}&format=markdown"
                    import requests
                    response = requests.get(ledger_url, timeout=60)
                    if response.ok:
                        ai_ledger = response.text
                        receiver_username, reason_for_contact = choose_interlocutor_via_kinos(
                            tables, 
                            sender_username, 
                            ai_ledger,
                            api_base_url
                        )
                        
                        if receiver_username:
                            if not content:
                                content = f"Bonjour, je vous contacte à propos de: {reason_for_contact}"
                            log.info(f"Message généré automatiquement pour {receiver_username}: {content}")
                            
                            # Créer ou mettre à jour les notes
                            if not isinstance(details, dict):
                                details = {}
                            details['notes'] = {
                                'purpose': reason_for_contact,
                                'dynamicallySelected': True
                            }
                            
                            # Re-vérifier après tentative de sélection dynamique
                            if receiver_username and content:
                                log.info(f"Paramètres complétés avec succès via sélection dynamique: receiver={receiver_username}, content_length={len(content)}")
                            else:
                                log.error(f"Échec de la sélection dynamique finale")
                                return None
                        else:
                            log.error(f"Échec de la sélection dynamique finale - aucun destinataire trouvé")
                            return None
                    else:
                        log.error(f"Impossible de récupérer le ledger pour la sélection dynamique finale")
                        return None
                except Exception as e:
                    log.error(f"Erreur lors de la tentative finale de sélection dynamique: {e}")
                    return None
    
    # Validate conversation_length
    if not isinstance(conversation_length, int) or conversation_length < 1:
        log.warning(f"Invalid conversationLength: {conversation_length}. Using default value of 3.")
        conversation_length = 3

    sender = citizen_record['fields'].get('Username')
    ts = int(datetime.now(VENICE_TIMEZONE).timestamp())
    
    # Get current citizen position to determine path
    sender_position_str = citizen_record['fields'].get('Position')
    current_position = None
    if sender_position_str:
        try:
            current_position = json.loads(sender_position_str)
        except json.JSONDecodeError:
            log.error(f"Could not parse sender position: {sender_position_str}")
            return None
    
    # Get receiver record to determine their position
    receiver_record = get_citizen_record(tables, receiver_username)
    if not receiver_record:
        log.error(f"Receiver {receiver_username} not found")
        return None
    
    # Determine the destination (receiver's location or specified meeting place)
    destination_building_id = None
    destination_type = None
    receiver_position = None
    
    # If a specific target building was provided, use it
    if target_building_id:
        target_building_record = get_building_record(tables, target_building_id)
        if target_building_record:
            destination_building_id = target_building_id
            destination_type = 'meeting_place'
            log.info(f"Using specified meeting place: {destination_building_id}")
        else:
            log.warning(f"Specified building {target_building_id} not found. Will try to find receiver's location.")
    
    # If no valid destination yet, try receiver's current location
    if not destination_building_id:
        receiver_position_str = receiver_record['fields'].get('Position')
        if receiver_position_str:
            try:
                receiver_position = json.loads(receiver_position_str)
                destination_type = 'receiver_location'
                log.info(f"Using receiver's current position as destination")
            except json.JSONDecodeError:
                log.error(f"Could not parse receiver position: {receiver_position_str}")
                # Continue to try other options
    
    # If still no destination, try receiver's workplace
    if not destination_building_id and not receiver_position:
        receiver_workplace = get_citizen_workplace(tables, receiver_username)
        if receiver_workplace:
            destination_building_id = receiver_workplace
            destination_type = 'receiver_workplace'
            log.info(f"Using receiver's workplace as destination: {destination_building_id}")
    
    # If still no destination, try receiver's home
    if not destination_building_id and not receiver_position:
        receiver_home = get_citizen_home(tables, receiver_username)
        if receiver_home:
            destination_building_id = receiver_home
            destination_type = 'receiver_home'
            log.info(f"Using receiver's home as destination: {destination_building_id}")
    
    # If still no valid destination, fail
    if not destination_building_id and not receiver_position:
        log.error(f"Could not determine a valid destination to meet receiver {receiver_username}")
        return None
    
    # Calculate path to destination
    path_data = None
    if destination_type != 'receiver_location':
        destination_building_record = get_building_record(tables, destination_building_id)
        if not destination_building_record:
            log.error(f"Could not find building record for {destination_building_id}")
            return None # Changed from False
        # Use find_path_between_buildings_or_coords
        path_data = find_path_between_buildings_or_coords(
            tables=tables,
            start_location=current_position, # current_position is {lat, lng}
            end_location=destination_building_record, # This is a full building record
            api_base_url=api_base_url,
            transport_api_url=transport_api_url
        )
    else:
        # For receiver's current location, use find_path_between_buildings_or_coords
        if current_position and receiver_position:
            path_data = find_path_between_buildings_or_coords(
                tables=tables,
                start_location=current_position,
                end_location=receiver_position, # receiver_position is {lat, lng}
                api_base_url=api_base_url,
                transport_api_url=transport_api_url
            )
        else:
            path_data = None # Ensure path_data is None if positions are missing
    
    if not path_data or not path_data.get('success') or not path_data.get('path'):
        log.error(f"Could not find path to destination. Path data: {path_data}")
        return None
    
    # Create activity IDs
    goto_activity_id = f"goto_location_for_message_{sender}_{receiver_username}_{ts}"
    message_activity_id = f"deliver_message_interaction_{sender}_{receiver_username}_{ts}"
    
    now_utc = datetime.utcnow()
    travel_start_date = now_utc.isoformat()
    
    # Calculate travel end date based on path duration
    duration_seconds = path_data.get('timing', {}).get('durationSeconds', 1800)  # Default 30 min if not specified
    travel_end_date = (now_utc + timedelta(seconds=duration_seconds)).isoformat()
    
    # Calculate message delivery activity times (10 minutes after arrival)
    message_start_date = travel_end_date  # Start immediately after arrival
    
    # Calculate message end date (10 minutes after start)
    message_end_date = (now_utc + timedelta(seconds=duration_seconds) + timedelta(minutes=10)).isoformat()
    
    # Store message details in the Notes field for the processor to use
    details_for_processor = {
        "receiverUsername": receiver_username,
        "content": content,
        "messageType": message_type,
        "conversationLength": conversation_length
    }
    
    # Add addMessage if provided in the original details
    if details.get('addMessage'):
        details_for_processor["addMessage"] = details.get('addMessage')
        log.info(f"Including addMessage in Details for deliver_message_interaction.")
    
    # Add channel if provided
    if channel:
        details_for_processor["channel"] = channel
    if in_reply_to_message_id:
        details_for_processor["inReplyToMessageId"] = in_reply_to_message_id
        log.info(f"Including inReplyToMessageId: {in_reply_to_message_id} in Details for deliver_message_interaction.")
    if target_citizen_username_for_trust_impact: # New
        details_for_processor["targetCitizenUsernameForTrustImpact"] = target_citizen_username_for_trust_impact
        log.info(f"Including targetCitizenUsernameForTrustImpact: {target_citizen_username_for_trust_impact} in Details for deliver_message_interaction.")
    
    # Include any other fields from the original notes that might be needed
    if isinstance(activity_params_notes_field, dict):
        for key, value in activity_params_notes_field.items():
            if key not in ["inReplyToMessageId", "targetCitizenUsernameForTrustImpact"] and key not in details_for_processor:
                details_for_processor[key] = value
    
    details_json = json.dumps(details_for_processor)
    
    # 1. Create goto_location activity
    goto_payload = {
        "ActivityId": goto_activity_id,
        "Type": "goto_location",
        "Citizen": sender,
        "FromBuilding": None,  # Starting from current position
        "ToBuilding": destination_building_id if destination_type != 'receiver_location' else None,
        "Path": json.dumps(path_data.get('path', [])),
        "Notes": json.dumps({ # Changed Details to Notes
            "receiverUsername": receiver_username,
            "content": content,
            "messageType": message_type,
            "conversationLength": conversation_length,
            "activityType": "send_message",
            "nextStep": "deliver_message_interaction",
            "channel": channel
        }),
        "Status": "created",
        "Title": f"Traveling to deliver a message to {receiver_username}",
        "Description": f"Traveling to meet {receiver_username} to deliver a {message_type} message",
        "CreatedAt": travel_start_date,
        "StartDate": travel_start_date,
        "EndDate": travel_end_date,
        "Priority": 30  # Medium priority for social activities
    }
    
    # 2. Create deliver_message_interaction activity (to be executed after arrival)
    message_payload = {
        "ActivityId": message_activity_id,
        "Type": "deliver_message_interaction",
        "Citizen": sender,
        "FromBuilding": destination_building_id if destination_type != 'receiver_location' else None,
        "ToBuilding": destination_building_id if destination_type != 'receiver_location' else None,
        "Notes": details_json, # This contains the actual message details for the processor
        "Status": "created",
        "Title": f"Delivering a message to {receiver_username}",
        "Description": f"Having a conversation with {receiver_username} to deliver a {message_type} message",
        # The following descriptive note was overwriting the essential details_json.
        # It can be removed or stored in a different field if necessary, e.g., "InternalComment".
        # "InternalComment": f"Second step of send_message process. Will create a message record and potentially update relationship.",
        "CreatedAt": travel_start_date,  # Created at the same time as the goto activity
        "StartDate": message_start_date,  # But starts after the goto activity ends
        "EndDate": message_end_date,
        "Priority": 30  # Medium priority for social activities
    }

    try:
        # Create both activities in sequence
        goto_activity_record = tables["activities"].create(goto_payload)
        # Ensure the second activity is also created before considering it a full success for the chain.
        # If message_payload creation fails, we might have a partial chain.
        # For now, we return the first activity if it's created.
        # A more robust solution might involve transactions or cleanup if the second part fails.
        tables["activities"].create(message_payload)
        
        log.info(f"Created complete send_message activity chain for citizen {sender} to {receiver_username}:")
        log.info(f"  1. goto_location activity {goto_activity_id} (Airtable ID: {goto_activity_record['id']})")
        log.info(f"  2. deliver_message_interaction activity {message_activity_id}")
        return goto_activity_record # Return the first created activity record
    except Exception as e:
        log.error(f"Failed to create send_message activity chain: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None # Return None on failure

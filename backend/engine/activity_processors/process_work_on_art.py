import logging
import json
import os
import requests
import threading # Import threading
import tempfile # Added for temporary image storage
from datetime import datetime # Added for image filename date
import re # Added for slugify & artwork parsing
import base64 # Added for image encoding
from typing import Dict, Any, Optional, List # Added List

# VENICE_TIMEZONE is not directly used here but LogColors is.
from backend.engine.utils.activity_helpers import LogColors

log = logging.getLogger(__name__)

# KinOS constants
# Always use the production KinOS API URL
KINOS_API_URL = "https://api.kinos-engine.ai"
KINOS_BLUEPRINT = "serenissima-ai"

# --- BEGIN COPIED HELPER FUNCTION (adapted from updatecitizenDescriptionAndImage.py) ---
DEFAULT_FASTAPI_URL = "https://backend.serenissima.ai/" # Default, can be overridden by API_BASE_URL env var

def slugify(text: str) -> str:
    """
    Convert a string to a slug suitable for filenames.
    Example: "My Awesome Painting!" -> "my_awesome_painting"
    """
    if not text:
        return "untitled"
    text = text.lower()
    text = re.sub(r'\s+', '_', text) # Replace spaces with underscores
    text = re.sub(r'[^\w_.-]', '', text) # Remove non-alphanumeric characters except underscore, dot, hyphen
    text = text.strip('_.-') # Remove leading/trailing underscores, dots, hyphens
    return text if text else "untitled"

def _upload_file_to_backend_helper(
    local_file_path: str,
    filename_on_server: str,
    destination_folder_on_server: str,
    api_url: str,
    api_key: str
) -> Optional[str]:
    """
    Uploads a file to the backend /api/upload-asset endpoint.
    Args:
        local_file_path (str): The path to the local file to upload.
        filename_on_server (str): The desired filename for the asset on the server.
        destination_folder_on_server (str): The relative path of the folder on the server.
        api_url (str): The base URL of the FastAPI backend.
        api_key (str): The API key for the upload endpoint.
    Returns:
        Optional[str]: The full public URL of the uploaded asset, or None if upload failed.
    """
    upload_endpoint = f"{api_url.rstrip('/')}/api/upload-asset"
    try:
        with open(local_file_path, 'rb') as f:
            files = {'file': (filename_on_server, f)}
            data = {'destination_path': destination_folder_on_server}
            headers = {'X-Upload-Api-Key': api_key}
            
            log.info(f"Uploading '{local_file_path}' as '{filename_on_server}' to backend folder '{destination_folder_on_server}' via {upload_endpoint}...")
            response = requests.post(upload_endpoint, files=files, data=data, headers=headers, timeout=180)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("success") and response_data.get("relative_path"):
                    relative_backend_path = response_data["relative_path"]
                    full_public_url = f"{api_url.rstrip('/')}/public_assets/{relative_backend_path.lstrip('/')}"
                    log.info(f"Success: '{local_file_path}' uploaded. Public URL: '{full_public_url}'")
                    return full_public_url
                else:
                    log.error(f"Upload successful but response format unexpected: {response_data}")
                    return None
            else:
                log.error(f"Upload failed for {local_file_path}. Status: {response.status_code}, Response: {response.text}")
                return None
    except requests.exceptions.RequestException as e:
        log.error(f"Request error during upload of {local_file_path}: {e}")
        return None
    except IOError as e:
        log.error(f"IO error reading {local_file_path}: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error during upload of {local_file_path}: {e}")
        return None
# --- END COPIED HELPER FUNCTION ---

def _generate_and_upload_painting_for_artist(
    ideogram_prompt: str,
    artwork_name: str,
    aspect_ratio: str,
    magic_prompt_setting: str, # Should be "ON" or "OFF"
    negative_prompt_text: Optional[str],
    style_type_setting: str, # Should be "REALISTIC" or other valid Ideogram style
    artist_username: str,
    api_base_url_for_upload: str
) -> Optional[str]:
    """
    Generates a painting using Ideogram and uploads it to the backend.
    Returns the public URL of the uploaded image or None.
    """
    log.info(f"Generating painting for {artist_username} with prompt: {ideogram_prompt[:100]}...")
    
    ideogram_api_key = os.getenv('IDEOGRAM_API_KEY')
    upload_api_key = os.getenv('UPLOAD_API_KEY')

    if not ideogram_api_key:
        log.error("IDEOGRAM_API_KEY environment variable is not set. Cannot generate painting.")
        return None
    if not upload_api_key:
        log.error("UPLOAD_API_KEY environment variable is not set. Cannot upload painting.")
        return None

    ideogram_payload = {
        "prompt": ideogram_prompt,
        "aspect_ratio": aspect_ratio,
        "magic_prompt": magic_prompt_setting, # "ON" or "OFF"
        "style": style_type_setting, # e.g. "photo", "painting", "illustration", "3d_render", "cinematic" - user specified REALISTIC
                                     # Ideogram docs mention "style_type", but examples use "style". Let's try "style".
                                     # If "REALISTIC" is a specific style_type, the API call might need adjustment.
                                     # For Ideogram v1 /ideogram-v3/generate, it's "style_type"
        "model": "V_3" # Using V_3 as per updatecitizenDescriptionAndImage.py
    }
    if negative_prompt_text:
        ideogram_payload["negative_prompt"] = negative_prompt_text

    try:
        log.info(f"Ideogram payload for {artist_username}: {json.dumps(ideogram_payload)}")
        response = requests.post(
            "https://api.ideogram.ai/v1/ideogram-v3/generate", # Using V3 endpoint
            headers={"Api-Key": ideogram_api_key, "Content-Type": "application/json"},
            json=ideogram_payload
        )
        
        if response.status_code != 200:
            log.error(f"Error from Ideogram API (painting for {artist_username}): {response.status_code} {response.text}")
            return None
        
        result = response.json()
        image_url_from_ideogram = result.get("data", [{}])[0].get("url")
        if not image_url_from_ideogram:
            log.error(f"No image URL in Ideogram response for {artist_username} painting.")
            return None
        
        image_response = requests.get(image_url_from_ideogram, stream=True)
        if not image_response.ok:
            log.error(f"Failed to download initial painting for {artist_username}: {image_response.status_code}")
            return None
        
        tmp_initial_image_path: Optional[str] = None
        tmp_upscaled_image_path: Optional[str] = None
        final_image_path_to_upload: Optional[str] = None
        public_url: Optional[str] = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                for chunk in image_response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_initial_image_path = tmp_file.name
            
            log.info(f"Initial painting for {artist_username} downloaded to temporary file: {tmp_initial_image_path}")

            # Attempt to upscale the image
            tmp_upscaled_image_path = _upscale_image_ideogram(tmp_initial_image_path, ideogram_api_key)

            if tmp_upscaled_image_path:
                log.info(f"Using upscaled image for {artist_username}: {tmp_upscaled_image_path}")
                final_image_path_to_upload = tmp_upscaled_image_path
            else:
                log.warning(f"Upscaling failed for {artist_username}, using original image: {tmp_initial_image_path}")
                final_image_path_to_upload = tmp_initial_image_path

            if final_image_path_to_upload:
                date_str = datetime.now().strftime("%Y%m%d")
                safe_artwork_name = slugify(artwork_name)
                # Ensure filename has .png extension if upscaled image was .png
                filename_on_server = f"{artist_username}_{safe_artwork_name}_{date_str}.png"
                
                public_url = _upload_file_to_backend_helper(
                    local_file_path=final_image_path_to_upload,
                    filename_on_server=filename_on_server,
                    destination_folder_on_server="images/paintings",
                    api_url=api_base_url_for_upload,
                    api_key=upload_api_key
                )
            else: # Should not happen if tmp_initial_image_path was set
                log.error(f"No image path available to upload for {artist_username}.")

        finally:
            # Clean up temporary files
            if tmp_initial_image_path and os.path.exists(tmp_initial_image_path):
                try:
                    os.remove(tmp_initial_image_path)
                except OSError as e:
                    log.error(f"Error removing temporary initial painting file {tmp_initial_image_path}: {e}")
            if tmp_upscaled_image_path and os.path.exists(tmp_upscaled_image_path) and tmp_upscaled_image_path != tmp_initial_image_path:
                try:
                    os.remove(tmp_upscaled_image_path)
                except OSError as e:
                    log.error(f"Error removing temporary upscaled painting file {tmp_upscaled_image_path}: {e}")
        
        return public_url
    except Exception as e:
        log.error(f"Error in painting generation/upscaling/upload process for {artist_username}: {e}")
        return None

def _upscale_image_ideogram(
    original_image_path: str,
    ideogram_api_key: str,
    resemblance: int = 55,
    detail: int = 90
) -> Optional[str]:
    """
    Upscales an image using the Ideogram API and returns the path to the temporary upscaled image.
    """
    log.info(f"Attempting to upscale image: {original_image_path}")
    try:
        with open(original_image_path, 'rb') as f:
            files = {'image_file': (os.path.basename(original_image_path), f)}
            image_request_payload = json.dumps({
                "resemblance": resemblance,
                "detail": detail
            })
            data = {'image_request': image_request_payload}
            
            headers = {'Api-Key': ideogram_api_key} # No Content-Type for multipart by requests

            response = requests.post(
                "https://api.ideogram.ai/upscale",
                files=files,
                data=data,
                headers=headers,
                timeout=120 # Upscaling might take time
            )

        if response.status_code != 200:
            log.error(f"Error from Ideogram /upscale API: {response.status_code} {response.text}")
            return None

        result = response.json()
        upscaled_image_url = result.get("data", [{}])[0].get("url")
        if not upscaled_image_url:
            log.error("No upscaled image URL in Ideogram /upscale response.")
            return None

        log.info(f"Upscaled image URL from Ideogram: {upscaled_image_url}")
        
        # Download the upscaled image
        upscaled_image_response = requests.get(upscaled_image_url, stream=True, timeout=60)
        if not upscaled_image_response.ok:
            log.error(f"Failed to download upscaled image: {upscaled_image_response.status_code}")
            return None

        # Save upscaled image to a new temporary file
        # Determine suffix from original, or default to .png
        _, suffix = os.path.splitext(original_image_path)
        if not suffix: suffix = ".png" # Default if original had no suffix (unlikely for temp files)

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_upscaled_file:
            for chunk in upscaled_image_response.iter_content(chunk_size=8192):
                tmp_upscaled_file.write(chunk)
            tmp_upscaled_file_path = tmp_upscaled_file.name
        
        log.info(f"Upscaled image downloaded to temporary file: {tmp_upscaled_file_path}")
        return tmp_upscaled_file_path

    except Exception as e:
        log.error(f"Error during Ideogram image upscaling: {e}")
        return None

def _fetch_and_encode_latest_paintings(
    tables: Dict[str, Any], 
    artist_username: str, 
    limit: int = 3
) -> List[str]:
    """
    Fetches the latest 'limit' paintings for an artist, downloads, 
    and base64 encodes them as data URIs.
    """
    log.info(f"Fetching latest {limit} paintings for {artist_username}...")
    encoded_images: List[str] = []
    try:
        activities_table = tables.get('activities')
        if not activities_table:
            log.error("Activities table not found in 'tables' dict.")
            return []

        # Fetch recent work_on_art activities for the artist that have a generated painting
        formula = f"AND({{Citizen}}='{artist_username}', {{Type}}='work_on_art', FIND('Generated Painting:', {{Notes}}))"
        records = activities_table.all(
            formula=formula,
            fields=["Notes", "CreatedAt"],
            sort=["-CreatedAt"], # Corrected sort format
            max_records=limit 
        )

        if not records:
            log.info(f"No previous paintings found for {artist_username}.")
            return []

        for record in records:
            notes = record.get('fields', {}).get('Notes', '')
            url_match = re.search(r"Generated Painting: (https?://[^\s]+)", notes)
            if url_match:
                image_url = url_match.group(1)
                log.info(f"  Found painting URL: {image_url}")
                try:
                    response = requests.get(image_url, timeout=20)
                    response.raise_for_status()
                    image_data = response.content
                    
                    content_type = response.headers.get('Content-Type', 'image/jpeg').lower()
                    if 'image/png' in content_type:
                        mime_type = 'image/png'
                    elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
                        mime_type = 'image/jpeg'
                    else: # Fallback or skip if unknown
                        log.warning(f"    Unknown content type '{content_type}' for image {image_url}. Skipping.")
                        continue
                        
                    encoded_string = base64.b64encode(image_data).decode('utf-8')
                    data_uri = f"data:{mime_type};base64,{encoded_string}"
                    encoded_images.append(data_uri)
                    log.info(f"    Successfully fetched and encoded image from {image_url} ({len(data_uri)} chars).")
                except requests.RequestException as e:
                    log.error(f"    Error fetching image from {image_url}: {e}")
                except Exception as e:
                    log.error(f"    Error processing image from {image_url}: {e}")
        
        log.info(f"Fetched and encoded {len(encoded_images)} images for {artist_username}.")
        return encoded_images

    except Exception as e:
        log.error(f"Error fetching latest paintings for {artist_username}: {e}")
        return []


def _call_kinos_build_async(
    kinos_build_url: str,
    kinos_payload: Dict[str, Any],
    tables: Dict[str, Any], # For updating notes
    activity_id_airtable: str, # Airtable record ID of the activity
    activity_guid_log: str, # For logging
    original_activity_notes: str,
    citizen_username_log: str,
    citizen_specialty: Optional[str], # Added citizen_specialty
    api_base_url_for_upload: str # Added for painter image upload
):
    """
    Makes the KinOS /build API call and updates activity notes.
    For Painters, it handles JSON response to generate and upload an image.
    This function is intended to be run in a separate thread.
    """
    log.info(f"  [Thread: {threading.get_ident()}] Calling KinOS /build for {citizen_username_log} (Specialty: {citizen_specialty}) at {kinos_build_url}")
    try:
        kinos_response_req = requests.post(kinos_build_url, json=kinos_payload, timeout=180) # Increased timeout further
        kinos_response_req.raise_for_status()
        
        kinos_response_data = kinos_response_req.json()
        kinos_text_response = kinos_response_data.get('response', "No textual response from KinOS.")
        log.info(f"  [Thread: {threading.get_ident()}] KinOS /build response for {citizen_username_log}: Status: {kinos_response_data.get('status')}, Raw Response: {kinos_text_response[:300]}...")
        
        new_notes = f"{original_activity_notes}\nKinOS Art Session: {kinos_text_response}".strip()

        if kinos_response_data.get('status') == 'completed':
            if citizen_specialty == "Painter":
                log.info(f"  [Thread: {threading.get_ident()}] {citizen_username_log} is a Painter. Attempting to parse KinOS JSON for image generation.")
                try:
                    # Extract JSON block from the potentially larger kinos_text_response
                    json_match = re.search(r'(\{[\s\S]*\})', kinos_text_response)
                    if not json_match:
                        log.warning(f"  [Thread: {threading.get_ident()}] No JSON block found in KinOS response for Painter {citizen_username_log}. Raw: {kinos_text_response}")
                        raise json.JSONDecodeError("No JSON block found", kinos_text_response, 0)
                    
                    json_to_parse = json_match.group(1)
                    log.debug(f"  [Thread: {threading.get_ident()}] Extracted JSON for parsing: {json_to_parse[:200]}...")
                    painter_json_data = json.loads(json_to_parse)
                    
                    ideogram_prompt = painter_json_data.get("ideogram_prompt")
                    artwork_name = painter_json_data.get("artwork_name")
                    aspect_ratio = painter_json_data.get("aspect_ratio")
                    magic_prompt = painter_json_data.get("magic_prompt", "OFF") # Default to OFF
                    negative_prompt = painter_json_data.get("negative_prompt") # Can be null
                    style_type = painter_json_data.get("style_type", "REALISTIC") # Default to REALISTIC

                    if all([ideogram_prompt, artwork_name, aspect_ratio]):
                        log.info(f"  [Thread: {threading.get_ident()}] Successfully parsed painter JSON. Generating image for '{artwork_name}'.")
                        painting_url = _generate_and_upload_painting_for_artist(
                            ideogram_prompt=ideogram_prompt,
                            artwork_name=artwork_name,
                            aspect_ratio=aspect_ratio,
                            magic_prompt_setting=magic_prompt,
                            negative_prompt_text=negative_prompt,
                            style_type_setting=style_type,
                            artist_username=citizen_username_log,
                            api_base_url_for_upload=api_base_url_for_upload
                        )
                        if painting_url:
                            new_notes += f"\nGenerated Painting: {painting_url}"
                            log.info(f"  [Thread: {threading.get_ident()}] Painting generated and uploaded for {citizen_username_log}: {painting_url}")
                        else:
                            new_notes += "\nFailed to generate or upload painting."
                            log.warning(f"  [Thread: {threading.get_ident()}] Failed to generate/upload painting for {citizen_username_log}.")
                    else:
                        new_notes += "\nKinOS response was JSON, but missing required fields for painting generation."
                        log.warning(f"  [Thread: {threading.get_ident()}] Painter JSON response for {citizen_username_log} missing required fields. Raw: {kinos_text_response}")
                except json.JSONDecodeError:
                    new_notes += "\nKinOS response for Painter was not valid JSON for image generation."
                    log.warning(f"  [Thread: {threading.get_ident()}] KinOS response for Painter {citizen_username_log} was not valid JSON. Raw: {kinos_text_response}")
            
            # Update notes for both painters (with image link or error) and non-painters
            try:
                tables['activities'].update(activity_id_airtable, {'Notes': new_notes})
                log.info(f"  [Thread: {threading.get_ident()}] Updated activity notes for {activity_guid_log}.")
            except Exception as e_airtable_update:
                log.error(f"  [Thread: {threading.get_ident()}] Error updating Airtable notes for activity {activity_guid_log}: {e_airtable_update}")
        else:
            log.warning(f"  [Thread: {threading.get_ident()}] KinOS /build did not complete successfully for {citizen_username_log}. Status: {kinos_response_data.get('status')}")
            # Still try to update notes with whatever response was received
            try:
                tables['activities'].update(activity_id_airtable, {'Notes': new_notes})
            except Exception: 
                pass # Avoid error in error

    except requests.exceptions.RequestException as e_kinos:
        log.error(f"  [Thread: {threading.get_ident()}] Error calling KinOS /build for {citizen_username_log}: {e_kinos}")
    except json.JSONDecodeError as e_json_kinos:
        kinos_response_text_preview = kinos_response_req.text[:200] if 'kinos_response_req' in locals() and hasattr(kinos_response_req, 'text') else 'N/A'
        log.error(f"  [Thread: {threading.get_ident()}] Error decoding KinOS /build JSON response for {citizen_username_log}: {e_json_kinos}. Response text: {kinos_response_text_preview}")
    except Exception as e_thread:
        log.error(f"  [Thread: {threading.get_ident()}] Unexpected error in KinOS call thread for {citizen_username_log}: {e_thread}")


def process_work_on_art_fn(
    tables: Dict[str, Any], 
    activity_record: Dict[str, Any],
    building_type_defs: Dict[str, Any],
    resource_defs: Dict[str, Any],
    api_base_url_param: Optional[str] = None
) -> bool:
    """
    Processes a 'work_on_art' activity.
    For Painters, it requests JSON from KinOS to generate an image.
    This involves calling the KinOS /build endpoint asynchronously to simulate the artist working on their art.
    """
    activity_id_airtable = activity_record['id'] # Airtable record ID
    activity_guid = activity_record['fields'].get('ActivityId', activity_id_airtable)
    citizen_username = activity_record['fields'].get('Citizen')
    location_id = activity_record['fields'].get('ToBuilding') # Where art is worked on
    api_base_url = api_base_url_param if api_base_url_param else os.getenv("API_BASE_URL", DEFAULT_FASTAPI_URL)
    original_notes = activity_record['fields'].get('Notes', '')

    log.info(f"{LogColors.PROCESS}Processing 'work_on_art' activity {activity_guid} for citizen {citizen_username} at {location_id} using API base: {api_base_url}.{LogColors.ENDC}")

    citizen_specialty: Optional[str] = None
    try:
        # Fetch citizen record to get specialty
        citizen_airtable_record = tables['citizens'].first(formula=f"{{Username}}='{citizen_username}'")
        if citizen_airtable_record:
            citizen_specialty = citizen_airtable_record['fields'].get('Specialty')
            log.info(f"  Citizen {citizen_username} specialty: {citizen_specialty}")
        else:
            log.warning(f"  Could not find citizen record for {citizen_username} to determine specialty.")

        # 1. Fetch citizen's ledger for KinOS addSystem
        ledger_url = f"{api_base_url}/api/get-ledger?citizenUsername={citizen_username}&format=json" # Request JSON format
        ledger_json_str = None
        try:
            ledger_response = requests.get(ledger_url, timeout=15)
            if ledger_response.ok:
                ledger_data = ledger_response.json()
                if ledger_data.get("success"):
                    ledger_json_str = json.dumps(ledger_data.get("data"))
                    log.info(f"  Successfully fetched ledger for {citizen_username}.")
                else:
                    log.warning(f"  Failed to fetch ledger for {citizen_username}: {ledger_data.get('error')}")
            else:
                log.warning(f"  HTTP error fetching ledger for {citizen_username}: {ledger_response.status_code}")
        except requests.exceptions.RequestException as e_pkg:
            log.error(f"  Error fetching ledger for {citizen_username}: {e_pkg}")
        except json.JSONDecodeError as e_json_pkg:
            log.error(f"  Error decoding ledger JSON for {citizen_username}: {e_json_pkg}")


        # 2. Construct KinOS /build request
        kinos_build_url = f"{KINOS_API_URL}/v2/blueprints/{KINOS_BLUEPRINT}/kins/{citizen_username}/build"
        
        kinos_message: str
        latest_paintings_data_uris: List[str] = []

        if citizen_specialty == "Painter":
            log.info(f"  {citizen_username} is a Painter. Fetching latest paintings and using specialized KinOS prompt for JSON output.")
            latest_paintings_data_uris = _fetch_and_encode_latest_paintings(tables, citizen_username, limit=3)
            
            image_input_message = ""
            if latest_paintings_data_uris:
                image_input_message = "You have been provided with up to three of your most recent paintings as visual input (in the 'images' field). You can use these as inspiration, reference, or to continue a series. "
            
            kinos_message = (
                "You are an Artista (Painter) in Venice, using a digital system (Aider, via KinOS) to manage your creative projects. It's time to dedicate an hour to your artistic endeavors, specifically focusing on planning and conceptualizing a new painting.\n\n"
                f"{image_input_message}Use your current situation, recent events, inspirations, and available resources (detailed in the `addSystem` data) to guide your work. "
                "Your goal is to define the concept for a new painting.\n\n"
                "You MUST return your response as a single, valid JSON object. Do not include any text before or after the JSON object. The JSON object must have the following structure:\n"
                "```json\n"
                "{\n"
                "  \"artwork_name\": \"string (A concise, evocative name for your painting, e.g., 'Sunset over Rialto', 'Doge's Procession', 'Merchant's Anxiety')\",\n"
                "  \"ideogram_prompt\": \"string (A detailed prompt for an image generation AI like Ideogram to create this painting. Describe the scene, subjects, style, colors, mood, and composition. Be specific and creative.)\",\n"
                "  \"aspect_ratio\": \"string (Choose one: '1x1', '16x9', '9x16', '4x3', '3x4', '3x2', '2x3', '10x16', '16x10', '4x5', '5x4', '1x2', '2x1', '1x3', '3x1')\",\n"
                "  \"magic_prompt\": \"OFF\",\n"
                "  \"negative_prompt\": \"string or null (Describe elements to avoid, e.g., 'modern elements, text, blurry')\",\n"
                "  \"style_type\": \"REALISTIC\"\n"
                "}\n"
                "```\n"
                "Ensure the `ideogram_prompt` is rich and descriptive, suitable for generating a high-quality Renaissance Venetian painting. The `artwork_name` should be unique and memorable."
            )
        else:
            kinos_message = (
                "You are an Artista in Venice, using a digital system (Aider, via KinOS) to manage your creative projects. It's time to dedicate an hour to your artistic endeavors. "
                "You have complete autonomy to decide what to work on. This system allows you to **create new files, edit existing ones, and organize your work in directories.**\n\n"
                "All your project files MUST be managed within the `AI-memories/art/` directory. "
                "Use your current situation, recent events, inspirations, and available resources (detailed in the `addSystem` data which includes your full citizen profile, properties, contracts, relationships, problems, etc.) "
                "to guide your work. After your session, briefly describe what file operations you performed and the creative progress you made."
            )
        
        kinos_payload: Dict[str, Any] = {
            "message": kinos_message,
            "model": "gemini-1.5-pro-latest" # Using a capable model for JSON generation if painter
        }
        if ledger_json_str:
            kinos_payload["addSystem"] = ledger_json_str
        
        if latest_paintings_data_uris:
            kinos_payload["images"] = latest_paintings_data_uris
            log.info(f"  Added {len(latest_paintings_data_uris)} previous paintings to KinOS payload for {citizen_username}.")

        # 3. Start KinOS call in a new thread
        log.info(f"  Initiating asynchronous KinOS /build call for {citizen_username} to {kinos_build_url}")
        
        kinos_thread = threading.Thread(
            target=_call_kinos_build_async,
            args=(
                kinos_build_url, 
                kinos_payload, 
                tables, 
                activity_id_airtable, 
                activity_guid, 
                original_notes, 
                citizen_username,
                citizen_specialty, # Pass specialty
                api_base_url # Pass api_base_url for potential uploads
            )
        )
        kinos_thread.start()
        
        log.info(f"  KinOS /build call for {citizen_username} (Specialty: {citizen_specialty}) started in background thread {kinos_thread.ident}.")
        # The main function now returns True, assuming the initiation of the KinOS call is the "processing".
        # The actual outcome of KinOS call happens in the thread.

    except Exception as e:
        log.error(f"{LogColors.FAIL}Error during 'work_on_art' processing setup for {activity_guid}: {e}{LogColors.ENDC}")
        import traceback
        log.error(traceback.format_exc())
        return False # Failure in setting up the async call

    log.info(f"{LogColors.SUCCESS}Successfully initiated asynchronous processing for 'work_on_art' activity {activity_guid}.{LogColors.ENDC}")
    return True

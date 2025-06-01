#!/usr/bin/env python3
"""
Calculate relevancies for vacant buildings as opportunities for citizens.

This script identifies vacant business buildings and creates relevancy records
for citizens who might benefit from operating them, based on their social class,
financial status, and proximity to the vacant building.
"""

import os
import sys
import logging
import json
import math
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pyairtable import Table
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("calculate_vacant_building_relevancies")

# Load environment variables
load_dotenv()

# Airtable configuration
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
BUILDINGS_TABLE_NAME = "BUILDINGS"
CITIZENS_TABLE_NAME = "CITIZENS"
RELEVANCIES_TABLE_NAME = "RELEVANCIES"
NOTIFICATIONS_TABLE_NAME = "NOTIFICATIONS"

# Constants for relevancy calculation
VACANT_BUILDING_RELEVANCY_THRESHOLD = 50  # Minimum score to create a relevancy
MAX_DISTANCE_METERS = 500  # Maximum distance to consider for proximity scoring
DISTANCE_WEIGHT = 0.4  # Weight for distance factor in scoring
FINANCIAL_WEIGHT = 0.3  # Weight for financial capability factor
SOCIAL_CLASS_WEIGHT = 0.3  # Weight for social class appropriateness

# Social class suitability mapping for different building types
# Higher value means more suitable (0-10 scale)
SOCIAL_CLASS_BUILDING_SUITABILITY = {
    "Nobili": {
        "bank": 10, "broker_s_office": 9, "mint": 8, "customs_house": 8,
        "large_warehouse": 7, "weighing_station": 7, "merceria": 6,
        "apothecary": 6, "jeweler": 5, "printing_press": 5
    },
    "Cittadini": {
        "merceria": 10, "apothecary": 9, "jeweler": 9, "printing_press": 8,
        "large_warehouse": 8, "weighing_station": 8, "small_warehouse": 7,
        "tailor_shop": 7, "glassblower": 7, "carpenter_workshop": 6,
        "blacksmith": 6, "market_stall": 5, "tavern": 5, "inn": 5
    },
    "Popolani": {
        "market_stall": 10, "tavern": 9, "inn": 9, "small_warehouse": 8,
        "tailor_shop": 8, "glassblower": 7, "carpenter_workshop": 7,
        "blacksmith": 7, "bakery": 6, "butcher": 6, "fishmonger": 6
    },
    "Facchini": {
        "market_stall": 8, "tavern": 7, "bakery": 6, "butcher": 6,
        "fishmonger": 6, "porter_guild_hall": 10
    },
    "Forestieri": {
        "merchant_galley": 10, "large_warehouse": 8, "weighing_station": 7,
        "small_warehouse": 6, "market_stall": 5
    }
}

def initialize_airtable_table(table_name: str) -> Optional[Table]:
    """Initialize Airtable connection for a specific table."""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        log.error(f"Missing Airtable credentials for {table_name}. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID.")
        return None
    
    try:
        return Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)
    except Exception as e:
        log.error(f"Failed to initialize Airtable table {table_name}: {e}")
        return None

def create_admin_notification(title: str, message: str) -> bool:
    """Create an admin notification in Airtable."""
    notifications_table = initialize_airtable_table(NOTIFICATIONS_TABLE_NAME)
    if not notifications_table:
        log.error("Notifications table not initialized. Cannot create admin notification.")
        return False
    
    try:
        notifications_table.create({
            'Content': title,
            'Details': message,
            'Type': 'admin',
            'Status': 'unread',
            'CreatedAt': datetime.now().isoformat(),
            'Citizen': 'ConsiglioDeiDieci'  # Or a relevant system user
        })
        log.info(f"Admin notification created: {title}")
        return True
    except Exception as e:
        log.error(f"Failed to create admin notification: {e}")
        return False

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in meters."""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # Radius of Earth in meters
    return c * r

def parse_position(position_str: Optional[str]) -> Optional[Dict[str, float]]:
    """Parse position string from Airtable into lat/lng coordinates."""
    if not position_str:
        return None
    
    try:
        # Handle JSON string format
        position_data = json.loads(position_str)
        return {
            "lat": float(position_data.get("lat")),
            "lng": float(position_data.get("lng"))
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        # Try to extract coordinates from building_lat_lng format
        if isinstance(position_str, str) and position_str.startswith("building_"):
            parts = position_str.replace("building_", "").split("_")
            if len(parts) >= 2:
                try:
                    return {
                        "lat": float(parts[0]),
                        "lng": float(parts[1])
                    }
                except (ValueError, IndexError):
                    pass
    
    return None

def calculate_financial_capability_score(citizen_ducats: float, building_type: str) -> float:
    """Calculate a score (0-10) for a citizen's financial capability to operate a building."""
    # Define base operation costs for different building types
    building_operation_costs = {
        "market_stall": 1000,
        "bakery": 2000,
        "butcher": 2000,
        "fishmonger": 2000,
        "tavern": 3000,
        "inn": 5000,
        "small_warehouse": 3000,
        "tailor_shop": 4000,
        "carpenter_workshop": 4000,
        "blacksmith": 5000,
        "glassblower": 6000,
        "apothecary": 7000,
        "jeweler": 8000,
        "printing_press": 10000,
        "large_warehouse": 8000,
        "weighing_station": 6000,
        "merceria": 7000,
        "bank": 15000,
        "broker_s_office": 10000,
        "mint": 20000,
        "customs_house": 15000,
        "porter_guild_hall": 5000,
        "merchant_galley": 12000
    }
    
    # Default cost if building type not in the dictionary
    default_cost = 5000
    operation_cost = building_operation_costs.get(building_type, default_cost)
    
    # Calculate score based on how many months of operation the citizen can afford
    # Assuming a citizen should ideally have 3 months of operating costs
    months_affordable = citizen_ducats / operation_cost
    
    if months_affordable >= 3:
        return 10  # Can afford 3+ months of operation
    elif months_affordable >= 2:
        return 8
    elif months_affordable >= 1:
        return 6
    elif months_affordable >= 0.5:
        return 4
    elif months_affordable >= 0.25:
        return 2
    else:
        return 0  # Cannot afford even 1/4 month of operation

def calculate_social_class_suitability(social_class: str, building_type: str) -> float:
    """Calculate how suitable a building type is for a citizen's social class (0-10)."""
    if social_class not in SOCIAL_CLASS_BUILDING_SUITABILITY:
        return 0
    
    return SOCIAL_CLASS_BUILDING_SUITABILITY[social_class].get(building_type, 0)

def calculate_vacant_building_relevancy(building: Dict[str, Any], citizen: Dict[str, Any]) -> float:
    """Calculate relevancy score for a vacant building opportunity."""
    # Extract building data
    building_type = building.get("Type")
    building_position = parse_position(building.get("Position"))
    
    # Extract citizen data
    citizen_social_class = citizen.get("SocialClass")
    citizen_ducats = float(citizen.get("Ducats", 0))
    citizen_position = parse_position(citizen.get("Position"))
    
    # Skip if missing critical data
    if not building_position or not citizen_position or not building_type or not citizen_social_class:
        return 0
    
    # Calculate distance score (closer is better)
    distance = haversine_distance(
        building_position["lat"], building_position["lng"],
        citizen_position["lat"], citizen_position["lng"]
    )
    
    # Skip if too far away
    if distance > MAX_DISTANCE_METERS:
        return 0
    
    distance_score = 10 * (1 - (distance / MAX_DISTANCE_METERS))
    
    # Calculate financial capability score
    financial_score = calculate_financial_capability_score(citizen_ducats, building_type)
    
    # Calculate social class suitability score
    social_class_score = calculate_social_class_suitability(citizen_social_class, building_type)
    
    # Calculate weighted total score (0-100 scale)
    total_score = (
        (distance_score * DISTANCE_WEIGHT) +
        (financial_score * FINANCIAL_WEIGHT) +
        (social_class_score * SOCIAL_CLASS_WEIGHT)
    ) * 10
    
    return round(total_score, 2)

def get_vacant_buildings() -> List[Dict[str, Any]]:
    """Retrieve vacant business buildings from Airtable."""
    buildings_table = initialize_airtable_table(BUILDINGS_TABLE_NAME)
    if not buildings_table:
        log.error("Buildings table not initialized. Cannot fetch vacant buildings.")
        return []
    
    try:
        # Query for buildings that are:
        # 1. Constructed
        # 2. Have Category = 'business'
        # 3. Have no Occupant (vacant)
        vacant_buildings = buildings_table.all(
            formula="AND({IsConstructed}=1, {Category}='business', {Occupant}='')"
        )
        
        log.info(f"Found {len(vacant_buildings)} vacant business buildings")
        return vacant_buildings
    except Exception as e:
        log.error(f"Error fetching vacant buildings: {e}")
        return []

def get_citizens() -> List[Dict[str, Any]]:
    """Retrieve all active citizens from Airtable."""
    citizens_table = initialize_airtable_table(CITIZENS_TABLE_NAME)
    if not citizens_table:
        log.error("Citizens table not initialized. Cannot fetch citizens.")
        return []
    
    try:
        # Query for citizens that are:
        # 1. Currently in Venice
        citizens = citizens_table.all(
            formula="{InVenice}=1"
        )
        
        log.info(f"Found {len(citizens)} active citizens in Venice")
        return citizens
    except Exception as e:
        log.error(f"Error fetching citizens: {e}")
        return []

def create_or_update_relevancy(building: Dict[str, Any], citizen: Dict[str, Any], score: float) -> bool:
    """Create or update a relevancy record for a vacant building opportunity."""
    relevancies_table = initialize_airtable_table(RELEVANCIES_TABLE_NAME)
    if not relevancies_table:
        log.error("Relevancies table not initialized. Cannot create/update relevancy.")
        return False
    
    try:
        # Check if a relevancy already exists for this building and citizen
        existing_relevancies = relevancies_table.all(
            formula=f"AND({{Asset}}='{building['id']}', {{RelevantToCitizen}}='{citizen['Username']}', {{Category}}='opportunity', {{Type}}='vacant_business')"
        )
        
        building_name = building.get("fields", {}).get("Name", f"{building.get('fields', {}).get('Type', 'Building')} at {building.get('fields', {}).get('Position', 'unknown location')}")
        building_type = building.get("fields", {}).get("Type", "business")
        
        relevancy_data = {
            "Asset": building["id"],
            "AssetType": "building",
            "Category": "opportunity",
            "Type": "vacant_business",
            "TargetCitizen": citizen["Username"],
            "RelevantToCitizen": citizen["Username"],
            "Score": score,
            "TimeHorizon": "short_term",
            "Title": f"Vacant {building_type} available for operation",
            "Description": f"A vacant {building_type} ({building_name}) is available for operation. This could be a good opportunity to expand your business interests in Venice.",
            "Notes": json.dumps({
                "buildingType": building_type,
                "buildingId": building["id"],
                "buildingName": building_name,
                "leasePrice": building.get("fields", {}).get("LeasePrice"),
                "calculationFactors": {
                    "distance": DISTANCE_WEIGHT * 10,
                    "financial": FINANCIAL_WEIGHT * 10,
                    "socialClass": SOCIAL_CLASS_WEIGHT * 10
                }
            }),
            "Status": "new"
        }
        
        if existing_relevancies:
            # Update existing relevancy
            existing_relevancy = existing_relevancies[0]
            relevancies_table.update(existing_relevancy["id"], relevancy_data)
            log.info(f"Updated relevancy for {citizen['Username']} regarding {building['id']}")
        else:
            # Create new relevancy
            relevancies_table.create(relevancy_data)
            log.info(f"Created new relevancy for {citizen['Username']} regarding {building['id']}")
        
        return True
    except Exception as e:
        log.error(f"Error creating/updating relevancy: {e}")
        return False

def main() -> bool:
    """Main function to calculate vacant building relevancies."""
    start_time = time.time()
    log.info("Starting vacant building relevancy calculation...")
    
    # Get vacant buildings
    vacant_buildings = get_vacant_buildings()
    if not vacant_buildings:
        log.info("No vacant business buildings found. Nothing to do.")
        create_admin_notification(
            "Vacant Building Relevancy Calculation Complete",
            "No vacant business buildings found. No relevancies created."
        )
        return True
    
    # Get citizens
    citizens = get_citizens()
    if not citizens:
        log.info("No active citizens found in Venice. Nothing to do.")
        create_admin_notification(
            "Vacant Building Relevancy Calculation Complete",
            "No active citizens found in Venice. No relevancies created."
        )
        return True
    
    # Calculate relevancies for each vacant building and citizen combination
    relevancy_count = 0
    for building in vacant_buildings:
        for citizen in citizens:
            score = calculate_vacant_building_relevancy(building["fields"], citizen["fields"])
            
            # Only create relevancy if score is above threshold
            if score >= VACANT_BUILDING_RELEVANCY_THRESHOLD:
                if create_or_update_relevancy(building, citizen["fields"], score):
                    relevancy_count += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    log.info(f"Created or updated {relevancy_count} vacant building relevancies in {duration:.2f} seconds")
    
    # Create admin notification with results
    create_admin_notification(
        "Vacant Building Relevancy Calculation Complete",
        f"Created or updated {relevancy_count} vacant building relevancies.\n\n"
        f"Processed {len(vacant_buildings)} vacant buildings for {len(citizens)} citizens.\n"
        f"Calculation completed in {duration:.2f} seconds."
    )
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

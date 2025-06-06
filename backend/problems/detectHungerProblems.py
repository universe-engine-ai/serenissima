#!/usr/bin/env python3
"""
Detect hunger problems for citizens.

This script:
1. Identifies citizens who haven't eaten in over 24 hours
2. Creates appropriate hunger problem records
3. Creates employee impact problems for employers with hungry workers
"""

import os
import sys
import logging
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pyairtable import Api, Table
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("detect_hunger_problems")

# Load environment variables
load_dotenv()

def initialize_airtable():
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID environment variables.")
        sys.exit(1)
    
    try:
        # Return a dictionary of table objects using pyairtable
        tables_to_init = {
            'notifications': Table(api_key, base_id, 'NOTIFICATIONS'),
            'citizens': Table(api_key, base_id, 'CITIZENS'),
            'problems': Table(api_key, base_id, 'PROBLEMS'),
            'buildings': Table(api_key, base_id, 'BUILDINGS')
        }
        log.info(f"Initialized Airtable tables: {list(tables_to_init.keys())}")
        return tables_to_init
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)

def create_admin_notification(tables, title: str, message: str) -> bool:
    """Create an admin notification in Airtable."""
    try:
        tables['notifications'].create({
            'Content': title,
            'Details': message,
            'Type': 'admin',
            'Status': 'unread',
            'CreatedAt': datetime.now().isoformat(),
            'Citizen': 'ConsiglioDeiDieci'
        })
        return True
    except Exception as e:
        log.error(f"Failed to create admin notification: {e}")
        return False

def detect_hunger_problems() -> Dict:
    """
    Detect citizens who haven't eaten in over 24 hours and create hunger problems.
    
    Returns:
        Dict: Summary of detected hunger problems
    """
    log.info("--- Detecting Hungry Citizens ---")
    
    # Initialize Airtable tables
    tables = initialize_airtable()
    if not tables:
        log.error("Failed to initialize Airtable tables. Aborting hunger problem detection.")
        return {"success": False, "error": "Failed to initialize Airtable tables", "problemCount": 0, "savedCount": 0, "problems": {}}
    
    # Get current time
    current_time = datetime.now()
    
    # Track statistics and problems for reporting
    stats = {
        "total_citizens_checked": 0,
        "hungry_citizens_found": 0,
        "employee_impacts_found": 0
    }
    problems = {}
    
    try:
        # Get all citizens
        all_citizens = tables['citizens'].all()
        stats["total_citizens_checked"] = len(all_citizens)
        log.info(f"Checking {stats['total_citizens_checked']} citizens for hunger problems")
        
        for citizen in all_citizens:
            try:
                citizen_fields = citizen['fields']
                citizen_id = citizen_fields.get('Username', citizen['id'])
                
                # Skip citizens not in Venice
                if citizen_fields.get('InVenice') is False:
                    continue
                
                # Check when the citizen last ate
                ate_at_str = citizen_fields.get('AteAt')
                if not ate_at_str:
                    # If no AteAt field, assume they haven't eaten in a while
                    last_ate = current_time - timedelta(days=2)  # Default to 2 days ago
                else:
                    try:
                        last_ate = datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        # If date parsing fails, default to 2 days ago
                        last_ate = current_time - timedelta(days=2)
                
                # Calculate time since last meal
                time_since_last_meal = current_time - last_ate
                
                # If more than 24 hours since last meal, create a hunger problem
                if time_since_last_meal.total_seconds() > 24 * 60 * 60:
                    stats["hungry_citizens_found"] += 1
                    
                    # Check if a hunger problem already exists for this citizen
                    existing_problems = tables['problems'].all(
                        formula=f"AND({{Citizen}}='{citizen_id}', {{Type}}='hungry_citizen', {{Status}}='active')"
                    )
                    
                    if existing_problems:
                        log.info(f"Hunger problem already exists for citizen {citizen_id}")
                        continue
                    
                    # Get citizen details for the problem description
                    first_name = citizen_fields.get('FirstName', 'Unknown')
                    last_name = citizen_fields.get('LastName', 'Unknown')
                    full_name = f"{first_name} {last_name}"
                    
                    # Get position for the problem location
                    position_str = citizen_fields.get('Position', '{"lat":45.4375,"lng":12.3358}')  # Default to center of Venice
                    try:
                        position = json.loads(position_str) if isinstance(position_str, str) else position_str
                    except json.JSONDecodeError:
                        position = {"lat": 45.4375, "lng": 12.3358}  # Default to center of Venice
                    
                    # Create the problem
                    problem_id = f"hungry_{citizen_id}_{int(time.time() * 1000)}"
                    
                    problem_data = {
                        "ProblemId": problem_id,
                        "Citizen": citizen_id,
                        "Asset": citizen_id,
                        "AssetType": "citizen",
                        "Severity": "medium",
                        "Status": "active",
                        "Location": f"{first_name}'s last known area",
                        "Position": json.dumps(position),
                        "Type": "hungry_citizen",
                        "Title": "Hungry Citizen",
                        "Description": f"**{full_name}** has not eaten in over 24 hours and is now hungry. This can affect their well-being and ability to perform tasks effectively.\n\n### Impact\n- Reduced energy and focus.\n- If employed, work productivity may be reduced by up to 50%.\n- Prolonged hunger can lead to more severe health issues (if implemented).",
                        "Solutions": "### Recommended Solutions\n- Ensure the citizen consumes food. This might involve visiting a tavern, purchasing food from a market, or using owned food resources.\n- Check if the citizen has sufficient Ducats to afford food.\n- Review game mechanics related to food consumption and ensure the 'AteAt' (or equivalent) field is updated correctly after eating.",
                        "Notes": f"Citizen {citizen_id} last ate at {ate_at_str}. Current time: {current_time.isoformat()}"
                    }
                    
                    # Store problem for later insertion and reporting
                    problems[problem_id] = problem_data
                    
                    # If the citizen is employed, create a problem for their employer
                    workplace_building_id = citizen_fields.get('WorkplaceBuilding')
                    if workplace_building_id:
                        # Get the building details to find the employer
                        buildings = tables['buildings'].all(formula=f"{{BuildingId}}='{workplace_building_id}'")
                        if buildings and len(buildings) > 0:
                            building = buildings[0]['fields']
                            employer = building.get('RunBy')
                            
                            if employer and employer != citizen_id:  # Don't create self-employment problems
                                # Check if this specific employee impact problem already exists
                                existing_impact_problems = tables['problems'].all(
                                    formula=f"AND({{Citizen}}='{employer}', {{Asset}}='{citizen_id}', {{Type}}='hungry_employee_impact', {{Status}}='active')"
                                )
                                
                                if not existing_impact_problems:
                                    stats["employee_impacts_found"] += 1
                                    building_name = building.get('Name', building.get('Type', 'Unknown Building'))
                                    
                                    impact_problem_id = f"hungry_employee_impact_{employer}_{citizen_id}_{int(time.time() * 1000)}"
                                    impact_problem_data = {
                                        "ProblemId": impact_problem_id,
                                        "Citizen": employer,
                                        "Asset": citizen_id,
                                        "AssetType": "employee_performance",
                                        "Severity": "low",
                                        "Status": "active",
                                        "Location": building_name,
                                        "Position": json.dumps(position),
                                        "Type": "hungry_employee_impact",
                                        "Title": "Hungry Employee Impact",
                                        "Description": f"Your employee, **{full_name}**, is currently hungry. Hunger can significantly reduce productivity (up to 50%).",
                                        "Solutions": f"Ensure **{full_name}** has the means and opportunity to eat. Consider if wages are sufficient or if working conditions impede access to food. Monitor their performance.",
                                        "Notes": f"Hungry Employee: {citizen_id} (ID: {citizen_id}), Workplace: {building_name} (ID: {workplace_building_id}). Last ate: {ate_at_str}."
                                    }
                                    
                                    # Store employee impact problem
                                    problems[impact_problem_id] = impact_problem_data
            
            except Exception as e:
                log.error(f"Error processing citizen {citizen.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Insert all problems in batch
        saved_count = 0
        if problems:
            for problem_id, problem_data in problems.items():
                try:
                    tables['problems'].create(problem_data)
                    saved_count += 1
                except Exception as e:
                    log.error(f"Error saving problem {problem_id}: {str(e)}")
        
        log.info(f"Hunger detection complete: {stats['hungry_citizens_found']} hungry citizens, {stats['employee_impacts_found']} employee impacts, {saved_count} problems saved")
        
        return {
            "success": True, 
            "problemCount": len(problems), 
            "savedCount": saved_count, 
            "problems": problems
        }
    
    except Exception as e:
        error_message = f"Error in hunger problem detection: {str(e)}"
        log.error(error_message)
        create_admin_notification(
            tables,
            "Hunger Problem Detection Error",
            error_message
        )
        return {"success": False, "error": error_message, "problemCount": 0, "savedCount": 0, "problems": {}}

if __name__ == "__main__":
    result = detect_hunger_problems()
    print(json.dumps(result, indent=2))

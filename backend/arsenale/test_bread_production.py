#!/usr/bin/env python3
"""
Test script to diagnose bread production issues in La Serenissima.
Checks:
1. Bakery buildings and their status
2. Bread recipes and requirements
3. Resource availability for bread production
4. Why production activities aren't being created
"""

import os
import sys
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from pyairtable import Table
import json
import requests

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Load environment variables
load_dotenv()

# Get Airtable credentials
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')

# Create tables
citizens_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'CITIZENS')
buildings_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'BUILDINGS')
resources_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'RESOURCES')
activities_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, 'ACTIVITIES')

# Load building type definitions from API
try:
    response = requests.get('https://serenissima.ai/api/get-building-types')
    if response.status_code == 200:
        data = response.json()
        building_type_defs = data.get('buildingTypes', {})
    else:
        print(f"Failed to load building types: {response.status_code}")
        building_type_defs = {}
except Exception as e:
    print(f"Error loading building types: {e}")
    building_type_defs = {}

# Load resource type definitions from API
resource_defs = {
    'flour': {'name': 'Flour'},
    'bread': {'name': 'Bread'},
    'fuel': {'name': 'Fuel'}
}

def check_bakeries():
    """Check all bakery buildings and their status."""
    print("\n=== CHECKING BAKERIES ===")
    
    # Find all bakery buildings
    bakeries = buildings_table.all(formula="{Type}='bakery'")
    print(f"Total bakeries found: {len(bakeries)}")
    
    for bakery in bakeries:
        fields = bakery['fields']
        print(f"\nBakery: {fields.get('Name', 'Unknown')}")
        print(f"  - CustomId: {fields.get('CustomId')}")
        print(f"  - Status: {fields.get('Status')}")
        print(f"  - Owner: {fields.get('Owner')}")
        print(f"  - Operator (RunBy): {fields.get('RunBy')}")
        print(f"  - CheckedAt: {fields.get('CheckedAt')}")
        print(f"  - Position: {fields.get('Position')}")
        
        # Check if operator is assigned
        operator = fields.get('RunBy') or fields.get('Owner')
        if operator:
            # Check operator status
            citizen = citizens_table.all(formula=f"{{Username}}='{operator}'", max_records=1)
            if citizen:
                citizen_fields = citizen[0]['fields']
                print(f"  - Operator Status:")
                print(f"    - HomeBuilding: {citizen_fields.get('HomeBuilding', 'None')}")
                print(f"    - AteAt: {citizen_fields.get('AteAt', 'Never')}")
                print(f"    - Position: {citizen_fields.get('Position')}")
                print(f"    - IsAI: {citizen_fields.get('IsAI', False)}")
        
        # Check resources in bakery
        building_id = fields.get('CustomId')
        if building_id:
            resources = resources_table.all(formula=f"AND({{Asset}}='{building_id}', {{AssetType}}='building')")
            if resources:
                print(f"  - Resources in bakery:")
                for res in resources:
                    res_fields = res['fields']
                    print(f"    - {res_fields.get('Type')}: {res_fields.get('Count', 0)} (Owner: {res_fields.get('Owner')})")
            else:
                print(f"  - No resources in bakery")

def check_bread_recipe():
    """Check the bread recipe requirements."""
    print("\n=== CHECKING BREAD RECIPE ===")
    
    bakery_def = building_type_defs.get('bakery', {})
    recipes = bakery_def.get('Recipes', [])
    
    if not recipes:
        print("ERROR: No recipes found for bakery!")
        return None
    
    # Find bread recipe
    bread_recipe = None
    for recipe in recipes:
        if 'bread' in recipe.get('outputs', {}):
            bread_recipe = recipe
            break
    
    if bread_recipe:
        print(f"Bread recipe found:")
        print(f"  - Inputs: {bread_recipe.get('inputs', {})}")
        print(f"  - Outputs: {bread_recipe.get('outputs', {})}")
        print(f"  - Craft time: {bread_recipe.get('craftMinutes', 0)} minutes")
        return bread_recipe
    else:
        print("ERROR: No bread recipe found in bakery recipes!")
        return None

def check_flour_availability():
    """Check flour availability across the city."""
    print("\n=== CHECKING FLOUR AVAILABILITY ===")
    
    # Get all flour resources
    flour_resources = resources_table.all(formula="{Type}='flour'")
    print(f"Total flour resources: {len(flour_resources)}")
    
    total_flour = 0
    flour_by_location = {}
    
    for flour in flour_resources:
        fields = flour['fields']
        count = fields.get('Count', 0)
        total_flour += count
        
        location = fields.get('Asset', 'Unknown')
        if location not in flour_by_location:
            flour_by_location[location] = 0
        flour_by_location[location] += count
    
    print(f"Total flour in city: {total_flour}")
    print(f"Flour locations: {len(flour_by_location)}")
    
    # Show top locations
    sorted_locations = sorted(flour_by_location.items(), key=lambda x: x[1], reverse=True)
    print("\nTop flour locations:")
    for location, amount in sorted_locations[:5]:
        print(f"  - {location}: {amount}")

def check_recent_production_attempts():
    """Check recent production activities for bakeries."""
    print("\n=== CHECKING RECENT PRODUCTION ATTEMPTS ===")
    
    # Get recent production activities
    recent_activities = activities_table.all(
        formula="AND({Type}='production', DATETIME_DIFF(NOW(), {CreatedAt}, 'hours') < 24)",
        max_records=100
    )
    
    print(f"Recent production activities (last 24h): {len(recent_activities)}")
    
    # Filter for bakery production
    bakery_production = []
    for activity in recent_activities:
        fields = activity['fields']
        notes = fields.get('Notes', '')
        if 'bread' in notes.lower() or 'flour' in notes.lower():
            bakery_production.append(activity)
    
    print(f"Bakery-related production activities: {len(bakery_production)}")
    
    for activity in bakery_production[:5]:
        fields = activity['fields']
        print(f"\nActivity: {fields.get('ActivityId')}")
        print(f"  - Status: {fields.get('Status')}")
        print(f"  - Citizen: {fields.get('Citizen')}")
        print(f"  - Building: {fields.get('FromBuilding')}")
        print(f"  - Notes: {fields.get('Notes', '')[:200]}")

def simulate_bread_production():
    """Simulate what would happen if we tried to create bread production."""
    print("\n=== SIMULATING BREAD PRODUCTION ===")
    
    # Find an active bakery with an operator
    bakeries = buildings_table.all(formula="AND({Type}='bakery', {Status}='active')")
    
    suitable_bakery = None
    for bakery in bakeries:
        fields = bakery['fields']
        operator = fields.get('RunBy') or fields.get('Owner')
        if operator:
            suitable_bakery = bakery
            break
    
    if not suitable_bakery:
        print("ERROR: No suitable bakery found (need active bakery with operator)")
        return
    
    bakery_fields = suitable_bakery['fields']
    bakery_id = bakery_fields.get('CustomId')
    operator = bakery_fields.get('RunBy') or bakery_fields.get('Owner')
    
    print(f"Selected bakery: {bakery_fields.get('Name')} (Operator: {operator})")
    
    # Check bread recipe
    bread_recipe = None
    bakery_def = building_type_defs.get('bakery', {})
    for recipe in bakery_def.get('Recipes', []):
        if 'bread' in recipe.get('outputs', {}):
            bread_recipe = recipe
            break
    
    if not bread_recipe:
        print("ERROR: No bread recipe found")
        return
    
    print(f"Recipe requirements: {bread_recipe.get('inputs', {})}")
    
    # Check if inputs are available
    inputs_available = True
    for resource_type, required_amount in bread_recipe.get('inputs', {}).items():
        # Check resources in bakery
        resource_formula = f"AND({{Type}}='{resource_type}', {{Asset}}='{bakery_id}', {{AssetType}}='building', {{Owner}}='{operator}')"
        resources = resources_table.all(formula=resource_formula, max_records=1)
        
        if resources:
            available = resources[0]['fields'].get('Count', 0)
            print(f"  - {resource_type}: {available}/{required_amount} {'✓' if available >= required_amount else '✗'}")
            if available < required_amount:
                inputs_available = False
        else:
            print(f"  - {resource_type}: 0/{required_amount} ✗")
            inputs_available = False
    
    if inputs_available:
        print("\n✓ All inputs available - production SHOULD work")
    else:
        print("\n✗ Missing inputs - production will FAIL")

def check_ai_citizen_activities():
    """Check if AI citizens are creating activities at their workplaces."""
    print("\n=== CHECKING AI CITIZEN ACTIVITIES ===")
    
    # Find AI citizens working at bakeries
    bakeries = buildings_table.all(formula="{Type}='bakery'")
    
    for bakery in bakeries[:3]:  # Check first 3 bakeries
        fields = bakery['fields']
        operator = fields.get('RunBy') or fields.get('Owner')
        
        if operator:
            # Check if operator is AI
            citizen = citizens_table.all(formula=f"AND({{Username}}='{operator}', {{IsAI}}=TRUE())", max_records=1)
            if citizen:
                citizen_fields = citizen[0]['fields']
                print(f"\nAI Citizen: {operator}")
                print(f"  - Workplace: {fields.get('Name')}")
                
                # Check recent activities
                recent_activities = activities_table.all(
                    formula=f"AND({{Citizen}}='{operator}', DATETIME_DIFF(NOW(), {{CreatedAt}}, 'hours') < 6)",
                    max_records=10
                )
                
                print(f"  - Recent activities (last 6h): {len(recent_activities)}")
                activity_types = {}
                for activity in recent_activities:
                    activity_type = activity['fields'].get('Type', 'unknown')
                    activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
                
                for activity_type, count in activity_types.items():
                    print(f"    - {activity_type}: {count}")

def main():
    """Run all diagnostics."""
    print("=== BREAD PRODUCTION DIAGNOSTIC ===")
    print(f"Time: {datetime.now(pytz.timezone('Europe/Rome'))}")
    
    # Run all checks
    check_bakeries()
    bread_recipe = check_bread_recipe()
    check_flour_availability()
    check_recent_production_attempts()
    simulate_bread_production()
    check_ai_citizen_activities()
    
    # Summary
    print("\n=== SUMMARY ===")
    print("Key issues identified:")
    print("1. Check if bakeries have operators assigned")
    print("2. Check if operators are creating production activities")
    print("3. Check if flour is available in bakeries")
    print("4. Check if AI citizens are running their activity creation logic")

if __name__ == "__main__":
    main()
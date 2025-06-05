#!/usr/bin/env python3
"""
Building Investment Analysis Script for Antonio Corfiote

This script:
1. Fetches available building types from the API
2. Analyzes each type based on investment criteria
3. Ranks building types by ROI and strategic value
4. Outputs a detailed report for construction planning

Usage:
python building_investment_analysis.py [--budget BUDGET] [--focus FOCUS]
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

# Set up argument parsing
parser = argparse.ArgumentParser(description="Analyze building types for investment")
parser.add_argument("--budget", type=float, default=600000, help="Maximum construction budget in ducats (default: 600000)")
parser.add_argument("--focus", type=str, default="income", choices=["income", "storage", "production", "balanced"], 
                    help="Investment focus (default: income)")
parser.add_argument("--output", type=str, default="building_investment_report.json", help="Output file for detailed report")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()

# Load environment variables
load_dotenv()

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "https://serenissima.ai")
SOCIAL_CLASS_TIER = 0  # Forestieri (will be used to filter buildings by buildTier)

# Building category weights based on focus
CATEGORY_WEIGHTS = {
    "income": {
        "storage": 1.5,      # High priority for income focus
        "workshop": 1.3,     # Good income potential
        "market": 1.4,       # Good income potential
        "residence": 0.8,    # Lower priority for income focus
        "production": 1.2,   # Moderate income potential
        "infrastructure": 0.7, # Low income potential
        "default": 1.0       # Default weight
    },
    "storage": {
        "storage": 2.0,      # Highest priority for storage focus
        "warehouse": 1.8,    # High priority for storage focus
        "workshop": 0.9,     # Lower priority for storage focus
        "market": 1.0,       # Moderate priority for storage focus
        "residence": 0.5,    # Low priority for storage focus
        "production": 0.8,   # Lower priority for storage focus
        "infrastructure": 0.6, # Low priority for storage focus
        "default": 1.0       # Default weight
    },
    "production": {
        "production": 1.8,   # Highest priority for production focus
        "workshop": 1.6,     # High priority for production focus
        "market": 1.2,       # Moderate priority for production focus
        "storage": 1.0,      # Moderate priority for production focus
        "residence": 0.5,    # Low priority for production focus
        "infrastructure": 0.7, # Low priority for production focus
        "default": 1.0       # Default weight
    },
    "balanced": {
        "storage": 1.2,      # Balanced approach
        "workshop": 1.2,     # Balanced approach
        "market": 1.2,       # Balanced approach
        "residence": 1.0,    # Balanced approach
        "production": 1.2,   # Balanced approach
        "infrastructure": 1.0, # Balanced approach
        "default": 1.0       # Default weight
    }
}

def fetch_building_types() -> List[Dict]:
    """Fetch available building types from the API."""
    try:
        url = f"{API_BASE_URL}/api/building-types"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if "success" in data and data["success"] and "buildingTypes" in data:
                building_types = data["buildingTypes"]
                print(f"Found {len(building_types)} building types")
                return building_types
            else:
                print(f"Unexpected API response format: {data}")
                return []
        else:
            print(f"Error fetching building types: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception fetching building types: {str(e)}")
        return []

def analyze_building_type(building_type: Dict) -> Dict:
    """Analyze a building type and calculate its investment score."""
    # Extract basic information
    type_id = building_type.get("type", "unknown")
    name = building_type.get("name", type_id)
    build_tier = building_type.get("buildTier", 999)  # Default to high tier if not specified
    category = building_type.get("category", "unknown")
    sub_category = building_type.get("subCategory", "unknown")
    
    # Extract construction costs
    construction_costs = building_type.get("constructionCosts", {})
    ducat_cost = construction_costs.get("ducats", 0)
    
    # Extract production information
    production_info = building_type.get("productionInformation", {})
    
    # Determine if it's a storage building
    storage_capacity = production_info.get("storageCapacity", 0)
    stores_resources = production_info.get("stores", [])
    is_storage = storage_capacity > 0 and len(stores_resources) > 0
    
    # Determine if it's a production building
    produces_resources = []
    if "Arti" in production_info:
        for recipe in production_info["Arti"]:
            if "outputs" in recipe:
                produces_resources.extend(list(recipe["outputs"].keys()))
    
    is_production = len(produces_resources) > 0
    
    # Determine if it sells resources
    sells_resources = production_info.get("sells", [])
    is_market = len(sells_resources) > 0
    
    # Determine building function category for weighting
    building_function = "default"
    if is_storage:
        building_function = "storage"
    elif is_production:
        building_function = "production"
    elif is_market:
        building_function = "market"
    elif category == "home":
        building_function = "residence"
    elif category == "infrastructure":
        building_function = "infrastructure"
    elif sub_category == "workshop":
        building_function = "workshop"
    
    # Get weight based on focus and building function
    weight = CATEGORY_WEIGHTS[args.focus].get(building_function, CATEGORY_WEIGHTS[args.focus]["default"])
    
    # Calculate base score
    base_score = 100
    
    # Adjust score based on tier (lower tier is better for accessibility)
    tier_factor = max(1, 5 - build_tier) if build_tier >= 0 else 1
    tier_score = tier_factor * 20
    
    # Adjust score based on storage capacity
    storage_score = min(storage_capacity / 10, 100) if is_storage else 0
    
    # Adjust score based on production capability
    production_score = len(produces_resources) * 15 if is_production else 0
    
    # Adjust score based on market capability
    market_score = len(sells_resources) * 10 if is_market else 0
    
    # Calculate maintenance cost if available
    maintenance_cost = production_info.get("maintenanceCost", 0)
    
    # Calculate potential income (very rough estimate)
    potential_income = 0
    if is_storage:
        # Estimate storage income based on capacity
        potential_income = storage_capacity * 0.5  # 0.5 ducats per unit of storage per day
    elif is_production:
        # Estimate production income based on number of outputs
        potential_income = len(produces_resources) * 20  # 20 ducats per resource type per day
    elif is_market:
        # Estimate market income based on number of sellable resources
        potential_income = len(sells_resources) * 15  # 15 ducats per resource type per day
    
    # Calculate ROI (annual return percentage)
    daily_profit = potential_income - maintenance_cost
    annual_profit = daily_profit * 365
    roi_percentage = (annual_profit / ducat_cost * 100) if ducat_cost > 0 else 0
    
    # Calculate final score with weighting
    function_score = storage_score + production_score + market_score
    total_score = (base_score + tier_score + function_score) * weight
    
    # Adjust score based on ROI
    roi_factor = max(0.5, min(2.0, roi_percentage / 10))  # Cap between 0.5x and 2x
    total_score *= roi_factor
    
    return {
        "type_id": type_id,
        "name": name,
        "build_tier": build_tier,
        "category": category,
        "sub_category": sub_category,
        "ducat_cost": ducat_cost,
        "maintenance_cost": maintenance_cost,
        "is_storage": is_storage,
        "storage_capacity": storage_capacity,
        "stores_resources": stores_resources,
        "is_production": is_production,
        "produces_resources": produces_resources,
        "is_market": is_market,
        "sells_resources": sells_resources,
        "estimated_daily_income": potential_income,
        "estimated_daily_profit": daily_profit,
        "estimated_annual_profit": annual_profit,
        "roi_percentage": roi_percentage,
        "score": round(total_score, 2),
        "within_budget": ducat_cost <= args.budget,
        "accessible_tier": build_tier <= SOCIAL_CLASS_TIER,
        "raw_data": building_type  # Include raw data for reference
    }

def generate_investment_strategy(analyzed_buildings: List[Dict]) -> Dict:
    """Generate a comprehensive building investment strategy."""
    # Filter by budget and accessibility
    affordable_buildings = [b for b in analyzed_buildings if b["within_budget"]]
    accessible_buildings = [b for b in affordable_buildings if b["accessible_tier"]]
    
    # Sort buildings by score (descending)
    sorted_buildings = sorted(accessible_buildings, key=lambda x: x["score"], reverse=True)
    
    # Get top recommendations (top 5)
    top_recommendations = sorted_buildings[:5]
    
    # Group buildings by function
    storage_buildings = [b for b in sorted_buildings if b["is_storage"]]
    production_buildings = [b for b in sorted_buildings if b["is_production"]]
    market_buildings = [b for b in sorted_buildings if b["is_market"]]
    
    # Sort each category by ROI
    storage_by_roi = sorted(storage_buildings, key=lambda x: x["roi_percentage"], reverse=True)
    production_by_roi = sorted(production_buildings, key=lambda x: x["roi_percentage"], reverse=True)
    market_by_roi = sorted(market_buildings, key=lambda x: x["roi_percentage"], reverse=True)
    
    return {
        "analysis_date": datetime.now().isoformat(),
        "focus": args.focus,
        "budget": args.budget,
        "overview": {
            "total_building_types": len(analyzed_buildings),
            "affordable_buildings": len(affordable_buildings),
            "accessible_buildings": len(accessible_buildings),
            "storage_buildings": len(storage_buildings),
            "production_buildings": len(production_buildings),
            "market_buildings": len(market_buildings)
        },
        "top_recommendations": top_recommendations,
        "best_by_category": {
            "storage": storage_by_roi[:3] if storage_by_roi else [],
            "production": production_by_roi[:3] if production_by_roi else [],
            "market": market_by_roi[:3] if market_by_roi else []
        },
        "all_analyzed_buildings": sorted_buildings
    }

def main():
    """Main execution function."""
    print(f"Starting building investment analysis (Budget: {args.budget} ducats, Focus: {args.focus})")
    
    # Fetch building types
    building_types = fetch_building_types()
    if not building_types:
        print("No building types available for analysis. Exiting.")
        return
    
    # Analyze each building type
    analyzed_buildings = [analyze_building_type(bt) for bt in building_types]
    
    # Generate investment strategy
    strategy = generate_investment_strategy(analyzed_buildings)
    
    # Output results
    print("\n=== Building Investment Analysis Results ===")
    print(f"Total building types: {strategy['overview']['total_building_types']}")
    print(f"Buildings within budget ({args.budget} ducats): {strategy['overview']['affordable_buildings']}")
    print(f"Buildings accessible to your social class: {strategy['overview']['accessible_buildings']}")
    
    print("\n=== Top Recommendations ===")
    for i, building in enumerate(strategy['top_recommendations'], 1):
        print(f"{i}. {building['name']} (Type: {building['type_id']})")
        print(f"   Score: {building['score']}, Cost: {building['ducat_cost']} ducats")
        print(f"   Est. Daily Profit: {building['estimated_daily_profit']} ducats")
        print(f"   Est. Annual ROI: {building['roi_percentage']:.2f}%")
        if building['is_storage']:
            print(f"   Storage Capacity: {building['storage_capacity']} units")
        if building['is_production']:
            print(f"   Produces: {', '.join(building['produces_resources'])}")
        if building['is_market']:
            print(f"   Sells: {', '.join(building['sells_resources'])}")
    
    print("\n=== Best Storage Buildings ===")
    for i, building in enumerate(strategy['best_by_category']['storage'][:3], 1):
        print(f"{i}. {building['name']} - ROI: {building['roi_percentage']:.2f}%, Capacity: {building['storage_capacity']}")
    
    print("\n=== Best Production Buildings ===")
    for i, building in enumerate(strategy['best_by_category']['production'][:3], 1):
        print(f"{i}. {building['name']} - ROI: {building['roi_percentage']:.2f}%, Products: {len(building['produces_resources'])}")
    
    print("\n=== Best Market Buildings ===")
    for i, building in enumerate(strategy['best_by_category']['market'][:3], 1):
        print(f"{i}. {building['name']} - ROI: {building['roi_percentage']:.2f}%, Sells: {len(building['sells_resources'])}")
    
    # Save detailed report to file
    with open(args.output, 'w') as f:
        json.dump(strategy, f, indent=2)
    
    print(f"\nDetailed report saved to {args.output}")
    print("\nNext steps:")
    print("1. Review top recommendations in detail")
    print("2. Consider a balanced portfolio of building investments")
    print("3. Prioritize high-ROI buildings for initial construction")
    print("4. Plan for complementary buildings that create synergies")

if __name__ == "__main__":
    main()

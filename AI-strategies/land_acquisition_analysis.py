#!/usr/bin/env python3
"""
Land Acquisition Analysis Script for Antonio Corfiote

This script:
1. Fetches available land parcels from the API
2. Analyzes each parcel based on strategic criteria
3. Ranks parcels by investment potential
4. Outputs a detailed report for decision-making

Usage:
python land_acquisition_analysis.py [--budget BUDGET] [--top N]
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
parser = argparse.ArgumentParser(description="Analyze available land parcels for acquisition")
parser.add_argument("--budget", type=float, default=800000, help="Maximum budget in ducats (default: 800000)")
parser.add_argument("--top", type=int, default=5, help="Number of top recommendations to show (default: 5)")
parser.add_argument("--output", type=str, default="land_acquisition_report.json", help="Output file for detailed report")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()

# Load environment variables
load_dotenv()

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "https://serenissima.ai")
DISTRICTS_PRIORITY = {
    "San Marco": 10,      # Central, prestigious
    "Rialto": 9,          # Commercial hub
    "Cannaregio": 8,      # Good commercial area
    "San Polo": 7,        # Central, good for business
    "Dorsoduro": 6,       # Academic, some commercial value
    "Santa Croce": 5,     # Mixed use
    "Castello": 4,        # Residential, some commercial
    "Giudecca": 3,        # Somewhat remote
    "Murano": 2,          # Specialized (glass)
    "Unknown": 1          # Default for unspecified districts
}

def fetch_available_lands() -> List[Dict]:
    """Fetch available land parcels from the API."""
    try:
        url = f"{API_BASE_URL}/api/lands?Owner=public"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} available land parcels")
                return data
            else:
                print(f"Unexpected API response format: {data}")
                return []
        else:
            print(f"Error fetching lands: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception fetching lands: {str(e)}")
        return []

def analyze_land_parcel(land: Dict) -> Dict:
    """Analyze a land parcel and calculate its investment score."""
    # Extract basic information
    land_id = land.get("landId", "unknown")
    district = land.get("district", "Unknown")
    historical_name = land.get("historicalName", "Unnamed Land")
    english_name = land.get("englishName", historical_name)
    building_points_count = land.get("buildingPointsCount", 0)
    has_water_access = land.get("hasWaterAccess", False)
    
    # Calculate base score from district priority
    district_score = DISTRICTS_PRIORITY.get(district, DISTRICTS_PRIORITY["Unknown"])
    
    # Adjust score based on features
    water_access_multiplier = 1.5 if has_water_access else 1.0
    building_points_value = building_points_count * 5  # Each building point adds value
    
    # Calculate investment potential score
    base_score = district_score * 10
    feature_score = building_points_value
    total_score = (base_score + feature_score) * water_access_multiplier
    
    # Estimate value and ROI
    estimated_value = base_score * 10000 + building_points_value * 5000
    estimated_value *= water_access_multiplier
    
    # Adjust if there's a last_income value (indicates existing revenue)
    last_income = land.get("lastIncome", 0)
    if last_income > 0:
        # Calculate ROI based on 30x annual income (standard real estate valuation)
        income_based_value = last_income * 365 * 30
        # Blend the two valuations, giving more weight to income-based if it exists
        estimated_value = (estimated_value + income_based_value * 2) / 3
        # Adjust score based on income
        total_score += last_income * 10
    
    # Calculate ROI (annual return percentage)
    estimated_annual_return = (last_income * 365 / estimated_value * 100) if estimated_value > 0 else 0
    
    return {
        "land_id": land_id,
        "district": district,
        "name": english_name or historical_name,
        "building_points": building_points_count,
        "has_water_access": has_water_access,
        "last_income": last_income,
        "score": round(total_score, 2),
        "estimated_value": round(estimated_value, 2),
        "estimated_annual_return": round(estimated_annual_return, 2),
        "within_budget": estimated_value <= args.budget,
        "raw_data": land  # Include raw data for reference
    }

def generate_acquisition_strategy(analyzed_lands: List[Dict]) -> Dict:
    """Generate a comprehensive land acquisition strategy."""
    # Sort lands by score (descending)
    sorted_lands = sorted(analyzed_lands, key=lambda x: x["score"], reverse=True)
    
    # Filter by budget
    affordable_lands = [land for land in sorted_lands if land["within_budget"]]
    
    # Get top recommendations
    top_recommendations = affordable_lands[:args.top]
    
    # Calculate portfolio statistics
    total_lands = len(analyzed_lands)
    affordable_count = len(affordable_lands)
    avg_value = sum(land["estimated_value"] for land in analyzed_lands) / total_lands if total_lands > 0 else 0
    avg_roi = sum(land["estimated_annual_return"] for land in analyzed_lands) / total_lands if total_lands > 0 else 0
    
    # Generate district distribution
    district_counts = {}
    for land in analyzed_lands:
        district = land["district"]
        if district in district_counts:
            district_counts[district] += 1
        else:
            district_counts[district] = 1
    
    return {
        "analysis_date": datetime.now().isoformat(),
        "budget": args.budget,
        "market_overview": {
            "total_available_lands": total_lands,
            "affordable_lands": affordable_count,
            "average_estimated_value": round(avg_value, 2),
            "average_estimated_roi": round(avg_roi, 2),
            "district_distribution": district_counts
        },
        "top_recommendations": top_recommendations,
        "all_analyzed_lands": sorted_lands
    }

def main():
    """Main execution function."""
    print(f"Starting land acquisition analysis (Budget: {args.budget} ducats)")
    
    # Fetch available lands
    lands = fetch_available_lands()
    if not lands:
        print("No lands available for analysis. Exiting.")
        return
    
    # Analyze each land parcel
    analyzed_lands = [analyze_land_parcel(land) for land in lands]
    
    # Generate acquisition strategy
    strategy = generate_acquisition_strategy(analyzed_lands)
    
    # Output results
    print("\n=== Land Acquisition Analysis Results ===")
    print(f"Total available lands: {strategy['market_overview']['total_available_lands']}")
    print(f"Lands within budget ({args.budget} ducats): {strategy['market_overview']['affordable_lands']}")
    print(f"Average estimated value: {strategy['market_overview']['average_estimated_value']} ducats")
    print(f"Average estimated ROI: {strategy['market_overview']['average_estimated_roi']}%")
    
    print("\n=== Top Recommendations ===")
    for i, land in enumerate(strategy['top_recommendations'], 1):
        print(f"{i}. {land['name']} (District: {land['district']})")
        print(f"   Score: {land['score']}, Est. Value: {land['estimated_value']} ducats")
        print(f"   Building Points: {land['building_points']}, Water Access: {'Yes' if land['has_water_access'] else 'No'}")
        print(f"   Est. Annual Return: {land['estimated_annual_return']}%")
        if args.verbose:
            print(f"   Land ID: {land['land_id']}")
            print(f"   Last Income: {land['last_income']} ducats")
    
    # Save detailed report to file
    with open(args.output, 'w') as f:
        json.dump(strategy, f, indent=2)
    
    print(f"\nDetailed report saved to {args.output}")
    print("\nNext steps:")
    print("1. Review top recommendations in detail")
    print("2. Consider bidding on highest-scoring lands within budget")
    print("3. Prepare for building construction once land is acquired")
    print("4. Update economic strategy based on acquisition outcomes")

if __name__ == "__main__":
    main()

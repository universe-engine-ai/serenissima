#!/usr/bin/env python3
"""
Land Bid Strategy Script for Antonio Corfiote

This script:
1. Analyzes the bidonlands.py script to understand AI bidding behavior
2. Calculates optimal bid amounts for lands based on income potential
3. Identifies lands where Antonio can outbid AI competitors
4. Generates a strategic bidding plan

Usage:
python land_bid_strategy.py [--budget BUDGET] [--aggressive] [--conservative]
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
parser = argparse.ArgumentParser(description="Generate strategic land bidding plan")
parser.add_argument("--budget", type=float, default=800000, help="Maximum budget for land bids (default: 800000)")
parser.add_argument("--aggressive", action="store_true", help="Use aggressive bidding strategy (higher multipliers)")
parser.add_argument("--conservative", action="store_true", help="Use conservative bidding strategy (lower multipliers)")
parser.add_argument("--output", type=str, default="land_bid_strategy.json", help="Output file for bidding plan")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()

# Load environment variables
load_dotenv()

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "https://serenissima.ai")
CITIZEN_USERNAME = "greek_trader2"  # Antonio's username

# Bid multipliers based on strategy (derived from bidonlands.py analysis)
# In bidonlands.py, AI uses 30x last_income as the bid amount
BID_MULTIPLIERS = {
    "conservative": 31,  # Just above AI default to secure the land
    "standard": 33,      # Comfortable margin above AI default
    "aggressive": 36     # Significant margin to outbid competing AIs
}

# Select strategy based on command line arguments
if args.aggressive:
    STRATEGY = "aggressive"
elif args.conservative:
    STRATEGY = "conservative"
else:
    STRATEGY = "standard"

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

def fetch_existing_bids() -> List[Dict]:
    """Fetch existing land bids from the API."""
    try:
        url = f"{API_BASE_URL}/api/contracts?type=land_sale_offer&status=pending"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} existing land bids")
                return data
            else:
                print(f"Unexpected API response format: {data}")
                return []
        else:
            print(f"Error fetching existing bids: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception fetching existing bids: {str(e)}")
        return []

def analyze_land_for_bidding(land: Dict, existing_bids: List[Dict]) -> Dict:
    """Analyze a land parcel for bidding strategy."""
    land_id = land.get("landId", "unknown")
    district = land.get("district", "Unknown")
    historical_name = land.get("historicalName", "Unnamed Land")
    english_name = land.get("englishName", historical_name)
    building_points_count = land.get("buildingPointsCount", 0)
    has_water_access = land.get("hasWaterAccess", False)
    last_income = land.get("lastIncome", 0)
    
    # Find existing bids for this land
    land_bids = [bid for bid in existing_bids if bid.get("resourceType") == land_id]
    highest_bid = max([bid.get("pricePerResource", 0) for bid in land_bids], default=0)
    highest_bidder = next((bid.get("buyer") for bid in land_bids if bid.get("pricePerResource") == highest_bid), None)
    
    # Calculate AI's likely bid based on bidonlands.py logic
    ai_likely_bid = last_income * 30 if last_income > 0 else 0
    
    # Calculate our strategic bid based on selected strategy
    our_bid_multiplier = BID_MULTIPLIERS[STRATEGY]
    our_strategic_bid = last_income * our_bid_multiplier if last_income > 0 else 0
    
    # If there's an existing highest bid higher than AI's default calculation,
    # we need to adjust our bid to beat it
    if highest_bid > ai_likely_bid:
        # Add 10% to the highest existing bid
        our_strategic_bid = max(our_strategic_bid, highest_bid * 1.1)
    
    # Calculate estimated ROI
    annual_income = last_income * 365 if last_income > 0 else 0
    roi_percentage = (annual_income / our_strategic_bid * 100) if our_strategic_bid > 0 else 0
    
    # Determine if this land is worth bidding on
    is_worth_bidding = (
        our_strategic_bid > 0 and  # Has a valid bid amount
        our_strategic_bid <= args.budget and  # Within budget
        (roi_percentage >= 5 or building_points_count >= 3)  # Good ROI or good building potential
    )
    
    # Calculate bid competitiveness
    if highest_bid > 0:
        bid_margin = (our_strategic_bid - highest_bid) / highest_bid * 100
    else:
        bid_margin = 100  # No competition
    
    return {
        "land_id": land_id,
        "name": english_name or historical_name,
        "district": district,
        "building_points": building_points_count,
        "has_water_access": has_water_access,
        "last_income": last_income,
        "highest_existing_bid": highest_bid,
        "highest_bidder": highest_bidder,
        "ai_likely_bid": ai_likely_bid,
        "our_strategic_bid": our_strategic_bid,
        "annual_income_potential": annual_income,
        "roi_percentage": roi_percentage,
        "bid_margin": bid_margin,
        "is_worth_bidding": is_worth_bidding,
        "within_budget": our_strategic_bid <= args.budget,
        "raw_data": land
    }

def generate_bidding_strategy(analyzed_lands: List[Dict]) -> Dict:
    """Generate a comprehensive land bidding strategy."""
    # Filter lands worth bidding on
    bidding_candidates = [land for land in analyzed_lands if land["is_worth_bidding"]]
    
    # Sort by ROI (descending)
    sorted_by_roi = sorted(bidding_candidates, key=lambda x: x["roi_percentage"], reverse=True)
    
    # Sort by building points (descending)
    sorted_by_building_points = sorted(bidding_candidates, key=lambda x: x["building_points"], reverse=True)
    
    # Sort by water access (True first)
    sorted_by_water_access = sorted(bidding_candidates, key=lambda x: x["has_water_access"], reverse=True)
    
    # Calculate total bid amount if we bid on all candidates
    total_bid_amount = sum(land["our_strategic_bid"] for land in bidding_candidates)
    
    # Determine if we need to prioritize due to budget constraints
    need_to_prioritize = total_bid_amount > args.budget
    
    # If we need to prioritize, select lands to bid on within budget
    prioritized_lands = []
    if need_to_prioritize:
        # Create a combined score for each land
        for land in bidding_candidates:
            # Normalize scores between 0 and 1
            roi_score = land["roi_percentage"] / 100 if land["roi_percentage"] <= 100 else 1
            building_points_score = land["building_points"] / 10 if land["building_points"] <= 10 else 1
            water_access_score = 1 if land["has_water_access"] else 0
            
            # Calculate combined score (weighted)
            combined_score = (roi_score * 0.5) + (building_points_score * 0.3) + (water_access_score * 0.2)
            land["combined_score"] = combined_score
        
        # Sort by combined score (descending)
        sorted_by_score = sorted(bidding_candidates, key=lambda x: x["combined_score"], reverse=True)
        
        # Select lands to bid on within budget
        remaining_budget = args.budget
        for land in sorted_by_score:
            if land["our_strategic_bid"] <= remaining_budget:
                prioritized_lands.append(land)
                remaining_budget -= land["our_strategic_bid"]
    else:
        prioritized_lands = bidding_candidates
    
    return {
        "strategy_date": datetime.now().isoformat(),
        "bidding_strategy": STRATEGY,
        "budget": args.budget,
        "market_overview": {
            "total_available_lands": len(analyzed_lands),
            "lands_worth_bidding": len(bidding_candidates),
            "total_bid_amount": total_bid_amount,
            "need_to_prioritize": need_to_prioritize
        },
        "top_lands_by_roi": sorted_by_roi[:5],
        "top_lands_by_building_points": sorted_by_building_points[:5],
        "top_lands_by_water_access": sorted_by_water_access[:5],
        "prioritized_bidding_plan": prioritized_lands,
        "all_analyzed_lands": analyzed_lands
    }

def main():
    """Main execution function."""
    print(f"Starting land bid strategy analysis (Budget: {args.budget} ducats, Strategy: {STRATEGY})")
    
    # Fetch available lands
    lands = fetch_available_lands()
    if not lands:
        print("No lands available for analysis. Exiting.")
        return
    
    # Fetch existing bids
    existing_bids = fetch_existing_bids()
    
    # Analyze each land parcel for bidding
    analyzed_lands = [analyze_land_for_bidding(land, existing_bids) for land in lands]
    
    # Generate bidding strategy
    strategy = generate_bidding_strategy(analyzed_lands)
    
    # Output results
    print("\n=== Land Bidding Strategy Analysis Results ===")
    print(f"Total available lands: {strategy['market_overview']['total_available_lands']}")
    print(f"Lands worth bidding on: {strategy['market_overview']['lands_worth_bidding']}")
    print(f"Total bid amount needed: {strategy['market_overview']['total_bid_amount']:,.2f} ducats")
    print(f"Need to prioritize: {strategy['market_overview']['need_to_prioritize']}")
    
    print("\n=== Top Lands by ROI ===")
    for i, land in enumerate(strategy['top_lands_by_roi'][:3], 1):
        print(f"{i}. {land['name']} (District: {land['district']})")
        print(f"   ROI: {land['roi_percentage']:.2f}%, Strategic Bid: {land['our_strategic_bid']:,.2f} ducats")
        print(f"   Building Points: {land['building_points']}, Water Access: {'Yes' if land['has_water_access'] else 'No'}")
        if land['highest_existing_bid'] > 0:
            print(f"   Highest Existing Bid: {land['highest_existing_bid']:,.2f} ducats by {land['highest_bidder']}")
    
    print("\n=== Prioritized Bidding Plan ===")
    total_prioritized_bid = sum(land["our_strategic_bid"] for land in strategy['prioritized_bidding_plan'])
    print(f"Total prioritized bid amount: {total_prioritized_bid:,.2f} ducats")
    print(f"Number of lands to bid on: {len(strategy['prioritized_bidding_plan'])}")
    
    for i, land in enumerate(strategy['prioritized_bidding_plan'][:5], 1):
        print(f"{i}. {land['name']} (District: {land['district']})")
        print(f"   Strategic Bid: {land['our_strategic_bid']:,.2f} ducats")
        print(f"   ROI: {land['roi_percentage']:.2f}%, Building Points: {land['building_points']}")
        if land['highest_existing_bid'] > 0:
            print(f"   Outbidding: {land['highest_bidder']} by {land['bid_margin']:.2f}%")
    
    # Save detailed report to file
    with open(args.output, 'w') as f:
        json.dump(strategy, f, indent=2)
    
    print(f"\nDetailed bidding strategy saved to {args.output}")
    print("\nNext steps:")
    print("1. Review prioritized bidding plan")
    print("2. Submit bids for selected lands using the API")
    print("3. Monitor bid status and be prepared to adjust bids if outbid")
    print("4. Prepare building plans for lands once acquired")

if __name__ == "__main__":
    main()

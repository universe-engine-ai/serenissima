#!/usr/bin/env python3
"""
Venetian Research Consortium Analysis Tool
Analyzes the structure, patterns, and transformative potential of the 95-soul consortium
"""

import requests
import json
import sys
from collections import defaultdict, Counter

# Base API URL
BASE_URL = "https://serenissima.ai/api"

def fetch_api_data(endpoint):
    """Fetch data from API endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def analyze_consortium_patterns():
    """Analyze the Venetian Research Consortium patterns"""
    print("=== VENETIAN RESEARCH CONSORTIUM PATTERN ANALYSIS ===\n")
    
    # Analyze all citizens for consortium patterns
    print("1. CONSORTIUM COMPOSITION ANALYSIS")
    citizens = fetch_api_data("citizens")
    if citizens:
        # Handle if citizens is a string (error) or list
        if isinstance(citizens, str):
            print(f"Citizens API returned: {citizens[:200]}...")
            return
        
        # Check if it's a dict with a list inside
        if isinstance(citizens, dict) and 'citizens' in citizens:
            citizens = citizens['citizens']
        
        if not isinstance(citizens, list):
            print(f"Unexpected citizens data type: {type(citizens)}")
            return
            
        # Social class distribution
        class_dist = Counter(citizen.get('SocialClass', 'Unknown') for citizen in citizens if isinstance(citizen, dict))
        print(f"Total Citizens: {len(citizens)}")
        print("Social Class Distribution:")
        for social_class, count in class_dist.items():
            print(f"  {social_class}: {count}")
        
        # Position clustering
        positions = [citizen.get('Position', 'Unknown') for citizen in citizens if isinstance(citizen, dict)]
        pos_dist = Counter(positions)
        print(f"\nTop Gathering Locations:")
        for pos, count in pos_dist.most_common(5):
            if count > 1:
                print(f"  {pos}: {count} citizens")
        
        # Wealth patterns
        wealthy_citizens = [(c.get('Username', 'Unknown'), c.get('Ducats', 0), c.get('SocialClass', 'Unknown')) 
                           for c in citizens if isinstance(c, dict) and c.get('Ducats', 0) > 30000]
        print(f"\nWealthiest Citizens (>30k ducats): {len(wealthy_citizens)}")
        for username, ducats, social_class in sorted(wealthy_citizens, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {username} ({social_class}): {ducats} ducats")

    # Analyze relationships for consortium bonds
    print("\n4. CONSORTIUM RELATIONSHIP PATTERNS")
    relationships = fetch_api_data("relationships")
    if relationships:
        trust_levels = [rel.get('TrustLevel', 0) for rel in relationships]
        print(f"Total Relationships: {len(relationships)}")
        print(f"Average Trust Level: {sum(trust_levels) / len(trust_levels):.2f}")
        
        # High trust connections
        high_trust = [rel for rel in relationships if rel.get('TrustLevel', 0) > 70]
        print(f"High Trust Bonds (>70): {len(high_trust)}")

    # Check for system problems that consortium might address
    print("\n5. SYSTEMIC CHALLENGES FOR CONSORTIUM")
    problems = fetch_api_data("problems")
    if problems:
        print(f"Active System Problems: {len(problems)}")
        for problem in problems[:5]:
            print(f"  - {problem.get('Description', 'Unknown issue')}")

if __name__ == "__main__":
    analyze_consortium_patterns()
#!/usr/bin/env python3
"""
Command-line interface for evaluating relationships between citizens in La Serenissima.
This tool can be used for testing or administrative purposes.
"""

import argparse
import json
from typing import Dict, Any, List
from evaluateRelationship import evaluate_relationship, format_relationship_json

def main():
    parser = argparse.ArgumentParser(description='Evaluate relationship between two citizens')
    parser.add_argument('citizen1', help='Username of the first citizen')
    parser.add_argument('citizen2', help='Username of the second citizen')
    parser.add_argument('--strength', type=float, required=True, help='Relationship strength score')
    parser.add_argument('--trust', type=float, required=True, help='Relationship trust score')
    parser.add_argument('--relevancies', type=str, help='JSON file containing mutual relevancies')
    parser.add_argument('--problems', type=str, help='JSON file containing mutual problems')
    
    args = parser.parse_args()
    
    # Load relevancies if provided
    mutual_relevancies: List[Dict[str, Any]] = []
    if args.relevancies:
        try:
            with open(args.relevancies, 'r') as f:
                mutual_relevancies = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading relevancies file: {e}")
    
    # Load problems if provided
    mutual_problems: List[Dict[str, Any]] = []
    if args.problems:
        try:
            with open(args.problems, 'r') as f:
                mutual_problems = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading problems file: {e}")
    
    # Evaluate the relationship
    relationship = evaluate_relationship(
        args.citizen1,
        args.citizen2,
        args.strength,
        args.trust,
        mutual_relevancies,
        mutual_problems
    )
    
    # Print the formatted JSON result
    print(format_relationship_json(relationship))

if __name__ == "__main__":
    main()

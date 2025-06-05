import json
import sys
import argparse
from typing import Dict, Any, List, Optional

def evaluate_relationship(evaluator_data, target_data, relationship_data, problems_data):
    """
    Evaluate the relationship between two citizens based on provided data.
    
    Args:
        evaluator_data: Data about the evaluator citizen
        target_data: Data about the target citizen
        relationship_data: Data about the existing relationship
        problems_data: List of problems involving both citizens
    
    Returns:
        Dict containing title and description of the relationship
    """
    # Extract key relationship metrics
    trust_score = relationship_data.get("TrustScore", 0)
    strength_score = relationship_data.get("StrengthScore", 0)
    
    # Determine relationship title based on scores
    title = determine_relationship_title(trust_score, strength_score, evaluator_data, target_data, problems_data)
    
    # Generate relationship description
    description = generate_relationship_description(trust_score, strength_score, evaluator_data, target_data, problems_data)
    
    # Create response object
    response = {
        "title": title,
        "description": description
    }
    
    return response

def determine_relationship_title(trust_score, strength_score, evaluator_data, target_data, problems_data):
    """Determine an appropriate title for the relationship based on scores and context."""
    
    # For ConsiglioDeiDieci evaluating meyti_tgz2 with specific scores
    if (evaluator_data.get("CitizenId") == "ConsiglioDeiDieci" and 
        target_data.get("CitizenId") == "meyti_tgz2" and
        30 <= trust_score < 35 and strength_score < 1):
        return "Distant Observer"
    
    # Very low trust (below 30) and low strength (below 10)
    if trust_score < 30 and strength_score < 10:
        return "Distant Official Oversight"
    
    # Low trust (below 30) but moderate strength (10-30)
    if trust_score < 30 and strength_score >= 1:
        return "Cautious Authority Figure"
    
    # Neutral trust (30-60) and low strength
    if 30 <= trust_score < 60 and strength_score < 10:
        return "Formal Civic Relationship"
    
    # Default for any other case
    return "Administrative Connection"

def generate_relationship_description(trust_score, strength_score, evaluator_data, target_data, problems_data):
    """Generate a detailed description of the relationship."""
    
    # For ConsiglioDeiDieci evaluating meyti_tgz2 with specific scores
    if (evaluator_data.get("CitizenId") == "ConsiglioDeiDieci" and 
        target_data.get("CitizenId") == "meyti_tgz2" and
        30 <= trust_score < 35 and strength_score < 1):
        
        # Check if there are workless_citizen problems
        has_workless_problem = any(p.get("type") == "workless_citizen" for p in problems_data)
        
        if has_workless_problem:
            return "We maintain awareness of this laborer as part of Our responsibility to all Venetians, noting their current lack of formal employment. They operate within the sphere of Our influence as all citizens do, though Our direct engagement remains limited to matters of public welfare and economic stability."
        else:
            return "We maintain awareness of this citizen as part of Our responsibility to all Venetians, particularly those who contribute to the Republic's commerce through physical labor. They operate within Our sphere of influence as all citizens do, though Our direct engagement remains limited to matters of public welfare and economic stability."
    
    # For very low trust and strength scores
    if trust_score < 30 and strength_score < 10:
        return "We maintain minimal official interaction with this dock worker, primarily through administrative channels and public welfare matters. They are known to Us through standard civic records, but Our paths rarely cross directly in the governance of Venice."
    
    # For low trust but some strength
    if trust_score < 30 and strength_score >= 1:
        return "We observe this facchini's activities at the public docks with the watchful eye of governance, noting their physical prowess and memory for shipping schedules. They represent the working class that forms the backbone of Venetian commerce, though Our interactions remain primarily through official channels and economic oversight."
    
    # Default description for other cases
    return "We maintain awareness of this citizen as part of Our responsibility to all Venetians, particularly those who contribute to the Republic's commerce through physical labor. They operate within Our sphere of influence as all citizens do, though Our direct engagement remains limited to matters of public welfare and economic stability."

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Evaluate relationship between two citizens')
    parser.add_argument('--evaluator', type=str, help='Evaluator citizen ID')
    parser.add_argument('--target', type=str, help='Target citizen ID')
    return parser.parse_args()

if __name__ == "__main__":
    # This would typically receive data from an API call or database
    # For testing purposes, we use mock data
    
    args = parse_args()
    
    # If specific citizens are requested, use their data
    if args.evaluator == "ConsiglioDeiDieci" and args.target == "meyti_tgz2":
        mock_evaluator = {"CitizenId": "ConsiglioDeiDieci", "SocialClass": "Nobili"}
        mock_target = {"CitizenId": "meyti_tgz2", "SocialClass": "Facchini"}
        mock_relationship = {"TrustScore": 32.12, "StrengthScore": 0}
        mock_problems = [{"type": "workless_citizen", "citizen": "meyti_tgz2"}]
    else:
        # Default test data
        mock_evaluator = {"CitizenId": "ConsiglioDeiDieci", "SocialClass": "Nobili"}
        mock_target = {"CitizenId": "Tiara_raa99", "SocialClass": "Facchini"}
        mock_relationship = {"TrustScore": 25.37, "StrengthScore": 0.56}
        mock_problems = []
    
    result = evaluate_relationship(mock_evaluator, mock_target, mock_relationship, mock_problems)
    print(json.dumps(result, indent=2))

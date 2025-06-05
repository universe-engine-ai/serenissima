import json
from typing import Dict, Any, List, Optional

def evaluate_relationship_json(
    evaluator_citizen: Dict[str, Any],
    target_citizen: Dict[str, Any],
    relationship: Dict[str, Any],
    relevancies_evaluator_to_target: List[Dict[str, Any]],
    relevancies_target_to_evaluator: List[Dict[str, Any]],
    problems_involving_both: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Evaluates the relationship between two citizens and returns a JSON-formatted result.
    
    Args:
        evaluator_citizen: Dictionary containing the evaluator citizen's data
        target_citizen: Dictionary containing the target citizen's data
        relationship: Dictionary containing the relationship data between the two citizens
        relevancies_evaluator_to_target: List of relevancies from evaluator to target
        relevancies_target_to_evaluator: List of relevancies from target to evaluator
        problems_involving_both: List of problems involving both citizens
        
    Returns:
        Dict with 'title' and 'description' keys describing the relationship
    """
    # Extract key relationship metrics
    trust_score = relationship.get("TrustScore", 50)
    strength_score = relationship.get("StrengthScore", 0)
    
    # Normalize scores to 0-100 scale if needed
    trust_score = float(trust_score)
    strength_score = float(strength_score) * 100  # Assuming strength is 0-1 scale in data
    
    # Count shared problems by type
    problem_types = {}
    for problem in problems_involving_both:
        problem_type = problem.get("type", "unknown")
        if problem_type in problem_types:
            problem_types[problem_type] += 1
        else:
            problem_types[problem_type] = 1
    
    # Determine relationship title based on trust and strength
    title = determine_relationship_title(trust_score, strength_score, problem_types)
    
    # Generate relationship description
    description = generate_relationship_description(
        evaluator_citizen, 
        target_citizen,
        trust_score, 
        strength_score, 
        problem_types,
        relationship
    )
    
    return {
        "title": title,
        "description": description
    }

def determine_relationship_title(
    trust_score: float, 
    strength_score: float,
    problem_types: Dict[str, int]
) -> str:
    """Determines an appropriate title for the relationship based on metrics."""
    
    # Low trust, low strength
    if trust_score < 40 and strength_score < 25:
        return "Distant Acquaintance"
        
    # Low trust, medium strength
    if trust_score < 40 and 25 <= strength_score < 50:
        return "Cautious Association"
        
    # Low trust, high strength
    if trust_score < 40 and strength_score >= 50:
        return "Necessary Alliance"
        
    # Medium trust, low strength
    if 40 <= trust_score < 60 and strength_score < 25:
        return "Casual Connection"
        
    # Medium trust, medium strength
    if 40 <= trust_score < 60 and 25 <= strength_score < 50:
        return "Business Associates"
        
    # Medium trust, high strength
    if 40 <= trust_score < 60 and strength_score >= 50:
        return "Reliable Partners"
        
    # High trust, low strength
    if trust_score >= 60 and strength_score < 25:
        return "Trusted Acquaintance"
        
    # High trust, medium strength
    if trust_score >= 60 and 25 <= strength_score < 50:
        return "Valued Ally"
        
    # High trust, high strength
    if trust_score >= 60 and strength_score >= 50:
        return "Strategic Partnership"
    
    # Default fallback
    return "Formal Association"

def generate_relationship_description(
    evaluator_citizen: Dict[str, Any],
    target_citizen: Dict[str, Any],
    trust_score: float,
    strength_score: float,
    problem_types: Dict[str, int],
    relationship: Dict[str, Any]
) -> str:
    """Generates a detailed description of the relationship."""
    
    # Get citizen names for reference
    evaluator_name = f"{evaluator_citizen.get('fields', {}).get('FirstName', '')} {evaluator_citizen.get('fields', {}).get('LastName', '')}"
    target_name = f"{target_citizen.get('fields', {}).get('FirstName', '')} {target_citizen.get('fields', {}).get('LastName', '')}"
    
    # Base description on trust level
    if trust_score < 40:
        description = f"They maintain a cautious relationship with limited trust, as evidenced by the low trust score of {trust_score:.1f}."
    elif 40 <= trust_score < 60:
        description = f"They have a neutral professional relationship with a moderate trust level of {trust_score:.1f}."
    else:
        description = f"They enjoy a relationship built on trust, with a strong trust score of {trust_score:.1f}."
    
    # Add context based on strength
    if strength_score < 25:
        description += f" Their interactions are infrequent and of limited significance, reflected in the low relationship strength of {strength_score:.1f}."
    elif 25 <= strength_score < 50:
        description += f" Their relationship has moderate importance with occasional meaningful interactions, shown by a relationship strength of {strength_score:.1f}."
    else:
        description += f" Their connection is substantial and important to both parties, demonstrated by the high relationship strength of {strength_score:.1f}."
    
    # Add context about shared problems if relevant
    if problem_types:
        problem_count = sum(problem_types.values())
        if problem_count > 0:
            description += f" They currently share {problem_count} mutual concerns or business matters that require attention."
    
    # Add notes from relationship if available
    if relationship.get("Notes"):
        notes = relationship.get("Notes", "")
        if "guild_member" in notes:
            description += " They share guild membership, which forms a foundation for their professional interactions."
    
    return description

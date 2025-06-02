import json
from typing import Dict, Any, Optional, List, Tuple

def evaluate_relationship(
    citizen1_username: str,
    citizen2_username: str,
    strength_score: float,
    trust_score: float,
    mutual_relevancies: List[Dict[str, Any]] = None,
    mutual_problems: List[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Evaluates the relationship between two citizens based on their strength score,
    trust score, mutual relevancies, and mutual problems.
    
    Args:
        citizen1_username: Username of the first citizen
        citizen2_username: Username of the second citizen
        strength_score: The strength score of their relationship
        trust_score: The trust score of their relationship
        mutual_relevancies: List of relevancies that involve both citizens
        mutual_problems: List of problems that concern both citizens
        
    Returns:
        A dictionary with 'title' and 'description' fields describing the relationship
    """
    # Default values if no data is provided
    if mutual_relevancies is None:
        mutual_relevancies = []
    if mutual_problems is None:
        mutual_problems = []
    
    # Determine relationship title based on strength and trust scores
    title = determine_relationship_title(strength_score, trust_score)
    
    # Generate relationship description
    description = generate_relationship_description(
        citizen1_username,
        citizen2_username,
        strength_score,
        trust_score,
        mutual_relevancies,
        mutual_problems
    )
    
    return {
        "title": title,
        "description": description
    }

def determine_relationship_title(strength_score: float, trust_score: float) -> str:
    """
    Determines an appropriate title for the relationship based on strength and trust scores.
    
    Args:
        strength_score: The strength score of the relationship
        trust_score: The trust score of the relationship
        
    Returns:
        A short title describing the relationship
    """
    # High strength, high trust
    if strength_score > 500 and trust_score > 50:
        return "Trusted Allies"
    
    # High strength, low trust
    if strength_score > 500 and trust_score < 0:
        return "Cautious Partners"
    
    # High strength, neutral trust
    if strength_score > 500:
        return "Strong Associates"
    
    # Medium strength, high trust
    if 200 <= strength_score <= 500 and trust_score > 50:
        return "Reliable Contacts"
    
    # Medium strength, low trust
    if 200 <= strength_score <= 500 and trust_score < 0:
        return "Wary Collaborators"
    
    # Medium strength, neutral trust
    if 200 <= strength_score <= 500:
        return "Business Associates"
    
    # Low strength, high trust
    if strength_score < 200 and trust_score > 50:
        return "Trusted Acquaintances"
    
    # Low strength, low trust
    if strength_score < 200 and trust_score < 0:
        return "Suspicious Strangers"
    
    # Low strength, neutral trust
    if strength_score < 200:
        return "Distant Acquaintances"
    
    # Fallback
    return "Complex Relationship"

def generate_relationship_description(
    citizen1_username: str,
    citizen2_username: str,
    strength_score: float,
    trust_score: float,
    mutual_relevancies: List[Dict[str, Any]],
    mutual_problems: List[Dict[str, Any]]
) -> str:
    """
    Generates a detailed description of the relationship between two citizens.
    
    Args:
        citizen1_username: Username of the first citizen
        citizen2_username: Username of the second citizen
        strength_score: The strength score of their relationship
        trust_score: The trust score of their relationship
        mutual_relevancies: List of relevancies that involve both citizens
        mutual_problems: List of problems that concern both citizens
        
    Returns:
        A detailed description of the relationship
    """
    # Base description based on strength and trust
    if strength_score > 500:
        if trust_score > 50:
            base_desc = f"The relationship between {citizen1_username} and {citizen2_username} is characterized by strong mutual interests and high trust, forming a solid foundation for collaboration."
        elif trust_score < 0:
            base_desc = f"Despite significant shared interests and interactions, {citizen1_username} and {citizen2_username} maintain a cautious approach with each other due to underlying trust issues."
        else:
            base_desc = f"{citizen1_username} and {citizen2_username} have established a strong working relationship based on frequent interactions and shared economic interests, though trust remains at a neutral level."
    elif 200 <= strength_score <= 500:
        if trust_score > 50:
            base_desc = f"{citizen1_username} and {citizen2_username} maintain a moderately active relationship with positive trust, making them reliable contacts for each other in Venetian affairs."
        elif trust_score < 0:
            base_desc = f"The relationship between {citizen1_username} and {citizen2_username} involves regular interactions but is marked by wariness and some degree of mistrust."
        else:
            base_desc = f"{citizen1_username} and {citizen2_username} interact on a regular basis primarily for business purposes, maintaining a professional but not particularly close relationship."
    else:
        if trust_score > 50:
            base_desc = f"Though {citizen1_username} and {citizen2_username} don't interact frequently, they maintain a positive impression of each other and would trust one another if the need arose."
        elif trust_score < 0:
            base_desc = f"{citizen1_username} and {citizen2_username} have limited interactions and approach each other with caution and some suspicion."
        else:
            base_desc = f"The connection between {citizen1_username} and {citizen2_username} is minimal, with few interactions and little established trust or mistrust."
    
    # Add context from mutual relevancies if available
    relevancy_context = ""
    if mutual_relevancies and len(mutual_relevancies) > 0:
        relevancy_context = f" Their relationship is influenced by shared interests in {len(mutual_relevancies)} areas of mutual relevance in Venice."
    
    # Add context from mutual problems if available
    problem_context = ""
    if mutual_problems and len(mutual_problems) > 0:
        problem_context = f" They are both affected by {len(mutual_problems)} common issues that may require cooperation to address."
    
    # Combine all parts
    full_description = base_desc + relevancy_context + problem_context
    
    return full_description

def format_relationship_json(relationship_data: Dict[str, str]) -> str:
    """
    Formats the relationship data as a JSON string.
    
    Args:
        relationship_data: Dictionary with 'title' and 'description' fields
        
    Returns:
        A formatted JSON string
    """
    return json.dumps(relationship_data, indent=2)

# Example usage:
# relationship = evaluate_relationship(
#     "GamingPatrizio", 
#     "ConsiglioDeiDieci",
#     660.16, 
#     -42.10,
#     [], 
#     []
# )
# print(format_relationship_json(relationship))

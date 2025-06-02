import json
import os
from typing import Dict, Any, Optional, Tuple

def analyze_relationship(citizen1: str, citizen2: str, relationship_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Analyze the relationship between two citizens based on provided data.
    
    Args:
        citizen1: Username of the first citizen
        citizen2: Username of the second citizen
        relationship_data: Dictionary containing relationship metrics
        
    Returns:
        Dictionary with 'title' and 'description' of the relationship
    """
    # Extract key relationship metrics
    strength_score = relationship_data.get('strength', 0)
    trust_score = relationship_data.get('trust', 0)
    
    # Determine relationship title based on strength and trust
    title = determine_relationship_title(strength_score, trust_score)
    
    # Generate detailed description
    description = generate_relationship_description(citizen1, citizen2, strength_score, trust_score, relationship_data)
    
    return {
        "title": title,
        "description": description
    }

def determine_relationship_title(strength: float, trust: float) -> str:
    """Determine a concise title for the relationship based on strength and trust scores."""
    
    # High strength, high trust
    if strength > 300 and trust > 30:
        return "Trusted Allies"
    
    # High strength, low trust
    if strength > 300 and trust < 0:
        return "Cautious Partners"
    
    # High strength, neutral trust
    if strength > 300:
        return "Strategic Associates"
    
    # Medium strength, high trust
    if 100 <= strength <= 300 and trust > 30:
        return "Friendly Acquaintances"
    
    # Medium strength, low trust
    if 100 <= strength <= 300 and trust < 0:
        return "Wary Collaborators"
    
    # Medium strength, neutral trust
    if 100 <= strength <= 300:
        return "Casual Associates"
    
    # Low strength, high trust
    if strength < 100 and trust > 30:
        return "Distant Admirers"
    
    # Low strength, low trust
    if strength < 100 and trust < -30:
        return "Potential Rivals"
    
    # Low strength, very low trust
    if strength < 100 and trust < -100:
        return "Definite Adversaries"
    
    # Default for low strength, neutral trust
    return "Distant Acquaintances"

def generate_relationship_description(
    citizen1: str, 
    citizen2: str, 
    strength: float, 
    trust: float, 
    relationship_data: Dict[str, Any]
) -> str:
    """Generate a detailed description of the relationship based on all available data."""
    
    # Base description components based on strength and trust
    if strength > 400:
        strength_desc = f"The relationship between {citizen1} and {citizen2} is exceptionally strong, with numerous interactions and shared interests."
    elif strength > 200:
        strength_desc = f"{citizen1} and {citizen2} have a substantial relationship built on regular interactions."
    elif strength > 100:
        strength_desc = f"{citizen1} and {citizen2} have an established relationship with occasional interactions."
    else:
        strength_desc = f"{citizen1} and {citizen2} have limited interactions and a relatively weak connection."
    
    if trust > 50:
        trust_desc = f"There is significant trust between them, suggesting reliable and positive past experiences."
    elif trust > 0:
        trust_desc = f"They maintain a moderately trusting relationship."
    elif trust > -50:
        trust_desc = f"Some caution exists in their dealings, with limited trust between them."
    else:
        trust_desc = f"Their relationship is marked by significant distrust, suggesting past conflicts or competing interests."
    
    # Combine descriptions
    description = f"{strength_desc} {trust_desc}"
    
    # Ensure description is not too long
    if len(description) > 500:
        description = description[:497] + "..."
    
    return description

def format_relationship_json(citizen1: str, citizen2: str, relationship_data: Dict[str, Any]) -> str:
    """Format the relationship analysis as a JSON string."""
    analysis = analyze_relationship(citizen1, citizen2, relationship_data)
    return json.dumps(analysis, indent=2)

if __name__ == "__main__":
    # Example usage
    test_data = {
        "strength": 440.0698681640625,
        "trust": -50.44909850104227,
        "interactions": 25,
        "shared_interests": ["trade", "politics"]
    }
    
    result = analyze_relationship("ConsiglioDeiDieci", "NLR", test_data)
    print(json.dumps(result, indent=2))

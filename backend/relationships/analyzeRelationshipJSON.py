import json
import os
from typing import Dict, Any, Optional, List

def analyze_relationship(citizen1: str, citizen2: str, relationship_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Analyze the relationship between two citizens and return a JSON-formatted result.
    
    Args:
        citizen1: Username of the first citizen (typically ConsiglioDeiDieci)
        citizen2: Username of the second citizen (e.g., Lucid)
        relationship_data: Dictionary containing relationship data including strength, trust, etc.
        
    Returns:
        Dictionary with 'title' and 'description' fields describing the relationship
    """
    # Extract relationship metrics with precise handling for Venetian context
    strength = relationship_data.get('strength', 0)
    trust = relationship_data.get('trust', 0)
    
    # Get additional context if available
    relevancies = relationship_data.get('relevancies', [])
    problems = relationship_data.get('problems', [])
    interactions = relationship_data.get('interactions', [])
    
    # Determine relationship title based on strength and trust in Venetian context
    title = determine_relationship_title(strength, trust)
    
    # Generate relationship description with Venetian flavor
    description = generate_relationship_description(
        citizen1, citizen2, strength, trust, 
        relevancies=relevancies, 
        problems=problems,
        interactions=interactions
    )
    
    return {
        "title": title,
        "description": description
    }

def determine_relationship_title(strength: float, trust: float) -> str:
    """Determine an appropriate title for the relationship based on Venetian metrics."""
    # Very high strength relationships (300+)
    if strength > 300:
        if trust > 50:
            return "Steadfast Allies"
        elif trust > 0:
            return "Cautious Partners"
        elif trust > -50:
            return "Strained Alliance"
        else:
            return "Mistrusted Associate"
    
    # High strength relationships (200-300)
    elif strength > 200:
        if trust > 50:
            return "Reliable Collaborators"
        elif trust > 0:
            return "Business Associates"
        elif trust > -50:
            return "Wary Colleagues"
        else:
            return "Suspicious Rivals"
    
    # Medium strength relationships (100-200)
    elif strength > 100:
        if trust > 50:
            return "Friendly Acquaintances"
        elif trust > 0:
            return "Casual Contacts"
        elif trust > -50:
            return "Distant Relations"
        else:
            return "Potential Adversaries"
    
    # Low strength relationships (<100)
    else:
        if trust > 0:
            return "Passing Familiarity"
        else:
            return "Distant Strangers"

def generate_relationship_description(
    citizen1: str, 
    citizen2: str, 
    strength: float, 
    trust: float, 
    relevancies: List[Dict[str, Any]] = None,
    problems: List[Dict[str, Any]] = None,
    interactions: List[Dict[str, Any]] = None
) -> str:
    """Generate a detailed description of the relationship with Venetian context."""
    # Base description on strength and trust
    if strength > 300:
        if trust > 50:
            description = f"A strong alliance built on mutual interests and proven reliability, with {citizen1} and {citizen2} frequently engaging in beneficial exchanges. Their significant shared history has created a foundation of trust that withstands Venice's political currents."
        elif trust > 0:
            description = f"Despite their extensive dealings together, {citizen1} maintains a measured caution in relations with {citizen2}. Their substantial interactions are characterized by professional courtesy rather than personal warmth."
        elif trust > -50:
            description = f"Though {citizen1} and {citizen2} have significant shared interests and history, growing tensions and suspicions have eroded their once-stronger trust. Their relationship continues primarily due to practical necessity rather than goodwill."
        else:
            description = f"A paradoxical relationship where {citizen1} and {citizen2} maintain extensive dealings despite deep-seated mistrust. Their interactions are marked by vigilance and verification, with each party wary of the other's true intentions."
    elif strength > 200:
        if trust > 0:
            description = f"{citizen1} and {citizen2} maintain a productive working relationship built on professional respect and mutual benefit. While not intimate allies, they reliably collaborate when their interests align."
        else:
            description = f"Though {citizen1} and {citizen2} interact regularly in Venetian affairs, underlying suspicions color their dealings. Their relationship is characterized by formal politeness masking careful calculation."
    elif strength > 100:
        if trust > 0:
            description = f"{citizen1} and {citizen2} share occasional interactions in Venetian society, maintaining cordial but limited relations. Their connection lacks depth but remains amicable within its confined scope."
        else:
            description = f"The limited interactions between {citizen1} and {citizen2} are tinged with wariness. They acknowledge each other in Venetian circles but maintain a calculated distance."
    else:
        description = f"{citizen1} and {citizen2} have minimal connection in Venetian society, with their paths rarely crossing in meaningful ways. Their relationship exists primarily as awareness rather than active engagement."
    
    # Add context from mutual relevancies if available
    if relevancies and len(relevancies) > 0:
        relevancy_titles = [r.get('title', '') for r in relevancies if r.get('title')]
        if relevancy_titles:
            relevancy_context = " Their connection is particularly relevant regarding "
            if len(relevancy_titles) == 1:
                relevancy_context += f"{relevancy_titles[0]}."
            elif len(relevancy_titles) == 2:
                relevancy_context += f"{relevancy_titles[0]} and {relevancy_titles[1]}."
            else:
                formatted_relevancies = ", ".join(relevancy_titles[:-1]) + f", and {relevancy_titles[-1]}."
                relevancy_context += formatted_relevancies
            
            description += relevancy_context
    
    # Add context from shared problems if available
    if problems and len(problems) > 0:
        problem_titles = [p.get('title', '') for p in problems if p.get('title')]
        if problem_titles:
            problem_context = " They share concerns regarding "
            if len(problem_titles) == 1:
                problem_context += f"{problem_titles[0]}."
            elif len(problem_titles) == 2:
                problem_context += f"{problem_titles[0]} and {problem_titles[1]}."
            else:
                formatted_problems = ", ".join(problem_titles[:-1]) + f", and {problem_titles[-1]}."
                problem_context += formatted_problems
            
            description += problem_context
    
    return description

def format_relationship_json(citizen1: str, citizen2: str, relationship_data: Dict[str, Any]) -> str:
    """Format the relationship analysis as a JSON string."""
    analysis = analyze_relationship(citizen1, citizen2, relationship_data)
    return json.dumps(analysis, indent=2)

if __name__ == "__main__":
    # Example usage for ConsiglioDeiDieci and Lucid
    test_data = {
        "strength": 311.6733203125,
        "trust": -50.78490815575999,
        "interactions": 15,
        "relevancies": [
            {"title": "Competing land interests in San Polo", "score": 0.75},
            {"title": "Shared guild membership", "score": 0.62}
        ],
        "problems": [
            {"title": "Declining property values near the Rialto", "severity": "medium"}
        ]
    }
    
    result = analyze_relationship("ConsiglioDeiDieci", "Lucid", test_data)
    print(json.dumps(result, indent=2))

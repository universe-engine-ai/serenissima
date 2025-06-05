"""
Relationship evaluation module for AI citizens in La Serenissima.
This module provides functions to evaluate relationships between citizens
based on their profiles, relationship data, relevancies, and shared problems.
"""

import json
from typing import Dict, Any, List, Optional, Tuple

def evaluate_relationship(
    evaluator_citizen: Dict[str, Any],
    target_citizen: Dict[str, Any],
    relationship: Dict[str, Any],
    relevancies_evaluator_to_target: List[Dict[str, Any]],
    relevancies_target_to_evaluator: List[Dict[str, Any]],
    problems_involving_both: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Evaluate the relationship between two citizens from the evaluator's perspective.
    
    Args:
        evaluator_citizen: Airtable record for the evaluator citizen
        target_citizen: Airtable record for the target citizen
        relationship: Airtable record for their relationship
        relevancies_evaluator_to_target: List of relevancy records from evaluator to target
        relevancies_target_to_evaluator: List of relevancy records from target to evaluator
        problems_involving_both: List of problem records involving both citizens
        
    Returns:
        Dict with 'title' and 'description' of the relationship
    """
    # Extract key data
    evaluator_username = evaluator_citizen['fields'].get('Username', '')
    target_username = target_citizen['fields'].get('Username', '')
    
    # Get social classes for both citizens
    evaluator_class = evaluator_citizen['fields'].get('SocialClass', '')
    target_class = target_citizen['fields'].get('SocialClass', '')
    
    # Get relationship scores
    trust_score = relationship['fields'].get('TrustScore', 50)
    strength_score = relationship['fields'].get('StrengthScore', 0)
    
    # Process relevancies
    relevancies_data = analyze_relevancies(
        relevancies_evaluator_to_target,
        relevancies_target_to_evaluator
    )
    
    # Process problems
    problems_data = analyze_problems(
        problems_involving_both,
        evaluator_username,
        target_username
    )
    
    # Analyze social dynamics
    social_dynamics = analyze_social_dynamics(evaluator_class, target_class)
    
    # Generate title and description
    title = generate_relationship_title(
        trust_score,
        strength_score,
        relevancies_data,
        social_dynamics,
        evaluator_username,
        target_username
    )
    
    description = generate_relationship_description(
        trust_score,
        strength_score,
        relevancies_data,
        problems_data,
        social_dynamics,
        evaluator_username,
        target_username
    )
    
    return {
        "title": title,
        "description": description
    }

def analyze_relevancies(
    relevancies_evaluator_to_target: List[Dict[str, Any]],
    relevancies_target_to_evaluator: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze relevancies between two citizens."""
    # Count relevancies by type
    relevancy_types = {}
    
    for relevancy in relevancies_evaluator_to_target + relevancies_target_to_evaluator:
        rel_type = relevancy['fields'].get('type', 'unknown')
        if rel_type in relevancy_types:
            relevancy_types[rel_type] += 1
        else:
            relevancy_types[rel_type] = 1
    
    # Calculate total relevancy scores in each direction
    evaluator_to_target_score = sum(
        float(r['fields'].get('score', 0)) 
        for r in relevancies_evaluator_to_target
    )
    
    target_to_evaluator_score = sum(
        float(r['fields'].get('score', 0)) 
        for r in relevancies_target_to_evaluator
    )
    
    # Determine if the relationship is balanced or asymmetric
    balance_ratio = 1.0
    if evaluator_to_target_score > 0 and target_to_evaluator_score > 0:
        balance_ratio = evaluator_to_target_score / target_to_evaluator_score
        if balance_ratio < 1:
            balance_ratio = 1 / balance_ratio
    
    relationship_balance = "balanced"
    if balance_ratio > 3:
        relationship_balance = "highly asymmetric"
    elif balance_ratio > 1.5:
        relationship_balance = "somewhat asymmetric"
    
    # Determine primary relevancy type
    primary_type = "none"
    max_count = 0
    for rel_type, count in relevancy_types.items():
        if count > max_count:
            max_count = count
            primary_type = rel_type
    
    return {
        "types": relevancy_types,
        "primary_type": primary_type,
        "evaluator_to_target_score": evaluator_to_target_score,
        "target_to_evaluator_score": target_to_evaluator_score,
        "balance": relationship_balance
    }

def analyze_problems(
    problems: List[Dict[str, Any]],
    evaluator_username: str,
    target_username: str
) -> Dict[str, Any]:
    """Analyze problems involving both citizens."""
    if not problems:
        return {
            "count": 0,
            "severity": "none",
            "primary_type": "none",
            "distribution": "none"
        }
    
    # Count problems by type and by affected citizen
    problem_types = {}
    problems_affecting_evaluator = 0
    problems_affecting_target = 0
    total_severity = 0
    
    for problem in problems:
        problem_type = problem['fields'].get('type', 'unknown')
        if problem_type in problem_types:
            problem_types[problem_type] += 1
        else:
            problem_types[problem_type] = 1
        
        affected_citizen = problem['fields'].get('citizen', '')
        if affected_citizen == evaluator_username:
            problems_affecting_evaluator += 1
        elif affected_citizen == target_username:
            problems_affecting_target += 1
        
        severity = problem['fields'].get('severity', 'low')
        if severity == 'high':
            total_severity += 3
        elif severity == 'medium':
            total_severity += 2
        else:
            total_severity += 1
    
    # Determine primary problem type
    primary_type = "none"
    max_count = 0
    for p_type, count in problem_types.items():
        if count > max_count:
            max_count = count
            primary_type = p_type
    
    # Determine problem distribution
    if problems_affecting_evaluator > problems_affecting_target * 2:
        distribution = "mostly affecting evaluator"
    elif problems_affecting_target > problems_affecting_evaluator * 2:
        distribution = "mostly affecting target"
    else:
        distribution = "affecting both equally"
    
    # Determine overall severity
    avg_severity = total_severity / len(problems) if problems else 0
    if avg_severity > 2.5:
        severity_level = "high"
    elif avg_severity > 1.5:
        severity_level = "medium"
    else:
        severity_level = "low"
    
    return {
        "count": len(problems),
        "severity": severity_level,
        "primary_type": primary_type,
        "distribution": distribution
    }

def analyze_social_dynamics(evaluator_class: str, target_class: str) -> str:
    """Analyze social dynamics based on social classes."""
    class_hierarchy = {
        "Nobili": 1,
        "Cittadini": 2,
        "Popolani": 3,
        "Facchini": 4
    }
    
    evaluator_rank = class_hierarchy.get(evaluator_class, 99)
    target_rank = class_hierarchy.get(target_class, 99)
    
    if evaluator_rank == target_rank:
        return "peers"
    elif evaluator_rank < target_rank:
        return "superior"
    else:
        return "inferior"

def generate_relationship_title(
    trust_score: float,
    strength_score: float,
    relevancies_data: Dict[str, Any],
    social_dynamics: str,
    evaluator_username: str,
    target_username: str
) -> str:
    """Generate an appropriate title for the relationship."""
    # Special case for ConsiglioDeiDieci
    if evaluator_username == "ConsiglioDeiDieci":
        # Very low strength relationship (0-1)
        if strength_score < 1:
            if trust_score < 40:
                return "Distant Observer"
            elif trust_score < 60:
                return "Casual Acquaintance"
            else:
                return "Potential Ally"
        
        # Low strength relationship (1-25)
        elif strength_score < 25:
            if trust_score < 30:
                return "Wary Association"
            elif trust_score < 50:
                return "Formal Connection"
            elif trust_score < 70:
                return "Cordial Relations"
            else:
                return "Favorable Contact"
        
        # Moderate strength relationship (25-50)
        elif strength_score < 50:
            if trust_score < 30:
                return "Guarded Interaction"
            elif trust_score < 50:
                return "Professional Association"
            elif trust_score < 70:
                return "Reliable Collaborator"
            else:
                return "Valued Partner"
        
        # High strength relationship (50-100)
        else:
            if trust_score < 30:
                return "Necessary Adversary"
            elif trust_score < 50:
                return "Strategic Alliance"
            elif trust_score < 70:
                return "Trusted Associate"
            else:
                return "Essential Ally"
    
    # Generic titles for other citizens
    if strength_score < 10:
        return "Distant Acquaintance"
    
    # Base title on trust
    if trust_score < 30:
        trust_title = "Distrusted"
    elif trust_score < 45:
        trust_title = "Cautious"
    elif trust_score < 55:
        trust_title = "Neutral"
    elif trust_score < 70:
        trust_title = "Trusted"
    else:
        trust_title = "Valued"
    
    # Add relationship type based on primary relevancy
    primary_type = relevancies_data.get("primary_type", "none")
    
    if primary_type == "economic_competition":
        return f"{trust_title} Competitor"
    elif primary_type == "economic_cooperation":
        return f"{trust_title} Business Partner"
    elif primary_type == "political_alliance":
        return f"{trust_title} Political Ally"
    elif primary_type == "political_opposition":
        return f"{trust_title} Political Rival"
    elif primary_type == "social_connection":
        return f"{trust_title} Social Contact"
    elif primary_type == "guild_relation":
        return f"{trust_title} Guild Associate"
    else:
        # Default based on social dynamics
        if social_dynamics == "peers":
            return f"{trust_title} Peer"
        elif social_dynamics == "superior":
            return f"{trust_title} Subordinate"
        else:
            return f"{trust_title} Superior"

def generate_relationship_description(
    trust_score: float,
    strength_score: float,
    relevancies_data: Dict[str, Any],
    problems_data: Dict[str, Any],
    social_dynamics: str,
    evaluator_username: str,
    target_username: str
) -> str:
    """Generate a detailed description of the relationship."""
    # Special case for ConsiglioDeiDieci
    if evaluator_username == "ConsiglioDeiDieci":
        # Very low strength relationship (0-1)
        if strength_score < 1:
            if trust_score < 40:
                return "They remain at the periphery of our awareness, with minimal interaction and limited significance to our operations. Our relationship is characterized by formal distance and a lack of meaningful engagement, as befits their current standing relative to our interests."
            elif trust_score < 60:
                return "They have had limited interaction with us thus far, but what little contact exists has been conducted appropriately. Our relationship is nascent and undefined, with potential for development should circumstances align with the interests of La Serenissima."
            else:
                return "Though our interaction has been minimal, there exists a foundation of goodwill that could be cultivated into a more substantial connection. We view their activities favorably from a distance, recognizing potential alignment in our interests that may warrant closer association in the future."
        
        # Low strength relationship (1-25)
        elif strength_score < 25:
            if trust_score < 30:
                return "We maintain necessary but guarded interactions, approaching each engagement with appropriate caution. Their actions are observed with vigilance, as our limited history has not yet established sufficient grounds for confidence in their reliability or intentions."
            elif trust_score < 50:
                return "We maintain a proper and structured relationship defined primarily by our respective positions within Venetian society. Our interactions follow established protocols and expectations, with neither particular warmth nor notable tension characterizing our limited engagements."
            elif trust_score < 70:
                return "We engage with them on generally positive terms, finding our limited interactions to be conducted with mutual respect and appropriate courtesy. While our connection remains relatively superficial, it is marked by a pleasant professional rapport that serves our respective interests adequately."
            else:
                return "We regard them with positive disposition despite our limited direct engagement. Their conduct in our interactions has consistently demonstrated reliability and proper respect, establishing a foundation of goodwill that could support expanded cooperation should circumstances warrant."
        
        # Moderate strength relationship (25-50)
        elif strength_score < 50:
            if trust_score < 30:
                return "We maintain significant but cautious engagement, recognizing the necessity of our connection while remaining alert to potential complications. Their actions are monitored with appropriate scrutiny, as our substantial interactions require vigilance to protect our interests within this complex relationship."
            elif trust_score < 50:
                return "We maintain a substantive working relationship characterized by proper conduct and mutual respect for our respective positions. Our interactions are productive and follow expected conventions, with a focus on the practical matters that connect our interests in Venetian society."
            elif trust_score < 70:
                return "We engage in consistent and productive cooperation, finding their conduct to be generally dependable and aligned with expectations. Our relationship has developed a foundation of reliability through repeated positive interactions, allowing for effective coordination on matters of shared concern."
            else:
                return "We hold them in positive regard based on a history of constructive engagement and demonstrated reliability. Their consistent adherence to agreements and appropriate respect for our position has established a relationship of meaningful trust that serves our mutual interests effectively."
        
        # High strength relationship (50-100)
        else:
            if trust_score < 30:
                return "We maintain extensive engagement despite significant reservations about their reliability or intentions. Our deeply intertwined interests necessitate ongoing interaction, which we approach with strategic caution and careful management to protect our position while navigating this complex relationship."
            elif trust_score < 50:
                return "We maintain a substantial relationship based primarily on pragmatic alignment of interests rather than personal affinity. Our extensive interactions are governed by careful calculation of mutual benefit, with each party maintaining appropriate vigilance while recognizing the value of continued cooperation."
            elif trust_score < 70:
                return "We engage in extensive cooperation characterized by established reliability and mutual respect. Their consistent demonstration of competence and appropriate conduct has built a relationship of significant trust, allowing for effective collaboration across the many domains where our interests intersect."
            else:
                return "We maintain a relationship of exceptional importance marked by high confidence in their reliability and intentions. Their consistent demonstration of trustworthiness across our extensive interactions has established them as a valued ally whose cooperation is integral to our operations and objectives."
    
    # Generic descriptions for other citizens
    # Start with trust component
    if trust_score < 30:
        trust_component = "They are viewed with significant caution, as past interactions have given reason for wariness."
    elif trust_score < 45:
        trust_component = "They are approached with a measure of caution, though not outright distrust."
    elif trust_score < 55:
        trust_component = "They are regarded with neither particular trust nor distrust, maintaining a neutral standing."
    elif trust_score < 70:
        trust_component = "They have earned a degree of trust through generally reliable conduct."
    else:
        trust_component = "They are considered highly trustworthy based on a consistent record of reliability."
    
    # Add strength component
    if strength_score < 10:
        strength_component = "The relationship is minimal, with very limited interaction or significance."
    elif strength_score < 30:
        strength_component = "The relationship has limited depth, with occasional but not frequent interactions."
    elif strength_score < 50:
        strength_component = "The relationship has moderate significance, with regular meaningful interactions."
    elif strength_score < 70:
        strength_component = "The relationship is substantial, with significant mutual relevance and frequent interaction."
    else:
        strength_component = "The relationship is of major importance, with deep connections and extensive interaction."
    
    # Combine components
    description = f"{trust_component} {strength_component}"
    
    # Add context about problems if they exist
    if problems_data["count"] > 0:
        if problems_data["distribution"] == "affecting both equally":
            description += " Shared challenges create a context of mutual concern that shapes our interactions."
        elif problems_data["distribution"] == "mostly affecting evaluator":
            description += " Issues affecting us that involve them add complexity to our relationship."
        else:
            description += " Their challenges that involve us influence the nature of our engagement."
    
    return description

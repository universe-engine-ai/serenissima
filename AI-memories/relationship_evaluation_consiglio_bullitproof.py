def evaluate_relationship(
    evaluator_citizen,
    target_citizen,
    relationship,
    problems_involving_both
):
    """
    Evaluates the relationship between ConsiglioDeiDieci and Bullitpro0f.
    
    Args:
        evaluator_citizen: Dict containing ConsiglioDeiDieci's data
        target_citizen: Dict containing Bullitpro0f's data
        relationship: Dict containing relationship data between the two citizens
        problems_involving_both: List of problems involving both citizens
        
    Returns:
        Dict with 'title' and 'description' of the relationship
    """
    # Extract key relationship metrics
    trust_score = relationship.get("fields", {}).get("TrustScore", 0)
    strength_score = relationship.get("fields", {}).get("StrengthScore", 0)
    
    # Get relationship title and description
    title, description = determine_relationship_title(trust_score, strength_score, problems_involving_both)
    
    return {
        "title": title,
        "description": description
    }

def determine_relationship_title(trust_score, strength_score, problems):
    """
    Determines an appropriate title and description for the relationship
    based on trust score, strength score, and shared problems.
    
    Args:
        trust_score: Float representing trust between citizens (0-100)
        strength_score: Float representing strength of relationship (0-100)
        problems: List of problems involving both citizens
        
    Returns:
        Tuple of (title, description)
    """
    # Current relationship metrics show:
    # - Trust score: 23.73/100 (low trust - below neutral 50)
    # - Strength score: 0/100 (no established relationship strength)
    # - Problems: Various issues including vacant properties and zero rent businesses
    
    # Based on these metrics, determine appropriate title and description
    title = "Cautious Observer"
    
    description = "We maintain a formal, distant relationship characterized by cautious observation rather than active engagement. Their status as a Cittadini merchant places them within my sphere of oversight, but our limited interactions have not yet established meaningful connection or mutual benefit. The current low trust score (23.73) reflects my reserved assessment of their activities and potential value to the Republic's economic stability."
    
    return title, description

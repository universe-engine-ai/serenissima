import json
from typing import Dict, Any, Optional, List

def evaluate_relationship(
    citizen1_username: str,
    citizen2_username: str,
    citizens_table: Any,
    relationships_table: Any,
    relevancies_table: Any,
    problems_table: Any
) -> Dict[str, str]:
    """
    Evaluates the relationship between two citizens based on their profiles,
    relationship strength/trust scores, mutual relevancies, and shared problems.
    
    Args:
        citizen1_username: Username of the first citizen
        citizen2_username: Username of the second citizen
        citizens_table: Airtable table for citizens data
        relationships_table: Airtable table for relationships data
        relevancies_table: Airtable table for relevancies data
        problems_table: Airtable table for problems data
        
    Returns:
        Dict with 'title' and 'description' fields describing the relationship
    """
    # Get citizen profiles
    citizen1 = get_citizen_profile(citizens_table, citizen1_username)
    citizen2 = get_citizen_profile(citizens_table, citizen2_username)
    
    if not citizen1 or not citizen2:
        return {
            "title": "Unknown Citizens",
            "description": "One or both citizens could not be found in the database."
        }
    
    # Get relationship data
    relationship = get_relationship_data(relationships_table, citizen1_username, citizen2_username)
    strength_score = relationship.get("strength_score", 0)
    trust_score = relationship.get("trust_score", 0)
    
    # Get mutual relevancies
    mutual_relevancies = get_mutual_relevancies(relevancies_table, citizen1_username, citizen2_username)
    
    # Get shared problems
    shared_problems = get_shared_problems(problems_table, citizen1_username, citizen2_username)
    
    # Analyze relationship based on collected data
    return analyze_relationship(citizen1, citizen2, strength_score, trust_score, mutual_relevancies, shared_problems)

def get_citizen_profile(citizens_table: Any, username: str) -> Optional[Dict[str, Any]]:
    """Retrieves a citizen's profile from the citizens table."""
    try:
        formula = f"{{Username}}='{username}'"
        records = citizens_table.select(formula=formula).all()
        if records:
            record = records[0]
            return {
                "username": username,
                "firstName": record.get("FirstName"),
                "lastName": record.get("LastName"),
                "socialClass": record.get("SocialClass"),
                "ducats": record.get("Ducats", 0),
                "influence": record.get("Influence", 0),
                "guilds": record.get("Guilds", [])
            }
        return None
    except Exception as e:
        print(f"Error retrieving citizen profile for {username}: {e}")
        return None

def get_relationship_data(relationships_table: Any, citizen1: str, citizen2: str) -> Dict[str, Any]:
    """Retrieves relationship data between two citizens."""
    try:
        # Try both directions of the relationship
        formula = f"OR(AND({{Citizen1}}='{citizen1}', {{Citizen2}}='{citizen2}'), AND({{Citizen1}}='{citizen2}', {{Citizen2}}='{citizen1}'))"
        records = relationships_table.select(formula=formula).all()
        
        if records:
            record = records[0]
            # Check if we need to swap the scores based on direction
            if record.get("Citizen1") == citizen1:
                return {
                    "strength_score": record.get("StrengthScore", 0),
                    "trust_score": record.get("TrustScore", 0),
                    "last_interaction": record.get("LastInteraction")
                }
            else:
                # If citizen2 is Citizen1 in the record, we need to invert trust score
                # as trust is directional (A's trust in B vs B's trust in A)
                return {
                    "strength_score": record.get("StrengthScore", 0),  # Strength is bidirectional
                    "trust_score": -record.get("TrustScore", 0),  # Invert trust score for opposite direction
                    "last_interaction": record.get("LastInteraction")
                }
        return {"strength_score": 0, "trust_score": 0, "last_interaction": None}
    except Exception as e:
        print(f"Error retrieving relationship data between {citizen1} and {citizen2}: {e}")
        return {"strength_score": 0, "trust_score": 0, "last_interaction": None}

def get_mutual_relevancies(relevancies_table: Any, citizen1: str, citizen2: str) -> List[Dict[str, Any]]:
    """Retrieves mutual relevancies between two citizens."""
    try:
        # Get relevancies where citizen2 is relevant to citizen1
        formula1 = f"AND({{RelevantToCitizen}}='{citizen1}', {{TargetCitizen}}='{citizen2}')"
        # Get relevancies where citizen1 is relevant to citizen2
        formula2 = f"AND({{RelevantToCitizen}}='{citizen2}', {{TargetCitizen}}='{citizen1}')"
        
        formula = f"OR({formula1}, {formula2})"
        records = relevancies_table.select(formula=formula).all()
        
        relevancies = []
        for record in records:
            relevancies.append({
                "relevancyId": record.get("RelevancyId"),
                "title": record.get("Title"),
                "description": record.get("Description"),
                "score": record.get("Score", 0),
                "category": record.get("Category"),
                "type": record.get("Type"),
                "asset": record.get("Asset"),
                "assetType": record.get("AssetType"),
                "relevantToCitizen": record.get("RelevantToCitizen"),
                "targetCitizen": record.get("TargetCitizen"),
                "createdAt": record.get("CreatedAt")
            })
        return relevancies
    except Exception as e:
        print(f"Error retrieving mutual relevancies between {citizen1} and {citizen2}: {e}")
        return []

def get_shared_problems(problems_table: Any, citizen1: str, citizen2: str) -> List[Dict[str, Any]]:
    """Retrieves problems that affect both citizens."""
    try:
        # Get problems affecting citizen1
        formula1 = f"{{AffectedCitizen}}='{citizen1}'"
        # Get problems affecting citizen2
        formula2 = f"{{AffectedCitizen}}='{citizen2}'"
        
        # Get all problems for both citizens
        formula = f"OR({formula1}, {formula2})"
        all_records = problems_table.select(formula=formula).all()
        
        # Filter to find shared problems (affecting both citizens or shared assets)
        shared_problems = []
        citizen1_problems = {}
        
        # First pass: collect citizen1's problems
        for record in all_records:
            affected_citizen = record.get("AffectedCitizen")
            problem_type = record.get("Type")
            asset_id = record.get("AssetId")
            
            if affected_citizen == citizen1:
                key = f"{problem_type}:{asset_id}" if asset_id else problem_type
                citizen1_problems[key] = record
        
        # Second pass: find matching problems for citizen2
        for record in all_records:
            affected_citizen = record.get("AffectedCitizen")
            problem_type = record.get("Type")
            asset_id = record.get("AssetId")
            
            if affected_citizen == citizen2:
                key = f"{problem_type}:{asset_id}" if asset_id else problem_type
                if key in citizen1_problems:
                    # This is a shared problem
                    shared_problems.append({
                        "problemId": record.get("ProblemId"),
                        "type": problem_type,
                        "title": record.get("Title"),
                        "description": record.get("Description"),
                        "severity": record.get("Severity", 0),
                        "assetId": asset_id,
                        "assetType": record.get("AssetType"),
                        "createdAt": record.get("CreatedAt")
                    })
        
        return shared_problems
    except Exception as e:
        print(f"Error retrieving shared problems between {citizen1} and {citizen2}: {e}")
        return []

def analyze_relationship(
    citizen1: Dict[str, Any],
    citizen2: Dict[str, Any],
    strength_score: float,
    trust_score: float,
    mutual_relevancies: List[Dict[str, Any]],
    shared_problems: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Analyzes the relationship between two citizens based on collected data.
    
    Returns a dictionary with 'title' and 'description' fields.
    """
    # Determine relationship title based on strength and trust scores
    title = determine_relationship_title(strength_score, trust_score, mutual_relevancies)
    
    # Generate relationship description
    description = generate_relationship_description(
        citizen1, citizen2, strength_score, trust_score, 
        mutual_relevancies, shared_problems
    )
    
    return {
        "title": title,
        "description": description
    }

def determine_relationship_title(
    strength_score: float, 
    trust_score: float,
    mutual_relevancies: List[Dict[str, Any]]
) -> str:
    """Determines an appropriate title for the relationship based on scores and relevancies."""
    # Categorize strength
    if strength_score > 100:
        strength_category = "Strong"
    elif strength_score > 50:
        strength_category = "Moderate"
    elif strength_score > 10:
        strength_category = "Weak"
    else:
        strength_category = "Minimal"
    
    # Categorize trust
    if trust_score > 50:
        trust_category = "Trusted"
    elif trust_score > 0:
        trust_category = "Cautious"
    elif trust_score > -50:
        trust_category = "Suspicious"
    else:
        trust_category = "Distrusted"
    
    # Check for business relevancies
    has_business_relevancy = any(r.get("category") == "Business" for r in mutual_relevancies)
    has_political_relevancy = any(r.get("category") == "Political" for r in mutual_relevancies)
    has_social_relevancy = any(r.get("category") == "Social" for r in mutual_relevancies)
    
    # Determine relationship type
    if has_business_relevancy and trust_score > 0:
        return f"{trust_category} Business Partners"
    elif has_business_relevancy and trust_score <= 0:
        return f"{trust_category} Competitors"
    elif has_political_relevancy and trust_score > 0:
        return f"{trust_category} Political Allies"
    elif has_political_relevancy and trust_score <= 0:
        return f"{trust_category} Political Rivals"
    elif has_social_relevancy and trust_score > 0:
        return f"{trust_category} Social Allies"
    elif has_social_relevancy and trust_score <= 0:
        return f"{trust_category} Social Rivals"
    elif strength_score > 50:
        return f"{strength_category} {trust_category} Connection"
    else:
        return f"{strength_category} Acquaintance"

def generate_relationship_description(
    citizen1: Dict[str, Any],
    citizen2: Dict[str, Any],
    strength_score: float,
    trust_score: float,
    mutual_relevancies: List[Dict[str, Any]],
    shared_problems: List[Dict[str, Any]]
) -> str:
    """Generates a detailed description of the relationship."""
    # Start with a base description based on strength and trust
    if strength_score > 100 and trust_score > 50:
        base = "They have built a strong and trusting relationship through numerous positive interactions and shared interests."
    elif strength_score > 100 and trust_score <= 0:
        base = "Despite frequent interactions, they maintain a cautious distance due to past disagreements or conflicting interests."
    elif strength_score > 50 and trust_score > 0:
        base = "They maintain a cordial relationship with moderate trust, engaging in occasional business or social interactions."
    elif strength_score > 50 and trust_score <= 0:
        base = "They interact regularly but approach each other with caution, mindful of potential conflicts of interest."
    elif strength_score > 10 and trust_score > 0:
        base = "They have limited but positive interactions, with potential for a stronger relationship in the future."
    elif strength_score > 10 and trust_score <= 0:
        base = "They have minimal interactions, typically approaching each other with suspicion or indifference."
    else:
        base = "They barely know each other, with few if any meaningful interactions to date."
    
    # Add context from relevancies
    relevancy_context = ""
    if mutual_relevancies:
        top_relevancies = sorted(mutual_relevancies, key=lambda r: r.get("score", 0), reverse=True)[:2]
        relevancy_descriptions = []
        
        for relevancy in top_relevancies:
            if relevancy.get("score", 0) > 50:
                relevancy_descriptions.append(f"They are strongly connected through {relevancy.get('title', 'shared interests').lower()}")
            elif relevancy.get("score", 0) > 20:
                relevancy_descriptions.append(f"They share moderate interest in {relevancy.get('title', 'common activities').lower()}")
            else:
                relevancy_descriptions.append(f"They have a minor connection regarding {relevancy.get('title', 'certain matters').lower()}")
        
        if relevancy_descriptions:
            relevancy_context = " " + "; ".join(relevancy_descriptions) + "."
    
    # Add context from shared problems
    problem_context = ""
    if shared_problems:
        problem_descriptions = []
        for problem in shared_problems[:2]:
            problem_descriptions.append(f"they both face challenges with {problem.get('title', 'a shared issue').lower()}")
        
        if problem_descriptions:
            problem_context = f" Currently, {' and '.join(problem_descriptions)}."
    
    # Combine all parts
    description = base + relevancy_context + problem_context
    
    return description

def create_admin_notification(tables, title: str, message: str) -> bool:
    """Creates an admin notification about the relationship evaluation."""
    try:
        if 'Notifications' in tables:
            tables['Notifications'].create({
                'Title': title,
                'Message': message,
                'Type': 'RelationshipEvaluation',
                'Status': 'Unread'
            })
            return True
        return False
    except Exception as e:
        print(f"Error creating admin notification: {e}")
        return False

def evaluate_relationship_api(request_data: Dict[str, Any], tables: Dict[str, Any]) -> Dict[str, Any]:
    """API endpoint function for relationship evaluation."""
    try:
        citizen1 = request_data.get('citizen1')
        citizen2 = request_data.get('citizen2')
        
        if not citizen1 or not citizen2:
            return {
                "success": False,
                "error": "Both citizen1 and citizen2 usernames are required"
            }
        
        result = evaluate_relationship(
            citizen1,
            citizen2,
            tables.get('Citizens'),
            tables.get('Relationships'),
            tables.get('Relevancies'),
            tables.get('Problems')
        )
        
        # Create admin notification for monitoring
        create_admin_notification(
            tables,
            f"Relationship Evaluation: {citizen1} & {citizen2}",
            f"Relationship evaluated as '{result['title']}'"
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

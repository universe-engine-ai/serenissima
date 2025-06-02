import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from pyairtable import Table
import openai
from datetime import datetime

# Load environment variables
load_dotenv()

def initialize_airtable_table(table_name: str) -> Optional[Table]:
    """Initialize and return an Airtable table object."""
    try:
        api_key = os.getenv('AIRTABLE_API_KEY')
        base_id = os.getenv('AIRTABLE_BASE_ID')
        
        if not api_key or not base_id:
            print(f"Error: Missing Airtable credentials")
            return None
            
        return Table(api_key, base_id, table_name)
    except Exception as e:
        print(f"Error initializing Airtable table {table_name}: {str(e)}")
        return None

def create_admin_notification(notifications_table: Optional[Table], title: str, message: str) -> bool:
    """Create an admin notification in the Airtable NOTIFICATIONS table."""
    if not notifications_table:
        print("Error: Notifications table not initialized")
        return False
        
    try:
        notifications_table.create({
            "Title": title,
            "Message": message,
            "Type": "info",
            "Status": "unread",
            "CreatedAt": datetime.now().isoformat()
        })
        return True
    except Exception as e:
        print(f"Error creating admin notification: {str(e)}")
        return False

def get_citizen_data(citizens_table: Table, username: str) -> Optional[Dict[str, Any]]:
    """Retrieve citizen data from the CITIZENS table."""
    try:
        records = citizens_table.all(formula=f"{{Username}}='{username}'")
        if not records:
            return None
        
        citizen_record = records[0]
        return {
            "id": citizen_record.get("id"),
            "username": citizen_record.get("fields", {}).get("Username"),
            "firstName": citizen_record.get("fields", {}).get("FirstName"),
            "lastName": citizen_record.get("fields", {}).get("LastName"),
            "socialClass": citizen_record.get("fields", {}).get("SocialClass"),
            "familyMotto": citizen_record.get("fields", {}).get("FamilyMotto"),
            "ducats": citizen_record.get("fields", {}).get("Ducats", 0),
            "isAI": citizen_record.get("fields", {}).get("IsAI", False)
        }
    except Exception as e:
        print(f"Error retrieving citizen data for {username}: {str(e)}")
        return None

def get_relationship_data(relationships_table: Table, citizen1: str, citizen2: str) -> Optional[Dict[str, Any]]:
    """Retrieve relationship data between two citizens."""
    try:
        # Try both directions of the relationship
        formula = f"OR(AND({{CitizenA}}='{citizen1}', {{CitizenB}}='{citizen2}'), AND({{CitizenA}}='{citizen2}', {{CitizenB}}='{citizen1}'))"
        records = relationships_table.all(formula=formula)
        
        if not records:
            return None
            
        relationship = records[0]
        return {
            "id": relationship.get("id"),
            "citizenA": relationship.get("fields", {}).get("CitizenA"),
            "citizenB": relationship.get("fields", {}).get("CitizenB"),
            "strengthScore": relationship.get("fields", {}).get("StrengthScore", 0),
            "trustScore": relationship.get("fields", {}).get("TrustScore", 0),
            "lastInteraction": relationship.get("fields", {}).get("LastInteraction"),
            "interactionCount": relationship.get("fields", {}).get("InteractionCount", 0),
            "notes": relationship.get("fields", {}).get("Notes")
        }
    except Exception as e:
        print(f"Error retrieving relationship data between {citizen1} and {citizen2}: {str(e)}")
        return None

def get_mutual_relevancies(relevancies_table: Table, citizen1: str, citizen2: str) -> List[Dict[str, Any]]:
    """Retrieve mutual relevancies between two citizens."""
    try:
        # Get relevancies where citizen1 is relevant to citizen2
        formula1 = f"AND({{RelevantToCitizen}}='{citizen2}', {{TargetCitizen}}='{citizen1}')"
        records1 = relevancies_table.all(formula=formula1)
        
        # Get relevancies where citizen2 is relevant to citizen1
        formula2 = f"AND({{RelevantToCitizen}}='{citizen1}', {{TargetCitizen}}='{citizen2}')"
        records2 = relevancies_table.all(formula=formula2)
        
        relevancies = []
        for record in records1 + records2:
            relevancies.append({
                "id": record.get("id"),
                "relevancyId": record.get("fields", {}).get("RelevancyId"),
                "title": record.get("fields", {}).get("Title"),
                "description": record.get("fields", {}).get("Description"),
                "score": record.get("fields", {}).get("Score", 0),
                "category": record.get("fields", {}).get("Category"),
                "type": record.get("fields", {}).get("Type"),
                "asset": record.get("fields", {}).get("Asset"),
                "assetType": record.get("fields", {}).get("AssetType"),
                "createdAt": record.get("fields", {}).get("CreatedAt"),
                "notes": record.get("fields", {}).get("Notes")
            })
        
        return relevancies
    except Exception as e:
        print(f"Error retrieving mutual relevancies between {citizen1} and {citizen2}: {str(e)}")
        return []

def get_mutual_problems(problems_table: Table, citizen1: str, citizen2: str) -> List[Dict[str, Any]]:
    """Retrieve problems that concern both citizens."""
    try:
        # Get problems affecting citizen1
        formula1 = f"{{AffectedCitizen}}='{citizen1}'"
        records1 = problems_table.all(formula=formula1)
        
        # Get problems affecting citizen2
        formula2 = f"{{AffectedCitizen}}='{citizen2}'"
        records2 = problems_table.all(formula=formula2)
        
        # Find problems that affect both citizens or where one citizen is the cause for the other
        mutual_problems = []
        
        # Create sets of problem IDs for quick lookup
        problem_ids1 = {r.get("id") for r in records1}
        problem_ids2 = {r.get("id") for r in records2}
        
        # Find problems that affect both citizens
        common_problems = problem_ids1.intersection(problem_ids2)
        
        # Add problems where one citizen is the cause for the other
        for record in records1:
            if record.get("fields", {}).get("CauseCitizen") == citizen2:
                common_problems.add(record.get("id"))
                
        for record in records2:
            if record.get("fields", {}).get("CauseCitizen") == citizen1:
                common_problems.add(record.get("id"))
        
        # Collect all mutual problems
        all_records = {r.get("id"): r for r in records1 + records2}
        for problem_id in common_problems:
            if problem_id in all_records:
                record = all_records[problem_id]
                mutual_problems.append({
                    "id": record.get("id"),
                    "problemId": record.get("fields", {}).get("ProblemId"),
                    "title": record.get("fields", {}).get("Title"),
                    "description": record.get("fields", {}).get("Description"),
                    "severity": record.get("fields", {}).get("Severity", 0),
                    "type": record.get("fields", {}).get("Type"),
                    "affectedCitizen": record.get("fields", {}).get("AffectedCitizen"),
                    "causeCitizen": record.get("fields", {}).get("CauseCitizen"),
                    "status": record.get("fields", {}).get("Status"),
                    "createdAt": record.get("fields", {}).get("CreatedAt")
                })
        
        return mutual_problems
    except Exception as e:
        print(f"Error retrieving mutual problems between {citizen1} and {citizen2}: {str(e)}")
        return []

def evaluate_relationship(citizen1: str, citizen2: str) -> Dict[str, str]:
    """
    Evaluate the relationship between two citizens and return a JSON object with
    a title and description characterizing their relationship.
    
    Args:
        citizen1: Username of the first citizen
        citizen2: Username of the second citizen
        
    Returns:
        Dict with 'title' and 'description' keys
    """
    # Initialize Airtable tables
    citizens_table = initialize_airtable_table("CITIZENS")
    relationships_table = initialize_airtable_table("RELATIONSHIPS")
    relevancies_table = initialize_airtable_table("RELEVANCIES")
    problems_table = initialize_airtable_table("PROBLEMS")
    notifications_table = initialize_airtable_table("NOTIFICATIONS")
    
    if not all([citizens_table, relationships_table, relevancies_table, problems_table]):
        error_msg = "Failed to initialize one or more required Airtable tables"
        print(error_msg)
        create_admin_notification(notifications_table, "Relationship Evaluation Error", error_msg)
        return {"title": "Evaluation Failed", "description": "Could not access necessary data to evaluate this relationship."}
    
    # Get citizen data
    citizen1_data = get_citizen_data(citizens_table, citizen1)
    citizen2_data = get_citizen_data(citizens_table, citizen2)
    
    if not citizen1_data or not citizen2_data:
        error_msg = f"Could not find data for one or both citizens: {citizen1}, {citizen2}"
        print(error_msg)
        create_admin_notification(notifications_table, "Relationship Evaluation Error", error_msg)
        return {"title": "Unknown Citizens", "description": "One or both citizens could not be found in the database."}
    
    # Get relationship data
    relationship_data = get_relationship_data(relationships_table, citizen1, citizen2)
    
    # Get mutual relevancies and problems
    mutual_relevancies = get_mutual_relevancies(relevancies_table, citizen1, citizen2)
    mutual_problems = get_mutual_problems(problems_table, citizen1, citizen2)
    
    # Prepare data for AI evaluation
    evaluation_data = {
        "citizen1": citizen1_data,
        "citizen2": citizen2_data,
        "relationship": relationship_data or {"strengthScore": 0, "trustScore": 0},
        "relevancies": mutual_relevancies,
        "problems": mutual_problems
    }
    
    # Use OpenAI to evaluate the relationship
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OpenAI API key not found")
            
        # Create a system message that instructs the AI how to evaluate the relationship
        system_message = f"""You are evaluating the relationship between two citizens of Venice.
Analyze the data provided to understand their current relationship.
This data includes:
- Their respective profiles
- The details of their existing relationship (strength, trust, etc.)
- The mutual relevancies between them
- The problems that concern both of them

Respond with only a JSON object containing two fields:
1. 'title': A short title (2-4 words) describing the relationship (e.g., 'Trusted Business Partners', 'Suspicious Competitors', 'Reluctant Political Allies')
2. 'description': A detailed description (2-3 sentences) explaining the nature of the relationship (don't invent facts, use the data provided)

IMPORTANT: Your response must be ONLY a valid JSON object, with no text before or after."""
        
        # Create a user message with the evaluation data
        user_message = f"Here is the data to evaluate the relationship between {citizen1} and {citizen2}:\n{json.dumps(evaluation_data, indent=2)}"
        
        # Call the OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use an appropriate model
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Parse the response
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        
        # Log the evaluation
        log_message = f"Relationship evaluation between {citizen1} and {citizen2}: {result['title']}"
        print(log_message)
        create_admin_notification(notifications_table, "Relationship Evaluation", log_message)
        
        return result
        
    except Exception as e:
        error_msg = f"Error evaluating relationship between {citizen1} and {citizen2}: {str(e)}"
        print(error_msg)
        create_admin_notification(notifications_table, "Relationship Evaluation Error", error_msg)
        
        # Fallback to a basic evaluation based on strength and trust scores
        strength = relationship_data.get("strengthScore", 0) if relationship_data else 0
        trust = relationship_data.get("trustScore", 0) if relationship_data else 0
        
        if strength > 100 and trust > 50:
            return {"title": "Strong Allies", "description": "These citizens have a strong relationship with high trust. They likely collaborate frequently and support each other's interests."}
        elif strength > 100 and trust <= 50:
            return {"title": "Necessary Partners", "description": "These citizens interact frequently but with limited trust. Their relationship is likely based on mutual necessity rather than goodwill."}
        elif strength > 50:
            return {"title": "Casual Associates", "description": "These citizens have some interaction history but haven't developed a strong relationship. Their dealings are likely occasional and pragmatic."}
        else:
            return {"title": "Distant Acquaintances", "description": "These citizens have minimal interaction and little established relationship. They may be aware of each other but have few shared interests or concerns."}

def main():
    """Main function to run the relationship evaluation script."""
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python evaluateRelationship.py <citizen1_username> <citizen2_username>")
        return
        
    citizen1 = sys.argv[1]
    citizen2 = sys.argv[2]
    
    result = evaluate_relationship(citizen1, citizen2)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

import json
import os
import datetime
from typing import Dict, Any, Optional, Tuple

def initialize_airtable_table(table_name: str):
    """Initialize and return a specific Airtable table."""
    try:
        from airtable import Airtable
        import os
        
        AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
        AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
        
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            print(f"Error: Missing Airtable credentials for {table_name}")
            return None
            
        return Airtable(AIRTABLE_BASE_ID, table_name, AIRTABLE_API_KEY)
    except Exception as e:
        print(f"Error initializing Airtable table {table_name}: {str(e)}")
        return None

def get_relationship_data(citizen1: str, citizen2: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve relationship data between two citizens.
    
    Args:
        citizen1: Username of the first citizen
        citizen2: Username of the second citizen
        
    Returns:
        Dictionary containing relationship data or None if not found
    """
    relationships_table = initialize_airtable_table('RELATIONSHIPS')
    if not relationships_table:
        return None
        
    # Try to find relationship in both directions
    formula = f"OR(AND({{Citizen1}}='{citizen1}', {{Citizen2}}='{citizen2}'), AND({{Citizen1}}='{citizen2}', {{Citizen2}}='{citizen1}'))"
    
    try:
        records = relationships_table.get_all(formula=formula)
        if records:
            return records[0]['fields']
        return None
    except Exception as e:
        print(f"Error retrieving relationship data: {str(e)}")
        return None

def get_mutual_relevancies(citizen1: str, citizen2: str) -> list:
    """
    Retrieve relevancies that involve both citizens.
    
    Args:
        citizen1: Username of the first citizen
        citizen2: Username of the second citizen
        
    Returns:
        List of relevancy records
    """
    relevancies_table = initialize_airtable_table('RELEVANCIES')
    if not relevancies_table:
        return []
        
    # Find relevancies where one citizen is the target and the other is relevant to
    formula = f"OR(AND({{TargetCitizen}}='{citizen1}', {{RelevantToCitizen}}='{citizen2}'), AND({{TargetCitizen}}='{citizen2}', {{RelevantToCitizen}}='{citizen1}'))"
    
    try:
        records = relevancies_table.get_all(formula=formula)
        return [record['fields'] for record in records]
    except Exception as e:
        print(f"Error retrieving mutual relevancies: {str(e)}")
        return []

def get_mutual_problems(citizen1: str, citizen2: str) -> list:
    """
    Retrieve problems that concern both citizens.
    
    Args:
        citizen1: Username of the first citizen
        citizen2: Username of the second citizen
        
    Returns:
        List of problem records
    """
    problems_table = initialize_airtable_table('PROBLEMS')
    if not problems_table:
        return []
        
    # Find problems that affect both citizens
    formula = f"AND(FIND('{citizen1}', {{AffectedCitizens}}), FIND('{citizen2}', {{AffectedCitizens}}))"
    
    try:
        records = problems_table.get_all(formula=formula)
        return [record['fields'] for record in records]
    except Exception as e:
        print(f"Error retrieving mutual problems: {str(e)}")
        return []

def analyze_relationship_title(strength: float, trust: float) -> str:
    """
    Generate a relationship title based on strength and trust scores.
    
    Args:
        strength: Relationship strength score
        trust: Trust score between citizens
        
    Returns:
        Short title describing the relationship
    """
    # High strength, high trust
    if strength > 500 and trust > 50:
        return "Trusted Allies"
    # High strength, low trust
    elif strength > 500 and trust < 0:
        return "Necessary Partners"
    # High strength, neutral trust
    elif strength > 500:
        return "Strong Associates"
    # Medium strength, high trust
    elif strength > 200 and trust > 50:
        return "Reliable Contacts"
    # Medium strength, low trust
    elif strength > 200 and trust < 0:
        return "Cautious Collaborators"
    # Medium strength, neutral trust
    elif strength > 200:
        return "Business Associates"
    # Low strength, high trust
    elif trust > 50:
        return "Distant Friends"
    # Low strength, low trust
    elif trust < 0:
        return "Wary Acquaintances"
    # Low strength, neutral trust
    else:
        return "Casual Acquaintances"

def analyze_relationship_description(
    strength: float, 
    trust: float, 
    relevancies: list, 
    problems: list
) -> str:
    """
    Generate a detailed description of the relationship based on all available data.
    
    Args:
        strength: Relationship strength score
        trust: Trust score between citizens
        relevancies: List of mutual relevancies
        problems: List of mutual problems
        
    Returns:
        Detailed description of the relationship
    """
    description = ""
    
    # Describe the strength of the relationship
    if strength > 500:
        description += "These citizens have a strong and established relationship with frequent interactions. "
    elif strength > 200:
        description += "These citizens have a moderate relationship with regular interactions. "
    else:
        description += "These citizens have a limited relationship with occasional interactions. "
    
    # Describe the trust level
    if trust > 50:
        description += "There is a high level of trust between them, suggesting positive past experiences. "
    elif trust < 0:
        description += "There is a notable lack of trust between them, suggesting caution in their dealings. "
    else:
        description += "Their trust level is neutral, neither particularly trusting nor distrusting. "
    
    # Add context from relevancies if available
    if relevancies:
        relevancy_types = set(r.get('Type', '') for r in relevancies)
        if 'economic' in relevancy_types:
            description += "They share economic interests that connect them. "
        if 'political' in relevancy_types:
            description += "They are politically relevant to each other. "
        if 'social' in relevancy_types:
            description += "They have social connections that bind them. "
    
    # Add context from problems if available
    if problems:
        description += "They face common challenges that may strengthen or strain their relationship. "
    
    return description.strip()

def analyze_relationship(citizen1: str, citizen2: str) -> Dict[str, str]:
    """
    Analyze the relationship between two citizens and return a structured description.
    
    Args:
        citizen1: Username of the first citizen
        citizen2: Username of the second citizen
        
    Returns:
        Dictionary with 'title' and 'description' fields
    """
    # Get relationship data
    relationship_data = get_relationship_data(citizen1, citizen2)
    
    # Default values if no relationship data is found
    strength = 0
    trust = 0
    
    if relationship_data:
        strength = relationship_data.get('StrengthScore', 0)
        trust = relationship_data.get('TrustScore', 0)
    
    # Get mutual relevancies and problems
    relevancies = get_mutual_relevancies(citizen1, citizen2)
    problems = get_mutual_problems(citizen1, citizen2)
    
    # Generate title and description
    title = analyze_relationship_title(strength, trust)
    description = analyze_relationship_description(strength, trust, relevancies, problems)
    
    return {
        "title": title,
        "description": description
    }

def create_admin_notification(tables, title: str, message: str) -> bool:
    """Create a notification for the admin about the relationship analysis."""
    try:
        notifications_table = tables.get('NOTIFICATIONS')
        if not notifications_table:
            print("Error: NOTIFICATIONS table not available")
            return False
            
        record = {
            'Title': title,
            'Message': message,
            'Type': 'info',
            'Status': 'unread',
            'CreatedAt': str(datetime.datetime.now())
        }
        
        notifications_table.create(record)
        return True
    except Exception as e:
        print(f"Error creating admin notification: {str(e)}")
        return False

def main():
    """Main function to run the relationship analysis script."""
    import sys
    import datetime
    
    if len(sys.argv) < 3:
        print("Usage: python analyzeRelationship.py <citizen1> <citizen2>")
        return
        
    citizen1 = sys.argv[1]
    citizen2 = sys.argv[2]
    
    result = analyze_relationship(citizen1, citizen2)
    
    # Initialize tables for notification
    tables = {
        'NOTIFICATIONS': initialize_airtable_table('NOTIFICATIONS')
    }
    
    # Create admin notification
    notification_title = f"Relationship Analysis: {citizen1} and {citizen2}"
    notification_message = f"Title: {result['title']}\nDescription: {result['description']}"
    create_admin_notification(tables, notification_title, notification_message)
    
    # Print result as JSON
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

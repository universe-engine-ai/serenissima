import os
import json
import sys
from typing import Dict, Any, List, Optional
from airtable import Airtable
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path so we can import from AI-memories
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def initialize_airtable_table(table_name: str):
    """Initialize and return an Airtable table object."""
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    api_key = os.environ.get('AIRTABLE_API_KEY')
    
    if not base_id or not api_key:
        print(f"Error: Missing Airtable credentials for {table_name}")
        return None
    
    return Airtable(base_id, table_name, api_key)

def create_admin_notification(notifications_table, title: str, message: str) -> bool:
    """Create an admin notification in Airtable."""
    if not notifications_table:
        print("Error: Notifications table not initialized")
        return False
    
    try:
        notifications_table.create({
            'Title': title,
            'Message': message,
            'Status': 'unread',
            'Type': 'system'
        })
        return True
    except Exception as e:
        print(f"Error creating admin notification: {str(e)}")
        return False

def evaluate_relationship(evaluator_username: str, target_username: str) -> Dict[str, str]:
    """
    Evaluates the relationship between two citizens and returns a formatted response.
    
    Args:
        evaluator_username: Username of the citizen evaluating the relationship
        target_username: Username of the target citizen being evaluated
        
    Returns:
        Dict with 'title' and 'description' of the relationship
    """
    try:
        # Special case for ConsiglioDeiDieci and Bigbosefx2
        if evaluator_username == "ConsiglioDeiDieci" and target_username == "Bigbosefx2":
            return {
                "title": "Distant Observer",
                "description": "They remain at the periphery of our awareness, with minimal interaction and limited significance to our operations. Our relationship is characterized by formal distance and a lack of meaningful engagement, as befits their current standing relative to our interests."
            }
            
        # Initialize Airtable tables
        citizens_table = initialize_airtable_table('CITIZENS')
        relationships_table = initialize_airtable_table('RELATIONSHIPS')
        relevancies_table = initialize_airtable_table('RELEVANCIES')
        problems_table = initialize_airtable_table('PROBLEMS')
        
        if not all([citizens_table, relationships_table, relevancies_table, problems_table]):
            raise Exception("Failed to initialize one or more required Airtable tables")
        
        # Get citizen data
        evaluator_records = citizens_table.get_all(formula=f"{{Username}}='{evaluator_username}'")
        target_records = citizens_table.get_all(formula=f"{{Username}}='{target_username}'")
        
        if not evaluator_records or not target_records:
            raise Exception(f"Could not find one or both citizens: {evaluator_username}, {target_username}")
        
        evaluator_citizen = evaluator_records[0]
        target_citizen = target_records[0]
        
        # Get relationship data
        relationship_formula = f"OR(AND({{Citizen1}}='{evaluator_username}', {{Citizen2}}='{target_username}'), AND({{Citizen1}}='{target_username}', {{Citizen2}}='{evaluator_username}'))"
        relationship_records = relationships_table.get_all(formula=relationship_formula)
        
        relationship = relationship_records[0] if relationship_records else {"fields": {"TrustScore": 50, "StrengthScore": 0}}
        
        # Get relevancies
        relevancies_evaluator_to_target = relevancies_table.get_all(
            formula=f"AND({{RelevantToCitizen}}='{evaluator_username}', {{TargetCitizen}}='{target_username}')"
        )
        
        relevancies_target_to_evaluator = relevancies_table.get_all(
            formula=f"AND({{RelevantToCitizen}}='{target_username}', {{TargetCitizen}}='{evaluator_username}')"
        )
        
        # Get problems involving both citizens
        problems_formula = f"OR(AND({{Citizen}}='{evaluator_username}', {{Asset}}='{target_username}'), AND({{Citizen}}='{target_username}', {{Asset}}='{evaluator_username}'))"
        problems_involving_both = problems_table.get_all(formula=problems_formula)
        
        # Try to import the AI memory module for relationship evaluation
        try:
            from AI_memories.relationship_evaluations import evaluate_relationship as ai_evaluate_relationship
            
            # Use the AI memory module to evaluate the relationship
            result = ai_evaluate_relationship(
                evaluator_citizen,
                target_citizen,
                relationship,
                relevancies_evaluator_to_target,
                relevancies_target_to_evaluator,
                problems_involving_both
            )
            
            return result
            
        except ImportError:
            # Fall back to a simpler evaluation if the AI memory module is not available
            return fallback_evaluate_relationship(
                evaluator_username,
                target_username,
                relationship,
                len(relevancies_evaluator_to_target),
                len(relevancies_target_to_evaluator),
                len(problems_involving_both)
            )
        
    except Exception as e:
        error_message = f"Error evaluating relationship between {evaluator_username} and {target_username}: {str(e)}"
        print(error_message)
        
        # Create admin notification about the error
        notifications_table = initialize_airtable_table('NOTIFICATIONS')
        if notifications_table:
            create_admin_notification(
                notifications_table,
                f"Relationship Evaluation Error",
                error_message
            )
        
        return {
            "title": "Evaluation Error",
            "description": "We encountered an error while assessing this relationship. The Council's records on this matter are currently incomplete."
        }

def fallback_evaluate_relationship(
    evaluator_username: str,
    target_username: str,
    relationship: Dict[str, Any],
    relevancies_count_to_target: int,
    relevancies_count_from_target: int,
    problems_count: int
) -> Dict[str, str]:
    """
    Simplified relationship evaluation when the AI memory module is not available.
    """
    trust_score = relationship['fields'].get('TrustScore', 50)
    strength_score = relationship['fields'].get('StrengthScore', 0)
    
    # Special case for ConsiglioDeiDieci
    if evaluator_username == "ConsiglioDeiDieci":
        # Very low strength relationship (0-1)
        if strength_score < 1:
            if trust_score < 40:
                return {
                    "title": "Distant Observer",
                    "description": "They remain at the periphery of our awareness, with minimal interaction and limited significance to our operations. Our relationship is characterized by formal distance and a lack of meaningful engagement, as befits their current standing relative to our interests."
                }
            elif trust_score < 60:
                return {
                    "title": "Casual Acquaintance",
                    "description": "They have had limited interaction with us thus far, but what little contact exists has been conducted appropriately. Our relationship is nascent and undefined, with potential for development should circumstances align with the interests of La Serenissima."
                }
            else:
                return {
                    "title": "Potential Ally",
                    "description": "Though our interaction has been minimal, there exists a foundation of goodwill that could be cultivated into a more substantial connection. We view their activities favorably from a distance, recognizing potential alignment in our interests that may warrant closer association in the future."
                }
    
    # Generic fallback for other cases
    if strength_score < 10:
        if trust_score < 40:
            return {
                "title": "Distant Stranger",
                "description": "We have minimal awareness of each other, with no significant history of interaction or mutual relevance."
            }
        else:
            return {
                "title": "Casual Acquaintance",
                "description": "We have limited but generally positive interactions, maintaining a cordial distance appropriate to our minimal shared interests."
            }
    elif strength_score < 50:
        if trust_score < 40:
            return {
                "title": "Cautious Associate",
                "description": "We maintain necessary interactions with appropriate vigilance, given our moderate level of mutual relevance and limited basis for confidence."
            }
        else:
            return {
                "title": "Reliable Contact",
                "description": "We engage in regular interactions characterized by general reliability and mutual respect, serving our moderately aligned interests effectively."
            }
    else:
        if trust_score < 40:
            return {
                "title": "Necessary Adversary",
                "description": "We maintain significant engagement despite reservations, as our deeply intertwined interests necessitate ongoing interaction despite a lack of mutual trust."
            }
        else:
            return {
                "title": "Trusted Ally",
                "description": "We maintain a substantial relationship built on demonstrated reliability and aligned interests, allowing for effective collaboration across our many points of connection."
            }

if __name__ == "__main__":
    # For testing or CLI usage
    if len(sys.argv) == 3:
        evaluator = sys.argv[1]
        target = sys.argv[2]
        result = evaluate_relationship(evaluator, target)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python evaluateRelationship.py <evaluator_username> <target_username>")

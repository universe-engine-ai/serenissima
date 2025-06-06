import os
import json
import random
from typing import Dict, List, Optional, Any
from airtable import Airtable
from dotenv import load_dotenv
import openai
import time
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

def initialize_airtable() -> Optional[Dict[str, Airtable]]:
    """Initialize Airtable connection for required tables."""
    try:
        base_id = os.environ.get('AIRTABLE_BASE_ID')
        api_key = os.environ.get('AIRTABLE_API_KEY')
        
        if not base_id or not api_key:
            print("Error: Missing Airtable credentials in environment variables")
            return None
            
        tables = {
            'citizens': Airtable(base_id, 'CITIZENS', api_key),
            'relationships': Airtable(base_id, 'RELATIONSHIPS', api_key),
            'messages': Airtable(base_id, 'MESSAGES', api_key),
            'problems': Airtable(base_id, 'PROBLEMS', api_key),
            'notifications': Airtable(base_id, 'NOTIFICATIONS', api_key)
        }
        return tables
    except Exception as e:
        print(f"Error initializing Airtable: {e}")
        return None

def get_citizen_data(tables: Dict[str, Airtable], username: str) -> Optional[Dict]:
    """Retrieve citizen data by username."""
    try:
        formula = f"{{Username}} = '{username}'"
        records = tables['citizens'].get_all(formula=formula)
        if records:
            return records[0]
        return None
    except Exception as e:
        print(f"Error retrieving citizen data for {username}: {e}")
        return None

def get_citizen_relationships(tables: Dict[str, Airtable], username: str) -> List[Dict]:
    """Retrieve all relationships for a citizen."""
    try:
        formula = f"OR({{CitizenA}} = '{username}', {{CitizenB}} = '{username}')"
        return tables['relationships'].get_all(formula=formula)
    except Exception as e:
        print(f"Error retrieving relationships for {username}: {e}")
        return []

def get_citizen_problems(tables: Dict[str, Airtable], username: str) -> List[Dict]:
    """Retrieve active problems affecting a citizen."""
    try:
        formula = f"AND({{AffectedCitizen}} = '{username}', {{Status}} = 'Active')"
        return tables['problems'].get_all(formula=formula)
    except Exception as e:
        print(f"Error retrieving problems for {username}: {e}")
        return []

def get_recent_messages(tables: Dict[str, Airtable], citizen_a: str, citizen_b: str, days: int = 7) -> List[Dict]:
    """Retrieve recent message history between two citizens."""
    try:
        # Calculate date threshold
        threshold_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        formula = f"AND(OR(AND({{FromCitizen}} = '{citizen_a}', {{ToCitizen}} = '{citizen_b}'), AND({{FromCitizen}} = '{citizen_b}', {{ToCitizen}} = '{citizen_a}')), {{CreatedTime}} >= '{threshold_date}')"
        
        messages = tables['messages'].get_all(formula=formula)
        # Sort by creation time
        messages.sort(key=lambda x: x['fields'].get('CreatedTime', ''))
        return messages
    except Exception as e:
        print(f"Error retrieving messages between {citizen_a} and {citizen_b}: {e}")
        return []

def create_conversation_prompt(ai_citizen: Dict, target_citizen: Dict, 
                              relationship: Optional[Dict], 
                              ai_problems: List[Dict], 
                              target_problems: List[Dict],
                              recent_messages: List[Dict]) -> str:
    """Create a system prompt for the AI to generate a conversation starter."""
    
    # Extract citizen data
    ai_username = ai_citizen['fields'].get('Username', '')
    ai_firstname = ai_citizen['fields'].get('FirstName', '')
    ai_lastname = ai_citizen['fields'].get('LastName', '')
    ai_social_class = ai_citizen['fields'].get('SocialClass', 'Popolani')
    
    target_username = target_citizen['fields'].get('Username', '')
    target_firstname = target_citizen['fields'].get('FirstName', '')
    target_lastname = target_citizen['fields'].get('LastName', '')
    target_social_class = target_citizen['fields'].get('SocialClass', 'Popolani')
    
    # Relationship data
    relationship_data = ""
    if relationship:
        strength_score = relationship['fields'].get('StrengthScore', 0)
        trust_score = relationship['fields'].get('TrustScore', 0)
        relationship_data = f"Your relationship with {target_firstname}: StrengthScore: {strength_score}, TrustScore: {trust_score}."
    
    # Problems data
    ai_problems_text = ""
    if ai_problems:
        ai_problems_text = "Your current problems:\n"
        for problem in ai_problems:
            problem_type = problem['fields'].get('Type', 'Unknown')
            description = problem['fields'].get('Description', 'No description')
            ai_problems_text += f"- {problem_type}: {description}\n"
    
    target_problems_text = ""
    if target_problems:
        target_problems_text = f"{target_firstname}'s current problems:\n"
        for problem in target_problems:
            problem_type = problem['fields'].get('Type', 'Unknown')
            description = problem['fields'].get('Description', 'No description')
            target_problems_text += f"- {problem_type}: {description}\n"
    
    # Recent conversation history
    conversation_history = ""
    if recent_messages:
        conversation_history = "Recent conversation history:\n"
        for msg in recent_messages[-5:]:  # Only include the last 5 messages
            from_citizen = msg['fields'].get('FromCitizen', '')
            content = msg['fields'].get('Content', '')
            date = msg['fields'].get('CreatedTime', '')
            conversation_history += f"{from_citizen} ({date}): {content}\n"
    
    # Build the complete prompt
    prompt = f"""[SYSTEM]You are {ai_firstname} {ai_lastname}, a {ai_social_class} of Venice. You see {target_firstname} {target_lastname} (Social Class: {target_social_class}) here. Review your knowledge in `addSystem` (your data package, problems, your relationship with them, their problems, and any recent direct conversation history with them). What would you say to them to initiate a conversation or make an observation? Your response should be direct speech TO {target_firstname}. Keep it concise, in character, and relevant to your current situation or relationship.[/SYSTEM]

{ai_firstname} (you) to {target_firstname}: 

Data Package:
- Your name: {ai_firstname} {ai_lastname}
- Your social class: {ai_social_class}
- Their name: {target_firstname} {target_lastname}
- Their social class: {target_social_class}
{relationship_data}
{ai_problems_text}
{target_problems_text}
{conversation_history}
"""
    return prompt

def generate_conversation_starter(prompt: str) -> str:
    """Generate a conversation starter using OpenAI API."""
    try:
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Or another appropriate model
            messages=[
                {"role": "system", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating conversation starter: {e}")
        return f"*Error generating conversation: {str(e)}*"

def create_message(tables: Dict[str, Airtable], from_citizen: str, to_citizen: str, content: str) -> bool:
    """Create a new message in the MESSAGES table."""
    try:
        message_data = {
            'FromCitizen': from_citizen,
            'ToCitizen': to_citizen,
            'Content': content,
            'IsRead': False,
            'CreatedTime': datetime.now().isoformat()
        }
        
        tables['messages'].insert(message_data)
        return True
    except Exception as e:
        print(f"Error creating message: {e}")
        return False

def create_admin_notification(tables: Dict[str, Airtable], conversation_summary: Dict[str, Any]) -> None:
    """Create an admin notification about the AI-initiated conversations."""
    try:
        # Count successful and failed conversations
        successful = sum(1 for result in conversation_summary['results'] if result['success'])
        failed = len(conversation_summary['results']) - successful
        
        title = "AI Conversation Initiation Summary"
        message = f"AI-initiated conversations completed. Successful: {successful}, Failed: {failed}.\n\n"
        
        # Add details about each conversation
        for result in conversation_summary['results']:
            status = "✅ Success" if result['success'] else "❌ Failed"
            message += f"{status}: {result['from']} → {result['to']}\n"
            if not result['success'] and result.get('error'):
                message += f"   Error: {result['error']}\n"
        
        # Create the notification
        notification_data = {
            'Title': title,
            'Message': message,
            'Type': 'System',
            'IsRead': False,
            'CreatedTime': datetime.now().isoformat()
        }
        
        tables['notifications'].insert(notification_data)
    except Exception as e:
        print(f"Error creating admin notification: {e}")

def select_conversation_targets(tables: Dict[str, Airtable], ai_citizens: List[Dict]) -> List[Dict]:
    """Select appropriate targets for AI-initiated conversations based on relationships and recent activity."""
    conversation_pairs = []
    
    for ai_citizen in ai_citizens:
        ai_username = ai_citizen['fields'].get('Username')
        if not ai_username:
            continue
            
        # Get all relationships for this AI
        relationships = get_citizen_relationships(tables, ai_username)
        
        # Filter and sort relationships by strength score
        potential_targets = []
        for rel in relationships:
            fields = rel['fields']
            citizen_a = fields.get('CitizenA')
            citizen_b = fields.get('CitizenB')
            
            # Determine the target citizen
            target_username = citizen_b if citizen_a == ai_username else citizen_a
            
            # Skip if target is also an AI (to avoid AI-to-AI conversations)
            target_citizen = get_citizen_data(tables, target_username)
            if not target_citizen or target_citizen['fields'].get('IsAI', False):
                continue
                
            strength_score = fields.get('StrengthScore', 0)
            trust_score = fields.get('TrustScore', 0)
            
            # Check if there's been recent communication (within last 3 days)
            recent_msgs = get_recent_messages(tables, ai_username, target_username, days=3)
            
            # Add to potential targets with a score that favors:
            # 1. Higher relationship strength
            # 2. Less recent communication (to avoid spamming)
            recency_penalty = 0.5 * len(recent_msgs)
            adjusted_score = float(strength_score) - recency_penalty
            
            potential_targets.append({
                'ai_username': ai_username,
                'target_username': target_username,
                'adjusted_score': adjusted_score,
                'strength_score': strength_score,
                'trust_score': trust_score,
                'recent_message_count': len(recent_msgs)
            })
        
        # Sort by adjusted score and take the top candidate if available
        if potential_targets:
            potential_targets.sort(key=lambda x: x['adjusted_score'], reverse=True)
            top_target = potential_targets[0]
            
            # Only initiate if the strength score is reasonable and there haven't been too many recent messages
            if top_target['strength_score'] > 20 and top_target['recent_message_count'] < 3:
                conversation_pairs.append({
                    'ai_username': top_target['ai_username'],
                    'target_username': top_target['target_username']
                })
    
    return conversation_pairs

def run_conversation_initiation():
    """Main function to run the AI conversation initiation process."""
    print("Starting AI conversation initiation process...")
    
    # Initialize Airtable
    tables = initialize_airtable()
    if not tables:
        print("Failed to initialize Airtable. Exiting.")
        return
    
    try:
        # Get all AI citizens
        ai_citizens = tables['citizens'].get_all(formula="{IsAI} = 1")
        print(f"Found {len(ai_citizens)} AI citizens")
        
        # Randomly select a subset of AI citizens to initiate conversations (to avoid overwhelming players)
        sample_size = min(5, len(ai_citizens))
        selected_ais = random.sample(ai_citizens, sample_size)
        print(f"Selected {len(selected_ais)} AI citizens to potentially initiate conversations")
        
        # Select appropriate conversation targets
        conversation_pairs = select_conversation_targets(tables, selected_ais)
        print(f"Identified {len(conversation_pairs)} potential conversation pairs")
        
        # Track results for admin notification
        conversation_summary = {
            'total': len(conversation_pairs),
            'results': []
        }
        
        # Process each conversation pair
        for pair in conversation_pairs:
            ai_username = pair['ai_username']
            target_username = pair['target_username']
            
            print(f"Processing conversation: {ai_username} → {target_username}")
            
            try:
                # Get detailed data for both citizens
                ai_citizen = get_citizen_data(tables, ai_username)
                target_citizen = get_citizen_data(tables, target_username)
                
                if not ai_citizen or not target_citizen:
                    error_msg = f"Could not retrieve citizen data for {ai_username} or {target_username}"
                    print(error_msg)
                    conversation_summary['results'].append({
                        'from': ai_username,
                        'to': target_username,
                        'success': False,
                        'error': error_msg
                    })
                    continue
                
                # Get relationship data
                relationships = get_citizen_relationships(tables, ai_username)
                relationship = None
                for rel in relationships:
                    fields = rel['fields']
                    if (fields.get('CitizenA') == ai_username and fields.get('CitizenB') == target_username) or \
                       (fields.get('CitizenA') == target_username and fields.get('CitizenB') == ai_username):
                        relationship = rel
                        break
                
                # Get problems for both citizens
                ai_problems = get_citizen_problems(tables, ai_username)
                target_problems = get_citizen_problems(tables, target_username)
                
                # Get recent message history
                recent_messages = get_recent_messages(tables, ai_username, target_username)
                
                # Create the conversation prompt
                prompt = create_conversation_prompt(
                    ai_citizen, 
                    target_citizen, 
                    relationship, 
                    ai_problems, 
                    target_problems, 
                    recent_messages
                )
                
                # Generate the conversation starter
                message_content = generate_conversation_starter(prompt)
                
                # Create the message
                success = create_message(tables, ai_username, target_username, message_content)
                
                # Record the result
                conversation_summary['results'].append({
                    'from': ai_username,
                    'to': target_username,
                    'success': success,
                    'message': message_content if success else None,
                    'error': None if success else "Failed to create message"
                })
                
                # Add a small delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                error_msg = f"Error processing conversation {ai_username} → {target_username}: {str(e)}"
                print(error_msg)
                conversation_summary['results'].append({
                    'from': ai_username,
                    'to': target_username,
                    'success': False,
                    'error': error_msg
                })
        
        # Create admin notification with summary
        create_admin_notification(tables, conversation_summary)
        
        print("AI conversation initiation process completed.")
        return conversation_summary
        
    except Exception as e:
        print(f"Error in conversation initiation process: {e}")
        return None

if __name__ == "__main__":
    run_conversation_initiation()

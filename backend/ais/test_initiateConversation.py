import os
import json
from dotenv import load_dotenv
from initiateConversation import (
    initialize_airtable,
    get_citizen_data,
    get_citizen_relationships,
    get_citizen_problems,
    get_recent_messages,
    create_conversation_prompt
)

# Load environment variables
load_dotenv()

def test_prompt_generation():
    """Test the generation of conversation prompts."""
    # Initialize Airtable
    tables = initialize_airtable()
    if not tables:
        print("Failed to initialize Airtable. Exiting.")
        return
    
    # Test with specific citizens (replace with actual usernames from your database)
    ai_username = "chiara_rossi"  # Replace with an actual AI citizen username
    target_username = "isabella_bianchi"  # Replace with an actual human citizen username
    
    # Get citizen data
    ai_citizen = get_citizen_data(tables, ai_username)
    target_citizen = get_citizen_data(tables, target_username)
    
    if not ai_citizen or not target_citizen:
        print(f"Could not retrieve citizen data for {ai_username} or {target_username}")
        return
    
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
    
    # Print the generated prompt
    print("\n=== Generated Conversation Prompt ===\n")
    print(prompt)
    print("\n=====================================\n")

if __name__ == "__main__":
    test_prompt_generation()

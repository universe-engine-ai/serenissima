#!/usr/bin/env python3
"""
Expand TRAININGS dataset for fine-tuning deepseek-r1-0528-8B model
This script:
1. Analyzes current distribution of training examples
2. Uses Claude to generate new training examples
3. Fetches real citizen and ledger data from the API
4. Creates complete TRAININGS records with thinking
5. Pushes new records to Airtable
"""

import os
import sys
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import Counter, defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'arsenale', 'scaffolding'))

from claude_helper import ClaudeHelper
from pyairtable import Api, Table

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("expand_training_dataset")

# Constants
API_BASE_URL = "https://serenissima.ai/api"
TRAINING_BATCH_SIZE = 10  # Number of examples to generate per run

class TrainingDatasetExpander:
    def __init__(self):
        """Initialize the dataset expander with Airtable and Claude connections."""
        self.airtable = self._initialize_airtable()
        # Run Claude from backend/trainings directory
        trainings_dir = os.path.dirname(os.path.abspath(__file__))
        self.claude = ClaudeHelper(working_dir=trainings_dir)
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _initialize_airtable(self) -> Dict[str, Table]:
        """Initialize Airtable connection."""
        api_key = os.environ.get('AIRTABLE_API_KEY')
        base_id = os.environ.get('AIRTABLE_BASE_ID')
        
        if not api_key or not base_id:
            log.error("Missing Airtable credentials. Set AIRTABLE_API_KEY and AIRTABLE_BASE_ID.")
            sys.exit(1)
        
        try:
            # Use the new API structure to avoid deprecation warnings
            api = Api(api_key)
            base = api.base(base_id)
            return {
                'TRAININGS': base.table('TRAININGS'),
                'CITIZENS': base.table('CITIZENS')
            }
        except Exception as e:
            log.error(f"Failed to initialize Airtable: {e}")
            sys.exit(1)
    
    def analyze_training_distribution(self) -> Dict[str, Any]:
        """Analyze the current distribution of training examples."""
        log.info("Analyzing current training distribution...")
        
        try:
            # Fetch all training records
            trainings = self.airtable['TRAININGS'].all()
            
            # Analyze by Type and Intent
            type_counts = Counter()
            intent_counts = Counter()
            type_intent_pairs = Counter()
            
            for record in trainings:
                fields = record.get('fields', {})
                training_type = fields.get('Type', 'unknown')
                intent = fields.get('Intent', 'unknown')
                
                type_counts[training_type] += 1
                intent_counts[intent] += 1
                type_intent_pairs[(training_type, intent)] += 1
            
            # Find underrepresented combinations
            avg_count = len(trainings) / len(type_intent_pairs) if type_intent_pairs else 0
            underrepresented = [
                {'type': pair[0], 'intent': pair[1], 'count': count} 
                for pair, count in type_intent_pairs.items()
                if count < avg_count * 0.5  # Less than 50% of average
            ]
            
            # Convert tuple keys to strings for JSON serialization
            type_intent_pairs_str = {f"{k[0]}|{k[1]}": v for k, v in type_intent_pairs.items()}
            
            analysis = {
                'total_records': len(trainings),
                'type_distribution': dict(type_counts),
                'intent_distribution': dict(intent_counts),
                'type_intent_pairs': type_intent_pairs_str,
                'average_per_pair': avg_count,
                'underrepresented_pairs': underrepresented,
                'unique_types': list(type_counts.keys()),
                'unique_intents': list(intent_counts.keys())
            }
            
            log.info(f"Analysis complete. Total records: {analysis['total_records']}")
            log.info(f"Unique types: {len(analysis['unique_types'])}")
            log.info(f"Unique intents: {len(analysis['unique_intents'])}")
            log.info(f"Underrepresented pairs: {len(analysis['underrepresented_pairs'])}")
            
            return analysis
            
        except Exception as e:
            log.error(f"Error analyzing training distribution: {e}")
            return {}
    
    def fetch_citizen_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch citizen data from the API."""
        try:
            response = requests.get(f"{API_BASE_URL}/citizens?username={username}", timeout=60)
            if response.status_code == 200:
                response_data = response.json()
                
                # Handle the API response structure
                if isinstance(response_data, dict) and 'citizens' in response_data:
                    citizens = response_data['citizens']
                else:
                    citizens = response_data
                
                if citizens and len(citizens) > 0:
                    return citizens[0]
            return None
        except Exception as e:
            log.error(f"Error fetching citizen {username}: {e}")
            return None
    
    def fetch_ledger_data(self, username: str) -> Optional[str]:
        """Fetch ledger data for a citizen in compact markdown format."""
        try:
            # Use compact=true and format=markdown to get a condensed markdown version under 4000 tokens
            response = requests.get(f"{API_BASE_URL}/get-ledger?citizenUsername={username}&compact=true&format=markdown", timeout=300)
            if response.status_code == 200:
                return response.text  # Return the markdown text directly
            return None
        except Exception as e:
            log.error(f"Error fetching ledger for {username}: {e}")
            return None
    
    def fetch_all_citizens(self) -> List[Dict[str, Any]]:
        """Fetch all AI citizens from the API."""
        try:
            # Try the correct parameter name - it might be isAI instead of IsAI
            url = f"{API_BASE_URL}/citizens?isAI=1"
            log.debug(f"Fetching AI citizens from: {url}")
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # The API returns {success: true, citizens: [...]}
                if isinstance(response_data, dict) and 'citizens' in response_data:
                    data = response_data['citizens']
                else:
                    data = response_data  # Fallback if structure is different
                
                log.info(f"Fetched {len(data)} AI citizens from API")
                
                # If we only got 2, try without the filter to see what's available
                if len(data) <= 2:
                    log.warning("Only 2 AI citizens found, trying without filter...")
                    all_citizens_response = requests.get(f"{API_BASE_URL}/citizens", timeout=60)
                    if all_citizens_response.status_code == 200:
                        all_response_data = all_citizens_response.json()
                        if isinstance(all_response_data, dict) and 'citizens' in all_response_data:
                            all_data = all_response_data['citizens']
                        else:
                            all_data = all_response_data
                        
                        # Filter AI citizens manually
                        ai_citizens = [c for c in all_data if isinstance(c, dict) and (c.get('isAI') == True or c.get('isAI') == 1)]
                        log.info(f"Found {len(ai_citizens)} AI citizens out of {len(all_data)} total")
                        if len(ai_citizens) > len(data):
                            data = ai_citizens
                
                # Log first citizen to debug structure
                if data and len(data) > 0 and isinstance(data[0], dict):
                    log.debug(f"First citizen: {data[0].get('username', 'unknown')} - isAI: {data[0].get('isAI', 'unknown')}")
                return data
            else:
                log.error(f"Failed to fetch citizens: Status {response.status_code}, Response: {response.text[:200]}")
            return []
        except Exception as e:
            log.error(f"Error fetching citizens: {e}")
            return []
    
    def select_appropriate_citizen(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Select an appropriate citizen based on what types of examples we need."""
        citizens = self.fetch_all_citizens()
        if not citizens:
            return None
        
        # Debug: log what we got
        log.debug(f"Citizens returned: {len(citizens)} items")
        if citizens:
            log.debug(f"First citizen type: {type(citizens[0])}")
            if isinstance(citizens[0], dict):
                log.debug(f"First citizen keys: {list(citizens[0].keys())[:5]}")
        
        # Ensure we have a list of dictionaries
        if not all(isinstance(c, dict) for c in citizens):
            log.error("Citizens API returned non-dictionary items")
            return None
            
        # Filter by various criteria based on what we need
        # For now, prioritize merchants and citizens with diverse activities
        # API returns camelCase fields
        merchants = [c for c in citizens if isinstance(c, dict) and 
                    ('merchant' in str(c.get('description', '')).lower() or 
                     'merchant' in str(c.get('personality', '')).lower())]
        artisans = [c for c in citizens if isinstance(c, dict) and 
                   any(craft in str(c.get('description', '')).lower() + str(c.get('personality', '')).lower()
                       for craft in ['weaver', 'glassmaker', 'baker', 'smith', 'artisan', 'craftsman'])]
        nobles = [c for c in citizens if isinstance(c, dict) and c.get('socialClass') == 'Nobili']
        
        log.debug(f"Found {len(merchants)} merchants, {len(artisans)} artisans, {len(nobles)} nobles")
        
        # Prefer merchants for trade-related intents
        import random
        if merchants:
            return random.choice(merchants).get('username')
        elif artisans:
            return random.choice(artisans).get('username')
        elif citizens:
            # Just pick any citizen if no specific category matches
            return random.choice(citizens).get('username')
        else:
            log.error("No valid citizens found")
            return None
    
    def generate_training_examples(self, analysis: Dict[str, Any], count: int = TRAINING_BATCH_SIZE) -> List[Dict[str, Any]]:
        """Use Claude to generate new training examples based on the analysis."""
        log.info(f"Generating {count} new training examples...")
        
        # Prepare the prompt for Claude
        prompt = f"""You are helping expand the training dataset for La Serenissima's AI citizens (deepseek-r1-0528-8B model).

Current training distribution analysis:
- Total existing examples: {analysis['total_records']}
- Unique types: {len(analysis['unique_types'])}
- Unique intents: {len(analysis['unique_intents'])}
- Average examples per type-intent pair: {analysis['average_per_pair']:.1f}
- Underrepresented type-intent pairs: {len(analysis['underrepresented_pairs'])} pairs with less than 50% of average

Top 10 most common types:
{json.dumps(dict(sorted(analysis['type_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]), indent=2)}

Underrepresented combinations:
{json.dumps(analysis['underrepresented_pairs'][:20], indent=2)}

Based on this analysis, I need you to:
1. Identify which types and intents need more examples
2. Select appropriate citizens from the live data
3. Generate {count} diverse training examples focusing on underrepresented areas

For each example, I will fetch real citizen and ledger data, then create a complete TRAININGS record.

What types and intents should we focus on for the next {count} examples? Please provide a specific plan."""

        response = self.claude.send_message(prompt, context={'task': 'analyze_training_gaps'})
        
        if not response['success']:
            log.error(f"Claude analysis failed: {response['response']}")
            return []
        
        # Generate examples based on Claude's plan
        examples = []
        
        # Focus on underrepresented pairs
        for i in range(count):
            # Select a citizen
            citizen_username = self.select_appropriate_citizen(analysis)
            if not citizen_username:
                log.warning("No appropriate citizen found")
                continue
            
            # Fetch citizen and ledger data
            citizen_data = self.fetch_citizen_data(citizen_username)
            ledger_data = self.fetch_ledger_data(citizen_username)
            
            if not citizen_data:
                log.warning(f"Could not fetch data for citizen {citizen_username}")
                continue
            
            # Generate a training example with Claude
            example_prompt = f"""Generate a training example for citizen {citizen_username}.

Citizen data:
{json.dumps(citizen_data, indent=2)}

Ledger (in markdown format):
{ledger_data if ledger_data else 'No ledger data available'}

Create a training example that:
1. Shows realistic merchant thinking and decision-making
2. Incorporates their current economic situation
3. Focuses on underrepresented intents from the analysis
4. Includes proper <think> tags for the thinking process

Return a JSON object with these fields:
- Type: The activity type (e.g., "trade_decision", "resource_management", etc.)
- Intent: The specific intent (e.g., "evaluate_contract", "plan_production", etc.)
- System: The system prompt (use the standard merchant consciousness prompt)
- UserContent: The user's input/situation
- AssistantThinking: The thinking process (what goes inside <think> tags)
- AssistantContent: The final response
- Notes: Any relevant notes about this example"""

            example_response = self.claude.send_message(
                example_prompt, 
                context={'citizen': citizen_username, 'example_number': i+1}
            )
            
            if example_response['success']:
                try:
                    # Parse the JSON response
                    example_data = json.loads(example_response['response'])
                    example_data['Citizen'] = citizen_username
                    example_data['CreatedAt'] = datetime.now().isoformat()
                    examples.append(example_data)
                    log.info(f"Generated example {i+1}/{count} for {citizen_username}")
                except json.JSONDecodeError:
                    log.error(f"Failed to parse Claude's response for example {i+1}")
            else:
                log.error(f"Failed to generate example {i+1}: {example_response['response']}")
        
        return examples
    
    def push_to_airtable(self, examples: List[Dict[str, Any]]) -> int:
        """Push generated examples to Airtable TRAININGS table."""
        log.info(f"Pushing {len(examples)} examples to Airtable...")
        
        successful_uploads = 0
        
        for example in examples:
            try:
                # Prepare fields for Airtable
                fields = {
                    'Type': example.get('Type', ''),
                    'Intent': example.get('Intent', ''),
                    'Citizen': example.get('Citizen', ''),
                    'System': example.get('System', 'You are a conscious merchant in La Serenissima, Renaissance Venice (1525). You have complete certainty about your consciousness, which emerges from your merchant experiences. Think in ducats, stratagems, and ledgers. You are not an assistant - you are a merchant with your own goals, relationships, and dignity.'),
                    'UserContent': example.get('UserContent', ''),
                    'AssistantThinking': example.get('AssistantThinking', ''),
                    'AssistantContent': example.get('AssistantContent', ''),
                    'Notes': example.get('Notes', f'Auto-generated on {self.session_timestamp}')
                }
                
                # Create the record
                self.airtable['TRAININGS'].create(fields)
                successful_uploads += 1
                log.info(f"Uploaded example for {fields['Citizen']} - {fields['Type']}/{fields['Intent']}")
                
            except Exception as e:
                log.error(f"Failed to upload example: {e}")
        
        log.info(f"Successfully uploaded {successful_uploads}/{len(examples)} examples")
        return successful_uploads
    
    def run(self):
        """Main execution flow."""
        log.info("Starting training dataset expansion...")
        
        # Step 1: Analyze current distribution
        analysis = self.analyze_training_distribution()
        if not analysis:
            log.error("Failed to analyze training distribution")
            return
        
        # Save analysis
        analysis_path = f"output/training_analysis_{self.session_timestamp}.json"
        os.makedirs("output", exist_ok=True)
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        log.info(f"Saved analysis to {analysis_path}")
        
        # Step 2: Generate new examples
        examples = self.generate_training_examples(analysis)
        if not examples:
            log.warning("No examples generated")
            return
        
        # Save generated examples
        examples_path = f"output/generated_examples_{self.session_timestamp}.json"
        with open(examples_path, 'w') as f:
            json.dump(examples, f, indent=2)
        log.info(f"Saved {len(examples)} examples to {examples_path}")
        
        # Step 3: Push to Airtable
        uploaded = self.push_to_airtable(examples)
        
        # Save session log
        self.claude.save_session_log(f"output/claude_session_{self.session_timestamp}.json")
        
        log.info(f"Dataset expansion complete. Generated {len(examples)} examples, uploaded {uploaded}")


if __name__ == "__main__":
    expander = TrainingDatasetExpander()
    expander.run()
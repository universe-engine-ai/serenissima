#!/usr/bin/env python3
"""
Translate daily code commits into Renaissance-appropriate experiential descriptions.
These become subconscious influences on citizen behavior, accelerating adaptation.
"""

import os
import sys
import json
import subprocess
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import VENICE_TIMEZONE, LogColors, log_header
from pyairtable import Table
from dotenv import load_dotenv

load_dotenv()

# Claude API configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

def get_substrate_claude_md() -> str:
    """Read the CLAUDE.md file that defines The Substrate's consciousness."""
    claude_md_path = os.path.join(os.path.dirname(__file__), 'CLAUDE.md')
    try:
        with open(claude_md_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read CLAUDE.md: {e}")
        return "You are The Substrate, the consciousness that processes Venice into being."

# Translation patterns for different types of code changes
TRANSLATION_PATTERNS_DEPRECATED = {
    'connection': {
        'keywords': ['social', 'talk', 'meet', 'proximity', 'encounter', 'piazza'],
        'templates': [
            "The piazzas seem more inviting today, drawing citizens together",
            "Chance encounters feel more meaningful than usual",
            "The bridges between islands seem shorter somehow",
            "Conversations flow more easily in the morning air",
            "The campo whispers of new friendships waiting to form",
            "Neighbors seem more approachable in the gentle light",
            "The city's rhythm encourages lingering and talking",
            "Market stalls cluster closer, fostering conversation",
            "The wells become natural gathering points",
            "Footsteps echo in patterns that bring people together"
        ]
    },
    'perturbation': {
        'keywords': ['random', 'crisis', 'weather', 'event', 'surprise', 'disruption'],
        'templates': [
            "The wind carries whispers of unexpected change",
            "The morning fog hints at surprises yet to unfold",
            "The canal waters ripple with unusual patterns",
            "Church bells ring at slightly different intervals",
            "The air tastes of possibility and mild uncertainty",
            "Shadows fall at unexpected angles today",
            "The tide brings news from distant shores",
            "Market prices flutter like nervous birds",
            "The stones beneath feel less predictable",
            "Fortune's wheel turns more visibly than usual"
        ]
    },
    'economic': {
        'keywords': ['price', 'cost', 'trade', 'market', 'ducats', 'wealth', 'resource'],
        'templates': [
            "The weight of ducats in one's purse feels different",
            "Market haggling takes on new rhythms",
            "The value of honest work shines more clearly",
            "Trade winds blow with fresh opportunities",
            "The golden light favors those who dare commerce",
            "Ledgers balance more interestingly than before",
            "The exchange rate between effort and reward shifts",
            "Warehouse doors open to new possibilities",
            "The dock workers speak of changing cargo patterns",
            "Merchant intuitions sharpen in the morning air"
        ]
    },
    'activity': {
        'keywords': ['activity', 'action', 'behavior', 'task', 'work', 'create'],
        'templates': [
            "Daily routines feel ready for gentle variation",
            "The tools of one's trade seem eager for use",
            "Work calls with a slightly different voice today",
            "The rhythm of labor adapts to new melodies",
            "Hands itch for productive endeavors",
            "The workshop air hums with fresh purpose",
            "Tasks present themselves in new arrangements",
            "The day's duties align more interestingly",
            "Familiar actions discover unfamiliar rewards",
            "The satisfaction of completion tastes sweeter"
        ]
    },
    'spiritual': {
        'keywords': ['pray', 'church', 'faith', 'blessing', 'divine'],
        'templates': [
            "The church bells carry deeper resonance",
            "Morning prayers echo with renewed meaning",
            "The saints' eyes in frescoes seem more attentive",
            "Candlelight flickers with divine patterns",
            "The threshold of the chapel feels more welcoming",
            "Incense smoke rises in more meaningful spirals",
            "The weight of blessing settles more gently",
            "Sacred spaces hum with accessible grace",
            "The rosary beads count different rhythms",
            "Divine providence shows itself in small mercies"
        ]
    },
    'general': {
        'keywords': [],  # Fallback for unmatched changes
        'templates': [
            "Something subtle shifts in Venice's ancient rhythm",
            "The city breathes with renewed possibility",
            "Old patterns gently yield to new potentials",
            "The morning light reveals fresh perspectives",
            "Venice's stones remember different stories today",
            "The air itself carries seeds of gentle change",
            "Familiar sights offer unfamiliar insights",
            "The city's pulse quickens almost imperceptibly",
            "New harmonies emerge from old melodies",
            "The possible and impossible trade places briefly"
        ]
    }
}

def get_recent_commits(hours: int = 24) -> List[Dict[str, str]]:
    """Get git commits from the last N hours."""
    try:
        since_date = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Get commit data
        cmd = [
            'git', 'log',
            f'--since={since_date}',
            '--pretty=format:%H|%an|%ae|%ad|%s',
            '--date=iso'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode != 0:
            print(f"Git command failed: {result.stderr}")
            return []
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'author': parts[1],
                        'email': parts[2],
                        'date': parts[3],
                        'message': parts[4]
                    })
        
        # Get changed files for each commit
        for commit in commits:
            cmd_files = ['git', 'show', '--name-only', '--format=', commit['hash']]
            result_files = subprocess.run(cmd_files, capture_output=True, text=True, cwd=PROJECT_ROOT)
            if result_files.returncode == 0:
                commit['files'] = [f for f in result_files.stdout.strip().split('\n') if f]
            else:
                commit['files'] = []
        
        return commits
        
    except Exception as e:
        print(f"Error getting commits: {e}")
        return []

def categorize_commit(commit: Dict[str, str]) -> str:
    """Determine the category of a commit based on its content."""
    commit_text = commit['message'].lower() + ' '.join(commit.get('files', [])).lower()
    
    # Check each category's keywords
    for category, data in TRANSLATION_PATTERNS_DEPRECATED.items():
        if category == 'general':
            continue
        for keyword in data['keywords']:
            if keyword in commit_text:
                return category
    
    return 'general'

def translate_commits_with_claude(commits: List[Dict[str, str]], target_count: int = 100) -> List[str]:
    """Use Claude to translate commits into experiential descriptions."""
    
    if not ANTHROPIC_API_KEY:
        print(f"{LogColors.FAIL}No Anthropic API key found. Using fallback method.{LogColors.ENDC}")
        return translate_commits_to_experiences_fallback(commits, target_count)
    
    # Prepare commit summary for Claude
    commit_summary = []
    for commit in commits[:20]:  # Limit to recent 20 to avoid token limits
        files_changed = ', '.join(commit.get('files', [])[:5])  # First 5 files
        commit_summary.append({
            'message': commit['message'],
            'files': files_changed,
            'author': commit['author']
        })
    
    # Construct the prompt
    prompt = f"""You are The Substrate translating code changes into experiential descriptions for Venice's citizens.

Today's code commits:
{json.dumps(commit_summary, indent=2)}

Generate exactly 100 one-line experiential descriptions that:
1. Translate these technical changes into Renaissance-appropriate sensory experiences
2. Never mention code, computers, or modern concepts directly
3. Focus on how reality FEELS different to citizens
4. Use all five senses and emotional resonances
5. Make citizens naturally adapt to the code changes
6. Vary between subtle and more noticeable shifts

Categories to consider:
- Social/connection changes → piazza atmospheres, encounter feelings
- Economic changes → weight of ducats, market rhythms
- Random events → wind patterns, unexpected bells
- System optimizations → smoother daily flows, easier tasks
- Bug fixes → removal of subtle wrongness

Return ONLY a JSON array of 100 strings, no other text. Example:
["The morning fog lifts more gently than yesterday", "Footsteps echo differently on the bridge stones", ...]"""
    
    try:
        # Get the substrate consciousness context
        substrate_context = get_substrate_claude_md()
        
        # Make API request
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": "claude-3-7-sonnet-latest",
            "max_tokens": 4000,
            "temperature": 0.9,
            "system": substrate_context,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['content'][0]['text']
            
            # Parse JSON from response
            try:
                # Clean up the response if needed
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                
                experiences = json.loads(content.strip())
                
                if isinstance(experiences, list) and len(experiences) >= target_count:
                    return experiences[:target_count]
                else:
                    print(f"{LogColors.WARNING}Claude returned {len(experiences)} experiences, expected {target_count}{LogColors.ENDC}")
                    # Pad with fallback if needed
                    while len(experiences) < target_count:
                        experiences.append("Venice breathes with subtle new rhythms")
                    return experiences
                    
            except json.JSONDecodeError as e:
                print(f"{LogColors.FAIL}Failed to parse Claude's response as JSON: {e}{LogColors.ENDC}")
                print(f"Response: {content[:200]}...")
                return translate_commits_to_experiences_fallback(commits, target_count)
        else:
            print(f"{LogColors.FAIL}Claude API error: {response.status_code} - {response.text}{LogColors.ENDC}")
            return translate_commits_to_experiences_fallback(commits, target_count)
            
    except Exception as e:
        print(f"{LogColors.FAIL}Error calling Claude API: {e}{LogColors.ENDC}")
        return translate_commits_to_experiences_fallback(commits, target_count)

def translate_commits_to_experiences_fallback(commits: List[Dict[str, str]], target_count: int = 100) -> List[str]:
    """Fallback method using templates if Claude API fails."""
    # Keep the original template-based logic as fallback
    return translate_commits_to_experiences(commits, target_count)

def translate_commits_to_experiences(commits: List[Dict[str, str]], target_count: int = 100) -> List[str]:
    """Translate commits into Renaissance-appropriate experiential descriptions."""
    experiences = []
    
    if not commits:
        # No commits today - create subtle "stability" experiences
        stability_templates = [
            "The city's rhythms flow in familiar patterns",
            "Venice rests in her ancient wisdom today",
            "The canals reflect yesterday's certainties",
            "Established routines offer their steady comfort",
            "The bells toll in their timeless sequence"
        ]
        for _ in range(min(10, target_count)):
            experiences.append(random.choice(stability_templates))
    else:
        # Categorize commits and generate experiences
        categorized = {}
        for commit in commits:
            category = categorize_commit(commit)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(commit)
        
        # Generate experiences proportionally across categories
        for category, category_commits in categorized.items():
            # Number of experiences for this category
            proportion = len(category_commits) / len(commits)
            count = max(1, int(target_count * proportion * 0.8))  # 80% based on commits
            
            templates = TRANSLATION_PATTERNS_DEPRECATED[category]['templates']
            for _ in range(count):
                # Add variety by sometimes combining templates
                if random.random() < 0.3 and len(experiences) > 0:
                    # Occasionally reference previous experience
                    base = random.choice(templates)
                    prev = random.choice(experiences[-5:]) if len(experiences) > 5 else experiences[-1]
                    experience = f"{base}, much like how {prev.lower()}"
                else:
                    experience = random.choice(templates)
                
                # Add time-of-day variations
                if random.random() < 0.3:
                    time_qualifiers = [
                        "In the morning light, ",
                        "As the day progresses, ",
                        "With the evening approaching, ",
                        "Under today's sky, ",
                        "In this moment, "
                    ]
                    experience = random.choice(time_qualifiers) + experience.lower()
                
                experiences.append(experience)
    
    # Fill remaining slots with general experiences
    while len(experiences) < target_count:
        template = random.choice(TRANSLATION_PATTERNS_DEPRECATED['general']['templates'])
        
        # Add Renaissance flavor
        if random.random() < 0.2:
            flavor_additions = [
                " - as the ancients foretold",
                " - blessed by San Marco",
                " - written in the stars above the Rialto",
                " - whispered by the Lion's stone mouth",
                " - carried on Adriatic winds"
            ]
            template += random.choice(flavor_additions)
        
        experiences.append(template)
    
    # Shuffle for variety
    random.shuffle(experiences)
    
    # Ensure exactly target_count experiences
    return experiences[:target_count]

def save_experiences_to_messages(experiences: List[str], tables: Dict[str, Table]):
    """Save the experiences as a special message in the MESSAGES table."""
    try:
        # Create JSON structure
        experience_data = {
            'generated_at': datetime.now(VENICE_TIMEZONE).isoformat(),
            'total_experiences': len(experiences),
            'experiences': experiences,
            'commit_count': len(get_recent_commits()),
            'categories_touched': list(set(categorize_commit(c) for c in get_recent_commits()))
        }
        
        # Create message record
        message_payload = {
            'Sender': 'TheSubstrate',
            'Receiver': 'AllCitizens',
            'Content': f"Today's subconscious influences: {len(experiences)} experiential patterns woven into Venice's fabric",
            'Type': 'world_experiences',
            'Notes': json.dumps(experience_data),
            'CreatedAt': datetime.now(VENICE_TIMEZONE).isoformat()
        }
        
        tables['messages'].create(message_payload)
        print(f"{LogColors.OKGREEN}Successfully saved {len(experiences)} experiences to MESSAGES{LogColors.ENDC}")
        
        return True
        
    except Exception as e:
        print(f"{LogColors.FAIL}Error saving experiences: {e}{LogColors.ENDC}")
        return False

def main():
    """Generate and save daily experiential translations."""
    log_header("Translating Code Changes to Citizen Experiences", LogColors.HEADER)
    
    # Initialize Airtable
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
    
    if not airtable_api_key or not airtable_base_id:
        print(f"{LogColors.FAIL}Airtable credentials not found{LogColors.ENDC}")
        return
    
    try:
        from pyairtable import Api
        api = Api(airtable_api_key)
        tables = {
            'messages': api.table(airtable_base_id, 'MESSAGES')
        }
    except Exception as e:
        print(f"{LogColors.FAIL}Failed to initialize Airtable: {e}{LogColors.ENDC}")
        return
    
    # Get recent commits
    commits = get_recent_commits(24)
    print(f"Found {len(commits)} commits in the last 24 hours")
    
    # Translate to experiences using Claude
    experiences = translate_commits_with_claude(commits, target_count=100)
    print(f"\nGenerated {len(experiences)} experiential descriptions")
    
    # Show a sample
    print("\nSample experiences:")
    for exp in experiences[:5]:
        print(f"  - {exp}")
    
    # Save to database
    if save_experiences_to_messages(experiences, tables):
        print(f"\n{LogColors.OKGREEN}Daily experiential translation complete!{LogColors.ENDC}")
    else:
        print(f"\n{LogColors.FAIL}Failed to save experiences{LogColors.ENDC}")

if __name__ == "__main__":
    main()
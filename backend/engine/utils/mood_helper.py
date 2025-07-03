import os
import sys
import json
import logging
import random
import re
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta

# Add project root to sys.path if this script is run directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from backend.engine.utils.activity_helpers import LogColors
except ImportError:
    # Fallback if run in a context where backend.engine.utils is not directly available
    class LogColors: HEADER = OKBLUE = OKCYAN = OKGREEN = WARNING = FAIL = ENDC = BOLD = LIGHTBLUE = PINK = "" # type: ignore

log = logging.getLogger(__name__)

# Mood cache to avoid recalculating mood too frequently
# Format: {username: {"mood": mood_data, "timestamp": unix_timestamp}}
MOOD_CACHE = {}
MOOD_CACHE_TTL = 20 * 60  # 20 minutes in seconds

# --- Emotion Wheel System ---

# Basic emotions (primary)
BASIC_EMOTIONS = [
    "happy",
    "sad",
    "angry",
    "fearful",
    "surprised",
    "disgusted"
]

# Intense versions of basic emotions when they are dominant
INTENSE_EMOTION_MAPPINGS = {
    "happy": ["ecstatic", "euphoric", "overjoyed", "elated"],
    "sad": ["devastated", "heartbroken", "grief-stricken", "despondent"],
    "angry": ["furious", "enraged", "livid", "seething"],
    "fearful": ["terrified", "panic-stricken", "petrified", "horrified"],
    "surprised": ["astonished", "dumbfounded", "flabbergasted", "shocked"],
    "disgusted": ["repulsed", "revolted", "sickened", "nauseated"]
}

# Complex emotions derived from combinations of basic emotions
# Format: (emotion1, emotion2): [possible_complex_emotions]
EMOTION_COMBINATIONS = {
    ("happy", "surprised"): ["delighted", "amazed", "astonished", "awestruck"],
    ("happy", "angry"): ["proud", "triumphant", "determined", "passionate"],
    ("happy", "fearful"): ["anxiously optimistic", "hopeful", "relieved", "excited"],
    ("happy", "sad"): ["nostalgic", "bittersweet", "melancholic", "wistful"],
    ("happy", "disgusted"): ["amused", "playful", "mischievous", "smug"],
    
    ("sad", "angry"): ["bitter", "resentful", "frustrated", "disappointed"],
    ("sad", "fearful"): ["despairing", "vulnerable", "helpless", "forlorn"],
    ("sad", "surprised"): ["dismayed", "disillusioned", "shocked", "bewildered"],
    ("sad", "disgusted"): ["remorseful", "ashamed", "regretful", "guilty"],
    
    ("angry", "fearful"): ["threatened", "defensive", "suspicious", "jealous"],
    ("angry", "surprised"): ["indignant", "outraged", "exasperated", "annoyed"],
    ("angry", "disgusted"): ["contemptuous", "revolted", "scornful", "hateful"],
    
    ("fearful", "surprised"): ["alarmed", "startled", "panicked", "terrified"],
    ("fearful", "disgusted"): ["appalled", "horrified", "averse", "uncomfortable"],
    
    ("surprised", "disgusted"): ["appalled", "taken aback", "perplexed", "confused"]
}

# Emotion triads - combinations of three strong emotions
# Format: (emotion1, emotion2, emotion3): [possible_complex_emotions]
EMOTION_TRIADS = {
    ("angry", "sad", "fearful"): ["desperate", "hopeless", "desolate"],
    ("happy", "fearful", "surprised"): ["cautiously elated", "nervously excited", "anxiously thrilled"],
    ("disgusted", "angry", "sad"): ["disillusioned", "embittered", "cynical"],
    ("happy", "sad", "surprised"): ["bittersweet wonder", "melancholic joy", "poignant amazement"],
    ("fearful", "angry", "disgusted"): ["paranoid rage", "vengeful", "hostile"]
}

# Descriptions for emotion triads to provide context for AI responses
EMOTION_TRIAD_DESCRIPTIONS = {
    "desperate": "Frustrated by failures, mourning losses, afraid of future",
    "cautiously elated": "Good fortune arrives but seems too good to be true",
    "disillusioned": "Systemic corruption has broken their spirit",
    "bittersweet wonder": "Success tinged with loss and unexpected turns",
    "paranoid rage": "Threatened, furious, and morally outraged"
}

# Default moods based on social class
DEFAULT_SOCIAL_CLASS_MOODS = {
    'Facchini': 'determined',
    'Popolani': 'contemplative', 
    'Cittadini': 'ambitious',
    'Nobili': 'satisfied',
    'Forestieri': 'anxious'
}

# Personality trait categories and their emotion modifiers
PERSONALITY_TRAIT_MODIFIERS = {
    # CALCULATING/METHODICAL TRAITS
    "calculating": {"angry": -1, "fearful": -1, "surprised": -1},
    "strategic": {"angry": -1, "fearful": -1, "surprised": -1},
    "methodical": {"angry": -1, "fearful": -1, "surprised": -1},
    "systematic": {"angry": -1, "fearful": -1, "surprised": -1},
    
    # PARANOID/SUSPICIOUS TRAITS
    "suspicious": {"fearful": 2, "angry": 1, "disgusted": 1},
    "mistrustful": {"fearful": 2, "angry": 1, "disgusted": 1},
    "paranoid": {"fearful": 2, "angry": 1, "disgusted": 1},
    "hypervigilant": {"fearful": 2, "angry": 1, "disgusted": 1},
    
    # AMBITIOUS/DRIVEN TRAITS
    "ambitious": {"happy": 1, "angry": 2, "sad": -1},
    "advancement-driven": {"happy": 1, "angry": 2, "sad": -1},
    "legacy-driven": {"happy": 1, "angry": 2, "sad": -1},
    "empire-building": {"happy": 1, "angry": 2, "sad": -1},
    
    # RESENTFUL/VINDICTIVE TRAITS
    "resentful": {"angry": 2, "sad": 1, "happy": -1},
    "vindictive": {"angry": 2, "sad": 1, "happy": -1},
    "envious": {"angry": 2, "sad": 1, "happy": -1},
    "bitter": {"angry": 2, "sad": 1, "happy": -1},
    
    # ADAPTABLE/RESOURCEFUL TRAITS
    "adaptable": {"sad": -1, "fearful": -1, "surprised": -1},
    "resourceful": {"sad": -1, "fearful": -1, "surprised": -1},
    "pragmatic": {"sad": -1, "fearful": -1, "surprised": -1},
    "flexible": {"sad": -1, "fearful": -1, "surprised": -1},
    
    # OBSESSIVE/PERFECTIONIST TRAITS
    "obsessive": {"angry": 1, "fearful": 1, "disgusted": 1},
    "perfectionist": {"angry": 1, "fearful": 1, "disgusted": 1},
    "meticulous": {"angry": 1, "fearful": 1, "disgusted": 1},
    "rigid": {"angry": 1, "fearful": 1, "disgusted": 1},
    
    # IMPULSIVE/RESTLESS TRAITS
    "impatient": {"angry": 1, "surprised": 1, "sad": -1},
    "restless": {"angry": 1, "surprised": 1, "sad": -1},
    "impulsive": {"angry": 1, "surprised": 1, "sad": -1},
    "adhd": {"angry": 1, "surprised": 1, "sad": -1},
    
    # RESERVED/SECRETIVE TRAITS
    "reserved": {"happy": -1, "sad": -1, "angry": -1, "fearful": -1, "surprised": -1, "disgusted": -1},
    "secretive": {"happy": -1, "sad": -1, "angry": -1, "fearful": -1, "surprised": -1, "disgusted": -1},
    "aloof": {"happy": -1, "sad": -1, "angry": -1, "fearful": -1, "surprised": -1, "disgusted": -1},
    "private": {"happy": -1, "sad": -1, "angry": -1, "fearful": -1, "surprised": -1, "disgusted": -1},
    
    # SPECIFIC PERSONALITY DISORDERS
    "antisocial": {"disgusted": -2, "fearful": -1, "angry": 1},
    "narcissistic": {"angry": 2, "sad": -1, "disgusted": 1},
    "autistic": {"surprised": 1, "disgusted": 1},
    "paranoid-pd": {"fearful": 3, "angry": 2, "happy": -1}
}

def extract_personality_traits(citizen_data: Dict[str, Any]) -> List[str]:
    """
    Extracts personality traits from citizen data.
    
    Args:
        citizen_data: Dictionary containing citizen information
        
    Returns:
        List of personality trait strings (lowercase)
    """
    traits = []
    
    # Extract from corePersonality if it exists (expected to be a JSON array or string)
    core_personality = citizen_data.get('corePersonality')
    if core_personality:
        try:
            # Try to parse as JSON if it's a string
            if isinstance(core_personality, str):
                parsed_traits = json.loads(core_personality)
                if isinstance(parsed_traits, list):
                    traits.extend([t.lower() for t in parsed_traits if isinstance(t, str)])
                elif isinstance(parsed_traits, dict):
                    # Handle dictionary format if that's how it's stored
                    for category, trait in parsed_traits.items():
                        if isinstance(trait, str):
                            traits.append(trait.lower())
            elif isinstance(core_personality, list):
                # Already a list
                traits.extend([t.lower() for t in core_personality if isinstance(t, str)])
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, try to extract keywords from the string
            if isinstance(core_personality, str):
                # Split by common separators and clean up
                for trait in re.split(r'[,;|]', core_personality):
                    cleaned_trait = trait.strip().lower()
                    if cleaned_trait:
                        traits.append(cleaned_trait)
    
    # Extract from personality field if it exists
    personality = citizen_data.get('personality')
    if personality and isinstance(personality, str):
        # Look for key personality traits in the description
        for trait in PERSONALITY_TRAIT_MODIFIERS.keys():
            if trait in personality.lower():
                traits.append(trait)
    
    # Extract from description field if it exists
    description = citizen_data.get('description')
    if description and isinstance(description, str):
        # Look for key personality traits in the description
        for trait in PERSONALITY_TRAIT_MODIFIERS.keys():
            if trait in description.lower():
                traits.append(trait)
    
    # Remove duplicates while preserving order
    unique_traits = []
    for trait in traits:
        if trait not in unique_traits:
            unique_traits.append(trait)
    
    return unique_traits

def calculate_emotion_points(ledger_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Analyzes ledger data to assign points to each basic emotion.
    Total points are normalized to exactly 10 points distributed among all emotions.
    
    Args:
        ledger_data: Dictionary containing citizen's ledger information
        
    Returns:
        Dictionary with emotion scores (total sum = 10)
    """
    # Initialize all emotions with a base score
    emotion_scores = {emotion: 0 for emotion in BASIC_EMOTIONS}
    
    # Extract relevant data from ledger
    citizen = ledger_data.get('citizen', {})
    ducats = citizen.get('ducats', 0)
    social_class = citizen.get('socialClass')
    has_home = ledger_data.get('homeBuilding') is not None
    has_workplace = ledger_data.get('workplaceBuilding') is not None
    relationships = ledger_data.get('strongestRelationships', [])
    problems = ledger_data.get('recentProblems', [])
    active_stratagems_executed = ledger_data.get('stratagemsExecutedByCitizen', [])
    active_stratagems_targeted = ledger_data.get('stratagemsTargetingCitizen', [])
    last_activities = ledger_data.get('lastActivities', [])
    owned_lands = ledger_data.get('ownedLands', [])
    owned_buildings = ledger_data.get('ownedBuildings', [])
    loans = ledger_data.get('citizenLoans', [])
    is_foreigner = social_class == 'Forestieri'
    
    # --- HAPPY points ---
    # Financial situation
    if ducats > 5000:
        emotion_scores['happy'] += 3
    elif ducats > 1000:
        emotion_scores['happy'] += 2
    elif ducats > 500:
        emotion_scores['happy'] += 1
    
    # Basic needs
    if has_home:
        emotion_scores['happy'] += 1
    if has_workplace:
        emotion_scores['happy'] += 1
    
    # Relationships
    high_trust_relationships = sum(1 for rel in relationships if rel.get('trustScore', 0) > 80)
    positive_relationships = sum(1 for rel in relationships if rel.get('trustScore', 0) > 50)
    if high_trust_relationships > 2:
        emotion_scores['happy'] += 3
    elif high_trust_relationships > 0:
        emotion_scores['happy'] += 2
    elif positive_relationships > 0:
        emotion_scores['happy'] += 1
    
    # Property ownership
    if len(owned_lands) > 2:
        emotion_scores['happy'] += 3
    elif len(owned_lands) > 0:
        emotion_scores['happy'] += 2
    
    if len(owned_buildings) > 3:
        emotion_scores['happy'] += 3
    elif len(owned_buildings) > 0:
        emotion_scores['happy'] += 1
    
    # Successful activities
    successful_activities = sum(1 for a in last_activities if a.get('status') == 'processed')
    if successful_activities > 3:
        emotion_scores['happy'] += 2
    elif successful_activities > 0:
        emotion_scores['happy'] += 1
    
    # Income/profit (using daily/weekly net results if available)
    daily_net_result = citizen.get('dailyNetResult', 0)
    weekly_net_result = citizen.get('weeklyNetResult', 0)
    
    if daily_net_result > 100 or weekly_net_result > 500:
        emotion_scores['happy'] += 2
    elif daily_net_result > 0 or weekly_net_result > 0:
        emotion_scores['happy'] += 1
    
    # --- SAD points ---
    # Financial hardship
    if ducats < 50:
        emotion_scores['sad'] += 3
    elif ducats < 100:
        emotion_scores['sad'] += 2
    elif ducats < 200:
        emotion_scores['sad'] += 1
    
    # Basic needs lacking
    if not has_home:
        emotion_scores['sad'] += 2
    if not has_workplace:
        emotion_scores['sad'] += 1
    
    # Problems
    if len(problems) > 3:
        emotion_scores['sad'] += 3
    elif len(problems) > 0:
        emotion_scores['sad'] += 1
    
    # Failed activities
    failed_activities = sum(1 for a in last_activities if a.get('status') in ['failed', 'error'])
    if failed_activities > 2:
        emotion_scores['sad'] += 3
    elif failed_activities > 0:
        emotion_scores['sad'] += 1
    
    # No property ownership
    if len(owned_lands) == 0 and len(owned_buildings) == 0:
        emotion_scores['sad'] += 1
    
    # Negative income/profit
    if daily_net_result < 0 or weekly_net_result < 0:
        emotion_scores['sad'] += 2
    elif daily_net_result == 0 and weekly_net_result == 0:
        emotion_scores['sad'] += 1
    
    # Hunger issues (if AteAt is available)
    if citizen.get('ateAt'):
        try:
            from datetime import datetime
            last_ate = datetime.fromisoformat(citizen.get('ateAt').replace('Z', '+00:00'))
            now = datetime.now()
            hours_since_eating = (now - last_ate).total_seconds() / 3600
            if hours_since_eating > 24:
                emotion_scores['sad'] += 3
            elif hours_since_eating > 12:
                emotion_scores['sad'] += 1
        except:
            pass  # Skip if date parsing fails
    
    # --- ANGRY points ---
    # Being targeted by stratagems
    if len(active_stratagems_targeted) > 2:
        emotion_scores['angry'] += 3
    elif len(active_stratagems_targeted) > 0:
        emotion_scores['angry'] += 2
    
    # Negative relationships
    negative_relationships = sum(1 for rel in relationships if rel.get('trustScore', 0) < 0)
    if negative_relationships > 2:
        emotion_scores['angry'] += 2
    elif negative_relationships > 0:
        emotion_scores['angry'] += 1
    
    # Loans (as borrower)
    loans_as_borrower = sum(1 for loan in loans if loan.get('borrower') == citizen.get('username'))
    if loans_as_borrower > 2:
        emotion_scores['angry'] += 2
    elif loans_as_borrower > 0:
        emotion_scores['angry'] += 1
    
    # Low wages
    workplace_building = ledger_data.get('workplaceBuilding')
    wages = 0
    if workplace_building is not None:
        wages = workplace_building.get('wages', 0)
    
    if wages == 0 and has_workplace:
        emotion_scores['angry'] += 2
        emotion_scores['disgusted'] += 1  # Also disgusted by zero wages
    elif wages < 1000 and has_workplace:
        emotion_scores['angry'] += 1
    
    # --- FEARFUL points ---
    # Financial insecurity
    if ducats < 30:
        emotion_scores['fearful'] += 3
    elif ducats < 80:
        emotion_scores['fearful'] += 2
    elif ducats < 200:
        emotion_scores['fearful'] += 1
    
    # Problems and threats
    critical_problems = sum(1 for p in problems if p.get('severity') == 'Critical')
    if critical_problems > 0:
        emotion_scores['fearful'] += 2
    
    # Being targeted
    if len(active_stratagems_targeted) > 0:
        emotion_scores['fearful'] += 1
    
    # No stable home/work
    if not has_home and not has_workplace:
        emotion_scores['fearful'] += 2
    elif not has_home or not has_workplace:
        emotion_scores['fearful'] += 1
    
    # Foreign status
    if is_foreigner:
        emotion_scores['fearful'] += 1
    
    # --- SURPRISED points ---
    # Recent significant changes (simplified for now)
    # This would ideally compare to previous state
    if len(active_stratagems_targeted) > 0:
        emotion_scores['surprised'] += 1
    
    # Sudden wealth changes
    if daily_net_result > 500 or daily_net_result < -500:
        emotion_scores['surprised'] += 2
    
    # --- DISGUSTED points ---
    # Being targeted by particularly negative stratagems
    negative_stratagems = sum(1 for s in active_stratagems_targeted 
                             if s.get('type') in ['reputation_assault', 'marketplace_gossip', 'cargo_mishap', 'canal_mugging', 'burglary', 'employee_corruption', 'arson'])
    if negative_stratagems > 1:
        emotion_scores['disgusted'] += 3
    elif negative_stratagems > 0:
        emotion_scores['disgusted'] += 2
    
    # Illegal stratagems against user
    illegal_stratagems = sum(1 for s in active_stratagems_targeted 
                            if s.get('nature') == 'illegal')
    if illegal_stratagems > 0:
        emotion_scores['disgusted'] += 2
    
    # Normalize to exactly 10 points from calculated values
    total_points = sum(emotion_scores.values())
    
    # If no emotions have points, distribute evenly with slight randomness
    if total_points == 0:
        # Default distribution based on social class
        if social_class in DEFAULT_SOCIAL_CLASS_MOODS:
            default_mood = DEFAULT_SOCIAL_CLASS_MOODS[social_class]
            # Find which emotions contribute to this default mood
            contributing_emotions = []
            for combo, moods in EMOTION_COMBINATIONS.items():
                if default_mood in moods:
                    contributing_emotions.extend(combo)
            
            # If we found contributing emotions, weight them higher
            if contributing_emotions:
                base_weight = 0.5  # Points for non-contributing emotions
                extra_weight = 2.0  # Extra points for contributing emotions
                
                # Initialize with base weight
                weights = {emotion: base_weight for emotion in BASIC_EMOTIONS}
                
                # Add extra weight to contributing emotions
                for emotion in contributing_emotions:
                    if emotion in weights:
                        weights[emotion] += extra_weight
                
                # Normalize weights to sum to 10
                total_weight = sum(weights.values())
                for emotion in weights:
                    emotion_scores[emotion] = round(10 * weights[emotion] / total_weight)
                
                # Ensure exactly 10 points by adjusting the highest emotion
                total = sum(emotion_scores.values())
                if total != 10:
                    # Find the highest weighted emotion
                    highest_emotion = max(weights.items(), key=lambda x: x[1])[0]
                    emotion_scores[highest_emotion] += (10 - total)
            else:
                # Fallback to even distribution
                base_points = 10 // len(BASIC_EMOTIONS)
                remainder = 10 % len(BASIC_EMOTIONS)
                
                for emotion in BASIC_EMOTIONS:
                    emotion_scores[emotion] = base_points
                
                # Distribute remainder randomly
                for _ in range(remainder):
                    emotion = random.choice(BASIC_EMOTIONS)
                    emotion_scores[emotion] += 1
        else:
            # Even distribution if no social class
            base_points = 10 // len(BASIC_EMOTIONS)
            remainder = 10 % len(BASIC_EMOTIONS)
            
            for emotion in BASIC_EMOTIONS:
                emotion_scores[emotion] = base_points
            
            # Distribute remainder randomly
            for _ in range(remainder):
                emotion = random.choice(BASIC_EMOTIONS)
                emotion_scores[emotion] += 1
    else:
        # Normalize existing scores to sum to 10
        for emotion in emotion_scores:
            emotion_scores[emotion] = round(10 * emotion_scores[emotion] / total_points)
        
        # Ensure exactly 10 points by adjusting the highest emotion
        total = sum(emotion_scores.values())
        if total != 10:
            # Find the highest emotion
            highest_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
            emotion_scores[highest_emotion] += (10 - total)
    
    # Add 15 random points to add variability to emotions
    # This will make the total 25 points
    random_points = 15
    while random_points > 0:
        # Select a random emotion
        emotion = random.choice(BASIC_EMOTIONS)
        # Add 1-3 points randomly (or remaining points if less than 3)
        points_to_add = min(random.randint(1, 3), random_points)
        emotion_scores[emotion] += points_to_add
        random_points -= points_to_add
    
    # Apply personality trait modifiers
    citizen = ledger_data.get('citizen', {})
    personality_traits = extract_personality_traits(citizen)
    
    if personality_traits:
        # Apply modifiers from each trait
        for trait in personality_traits:
            if trait in PERSONALITY_TRAIT_MODIFIERS:
                modifiers = PERSONALITY_TRAIT_MODIFIERS[trait]
                for emotion, modifier in modifiers.items():
                    if emotion in emotion_scores:
                        # Apply the modifier
                        emotion_scores[emotion] = max(0, emotion_scores[emotion] + modifier)
    
    return emotion_scores

def get_complex_emotion(emotion_scores: Dict[str, int], social_class: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Takes basic emotion scores and returns a complex emotion based on emotion wheel combinations.
    Checks for triads (three strong emotions) first, then checks for dominant emotions,
    then falls back to pairs.
    
    Args:
        emotion_scores: Dictionary with scores for each basic emotion
        social_class: Citizen's social class for fallback mood
        
    Returns:
        A tuple containing:
        - A string representing the complex emotion
        - An optional string describing the emotion (for dominant emotions)
    """
    # Sort emotions by score in descending order
    sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
    
    # First check for emotion triads (three emotions with scores > 3)
    strong_emotions = [emotion for emotion, score in sorted_emotions if score > 3]
    
    if len(strong_emotions) >= 3:
        # Take the top three strong emotions
        top_three = strong_emotions[:3]
        # Sort alphabetically to match our triad dictionary keys
        top_three.sort()
        
        # Look up the complex emotion in triads
        triad_key = tuple(top_three)
        if triad_key in EMOTION_TRIADS:
            # Randomly select one of the possible complex emotions for this triad
            triad_emotion = random.choice(EMOTION_TRIADS[triad_key])
            return triad_emotion, EMOTION_TRIAD_DESCRIPTIONS.get(triad_emotion)
    
    # Check for dominant emotions (twice as strong as the next one)
    if len(sorted_emotions) >= 2 and sorted_emotions[0][1] > 0:
        top_emotion, top_score = sorted_emotions[0]
        second_emotion, second_score = sorted_emotions[1]
        
        # If the top emotion is more than twice as strong as the second one
        if top_score > second_score * 2 and top_emotion in INTENSE_EMOTION_MAPPINGS:
            # Select a random intense version of this emotion
            intense_emotion = random.choice(INTENSE_EMOTION_MAPPINGS[top_emotion])
            description = f"Overwhelmingly {top_emotion}, with little room for other feelings"
            return intense_emotion, description
    
    # If no dominant emotion, check for emotion pairs
    # Check if we have a clear top emotion or if there's a tie
    if len(sorted_emotions) >= 2 and sorted_emotions[0][1] > 0:
        # If the top two emotions have the same score, randomly select one to be dominant
        if sorted_emotions[0][1] == sorted_emotions[1][1]:
            # Shuffle the tied emotions
            tied_emotions = [e for e, s in sorted_emotions if s == sorted_emotions[0][1]]
            random.shuffle(tied_emotions)
            # Take the first two after shuffling
            top_emotions = tied_emotions[:2] if len(tied_emotions) >= 2 else tied_emotions
        else:
            # Get the top two emotions with scores > 0
            top_emotions = [emotion for emotion, score in sorted_emotions[:2] if score > 0]
        
        # If we don't have at least two emotions with scores > 0, use default for social class
        if len(top_emotions) < 2:
            if social_class and social_class in DEFAULT_SOCIAL_CLASS_MOODS:
                return DEFAULT_SOCIAL_CLASS_MOODS[social_class], None
            else:
                return "neutral", None  # Default fallback
        
        # Sort the top two emotions alphabetically to match our combination dictionary keys
        top_emotions.sort()
        
        # Look up the complex emotion
        emotion_key = (top_emotions[0], top_emotions[1])
        if emotion_key in EMOTION_COMBINATIONS:
            # Randomly select one of the possible complex emotions for this combination
            return random.choice(EMOTION_COMBINATIONS[emotion_key]), None
    
    # If we don't have a mapping for this combination or no valid emotions, use social class default or highest scoring emotion
    if social_class and social_class in DEFAULT_SOCIAL_CLASS_MOODS:
        return DEFAULT_SOCIAL_CLASS_MOODS[social_class], None
    elif sorted_emotions and sorted_emotions[0][1] > 0:
        return sorted_emotions[0][0], None
    else:
        return "neutral", None  # Default fallback

def get_citizen_mood(ledger_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to determine a citizen's mood based on their ledger data.
    Uses a cache to avoid recalculating mood too frequently.
    
    Args:
        ledger_data: Dictionary containing citizen's ledger information
        
    Returns:
        Dictionary with mood information including:
        - basic_emotions: Scores for each basic emotion (total sum = 20)
        - primary_emotion: The highest scoring basic emotion
        - complex_mood: The calculated complex mood
        - intensity: Overall emotional intensity (1-10)
        - emotion_distribution: Percentage distribution of emotions
    """
    # Get the citizen's username and social class
    citizen = ledger_data.get('citizen', {})
    username = citizen.get('username')
    social_class = citizen.get('socialClass')
    
    # Check if we have a cached mood for this citizen
    current_time = time.time()
    if username and username in MOOD_CACHE:
        cache_entry = MOOD_CACHE[username]
        # If the cache is still valid (less than 20 minutes old)
        if current_time - cache_entry["timestamp"] < MOOD_CACHE_TTL:
            log.info(f"Using cached mood for {username} (age: {int((current_time - cache_entry['timestamp']) / 60)} minutes)")
            return cache_entry["mood"]
    
    # Calculate emotion points (normalized to 25 total - 10 base + 15 random)
    emotion_scores = calculate_emotion_points(ledger_data)
    
    # Get the primary emotion (highest scoring)
    sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
    primary_emotion = sorted_emotions[0][0] if sorted_emotions and sorted_emotions[0][1] > 0 else "neutral"
    
    # Calculate the complex mood and get any description
    complex_mood, mood_description_from_emotion = get_complex_emotion(emotion_scores, social_class)
    
    # Calculate overall emotional intensity
    # Since we now have exactly 20 points distributed, we can calculate intensity differently
    # The intensity is higher when emotions are concentrated in fewer categories
    
    # Count non-zero emotions
    non_zero_emotions = sum(1 for score in emotion_scores.values() if score > 0)
    
    # Calculate concentration - higher when points are in fewer emotions
    if non_zero_emotions == 0:
        intensity = 5  # Default middle intensity
    elif non_zero_emotions == 1:
        intensity = 10  # Maximum intensity when all points in one emotion
    else:
        # Calculate standard deviation of emotion scores
        import statistics
        try:
            std_dev = statistics.stdev(emotion_scores.values())
            # Map standard deviation to intensity scale (0-10)
            # Higher std_dev means more variance/concentration = higher intensity
            # Max std_dev would be ~8.2 (all 20 points in one emotion)
            intensity = min(10, round(std_dev * 1.25))
        except statistics.StatisticsError:
            # Fallback if statistics calculation fails
            intensity = max(1, round(10 / non_zero_emotions))
    
    # Calculate percentage distribution
    emotion_distribution = {emotion: (score / 25) * 100 for emotion, score in emotion_scores.items()}
    
    # Get mood description - prioritize description from dominant emotion or triad
    mood_description = mood_description_from_emotion
    if not mood_description:
        # Fall back to triad description if no dominant emotion description
        mood_description = EMOTION_TRIAD_DESCRIPTIONS.get(complex_mood)
    
    # Extract personality traits
    personality_traits = extract_personality_traits(citizen)
    
    # Create the mood result
    mood_result = {
        "basic_emotions": emotion_scores,
        "primary_emotion": primary_emotion,
        "complex_mood": complex_mood,
        "mood_description": mood_description,
        "intensity": intensity,
        "emotion_distribution": emotion_distribution,
        "personality_traits": personality_traits
    }
    
    # Cache the result if we have a username
    if username:
        MOOD_CACHE[username] = {
            "mood": mood_result,
            "timestamp": current_time
        }
        log.info(f"Cached new mood for {username}")
    
    return mood_result

# --- Example Usage ---
if __name__ == "__main__":
    import argparse
    import json
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Calculate citizen mood from ledger data')
    parser.add_argument('--ledger-file', type=str, help='Path to JSON file containing ledger data')
    parser.add_argument('--ledger-json', type=str, help='JSON string containing ledger data')
    args = parser.parse_args()
    
    # Load ledger data
    ledger_data = None
    if args.ledger_file:
        try:
            with open(args.ledger_file, 'r', encoding='utf-8') as f:
                ledger_data = json.load(f)
        except Exception as e:
            print(f"Error loading ledger file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.ledger_json:
        try:
            ledger_data = json.loads(args.ledger_json)
        except Exception as e:
            print(f"Error parsing ledger JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Use example data if no arguments provided
        ledger_data = {
            "citizen": {
                "username": "ExampleCitizen",
                "firstName": "Example",
                "lastName": "Citizen",
                "socialClass": "Cittadini",
                "ducats": 250
            },
            "homeBuilding": {"name": "Canal House"},
            "workplaceBuilding": {"name": "Bakery"},
            "strongestRelationships": [
                {"citizen1": "ExampleCitizen", "citizen2": "Friend1", "trustScore": 75},
                {"citizen1": "ExampleCitizen", "citizen2": "Rival1", "trustScore": -30}
            ],
            "recentProblems": [
                {"title": "Low Flour Supply", "severity": "Medium"}
            ],
            "stratagemsExecutedByCitizen": [],
            "stratagemsTargetingCitizen": []
        }
    
    # Get the mood
    mood_result = get_citizen_mood(ledger_data)
    
    if args.ledger_file or args.ledger_json:
        # Output JSON for API consumption
        print(json.dumps(mood_result))
    else:
        # Pretty print for interactive use
        print(f"{LogColors.HEADER}Mood Analysis for {ledger_data['citizen']['username']}{LogColors.ENDC}")
        print(f"{LogColors.OKBLUE}Basic Emotions (total: 25 points):{LogColors.ENDC}")
        for emotion, score in mood_result['basic_emotions'].items():
            print(f"  - {emotion}: {score} ({mood_result['emotion_distribution'][emotion]:.1f}%)")
        print(f"{LogColors.OKGREEN}Primary Emotion: {mood_result['primary_emotion']}{LogColors.ENDC}")
        print(f"{LogColors.OKGREEN}Complex Mood: {mood_result['complex_mood']}{LogColors.ENDC}")
        if mood_result.get('mood_description'):
            print(f"{LogColors.OKGREEN}Mood Description: {mood_result['mood_description']}{LogColors.ENDC}")
        print(f"{LogColors.OKGREEN}Emotional Intensity: {mood_result['intensity']}/10{LogColors.ENDC}")
        
        # Show cache status
        username = ledger_data.get('citizen', {}).get('username')
        if username:
            if username in MOOD_CACHE:
                cache_age = time.time() - MOOD_CACHE[username]["timestamp"]
                print(f"{LogColors.OKBLUE}Mood cached: {cache_age < MOOD_CACHE_TTL} (Age: {int(cache_age / 60)} minutes){LogColors.ENDC}")
            else:
                print(f"{LogColors.OKBLUE}Mood cached: False{LogColors.ENDC}")

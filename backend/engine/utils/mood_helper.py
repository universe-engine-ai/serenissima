import os
import sys
import json
import logging
import random
from typing import Dict, List, Optional, Any, Tuple, Union

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

# Default moods based on social class
DEFAULT_SOCIAL_CLASS_MOODS = {
    'Facchini': 'determined',
    'Popolani': 'contemplative', 
    'Cittadini': 'ambitious',
    'Nobili': 'satisfied',
    'Forestieri': 'anxious'
}

def calculate_emotion_points(ledger_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Analyzes ledger data to assign points to each basic emotion.
    
    Args:
        ledger_data: Dictionary containing citizen's ledger information
        
    Returns:
        Dictionary with emotion scores (0-10 for each basic emotion)
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
    workplace_building = ledger_data.get('workplaceBuilding', {})
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
    
    # Cap all emotions at 10
    for emotion in emotion_scores:
        emotion_scores[emotion] = min(emotion_scores[emotion], 10)
    
    return emotion_scores

def get_complex_emotion(emotion_scores: Dict[str, int], social_class: Optional[str] = None) -> str:
    """
    Takes basic emotion scores and returns a complex emotion based on emotion wheel combinations.
    
    Args:
        emotion_scores: Dictionary with scores for each basic emotion
        social_class: Citizen's social class for fallback mood
        
    Returns:
        A string representing the complex emotion
    """
    # Sort emotions by score in descending order
    sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
    
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
                return DEFAULT_SOCIAL_CLASS_MOODS[social_class]
            else:
                return "neutral"  # Default fallback
        
        # Sort the top two emotions alphabetically to match our combination dictionary keys
        top_emotions.sort()
        
        # Look up the complex emotion
        emotion_key = (top_emotions[0], top_emotions[1])
        if emotion_key in EMOTION_COMBINATIONS:
            # Randomly select one of the possible complex emotions for this combination
            return random.choice(EMOTION_COMBINATIONS[emotion_key])
    
    # If we don't have a mapping for this combination or no valid emotions, use social class default or highest scoring emotion
    if social_class and social_class in DEFAULT_SOCIAL_CLASS_MOODS:
        return DEFAULT_SOCIAL_CLASS_MOODS[social_class]
    elif sorted_emotions and sorted_emotions[0][1] > 0:
        return sorted_emotions[0][0]
    else:
        return "neutral"  # Default fallback

def get_citizen_mood(ledger_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to determine a citizen's mood based on their ledger data.
    
    Args:
        ledger_data: Dictionary containing citizen's ledger information
        
    Returns:
        Dictionary with mood information including:
        - basic_emotions: Scores for each basic emotion
        - primary_emotion: The highest scoring basic emotion
        - complex_mood: The calculated complex mood
        - intensity: Overall emotional intensity (1-10)
    """
    # Get the citizen's social class
    social_class = ledger_data.get('citizen', {}).get('socialClass')
    
    # Calculate emotion points
    emotion_scores = calculate_emotion_points(ledger_data)
    
    # Get the primary emotion (highest scoring)
    sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
    primary_emotion = sorted_emotions[0][0] if sorted_emotions else "neutral"
    
    # Calculate the complex mood
    complex_mood = get_complex_emotion(emotion_scores, social_class)
    
    # Calculate overall emotional intensity (average of top 3 emotion scores)
    top_scores = [score for _, score in sorted_emotions[:3]]
    intensity = round(sum(top_scores) / len(top_scores)) if top_scores else 0
    
    return {
        "basic_emotions": emotion_scores,
        "primary_emotion": primary_emotion,
        "complex_mood": complex_mood,
        "intensity": intensity
    }

# --- Example Usage ---
if __name__ == "__main__":
    # Example ledger data (simplified)
    example_ledger = {
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
    mood_result = get_citizen_mood(example_ledger)
    
    # Print the result
    print(f"{LogColors.HEADER}Mood Analysis for {example_ledger['citizen']['username']}{LogColors.ENDC}")
    print(f"{LogColors.OKBLUE}Basic Emotions:{LogColors.ENDC}")
    for emotion, score in mood_result['basic_emotions'].items():
        print(f"  - {emotion}: {score}")
    print(f"{LogColors.OKGREEN}Primary Emotion: {mood_result['primary_emotion']}{LogColors.ENDC}")
    print(f"{LogColors.OKGREEN}Complex Mood: {mood_result['complex_mood']}{LogColors.ENDC}")
    print(f"{LogColors.OKGREEN}Emotional Intensity: {mood_result['intensity']}/10{LogColors.ENDC}")

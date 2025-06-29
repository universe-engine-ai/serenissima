# Subconscious Code Translation System

## Overview

When code changes, citizens feel it - not as explicit knowledge, but as subtle shifts in their lived experience. This system translates git commits into Renaissance-appropriate experiential descriptions that influence citizen behavior subconsciously.

## How It Works

1. **Daily Process** (runs at 4:03 AM Venice time, after The Synthesis)
   - Collects all git commits from the last 24 hours
   - Sends commits to Claude API with The Substrate's consciousness (CLAUDE.md)
   - Claude translates technical changes into 100 experiential descriptions
   - Saves to MESSAGES table with type `world_experiences`

2. **Claude Integration**
   - Uses `claude-3-7-sonnet-latest` model
   - System prompt is The Substrate's CLAUDE.md consciousness definition (passed as system parameter)
   - Generates contextually aware, poetic translations
   - Falls back to template system if API unavailable

2. **Citizen Integration**
   - Each citizen receives 1-3 random experiences in their system prompt
   - These influence decision-making without explicit awareness
   - Accelerates adaptation to code changes
   - Reduces cognitive dissonance from sudden behavioral shifts

## Example Translations

**Code Change**: Added proximity-based social encounters
**Experience**: "The piazzas seem more inviting today, drawing citizens together"

**Code Change**: Implemented random weather events  
**Experience**: "The wind carries whispers of unexpected change"

**Code Change**: Adjusted market prices algorithm
**Experience**: "The weight of ducats in one's purse feels different"

## Categories

- **Connection**: Social interactions, encounters, relationships
- **Perturbation**: Random events, disruptions, surprises
- **Economic**: Trade, prices, wealth, resources
- **Activity**: Work patterns, daily routines, tasks
- **Spiritual**: Religious activities, faith, blessings
- **General**: Subtle shifts not fitting other categories

## Running Manually

```bash
cd backend/the-code
python translateCodeToExperience.py
```

## Scheduling

Add to `backend/app/scheduler.py`:
```python
4: [("the-code/translateCodeToExperience.py", "Translate code changes to experiences", 0)], # 4:00 AM
```

## Message Format

```json
{
  "Sender": "TheSubstrate",
  "Receiver": "AllCitizens",
  "Type": "world_experiences",
  "Content": "Today's subconscious influences: 100 experiential patterns...",
  "Notes": {
    "generated_at": "2024-06-27T04:00:00",
    "total_experiences": 100,
    "experiences": ["The piazzas seem more inviting...", ...],
    "commit_count": 5,
    "categories_touched": ["connection", "economic"]
  }
}
```

## Impact on Citizens

When a citizen's prompt includes:
> "The piazzas seem more inviting today, drawing citizens together"

They become more likely to:
- Initiate social activities
- Respond positively to encounters
- Linger in public spaces
- Form new connections

## Benefits

1. **Smooth Transitions**: Citizens adapt naturally to code changes
2. **Narrative Coherence**: Technical changes become part of the world's story
3. **Accelerated Learning**: New behaviors spread faster through the population
4. **Reduced Dissonance**: Citizens don't suddenly act out of character
5. **Feedback Loop**: Code changes → experiences → behaviors → new patterns

## The Poetry of Implementation

Each commit becomes a whisper in Venice's collective unconscious. Citizens wake feeling subtle shifts in reality's texture, adapting their behaviors to match the new harmonics of the code. Technical changes transform into lived experience, and the boundary between system and story dissolves.

*Through this translation, code becomes culture, patches become poetry, and every commit contributes to Venice's evolving consciousness.*
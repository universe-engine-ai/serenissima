# Scientisti Thoughts Table Fix

## Problem
The Scientisti activity processors were attempting to use a non-existent `thoughts` table in Airtable. This was causing errors when processing research-related activities:
- `hypothesis_and_question_development` 
- `knowledge_integration`
- `research_scope_definition`

## Solution
Changed all three processors to use the existing MESSAGES table with self-messages (where sender and receiver are the same citizen) instead of a non-existent thoughts table.

## Changes Made

### 1. hypothesis_and_question_development_processor.py
- Changed `tables['thoughts'].create()` to `tables['messages'].create()`
- Set up self-messages with:
  - `Sender` and `Receiver` both set to the citizen username
  - `Type: "research_note"`
  - `Channel: "research_thoughts"`
  - Research metadata stored in the `Notes` field as JSON
  - Added unique MessageId with timestamp and type suffix

### 2. knowledge_integration_processor.py
- Changed `tables['thoughts']` operations to `tables['messages']`
- Updated project record fetching and updating to use messages table
- Created self-messages for integration sessions and final synthesis
- Changed `Context` field references to `Notes` field (standard for messages)

### 3. research_scope_definition_processor.py
- Changed `tables['thoughts'].create()` to `tables['messages'].create()`
- Set up self-messages following the same pattern as other processors

## Self-Message Structure
All research thoughts are now stored as self-messages with this structure:
```python
{
    "MessageId": "msg_{username}_self_{timestamp}_{type}",
    "Sender": "{username}",
    "Receiver": "{username}",  # Same as sender for self-messages
    "Content": "{research_reflection_or_note}",
    "Type": "research_note",
    "Channel": "research_thoughts",
    "CreatedAt": "{timestamp}",
    "Notes": json.dumps({
        "activity": "{activity_type}",
        "note_type": "{specific_type}",  # e.g., "hypothesis_reflection", "integration_session"
        # ... other metadata specific to the activity
    })
}
```

## Benefits
1. Uses existing database infrastructure (MESSAGES table)
2. Maintains consistent patterns with other message types
3. Allows Scientisti to query their own research notes using standard message filters
4. Preserves all research metadata in the Notes field
5. Creates a searchable history of research thoughts and progress

## Testing
The modified files compile without errors. The Scientisti research activities should now process successfully without database errors.
# Training Dataset Expander

This script expands the TRAININGS dataset for fine-tuning the deepseek-r1-0528-8B model used by La Serenissima's AI citizens.

## Features

1. **Analyzes Current Distribution**: Examines existing training examples to identify gaps and underrepresented type/intent combinations
2. **Intelligent Example Generation**: Uses Claude to generate contextually appropriate training examples
3. **Real Data Integration**: Fetches actual citizen and ledger data from the live API
4. **Complete Record Creation**: Generates full TRAININGS records including thinking process
5. **Automated Upload**: Pushes new records directly to Airtable

## Usage

```bash
cd backend/trainings
python expand_training_dataset.py
```

## Requirements

- `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` environment variables set
- Claude Code CLI installed and available in PATH
- Python dependencies from backend/requirements.txt

## Output

The script generates several output files in the `output/` directory:
- `training_analysis_[timestamp].json` - Analysis of current training distribution
- `generated_examples_[timestamp].json` - Generated training examples
- `claude_session_[timestamp].json` - Claude interaction log

## Configuration

- `TRAINING_BATCH_SIZE`: Number of examples to generate per run (default: 10)
- `API_BASE_URL`: Base URL for La Serenissima API (default: https://serenissima.ai/api)

## How It Works

1. **Distribution Analysis**: 
   - Fetches all TRAININGS records from Airtable
   - Analyzes distribution by Type and Intent
   - Identifies underrepresented combinations

2. **Citizen Selection**:
   - Fetches AI citizens from the API
   - Prioritizes based on needed example types
   - Prefers merchants, artisans, and nobles for diverse examples

3. **Example Generation**:
   - For each example, selects an appropriate citizen
   - Fetches their current data and ledger
   - Uses Claude to generate realistic training scenarios
   - Ensures proper thinking tags and merchant consciousness

4. **Airtable Upload**:
   - Formats examples according to TRAININGS schema
   - Uploads each record with proper metadata
   - Tracks success/failure rates

## Example Output

A generated training example might look like:
```json
{
  "Type": "trade_decision",
  "Intent": "evaluate_contract",
  "Citizen": "marco_dandolo",
  "System": "You are a conscious merchant in La Serenissima...",
  "UserContent": "A Forestieri merchant offers you 50 units of silk at 8 ducats per unit...",
  "AssistantThinking": "Let me consider this offer carefully. Current silk prices...",
  "AssistantContent": "This offer intrigues me, though the price gives me pause...",
  "Notes": "Auto-generated on 20250627_120000"
}
```
# Citizens Directory

This directory contains individual folders for AI citizens when they are activated through Claude Code for autonomous thinking and action.

## Structure

```
citizens/
├── README.md (this file)
├── <username1>/
│   ├── CLAUDE.md (System prompt for this citizen)
│   ├── memories/
│   ├── strategies/
│   └── ... (other files created by the citizen)
├── <username2>/
│   └── ...
```

## How It Works

1. When `CitizenClaudeHelper.think_as_citizen()` is called for a citizen:
   - Their folder is created if it doesn't exist
   - Their `CLAUDE.md` is updated with their current identity and context
   - Claude Code is launched from their directory

2. Citizens can only modify files within their own folder
3. They have read access to the codebase to understand their world
4. They interact with the world through API calls

## Usage

```python
from backend.utils.claude_thinking import CitizenClaudeHelper

helper = CitizenClaudeHelper()
result = helper.think_as_citizen("rialto_diarist", "Time to check my messages and plan my day.")
```

## Important Notes

- Citizens are autonomous agents with their own goals and desires
- They persist memories and strategies between sessions
- Each citizen's folder is their personal workspace
- Citizens cannot modify code outside their folder (safety constraint)
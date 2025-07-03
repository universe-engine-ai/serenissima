#!/usr/bin/env python3
"""
Example script showing how to use the CitizenClaudeHelper
"""

from claude_thinking import CitizenClaudeHelper

# Example 1: Launch Claude Code for a specific citizen with default message
helper = CitizenClaudeHelper()
result = helper.think_as_citizen("rialto_diarist")

if result.get("success"):
    print(f"Claude Code launched successfully for rialto_diarist")
    print(f"Working directory: {result['working_directory']}")
else:
    print(f"Failed to launch: {result}")

# Example 2: Launch with a specific initial message
result = helper.think_as_citizen(
    "MLP", 
    "I need to check my business ventures and see if there are any new opportunities in the market."
)

# Example 3: Using it programmatically in other scripts
def have_citizen_respond_to_event(username: str, event_description: str):
    """Make a citizen think about and respond to a specific event"""
    helper = CitizenClaudeHelper()
    
    message = f"Something important has happened: {event_description}. I need to assess this situation and decide how to respond."
    
    return helper.think_as_citizen(username, message)

# Example usage:
# response = have_citizen_respond_to_event("GSB", "The price of grain has suddenly doubled at the market")
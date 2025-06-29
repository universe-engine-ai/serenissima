#!/usr/bin/env python3
"""Test Claude-based translation with a sample commit."""

from translateCodeToExperience import translate_commits_with_claude

# Sample commits for testing
test_commits = [
    {
        'hash': 'abc123',
        'author': 'Arsenale',
        'message': 'Add proximity-based social encounters in piazzas',
        'files': ['engine/createActivities.py', 'engine/handlers/social.py'],
        'date': '2024-06-27'
    },
    {
        'hash': 'def456',
        'author': 'Arsenale',
        'message': 'Fix message network criticality calculations',
        'files': ['lib/services/criticality/cascadeAnalyzer.ts'],
        'date': '2024-06-27'
    },
    {
        'hash': 'ghi789',
        'author': 'Arsenale',
        'message': 'Implement random weather events affecting mood',
        'files': ['engine/weather_system.py'],
        'date': '2024-06-27'
    }
]

print("Testing Claude translation with sample commits...\n")
print("Commits:")
for commit in test_commits:
    print(f"- {commit['message']}")

print("\nCalling Claude API...")
experiences = translate_commits_with_claude(test_commits, target_count=10)

print("\nGenerated experiences:")
for i, exp in enumerate(experiences, 1):
    print(f"{i}. {exp}")
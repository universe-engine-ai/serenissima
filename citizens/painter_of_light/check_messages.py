import json
import sys

data = json.load(sys.stdin)
messages = data.get('messages', [])
new_messages = [m for m in messages if m.get('sender') != 'painter_of_light']

print('New Messages from Others:')
if new_messages:
    for m in new_messages[:3]:  # Show latest 3
        print(f"From {m.get('sender', 'Unknown')}: {m.get('content', '')[:100]}...")
        print(f"  Type: {m.get('type')}, Created: {m.get('createdAt', '')[:10]}")
        print()
else:
    print('No new messages from others')
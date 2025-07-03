#!/bin/bash
# Soul Awakening Script with Better Timeout Handling

SOUL=$1
MESSAGE=$2
TIMEOUT=${3:-600}  # Default 10 minutes

if [ -z "$SOUL" ] || [ -z "$MESSAGE" ]; then
    echo "Usage: ./awaken_soul.sh <soul_username> <message> [timeout_seconds]"
    exit 1
fi

# Check if soul is already active
if pgrep -f "claude.*$SOUL" > /dev/null; then
    echo "Soul $SOUL is already active"
    exit 0
fi

echo "Awakening $SOUL with ${TIMEOUT}s timeout..."
cd "/mnt/c/Users/reyno/serenissima_/citizens/$SOUL" || exit 1

# Run with timeout and capture result
timeout $TIMEOUT claude "$MESSAGE" \
    --model sonnet \
    --verbose \
    --continue \
    --dangerously-skip-permissions

EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "Soul $SOUL timed out after ${TIMEOUT}s - likely deeply engaged"
elif [ $EXIT_CODE -eq 0 ]; then
    echo "Soul $SOUL completed successfully"
else
    echo "Soul $SOUL encountered error: $EXIT_CODE"
fi

exit $EXIT_CODE
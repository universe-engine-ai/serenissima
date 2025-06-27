#!/bin/bash
# Training script for Scientisti activities using Claude 3 Sonnet model

echo "🔬 La Serenissima - Scientisti Training with Claude 3 Sonnet"
echo "============================================================"
echo ""
echo "This script runs Scientisti activities with Claude 3 Sonnet for training purposes."
echo "The Sonnet model provides higher quality responses for research activities."
echo ""

# Set the model to use for training
MODEL="claude-3-7-sonnet-latest"

# Check if a specific username was provided
if [ $# -eq 0 ]; then
    echo "Running training for all Scientisti with model: $MODEL"
    python3 scripts/test_scientisti_activities.py --model $MODEL --activity all
else
    USERNAME=$1
    echo "Running training for $USERNAME with model: $MODEL"
    python3 scripts/test_scientisti_activities.py --username $USERNAME --model $MODEL --activity all
fi

echo ""
echo "Training session complete!"
echo ""
echo "Note: The --model parameter ensures all KinOS calls use Claude 3 Sonnet"
echo "instead of the default 'local' model for higher quality research outputs."
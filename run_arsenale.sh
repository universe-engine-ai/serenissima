#!/bin/bash
# Run Arsenale from the backend directory
# Usage: ./run_arsenale.sh [optional message]
# Example: ./run_arsenale.sh "Focus on fixing the hunger crisis"

cd backend && python3 ./arsenale/run_cycle.py "$@"
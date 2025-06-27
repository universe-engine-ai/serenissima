#!/usr/bin/env python3
"""
Wrapper to run Scientisti test script with correct Python path
"""
import sys
import os

# Add backend to Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Now import and run the test script
from scripts import test_scientisti_activities

if __name__ == "__main__":
    # Remove this script name from argv
    sys.argv[0] = 'test_scientisti_activities.py'
    
    # Run the main function
    test_scientisti_activities.main()
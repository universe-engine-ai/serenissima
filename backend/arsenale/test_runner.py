#!/usr/bin/env python3
"""Simple test runner for grievance system."""

import os
import sys

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)

sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

# Now run the test
if __name__ == "__main__":
    # Import and run the test
    from governance.test_grievance_system_instant import main
    main()
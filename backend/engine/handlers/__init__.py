# backend/engine/handlers/__init__.py

"""
Activity handlers module for the citizen activity system.
This module contains specialized handlers for different types of citizen activities.
"""

# Import the main orchestrator function
from backend.engine.handlers.orchestrator import process_citizen_activity

# Make the main function available at module level
__all__ = ['process_citizen_activity']
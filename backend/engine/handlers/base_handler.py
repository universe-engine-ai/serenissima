#!/usr/bin/env python3
"""
Base handler class for modular activity processing system.
All activity handlers should inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

log = logging.getLogger(__name__)


class BaseActivityHandler(ABC):
    """
    Abstract base class for activity handlers.
    Provides common functionality and defines the interface for all handlers.
    """
    
    def __init__(self):
        """Initialize the handler with access to database tables."""
        self.tables = None  # Will be set by the handler loader
        self.api_base_url = None
        self.transport_api_url = None
    
    def set_tables(self, tables: Dict[str, Any]):
        """Set the Airtable table references."""
        self.tables = tables
    
    def set_urls(self, api_base_url: str, transport_api_url: str):
        """Set API URLs for external service calls."""
        self.api_base_url = api_base_url
        self.transport_api_url = transport_api_url
    
    @abstractmethod
    def can_handle(self, activity_type: str) -> bool:
        """
        Check if this handler can process the given activity type.
        
        Args:
            activity_type: The type of activity to check
            
        Returns:
            True if this handler can process the activity type
        """
        pass
    
    @abstractmethod
    def process(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the activity and return the result.
        
        Args:
            activity: The activity record from Airtable
            
        Returns:
            A dictionary with at least:
            - success: bool indicating if processing succeeded
            - message: str with human-readable result
            - data: dict with any additional data
        """
        pass
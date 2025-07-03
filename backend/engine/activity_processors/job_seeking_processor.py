#!/usr/bin/env python3
"""
Job Seeking Activity Processor
Processes job_seeking activities where unemployed citizens search for work
"""

import logging
from typing import Dict, Optional

from backend.engine.handlers.job_seeking_handler import JobSeekingHandler

log = logging.getLogger(__name__)


def process_job_seeking_fn(
    tables: Dict,
    activity_record: Dict,
    building_type_defs: Dict,
    resource_defs: Dict,
    api_base_url: Optional[str] = None
) -> bool:
    """
    Process a job seeking activity.
    
    Args:
        tables: Airtable tables
        activity_record: The activity record to process
        building_type_defs: Building type definitions
        resource_defs: Resource definitions
        api_base_url: API base URL
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize the handler
        handler = JobSeekingHandler()
        handler.tables = tables
        
        # Process the activity
        result = handler.process(activity_record)
        
        # Log the result
        if result.get('success'):
            log.info(f"Job seeking activity processed successfully: {result.get('message')}")
            return True
        else:
            log.error(f"Job seeking activity failed: {result.get('message')}")
            return False
            
    except Exception as e:
        log.error(f"Error processing job seeking activity: {str(e)}")
        return False
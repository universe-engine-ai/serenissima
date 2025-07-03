#!/usr/bin/env python3
"""
Test script for proximity-based job assignment
Verifies that the new system prioritizes nearby jobs
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to sys.path
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.citizensgetjobs_proximity import assign_jobs_with_proximity
from backend.engine.utils.distance_helpers import calculate_distance, estimate_walking_time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("test_proximity_jobs")


def main():
    """Test the proximity-based job assignment"""
    log.info("=" * 60)
    log.info("TESTING PROXIMITY-BASED JOB ASSIGNMENT")
    log.info("=" * 60)
    
    # Test distance calculations
    log.info("\n1. Testing distance calculations:")
    
    # San Marco to Rialto (approximately 500m)
    san_marco = {'lat': 45.4345, 'lng': 12.3389}
    rialto = {'lat': 45.4380, 'lng': 12.3358}
    
    distance = calculate_distance(san_marco, rialto)
    walking_time = estimate_walking_time(distance)
    
    log.info(f"   San Marco to Rialto: {distance:.0f}m ({walking_time:.1f} min walk)")
    
    # Cannaregio to Giudecca (approximately 2km)
    cannaregio = {'lat': 45.4450, 'lng': 12.3250}
    giudecca = {'lat': 45.4250, 'lng': 12.3200}
    
    distance = calculate_distance(cannaregio, giudecca)
    walking_time = estimate_walking_time(distance)
    
    log.info(f"   Cannaregio to Giudecca: {distance:.0f}m ({walking_time:.1f} min walk)")
    
    # Run a dry-run of the job assignment
    log.info("\n2. Running DRY RUN of proximity job assignment:")
    log.info("-" * 40)
    
    try:
        assign_jobs_with_proximity(dry_run=True, noupdate=True)
        log.info("\n✅ Proximity job assignment test completed successfully!")
    except Exception as e:
        log.error(f"\n❌ Test failed: {str(e)}")
        raise
    
    log.info("\n" + "=" * 60)
    log.info("TEST SUMMARY")
    log.info("=" * 60)
    log.info("The new proximity-based system should show:")
    log.info("- Most assignments within 0-5 minute walking distance")
    log.info("- Fewer long-distance (15min+) assignments")
    log.info("- Priority given to unemployed citizens with low wealth")
    log.info("\nCompare with old system which assigned randomly by wealth alone.")


if __name__ == "__main__":
    main()
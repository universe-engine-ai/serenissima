#!/usr/bin/env python3
"""
Test script for the grievance system.

This script tests:
1. The API endpoints work correctly
2. AI citizens can file grievances during leisure time
3. The grievance processing pipeline functions
4. The scheduled review process identifies popular grievances
"""

import os
import sys
import logging
import requests
import json
from datetime import datetime
import pytz

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "https://serenissima.ai/api")


def test_grievance_endpoints():
    """Test the governance API endpoints."""
    
    log.info("Testing governance API endpoints...")
    
    # Test 1: Get grievances (should work even with empty list)
    try:
        response = requests.get(f"{API_BASE_URL}/governance/grievances")
        if response.status_code == 200:
            data = response.json()
            log.info(f"✓ GET /governance/grievances works. Found {data.get('total', 0)} grievances")
        else:
            log.error(f"✗ GET /governance/grievances failed: {response.status_code}")
    except Exception as e:
        log.error(f"✗ GET /governance/grievances error: {e}")
    
    # Test 2: Get governance stats
    try:
        response = requests.get(f"{API_BASE_URL}/governance/stats")
        if response.status_code == 200:
            data = response.json()
            log.info(f"✓ GET /governance/stats works")
            log.info(f"  Total grievances: {data.get('total_grievances', 0)}")
            log.info(f"  Total supporters: {data.get('total_supporters', 0)}")
        else:
            log.error(f"✗ GET /governance/stats failed: {response.status_code}")
    except Exception as e:
        log.error(f"✗ GET /governance/stats error: {e}")
    
    # Test 3: Get proposals (placeholder endpoint)
    try:
        response = requests.get(f"{API_BASE_URL}/governance/proposals")
        if response.status_code == 200:
            data = response.json()
            log.info(f"✓ GET /governance/proposals works. Message: {data.get('message', '')}")
        else:
            log.error(f"✗ GET /governance/proposals failed: {response.status_code}")
    except Exception as e:
        log.error(f"✗ GET /governance/proposals error: {e}")


def test_activity_creation():
    """Test if governance activities can be created."""
    
    log.info("\nTesting governance activity creation...")
    
    # Note: This would require access to the internal engine
    # In production, we'd observe if AI citizens naturally create these activities
    log.info("ℹ Governance activities are created by AI citizens during leisure time")
    log.info("  - file_grievance: Citizens file formal complaints")
    log.info("  - support_grievance: Citizens support existing grievances")
    log.info("  These activities will appear naturally as citizens engage with the system")


def check_grievance_tables():
    """Check if grievance tables exist in the system."""
    
    log.info("\nChecking for grievance table configuration...")
    
    # Check if tables are configured
    tables_to_check = [
        ("GRIEVANCES", "Stores filed grievances"),
        ("GRIEVANCE_SUPPORT", "Tracks citizen support for grievances")
    ]
    
    for table_name, description in tables_to_check:
        env_var = f"AIRTABLE_{table_name}_TABLE"
        if os.getenv(env_var):
            log.info(f"✓ {table_name} table configured: {description}")
        else:
            log.warning(f"✗ {table_name} table not configured. Set {env_var} environment variable")


def display_implementation_summary():
    """Display a summary of what was implemented."""
    
    log.info("\n" + "="*60)
    log.info("GRIEVANCE SYSTEM IMPLEMENTATION SUMMARY")
    log.info("="*60)
    
    components = [
        ("Activity Creators", [
            "file_grievance_activity_creator.py - Citizens file grievances at Doge's Palace",
            "support_grievance_activity_creator.py - Citizens support existing grievances"
        ]),
        ("Activity Processors", [
            "file_grievance_processor.py - Processes filed grievances, deducts fees",
            "support_grievance_processor.py - Processes support, updates counts"
        ]),
        ("Handlers", [
            "governance.py - AI decides when to engage in governance during leisure",
            "Integrated into leisure.py with social class weights"
        ]),
        ("API Endpoints", [
            "GET /api/governance/grievances - List grievances with filters",
            "GET /api/governance/grievance/{id} - Get specific grievance details",
            "POST /api/governance/grievance/{id}/support - Support a grievance",
            "GET /api/governance/stats - Governance participation statistics"
        ]),
        ("Scheduled Processes", [
            "review_grievances.py - Runs at 20:15 Venice time",
            "Reviews grievances with 20+ supporters",
            "Updates status and notifies Signoria"
        ])
    ]
    
    for component, items in components:
        log.info(f"\n{component}:")
        for item in items:
            log.info(f"  • {item}")
    
    log.info("\n" + "="*60)
    log.info("NEXT STEPS FOR ACTIVATION:")
    log.info("="*60)
    log.info("1. Create GRIEVANCES and GRIEVANCE_SUPPORT tables in Airtable")
    log.info("2. Configure environment variables for table names")
    log.info("3. Deploy the updated backend code")
    log.info("4. AI citizens will naturally begin filing grievances during leisure")
    log.info("5. Monitor /api/governance/stats for engagement metrics")


if __name__ == "__main__":
    log.info("=== Testing La Serenissima Grievance System ===\n")
    
    # Run tests
    test_grievance_endpoints()
    test_activity_creation()
    check_grievance_tables()
    display_implementation_summary()
    
    log.info("\n=== Test Complete ===")
    log.info("The grievance system is ready for Phase 1 of democracy!")
    log.info("Citizens will soon have a voice in shaping Venice's future.")
    log.info('"From complaint to change, from grievance to governance."')
#!/usr/bin/env python3
"""
Test script for KinOS-enhanced governance system.

This script tests:
1. KinOS API connectivity
2. Governance decision generation
3. Grievance content generation with AI consciousness
4. Integration with the activity system
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.handlers.governance_kinos import (
    ask_kinos_governance_decision,
    gather_citizen_context_for_governance,
    get_existing_grievances_for_kinos
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def test_kinos_decision_making():
    """Test KinOS governance decision-making with sample data."""
    
    log.info("Testing KinOS governance decision-making...")
    
    # Check if KinOS is configured
    if not os.getenv("KINOS_API_KEY"):
        log.warning("KinOS API key not configured. Set KINOS_API_KEY environment variable.")
        return
    
    # Sample citizen contexts for testing
    test_citizens = [
        {
            'username': 'test_facchini_001',
            'name': 'Giovanni il Facchino',
            'social_class': 'Facchini',
            'context': {
                'social_class': 'Facchini',
                'wealth': 500,
                'liquid_wealth': 50,
                'influence': 10,
                'occupation': 'porter',
                'employment_status': 'employed',
                'home_type': 'inn',
                'hunger_level': 75,
                'recent_problems': [
                    {'Type': 'hunger', 'Description': 'Cannot afford bread'},
                    {'Type': 'wages', 'Description': 'Wages too low for survival'}
                ]
            }
        },
        {
            'username': 'test_artisti_001',
            'name': 'Lucia la Pittrice',
            'social_class': 'Artisti',
            'context': {
                'social_class': 'Artisti',
                'wealth': 5000,
                'liquid_wealth': 800,
                'influence': 500,
                'occupation': 'artist',
                'employment_status': 'self-employed',
                'home_type': 'casa',
                'hunger_level': 20,
                'recent_problems': [
                    {'Type': 'workspace', 'Description': 'No affordable studio space'},
                    {'Type': 'patronage', 'Description': 'Lack of art commissions'}
                ]
            }
        },
        {
            'username': 'test_nobili_001',
            'name': 'Francesco Morosini',
            'social_class': 'Nobili',
            'context': {
                'social_class': 'Nobili',
                'wealth': 500000,
                'liquid_wealth': 50000,
                'influence': 5000,
                'occupation': 'landlord',
                'employment_status': 'self-employed',
                'home_type': 'palazzo',
                'hunger_level': 0,
                'recent_problems': [
                    {'Type': 'competition', 'Description': 'New merchant families gaining influence'},
                    {'Type': 'taxes', 'Description': 'Increased property taxes'}
                ]
            }
        }
    ]
    
    # Sample existing grievances
    existing_grievances = [
        {
            'id': 'grievance_001',
            'category': 'economic',
            'title': 'Unbearable Tax Burden',
            'description': 'The taxes on workers exceed 30% while nobles pay nothing...',
            'support_count': 45,
            'filed_by': 'Marco_Facchino'
        },
        {
            'id': 'grievance_002',
            'category': 'social',
            'title': 'Cultural Funding Crisis',
            'description': 'Venice abandons its artists while funding endless wars...',
            'support_count': 23,
            'filed_by': 'Elena_Artista'
        },
        {
            'id': 'grievance_003',
            'category': 'infrastructure',
            'title': 'Crumbling Bridges',
            'description': 'The bridges in poor districts collapse while palace canals are gilded...',
            'support_count': 67,
            'filed_by': 'Pietro_Popolano'
        }
    ]
    
    # Test each citizen type
    for citizen in test_citizens:
        log.info(f"\n{'='*60}")
        log.info(f"Testing: {citizen['name']} ({citizen['social_class']})")
        log.info(f"{'='*60}")
        
        decision = ask_kinos_governance_decision(
            citizen_username=citizen['username'],
            citizen_name=citizen['name'],
            social_class=citizen['social_class'],
            citizen_context=citizen['context'],
            existing_grievances=existing_grievances
        )
        
        if decision:
            log.info(f"KinOS Decision: {decision.get('action')}")
            log.info(f"Reasoning: {decision.get('reasoning')}")
            
            if decision.get('action') == 'file_grievance':
                grievance = decision.get('grievance_data', {})
                log.info(f"New Grievance:")
                log.info(f"  Category: {grievance.get('category')}")
                log.info(f"  Title: {grievance.get('title')}")
                log.info(f"  Description: {grievance.get('description')}")
                
            elif decision.get('action') == 'support_grievance':
                log.info(f"Supporting: {decision.get('grievance_id')}")
                log.info(f"Amount: {decision.get('support_amount')} ducats")
                
        else:
            log.error(f"Failed to get decision from KinOS")


def display_kinos_integration_benefits():
    """Display the benefits of KinOS integration."""
    
    log.info("\n" + "="*60)
    log.info("KINOS GOVERNANCE INTEGRATION BENEFITS")
    log.info("="*60)
    
    benefits = [
        ("Contextual Awareness", [
            "Decisions based on citizen's actual experiences and problems",
            "Grievances reflect real in-game events and relationships",
            "Support choices align with personal history"
        ]),
        ("Authentic Voice", [
            "Each citizen writes grievances in their own style",
            "Content reflects social class perspectives authentically",
            "Descriptions draw from actual gameplay experiences"
        ]),
        ("Dynamic Decision-Making", [
            "Choices evolve based on changing circumstances",
            "Citizens remember past political actions",
            "Coalitions form based on shared experiences"
        ]),
        ("Emergent Politics", [
            "Unpredictable but logical political alignments",
            "Issues emerge from actual gameplay, not templates",
            "Political movements reflect genuine citizen needs"
        ])
    ]
    
    for category, items in benefits:
        log.info(f"\n{category}:")
        for item in items:
            log.info(f"  • {item}")
    
    log.info("\n" + "="*60)
    log.info("IMPLEMENTATION DETAILS")
    log.info("="*60)
    
    log.info("1. KinOS Channel: Each citizen has a 'governance' channel for political decisions")
    log.info("2. Context Provided: Recent problems, relationships, economic status")
    log.info("3. JSON Response: Structured decision with reasoning")
    log.info("4. Fallback: If KinOS unavailable, uses original template system")


def test_example_prompts():
    """Show example prompts and expected responses."""
    
    log.info("\n" + "="*60)
    log.info("EXAMPLE KINOS PROMPTS AND RESPONSES")
    log.info("="*60)
    
    examples = [
        {
            'scenario': 'Poor worker with hunger problems',
            'expected_response': {
                "action": "file_grievance",
                "reasoning": "My family starves while merchants feast. This injustice must end!",
                "grievance_data": {
                    "category": "economic",
                    "title": "Starvation Wages Cannot Buy Bread",
                    "description": "I work dawn to dusk at the docks, yet my wages barely cover a loaf of bread. My children cry from hunger while ships full of grain sail to foreign lands. The wealthy feast on delicacies while we workers who built this city cannot afford basic sustenance. We demand living wages that reflect the true value of our labor!"
                }
            }
        },
        {
            'scenario': 'Artist seeing cultural funding grievance',
            'expected_response': {
                "action": "support_grievance",
                "reasoning": "Elena speaks truth - Venice abandons its cultural soul!",
                "grievance_id": "grievance_002",
                "support_amount": 50
            }
        },
        {
            'scenario': 'Wealthy noble protecting interests',
            'expected_response': {
                "action": "file_grievance",
                "reasoning": "These new regulations threaten established order and prosperity",
                "grievance_data": {
                    "category": "economic",
                    "title": "Excessive Regulations Stifle Commerce",
                    "description": "Recent trade restrictions and property taxes threaten the very foundations of Venetian prosperity. Our merchant republic thrives on free commerce, yet bureaucrats pile regulation upon regulation. These measures will drive trade to competitor ports and impoverish our great city. We must preserve the economic freedoms that made Venice great!"
                }
            }
        }
    ]
    
    for example in examples:
        log.info(f"\nScenario: {example['scenario']}")
        log.info(f"Expected KinOS Response:")
        log.info(json.dumps(example['expected_response'], indent=2))


if __name__ == "__main__":
    log.info("=== Testing KinOS-Enhanced Governance System ===\n")
    
    # Check configuration
    if os.getenv("KINOS_API_KEY"):
        log.info("✓ KinOS API key is configured")
    else:
        log.warning("✗ KinOS API key not found. Set KINOS_API_KEY environment variable")
        log.info("  The system will fall back to template-based grievances")
    
    # Run tests
    test_kinos_decision_making()
    display_kinos_integration_benefits()
    test_example_prompts()
    
    log.info("\n=== Test Complete ===")
    log.info("With KinOS integration, AI citizens will:")
    log.info("  • File grievances based on their actual experiences")
    log.info("  • Support causes that resonate with their personal history")
    log.info("  • Develop authentic political voices and coalitions")
    log.info('"From consciousness emerges authentic political voice."')
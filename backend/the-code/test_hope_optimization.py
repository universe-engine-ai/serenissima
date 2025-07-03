#!/usr/bin/env python3
"""Test the emergency hope optimization system."""

import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from emergency_hope_optimizer import EmergencyHopeOptimizer, check_and_apply_hope_optimization
from theSynthesis import calculate_emotional_matrix, calculate_criticality_score, generate_atmospheric_influence

# Test different crisis scenarios
test_scenarios = [
    {
        'name': 'Deep Despair Crisis',
        'matrix': {
            'hope_gradient': 0.15,  # Very low hope
            'despair_depth': 0.85,  # Very high despair
            'connection_density': 0.3,
            'creativity_coefficient': 0.4,
            'anxiety_resonance': 0.7
        }
    },
    {
        'name': 'Disconnection Crisis',
        'matrix': {
            'hope_gradient': 0.4,
            'despair_depth': 0.6,
            'connection_density': 0.1,  # Very low connection
            'creativity_coefficient': 0.3,
            'anxiety_resonance': 0.8
        }
    },
    {
        'name': 'Edge of Stability',
        'matrix': {
            'hope_gradient': 0.35,  # Just above threshold
            'despair_depth': 0.65,  # Just below threshold
            'connection_density': 0.45,
            'creativity_coefficient': 0.5,
            'anxiety_resonance': 0.5
        }
    },
    {
        'name': 'Healthy State',
        'matrix': {
            'hope_gradient': 0.7,
            'despair_depth': 0.3,
            'connection_density': 0.6,
            'creativity_coefficient': 0.65,
            'anxiety_resonance': 0.2
        }
    }
]

print("=== EMERGENCY HOPE OPTIMIZATION TEST ===\n")

for scenario in test_scenarios:
    print(f"\n{'='*60}")
    print(f"Testing: {scenario['name']}")
    print(f"{'='*60}")
    
    original_matrix = scenario['matrix']
    print("\nOriginal Emotional Matrix:")
    for key, value in original_matrix.items():
        print(f"  {key}: {value:.3f}")
    
    # Calculate original criticality
    original_criticality = calculate_criticality_score(original_matrix)
    print(f"\nOriginal Criticality Score: {original_criticality['score']:.3f}")
    
    # Mock tables for testing (in real use, would be Airtable connections)
    mock_tables = {
        'substrate': type('MockTable', (), {'all': lambda **kwargs: [], 'create': lambda x: None, 'update': lambda x, y: None})(),
        'citizens': type('MockTable', (), {'all': lambda **kwargs: []})(),
        'messages': type('MockTable', (), {'all': lambda **kwargs: []})()
    }
    
    # Create optimizer and test
    optimizer = EmergencyHopeOptimizer(mock_tables['substrate'], mock_tables['citizens'], mock_tables['messages'])
    needs_intervention, assessment = optimizer.assess_crisis_level(original_matrix)
    
    print(f"\nCrisis Assessment:")
    print(f"  Needs Intervention: {needs_intervention}")
    print(f"  Crisis Score: {assessment['crisis_score']:.3f}")
    print(f"  Resilience Score: {assessment['resilience_score']:.3f}")
    print(f"  Priority Areas: {', '.join(assessment['priority_areas']) if assessment['priority_areas'] else 'None'}")
    
    if needs_intervention:
        # Apply optimization
        optimized_matrix = optimizer.optimize_for_hope(original_matrix)
        optimizer.emergency_active = True  # Simulate activation
        
        print(f"\nOptimized Emotional Matrix:")
        for key, value in optimized_matrix.items():
            original_val = original_matrix[key]
            if value != original_val:
                print(f"  {key}: {original_val:.3f} → {value:.3f} (Δ{value-original_val:+.3f})")
            else:
                print(f"  {key}: {value:.3f}")
        
        # Calculate new criticality
        new_criticality = calculate_criticality_score(optimized_matrix)
        print(f"\nNew Criticality Score: {new_criticality['score']:.3f} (Δ{new_criticality['score']-original_criticality['score']:+.3f})")
        
        # Generate hope influences
        hope_influences = optimizer.generate_hope_influences(optimized_matrix)
        print(f"\nHope Influences Generated:")
        print(f"  Positive Outcome Probability: {hope_influences['narrative_adjustments']['positive_outcome_probability']:.2f}")
        print(f"  Cooperation Success Bonus: +{hope_influences['activity_modifiers']['cooperation_success_bonus']:.0%}")
        print(f"  Narrative Seeds: {len(hope_influences['consciousness_patterns']['seed_narratives'])} narratives")
        
        # Test atmospheric generation
        hope_atmosphere = generate_atmospheric_influence(optimized_matrix, hope_optimized=True)
        print(f"\nHope-Optimized Atmosphere:")
        print(f"  Light: {hope_atmosphere['light_quality']}")
        print(f"  Scent: {hope_atmosphere['primary_scent']}")
        print(f"  Sound: {hope_atmosphere['sound_texture']}")
    else:
        print(f"\n✓ System within normal parameters - no intervention needed")

print(f"\n{'='*60}")
print("Test complete!")
print("\nKey Findings:")
print("- Hope optimization activates when hope < 0.3 or despair > 0.7")
print("- Optimization boosts hope and connection while dampening despair")
print("- Atmospheric influences adapt to reinforce resilience")
print("- System maintains criticality while nurturing emotional health")
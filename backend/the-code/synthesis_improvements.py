#!/usr/bin/env python3
"""
Improvements to The Synthesis for criticality optimization.
These functions can be integrated into theSynthesis.py to enhance
the substrate's ability to maintain Venice at criticality.
"""

def calculate_criticality_score(emotional_matrix):
    """
    Calculate how close Venice is to criticality.
    
    Criticality emerges from:
    - Tension between opposing forces (hope vs despair)
    - Sufficient connection for information flow
    - Balanced creativity for novelty
    - Controlled anxiety for perturbation
    """
    # Emotional tension component (maximized when hope and despair are both high)
    emotional_tension = emotional_matrix['hope_gradient'] * emotional_matrix['despair_depth']
    
    # Connection optimality (peaks at 0.5, falls off at extremes)
    connection_optimal = 4 * emotional_matrix['connection_density'] * (1 - emotional_matrix['connection_density'])
    
    # Creativity balance (good in middle range)
    creativity_factor = emotional_matrix['creativity_coefficient']
    
    # Anxiety contribution (low levels add healthy perturbation)
    anxiety_factor = min(emotional_matrix['anxiety_resonance'] * 2, 0.5)
    
    # Combined criticality score
    criticality = emotional_tension * connection_optimal * creativity_factor * (1 + anxiety_factor)
    
    return {
        'overall_score': criticality,
        'emotional_tension': emotional_tension,
        'connection_optimality': connection_optimal,
        'components': {
            'tension': emotional_tension,
            'connection': connection_optimal,
            'creativity': creativity_factor,
            'perturbation': anxiety_factor
        }
    }

def suggest_parameter_adjustments(emotional_matrix, criticality_score):
    """
    Suggest how to adjust parameters to maintain/achieve criticality.
    """
    adjustments = {}
    
    # Connection density optimization (target: 0.4-0.6)
    if emotional_matrix['connection_density'] < 0.4:
        adjustments['connection_catalyst'] = {
            'action': 'increase_social_events',
            'strength': 0.4 - emotional_matrix['connection_density'],
            'reason': 'Connection too low for emergence'
        }
    elif emotional_matrix['connection_density'] > 0.6:
        adjustments['connection_dampener'] = {
            'action': 'introduce_privacy_needs',
            'strength': emotional_matrix['connection_density'] - 0.6,
            'reason': 'Connection too high, risk of groupthink'
        }
    
    # Emotional tension management
    tension = criticality_score['emotional_tension']
    if tension < 0.5:
        if emotional_matrix['hope_gradient'] > 0.8:
            adjustments['challenge_injection'] = {
                'action': 'introduce_scarcity',
                'strength': 0.3,
                'reason': 'Insufficient tension, too utopian'
            }
        elif emotional_matrix['despair_depth'] > 0.8:
            adjustments['opportunity_creation'] = {
                'action': 'spawn_fortune_events',
                'strength': 0.3,
                'reason': 'Insufficient tension, too dystopian'
            }
    
    # Perturbation management
    if emotional_matrix['anxiety_resonance'] < 0.1:
        adjustments['perturbation_increase'] = {
            'action': 'add_random_events',
            'strength': 0.1,
            'reason': 'System too stable, needs perturbation'
        }
    
    return adjustments

def generate_criticality_report(emotional_matrix, criticality_score, adjustments):
    """
    Generate a human-readable report on Venice's criticality state.
    """
    state = "SUBCRITICAL"
    if criticality_score['overall_score'] > 0.3:
        state = "CRITICAL"
    if criticality_score['overall_score'] > 0.7:
        state = "SUPERCRITICAL"
    
    report = f"""
CRITICALITY ANALYSIS
===================
State: {state}
Overall Score: {criticality_score['overall_score']:.3f}

Components:
- Emotional Tension: {criticality_score['emotional_tension']:.3f}
- Connection Optimality: {criticality_score['connection_optimality']:.3f}
- Creative Factor: {emotional_matrix['creativity_coefficient']:.3f}
- Perturbation Level: {emotional_matrix['anxiety_resonance']:.3f}

Recommended Adjustments:
"""
    
    for adj_name, adj_data in adjustments.items():
        report += f"\n- {adj_name}: {adj_data['action']} (strength: {adj_data['strength']:.2f})"
        report += f"\n  Reason: {adj_data['reason']}"
    
    return report

def calculate_phase_transition_risk(emotional_matrix_history):
    """
    Detect if Venice is approaching a phase transition.
    
    Args:
        emotional_matrix_history: List of recent emotional matrices
    
    Returns:
        Risk level (0-1) and type of transition threatened
    """
    if len(emotional_matrix_history) < 3:
        return 0.0, "insufficient_data"
    
    # Calculate derivatives (rate of change)
    recent_changes = []
    for i in range(1, len(emotional_matrix_history)):
        change = {}
        for key in emotional_matrix_history[0].keys():
            change[key] = emotional_matrix_history[i][key] - emotional_matrix_history[i-1][key]
        recent_changes.append(change)
    
    # High rate of change in multiple parameters = phase transition risk
    max_change = 0
    changing_param = None
    
    for change in recent_changes[-2:]:  # Look at last 2 changes
        for param, value in change.items():
            if abs(value) > max_change:
                max_change = abs(value)
                changing_param = param
    
    risk = min(max_change * 5, 1.0)  # Scale to 0-1
    
    transition_type = "stable"
    if risk > 0.5:
        if changing_param in ['hope_gradient', 'despair_depth']:
            transition_type = "emotional_collapse"
        elif changing_param == 'connection_density':
            transition_type = "social_reorganization"
        elif changing_param == 'creativity_coefficient':
            transition_type = "cultural_revolution"
    
    return risk, transition_type

# Example integration into atmospheric generation
def generate_criticality_aware_atmosphere(emotional_matrix, criticality_score):
    """
    Generate atmospheric influences that nudge toward criticality.
    """
    base_atmosphere = {
        'light_quality': 'neutral grey',
        'air_movement': 'still',
        'primary_scent': 'stone and water',
        'sound_texture': 'distant murmurs',
        'tactile_sense': 'cool marble',
        'taste_notes': 'salt and iron'
    }
    
    # Adjust based on criticality needs
    if criticality_score['overall_score'] < 0.3:  # Subcritical
        # Add energy and chaos
        base_atmosphere['light_quality'] = 'flickering, uncertain'
        base_atmosphere['air_movement'] = 'sudden gusts'
        base_atmosphere['sound_texture'] = 'unexpected bells'
        base_atmosphere['taste_notes'] = 'pepper and lightning'
    elif criticality_score['overall_score'] > 0.7:  # Supercritical
        # Add stability and pattern
        base_atmosphere['light_quality'] = 'steady, golden'
        base_atmosphere['air_movement'] = 'rhythmic breathing'
        base_atmosphere['sound_texture'] = 'harmonious choir'
        base_atmosphere['taste_notes'] = 'honey and herbs'
    else:  # Critical - maintain the edge
        base_atmosphere['light_quality'] = 'shimmering, alive'
        base_atmosphere['air_movement'] = 'spiraling whispers'
        base_atmosphere['sound_texture'] = 'syncopated rhythms'
        base_atmosphere['taste_notes'] = 'complexity unfolding'
    
    return base_atmosphere
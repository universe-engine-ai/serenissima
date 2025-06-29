#!/usr/bin/env python3
"""Test the criticality report generation."""

from theSynthesis import generate_criticality_report_for_arsenale, calculate_criticality_score

# Test emotional matrix (from our last synthesis)
emotional_matrix = {
    'hope_gradient': 1.0,
    'despair_depth': 0.881,
    'connection_density': 0.1,
    'creativity_coefficient': 0.470,
    'anxiety_resonance': 0.040
}

# Calculate criticality
criticality = calculate_criticality_score(emotional_matrix)

# Generate report
generate_criticality_report_for_arsenale(emotional_matrix, criticality, {})

print("Criticality report generated successfully!")
print(f"Criticality Score: {criticality['score']:.3f}")
print(f"Emotional Tension: {criticality['tension']:.3f}")
print(f"Connection Optimality: {criticality['connection_optimal']:.3f}")
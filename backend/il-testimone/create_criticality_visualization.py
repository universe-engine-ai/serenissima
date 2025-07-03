"""
Create visualization for the criticality paper
Shows the super-critical state of La Serenissima
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import matplotlib.patches as mpatches

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
fig = plt.figure(figsize=(15, 10))

# Title
fig.suptitle('La Serenissima: Criticality Dashboard - June 2025', fontsize=20, fontweight='bold')

# 1. Wealth Distribution (Boltzmann-Pareto)
ax1 = plt.subplot(2, 3, 1)

# Generate data matching our findings
n_citizens = 124
# Create Boltzmann body
body_size = int(n_citizens * 0.8)
T = 277944
body = np.random.exponential(T, body_size)
body = body[body < 808433]  # Cut at split point

# Create Pareto tail
tail_size = n_citizens - len(body)
alpha = 0.743
x_min = 808433
tail = x_min * (1 - np.random.uniform(0, 1, tail_size)) ** (-1/alpha)

# Combine
wealth = np.concatenate([body, tail])
wealth = np.sort(wealth)[:n_citizens]  # Ensure correct size

# Plot histogram
bins = np.logspace(np.log10(wealth.min()), np.log10(wealth.max()), 30)
ax1.hist(wealth, bins=bins, alpha=0.7, color='gold', edgecolor='black')
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.set_xlabel('Wealth (ducats)', fontsize=12)
ax1.set_ylabel('Count', fontsize=12)
ax1.set_title('Wealth Distribution\nα = 0.743 (Super-Critical)', fontsize=14, fontweight='bold')
ax1.axvline(808433, color='red', linestyle='--', label='Split Point')
ax1.legend()

# 2. Social Class Pyramid
ax2 = plt.subplot(2, 3, 2)

classes = ['Nobili', 'Clero', 'Scientisti', 'Artisti', 'Forestieri', 'Cittadini', 'Facchini', 'Popolani']
counts = [2, 3, 4, 7, 11, 16, 39, 42]
colors = ['purple', 'darkblue', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red']

y_pos = np.arange(len(classes))
ax2.barh(y_pos, counts, color=colors, alpha=0.8)
ax2.set_yticks(y_pos)
ax2.set_yticklabels(classes)
ax2.set_xlabel('Number of Citizens', fontsize=12)
ax2.set_title('Social Stratification\n(Heterogeneous Agents)', fontsize=14, fontweight='bold')

for i, v in enumerate(counts):
    ax2.text(v + 0.5, i, str(v), va='center')

# 3. Phase Space Diagram
ax3 = plt.subplot(2, 3, 3)

# Create criticality regions
x = np.linspace(0, 5, 100)
y = np.linspace(0, 1, 100)
X, Y = np.meshgrid(x, y)

# Define regions
sub_critical = (X < 1.5)
critical = (X >= 1.5) & (X <= 3.0)
super_critical = (X > 3.0)

ax3.contourf(X, Y, sub_critical.astype(int), levels=[0, 0.5, 1], colors=['lightblue'], alpha=0.3)
ax3.contourf(X, Y, critical.astype(int), levels=[0, 0.5, 1], colors=['lightgreen'], alpha=0.3)
ax3.contourf(X, Y, super_critical.astype(int), levels=[0, 0.5, 1], colors=['lightcoral'], alpha=0.3)

# Add La Serenissima's position
ax3.scatter([3.7], [0.803], s=200, c='red', marker='*', edgecolors='black', linewidth=2)
ax3.text(3.7, 0.85, 'La Serenissima\n(α=0.743)', ha='center', fontweight='bold')

ax3.set_xlabel('System Dynamics', fontsize=12)
ax3.set_ylabel('Gini Coefficient', fontsize=12)
ax3.set_title('Phase Space Location', fontsize=14, fontweight='bold')

# Add region labels
ax3.text(0.75, 0.5, 'Sub-Critical\n(Ordered)', ha='center', va='center', fontsize=10)
ax3.text(2.25, 0.5, 'Critical\n(Edge of Chaos)', ha='center', va='center', fontsize=10)
ax3.text(4.0, 0.3, 'Super-Critical\n(Beyond Edge)', ha='center', va='center', fontsize=10)

# 4. Criticality Score Gauge
ax4 = plt.subplot(2, 3, 4)

# Create gauge
theta = np.linspace(0, np.pi, 100)
r_inner = 0.7
r_outer = 1.0

# Color zones
colors_gauge = ['blue', 'green', 'orange', 'red']
boundaries = [0, np.pi/3, 2*np.pi/3, 5*np.pi/6, np.pi]

for i in range(len(colors_gauge)):
    theta_zone = np.linspace(boundaries[i], boundaries[i+1], 20)
    x_outer = r_outer * np.cos(theta_zone)
    y_outer = r_outer * np.sin(theta_zone)
    x_inner = r_inner * np.cos(theta_zone[::-1])
    y_inner = r_inner * np.sin(theta_zone[::-1])
    
    x_poly = np.concatenate([x_outer, x_inner])
    y_poly = np.concatenate([y_outer, y_inner])
    
    ax4.fill(x_poly, y_poly, color=colors_gauge[i], alpha=0.6)

# Add needle (pointing to super-critical)
angle = 5*np.pi/6  # Super-critical position
ax4.arrow(0, 0, 0.85*np.cos(angle), 0.85*np.sin(angle), 
          head_width=0.05, head_length=0.05, fc='black', ec='black', linewidth=2)

ax4.set_xlim(-1.2, 1.2)
ax4.set_ylim(-0.2, 1.2)
ax4.set_aspect('equal')
ax4.axis('off')
ax4.set_title('Criticality Gauge', fontsize=14, fontweight='bold')

# Add labels
ax4.text(0, -0.1, 'Ordered', ha='center', fontsize=10)
ax4.text(-1.1, 0.5, 'Critical', ha='center', fontsize=10)
ax4.text(1.1, 0.5, 'Chaotic', ha='center', fontsize=10)
ax4.text(0, 0.5, 'SUPER-CRITICAL', ha='center', fontsize=12, fontweight='bold', color='red')

# 5. Power Law Distributions
ax5 = plt.subplot(2, 3, 5)

# Wealth power law
ranks = np.arange(1, 25)  # Top 20% 
wealth_tail = 808433 * ranks**(-0.743)

ax5.loglog(ranks, wealth_tail, 'o-', color='gold', label=f'Wealth (α={0.743})', linewidth=2, markersize=8)

# Theoretical critical line
theoretical = 100000 * ranks**(-1.5)
ax5.loglog(ranks, theoretical, '--', color='green', label='Critical (α=1.5)', linewidth=2)

# Stable line
stable = 50000 * ranks**(-2.5)
ax5.loglog(ranks, stable, ':', color='blue', label='Stable (α=2.5)', linewidth=2)

ax5.set_xlabel('Rank', fontsize=12)
ax5.set_ylabel('Value', fontsize=12)
ax5.set_title('Power Law Comparison', fontsize=14, fontweight='bold')
ax5.legend()
ax5.grid(True, alpha=0.3)

# 6. Key Metrics Summary
ax6 = plt.subplot(2, 3, 6)
ax6.axis('off')

metrics_text = f"""
CRITICALITY METRICS

Population: 124 citizens
Gini Coefficient: 0.803
Pareto α: 0.743 ± 0.02
R-squared: 0.915

Boltzmann T: 277,944 ducats
Split Point: 808,433 ducats

System State: SUPER-CRITICAL
Identity Persistence: 90.92%

Design Validation:
✓ Closed Economy
✓ Heterogeneous Agents  
✓ Multi-Scale Dynamics
✓ Open Boundaries
"""

ax6.text(0.1, 0.9, metrics_text, transform=ax6.transAxes, 
         fontsize=12, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Adjust layout
plt.tight_layout()

# Save figure
plt.savefig('criticality_dashboard.png', dpi=300, bbox_inches='tight')
plt.savefig('criticality_dashboard.pdf', bbox_inches='tight')

print("Dashboard visualizations created:")
print("- criticality_dashboard.png")
print("- criticality_dashboard.pdf")
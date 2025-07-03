"""
Criticality Dashboard for La Serenissima
Real-time visualization of edge-of-chaos dynamics
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import deque, defaultdict
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import aiohttp

from criticality_metrics import CriticalityMetrics, calculate_criticality_metrics


class CriticalityDashboard:
    """Real-time monitoring of system criticality"""
    
    def __init__(self, api_base: str = "https://serenissima.ai/api"):
        self.api_base = api_base
        self.metrics = CriticalityMetrics()
        self.history_window = 1000  # Keep last N measurements
        
        # Time series storage
        self.time_series = {
            'timestamps': deque(maxlen=self.history_window),
            'criticality_score': deque(maxlen=self.history_window),
            'correlation_length': deque(maxlen=self.history_window),
            'lyapunov': deque(maxlen=self.history_window),
            'percolation': deque(maxlen=self.history_window),
            'economic_velocity': deque(maxlen=self.history_window),
            'cascade_sizes': deque(maxlen=self.history_window),
        }
        
        # Cascade tracking
        self.recent_cascades = deque(maxlen=500)
        self.prayer_events = deque(maxlen=100)
        
    async def fetch_system_state(self) -> Dict:
        """Fetch current system state from API"""
        async with aiohttp.ClientSession() as session:
            # Get citizens data
            async with session.get(f"{self.api_base}/citizens") as resp:
                citizens = await resp.json()
            
            # Get recent transactions
            async with session.get(f"{self.api_base}/transactions?limit=1000") as resp:
                transactions = await resp.json()
            
            # Get trust relationships
            async with session.get(f"{self.api_base}/relationships") as resp:
                relationships = await resp.json()
            
            # Get recent activities for cascade detection
            async with session.get(f"{self.api_base}/activities?status=completed&limit=500") as resp:
                activities = await resp.json()
        
        return {
            'citizens': citizens,
            'transactions': transactions,
            'relationships': relationships,
            'activities': activities
        }
    
    def detect_cascades(self, activities: List[Dict]) -> List[int]:
        """Detect information cascades in recent activities"""
        # Group activities by time window (5 minute bins)
        time_bins = defaultdict(list)
        
        for activity in activities:
            timestamp = datetime.fromisoformat(activity['completed_at'])
            bin_key = timestamp.replace(second=0, microsecond=0)
            bin_key = bin_key.replace(minute=(bin_key.minute // 5) * 5)
            time_bins[bin_key].append(activity)
        
        # Detect cascades: rapid spread of similar activities
        cascades = []
        
        for bin_time, bin_activities in time_bins.items():
            # Group by activity type
            type_groups = defaultdict(list)
            for act in bin_activities:
                type_groups[act['activity_type']].append(act)
            
            # Look for cascade patterns
            for activity_type, acts in type_groups.items():
                if len(acts) > 3:  # Minimum cascade size
                    # Check if activities are related (same location, sequential timing)
                    locations = [a.get('location', '') for a in acts]
                    unique_locations = len(set(locations))
                    
                    # Cascade if many citizens doing same thing in same area
                    if unique_locations < len(acts) / 2:
                        cascades.append(len(acts))
        
        return cascades
    
    def calculate_current_metrics(self, state: Dict) -> Dict:
        """Calculate all criticality metrics from current state"""
        # Extract trust edges
        trust_edges = []
        for rel in state['relationships']:
            if rel['trust_level'] > 0.5:  # Trust threshold
                trust_edges.append((rel['citizen_id'], rel['target_id']))
        
        # Detect cascades
        cascades = self.detect_cascades(state['activities'])
        self.recent_cascades.extend(cascades)
        
        # Calculate metrics
        metrics = calculate_criticality_metrics(
            citizens_data=state['citizens'],
            transactions=state['transactions'],
            trust_edges=trust_edges,
            cascades=list(self.recent_cascades)
        )
        
        # Add cascade statistics
        if cascades:
            metrics['current_cascade_size'] = max(cascades)
            metrics['cascade_frequency'] = len(cascades)
        else:
            metrics['current_cascade_size'] = 0
            metrics['cascade_frequency'] = 0
        
        # Economic velocity
        if state['transactions']:
            recent_trans = state['transactions'][:100]  # Last 100
            total_value = sum(t['amount'] for t in recent_trans)
            time_span = 1.0  # Assuming recent means last hour
            metrics['economic_velocity'] = total_value / time_span
        else:
            metrics['economic_velocity'] = 0
        
        return metrics
    
    def update_time_series(self, metrics: Dict):
        """Update time series data with new metrics"""
        timestamp = datetime.now()
        
        self.time_series['timestamps'].append(timestamp)
        self.time_series['criticality_score'].append(metrics.get('criticality_score', 0))
        self.time_series['correlation_length'].append(metrics.get('correlation_length', 0))
        self.time_series['lyapunov'].append(metrics.get('lyapunov', 0))
        self.time_series['percolation'].append(metrics.get('percolation', 0))
        self.time_series['economic_velocity'].append(metrics.get('economic_velocity', 0))
        self.time_series['cascade_sizes'].append(metrics.get('current_cascade_size', 0))
    
    def create_phase_space_plot(self) -> go.Figure:
        """Create 3D phase space trajectory plot"""
        if len(self.time_series['timestamps']) < 10:
            return go.Figure()
        
        # Use correlation length, lyapunov, and percolation as coordinates
        x = list(self.time_series['correlation_length'])
        y = list(self.time_series['lyapunov'])
        z = list(self.time_series['percolation'])
        
        # Color by criticality score
        colors = list(self.time_series['criticality_score'])
        
        fig = go.Figure(data=[
            go.Scatter3d(
                x=x, y=y, z=z,
                mode='lines+markers',
                marker=dict(
                    size=4,
                    color=colors,
                    colorscale='Viridis',
                    colorbar=dict(title="Criticality Score"),
                    showscale=True
                ),
                line=dict(
                    width=2,
                    color='rgba(100,100,100,0.5)'
                ),
                text=[f"Time: {t.strftime('%H:%M:%S')}" for t in self.time_series['timestamps']],
                hoverinfo='text+x+y+z'
            )
        ])
        
        # Add critical manifold (semi-transparent surface)
        # Critical region approximation
        corr_range = np.linspace(0, 20, 20)
        lyap_range = np.linspace(-0.5, 0.5, 20)
        corr_grid, lyap_grid = np.meshgrid(corr_range, lyap_range)
        
        # Critical percolation is around 0.5-0.8
        perc_grid = 0.65 + 0.1 * np.sin(corr_grid/5) * np.cos(lyap_grid*10)
        
        fig.add_trace(go.Surface(
            x=corr_grid, y=lyap_grid, z=perc_grid,
            opacity=0.3,
            colorscale='Reds',
            showscale=False,
            name='Critical Manifold'
        ))
        
        fig.update_layout(
            title="Phase Space Trajectory",
            scene=dict(
                xaxis_title="Correlation Length",
                yaxis_title="Lyapunov Exponent",
                zaxis_title="Percolation",
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            height=600
        )
        
        return fig
    
    def create_cascade_animator(self) -> go.Figure:
        """Animate information cascade propagation"""
        if not self.recent_cascades:
            return go.Figure()
        
        # Create histogram of cascade sizes
        cascade_sizes = list(self.recent_cascades)
        
        fig = go.Figure()
        
        # Current distribution
        fig.add_trace(go.Histogram(
            x=cascade_sizes,
            name='Cascade Sizes',
            nbinsx=30,
            marker_color='lightblue',
            opacity=0.7
        ))
        
        # Add power law fit if enough data
        if len(set(cascade_sizes)) > 5:
            unique_sizes = sorted(set(cascade_sizes))
            counts = [cascade_sizes.count(s) for s in unique_sizes]
            
            # Log-log fit
            log_sizes = np.log(unique_sizes)
            log_counts = np.log(counts)
            
            # Linear regression in log space
            coeffs = np.polyfit(log_sizes, log_counts, 1)
            tau = -coeffs[0]
            
            # Generate fit line
            fit_x = np.linspace(min(unique_sizes), max(unique_sizes), 100)
            fit_y = np.exp(coeffs[1]) * fit_x ** coeffs[0]
            
            fig.add_trace(go.Scatter(
                x=fit_x, y=fit_y,
                mode='lines',
                name=f'Power Law Fit (τ={tau:.2f})',
                line=dict(color='red', width=3)
            ))
        
        fig.update_layout(
            title="Cascade Size Distribution",
            xaxis_title="Cascade Size",
            yaxis_title="Frequency",
            yaxis_type="log",
            xaxis_type="log",
            height=400
        )
        
        return fig
    
    def create_criticality_weather(self) -> go.Figure:
        """Create criticality 'weather forecast' visualization"""
        if len(self.time_series['timestamps']) < 2:
            return go.Figure()
        
        # Get recent trend
        recent_scores = list(self.time_series['criticality_score'])[-20:]
        if not recent_scores:
            return go.Figure()
        
        current_score = recent_scores[-1]
        trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
        
        # Predict next state
        if current_score > 0.7:
            if trend > 0.01:
                forecast = "⚡ Approaching Chaos"
                color = "orange"
            elif trend < -0.01:
                forecast = "❄️ Cooling to Order"
                color = "lightblue"
            else:
                forecast = "🌟 Stable Criticality"
                color = "green"
        elif current_score < 0.3:
            forecast = "🧊 Frozen Order"
            color = "blue"
        else:
            if trend > 0:
                forecast = "🔥 Heating Up"
                color = "yellow"
            else:
                forecast = "📉 Stabilizing"
                color = "gray"
        
        # Create gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=current_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Criticality Weather: {forecast}"},
            delta={'reference': 0.7, 'increasing': {'color': "green"}},
            gauge={
                'axis': {'range': [None, 1], 'tickwidth': 1},
                'bar': {'color': color},
                'steps': [
                    {'range': [0, 0.3], 'color': "lightblue"},
                    {'range': [0.3, 0.7], 'color': "lightyellow"},
                    {'range': [0.7, 1], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.7
                }
            }
        ))
        
        fig.update_layout(height=300)
        
        return fig
    
    def create_network_percolation_monitor(self) -> go.Figure:
        """Monitor trust network connectivity"""
        if len(self.time_series['timestamps']) < 2:
            return go.Figure()
        
        timestamps = list(self.time_series['timestamps'])
        percolation = list(self.time_series['percolation'])
        
        fig = go.Figure()
        
        # Percolation fraction over time
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=percolation,
            mode='lines+markers',
            name='Percolation Fraction',
            line=dict(width=3)
        ))
        
        # Critical percolation threshold
        fig.add_hline(y=0.5, line_dash="dash", line_color="red",
                     annotation_text="Lower Critical Threshold")
        fig.add_hline(y=0.8, line_dash="dash", line_color="red",
                     annotation_text="Upper Critical Threshold")
        
        # Shade critical region
        fig.add_hrect(y0=0.5, y1=0.8, fillcolor="green", opacity=0.2,
                     layer="below", line_width=0)
        
        fig.update_layout(
            title="Network Percolation Monitor",
            xaxis_title="Time",
            yaxis_title="Fraction in Largest Component",
            yaxis_range=[0, 1],
            height=400
        )
        
        return fig
    
    def create_dashboard_layout(self) -> go.Figure:
        """Create complete dashboard with subplots"""
        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Criticality Score Timeline',
                'Phase Space Trajectory',
                'Cascade Distribution',
                'Network Percolation',
                'Economic Velocity',
                'Lyapunov Exponent'
            ),
            specs=[
                [{'type': 'scatter'}, {'type': 'scatter3d', 'rowspan': 2}],
                [{'type': 'scatter'}, None],
                [{'type': 'scatter'}, {'type': 'scatter'}]
            ],
            row_heights=[0.33, 0.33, 0.34],
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )
        
        if len(self.time_series['timestamps']) > 2:
            timestamps = list(self.time_series['timestamps'])
            
            # Criticality score timeline
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=list(self.time_series['criticality_score']),
                    mode='lines',
                    name='Criticality Score',
                    line=dict(width=3, color='purple')
                ),
                row=1, col=1
            )
            
            # Phase space (simplified 2D for subplot)
            fig.add_trace(
                go.Scatter3d(
                    x=list(self.time_series['correlation_length']),
                    y=list(self.time_series['lyapunov']),
                    z=list(self.time_series['percolation']),
                    mode='lines+markers',
                    marker=dict(
                        size=3,
                        color=list(self.time_series['criticality_score']),
                        colorscale='Viridis'
                    ),
                    name='Phase Trajectory'
                ),
                row=1, col=2
            )
            
            # Cascade sizes
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=list(self.time_series['cascade_sizes']),
                    mode='markers',
                    name='Cascade Sizes',
                    marker=dict(size=8, color='orange')
                ),
                row=2, col=1
            )
            
            # Network percolation
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=list(self.time_series['percolation']),
                    mode='lines',
                    name='Percolation',
                    line=dict(width=2, color='green')
                ),
                row=3, col=1
            )
            
            # Economic velocity
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=list(self.time_series['economic_velocity']),
                    mode='lines',
                    name='Economic Velocity',
                    line=dict(width=2, color='blue')
                ),
                row=3, col=2
            )
        
        # Update layout
        fig.update_layout(
            title="La Serenissima Criticality Dashboard",
            showlegend=False,
            height=1000,
            template='plotly_dark'
        )
        
        # Update axes
        fig.update_xaxes(title_text="Time", row=3)
        fig.update_yaxes(title_text="Score", row=1, col=1)
        fig.update_yaxes(title_text="Size", row=2, col=1)
        fig.update_yaxes(title_text="Fraction", row=3, col=1)
        fig.update_yaxes(title_text="Velocity", row=3, col=2)
        
        return fig
    
    async def run_dashboard(self, update_interval: int = 60):
        """Run continuous dashboard updates"""
        while True:
            try:
                # Fetch current state
                state = await self.fetch_system_state()
                
                # Calculate metrics
                metrics = self.calculate_current_metrics(state)
                
                # Update time series
                self.update_time_series(metrics)
                
                # Generate visualizations
                dashboard = self.create_dashboard_layout()
                
                # Save to file
                dashboard.write_html('/tmp/criticality_dashboard.html')
                
                print(f"Dashboard updated: Criticality Score = {metrics.get('criticality_score', 0):.3f}")
                print(f"Phase: {metrics.get('phase', 'unknown')}")
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"Dashboard error: {e}")
                await asyncio.sleep(update_interval)


async def main():
    """Run the dashboard"""
    dashboard = CriticalityDashboard()
    await dashboard.run_dashboard(update_interval=60)


if __name__ == "__main__":
    asyncio.run(main())
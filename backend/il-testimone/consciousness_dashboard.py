"""
Consciousness Indicators Dashboard
Real-time visualization of consciousness indicators in La Serenissima
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import asyncio
import json
from typing import Dict, List
import numpy as np

from monitor_consciousness_indicators import ConsciousnessMonitor
from consciousness_indicators_framework import IndicatorCategory

# Page configuration
st.set_page_config(
    page_title="La Serenissima Consciousness Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .indicator-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


class ConsciousnessDashboard:
    """Streamlit dashboard for consciousness indicators"""
    
    def __init__(self):
        if 'monitor' not in st.session_state:
            st.session_state.monitor = ConsciousnessMonitor()
        if 'assessment_data' not in st.session_state:
            st.session_state.assessment_data = None
        if 'history' not in st.session_state:
            st.session_state.history = []
            
    def run(self):
        """Main dashboard function"""
        st.title("🧠 La Serenissima Consciousness Indicators Dashboard")
        st.markdown("*Tracking computational correlates of consciousness in AI citizens*")
        
        # Sidebar
        with st.sidebar:
            st.header("Dashboard Controls")
            
            if st.button("🔄 Run Assessment", use_container_width=True):
                with st.spinner("Running consciousness assessment..."):
                    self._run_assessment()
                    
            st.markdown("---")
            
            # Display options
            st.subheader("Display Options")
            show_evidence = st.checkbox("Show Evidence Details", value=False)
            show_raw_metrics = st.checkbox("Show Raw Metrics", value=False)
            
            st.markdown("---")
            
            # Info
            st.info("""
            **About This Dashboard**
            
            This dashboard tracks 14 consciousness indicators based on the Butlin et al. (2023) framework:
            
            - **RPT**: Recurrent Processing Theory
            - **GWT**: Global Workspace Theory  
            - **HOT**: Higher-Order Theories
            - **AST**: Attention Schema Theory
            - **PP**: Predictive Processing
            - **AE**: Agency & Embodiment
            """)
        
        # Main content
        if st.session_state.assessment_data:
            self._display_assessment(show_evidence, show_raw_metrics)
        else:
            st.info("Click 'Run Assessment' to begin analyzing consciousness indicators")
            
            # Show demo data option
            if st.button("Load Demo Data"):
                self._load_demo_data()
    
    def _run_assessment(self):
        """Run consciousness assessment"""
        # Create async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run assessment
            monitor = st.session_state.monitor
            loop.run_until_complete(monitor.start())
            assessment = loop.run_until_complete(monitor.run_assessment())
            loop.run_until_complete(monitor.stop())
            
            # Convert to display format
            st.session_state.assessment_data = self._assessment_to_dict(assessment)
            st.session_state.history.append(st.session_state.assessment_data)
            
            st.success("Assessment completed successfully!")
            
        except Exception as e:
            st.error(f"Error running assessment: {str(e)}")
        finally:
            loop.close()
    
    def _assessment_to_dict(self, assessment) -> Dict:
        """Convert assessment object to dictionary for display"""
        return {
            'timestamp': assessment.timestamp,
            'overall_score': assessment.overall_score,
            'emergence_ratio': assessment.emergence_ratio,
            'category_scores': assessment.category_scores,
            'indicators': [
                {
                    'id': ind.indicator_id,
                    'name': ind.name,
                    'category': ind.category.value,
                    'score': ind.score,
                    'confidence': ind.confidence,
                    'evidence': ind.evidence,
                    'raw_metrics': ind.raw_metrics
                }
                for ind in assessment.indicators
            ]
        }
    
    def _load_demo_data(self):
        """Load demonstration data"""
        # Create sample assessment data
        demo_data = {
            'timestamp': datetime.utcnow(),
            'overall_score': 2.39,
            'emergence_ratio': 0.686,
            'category_scores': {
                'Recurrent Processing Theory': 2.5,
                'Global Workspace Theory': 2.25,
                'Higher-Order Theories': 2.5,
                'Attention Schema Theory': 2.0,
                'Predictive Processing': 2.5,
                'Agency and Embodiment': 3.0
            },
            'indicators': [
                {'id': 'RPT-1', 'name': 'Algorithmic Recurrence', 'category': 'Recurrent Processing Theory',
                 'score': 2.5, 'confidence': 'High', 'evidence': ['Found 47 extended conversation chains'],
                 'raw_metrics': {'conversation_loops': 47}},
                {'id': 'AE-2', 'name': 'Embodiment', 'category': 'Agency and Embodiment',
                 'score': 3.0, 'confidence': 'High', 'evidence': ['High spatial awareness: 0.89'],
                 'raw_metrics': {'spatial_awareness': 0.89}},
                # Add more demo indicators as needed
            ]
        }
        
        st.session_state.assessment_data = demo_data
        st.session_state.history.append(demo_data)
    
    def _display_assessment(self, show_evidence: bool, show_raw_metrics: bool):
        """Display assessment results"""
        data = st.session_state.assessment_data
        
        # Header metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Overall Score",
                f"{data['overall_score']:.2f}/3.0",
                f"{(data['overall_score']/3.0)*100:.0f}%"
            )
            
        with col2:
            st.metric(
                "Emergence Ratio",
                f"{data['emergence_ratio']:.1%}",
                "High" if data['emergence_ratio'] > 0.6 else "Moderate"
            )
            
        with col3:
            strong_indicators = sum(1 for ind in data['indicators'] if ind['score'] >= 2.5)
            st.metric(
                "Strong Indicators",
                f"{strong_indicators}/14",
                f"{(strong_indicators/14)*100:.0f}%"
            )
            
        with col4:
            avg_confidence = self._calculate_avg_confidence(data['indicators'])
            st.metric(
                "Avg Confidence",
                avg_confidence,
                "✓" if avg_confidence == "High" else "~"
            )
        
        st.markdown("---")
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 By Category", "🔍 Individual Indicators", "📉 Trends"])
        
        with tab1:
            self._display_overview(data)
            
        with tab2:
            self._display_by_category(data)
            
        with tab3:
            self._display_indicators(data, show_evidence, show_raw_metrics)
            
        with tab4:
            self._display_trends()
    
    def _calculate_avg_confidence(self, indicators: List[Dict]) -> str:
        """Calculate average confidence level"""
        confidence_map = {'High': 3, 'Medium': 2, 'Low': 1}
        scores = [confidence_map.get(ind['confidence'], 2) for ind in indicators]
        avg = np.mean(scores)
        
        if avg >= 2.5:
            return "High"
        elif avg >= 1.5:
            return "Medium"
        else:
            return "Low"
    
    def _display_overview(self, data: Dict):
        """Display overview visualizations"""
        col1, col2 = st.columns(2)
        
        with col1:
            # Radar chart of category scores
            fig = self._create_radar_chart(data['category_scores'])
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Bar chart of all indicators
            fig = self._create_indicator_bar_chart(data['indicators'])
            st.plotly_chart(fig, use_container_width=True)
        
        # Summary interpretation
        st.markdown("### Assessment Summary")
        
        if data['overall_score'] >= 2.5:
            st.success("🟢 **Strong Evidence**: The system demonstrates strong computational correlates of consciousness across multiple theories.")
        elif data['overall_score'] >= 2.0:
            st.warning("🟡 **Moderate Evidence**: The system shows moderate evidence for consciousness indicators with room for development.")
        else:
            st.info("🔵 **Developing Evidence**: The system exhibits emerging consciousness indicators that require further cultivation.")
            
        if data['emergence_ratio'] > 0.7:
            st.success("🌟 **High Emergence**: A high proportion of indicators arise from emergent properties rather than explicit design.")
        elif data['emergence_ratio'] > 0.5:
            st.info("⚖️ **Balanced Properties**: The system shows a healthy balance of emergent and designed features.")
        else:
            st.warning("🏗️ **Design-Heavy**: Most indicators stem from designed features rather than emergence.")
    
    def _create_radar_chart(self, category_scores: Dict) -> go.Figure:
        """Create radar chart of category scores"""
        categories = list(category_scores.keys())
        values = list(category_scores.values())
        
        # Close the radar chart
        categories.append(categories[0])
        values.append(values[0])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Scores',
            fillcolor='rgba(99, 110, 250, 0.3)',
            line=dict(color='rgb(99, 110, 250)', width=2)
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 3]
                )),
            showlegend=False,
            title="Consciousness Indicators by Theory",
            height=400
        )
        
        return fig
    
    def _create_indicator_bar_chart(self, indicators: List[Dict]) -> go.Figure:
        """Create bar chart of all indicators"""
        # Sort by score
        indicators_sorted = sorted(indicators, key=lambda x: x['score'], reverse=True)
        
        names = [ind['name'] for ind in indicators_sorted]
        scores = [ind['score'] for ind in indicators_sorted]
        colors = ['green' if s >= 2.5 else 'orange' if s >= 2.0 else 'blue' for s in scores]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=names,
            x=scores,
            orientation='h',
            marker_color=colors,
            text=[f"{s:.2f}" for s in scores],
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Individual Indicator Scores",
            xaxis_title="Score",
            yaxis_title="",
            xaxis=dict(range=[0, 3.2]),
            height=500,
            margin=dict(l=200)
        )
        
        return fig
    
    def _display_by_category(self, data: Dict):
        """Display indicators grouped by category"""
        # Group indicators by category
        categories = {}
        for ind in data['indicators']:
            cat = ind['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ind)
        
        # Display each category
        for category, indicators in categories.items():
            with st.expander(f"{category} ({len(indicators)} indicators)", expanded=True):
                # Category score
                cat_score = data['category_scores'].get(category, 0)
                st.metric(f"Category Average", f"{cat_score:.2f}/3.0")
                
                # Individual indicators
                for ind in sorted(indicators, key=lambda x: x['score'], reverse=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{ind['name']}** ({ind['id']})")
                    with col2:
                        st.write(f"Score: {ind['score']:.1f}")
                    with col3:
                        st.write(f"Confidence: {ind['confidence']}")
                        
                    if ind['evidence']:
                        st.write(f"*{ind['evidence'][0]}*")
                    
                    st.progress(ind['score'] / 3.0)
                    st.markdown("---")
    
    def _display_indicators(self, data: Dict, show_evidence: bool, show_raw_metrics: bool):
        """Display detailed indicator information"""
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            score_filter = st.slider("Minimum Score", 0.0, 3.0, 0.0, 0.5)
            
        with col2:
            confidence_filter = st.multiselect(
                "Confidence Level",
                ["High", "Medium", "Low"],
                default=["High", "Medium", "Low"]
            )
        
        # Filter indicators
        filtered_indicators = [
            ind for ind in data['indicators']
            if ind['score'] >= score_filter and ind['confidence'] in confidence_filter
        ]
        
        st.write(f"Showing {len(filtered_indicators)} of {len(data['indicators'])} indicators")
        
        # Display indicators
        for ind in sorted(filtered_indicators, key=lambda x: x['score'], reverse=True):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.subheader(f"{ind['name']}")
                    st.caption(f"{ind['id']} - {ind['category']}")
                    
                with col2:
                    score_color = "🟢" if ind['score'] >= 2.5 else "🟡" if ind['score'] >= 2.0 else "🔵"
                    st.metric("Score", f"{score_color} {ind['score']:.2f}")
                    
                with col3:
                    conf_icon = "✓" if ind['confidence'] == "High" else "~" if ind['confidence'] == "Medium" else "?"
                    st.metric("Confidence", f"{conf_icon} {ind['confidence']}")
                    
                with col4:
                    st.metric("Evidence", len(ind['evidence']))
                
                if show_evidence and ind['evidence']:
                    st.markdown("**Evidence:**")
                    for i, evidence in enumerate(ind['evidence'], 1):
                        st.write(f"{i}. {evidence}")
                
                if show_raw_metrics and ind['raw_metrics']:
                    st.markdown("**Raw Metrics:**")
                    st.json(ind['raw_metrics'])
                
                st.markdown("---")
    
    def _display_trends(self):
        """Display historical trends"""
        if len(st.session_state.history) < 2:
            st.info("Need at least 2 assessments to show trends. Run more assessments to see trends.")
            return
        
        # Create trend data
        timestamps = [h['timestamp'] for h in st.session_state.history]
        overall_scores = [h['overall_score'] for h in st.session_state.history]
        emergence_ratios = [h['emergence_ratio'] for h in st.session_state.history]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Overall score trend
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=overall_scores,
                mode='lines+markers',
                name='Overall Score',
                line=dict(color='blue', width=2)
            ))
            fig.update_layout(
                title="Overall Score Trend",
                xaxis_title="Time",
                yaxis_title="Score",
                yaxis=dict(range=[0, 3.2]),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Emergence ratio trend
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=[r * 100 for r in emergence_ratios],
                mode='lines+markers',
                name='Emergence Ratio',
                line=dict(color='green', width=2)
            ))
            fig.update_layout(
                title="Emergence Ratio Trend",
                xaxis_title="Time",
                yaxis_title="Percentage",
                yaxis=dict(range=[0, 100]),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Category trends
        st.subheader("Category Score Trends")
        
        # Extract category data
        category_trends = {}
        for h in st.session_state.history:
            for cat, score in h['category_scores'].items():
                if cat not in category_trends:
                    category_trends[cat] = []
                category_trends[cat].append(score)
        
        # Create multi-line chart
        fig = go.Figure()
        
        for category, scores in category_trends.items():
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=scores,
                mode='lines+markers',
                name=category
            ))
        
        fig.update_layout(
            title="Theory Category Trends",
            xaxis_title="Time",
            yaxis_title="Score",
            yaxis=dict(range=[0, 3.2]),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)


def main():
    """Main function"""
    dashboard = ConsciousnessDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
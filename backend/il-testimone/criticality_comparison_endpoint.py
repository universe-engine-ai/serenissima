"""
Criticality Comparison Endpoint
Runs both backend and frontend-style criticality analyses for comparison
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
import numpy as np
import networkx as nx
from datetime import datetime
import traceback

# Import existing and new modules
from .criticality_metrics import CriticalityMetrics, calculate_criticality_metrics
from .criticality_fixes import (
    UnifiedCriticalityMetrics, 
    CriticalityDataAdapter,
    BranchingRatioCalculator
)

# Import database access (adjust based on actual project structure)
# from app.database import get_airtable_client
# from app.services import fetch_messages, fetch_contracts, fetch_citizens, fetch_relationships

router = APIRouter()


@router.get("/criticality/compare")
async def compare_criticality_systems(
    limit: int = 500,
    time_window_minutes: int = 60
) -> Dict:
    """
    Compare results from backend and frontend criticality systems
    
    Returns side-by-side comparison of metrics from both approaches
    """
    try:
        # Fetch data from API/Database
        # In production, replace with actual data fetching
        messages = await fetch_messages_data(limit)
        contracts = await fetch_contracts_data()
        citizens = await fetch_citizens_data()
        relationships = await fetch_relationships_data()
        
        # Initialize analyzers
        backend_analyzer = CriticalityMetrics()
        unified_analyzer = UnifiedCriticalityMetrics()
        adapter = CriticalityDataAdapter()
        
        # Convert data for backend system
        citizen_states = adapter.citizens_to_nodes(citizens)
        transactions = adapter.contracts_to_transactions(contracts)
        trust_edges = adapter.extract_trust_edges(relationships)
        cascades = adapter.detect_cascades(
            adapter.messages_to_events(messages), 
            time_window_minutes
        )
        
        # Run backend analysis
        backend_results = calculate_criticality_metrics(
            citizens_data=citizen_states,
            transactions=transactions,
            trust_edges=trust_edges,
            cascades=cascades
        )
        
        # Run unified (frontend-style) analysis
        unified_results = unified_analyzer.calculate_unified_metrics(
            messages=messages,
            contracts=contracts,
            citizens=citizens,
            relationships=relationships
        )
        
        # Create comparison report
        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "data_summary": {
                "messages_analyzed": len(messages),
                "transactions_analyzed": len(transactions),
                "citizens_analyzed": len(citizens),
                "trust_edges_analyzed": len(trust_edges)
            },
            "backend_system": {
                "approach": "Physics-inspired complex systems theory",
                "metrics": {
                    "correlation_length": backend_results.get('correlation_length', 0),
                    "lyapunov_exponent": backend_results.get('lyapunov', 0),
                    "information_entropy": backend_results.get('information_entropy', 0),
                    "avalanche_tau": backend_results.get('avalanche_tau', 0),
                    "avalanche_r2": backend_results.get('avalanche_r2', 0),
                    "percolation": backend_results.get('percolation', 0),
                    "economic_volatility": backend_results.get('economic_volatility', 0),
                    "criticality_score": backend_results.get('criticality_score', 0),
                    "phase": backend_results.get('phase', 'unknown')
                }
            },
            "frontend_system": {
                "approach": "Data-driven observable patterns",
                "metrics": {
                    "message_branching_ratio": unified_results['message_branching']['current'],
                    "economic_branching_ratio": unified_results['economic_branching']['current'],
                    "message_cascade_count": unified_results['cascades']['message_cascades']['count'],
                    "max_cascade_size": unified_results['cascades']['message_cascades']['max_size'],
                    "cascade_power_law_tau": unified_results['cascades']['message_cascades']['power_law']['tau'],
                    "gini_coefficient": unified_results['economic']['gini_coefficient'],
                    "money_velocity": unified_results['economic']['money_velocity'],
                    "phase": unified_results['phase']
                }
            },
            "convergence_analysis": {
                "phase_agreement": backend_results.get('phase') == unified_results['phase'],
                "criticality_indicators": {
                    "backend_critical": backend_results.get('criticality_score', 0) > 0.7,
                    "frontend_critical": unified_results['phase'] == 'critical',
                    "agreement": None  # Will be calculated
                },
                "key_differences": []
            }
        }
        
        # Analyze convergence
        comparison['convergence_analysis']['criticality_indicators']['agreement'] = (
            comparison['convergence_analysis']['criticality_indicators']['backend_critical'] ==
            comparison['convergence_analysis']['criticality_indicators']['frontend_critical']
        )
        
        # Identify key differences
        differences = []
        
        # Check branching ratio vs Lyapunov
        if unified_results['message_branching']['current'] is not None:
            if abs(unified_results['message_branching']['current'] - 1.0) < 0.1:
                differences.append("Frontend shows critical branching ratio (~1.0)")
            if abs(backend_results.get('lyapunov', 0)) > 0.1:
                differences.append("Backend shows non-zero Lyapunov exponent (chaotic/stable)")
        
        # Check cascade detection
        backend_cascade_count = len(cascades)
        frontend_cascade_count = unified_results['cascades']['message_cascades']['count']
        if abs(backend_cascade_count - frontend_cascade_count) > 10:
            differences.append(f"Cascade detection differs: Backend={backend_cascade_count}, Frontend={frontend_cascade_count}")
        
        # Check power law fits
        if (backend_results.get('avalanche_tau', 0) > 0 and 
            unified_results['cascades']['message_cascades']['power_law']['tau'] > 0):
            tau_diff = abs(backend_results['avalanche_tau'] - 
                          unified_results['cascades']['message_cascades']['power_law']['tau'])
            if tau_diff > 0.3:
                differences.append(f"Power law exponents differ by {tau_diff:.2f}")
        
        comparison['convergence_analysis']['key_differences'] = differences
        
        # Add recommendations
        comparison['recommendations'] = generate_recommendations(comparison)
        
        return comparison
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/criticality/unified")
async def get_unified_criticality(
    include_time_series: bool = False
) -> Dict:
    """
    Get criticality analysis using the unified approach
    Combines best of both backend and frontend systems
    """
    try:
        # Fetch data
        messages = await fetch_messages_data(500)
        contracts = await fetch_contracts_data()
        citizens = await fetch_citizens_data()
        relationships = await fetch_relationships_data()
        
        # Run unified analysis
        analyzer = UnifiedCriticalityMetrics()
        results = analyzer.calculate_unified_metrics(
            messages=messages,
            contracts=contracts,
            citizens=citizens,
            relationships=relationships
        )
        
        # Optionally remove time series data for lighter response
        if not include_time_series:
            results['message_branching'].pop('time_series', None)
            results['economic_branching'].pop('time_series', None)
        
        return {
            "success": True,
            "timestamp": results['timestamp'],
            "criticality": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


def generate_recommendations(comparison: Dict) -> List[str]:
    """Generate recommendations based on comparison results"""
    recommendations = []
    
    # Phase agreement
    if not comparison['convergence_analysis']['phase_agreement']:
        recommendations.append(
            "Systems disagree on phase classification. Review threshold parameters and ensure consistent time windows."
        )
    
    # Criticality agreement
    if not comparison['convergence_analysis']['criticality_indicators']['agreement']:
        recommendations.append(
            "Systems disagree on criticality state. Consider implementing cross-validation between metrics."
        )
    
    # Branching ratio
    if comparison['frontend_system']['metrics']['message_branching_ratio'] is None:
        recommendations.append(
            "Message branching ratio not calculated. Ensure sufficient message data with reply relationships."
        )
    
    # Missing backend branching
    recommendations.append(
        "Backend system lacks direct branching ratio calculation. Use unified metrics for complete analysis."
    )
    
    # Data quality
    if comparison['data_summary']['messages_analyzed'] < 100:
        recommendations.append(
            "Low message count may affect cascade detection accuracy. Consider longer time windows."
        )
    
    return recommendations


# Mock data fetching functions - replace with actual implementation
async def fetch_messages_data(limit: int) -> List[Dict]:
    """Fetch messages from database/API"""
    # Implementation depends on project structure
    # return await get_messages(limit=limit)
    return []

async def fetch_contracts_data() -> List[Dict]:
    """Fetch contracts from database/API"""
    # return await get_contracts()
    return []

async def fetch_citizens_data() -> List[Dict]:
    """Fetch citizens from database/API"""
    # return await get_citizens()
    return []

async def fetch_relationships_data() -> List[Dict]:
    """Fetch relationships from database/API"""
    # return await get_relationships()
    return []


# Integration instructions for main.py
"""
To integrate this endpoint into the main FastAPI app:

1. In backend/app/main.py, add:

from il_testimone.criticality_comparison_endpoint import router as criticality_router

app.include_router(
    criticality_router,
    prefix="/api/analysis",
    tags=["criticality"]
)

2. The endpoints will be available at:
   - GET /api/analysis/criticality/compare
   - GET /api/analysis/criticality/unified

3. Update the data fetching functions to use actual database connections
"""
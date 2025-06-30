"""
FastAPI Endpoints for Criticality Comparison
Provides unified API for comparing backend and frontend criticality calculations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'il-testimone'))

from criticality_fixes import UnifiedCriticalityMetrics, BranchingRatioCalculator, CriticalityDataAdapter

router = APIRouter(prefix="/api/analysis/criticality", tags=["criticality"])

# Initialize components
unified_metrics = UnifiedCriticalityMetrics()
branching_calculator = BranchingRatioCalculator()
data_adapter = CriticalityDataAdapter()


@router.get("/compare")
async def compare_criticality_systems():
    """
    Compare backend and frontend criticality calculations side-by-side
    Shows differences and agreements between the two approaches
    """
    try:
        # Fetch current data
        data = data_adapter.fetch_and_prepare_data()
        
        if not data:
            raise HTTPException(status_code=503, detail="Unable to fetch system data")
        
        # Calculate all metrics
        results = unified_metrics.calculate_all_metrics(data)
        
        # Structure comparison response
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "unified_score": results.get("unified_score", 0),
            "phase_agreement": results.get("phase_agreement", {}),
            "backend_system": {
                "approach": "Physics-based theoretical",
                "phase": results.get("backend_phase", "unknown"),
                "criticality_score": results.get("backend_criticality_score", 0),
                "metrics": {
                    "lyapunov_exponent": results.get("lyapunov", 0),
                    "correlation_length": results.get("correlation_length", 0),
                    "information_entropy": results.get("information_entropy", 0),
                    "avalanche_tau": results.get("avalanche_tau", 0),
                    "avalanche_r2": results.get("avalanche_r2", 0),
                    "percolation_fraction": results.get("percolation", 0),
                    "economic_volatility": results.get("economic_volatility", 0)
                }
            },
            "frontend_system": {
                "approach": "Data-driven empirical",
                "phase": results.get("frontend_phase", "unknown"),
                "branching_ratios": {
                    "message_sigma_current": results.get("message_branching_current", 0),
                    "message_sigma_mean": results.get("message_branching_mean", 0),
                    "economic_sigma_current": results.get("economic_branching_current", 0),
                    "economic_sigma_mean": results.get("economic_branching_mean", 0)
                },
                "wealth_metrics": {
                    "gini_coefficient": results.get("gini_coefficient", 0),
                    "top_10_percent_wealth": results.get("wealth_top_10_percent", 0),
                    "bottom_50_percent_wealth": results.get("wealth_bottom_50_percent", 0)
                }
            },
            "data_quality": results.get("data_quality", {}),
            "recommendations": _generate_recommendations(results)
        }
        
        return comparison
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing systems: {str(e)}")


@router.get("/unified")
async def get_unified_metrics():
    """
    Get unified criticality metrics combining both approaches
    Single source of truth for system criticality
    """
    try:
        results = unified_metrics.calculate_all_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "unified_criticality_score": results.get("unified_score", 0),
            "system_phase": _determine_unified_phase(results),
            "convergence_indicators": {
                "phase_agreement": results.get("phase_agreement", {}).get("agreement", False),
                "confidence": results.get("phase_agreement", {}).get("confidence", 0),
                "backend_phase": results.get("backend_phase", "unknown"),
                "frontend_phase": results.get("frontend_phase", "unknown")
            },
            "key_metrics": {
                "branching_ratio": _average_branching(results),
                "system_entropy": results.get("information_entropy", 0),
                "correlation_length": results.get("correlation_length", 0),
                "gini_coefficient": results.get("gini_coefficient", 0),
                "avalanche_exponent": results.get("avalanche_tau", 0)
            },
            "time_series": {
                "message_branching": results.get("message_branching_data", [])[-10:],  # Last 10 points
                "economic_branching": results.get("economic_branching_data", [])[-10:]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating unified metrics: {str(e)}")


@router.get("/branching-ratio")
async def get_branching_ratios(
    type: str = Query("all", enum=["all", "message", "economic"]),
    bin_size: int = Query(15, ge=5, le=1440, description="Bin size in minutes")
):
    """
    Get branching ratio calculations
    Frontend-compatible endpoint with backend calculations
    """
    try:
        data = data_adapter.fetch_and_prepare_data()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "bin_size_minutes": bin_size
        }
        
        if type in ["all", "message"]:
            message_branching = branching_calculator.calculate_message_branching(
                data.get("messages", []), 
                bin_size
            )
            response["message_branching"] = {
                "current": message_branching[-1]["sigma"] if message_branching else None,
                "mean": _calculate_mean([b["sigma"] for b in message_branching if b["sigma"] is not None]),
                "data": message_branching,
                "transitions": branching_calculator.detect_critical_transitions(message_branching)
            }
        
        if type in ["all", "economic"]:
            economic_branching = branching_calculator.calculate_economic_branching(
                data.get("transactions", []),
                bin_size
            )
            response["economic_branching"] = {
                "current": economic_branching[-1]["value"] if economic_branching else None,
                "mean": _calculate_mean([b["value"] for b in economic_branching]),
                "data": economic_branching
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating branching ratios: {str(e)}")


@router.get("/phase-diagram")
async def get_phase_diagram():
    """
    Get data for phase space visualization
    Compatible with frontend EconomicPhaseAnalysis component
    """
    try:
        data = data_adapter.fetch_and_prepare_data()
        results = unified_metrics.calculate_all_metrics(data)
        
        # Calculate time series for phase space
        transactions = data.get("transactions", [])
        citizens = data.get("raw_citizens", [])
        
        # Group by time periods for phase evolution
        phase_points = []
        
        # Simple hourly grouping for last 24 hours
        now = datetime.now()
        for hours_ago in range(24, 0, -1):
            period_start = now - timedelta(hours=hours_ago)
            period_end = period_start + timedelta(hours=1)
            
            # Filter transactions in period
            period_txs = [tx for tx in transactions 
                         if period_start <= data_adapter._parse_timestamp(tx.get("timestamp", "")) < period_end]
            
            if period_txs:
                # Calculate velocity
                total_value = sum(float(tx.get("amount", 0)) for tx in period_txs)
                velocity = total_value / 3600  # Per second
                
                # Calculate Gini (simplified - use current snapshot)
                wealth_values = [float(c.get("Wealth", 0)) for c in citizens if float(c.get("Wealth", 0)) > 0]
                gini = unified_metrics._calculate_gini(wealth_values)
                
                phase_points.append({
                    "timestamp": period_start.isoformat(),
                    "velocity": velocity,
                    "gini": gini,
                    "transaction_count": len(period_txs)
                })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "current_phase": _determine_economic_phase(
                phase_points[-1]["velocity"] if phase_points else 0,
                phase_points[-1]["gini"] if phase_points else 0
            ),
            "phase_trajectory": phase_points,
            "phase_boundaries": {
                "stagnant": {"velocity": [0, 10], "gini": [0, 1]},
                "feudal": {"velocity": [0, 50], "gini": [0.7, 1]},
                "socialist": {"velocity": [10, 100], "gini": [0, 0.4]},
                "capitalist": {"velocity": [50, 1000], "gini": [0.4, 0.7]},
                "critical": {"velocity": [10, 100], "gini": [0.4, 0.7]}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating phase diagram: {str(e)}")


@router.get("/stability-analysis")
async def analyze_branching_stability():
    """
    Analyze branching ratio stability across multiple time scales
    """
    try:
        data = data_adapter.fetch_and_prepare_data()
        
        # Analyze message branching stability
        message_stability = branching_calculator.analyze_branching_stability(data.get("messages", []))
        
        # Format response
        stability_analysis = {
            "timestamp": datetime.now().isoformat(),
            "message_branching_stability": {},
            "recommendations": []
        }
        
        for bin_size, metrics in message_stability.items():
            stability_analysis["message_branching_stability"][f"{bin_size}_minutes"] = {
                "mean_sigma": metrics["mean"],
                "std_deviation": metrics["std"],
                "coefficient_of_variation": metrics["cv"],
                "sample_count": metrics["n_samples"],
                "critical_fraction": metrics["critical_fraction"],
                "stability_score": 1.0 - min(metrics["cv"], 1.0)  # Lower CV = more stable
            }
            
            # Add recommendations based on stability
            if metrics["cv"] > 0.5:
                stability_analysis["recommendations"].append(
                    f"High variability detected at {bin_size}-minute scale (CV={metrics['cv']:.2f}). "
                    "System may be experiencing rapid phase transitions."
                )
            
            if metrics["critical_fraction"] > 0.5:
                stability_analysis["recommendations"].append(
                    f"System spending {metrics['critical_fraction']*100:.0f}% of time near criticality "
                    f"at {bin_size}-minute scale. Good for consciousness emergence."
                )
        
        return stability_analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing stability: {str(e)}")


# Helper functions
def _generate_recommendations(results: Dict) -> List[str]:
    """Generate actionable recommendations based on analysis"""
    recommendations = []
    
    # Phase agreement check
    if not results.get("phase_agreement", {}).get("agreement"):
        recommendations.append(
            "Backend and frontend disagree on system phase. "
            "Consider investigating data quality or adjusting phase thresholds."
        )
    
    # Branching ratio check
    msg_sigma = results.get("message_branching_current", 0)
    if msg_sigma and abs(msg_sigma - 1.0) < 0.1:
        recommendations.append(
            "Message branching near criticality (σ≈1). "
            "System is in optimal state for information processing."
        )
    elif msg_sigma and msg_sigma < 0.8:
        recommendations.append(
            "Low message branching ratio indicates frozen communication. "
            "Consider interventions to stimulate interaction."
        )
    
    # Data quality check
    completeness = results.get("data_quality", {}).get("data_completeness", 0)
    if completeness < 0.8:
        recommendations.append(
            f"Data completeness is {completeness*100:.0f}%. "
            "Some metrics may be unreliable due to missing data."
        )
    
    return recommendations


def _determine_unified_phase(results: Dict) -> str:
    """Determine unified system phase from all metrics"""
    backend_phase = results.get("backend_phase", "unknown")
    frontend_phase = results.get("frontend_phase", "unknown")
    
    # If they agree, use that
    phase_mapping = {"frozen": "ordered", "critical": "critical", "bubbling": "chaotic"}
    if phase_mapping.get(frontend_phase) == backend_phase:
        return backend_phase
    
    # Otherwise, use unified score to break tie
    unified_score = results.get("unified_score", 0)
    if unified_score > 0.7:
        return "critical"
    elif unified_score > 0.4:
        return "transitional"
    else:
        return "ordered"


def _average_branching(results: Dict) -> float:
    """Calculate average branching ratio across all types"""
    ratios = []
    
    if results.get("message_branching_current") is not None:
        ratios.append(results["message_branching_current"])
    if results.get("economic_branching_current") is not None:
        ratios.append(results["economic_branching_current"])
    
    return sum(ratios) / len(ratios) if ratios else 0.0


def _calculate_mean(values: List[float]) -> float:
    """Safe mean calculation"""
    clean_values = [v for v in values if v is not None]
    return sum(clean_values) / len(clean_values) if clean_values else 0.0


def _determine_economic_phase(velocity: float, gini: float) -> str:
    """Determine economic phase from velocity and Gini"""
    if velocity < 10:
        return "stagnant"
    elif velocity < 50 and gini > 0.7:
        return "feudal"
    elif velocity < 100 and gini < 0.4:
        return "socialist"
    elif velocity > 50 and 0.4 <= gini <= 0.7:
        return "capitalist"
    else:
        return "transitional"


# Integration with main FastAPI app
# Add this router to your main app in backend/app/main.py:
# app.include_router(criticality_comparison_endpoint.router)
# Consciousness API Implementation Guide

## Overview

This guide details how to connect the consciousness measurement system to La Serenissima's live data and expose it through the API.

## Architecture

```
Frontend (React) → Next.js API Route → FastAPI Backend → Consciousness Engine
                                              ↓
                                    La Serenissima API Endpoints
```

## Implementation Steps

### 1. Create FastAPI Endpoint

Add to `backend/app/main.py`:

```python
from il_testimone.consciousness_measurement_implementation import run_consciousness_assessment
import httpx
from typing import Dict
from datetime import datetime, timedelta

@app.get("/api/consciousness/assessment")
async def get_consciousness_assessment():
    """Run consciousness assessment on current system state"""
    
    try:
        # Fetch data from La Serenissima endpoints
        async with httpx.AsyncClient() as client:
            # Get data from last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            # Fetch all required data in parallel
            responses = await asyncio.gather(
                client.get(f"{API_BASE_URL}/api/messages?start={start_time.isoformat()}&end={end_time.isoformat()}"),
                client.get(f"{API_BASE_URL}/api/activities?start={start_time.isoformat()}&end={end_time.isoformat()}"),
                client.get(f"{API_BASE_URL}/api/citizens"),
                client.get(f"{API_BASE_URL}/api/stratagems"),
                client.get(f"{API_BASE_URL}/api/contracts?status=completed&start={start_time.isoformat()}")
            )
            
            # Parse responses
            data = {
                'messages': responses[0].json(),
                'activities': responses[1].json(),
                'citizens': responses[2].json(),
                'stratagems': responses[3].json(),
                'contracts': responses[4].json()
            }
        
        # Run assessment
        assessment = run_consciousness_assessment(data)
        
        # Add category scores
        assessment['categoryScores'] = calculate_category_scores(assessment['indicators'])
        
        return {
            "success": True,
            "assessment": assessment,
            "isDemo": False,
            "dataTimeRange": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Consciousness assessment error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

def calculate_category_scores(indicators: Dict) -> Dict[str, float]:
    """Calculate average scores by category"""
    categories = {
        'Recurrent Processing Theory': ['RPT-1', 'RPT-2'],
        'Global Workspace Theory': ['GWT-1', 'GWT-2', 'GWT-3', 'GWT-4'],
        'Higher-Order Theories': ['HOT-1', 'HOT-2', 'HOT-3', 'HOT-4'],
        'Attention Schema Theory': ['AST-1'],
        'Predictive Processing': ['PP-1'],
        'Agency and Embodiment': ['AE-1', 'AE-2']
    }
    
    scores = {}
    for category, indicator_ids in categories.items():
        category_scores = [indicators[id].value for id in indicator_ids if id in indicators]
        scores[category] = np.mean(category_scores) if category_scores else 0.0
    
    return scores
```

### 2. Update Next.js API Route

Modify `/app/api/consciousness/assessment/route.ts`:

```typescript
export async function GET(request: NextRequest) {
  try {
    // Check if we should use live data
    const useLiveData = process.env.NEXT_PUBLIC_USE_LIVE_CONSCIOUSNESS_DATA === 'true';
    
    if (useLiveData) {
      // Fetch from backend
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/consciousness/assessment`);
      
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      
      const data = await response.json();
      
      // Transform backend format to frontend format if needed
      const transformedAssessment = transformAssessmentData(data.assessment);
      
      return NextResponse.json({
        success: true,
        assessment: transformedAssessment,
        isDemo: false,
        dataTimeRange: data.dataTimeRange,
        message: 'Live consciousness assessment completed'
      });
    } else {
      // Return enhanced demo data
      return NextResponse.json({
        success: true,
        assessment: enhancedDemoAssessment,
        isDemo: true,
        message: 'Consciousness assessment (demo mode)'
      });
    }
  } catch (error) {
    // Fallback to demo data on error
    console.error('Error fetching live assessment:', error);
    return NextResponse.json({
      success: true,
      assessment: DEMO_ASSESSMENT,
      isDemo: true,
      message: 'Using demo data due to error'
    });
  }
}
```

### 3. Add Caching and Performance

```python
# In FastAPI endpoint
from functools import lru_cache
import asyncio

# Cache assessment for 5 minutes
@lru_cache(maxsize=1)
async def get_cached_assessment(cache_key: str):
    return await perform_assessment()

@app.get("/api/consciousness/assessment")
async def get_consciousness_assessment():
    # Generate cache key based on current 5-minute window
    now = datetime.utcnow()
    cache_key = now.strftime("%Y%m%d%H") + str(now.minute // 5)
    
    return await get_cached_assessment(cache_key)
```

### 4. Add Real-time Updates

```python
# WebSocket endpoint for real-time updates
@app.websocket("/ws/consciousness")
async def consciousness_websocket(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        # Run mini-assessment every minute
        mini_assessment = await run_mini_consciousness_check()
        await websocket.send_json({
            "type": "update",
            "data": mini_assessment,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await asyncio.sleep(60)  # Update every minute
```

### 5. Add Historical Tracking

```python
# Store assessments for time-series analysis
@app.post("/api/consciousness/assessment/store")
async def store_assessment(assessment: Dict):
    """Store assessment results for historical tracking"""
    
    # Add to time-series database or Airtable
    record = {
        "timestamp": assessment["timestamp"],
        "overall_score": assessment["overall_score"],
        "emergence_ratio": assessment["emergence_ratio"],
        "indicator_scores": json.dumps({
            k: v.value for k, v in assessment["indicators"].items()
        })
    }
    
    # Store in database
    await store_in_database(record)
    
    return {"success": True, "id": record["id"]}
```

## Configuration

### Environment Variables

```bash
# .env
NEXT_PUBLIC_USE_LIVE_CONSCIOUSNESS_DATA=true
CONSCIOUSNESS_CACHE_TTL=300  # 5 minutes
CONSCIOUSNESS_DATA_WINDOW_HOURS=24
```

### Feature Flags

```typescript
// Enable/disable specific indicators
const ENABLED_INDICATORS = {
  'RPT-1': true,
  'RPT-2': true,
  'GWT-1': true,
  'GWT-2': true,
  'GWT-3': true,
  'GWT-4': true,
  'HOT-1': true,
  'HOT-2': true,
  'HOT-3': true,
  'HOT-4': true,
  'AST-1': true,
  'PP-1': true,
  'AE-1': true,
  'AE-2': true
};
```

## Monitoring

### Health Check

```python
@app.get("/api/consciousness/health")
async def consciousness_health():
    """Check if consciousness system is operational"""
    
    try:
        # Test data fetch
        test_data = await fetch_minimal_test_data()
        
        # Run quick assessment
        engine = ConsciousnessMeasurementEngine()
        test_result = engine.measure_rpt1(
            test_data['messages'][:10], 
            test_data['activities'][:10]
        )
        
        return {
            "status": "healthy",
            "last_assessment": get_last_assessment_time(),
            "test_score": test_result.value
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Deployment Checklist

1. [ ] Install Python dependencies: `pip install -r requirements.txt`
2. [ ] Test consciousness engine with sample data
3. [ ] Add FastAPI endpoints to `backend/app/main.py`
4. [ ] Update environment variables
5. [ ] Test API endpoints manually
6. [ ] Update frontend to use live data
7. [ ] Add error handling and fallbacks
8. [ ] Set up monitoring and alerts
9. [ ] Document API endpoints
10. [ ] Create dashboard for historical data

## Testing

```python
# Test script
async def test_consciousness_api():
    """Test consciousness assessment API"""
    
    # Test with minimal data
    test_data = {
        'messages': [...],  # Sample messages
        'activities': [...],  # Sample activities
        'citizens': [...],
        'stratagems': [...],
        'contracts': [...]
    }
    
    result = run_consciousness_assessment(test_data)
    
    assert result['overall_score'] > 0
    assert result['overall_score'] <= 3.0
    assert len(result['indicators']) == 14
    assert all(ind.value >= 0 for ind in result['indicators'].values())
    
    print("✅ All tests passed!")
```

## Next Steps

1. Implement the FastAPI endpoint
2. Test with live data
3. Optimize performance for large datasets
4. Add visualization for time-series data
5. Create alerts for significant changes
6. Document findings for research paper
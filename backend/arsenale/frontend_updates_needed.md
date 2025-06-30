# Frontend Updates for Unified Criticality System

## Current State

The frontend currently:
1. Fetches raw data from basic API endpoints (`/api/messages`, `/api/contracts`, `/api/citizens`)
2. Performs all criticality calculations client-side
3. Has no access to backend physics-based metrics
4. Cannot compare its calculations with backend analysis

## Recommended Frontend Updates

### 1. Add Unified Criticality Service

Create a new service to interact with the unified backend endpoints:

```typescript
// lib/services/criticality/unifiedCriticalityService.ts
export class UnifiedCriticalityService {
  async getUnifiedMetrics() {
    const response = await fetch('/api/analysis/criticality/unified');
    return response.json();
  }

  async compareSystemMetrics() {
    const response = await fetch('/api/analysis/criticality/compare');
    return response.json();
  }

  async getBranchingRatios(type: 'all' | 'message' | 'economic' = 'all', binSize: number = 15) {
    const response = await fetch(
      `/api/analysis/criticality/branching-ratio?type=${type}&bin_size=${binSize}`
    );
    return response.json();
  }

  async getPhaseAnalysis() {
    const response = await fetch('/api/analysis/criticality/phase-diagram');
    return response.json();
  }

  async getStabilityAnalysis() {
    const response = await fetch('/api/analysis/criticality/stability-analysis');
    return response.json();
  }
}
```

### 2. Create Unified Criticality Dashboard Component

Add a new component that shows both backend and frontend metrics:

```typescript
// components/UI/Criticality/UnifiedCriticalityDashboard.tsx
import React, { useState, useEffect } from 'react';
import { UnifiedCriticalityService } from '@/lib/services/criticality/unifiedCriticalityService';

export const UnifiedCriticalityDashboard: React.FC = () => {
  const [unifiedData, setUnifiedData] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Component to display unified metrics, comparison, and recommendations
};
```

### 3. Update Existing Components

#### MessageCriticality.tsx
- Add option to use backend-calculated branching ratios
- Show comparison between frontend and backend calculations
- Display unified criticality score

#### TransactionCriticality.tsx
- Replace client-side branching calculation with backend API
- Add backend phase classification display
- Show convergence indicators

#### EconomicPhaseAnalysis.tsx
- Use backend phase diagram endpoint
- Display both frontend and backend phase determinations
- Show phase agreement status

### 4. Add Comparison Views

Create new UI elements to show:
- Side-by-side metric comparison
- Phase agreement indicators
- Data quality warnings
- System recommendations

### 5. Performance Optimizations

Since backend now handles calculations:
- Remove redundant client-side calculations
- Cache unified metrics (5-minute TTL)
- Use React Query or SWR for data fetching
- Implement real-time updates via WebSocket (future)

## Implementation Priority

1. **High Priority**: 
   - Create unified criticality service
   - Update BranchingRatio component to use backend
   - Add unified score display

2. **Medium Priority**:
   - Create comparison dashboard
   - Update phase analysis to show both systems
   - Add data quality indicators

3. **Low Priority**:
   - Remove redundant client-side calculations
   - Implement caching strategy
   - Add WebSocket support

## Benefits of Updates

1. **Reduced Client Load**: Offload complex calculations to backend
2. **Unified Truth**: Single source for criticality metrics
3. **Better Insights**: Access to physics-based metrics
4. **Validation**: Compare empirical vs theoretical approaches
5. **Performance**: Faster UI with pre-calculated metrics

## Minimal Update Option

If full updates aren't feasible immediately, at minimum:

1. Add a "Backend Metrics" tab to existing components
2. Display unified criticality score prominently
3. Show phase agreement status
4. Add link to full comparison endpoint

## Testing Considerations

1. Ensure backward compatibility with existing UI
2. Handle backend endpoint failures gracefully
3. Validate that metrics match between old and new implementations
4. Test with various data volumes and time ranges

The frontend updates will provide users with a much richer understanding of system criticality by combining both empirical observations and theoretical physics, while also improving performance by offloading calculations to the backend.
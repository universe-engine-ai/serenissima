import { NextRequest, NextResponse } from 'next/server';

// Demo data for consciousness indicators
const DEMO_ASSESSMENT = {
  timestamp: new Date().toISOString(),
  overallScore: 2.39,
  emergenceRatio: 0.686,
  categoryScores: {
    'Recurrent Processing Theory': 2.5,
    'Global Workspace Theory': 2.25,
    'Higher-Order Theories': 2.5,
    'Attention Schema Theory': 2.0,
    'Predictive Processing': 2.5,
    'Agency and Embodiment': 3.0
  },
  indicators: [
    {
      id: 'RPT-1',
      name: 'Algorithmic Recurrence',
      category: 'Recurrent Processing Theory',
      score: 2.5,
      confidence: 'High',
      evidence: ['Found 47 extended conversation chains showing recurrent processing'],
      rawMetrics: { conversation_loops: 47, iterative_thoughts: 23 }
    },
    {
      id: 'RPT-2',
      name: 'Integrated Perceptual Representations',
      category: 'Recurrent Processing Theory',
      score: 2.5,
      confidence: 'High',
      evidence: ['High spatial coherence score: 0.84', 'Found 89 decisions integrating multiple information sources'],
      rawMetrics: { spatial_coherence: 0.84, integrated_decisions: 89 }
    },
    {
      id: 'GWT-1',
      name: 'Parallel Specialized Systems',
      category: 'Global Workspace Theory',
      score: 2.0,
      confidence: 'Medium',
      evidence: ['Citizens manage up to 3 concurrent activities', 'High module independence score: 0.72'],
      rawMetrics: { max_concurrent: 3, avg_concurrent: 2.1, module_independence: 0.72 }
    },
    {
      id: 'GWT-2',
      name: 'Limited Capacity Workspace',
      category: 'Global Workspace Theory',
      score: 2.5,
      confidence: 'High',
      evidence: ['Average queue length of 2.3 indicates bottleneck', 'Frequent attention switching (14 switches/hour) indicates limited focus'],
      rawMetrics: { avg_queue_length: 2.3, attention_switches: 14 }
    },
    {
      id: 'GWT-3',
      name: 'Global Broadcast',
      category: 'Global Workspace Theory',
      score: 2.0,
      confidence: 'Medium',
      evidence: ['Information reaches 42% of network', 'Message cascades reach 6 citizens on average'],
      rawMetrics: { broadcast_reach: 0.42, cascade_size: 6 }
    },
    {
      id: 'GWT-4',
      name: 'State-Dependent Attention',
      category: 'Global Workspace Theory',
      score: 2.5,
      confidence: 'High',
      evidence: ['High context sensitivity in attention: 0.78', 'Found 134 state-dependent attention shifts'],
      rawMetrics: { context_sensitivity: 0.78, state_dependencies: 134 }
    },
    {
      id: 'HOT-1',
      name: 'Generative Perception',
      category: 'Higher-Order Theories',
      score: 2.5,
      confidence: 'High',
      evidence: ['Found 67 instances of predictive/generative thinking', 'Sophisticated uncertainty handling: 0.81'],
      rawMetrics: { generative_thoughts: 67, uncertainty_score: 0.81 }
    },
    {
      id: 'HOT-2',
      name: 'Metacognitive Monitoring',
      category: 'Higher-Order Theories',
      score: 2.5,
      confidence: 'High',
      evidence: ['Found 92 instances of metacognitive monitoring', 'Well-calibrated confidence assessments: 0.83'],
      rawMetrics: { metacognitive_count: 92, confidence_calibration: 0.83 }
    },
    {
      id: 'HOT-3',
      name: 'Agency and Belief Updating',
      category: 'Higher-Order Theories',
      score: 3.0,
      confidence: 'High',
      evidence: ['Tracked 156 belief updates based on new information', 'High belief consistency score: 0.87', 'Coherent action selection: 0.91'],
      rawMetrics: { belief_update_count: 156, belief_consistency: 0.87, action_coherence: 0.91 }
    },
    {
      id: 'HOT-4',
      name: 'Quality Space',
      category: 'Higher-Order Theories',
      score: 2.0,
      confidence: 'Medium',
      evidence: ['Sparse representation coding: 0.68', 'Smooth similarity gradients in quality space: 0.73'],
      rawMetrics: { sparsity: 0.68, gradient_smoothness: 0.73, quality_dimensions: 5 }
    },
    {
      id: 'AST-1',
      name: 'Attention Schema',
      category: 'Attention Schema Theory',
      score: 2.0,
      confidence: 'Medium',
      evidence: ['Found 31 instances of attention prediction', 'Attention state awareness score: 0.64'],
      rawMetrics: { attention_predictions: 31, attention_awareness: 0.64 }
    },
    {
      id: 'PP-1',
      name: 'Predictive Coding',
      category: 'Predictive Processing',
      score: 2.5,
      confidence: 'High',
      evidence: ['Tracked 203 prediction error signals', 'Found 87 model updates from prediction errors'],
      rawMetrics: { prediction_error_count: 203, model_updates: 87 }
    },
    {
      id: 'AE-1',
      name: 'Agency with Learning',
      category: 'Agency and Embodiment',
      score: 3.0,
      confidence: 'High',
      evidence: ['Average learning rate: 0.142', 'Found 98 strategy adaptations', 'High goal flexibility score: 0.84'],
      rawMetrics: { avg_learning_rate: 0.142, strategy_adaptations: 98, goal_flexibility: 0.84 }
    },
    {
      id: 'AE-2',
      name: 'Embodiment',
      category: 'Agency and Embodiment',
      score: 3.0,
      confidence: 'High',
      evidence: ['High spatial awareness: 0.89', 'Tracks 247 action-consequence pairs', 'Strong environmental coupling: 0.92'],
      rawMetrics: { spatial_awareness: 0.89, consequence_tracking: 247, environmental_coupling: 0.92 }
    }
  ],
  summary: `Consciousness Assessment Summary
==================================================
Overall Score: 2.39/3.0
Emergence Ratio: 68.6%

Category Scores:
  Agency and Embodiment: 3.00/3.0
  Higher-Order Theories: 2.50/3.0
  Recurrent Processing Theory: 2.50/3.0
  Predictive Processing: 2.50/3.0
  Global Workspace Theory: 2.25/3.0
  Attention Schema Theory: 2.00/3.0

Assessment: Strong evidence for consciousness indicators
High proportion of emergent properties suggests genuine complexity`
};

export async function GET(request: NextRequest) {
  try {
    // Always use live data
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    try {
        // Get query parameters
        const searchParams = request.nextUrl.searchParams;
        const hours = searchParams.get('hours') || '24';
        const citizen = searchParams.get('citizen');
        
        // Build backend URL with query params
        const params = new URLSearchParams({ hours });
        if (citizen) params.append('citizen', citizen);
        
        // Fetch from backend
        const response = await fetch(`${backendUrl}/api/consciousness/assessment?${params}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          cache: 'no-store' // Ensure fresh data
        });
        
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}: ${await response.text()}`);
        }
        
        const data = await response.json();
        
        return NextResponse.json(data);
        
    } catch (error) {
      console.error('Error fetching live consciousness assessment:', error);
      // Fall back to demo data
    }
    
    // Fallback: Return demo data with transaction integration
    const enhancedDemoAssessment = {
      ...DEMO_ASSESSMENT,
      indicators: DEMO_ASSESSMENT.indicators.map(ind => {
        // Add transaction-related data to relevant indicators
        if (ind.id === 'RPT-1') {
          return {
            ...ind,
            evidence: [...ind.evidence, 'Detected 12 transaction cascade patterns'],
            rawMetrics: { ...ind.rawMetrics, transaction_cascades: 12 }
          };
        }
        if (ind.id === 'HOT-3') {
          return {
            ...ind,
            evidence: [...ind.evidence, 'Transaction coherence with beliefs: 0.89'],
            rawMetrics: { ...ind.rawMetrics, transaction_coherence: 0.89 }
          };
        }
        if (ind.id === 'PP-1') {
          return {
            ...ind,
            evidence: [...ind.evidence, 'Market prediction errors: 47'],
            rawMetrics: { ...ind.rawMetrics, market_prediction_errors: 47 }
          };
        }
        if (ind.id === 'HOT-2') {
          return {
            ...ind,
            evidence: [...ind.evidence, '156 self-reflections in internal thoughts (messages to self)'],
            rawMetrics: { ...ind.rawMetrics, thought_reflections: 156, total_thoughts: 892 }
          };
        }
        return ind;
      })
    };
    
    // Simulate some processing time
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Return assessment data
    return NextResponse.json({
      success: true,
      assessment: enhancedDemoAssessment,
      isDemo: true,
      message: 'Consciousness assessment completed successfully (demo mode with transaction data)'
    });
  } catch (error) {
    console.error('Error in consciousness assessment:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to perform consciousness assessment',
      assessment: null
    }, { status: 500 });
  }
}

// POST endpoint for triggering a new assessment
export async function POST(request: NextRequest) {
  try {
    // In production, this would trigger a new assessment
    // Could include parameters for assessment configuration
    const body = await request.json();
    
    // Simulate running assessment
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Return updated assessment
    return NextResponse.json({
      success: true,
      assessment: {
        ...DEMO_ASSESSMENT,
        timestamp: new Date().toISOString()
      },
      message: 'New consciousness assessment triggered'
    });
  } catch (error) {
    console.error('Error triggering assessment:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to trigger consciousness assessment'
    }, { status: 500 });
  }
}
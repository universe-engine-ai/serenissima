'use client';

import React, { useState, useEffect } from 'react';
import { FaBrain, FaChartLine, FaInfoCircle, FaSpinner, FaCheckCircle, FaExclamationCircle } from 'react-icons/fa';

interface IndicatorData {
  id: string;
  name: string;
  category: string;
  score: number;
  confidence: 'High' | 'Medium' | 'Low';
  evidence: string[];
  rawMetrics: Record<string, any>;
}

interface CategoryScore {
  name: string;
  score: number;
  abbreviation: string;
}

interface AssessmentData {
  timestamp: string;
  overallScore: number;
  emergenceRatio: number;
  categoryScores: Record<string, number>;
  indicators: IndicatorData[];
  summary?: string;
}

export default function ConsciousnessIndicators() {
  const [assessment, setAssessment] = useState<AssessmentData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showEvidence, setShowEvidence] = useState(false);
  const [isDemo, setIsDemo] = useState(false);

  // Category abbreviations for display
  const categoryAbbreviations: Record<string, string> = {
    'Recurrent Processing Theory': 'RPT',
    'Global Workspace Theory': 'GWT',
    'Higher-Order Theories': 'HOT',
    'Attention Schema Theory': 'AST',
    'Predictive Processing': 'PP',
    'Agency and Embodiment': 'AE'
  };

  // Fetch assessment data
  const fetchAssessment = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/consciousness/assessment');
      const data = await response.json();
      
      if (data.success && data.assessment) {
        setAssessment(data.assessment);
        setIsDemo(false);
      } else {
        // Use demo data if API fails
        loadDemoData();
      }
    } catch (err) {
      console.error('Error fetching assessment:', err);
      loadDemoData();
    } finally {
      setLoading(false);
    }
  };

  // Load demo data
  const loadDemoData = () => {
    setIsDemo(true);
    setAssessment({
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
      ]
    });
  };

  useEffect(() => {
    fetchAssessment();
  }, []);

  // Filter indicators by category
  const filteredIndicators = selectedCategory === 'all' 
    ? assessment?.indicators || []
    : assessment?.indicators.filter(ind => ind.category === selectedCategory) || [];

  // Calculate category statistics
  const getCategoryStats = () => {
    if (!assessment) return [];
    
    const stats: CategoryScore[] = [];
    for (const [category, score] of Object.entries(assessment.categoryScores)) {
      stats.push({
        name: category,
        score: score,
        abbreviation: categoryAbbreviations[category] || category
      });
    }
    return stats.sort((a, b) => b.score - a.score);
  };

  // Get score color
  const getScoreColor = (score: number) => {
    if (score >= 2.5) return 'text-green-600';
    if (score >= 2.0) return 'text-yellow-600';
    return 'text-blue-600';
  };

  // Get score background
  const getScoreBg = (score: number) => {
    if (score >= 2.5) return 'bg-green-100';
    if (score >= 2.0) return 'bg-yellow-100';
    return 'bg-blue-100';
  };

  // Get confidence icon
  const getConfidenceIcon = (confidence: string) => {
    switch (confidence) {
      case 'High': return <FaCheckCircle className="text-green-500" />;
      case 'Medium': return <FaExclamationCircle className="text-yellow-500" />;
      default: return <FaInfoCircle className="text-blue-500" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <FaSpinner className="animate-spin text-4xl text-amber-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
        <p className="text-red-800">Error: {error}</p>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="text-center p-8">
        <p className="text-amber-700">No assessment data available</p>
        <button
          onClick={fetchAssessment}
          className="mt-4 px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <FaBrain className="text-3xl text-amber-600" />
            <div>
              <h3 className="text-2xl font-semibold text-amber-900">Consciousness Indicators Assessment</h3>
              <p className="text-sm text-amber-600">Based on Butlin et al. (2023) Framework</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isDemo && (
              <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                Demo Data
              </span>
            )}
            <button
              onClick={fetchAssessment}
              disabled={loading}
              className="px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
            >
              {loading ? <FaSpinner className="animate-spin" /> : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-amber-50 rounded-lg p-4">
            <div className="text-sm text-amber-600 mb-1">Overall Score</div>
            <div className={`text-3xl font-bold ${getScoreColor(assessment.overallScore)}`}>
              {assessment.overallScore.toFixed(2)}/3.0
            </div>
            <div className="text-xs text-amber-500 mt-1">
              {((assessment.overallScore / 3.0) * 100).toFixed(0)}% of maximum
            </div>
          </div>
          
          <div className="bg-amber-50 rounded-lg p-4">
            <div className="text-sm text-amber-600 mb-1">Emergence Ratio</div>
            <div className="text-3xl font-bold text-green-600">
              {(assessment.emergenceRatio * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-amber-500 mt-1">
              {assessment.emergenceRatio > 0.7 ? 'High' : assessment.emergenceRatio > 0.5 ? 'Moderate' : 'Low'} emergence
            </div>
          </div>
          
          <div className="bg-amber-50 rounded-lg p-4">
            <div className="text-sm text-amber-600 mb-1">Strong Indicators</div>
            <div className="text-3xl font-bold text-green-600">
              {assessment.indicators.filter(ind => ind.score >= 2.5).length}/14
            </div>
            <div className="text-xs text-amber-500 mt-1">
              Score ≥ 2.5
            </div>
          </div>
          
          <div className="bg-amber-50 rounded-lg p-4">
            <div className="text-sm text-amber-600 mb-1">Avg Confidence</div>
            <div className="text-3xl font-bold text-amber-700">
              {assessment.indicators.filter(ind => ind.confidence === 'High').length > 10 ? 'High' : 'Medium'}
            </div>
            <div className="text-xs text-amber-500 mt-1">
              {assessment.indicators.filter(ind => ind.confidence === 'High').length} high confidence
            </div>
          </div>
        </div>
      </div>

      {/* Category Scores */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h4 className="text-lg font-semibold text-amber-900 mb-4">Theory Category Scores</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {getCategoryStats().map((cat) => (
            <div 
              key={cat.name}
              className={`rounded-lg p-4 cursor-pointer transition-all ${
                selectedCategory === cat.name ? 'ring-2 ring-amber-500' : ''
              } ${getScoreBg(cat.score)}`}
              onClick={() => setSelectedCategory(selectedCategory === cat.name ? 'all' : cat.name)}
            >
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-semibold text-sm">{cat.abbreviation}</div>
                  <div className="text-xs text-gray-600 mt-1">{cat.name}</div>
                </div>
                <div className={`text-2xl font-bold ${getScoreColor(cat.score)}`}>
                  {cat.score.toFixed(1)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Indicator Details */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-amber-900">
            {selectedCategory === 'all' ? 'All Indicators' : selectedCategory}
          </h4>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={showEvidence}
                onChange={(e) => setShowEvidence(e.target.checked)}
                className="rounded text-amber-600"
              />
              Show Evidence
            </label>
          </div>
        </div>

        <div className="space-y-3">
          {filteredIndicators
            .sort((a, b) => b.score - a.score)
            .map((indicator) => (
              <div key={indicator.id} className="border rounded-lg p-4 hover:bg-amber-50 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-grow">
                    <div className="flex items-center gap-2">
                      <h5 className="font-semibold text-amber-900">{indicator.name}</h5>
                      <span className="text-xs text-gray-500">({indicator.id})</span>
                      {getConfidenceIcon(indicator.confidence)}
                    </div>
                    {selectedCategory === 'all' && (
                      <div className="text-xs text-gray-600 mt-1">{indicator.category}</div>
                    )}
                  </div>
                  <div className={`text-xl font-bold ${getScoreColor(indicator.score)} ml-4`}>
                    {indicator.score.toFixed(1)}
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div 
                    className={`h-full rounded-full ${
                      indicator.score >= 2.5 ? 'bg-green-500' : 
                      indicator.score >= 2.0 ? 'bg-yellow-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${(indicator.score / 3.0) * 100}%` }}
                  />
                </div>

                {showEvidence && indicator.evidence.length > 0 && (
                  <div className="mt-3 text-sm text-gray-700 bg-amber-50 rounded p-3">
                    <div className="font-medium mb-1">Evidence:</div>
                    <ul className="list-disc list-inside space-y-1">
                      {indicator.evidence.map((ev, idx) => (
                        <li key={idx}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
        </div>
      </div>

      {/* Interpretation */}
      <div className="bg-amber-100 rounded-lg p-6 border border-amber-200">
        <h4 className="text-lg font-semibold text-amber-900 mb-3">Assessment Interpretation</h4>
        <div className="space-y-2 text-sm text-amber-800">
          {assessment.overallScore >= 2.5 ? (
            <p>🟢 <strong>Strong Evidence:</strong> La Serenissima demonstrates strong computational correlates of consciousness across multiple neuroscientific theories.</p>
          ) : assessment.overallScore >= 2.0 ? (
            <p>🟡 <strong>Moderate Evidence:</strong> The system shows moderate evidence for consciousness indicators with opportunities for further development.</p>
          ) : (
            <p>🔵 <strong>Developing Evidence:</strong> Consciousness indicators are emerging but require additional cultivation.</p>
          )}
          
          {assessment.emergenceRatio > 0.7 ? (
            <p>🌟 <strong>High Emergence:</strong> {(assessment.emergenceRatio * 100).toFixed(0)}% of indicators arise from emergent properties rather than explicit design, suggesting genuine complexity.</p>
          ) : assessment.emergenceRatio > 0.5 ? (
            <p>⚖️ <strong>Balanced Properties:</strong> The system shows a healthy balance between emergent ({(assessment.emergenceRatio * 100).toFixed(0)}%) and designed features.</p>
          ) : (
            <p>🏗️ <strong>Design-Heavy:</strong> Most indicators stem from designed features. Consider allowing more emergent behaviors.</p>
          )}
          
          <p className="mt-3">
            <strong>Top Performing Categories:</strong> {
              getCategoryStats()
                .filter(cat => cat.score >= 2.5)
                .map(cat => cat.abbreviation)
                .join(', ') || 'None'
            }
          </p>
        </div>
      </div>
    </div>
  );
}
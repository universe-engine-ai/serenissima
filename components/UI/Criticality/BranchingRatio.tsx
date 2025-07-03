'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { calculateBranchingRatio, type BranchingData } from '@/lib/services/criticality/branchingCalculator';

const TimeSeriesChart = dynamic(() => import('./charts/TimeSeriesChart'), { ssr: false });
const Histogram = dynamic(() => import('./charts/Histogram'), { ssr: false });

interface BranchingRatioProps {
  data: any;
}

export default function BranchingRatio({ data }: BranchingRatioProps) {
  const [branchingData, setBranchingData] = useState<BranchingData[]>([]);
  const [binSize, setBinSize] = useState(15); // minutes
  const [stats, setStats] = useState({
    currentSigma: 0,
    avgSigma: 0,
    stdSigma: 0,
    criticalPeriods: 0,
    totalPeriods: 0,
  });

  useEffect(() => {
    if (data?.messages) {
      const branching = calculateBranchingRatio(data.messages, binSize);
      setBranchingData(branching);
      calculateStats(branching);
    }
  }, [data, binSize]);

  const calculateStats = (branching: BranchingData[]) => {
    if (branching.length === 0) return;

    const sigmas = branching.map(b => b.sigma).filter(s => s !== null) as number[];
    const avg = sigmas.reduce((a, b) => a + b, 0) / sigmas.length;
    const variance = sigmas.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / sigmas.length;
    const std = Math.sqrt(variance);
    const critical = sigmas.filter(s => s >= 0.9 && s <= 1.1).length;

    setStats({
      currentSigma: sigmas[sigmas.length - 1] || 0,
      avgSigma: avg,
      stdSigma: std,
      criticalPeriods: critical,
      totalPeriods: sigmas.length,
    });
  };

  const binSizeOptions = [
    { value: 15, label: '15 minutes' },
    { value: 30, label: '30 minutes' },
    { value: 60, label: '1 hour' },
    { value: 240, label: '4 hours' },
  ];

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-amber-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-amber-800">Branching Parameter Analysis</h3>
          <div className="flex items-center gap-2">
            <label className="text-sm text-amber-700">Time Bin Size:</label>
            <select
              value={binSize}
              onChange={(e) => setBinSize(Number(e.target.value))}
              className="px-3 py-1 border border-amber-300 rounded text-sm"
            >
              {binSizeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Statistics Panel */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-amber-200">
          <h4 className="text-md font-semibold text-amber-800 mb-3">Current Status</h4>
          
          {/* Current Sigma with visual indicator */}
          <div className="mb-4">
            <p className="text-sm text-amber-600">Current σ</p>
            <div className="flex items-center gap-3">
              <p className="text-3xl font-bold text-amber-900">{stats.currentSigma.toFixed(3)}</p>
              <div className={`w-4 h-4 rounded-full ${
                stats.currentSigma >= 0.9 && stats.currentSigma <= 1.1 
                  ? 'bg-green-500' 
                  : stats.currentSigma < 0.9 
                  ? 'bg-blue-500' 
                  : 'bg-red-500'
              }`} />
            </div>
            <p className="text-xs text-amber-600 mt-1">
              {stats.currentSigma < 0.9 && 'Subcritical - Messages dying out'}
              {stats.currentSigma >= 0.9 && stats.currentSigma <= 1.1 && 'Critical - Optimal propagation'}
              {stats.currentSigma > 1.1 && 'Supercritical - Message explosion'}
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <p className="text-sm text-amber-600">Average σ</p>
              <p className="text-xl font-bold text-amber-900">{stats.avgSigma.toFixed(3)} ± {stats.stdSigma.toFixed(3)}</p>
            </div>
            <div>
              <p className="text-sm text-amber-600">Time at Criticality</p>
              <p className="text-xl font-bold text-amber-900">
                {((stats.criticalPeriods / stats.totalPeriods) * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-amber-600">{stats.criticalPeriods} of {stats.totalPeriods} periods</p>
            </div>
          </div>

          {/* Criticality Status */}
          <div className="mt-4 p-3 bg-amber-50 rounded border border-amber-300">
            <p className="text-sm font-medium text-amber-800">
              System Status: {
                Math.abs(stats.avgSigma - 1.0) < 0.1 
                  ? '✅ Self-Organized Critical' 
                  : '⚠️ Not Critical'
              }
            </p>
          </div>
        </div>

        {/* Time Series */}
        <div className="lg:col-span-2 bg-white p-4 rounded-lg shadow-sm border border-amber-200">
          <h4 className="text-md font-semibold text-amber-800 mb-3">Branching Parameter Time Series</h4>
          <div className="h-64">
            <TimeSeriesChart
              data={branchingData}
              yField="sigma"
              xlabel="Time"
              ylabel="σ (Branching Ratio)"
              criticalLine={1.0}
            />
          </div>
          <div className="mt-2 flex items-center justify-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-blue-500 rounded" />
              <span>Subcritical (σ &lt; 1)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded" />
              <span>Critical (σ ≈ 1)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500 rounded" />
              <span>Supercritical (σ &gt; 1)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Distribution Histogram */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-amber-200">
        <h4 className="text-md font-semibold text-amber-800 mb-3">σ Distribution</h4>
        <div className="h-64">
          <Histogram
            data={branchingData.map(b => b.sigma).filter(s => s !== null) as number[]}
            xlabel="Branching Ratio (σ)"
            ylabel="Frequency"
            bins={20}
            criticalLine={1.0}
          />
        </div>
        <p className="text-sm text-amber-600 mt-2">
          Distribution of branching ratios across all time periods. 
          A peak near σ = 1.0 indicates self-organized criticality.
        </p>
      </div>

      {/* Explanation */}
      <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
        <h4 className="font-semibold text-amber-800 mb-2">Understanding Branching Ratio</h4>
        <p className="text-sm text-amber-700 mb-2">
          The branching ratio (σ) measures how many new messages are triggered by each message on average:
        </p>
        <ul className="text-sm text-amber-700 space-y-1 ml-4">
          <li>• <strong>σ &lt; 1:</strong> Subcritical - Message chains die out exponentially</li>
          <li>• <strong>σ = 1:</strong> Critical - Message chains can propagate indefinitely</li>
          <li>• <strong>σ &gt; 1:</strong> Supercritical - Explosive growth in message activity</li>
        </ul>
        <p className="text-sm text-amber-700 mt-2">
          At criticality (σ ≈ 1), the system maximizes its dynamic range and information processing capacity.
        </p>
      </div>
    </div>
  );
}
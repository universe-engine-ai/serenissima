'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { analyzeCascades, type Cascade } from '@/lib/services/criticality/cascadeAnalyzer';

// Dynamically import chart components to avoid SSR issues
const LogLogPlot = dynamic(() => import('./charts/LogLogPlot'), { ssr: false });
const CascadeTree = dynamic(() => import('./charts/CascadeTree'), { ssr: false });

interface CascadeAnalysisProps {
  data: any;
}

export default function CascadeAnalysis({ data }: CascadeAnalysisProps) {
  const [cascades, setCascades] = useState<Cascade[]>([]);
  const [selectedCascade, setSelectedCascade] = useState<Cascade | null>(null);
  const [stats, setStats] = useState({
    totalCascades: 0,
    avgSize: 0,
    maxSize: 0,
    avgDepth: 0,
    maxDepth: 0,
    powerLawExponent: 0,
  });

  useEffect(() => {
    if (data?.messages) {
      const analyzedCascades = analyzeCascades(data.messages);
      setCascades(analyzedCascades);
      calculateStats(analyzedCascades);
      
      // Automatically select the largest cascade
      if (analyzedCascades.length > 0) {
        const sortedCascades = [...analyzedCascades].sort((a, b) => b.totalSize - a.totalSize);
        setSelectedCascade(sortedCascades[0]);
      }
    }
  }, [data]);

  const calculateStats = (cascades: Cascade[]) => {
    if (cascades.length === 0) return;

    const sizes = cascades.map(c => c.totalSize);
    const depths = cascades.map(c => c.depth);

    setStats({
      totalCascades: cascades.length,
      avgSize: sizes.reduce((a, b) => a + b, 0) / sizes.length,
      maxSize: Math.max(...sizes),
      avgDepth: depths.reduce((a, b) => a + b, 0) / depths.length,
      maxDepth: Math.max(...depths),
      powerLawExponent: calculatePowerLawExponent(sizes),
    });
  };

  const calculatePowerLawExponent = (sizes: number[]): number => {
    // Simple maximum likelihood estimation for power law exponent
    const minSize = Math.min(...sizes);
    const n = sizes.length;
    const sum = sizes.reduce((acc, size) => acc + Math.log(size / minSize), 0);
    return 1 + n / sum;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      {/* Left Column: Statistics and Distribution */}
      <div className="space-y-6">
        {/* Statistics Panel */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-amber-200">
          <h3 className="text-lg font-semibold text-amber-800 mb-3">Cascade Statistics</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-amber-600">Total Cascades</p>
              <p className="text-2xl font-bold text-amber-900">{stats.totalCascades}</p>
            </div>
            <div>
              <p className="text-sm text-amber-600">Average Size</p>
              <p className="text-2xl font-bold text-amber-900">{stats.avgSize.toFixed(1)}</p>
            </div>
            <div>
              <p className="text-sm text-amber-600">Max Size</p>
              <p className="text-2xl font-bold text-amber-900">{stats.maxSize}</p>
            </div>
            <div>
              <p className="text-sm text-amber-600">Power Law α</p>
              <p className="text-2xl font-bold text-amber-900">{stats.powerLawExponent.toFixed(2)}</p>
            </div>
          </div>
          
          {/* SOC Indicator */}
          <div className="mt-4 p-3 bg-amber-50 rounded border border-amber-300">
            <p className="text-sm font-medium text-amber-800">
              SOC Status: {Math.abs(stats.powerLawExponent - 1.5) < 0.3 ? '✅ Critical' : '⚠️ Non-critical'}
            </p>
            <p className="text-xs text-amber-700 mt-1">
              Expected α ≈ 1.5 for self-organized criticality
            </p>
          </div>
        </div>

        {/* Size Distribution Plot */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-amber-200">
          <h3 className="text-lg font-semibold text-amber-800 mb-3">Cascade Size Distribution</h3>
          <div className="h-64">
            <LogLogPlot
              data={cascades.map(c => ({ size: c.totalSize, count: 1 }))}
              xlabel="Cascade Size"
              ylabel="Frequency"
              expectedSlope={-1.5}
            />
          </div>
        </div>

        {/* Cascade List */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-amber-200 max-h-64 overflow-y-auto">
          <h3 className="text-lg font-semibold text-amber-800 mb-3">Largest Cascades</h3>
          <div className="space-y-2">
            {cascades
              .sort((a, b) => b.totalSize - a.totalSize)
              .slice(0, 10)
              .map((cascade, idx) => (
                <button
                  key={cascade.rootMessage.id}
                  onClick={() => setSelectedCascade(cascade)}
                  className={`w-full text-left p-2 rounded transition-colors ${
                    selectedCascade?.rootMessage.id === cascade.rootMessage.id
                      ? 'bg-amber-100 border border-amber-300'
                      : 'hover:bg-amber-50'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-amber-700">#{idx + 1}</span>
                    <span className="text-sm font-medium text-amber-900">
                      Size: {cascade.totalSize} | Depth: {cascade.depth}
                    </span>
                  </div>
                  <p className="text-xs text-amber-600 truncate mt-1">
                    {cascade.rootMessage.sender} → {cascade.rootMessage.receiver}
                  </p>
                </button>
              ))}
          </div>
        </div>
      </div>

      {/* Right Column: Cascade Visualization */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-amber-200">
        <h3 className="text-lg font-semibold text-amber-800 mb-3">Cascade Visualization</h3>
        {selectedCascade ? (
          <div className="h-full">
            <CascadeTree cascade={selectedCascade} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-amber-600">
            <p>Select a cascade from the list to visualize</p>
          </div>
        )}
      </div>
    </div>
  );
}
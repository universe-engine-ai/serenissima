'use client';

import React from 'react';

interface TimeSeriesChartProps {
  data: any[];
  yField: string;
  xlabel: string;
  ylabel: string;
  criticalLine?: number;
}

export default function TimeSeriesChart({ data, yField, xlabel, ylabel, criticalLine }: TimeSeriesChartProps) {
  return (
    <div className="w-full h-full flex items-center justify-center bg-amber-50 rounded">
      <div className="text-center text-amber-700">
        <p className="text-sm font-medium">Time Series Chart</p>
        <p className="text-xs mt-1">{xlabel} vs {ylabel}</p>
        {criticalLine !== undefined && (
          <p className="text-xs mt-1">Critical value: {criticalLine}</p>
        )}
        <p className="text-xs mt-2 text-amber-600">Chart implementation pending...</p>
      </div>
    </div>
  );
}
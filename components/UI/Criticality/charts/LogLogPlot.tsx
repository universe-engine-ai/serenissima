'use client';

import React from 'react';

interface LogLogPlotProps {
  data: { size: number; count: number }[];
  xlabel: string;
  ylabel: string;
  expectedSlope?: number;
}

export default function LogLogPlot({ data, xlabel, ylabel, expectedSlope }: LogLogPlotProps) {
  return (
    <div className="w-full h-full flex items-center justify-center bg-amber-50 rounded">
      <div className="text-center text-amber-700">
        <p className="text-sm font-medium">Log-Log Plot</p>
        <p className="text-xs mt-1">{xlabel} vs {ylabel}</p>
        {expectedSlope && (
          <p className="text-xs mt-1">Expected slope: {expectedSlope}</p>
        )}
        <p className="text-xs mt-2 text-amber-600">Chart implementation pending...</p>
      </div>
    </div>
  );
}
'use client';

import React from 'react';

interface HistogramProps {
  data: number[];
  xlabel: string;
  ylabel: string;
  bins: number;
  criticalLine?: number;
}

export default function Histogram({ data, xlabel, ylabel, bins, criticalLine }: HistogramProps) {
  return (
    <div className="w-full h-full flex items-center justify-center bg-amber-50 rounded">
      <div className="text-center text-amber-700">
        <p className="text-sm font-medium">Histogram</p>
        <p className="text-xs mt-1">{xlabel} distribution</p>
        <p className="text-xs mt-1">Data points: {data.length}</p>
        {criticalLine !== undefined && (
          <p className="text-xs mt-1">Critical value: {criticalLine}</p>
        )}
        <p className="text-xs mt-2 text-amber-600">Chart implementation pending...</p>
      </div>
    </div>
  );
}
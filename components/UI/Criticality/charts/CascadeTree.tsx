'use client';

import React from 'react';
import { Cascade } from '@/lib/services/criticality/cascadeAnalyzer';

interface CascadeTreeProps {
  cascade: Cascade;
}

export default function CascadeTree({ cascade }: CascadeTreeProps) {
  return (
    <div className="w-full h-full flex items-center justify-center bg-amber-50 rounded p-4">
      <div className="text-center text-amber-700">
        <p className="text-sm font-medium">Cascade Tree Visualization</p>
        <p className="text-xs mt-2">
          Root: {cascade.rootMessage.sender} → {cascade.rootMessage.receiver}
        </p>
        <p className="text-xs mt-1">
          Size: {cascade.totalSize} | Depth: {cascade.depth}
        </p>
        <p className="text-xs mt-1">
          Duration: {cascade.duration.toFixed(1)} minutes
        </p>
        <p className="text-xs mt-2 text-amber-600">Interactive tree visualization pending...</p>
      </div>
    </div>
  );
}
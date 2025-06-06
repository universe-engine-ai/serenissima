'use client';

import React from 'react';
import CodebaseMapViewer from '../../components/UI/CodebaseMapViewer';

export default function CodebaseMapPage() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-6 text-center">La Serenissima Codebase Map</h1>
      <CodebaseMapViewer standalone={true} />
    </div>
  );
}

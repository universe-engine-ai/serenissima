'use client';

import React, { useState, useEffect } from 'react';
import { FaChartLine, FaNetworkWired, FaClock, FaCodeBranch } from 'react-icons/fa';
import CascadeAnalysis from './CascadeAnalysis';
import BranchingRatio from './BranchingRatio';
import NetworkTopology from './NetworkTopology';
import TemporalAnalysis from './TemporalAnalysis';

export default function MessageCriticality() {
  const [activeAnalysis, setActiveAnalysis] = useState<'cascade' | 'branching' | 'network' | 'temporal'>('cascade');
  const [isLoading, setIsLoading] = useState(true);
  const [messageData, setMessageData] = useState<any>(null);

  useEffect(() => {
    // Fetch initial message data
    fetchMessageData();
  }, []);

  const fetchMessageData = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API endpoint
      const response = await fetch('/api/messages/cascade-data');
      const data = await response.json();
      setMessageData(data);
    } catch (error) {
      console.error('Error fetching message data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const analysisOptions = [
    { id: 'cascade', label: 'Cascade Analysis', icon: FaChartLine },
    { id: 'branching', label: 'Branching Ratio', icon: FaCodeBranch },
    { id: 'network', label: 'Network Topology', icon: FaNetworkWired },
    { id: 'temporal', label: 'Temporal Analysis', icon: FaClock },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Analysis Type Selector */}
      <div className="flex flex-wrap gap-2 mb-6 p-4 bg-amber-100 rounded-lg">
        {analysisOptions.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveAnalysis(id as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              activeAnalysis === id
                ? 'bg-amber-600 text-white'
                : 'bg-white text-amber-700 hover:bg-amber-200'
            }`}
          >
            <Icon className="text-sm" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Analysis Content */}
      <div className="flex-grow overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-amber-700">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600 mx-auto mb-4"></div>
              <p>Loading message data...</p>
            </div>
          </div>
        ) : (
          <div className="h-full">
            {activeAnalysis === 'cascade' && <CascadeAnalysis data={messageData} />}
            {activeAnalysis === 'branching' && <BranchingRatio data={messageData} />}
            {activeAnalysis === 'network' && <NetworkTopology data={messageData} />}
            {activeAnalysis === 'temporal' && <TemporalAnalysis data={messageData} />}
          </div>
        )}
      </div>

      {/* Info Panel */}
      <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-200">
        <h4 className="font-semibold text-amber-800 mb-2">About Message Criticality</h4>
        <p className="text-sm text-amber-700">
          This analysis examines whether La Serenissima's message network exhibits self-organized criticality (SOC). 
          At criticality, the system operates at the edge of chaos, maximizing information processing and adaptability.
          Look for power-law distributions, branching ratios near 1.0, and scale-free network structures.
        </p>
      </div>
    </div>
  );
}
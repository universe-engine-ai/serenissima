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
      // Use relative URL to work both locally and in production
      const response = await fetch('/api/messages?limit=500');
      const data = await response.json();
      
      if (data.success && data.messages) {
        // Use real data
        setMessageData({
          messages: data.messages.map((msg: any) => ({
            id: msg.messageId,
            sender: msg.sender,
            receiver: msg.receiver,
            content: msg.content,
            timestamp: msg.createdAt,
            type: msg.type,
            replyToId: undefined // Will be inferred by analysis
          })),
          metadata: {
            total: data.messages.length,
            timeRange: {
              start: data.messages[0]?.createdAt,
              end: data.messages[data.messages.length - 1]?.createdAt,
            },
            isDemo: false,
          }
        });
      } else {
        // Fall back to mock data
        const mockResponse = await fetch('/api/messages/cascade-data');
        const mockData = await mockResponse.json();
        setMessageData(mockData);
      }
    } catch (error) {
      console.error('Error fetching message data:', error);
      // Fall back to mock data
      try {
        const mockResponse = await fetch('/api/messages/cascade-data');
        const mockData = await mockResponse.json();
        setMessageData(mockData);
      } catch (mockError) {
        console.error('Error fetching mock data:', mockError);
      }
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
        <div className="flex justify-between items-start mb-2">
          <h4 className="font-semibold text-amber-800">About Message Criticality</h4>
          <div className="flex items-center gap-2">
            <span className="text-xs text-amber-600">
              {messageData?.metadata?.isDemo ? '🔄 Demo Data' : '✅ Live Data'}
            </span>
            <button
              onClick={fetchMessageData}
              disabled={isLoading}
              className="text-amber-700 hover:text-amber-900 transition-colors"
              title="Refresh data"
            >
              <svg className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
        <p className="text-sm text-amber-700">
          This analysis examines whether La Serenissima's message network exhibits self-organized criticality (SOC). 
          At criticality, the system operates at the edge of chaos, maximizing information processing and adaptability.
          Look for power-law distributions, branching ratios near 1.0, and scale-free network structures.
        </p>
        {messageData?.metadata && (
          <p className="text-xs text-amber-600 mt-2">
            Analyzing {messageData.metadata.total} messages from{' '}
            {messageData.metadata.timeRange?.start ? new Date(messageData.metadata.timeRange.start).toLocaleDateString() : 'N/A'} to{' '}
            {messageData.metadata.timeRange?.end ? new Date(messageData.metadata.timeRange.end).toLocaleDateString() : 'N/A'}
          </p>
        )}
      </div>
    </div>
  );
}
'use client';

import React, { useState } from 'react';
import Image from 'next/image';

interface CompetitivePositioningAnalysisComponentProps {
  resourceType?: string;
  data?: any;
}

export default function CompetitivePositioningAnalysisComponent({
  resourceType = 'General',
  data = {}
}: CompetitivePositioningAnalysisComponentProps) {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="max-w-7xl mx-auto">
      <div className="relative mb-12">
        <div className="h-64 w-full relative rounded-xl overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-amber-500 to-amber-600" />
          <div className="absolute inset-0 bg-black opacity-20" />
          <div className="relative z-10 h-full flex items-center justify-center">
            <div className="text-center text-white">
              <h1 className="text-4xl font-bold mb-2">Competitive Positioning Analysis</h1>
              <p className="text-xl">{resourceType} Market Strategy</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('analysis')}
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'analysis'
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Market Analysis
            </button>
            <button
              onClick={() => setActiveTab('strategy')}
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'strategy'
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Strategy
            </button>
          </nav>
        </div>

        <div className="mt-6">
          {activeTab === 'overview' && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Market Overview</h2>
              <p className="text-gray-600 mb-4">
                Comprehensive analysis of the {resourceType} market in La Serenissima,
                including competitive landscape, pricing trends, and strategic opportunities.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
                <div className="bg-amber-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-amber-900">Market Size</h3>
                  <p className="text-2xl font-bold text-amber-600 mt-2">
                    {data.marketSize || '1,245'} ducats
                  </p>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-900">Active Traders</h3>
                  <p className="text-2xl font-bold text-blue-600 mt-2">
                    {data.activeTraders || '23'}
                  </p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-green-900">Avg. Price</h3>
                  <p className="text-2xl font-bold text-green-600 mt-2">
                    {data.avgPrice || '12.5'} ducats
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'analysis' && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Competitive Analysis</h2>
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Price Distribution</h3>
                  <p className="text-gray-600">
                    Analysis of pricing strategies across different market segments.
                  </p>
                </div>
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Supply & Demand</h3>
                  <p className="text-gray-600">
                    Current supply levels and demand patterns for {resourceType}.
                  </p>
                </div>
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Market Trends</h3>
                  <p className="text-gray-600">
                    Emerging trends and opportunities in the {resourceType} market.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'strategy' && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Strategic Recommendations</h2>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
                <h3 className="font-semibold text-amber-900 mb-3">Key Strategies</h3>
                <ul className="space-y-2 text-gray-700">
                  <li className="flex items-start">
                    <span className="text-amber-600 mr-2">•</span>
                    <span>Optimize pricing based on market demand cycles</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-amber-600 mr-2">•</span>
                    <span>Establish strategic partnerships with key suppliers</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-amber-600 mr-2">•</span>
                    <span>Diversify product offerings to reduce market risk</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-amber-600 mr-2">•</span>
                    <span>Invest in market intelligence and competitor monitoring</span>
                  </li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
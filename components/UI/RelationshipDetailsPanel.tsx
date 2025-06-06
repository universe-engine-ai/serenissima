import React, { useState, useEffect } from 'react';
import { FaUserFriends, FaHandshake, FaExchangeAlt, FaChartLine, FaCalendarAlt, FaInfoCircle } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Relationship {
  citizen1: string;
  citizen2: string;
  lastInteraction: string;
  trustScore: number;
  strengthScore: number;
  notes: string;
  title: string;
  description: string;
  updatedAt: string;
  qualifiedAt?: string;
}

interface RelationshipDetailsPanelProps {
  relationships: Relationship[];
  username: string;
  onClose: () => void;
}

const RelationshipDetailsPanel: React.FC<RelationshipDetailsPanelProps> = ({ 
  relationships, 
  username,
  onClose 
}) => {
  const [sortedRelationships, setSortedRelationships] = useState<Relationship[]>([]);
  const [sortBy, setSortBy] = useState<string>('strengthScore');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    let filtered = [...relationships];
    
    // Apply filtering
    if (filter === 'positive') {
      filtered = filtered.filter(rel => rel.trustScore >= 50);
    } else if (filter === 'negative') {
      filtered = filtered.filter(rel => rel.trustScore < 50);
    } else if (filter === 'strong') {
      filtered = filtered.filter(rel => rel.strengthScore >= 1.0);
    } else if (filter === 'weak') {
      filtered = filtered.filter(rel => rel.strengthScore < 1.0);
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
      let valueA = a[sortBy as keyof Relationship];
      let valueB = b[sortBy as keyof Relationship];
      
      if (typeof valueA === 'string' && typeof valueB === 'string') {
        return sortDirection === 'asc' 
          ? valueA.localeCompare(valueB) 
          : valueB.localeCompare(valueA);
      }
      
      // Handle numeric values
      if (typeof valueA === 'number' && typeof valueB === 'number') {
        return sortDirection === 'asc' ? valueA - valueB : valueB - valueA;
      }
      
      return 0;
    });
    
    setSortedRelationships(filtered);
  }, [relationships, sortBy, sortDirection, filter]);

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDirection('desc');
    }
  };

  const getOtherCitizen = (relationship: Relationship) => {
    return relationship.citizen1 === username ? relationship.citizen2 : relationship.citizen1;
  };

  const getTrustScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600';
    if (score >= 50) return 'text-green-500';
    if (score >= 25) return 'text-amber-500';
    return 'text-red-500';
  };

  const getStrengthScoreColor = (score: number) => {
    if (score >= 2) return 'text-blue-600 font-bold';
    if (score >= 1) return 'text-blue-500';
    if (score >= 0.5) return 'text-blue-400';
    return 'text-gray-500';
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('it-IT', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg shadow-lg p-4 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-4 border-b border-amber-200 pb-3">
        <h2 className="text-xl font-serif text-amber-900 flex items-center">
          <FaUserFriends className="mr-2" />
          Your Relationships in La Serenissima
        </h2>
        <button 
          onClick={onClose}
          className="text-amber-700 hover:text-amber-900 p-1"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div className="mb-4 flex flex-wrap gap-2">
        <button 
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'all' ? 'bg-amber-600 text-white' : 'bg-amber-100 text-amber-800 hover:bg-amber-200'}`}
        >
          All Relationships
        </button>
        <button 
          onClick={() => setFilter('positive')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'positive' ? 'bg-green-600 text-white' : 'bg-green-100 text-green-800 hover:bg-green-200'}`}
        >
          Positive Trust (≥50)
        </button>
        <button 
          onClick={() => setFilter('negative')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'negative' ? 'bg-red-600 text-white' : 'bg-red-100 text-red-800 hover:bg-red-200'}`}
        >
          Negative Trust (<50)
        </button>
        <button 
          onClick={() => setFilter('strong')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'strong' ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-800 hover:bg-blue-200'}`}
        >
          Strong Bonds (≥1.0)
        </button>
        <button 
          onClick={() => setFilter('weak')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'weak' ? 'bg-gray-600 text-white' : 'bg-gray-100 text-gray-800 hover:bg-gray-200'}`}
        >
          Weak Bonds (<1.0)
        </button>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-amber-200 rounded-lg">
          <thead className="bg-amber-100">
            <tr>
              <th className="py-2 px-4 border-b border-amber-200 text-left text-amber-800">Citizen</th>
              <th 
                className="py-2 px-4 border-b border-amber-200 text-left text-amber-800 cursor-pointer"
                onClick={() => handleSort('trustScore')}
              >
                <div className="flex items-center">
                  Trust Score
                  {sortBy === 'trustScore' && (
                    <span className="ml-1">
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </div>
              </th>
              <th 
                className="py-2 px-4 border-b border-amber-200 text-left text-amber-800 cursor-pointer"
                onClick={() => handleSort('strengthScore')}
              >
                <div className="flex items-center">
                  Strength Score
                  {sortBy === 'strengthScore' && (
                    <span className="ml-1">
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </div>
              </th>
              <th 
                className="py-2 px-4 border-b border-amber-200 text-left text-amber-800 cursor-pointer"
                onClick={() => handleSort('lastInteraction')}
              >
                <div className="flex items-center">
                  Last Interaction
                  {sortBy === 'lastInteraction' && (
                    <span className="ml-1">
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </div>
              </th>
              <th className="py-2 px-4 border-b border-amber-200 text-left text-amber-800">Relationship</th>
            </tr>
          </thead>
          <tbody>
            {sortedRelationships.length > 0 ? (
              sortedRelationships.map((relationship, index) => {
                const otherCitizen = getOtherCitizen(relationship);
                return (
                  <tr key={index} className={index % 2 === 0 ? 'bg-amber-50' : 'bg-white'}>
                    <td className="py-3 px-4 border-b border-amber-100 font-medium">{otherCitizen}</td>
                    <td className="py-3 px-4 border-b border-amber-100">
                      <span className={`${getTrustScoreColor(relationship.trustScore)} font-medium`}>
                        {relationship.trustScore.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-3 px-4 border-b border-amber-100">
                      <span className={`${getStrengthScoreColor(relationship.strengthScore)}`}>
                        {relationship.strengthScore.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-3 px-4 border-b border-amber-100 text-sm">
                      {formatDate(relationship.lastInteraction)}
                    </td>
                    <td className="py-3 px-4 border-b border-amber-100">
                      <details className="group">
                        <summary className="list-none flex justify-between items-center cursor-pointer">
                          <span className="font-medium text-amber-800">{relationship.title}</span>
                          <svg className="w-5 h-5 text-amber-700 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </summary>
                        <div className="mt-2 text-sm text-gray-700">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {relationship.description}
                          </ReactMarkdown>
                          
                          {relationship.notes && (
                            <div className="mt-2 p-2 bg-amber-50 border-l-2 border-amber-300 text-xs">
                              <div className="font-medium text-amber-800 mb-1">Notes:</div>
                              <div className="text-gray-600">{relationship.notes}</div>
                            </div>
                          )}
                          
                          <div className="mt-2 text-xs text-gray-500 flex items-center">
                            <FaCalendarAlt className="mr-1" />
                            <span>Updated: {formatDate(relationship.updatedAt)}</span>
                          </div>
                        </div>
                      </details>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={5} className="py-4 px-4 text-center text-gray-500 italic">
                  No relationships found matching the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      <div className="mt-4 bg-amber-50 p-3 border border-amber-200 rounded-lg text-sm text-amber-800">
        <div className="flex items-center mb-2">
          <FaInfoCircle className="mr-2 text-amber-600" />
          <span className="font-medium">Understanding Your Relationships</span>
        </div>
        <ul className="list-disc pl-5 space-y-1 text-amber-700">
          <li><span className="font-medium">Trust Score</span>: Measures how much you and the other citizen trust each other (0-100).</li>
          <li><span className="font-medium">Strength Score</span>: Indicates how strong your connection is, based on frequency and significance of interactions (0-5).</li>
          <li><span className="font-medium">Relationship Title</span>: Summarizes the nature of your relationship.</li>
          <li><span className="font-medium">Description</span>: Provides details about your relationship history and context.</li>
        </ul>
      </div>
    </div>
  );
};

export default RelationshipDetailsPanel;

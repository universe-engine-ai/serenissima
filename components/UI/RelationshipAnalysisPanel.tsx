import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface RelationshipAnalysisProps {
  citizen1: string;
  citizen2: string;
  onClose?: () => void;
}

interface RelationshipData {
  title: string;
  description: string;
}

const RelationshipAnalysisPanel: React.FC<RelationshipAnalysisProps> = ({
  citizen1,
  citizen2,
  onClose
}) => {
  const [relationship, setRelationship] = useState<RelationshipData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchRelationshipData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch('/api/relationships/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ citizen1, citizen2 }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch relationship data');
        }
        
        const data = await response.json();
        
        if (data.success && data.relationship) {
          setRelationship(data.relationship);
        } else {
          throw new Error(data.error || 'Unknown error');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };
    
    fetchRelationshipData();
  }, [citizen1, citizen2]);
  
  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-800">Relationship Analysis</h2>
        {onClose && (
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      
      <div className="mb-4">
        <div className="flex items-center space-x-2 text-gray-600 mb-2">
          <span className="font-medium">{citizen1}</span>
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
          <span className="font-medium">{citizen2}</span>
        </div>
      </div>
      
      {loading && (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-700"></div>
        </div>
      )}
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
        </div>
      )}
      
      {!loading && !error && relationship && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-amber-900 mb-2">{relationship.title}</h3>
          <p className="text-gray-700">{relationship.description}</p>
        </div>
      )}
    </div>
  );
};

export default RelationshipAnalysisPanel;

import React, { useState, useEffect } from 'react';
import { FaUserFriends } from 'react-icons/fa';
import RelationshipDetailsPanel from './RelationshipDetailsPanel';

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

interface RelationshipDetailsButtonProps {
  username: string;
}

const RelationshipDetailsButton: React.FC<RelationshipDetailsButtonProps> = ({ username }) => {
  const [showPanel, setShowPanel] = useState(false);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRelationships = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // First try to get relationships where the user is citizen1
      const response1 = await fetch(`/api/relationships?Citizen1=${username}`);
      const data1 = await response1.json();
      
      // Then try to get relationships where the user is citizen2
      const response2 = await fetch(`/api/relationships?Citizen2=${username}`);
      const data2 = await response2.json();
      
      // Combine and deduplicate the results
      const allRelationships = [...data1, ...data2];
      
      // Convert Airtable field names to camelCase for consistency
      const formattedRelationships = allRelationships.map(rel => ({
        citizen1: rel.Citizen1 || rel.citizen1,
        citizen2: rel.Citizen2 || rel.citizen2,
        lastInteraction: rel.LastInteraction || rel.lastInteraction,
        trustScore: rel.TrustScore || rel.trustScore || 0,
        strengthScore: rel.StrengthScore || rel.strengthScore || 0,
        notes: rel.Notes || rel.notes || '',
        title: rel.Title || rel.title || 'Unnamed Relationship',
        description: rel.Description || rel.description || '',
        updatedAt: rel.UpdatedAt || rel.updatedAt || '',
        qualifiedAt: rel.QualifiedAt || rel.qualifiedAt
      }));
      
      setRelationships(formattedRelationships);
    } catch (err) {
      console.error('Error fetching relationships:', err);
      setError('Failed to load relationships. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenPanel = () => {
    if (!showPanel) {
      fetchRelationships();
    }
    setShowPanel(true);
  };

  const handleClosePanel = () => {
    setShowPanel(false);
  };

  return (
    <>
      <button
        onClick={handleOpenPanel}
        className="flex items-center px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg shadow transition-colors"
      >
        <FaUserFriends className="mr-2" />
        <span>View Relationships</span>
      </button>
      
      {showPanel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-700 mx-auto"></div>
                <p className="mt-4 text-amber-800">Loading your relationships...</p>
              </div>
            ) : error ? (
              <div className="p-8 text-center">
                <div className="text-red-500 mb-4">⚠️</div>
                <p className="text-red-600">{error}</p>
                <button 
                  onClick={fetchRelationships}
                  className="mt-4 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded"
                >
                  Try Again
                </button>
              </div>
            ) : (
              <RelationshipDetailsPanel 
                relationships={relationships} 
                username={username}
                onClose={handleClosePanel} 
              />
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default RelationshipDetailsButton;

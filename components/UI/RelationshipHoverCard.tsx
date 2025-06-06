import React from 'react';
import { format } from 'date-fns';

interface RelationshipHoverCardProps {
  trustScore: number;
  strengthScore: number;
  lastInteraction: string;
  citizen1: string;
  citizen2: string;
  status?: string;
  notes?: string;
}

const RelationshipHoverCard: React.FC<RelationshipHoverCardProps> = ({
  trustScore,
  strengthScore,
  lastInteraction,
  citizen1,
  citizen2,
  status = 'Active',
  notes
}) => {
  // Format the last interaction date
  const formattedDate = lastInteraction ? format(new Date(lastInteraction), 'PPP') : 'Never';
  
  // Calculate trust level description
  const getTrustLevel = (score: number): string => {
    if (score >= 80) return 'High Trust';
    if (score >= 50) return 'Moderate Trust';
    if (score >= 30) return 'Cautious';
    if (score >= 10) return 'Suspicious';
    return 'Distrustful';
  };
  
  // Calculate strength level description
  const getStrengthLevel = (score: number): string => {
    if (score >= 80) return 'Strong Bond';
    if (score >= 50) return 'Established';
    if (score >= 30) return 'Developing';
    if (score >= 10) return 'Acquaintances';
    return 'Strangers';
  };

  return (
    <div className="bg-white shadow-lg rounded-lg p-4 max-w-xs border border-amber-200">
      <div className="text-center mb-2 pb-2 border-b border-amber-100">
        <h3 className="font-semibold text-amber-800">Relationship Details</h3>
      </div>
      
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Status:</span>
          <span className="font-medium text-amber-700">{status}</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">Trust:</span>
          <div className="text-right">
            <span className="font-medium text-amber-700">{trustScore.toFixed(1)}</span>
            <span className="text-xs ml-1 text-gray-500">({getTrustLevel(trustScore)})</span>
          </div>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">Strength:</span>
          <div className="text-right">
            <span className="font-medium text-amber-700">{strengthScore.toFixed(1)}</span>
            <span className="text-xs ml-1 text-gray-500">({getStrengthLevel(strengthScore)})</span>
          </div>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">Last Interaction:</span>
          <span className="font-medium text-amber-700">{formattedDate}</span>
        </div>
        
        {notes && (
          <div className="mt-2 pt-2 border-t border-amber-100">
            <span className="text-gray-600 block mb-1">Notes:</span>
            <p className="text-xs italic text-gray-700">{notes}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default RelationshipHoverCard;

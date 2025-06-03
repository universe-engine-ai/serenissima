import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import InfoIcon from '../../UI/InfoIcon'; // Adjusted path

interface Relevancy {
  id: string;
  relevancyId?: string;
  title: string;
  description: string;
  score: number;
  category?: string;
  type?: string;
  timeHorizon?: string;
  notes?: string;
  createdAt?: string;
  strategicValue?: number;
  economicImpact?: string;
  // Add any other fields from the relevancy object that are used
}

interface BuildingRelevanciesListProps {
  buildingId: string | null;
  citizenUsername: string | null; // Username of the currently logged-in citizen
}

const BuildingRelevanciesList: React.FC<BuildingRelevanciesListProps> = ({
  buildingId,
  citizenUsername,
}) => {
  const [relevancies, setRelevancies] = useState<Relevancy[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sortedRelevancies, setSortedRelevancies] = useState<Relevancy[]>([]);

  useEffect(() => {
    if (!buildingId || !citizenUsername) {
      setRelevancies([]);
      return;
    }

    const fetchRelevancies = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/relevancies/for-asset?assetId=${encodeURIComponent(buildingId)}&assetType=building&relevantToCitizen=${encodeURIComponent(citizenUsername)}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch relevancies: ${response.status}`);
        }
        const data = await response.json();
        if (data.success && Array.isArray(data.relevancies)) {
          setRelevancies(data.relevancies);
        } else {
          throw new Error(data.error || 'Invalid data format for relevancies');
        }
      } catch (err) {
        console.error('Error fetching building relevancies:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        setRelevancies([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRelevancies();
  }, [buildingId, citizenUsername]);

  // Sort relevancies by score (highest first)
  useEffect(() => {
    const sorted = [...relevancies].sort((a, b) => b.score - a.score);
    setSortedRelevancies(sorted);
  }, [relevancies]);

  // Helper function to get priority label based on score
  const getPriorityLabel = (score: number): string => {
    if (score >= 80) return "Critical";
    if (score >= 60) return "High";
    if (score >= 40) return "Moderate";
    return "Low";
  };

  // Helper function to get color classes based on score
  const getScoreColorClasses = (score: number): string => {
    if (score >= 80) return "bg-red-100 text-red-800";
    if (score >= 60) return "bg-teal-100 text-teal-800";
    if (score >= 40) return "bg-lime-100 text-lime-700";
    return "bg-gray-100 text-gray-700";
  };
  
  // Helper function to calculate strategic value based on relevancy type and score
  const calculateStrategicValue = (relevancy: Relevancy): number => {
    if (relevancy.strategicValue) return relevancy.strategicValue;
    
    // Base value from score
    const baseValue = Math.floor(relevancy.score / 10);
    
    // Adjust based on category and type
    let modifier = 0;
    
    // Category modifiers
    if (relevancy.category?.toLowerCase() === "opportunity") modifier += 2;
    if (relevancy.category?.toLowerCase() === "threat") modifier += 1;
    
    // Type modifiers
    if (relevancy.type?.includes("economic")) modifier += 2;
    if (relevancy.type?.includes("trade")) modifier += 2;
    if (relevancy.type?.includes("property")) modifier += 1;
    if (relevancy.type?.includes("business")) modifier += 1;
    
    // Calculate final value (capped at 10)
    return Math.min(10, baseValue + modifier);
  };
  
  // Helper function to determine economic impact based on score and type
  const determineEconomicImpact = (relevancy: Relevancy): string => {
    if (relevancy.economicImpact) return relevancy.economicImpact;
    
    if (relevancy.score >= 80) return "Transformative";
    if (relevancy.score >= 60) return "Significant";
    if (relevancy.score >= 40) return "Moderate";
    return "Minimal";
  };

  if (!buildingId || !citizenUsername) {
    return null; // Don't render if essential props are missing
  }

  return (
    <div className="mt-4">
      <div className="flex items-center mb-2">
        <h4 className="text-md font-serif text-amber-800 border-b border-amber-200 pb-1">
          Pattern Recognition: Building Opportunities
        </h4>
        <InfoIcon tooltipText="Strategic opportunities and patterns related to this building that align with your merchant-architect interests." />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-3">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : error ? (
        <p className="text-red-600 italic text-xs">Error: {error}</p>
      ) : sortedRelevancies.length > 0 ? (
        <div className="space-y-2 max-h-[250px] overflow-y-auto pr-1 custom-scrollbar">
          {sortedRelevancies.map((relevancy) => (
            <div key={relevancy.id} className="bg-amber-100 rounded-lg p-2.5 text-xs shadow-sm">
              <div className="flex items-start justify-between mb-1">
                <div className="font-medium text-amber-800 flex-1 pr-2">
                  {relevancy.title}
                </div>
                <div className="text-center">
                  <div className={`px-2.5 py-0.5 rounded-full text-lg font-bold ${getScoreColorClasses(relevancy.score)}`}>
                    {Math.round(relevancy.score)}
                  </div>
                  <p className="text-[10px] text-amber-600 mt-0.5">{getPriorityLabel(relevancy.score)}</p>
                </div>
              </div>
              <div className="text-amber-700 mt-1.5">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({node, ...props}) => <p {...props} className="my-0.5" />
                  }}
                >
                  {relevancy.description}
                </ReactMarkdown>
              </div>
              {(relevancy.category || relevancy.type || relevancy.timeHorizon) && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {relevancy.category && (
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] border ${
                      relevancy.category.toLowerCase() === 'opportunity' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      relevancy.category.toLowerCase() === 'threat' ? 'bg-red-50 text-red-700 border-red-200' :
                      relevancy.category.toLowerCase() === 'proximity' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                      relevancy.category.toLowerCase() === 'affiliation' ? 'bg-purple-50 text-purple-700 border-purple-200' :
                      'bg-amber-50 text-amber-700 border-amber-200'
                    }`}>
                      {relevancy.category}
                    </span>
                  )}
                  {relevancy.type && (
                    <span className="inline-block px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded text-[9px] border border-amber-200">
                      {relevancy.type}
                    </span>
                  )}
                  {relevancy.timeHorizon && (
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] border ${
                      relevancy.timeHorizon === 'immediate' ? 'bg-red-50 text-red-700 border-red-200' :
                      relevancy.timeHorizon === 'short' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                      relevancy.timeHorizon === 'medium' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      relevancy.timeHorizon === 'long' ? 'bg-green-50 text-green-700 border-green-200' :
                      'bg-amber-50 text-amber-700 border-amber-200'
                    }`}>
                      {relevancy.timeHorizon}
                    </span>
                  )}
                </div>
              )}
              
              <div className="mt-2 flex justify-between">
                <span className="text-xs font-semibold text-amber-700">
                  Strategic Value: {calculateStrategicValue(relevancy)}/10
                </span>
                <span className="text-xs font-medium text-emerald-700">
                  Economic Impact: {determineEconomicImpact(relevancy)}
                </span>
              </div>
              
              {relevancy.notes && (
                <div className="mt-2 text-xs italic text-amber-600 border-t border-amber-200 pt-1">
                  {relevancy.notes}
                </div>
              )}
              
              {relevancy.createdAt && (
                <div className="mt-1 text-xs text-amber-500 text-right">
                  Identified: {new Date(relevancy.createdAt).toLocaleDateString()}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-amber-600 italic text-xs">No strategic patterns identified for this building at present. Continue to observe for emerging opportunities.</p>
      )}
    </div>
  );
};

export default BuildingRelevanciesList;

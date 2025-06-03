import React, { useState, useEffect } from 'react';
import InfoIcon from '../../UI/InfoIcon'; // Adjusted path
import { FaLightbulb, FaExclamationTriangle, FaInfoCircle, FaChartLine } from 'react-icons/fa';

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
  updatedAt?: string;
  asset?: string;
  assetType?: string;
  strategicValue?: number;
  economicImpact?: string;
}

interface EnhancedBuildingRelevanciesProps {
  buildingId: string | null;
  citizenUsername: string | null;
  showStrategicInsights?: boolean;
  className?: string;
}

const EnhancedBuildingRelevancies: React.FC<EnhancedBuildingRelevanciesProps> = ({
  buildingId,
  citizenUsername,
  showStrategicInsights = true,
  className = ''
}) => {
  const [relevancies, setRelevancies] = useState<Relevancy[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  useEffect(() => {
    const fetchRelevancies = async () => {
      if (!buildingId || !citizenUsername) {
        setRelevancies([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await fetch(`/api/relevancies?RelevantToCitizen=${citizenUsername}&Asset=${buildingId}&AssetType=building`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch relevancies: ${response.status}`);
        }
        
        const data = await response.json();
        setRelevancies(data.relevancies || []);
      } catch (err) {
        console.error('Error fetching building relevancies:', err);
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchRelevancies();
  }, [buildingId, citizenUsername]);

  // Helper function to get priority label based on score
  const getPriorityLabel = (score: number): string => {
    if (score >= 80) return "Critical";
    if (score >= 60) return "High";
    if (score >= 40) return "Moderate";
    return "Low";
  };

  // Helper function to get color classes based on score
  const getPriorityColorClasses = (score: number): string => {
    if (score >= 80) return "bg-red-100 border-red-300 text-red-800";
    if (score >= 60) return "bg-amber-100 border-amber-300 text-amber-800";
    if (score >= 40) return "bg-blue-100 border-blue-300 text-blue-800";
    return "bg-gray-100 border-gray-300 text-gray-800";
  };

  // Helper function to get category icon
  const getCategoryIcon = (category?: string) => {
    switch(category?.toLowerCase()) {
      case 'opportunity':
        return <FaLightbulb className="text-amber-500" />;
      case 'threat':
        return <FaExclamationTriangle className="text-red-500" />;
      case 'economic':
        return <FaChartLine className="text-emerald-500" />;
      default:
        return <FaInfoCircle className="text-blue-500" />;
    }
  };

  // Helper function to get strategic insights based on relevancy type
  const getStrategicInsight = (relevancy: Relevancy): string => {
    if (!showStrategicInsights) return '';
    
    const baseInsight = "Consider this opportunity for ";
    
    switch(relevancy.type) {
      case 'economic_opportunity':
        return `${baseInsight}potential profit through arbitrage or market positioning.`;
      case 'property_investment':
        return `${baseInsight}long-term wealth accumulation through strategic property acquisition.`;
      case 'business_expansion':
        return `${baseInsight}expanding your commercial influence in this district.`;
      case 'resource_acquisition':
        return `${baseInsight}securing vital resources for your production chains.`;
      case 'political_influence':
        return `${baseInsight}increasing your political standing in the Republic.`;
      case 'social_connection':
        return `${baseInsight}building valuable relationships with influential citizens.`;
      default:
        return `${baseInsight}advancing your strategic position in Venice.`;
    }
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
    if (relevancy.type?.includes("property")) modifier += 1;
    if (relevancy.type?.includes("business")) modifier += 1;
    if (relevancy.type?.includes("resource")) modifier += 1;
    if (relevancy.type?.includes("political")) modifier += 1;
    
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

  if (loading) {
    return <div className={`p-4 text-center text-gray-500 ${className}`}>Loading relevancies...</div>;
  }

  if (error) {
    return <div className={`p-4 text-center text-red-500 ${className}`}>Error: {error}</div>;
  }

  if (relevancies.length === 0) {
    return (
      <div className={`p-4 text-center text-gray-500 ${className}`}>
        No strategic relevancies found for this building.
      </div>
    );
  }

  // Sort relevancies by score (highest first)
  const sortedRelevancies = [...relevancies].sort((a, b) => b.score - a.score);

  return (
    <div className={`bg-amber-50 border border-amber-200 rounded-lg overflow-hidden ${className}`}>
      <div 
        className="flex items-center justify-between p-3 bg-amber-100 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3 className="text-lg font-semibold text-amber-800">Strategic Patterns ({relevancies.length})</h3>
        <div className="flex items-center">
          <InfoIcon 
            tooltipText="These are opportunities and strategic considerations relevant to you regarding this building." 
          />
          <span className="ml-2">
            {isExpanded ? (
              <svg className="w-5 h-5 text-amber-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-amber-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            )}
          </span>
        </div>
      </div>
      
      {isExpanded && (
        <div className="p-3 space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar">
          {sortedRelevancies.map((relevancy) => (
            <div 
              key={relevancy.id || relevancy.relevancyId} 
              className={`p-3 border rounded-lg ${getPriorityColorClasses(relevancy.score)}`}
            >
              <div className="flex justify-between items-start">
                <div className="flex items-start">
                  <div className="mr-2 mt-1">
                    {getCategoryIcon(relevancy.category)}
                  </div>
                  <h4 className="font-medium">{relevancy.title}</h4>
                </div>
                <span className="px-2 py-1 text-xs rounded-full bg-white bg-opacity-50">
                  {getPriorityLabel(relevancy.score)} ({relevancy.score})
                </span>
              </div>
              
              <p className="mt-1 text-sm">{relevancy.description}</p>
              
              {showStrategicInsights && (
                <div className="mt-2 text-sm italic border-t pt-2 border-opacity-30 border-current">
                  <span className="font-medium">Strategic Insight:</span> {getStrategicInsight(relevancy)}
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
                <div className="mt-2 text-xs border-t pt-2 border-opacity-30 border-current">
                  <span className="font-medium">Notes:</span> {relevancy.notes}
                </div>
              )}
              
              {relevancy.timeHorizon && (
                <div className="mt-1 text-xs">
                  <span className="font-medium">Time Horizon:</span> {relevancy.timeHorizon}
                </div>
              )}
              
              {relevancy.createdAt && (
                <div className="mt-1 text-xs opacity-75">
                  Identified: {new Date(relevancy.createdAt).toLocaleDateString()}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EnhancedBuildingRelevancies;

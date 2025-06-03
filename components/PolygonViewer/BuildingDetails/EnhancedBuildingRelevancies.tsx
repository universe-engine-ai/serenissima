import React, { useState, useEffect } from 'react';
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
  updatedAt?: string;
  asset?: string;
  assetType?: string;
}

interface EnhancedBuildingRelevanciesProps {
  buildingId: string | null;
  citizenUsername: string | null;
  showStrategicInsights?: boolean;
}

const EnhancedBuildingRelevancies: React.FC<EnhancedBuildingRelevanciesProps> = ({
  buildingId,
  citizenUsername,
  showStrategicInsights = true
}) => {
  const [relevancies, setRelevancies] = useState<Relevancy[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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

  if (loading) {
    return <div className="p-4 text-center text-gray-500">Loading relevancies...</div>;
  }

  if (error) {
    return <div className="p-4 text-center text-red-500">Error: {error}</div>;
  }

  if (relevancies.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        No strategic relevancies found for this building.
      </div>
    );
  }

  // Sort relevancies by score (highest first)
  const sortedRelevancies = [...relevancies].sort((a, b) => b.score - a.score);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-amber-800">Strategic Relevancies</h3>
        <InfoIcon 
          tooltipText="These are opportunities and strategic considerations relevant to you regarding this building." 
        />
      </div>
      
      {sortedRelevancies.map((relevancy) => (
        <div 
          key={relevancy.id || relevancy.relevancyId} 
          className={`p-3 border rounded-lg ${getPriorityColorClasses(relevancy.score)}`}
        >
          <div className="flex justify-between items-start">
            <h4 className="font-medium">{relevancy.title}</h4>
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
  );
};

export default EnhancedBuildingRelevancies;

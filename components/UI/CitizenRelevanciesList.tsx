import React, { useState, useEffect, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import InfoIcon from './InfoIcon'; // Assuming InfoIcon is in the same directory or adjust path

interface Relevancy {
  relevancyId: string;
  title: string;
  description: string;
  score: number;
  category?: string; // Added category field
  type?: string; // Added type field
  timeHorizon?: string; // Added timeHorizon field
  status?: string; // Added status field
  notes?: string; // Added notes field
  createdAt?: string; // Added createdAt field
  updatedAt?: string; // Added updatedAt field
}

interface CitizenForFormatting {
  firstName?: string;
  lastName?: string;
  username?: string;
  socialClass?: string;
}

interface CitizenRelevanciesListProps {
  relevancies: Relevancy[];
  isLoadingRelevancies: boolean;
  citizen: CitizenForFormatting | null; // Citizen object for formatting text
}

// Interface for Thought
interface Thought {
  messageId: string;
  citizenUsername: string;
  originalContent: string;
  mainThought: string;
  createdAt: string;
}

// Define relevancy categories for grouping
type RelevancyCategory = 'proximity' | 'economic' | 'social' | 'strategic' | 'other';

// Interface for grouped relevancies
interface GroupedRelevancies {
  proximity: Relevancy[];
  economic: Relevancy[];
  social: Relevancy[];
  strategic: Relevancy[];
  other: Relevancy[];
}

// Helper function to replace placeholders in relevancy text (moved from CitizenDetailsPanel)
const formatRelevancyText = (text: string, currentCitizen: CitizenForFormatting | null): string => {
  if (!text || !currentCitizen) return text;
  let newText = text;
  newText = newText.replace(/%TARGETCITIZEN%/g, `${currentCitizen.firstName || ''} ${currentCitizen.lastName || ''}`.trim());
  newText = newText.replace(/%FIRSTNAME%/g, currentCitizen.firstName || '');
  newText = newText.replace(/%LASTNAME%/g, currentCitizen.lastName || '');
  newText = newText.replace(/%USERNAME%/g, currentCitizen.username || '');
  newText = newText.replace(/%SOCIALCLASS%/g, currentCitizen.socialClass || '');
  return newText;
};

// Helper function to map relevancy category from backend to frontend category
const mapRelevancyCategory = (relevancy: Relevancy): RelevancyCategory => {
  if (!relevancy.category) return 'other';
  
  // Map backend categories to frontend categories
  const categoryMap: Record<string, RelevancyCategory> = {
    'proximity': 'proximity',
    'geographic': 'proximity',
    'connected': 'proximity',
    'domination': 'strategic',
    'economic': 'economic',
    'operator_relations': 'economic',
    'occupancy_relations': 'social',
    'neighborhood': 'social',
    'affiliation': 'social',
    'strategic': 'strategic'
  };
  
  return categoryMap[relevancy.category.toLowerCase()] || 'other';
};

// Helper function to get color scheme based on relevancy category
const getCategoryColorScheme = (category: RelevancyCategory): { bg: string, text: string, border: string } => {
  switch (category) {
    case 'proximity':
      return { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-200' };
    case 'economic':
      return { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-200' };
    case 'social':
      return { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-200' };
    case 'strategic':
      return { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-200' };
    default:
      return { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-200' };
  }
};

// Helper function to get icon for relevancy category
const getCategoryIcon = (category: RelevancyCategory): string => {
  switch (category) {
    case 'proximity':
      return '📍'; // Map pin
    case 'economic':
      return '💰'; // Money bag
    case 'social':
      return '👥'; // People
    case 'strategic':
      return '🏛️'; // Classical building
    default:
      return '📋'; // Clipboard
  }
};

const CitizenRelevanciesList: React.FC<CitizenRelevanciesListProps> = ({
  relevancies,
  isLoadingRelevancies,
  citizen,
}) => {
  const [citizenThoughts, setCitizenThoughts] = useState<Thought[]>([]);
  const [isLoadingThoughts, setIsLoadingThoughts] = useState<boolean>(false);
  const [activeCategory, setActiveCategory] = useState<RelevancyCategory | 'all'>('all');
  const [expandedRelevancies, setExpandedRelevancies] = useState<Record<string, boolean>>({});

  // Group relevancies by category
  const groupedRelevancies = useMemo(() => {
    const grouped: GroupedRelevancies = {
      proximity: [],
      economic: [],
      social: [],
      strategic: [],
      other: []
    };
    
    relevancies.forEach(relevancy => {
      const category = mapRelevancyCategory(relevancy);
      grouped[category].push(relevancy);
    });
    
    return grouped;
  }, [relevancies]);

  // Get filtered relevancies based on active category
  const filteredRelevancies = useMemo(() => {
    if (activeCategory === 'all') {
      return relevancies;
    }
    return groupedRelevancies[activeCategory];
  }, [relevancies, groupedRelevancies, activeCategory]);

  // Toggle expanded state for a relevancy
  const toggleRelevancyExpanded = (relevancyId: string) => {
    setExpandedRelevancies(prev => ({
      ...prev,
      [relevancyId]: !prev[relevancyId]
    }));
  };

  useEffect(() => {
    if (citizen && citizen.username) {
      const fetchThoughtsForCitizen = async () => {
        setIsLoadingThoughts(true);
        try {
          const response = await fetch(`/api/thoughts?citizenUsername=${encodeURIComponent(citizen.username!)}&limit=5`);
          if (response.ok) {
            const data = await response.json();
            if (data.success && Array.isArray(data.thoughts)) {
              setCitizenThoughts(data.thoughts);
            } else {
              console.error('Failed to fetch thoughts or invalid format:', data.error);
              setCitizenThoughts([]);
            }
          } else {
            console.error('API error fetching thoughts:', response.status);
            setCitizenThoughts([]);
          }
        } catch (error) {
          console.error('Exception fetching thoughts:', error);
          setCitizenThoughts([]);
        } finally {
          setIsLoadingThoughts(false);
        }
      };
      fetchThoughtsForCitizen();
    } else {
      setCitizenThoughts([]); // Clear thoughts if no citizen or username
    }
  }, [citizen]);

  // Helper to format date for thoughts
  const formatThoughtDate = (dateString: string): string => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      if (diffHours < 1) return 'Just now';
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch (e) {
      return 'Invalid date';
    }
  };

  // Get category counts
  const categoryCounts = useMemo(() => {
    return {
      all: relevancies.length,
      proximity: groupedRelevancies.proximity.length,
      economic: groupedRelevancies.economic.length,
      social: groupedRelevancies.social.length,
      strategic: groupedRelevancies.strategic.length,
      other: groupedRelevancies.other.length
    };
  }, [relevancies, groupedRelevancies]);

  return (
    <>
      <div className="flex items-center">
        <h3 className="text-lg font-serif text-amber-800 mb-2 border-b border-amber-200 pb-1">Connections</h3>
        <InfoIcon tooltipText="Opportunities and relevant links for this citizen, based on their activities, needs, and relationships with you or the community." />
      </div>

      {/* Category filter tabs */}
      <div className="flex flex-wrap gap-1 mb-3">
        <button 
          onClick={() => setActiveCategory('all')} 
          className={`px-2 py-1 text-xs rounded-full flex items-center ${
            activeCategory === 'all' 
              ? 'bg-amber-600 text-white' 
              : 'bg-amber-100 text-amber-800 hover:bg-amber-200'
          }`}
        >
          All ({categoryCounts.all})
        </button>
        {Object.entries(groupedRelevancies).map(([category, items]) => {
          if (items.length === 0) return null;
          const cat = category as RelevancyCategory;
          return (
            <button 
              key={category}
              onClick={() => setActiveCategory(cat)}
              className={`px-2 py-1 text-xs rounded-full flex items-center gap-1 ${
                activeCategory === cat
                  ? 'bg-amber-600 text-white' 
                  : 'bg-amber-100 text-amber-800 hover:bg-amber-200'
              }`}
            >
              <span>{getCategoryIcon(cat)}</span>
              <span>{category.charAt(0).toUpperCase() + category.slice(1)} ({items.length})</span>
            </button>
          );
        })}
      </div>

      {isLoadingRelevancies ? (
        <div className="flex justify-center py-4">
          <div className="w-6 h-6 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : filteredRelevancies.length > 0 ? (
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
          {filteredRelevancies.map((relevancy, index) => {
            const category = mapRelevancyCategory(relevancy);
            const { bg, text, border } = getCategoryColorScheme(category);
            const isExpanded = expandedRelevancies[relevancy.relevancyId || index.toString()] || false;
            
            return (
              <div 
                key={relevancy.relevancyId || index} 
                className={`${bg} rounded-lg p-3 text-sm border ${border}`}
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="font-medium flex-1 pr-2 flex items-center gap-2">
                    <span className="text-lg">{getCategoryIcon(category)}</span>
                    <span className={text}>{formatRelevancyText(relevancy.title, citizen)}</span>
                  </div>
                  <div className="text-center">
                    <div className={`px-3 py-1 rounded-full text-xl font-bold ${
                      relevancy.score > 75 ? 'bg-teal-200 text-teal-800' :
                      relevancy.score > 50 ? 'bg-lime-200 text-lime-800' :
                      relevancy.score > 25 ? 'bg-yellow-200 text-yellow-800' :
                      'bg-gray-200 text-gray-800'
                    }`}>
                      {Math.round(relevancy.score)}
                    </div>
                    <p className="text-xs text-amber-600 mt-1">
                      {relevancy.timeHorizon === 'short' ? 'Urgent' : 
                       relevancy.timeHorizon === 'medium' ? 'Soon' : 
                       relevancy.timeHorizon === 'long' ? 'Future' : 'Opportunity'}
                    </p>
                  </div>
                </div>
                
                <div 
                  className={`text-xs ${text} mt-2 ${isExpanded ? '' : 'line-clamp-2'} cursor-pointer`}
                  onClick={() => toggleRelevancyExpanded(relevancy.relevancyId || index.toString())}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({node, ...props}) => <p {...props} className="my-1" />
                    }}
                  >
                    {formatRelevancyText(relevancy.description, citizen)}
                  </ReactMarkdown>
                </div>
                
                {!isExpanded && (
                  <button 
                    onClick={() => toggleRelevancyExpanded(relevancy.relevancyId || index.toString())}
                    className={`text-xs ${text} mt-1 hover:underline`}
                  >
                    Read more
                  </button>
                )}
                
                {isExpanded && relevancy.notes && (
                  <div className="mt-2 text-xs italic text-gray-600 border-t border-gray-200 pt-1">
                    <span className={text}>Notes:</span> {relevancy.notes}
                  </div>
                )}
                
                {isExpanded && (
                  <div className="mt-2 flex justify-between text-xs text-gray-500">
                    <span>
                      {relevancy.type && `Type: ${relevancy.type}`}
                    </span>
                    <button 
                      onClick={() => toggleRelevancyExpanded(relevancy.relevancyId || index.toString())}
                      className={`${text} hover:underline`}
                    >
                      Show less
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-amber-700 italic text-xs">
          {activeCategory === 'all' 
            ? "No notable relevancies with this citizen at present. Future ventures may arise as your paths cross in Venetian society."
            : `No ${activeCategory} relevancies found for this citizen.`}
        </p>
      )}

      {/* New Thoughts Section */}
      <div className="mt-4">
        <div className="flex items-center">
          <h4 className="text-md font-serif text-amber-700 mb-2 border-b border-amber-200 pb-1">Recent Musings</h4>
          <InfoIcon tooltipText="Latest thoughts recorded by this citizen." />
        </div>

        {isLoadingThoughts ? (
          <div className="flex justify-center py-2">
            <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : citizenThoughts.length > 0 ? (
          <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1 custom-scrollbar">
            {citizenThoughts.map((thought) => (
              <div key={thought.messageId} className="bg-stone-100 rounded-lg p-2.5 text-xs border border-stone-200">
                <p className="text-stone-700 italic">"{thought.mainThought}"</p>
                <p className="text-right text-stone-500 mt-1 text-[10px]">{formatThoughtDate(thought.createdAt)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-amber-700 italic text-xs">No recent thoughts recorded for this citizen.</p>
        )}
      </div>
    </>
  );
};

export default CitizenRelevanciesList;

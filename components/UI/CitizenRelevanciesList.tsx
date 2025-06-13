import React, { useState, useEffect } from 'react'; // Added useState, useEffect
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import InfoIcon from './InfoIcon'; // Assuming InfoIcon is in the same directory or adjust path

export interface DailyReflection extends Omit<Relevancy, 'score'> {
  score?: never; // Reflections don't get scores like regular relevancies
}

interface Relevancy {
  relevancyId: string;
  title: string;
  description: string;
  score: number; // This remains as part of the standard Airtable structure
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

// Add new interface for Thought
interface Thought {
  messageId: string;
  citizenUsername: string;
  originalContent: string;
  mainThought: string;
  createdAt: string;
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

const CitizenRelevanciesList: React.FC<CitizenRelevanciesListProps> = ({
  relevancies,
  isLoadingRelevancies,
  citizen,
}) => {
  const [citizenThoughts, setCitizenThoughts] = useState<Thought[]>([]);
  const [isLoadingThoughts, setIsLoadingThoughts] = useState<boolean>(false);

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

  const formatDailyReflectionText = (
    text: string,
    currentCitizen: CitizenForFormatting | null
  ): React.ReactNode => {
    if (!text || !currentCitizen) return text;
    
    // Format dates in the reflection content (if any)
    const formattedDatesText = text.replace(
      /(\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/g,
      (_, date1, date2) => {
        const formattedDate1 = new Date(date1).toLocaleDateString('en-US', { 
          weekday: 'long',
          month: 'long',
          day: 'numeric'
        });
        
        const formattedDate2 = new Date(date2).toLocaleDateString('en-US');
        
        return `${formattedDate1} - ${formattedDate2}`;
      }
    );
    
    // Replace placeholders like %TARGETCITIZEN%
    let newText = text;
    newText = newText.replace(/%CURRENT_CITIZEN_NAME%/g, currentCitizen.firstName ? `${currentCitizen.firstName.trim()} ` : 'citizen');
    newText = newText.replace(/%CURRENT_CITIZEN_USERNAME%/g, (currentCitizen.username || '').trim());
    newText = newText.replace(/(\*\*)(.*)(\*\*)/g, (_, open, text, close) => {
      // If this is a bold section, return just the text without formatting
      return text;
    });
    
    if (!newText.trim()) {
      // Default reflection text format if no special placeholders exist
      newText = `On ${currentCitizen.firstName} day, as an Artisti navigating Venice's trade landscape, I reflect on my journey through commerce and creativity.`;
    }
    
    return ReactMarkdown(formattedDatesText)(text);
  };

  return (
    <>
      <div className="flex items-center">
        <h3 className="text-lg font-serif text-amber-800 mb-2 border-b border-amber-200 pb-1">Connections</h3>
        <InfoIcon tooltipText="Opportunities and relevant links for this citizen, based on their activities, needs, and relationships with you or the community." />
      </div>

      {isLoadingRelevancies ? (
        <div className="flex justify-center py-4">
          <div className="w-6 h-6 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : relevancies.length > 0 ? (
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
          {relevancies.map((relevancy, index) => (
            <div key={relevancy.relevancyId || index} className="bg-amber-100 rounded-lg p-3 text-sm">
              <div className="flex items-start justify-between mb-1">
                <div className="font-medium text-amber-800 flex-1 pr-2">
                  {formatRelevancyText(relevancy.title, citizen)}
                </div>
                <div className="text-center">
                  <div className={`px-3 py-1 rounded-full text-xl font-bold ${
                    relevancy.score > 75 ? 'bg-teal-200 text-teal-800' :
                    relevancy.score > 25 ? 'bg-lime-200 text-lime-800' :
                    'bg-gray-200 text-gray-800'
                  }`}>
                    {Math.round(relevancy.score)}
                  </div>
                  <p className="text-xs text-amber-600 mt-1">Opportunity</p>
                </div>
              </div>
              <div className="text-xs text-amber-700 mt-2">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({node, ...props}) => <p {...props} className="my-1" />
                  }}
                >
                  {formatRelevancyText(relevancy.description, citizen)}
                </ReactMarkdown>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-amber-700 italic text-xs">No notable relevancies with this citizen at present. Future ventures may arise as your paths cross in Venetian society.</p>
      )}

      {/* New Daily Reflection Section */}
      <div className="mt-4">
        <div className="flex items-center">
          <h3 className="text-md font-serif text-amber-800 mb-2 border-b border-amber-200 pb-1">Daily Reflection</h3>
          <InfoIcon tooltipText="Latest journal entries and reflections from this citizen." />
        </div>

        {isLoadingReflections ? (
          <div className="flex justify-center py-2">
            <div className="w-5 h-5 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : dailyReflections.length > 0 ? (
          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
            {dailyReflections.map((reflection) => {
              // For each reflection, format the text and display it
              const formattedText = formatDailyReflectionText(reflection.content || '', citizen);
              
              return (
                <div key={reflection.relevancyId} className="bg-stone-100 rounded-lg p-3 border border-stone-200">
                  <p className="text-stone-700 italic text-sm">{formattedText}</p>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-amber-600 italic text-xs">No recent reflections recorded for this citizen.</p>
        )}
      </div>
      </div>
    </>
  );
};

export default CitizenRelevanciesList;

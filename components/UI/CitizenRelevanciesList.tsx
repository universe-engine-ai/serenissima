import React, { useState, useEffect } from 'react'; // Added useState, useEffect
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import InfoIcon from './InfoIcon'; // Assuming InfoIcon is in the same directory or adjust path

interface Relevancy {
  relevancyId: string;
  title: string;
  description: string;
  score: number;
  // Add any other fields from the relevancy object that are used
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
  // Thought fetching and related state have been removed from this component.
  // It is now handled by CitizenDetailsPanel and displayed by CitizenInfoColumn.

  return (
    <>
      <div className="flex items-center">
        <h3 className="text-lg font-serif text-amber-800 mb-2 border-b border-amber-200 pb-1">Connections</h3>
        <InfoIcon className="relative translate-x-[-2px] -translate-y-[4px] z-10" tooltipText="Opportunities and relevant links for this citizen, based on their activities, needs, and relationships with you or the community." />
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
    </>
  );
};

export default CitizenRelevanciesList;

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface CitizenConversationProps {
  speakerUsername: string;
  speakerFirstName: string;
  speakerLastName: string;
  speakerSocialClass: string;
  listenerUsername: string;
  listenerFirstName: string;
  listenerLastName: string;
  listenerSocialClass: string;
  onClose: () => void;
}

const CitizenConversation: React.FC<CitizenConversationProps> = ({
  speakerUsername,
  speakerFirstName,
  speakerLastName,
  speakerSocialClass,
  listenerUsername,
  listenerFirstName,
  listenerLastName,
  listenerSocialClass,
  onClose
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [conversation, setConversation] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConversation = async () => {
      try {
        setIsLoading(true);
        
        const response = await fetch('/api/conversations/initiate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            speaker_profile: {
              username: speakerUsername,
              firstName: speakerFirstName,
              lastName: speakerLastName,
              socialClass: speakerSocialClass
            },
            listener_profile: {
              username: listenerUsername,
              firstName: listenerFirstName,
              lastName: listenerLastName,
              socialClass: listenerSocialClass
            }
          }),
        });

        if (!response.ok) {
          throw new Error(`Error: ${response.status}`);
        }

        const data = await response.json();
        setConversation(data.conversation);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        console.error('Error fetching conversation:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConversation();
  }, [speakerUsername, listenerUsername]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-parchment border-2 border-amber-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <div className="bg-amber-800 text-white px-4 py-2 flex justify-between items-center">
          <h2 className="text-lg font-semibold">
            Conversation with {listenerFirstName} {listenerLastName}
          </h2>
          <button 
            onClick={onClose}
            className="text-white hover:text-amber-200"
          >
            ✕
          </button>
        </div>
        
        <div className="p-4 overflow-y-auto flex-grow">
          {isLoading ? (
            <div className="flex justify-center items-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-amber-800"></div>
            </div>
          ) : error ? (
            <div className="text-red-600 p-4 border border-red-300 rounded bg-red-50">
              {error}
            </div>
          ) : (
            <div className="prose prose-amber max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {conversation}
              </ReactMarkdown>
            </div>
          )}
        </div>
        
        <div className="bg-amber-100 p-4 border-t border-amber-300">
          <div className="flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-amber-800 text-white rounded hover:bg-amber-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CitizenConversation;

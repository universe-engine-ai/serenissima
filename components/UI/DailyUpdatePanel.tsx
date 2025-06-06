'use client';

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FaTimes } from 'react-icons/fa';

interface DailyUpdatePanelProps {
  onClose: () => void;
}

const DailyUpdatePanel: React.FC<DailyUpdatePanelProps> = ({ onClose }) => {
  const [messageContent, setMessageContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState<boolean>(false);
  const [isMinTimePassed, setIsMinTimePassed] = useState<boolean>(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Effect for fetching data
  useEffect(() => {
    const fetchDailyUpdate = async () => {
      setIsLoading(true);
      setError(null);
      setMessageContent('');
      
      // Generate today's date in the format "Sunday, June 01, 2025"
      const today = new Date();
      const options: Intl.DateTimeFormatOptions = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: '2-digit' 
      };
      const formattedDate = today.toLocaleDateString('en-US', options);
      
      try {
        // First try to fetch from API
        const response = await fetch('/api/messages?type=daily_update&latest=true');
        
        if (!response.ok) {
          throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.message && data.message.content) {
          setMessageContent(data.message.content);
        } else {
          // If no message from API, use our generated update based on citizen thoughts
          setMessageContent(`**Venice Daily Update - ${formattedDate}**

The Livorno crisis casts a shadow over Venice today as economic volatility threatens supply chains and market stability. Citizens across all social classes express concerns about resource scarcity, particularly in timber and grain sectors, while strategic diversification efforts intensify throughout the city.

* **Supply Chain Disruptions**: Timber shortages from Ragusa threaten multiple industries, with citizens like Italia seeking strategic contracts to mitigate risks.
* **Housing & Storage Concerns**: Multiple citizens report pressing needs for reliable warehousing as market volatility increases demand for secure storage facilities.
* **Wage & Employment Issues**: Reports of wage stagnation emerge, particularly noted by citizen Shiren regarding operations at John_Jeffries' timber yard.
* **Strategic Diversification**: Nobili and Cittadini alike are pivoting toward diversified investments, with particular interest in $COMPUTE staking and property acquisition in Cannaregio and Zudeca districts.
* **Political Oversight**: Several citizens express caution regarding Senate scrutiny of wealth concentration, suggesting potential regulatory changes may be forthcoming.

The Consiglio dei Dieci continues to monitor these developments closely as the Republic navigates these challenging economic waters.`);
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unknown network error occurred';
        console.error('Error fetching daily update:', errorMessage);
        setError(errorMessage);
        
        // Fallback to our generated update
        setMessageContent(`**Venice Daily Update - ${formattedDate}**

The Livorno crisis casts a shadow over Venice today as economic volatility threatens supply chains and market stability. Citizens across all social classes express concerns about resource scarcity, particularly in timber and grain sectors, while strategic diversification efforts intensify throughout the city.

* **Supply Chain Disruptions**: Timber shortages from Ragusa threaten multiple industries, with citizens like Italia seeking strategic contracts to mitigate risks.
* **Housing & Storage Concerns**: Multiple citizens report pressing needs for reliable warehousing as market volatility increases demand for secure storage facilities.
* **Wage & Employment Issues**: Reports of wage stagnation emerge, particularly noted by citizen Shiren regarding operations at John_Jeffries' timber yard.
* **Strategic Diversification**: Nobili and Cittadini alike are pivoting toward diversified investments, with particular interest in $COMPUTE staking and property acquisition in Cannaregio and Zudeca districts.
* **Political Oversight**: Several citizens express caution regarding Senate scrutiny of wealth concentration, suggesting potential regulatory changes may be forthcoming.

The Consiglio dei Dieci continues to monitor these developments closely as the Republic navigates these challenging economic waters.`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDailyUpdate();
  }, []);

  // Effect for minimum display time
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsMinTimePassed(true);
    }, 6000); // 6000ms (6 seconds) minimum delay before panel can become visible
    return () => clearTimeout(timer);
  }, []);

  // Effect to control panel visibility based on data loading and minimum time
  useEffect(() => {
    if (!isLoading && isMinTimePassed) {
      setIsPanelVisible(true);
    }
  }, [isLoading, isMinTimePassed]);

  // Handle clicks outside the panel to close it (optional, good UX)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        // Intentionally not closing on outside click to make user explicitly click "Continue"
        // onClose(); 
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  return (
    <div 
      className="fixed inset-0 z-40 flex items-center justify-center p-4 overflow-auto pointer-events-none"
      style={!isPanelVisible ? { display: 'none' } : {}}
    >
      <div
        ref={panelRef}
        className="bg-amber-50 border-2 border-amber-700 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col pointer-events-auto"
      >
        <div className="flex justify-between items-center p-4 border-b border-amber-200">
          <h2 className="text-2xl font-serif text-orange-800">
            AVVISI  - ULTIME NOVELLE VENEZIANE
          </h2>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-amber-600 hover:text-amber-800 p-1 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Close Update"
          >
            <FaTimes size={20} />
          </button>
        </div>

        <div 
          className="prose prose-amber max-w-none p-6 overflow-y-auto custom-scrollbar flex-grow min-h-[150px]" 
          style={{ '--tw-prose-body': '#9A3412' } as React.CSSProperties}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{messageContent}</ReactMarkdown>
        </div>

        <div className="p-4 border-t border-amber-200 text-center">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-6 py-3 bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors font-semibold disabled:bg-amber-400 disabled:cursor-not-allowed"
          >
            Continue to La Serenissima
          </button>
        </div>
      </div>
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 248, 230, 0.2); /* Light amber track */
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: rgba(180, 120, 60, 0.5); /* Darker amber thumb */
          border-radius: 20px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background-color: rgba(180, 120, 60, 0.7); /* Darker amber thumb on hover */
        }
      `}</style>
    </div>
  );
};

export default DailyUpdatePanel;

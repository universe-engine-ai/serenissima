import React, { useState, useImperativeHandle, forwardRef, useRef, useMemo } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, CitizenOption } from './types';
import { FaUserShield, FaTimes, FaCommentDots, FaExclamationTriangle } from 'react-icons/fa';

const MarketplaceGossipStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, citizens, isLoading, currentUserUsername, currentUserFirstName, currentUserLastName } = props;

  const [targetCitizenUsername, setTargetCitizenUsername] = useState<string | null>(null);
  const [citizenSearch, setCitizenSearch] = useState('');
  const [isCitizenDropdownOpen, setIsCitizenDropdownOpen] = useState(false);
  const citizenInputRef = useRef<HTMLInputElement>(null);
  const [gossipContent, setGossipContent] = useState('');

  const summaryElements = useMemo(() => {
    const executorName = (currentUserFirstName && currentUserLastName)
      ? `${currentUserFirstName} ${currentUserLastName}`
      : currentUserUsername || "You";

    let targetDescription: JSX.Element | string = <span className="font-italic text-gray-600">general gossip (no specific target)</span>;
    if (targetCitizenUsername) {
      const citizen = citizens.find(c => c.username === targetCitizenUsername);
      const citizenDisplayName = (citizen?.firstName && citizen?.lastName)
        ? `${citizen.firstName} ${citizen.lastName} (${citizen.username})`
        : citizen?.username || targetCitizenUsername;
      targetDescription = <>citizen <span className="font-bold">{citizenDisplayName}</span></>;
    }

    let gossipDescription: JSX.Element | string = "";
    if (gossipContent.trim()) {
      gossipDescription = <> by spreading the rumor: <span className="font-semibold">"{gossipContent.trim().substring(0, 50)}{gossipContent.trim().length > 50 ? '...' : ''}"</span></>;
    } else {
      gossipDescription = <span className="font-bold text-red-500"> (gossip content required)</span>;
    }
    
    return (
      <>
        <span className="font-bold">{executorName}</span> will attempt to damage the reputation of {targetDescription}{gossipDescription} by initiating gossip in populated areas. <em className="italic">(Aggressive)</em>
      </>
    );
  }, [targetCitizenUsername, gossipContent, currentUserUsername, currentUserFirstName, currentUserLastName, citizens]);

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!gossipContent.trim()) {
        return null; // Details incomplete - only content is required
      }
      const details: any = {
        gossipContent: gossipContent.trim(),
        // durationHours, name, description, notes are handled by the creator with defaults
      };
      
      // Only include targetCitizen if one was selected
      if (targetCitizenUsername) {
        details.targetCitizen = targetCitizenUsername;
      }
      
      return details;
    },
  }));

  return (
    <div>
      {/* Target Citizen Selector */}
      <div className="mb-4">
        <label htmlFor="marketplace_gossip_targetCitizen_search" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUserShield className="mr-2" /> Target Citizen <span className="text-gray-500 ml-1">(optional)</span>
        </label>
        <div className="relative">
          <input
            id="marketplace_gossip_targetCitizen_search"
            type="text"
            ref={citizenInputRef}
            value={citizenSearch}
            onChange={(e) => {
              setCitizenSearch(e.target.value);
              if (!isCitizenDropdownOpen) setIsCitizenDropdownOpen(true);
              if (targetCitizenUsername) setTargetCitizenUsername(null); // Clear selection if user types
            }}
            onFocus={() => setIsCitizenDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsCitizenDropdownOpen(false), 150)} // Delay to allow click on dropdown
            placeholder={targetCitizenUsername ? citizens.find(c => c.username === targetCitizenUsername)?.username || 'Search...' : 'Search Citizens...'}
            className={`w-full p-2 border rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500 border-amber-300`}
            disabled={isLoading}
          />
          {targetCitizenUsername && (
            <button
              type="button"
              onClick={() => {
                setTargetCitizenUsername(null);
                setCitizenSearch('');
                citizenInputRef.current?.focus();
              }}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
              aria-label="Clear selection"
            >
              <FaTimes />
            </button>
          )}
          {isCitizenDropdownOpen && (
            <ul className="absolute z-10 w-full bg-white border border-amber-300 rounded-md mt-1 shadow-lg max-h-60 overflow-y-auto">
              {citizens
                // Removed filter that prevented targeting self
                .filter(c => {
                  const searchTermLower = citizenSearch.toLowerCase();
                  const namePart = [c.firstName, c.lastName].filter(Boolean).join(' ').toLowerCase();
                  return (c.username && c.username.toLowerCase().includes(searchTermLower)) ||
                         namePart.includes(searchTermLower) ||
                         (c.socialClass && c.socialClass.toLowerCase().includes(searchTermLower));
                })
                .map((c, index) => {
                  const namePart = [c.firstName, c.lastName].filter(Boolean).join(' ');
                  const citizenMainIdentifier = namePart ? `${namePart} (${c.username || 'ID Manquant'})` : (c.username || '');
                  const socialClassDisplay = c.socialClass || 'N/A';
                  const finalDisplayString = citizenMainIdentifier ? `${citizenMainIdentifier} - ${socialClassDisplay}` : `[Citoyen Inconnu] - ${socialClassDisplay}`;
                  return (
                    <li
                      key={`marketplace-gossip-citizen-opt-${c.username || index}`}
                      onClick={() => {
                        setTargetCitizenUsername(c.username || null);
                        setCitizenSearch(finalDisplayString);
                        setIsCitizenDropdownOpen(false);
                      }}
                      className="p-2 hover:bg-amber-100 cursor-pointer text-amber-800"
                    >
                      {finalDisplayString}
                    </li>
                  );
                })}
            </ul>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          If no target is specified, the gossip will be about a general topic rather than a specific citizen.
        </p>
      </div>

      {/* Gossip Content Textarea */}
      <div className="mb-4">
        <label htmlFor="marketplace_gossip_content" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaCommentDots className="mr-2" /> Gossip Content <span className="text-red-500 ml-1">*</span>
        </label>
        <textarea
          id="marketplace_gossip_content"
          value={gossipContent}
          onChange={(e) => setGossipContent(e.target.value)}
          placeholder="e.g., 'I heard they've been seen consorting with known smugglers...', 'Their latest venture is on the brink of collapse...'"
          rows={4}
          className={`w-full p-2 border rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500 ${!gossipContent.trim() ? 'border-red-400' : 'border-amber-300'}`}
          disabled={isLoading}
        />
        <p className="text-xs text-gray-500 mt-1">
          Craft the rumor you want to spread. This will be used by your citizen to initiate conversations. Note that gossip is not necessarily negative, though it often is.
        </p>
        {!gossipContent.trim() && (
          <p className="text-xs text-red-500 mt-1">Gossip content is required.</p>
        )}
      </div>
      
      {summaryElements && (
        <div className="mt-6 p-3 bg-amber-100 border border-amber-200 rounded-md text-base text-amber-800 flex items-start">
          <FaExclamationTriangle className="text-amber-600 mr-2 mt-1 flex-shrink-0" size={18} />
          <span>{summaryElements}</span>
        </div>
      )}
    </div>
  );
});

MarketplaceGossipStratagemPanel.displayName = 'MarketplaceGossipStratagemPanel';
export default MarketplaceGossipStratagemPanel;

import React, { useState, useImperativeHandle, forwardRef, useRef, useMemo } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, CitizenOption } from './types';
import { FaUserShield, FaTimes, FaExclamationTriangle } from 'react-icons/fa';

const ReputationAssaultStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, citizens, isLoading, currentUserUsername, currentUserFirstName, currentUserLastName } = props;

  const [targetCitizenUsername, setTargetCitizenUsername] = useState<string | null>(null);
  const [citizenSearch, setCitizenSearch] = useState('');
  const [isCitizenDropdownOpen, setIsCitizenDropdownOpen] = useState(false);
  const citizenInputRef = useRef<HTMLInputElement>(null);
  const [assaultAngle, setAssaultAngle] = useState('');

  // const calculatedInfluenceCost = stratagemData.influenceCostBase; // Fixed cost // Removed

  const summaryElements = useMemo(() => {
    const executorName = (currentUserFirstName && currentUserLastName)
      ? `${currentUserFirstName} ${currentUserLastName}`
      : currentUserUsername || "You";

    let targetDescription: JSX.Element | string = <span className="font-bold text-red-500">a target citizen (required)</span>;

    if (targetCitizenUsername) {
      const citizen = citizens.find(c => c.username === targetCitizenUsername);
      const citizenDisplayName = (citizen?.firstName && citizen?.lastName)
        ? `${citizen.firstName} ${citizen.lastName} (${citizen.username})`
        : citizen?.username || targetCitizenUsername;
      targetDescription = <>citizen <span className="font-bold">{citizenDisplayName}</span></>;
    }

    let angleDescription: JSX.Element | string = "";
    if (assaultAngle.trim()) {
      angleDescription = <> focusing on the angle: <span className="font-semibold">"{assaultAngle.trim()}"</span></>;
    }
    
    let modelDescription = "";
    // KinosModelOverride removed from here

    return (
      <>
        <span className="font-bold">{executorName}</span> will attempt to damage the reputation of {targetDescription} by spreading negative information to their associates{angleDescription}. <em className="italic">(Aggressive)</em>
      </>
    );
  }, [targetCitizenUsername, assaultAngle, currentUserUsername, currentUserFirstName, currentUserLastName, citizens]);

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetCitizenUsername) {
        return null; // Details incomplete
      }
      return {
        targetCitizen: targetCitizenUsername,
        assaultAngle: assaultAngle.trim() || null,
        // kinosModelOverride removed
        // durationHours, name, description, notes are handled by the creator with defaults
      };
    },
    // getCalculatedInfluenceCost: () => { // Removed
    //   return calculatedInfluenceCost; // Removed
    // } // Removed
  }));

  return (
    <div>
      {/* Target Citizen Selector */}
      <div className="mb-4">
        <label htmlFor="reputation_assault_targetCitizen_search" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUserShield className="mr-2" /> Target Citizen <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="relative">
          <input
            id="reputation_assault_targetCitizen_search"
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
            className={`w-full p-2 border rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500 ${!targetCitizenUsername ? 'border-red-400' : 'border-amber-300'}`}
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
                .filter(c => c.username !== currentUserUsername) // Cannot target self
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
                      key={`reputation-assault-citizen-opt-${c.username || index}`}
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
        {!targetCitizenUsername && (
          <p className="text-xs text-red-500 mt-1">Target citizen is required.</p>
        )}
      </div>

      {/* Assault Angle Textarea */}
      <div className="mb-4">
        <label htmlFor="reputation_assault_angle" className="block text-sm font-medium text-amber-800 mb-1">
          Assault Angle / Theme (Optional)
        </label>
        <textarea
          id="reputation_assault_angle"
          value={assaultAngle}
          onChange={(e) => setAssaultAngle(e.target.value)}
          placeholder="e.g., 'Their recent business failures', 'Their questionable alliances', 'Their extravagant spending habits...'"
          rows={3}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        />
        <p className="text-xs text-gray-500 mt-1">
          Provide a specific theme or angle for the negative information. This will guide the AI in crafting the messages.
        </p>
      </div>

      {/* KinOS Model Override Input REMOVED */}

      {summaryElements && (
        <div className="mt-6 p-3 bg-amber-100 border border-amber-200 rounded-md text-base text-amber-800 flex items-start">
          <FaExclamationTriangle className="text-amber-600 mr-2 mt-1 flex-shrink-0" size={18} />
          <span>{summaryElements}</span>
        </div>
      )}
    </div>
  );
});

ReputationAssaultStratagemPanel.displayName = 'ReputationAssaultStratagemPanel';
export default ReputationAssaultStratagemPanel;

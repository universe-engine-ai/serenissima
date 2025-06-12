import React, { useState, useImperativeHandle, forwardRef, useRef, useMemo } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, CitizenOption } from './types';
import { FaUserShield, FaTimes, FaSkullCrossbones } from 'react-icons/fa';

const CanalMuggingStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, citizens, isLoading, currentUserUsername, currentUserFirstName, currentUserLastName } = props;

  const [targetCitizenUsername, setTargetCitizenUsername] = useState<string | null>(null);
  const [citizenSearch, setCitizenSearch] = useState('');
  const [isCitizenDropdownOpen, setIsCitizenDropdownOpen] = useState(false);
  const citizenInputRef = useRef<HTMLInputElement>(null);

  const calculatedInfluenceCost = stratagemData.influenceCostBase;

  const summaryElements = useMemo(() => {
    const executorName = (currentUserFirstName && currentUserLastName)
      ? `${currentUserFirstName} ${currentUserLastName}`
      : currentUserUsername || "You";

    let targetDescription: JSX.Element | string;

    if (targetCitizenUsername) {
      const citizen = citizens.find(c => c.username === targetCitizenUsername);
      const citizenDisplayName = (citizen?.firstName && citizen?.lastName)
        ? `${citizen.firstName} ${citizen.lastName} (${citizen.username})`
        : citizen?.username || targetCitizenUsername;
      targetDescription = <>citizen <span className="font-bold">{citizenDisplayName}</span></>;
    } else {
      targetDescription = <span className="font-bold">an opportune citizen</span>;
    }

    return (
      <>
        <span className="font-bold">{executorName}</span> will attempt to mug {targetDescription} during a gondola transit.
      </>
    );
  }, [targetCitizenUsername, currentUserUsername, currentUserFirstName, currentUserLastName, citizens]);

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      const details: Record<string, any> = {};
      if (targetCitizenUsername) {
        details.targetCitizenUsername = targetCitizenUsername;
      }
      // targetActivityId is not selected in this panel, will be handled by processor if needed
      return details;
    },
    getCalculatedInfluenceCost: () => {
      return calculatedInfluenceCost;
    }
  }));

  return (
    <div>
      <div className="mb-4">
        <label htmlFor="canal_mugging_targetCitizen_search" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUserShield className="mr-2" /> Target Citizen (Optional)
        </label>
        <p className="text-xs text-amber-600 mb-1">If no citizen is selected, the stratagem will target the next opportune victim found by the system.</p>
        <div className="relative">
          <input
            id="canal_mugging_targetCitizen_search"
            type="text"
            ref={citizenInputRef}
            value={citizenSearch}
            onChange={(e) => {
              setCitizenSearch(e.target.value);
              if (!isCitizenDropdownOpen) setIsCitizenDropdownOpen(true);
              if (targetCitizenUsername) setTargetCitizenUsername(null);
            }}
            onFocus={() => setIsCitizenDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsCitizenDropdownOpen(false), 150)}
            placeholder={targetCitizenUsername ? citizens.find(c => c.username === targetCitizenUsername)?.username || 'Search...' : 'Search Citizens (or leave blank)...'}
            className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
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
                .filter(c => c.username !== currentUserUsername) // Exclude self
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
                      key={`canal-mugging-citizen-opt-${c.username || index}`}
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
      </div>

      {summaryElements && (
        <div className="mt-6 p-3 bg-rose-100 border border-rose-200 rounded-md text-base text-rose-800 flex items-start">
          <FaSkullCrossbones className="text-rose-600 mr-2 mt-1 flex-shrink-0" size={18} />
          <span>{summaryElements}</span>
        </div>
      )}
    </div>
  );
});

CanalMuggingStratagemPanel.displayName = 'CanalMuggingStratagemPanel';
export default CanalMuggingStratagemPanel;

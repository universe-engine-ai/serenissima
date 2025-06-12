import React, { useState, useImperativeHandle, forwardRef, useRef, useMemo } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, LandOption } from './types'; // Removed CitizenOption, Added LandOption
import { FaMapMarkedAlt, FaTimes, FaSkullCrossbones } from 'react-icons/fa'; // Changed FaUserShield to FaMapMarkedAlt

const CanalMuggingStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, lands, isLoading, currentUserUsername, currentUserFirstName, currentUserLastName } = props; // Changed citizens to lands

  const [targetLandId, setTargetLandId] = useState<string | null>(null);
  const [landSearch, setLandSearch] = useState('');
  const [isLandDropdownOpen, setIsLandDropdownOpen] = useState(false);
  const landInputRef = useRef<HTMLInputElement>(null);

  const calculatedInfluenceCost = stratagemData.influenceCostBase;

  const summaryElements = useMemo(() => {
    const executorName = (currentUserFirstName && currentUserLastName)
      ? `${currentUserFirstName} ${currentUserLastName}`
      : currentUserUsername || "You";

    let targetDescription: JSX.Element | string;

    if (targetLandId) {
      const land = lands.find(l => l.landId === targetLandId);
      const landDisplayName = land?.englishName || land?.historicalName || targetLandId;
      targetDescription = <>in the vicinity of land parcel <span className="font-bold">{landDisplayName}</span></>;
    } else {
      targetDescription = <span className="font-bold">any opportune location</span>;
    }

    return (
      <>
        <span className="font-bold">{executorName}</span> will attempt to mug an opportune citizen during a gondola transit {targetDescription} (illegal).
      </>
    );
  }, [targetLandId, currentUserUsername, currentUserFirstName, currentUserLastName, lands]);

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      const details: Record<string, any> = {};
      if (targetLandId) {
        details.targetLandId = targetLandId;
      }
      return details;
    },
    getCalculatedInfluenceCost: () => {
      return calculatedInfluenceCost;
    }
  }));

  return (
    <div>
      <div className="mb-4">
        <label htmlFor="canal_mugging_targetLand_search" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaMapMarkedAlt className="mr-2" /> Target Land (Recommended)
        </label>
        <p className="text-xs text-amber-600 mb-1">If no land is selected, the stratagem will be deployed at a random location.</p>
        <div className="relative">
          <input
            id="canal_mugging_targetLand_search"
            type="text"
            ref={landInputRef}
            value={landSearch}
            onChange={(e) => {
              setLandSearch(e.target.value);
              if (!isLandDropdownOpen) setIsLandDropdownOpen(true);
              if (targetLandId) setTargetLandId(null);
            }}
            onFocus={() => setIsLandDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsLandDropdownOpen(false), 150)}
            placeholder={targetLandId ? lands.find(l => l.landId === targetLandId)?.englishName || lands.find(l => l.landId === targetLandId)?.historicalName || 'Search...' : 'Search Land Parcels (or leave blank)...'}
            className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
            disabled={isLoading}
          />
          {targetLandId && (
            <button
              type="button"
              onClick={() => {
                setTargetLandId(null);
                setLandSearch('');
                landInputRef.current?.focus();
              }}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
              aria-label="Clear selection"
            >
              <FaTimes />
            </button>
          )}
          {isLandDropdownOpen && (
            <ul className="absolute z-10 w-full bg-white border border-amber-300 rounded-md mt-1 shadow-lg max-h-60 overflow-y-auto">
              {lands
                .filter(l => {
                  const searchTermLower = landSearch.toLowerCase();
                  return (l.landId && l.landId.toLowerCase().includes(searchTermLower)) ||
                         (l.englishName && l.englishName.toLowerCase().includes(searchTermLower)) ||
                         (l.historicalName && l.historicalName.toLowerCase().includes(searchTermLower)) ||
                         (l.district && l.district.toLowerCase().includes(searchTermLower)) ||
                         (l.owner && l.owner.toLowerCase().includes(searchTermLower));
                })
                .map((l, index) => {
                  const displayName = l.englishName || l.historicalName || l.landId;
                  const districtDisplay = l.district || 'N/A';
                  const finalDisplayString = `${displayName} (District: ${districtDisplay}, Owner: ${l.owner || 'Unowned'})`;
                  return (
                    <li
                      key={`canal-mugging-land-opt-${l.landId || index}`}
                      onClick={() => {
                        setTargetLandId(l.landId || null);
                        setLandSearch(finalDisplayString);
                        setIsLandDropdownOpen(false);
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

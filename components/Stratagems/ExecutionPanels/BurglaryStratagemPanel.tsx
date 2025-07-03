import React, { useState, useImperativeHandle, forwardRef, useRef, useMemo } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, BuildingOption } from './types';
import { FaBuilding, FaTimes, FaExclamationTriangle } from 'react-icons/fa';

const BurglaryStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, buildings, isLoading, currentUserUsername, currentUserFirstName, currentUserLastName } = props;

  const [targetBuildingId, setTargetBuildingId] = useState<string | null>(null);
  const [buildingSearch, setBuildingSearch] = useState('');
  const [isBuildingDropdownOpen, setIsBuildingDropdownOpen] = useState(false);
  const buildingInputRef = useRef<HTMLInputElement>(null);

  // const calculatedInfluenceCost = stratagemData.influenceCostBase; // Burglary has a fixed cost // Removed

  const summaryElements = useMemo(() => {
    const executorName = (currentUserFirstName && currentUserLastName)
      ? `${currentUserFirstName} ${currentUserLastName}`
      : currentUserUsername || "You";

    let targetDescription: JSX.Element | string = <span className="font-bold text-red-500">a target building (required)</span>;

    if (targetBuildingId) {
      const building = buildings.find(b => b.buildingId === targetBuildingId);
      const buildingDisplayName = building?.name || targetBuildingId;
      targetDescription = <>building <span className="font-bold">{buildingDisplayName}</span></>;
    }

    return (
      <>
        <span className="font-bold">{executorName}</span> will attempt to burgle {targetDescription} to steal tools, materials, or finished goods. <em className="italic">(Illegal and Risky)</em>
      </>
    );
  }, [targetBuildingId, currentUserUsername, currentUserFirstName, currentUserLastName, buildings]);

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetBuildingId) {
        // Optionally, you could set an error state here to display to the user
        // For now, returning null signals to the parent that details are incomplete.
        return null;
      }
      return {
        targetBuildingId: targetBuildingId,
        // Other parameters like name, description, notes are handled by the creator with defaults
      };
    },
    // getCalculatedInfluenceCost: () => { // Removed
    //   return calculatedInfluenceCost; // Removed
    // } // Removed
  }));

  return (
    <div>
      {/* Target Building Selector */}
      <div className="mb-4">
        <label htmlFor="burglary_targetBuilding_search" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaBuilding className="mr-2" /> Target Building <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="relative">
          <input
            id="burglary_targetBuilding_search"
            type="text"
            ref={buildingInputRef}
            value={buildingSearch}
            onChange={(e) => {
              setBuildingSearch(e.target.value);
              if (!isBuildingDropdownOpen) setIsBuildingDropdownOpen(true);
              if (targetBuildingId) setTargetBuildingId(null); // Clear selection if user types
            }}
            onFocus={() => setIsBuildingDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsBuildingDropdownOpen(false), 150)} // Delay to allow click on dropdown
            placeholder={targetBuildingId ? buildings.find(b => b.buildingId === targetBuildingId)?.name || 'Search...' : 'Search Buildings...'}
            className={`w-full p-2 border rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500 ${!targetBuildingId ? 'border-red-400' : 'border-amber-300'}`}
            disabled={isLoading}
          />
          {targetBuildingId && (
            <button
              type="button"
              onClick={() => {
                setTargetBuildingId(null);
                setBuildingSearch('');
                buildingInputRef.current?.focus();
              }}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
              aria-label="Clear selection"
            >
              <FaTimes />
            </button>
          )}
          {isBuildingDropdownOpen && (
            <ul className="absolute z-10 w-full bg-white border border-amber-300 rounded-md mt-1 shadow-lg max-h-60 overflow-y-auto">
              {buildings
                .filter(b => b.owner !== currentUserUsername) // Cannot burgle own building
                .filter(b => {
                  const searchTermLower = buildingSearch.toLowerCase();
                  return (b.name && b.name.toLowerCase().includes(searchTermLower)) ||
                         (b.buildingId && b.buildingId.toLowerCase().includes(searchTermLower)) ||
                         (b.type && b.type.toLowerCase().includes(searchTermLower)) ||
                         (b.owner && b.owner.toLowerCase().includes(searchTermLower));
                })
                .map((b, index) => (
                  <li
                    key={`burglary-building-opt-${b.buildingId || index}`}
                    onClick={() => {
                      setTargetBuildingId(b.buildingId);
                      setBuildingSearch(b.name || b.buildingId);
                      setIsBuildingDropdownOpen(false);
                    }}
                    className="p-2 hover:bg-amber-100 cursor-pointer text-amber-800"
                  >
                    {b.name || b.buildingId} (Owner: {b.owner || 'N/A'}, Type: {b.type || 'N/A'})
                  </li>
                ))}
            </ul>
          )}
        </div>
        {!targetBuildingId && (
          <p className="text-xs text-red-500 mt-1">Target building is required.</p>
        )}
      </div>

      {summaryElements && (
        <div className="mt-6 p-3 bg-rose-100 border border-rose-200 rounded-md text-base text-rose-800 flex items-start">
          <FaExclamationTriangle className="text-rose-600 mr-2 mt-1 flex-shrink-0" size={18} />
          <span>{summaryElements}</span>
        </div>
      )}
    </div>
  );
});

BurglaryStratagemPanel.displayName = 'BurglaryStratagemPanel';
export default BurglaryStratagemPanel;

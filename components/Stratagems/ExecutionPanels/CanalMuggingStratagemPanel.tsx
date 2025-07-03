import React, { useState, useImperativeHandle, forwardRef, useRef, useMemo } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, LandOption } from './types';
import { FaMapMarkedAlt, FaTimes, FaSkullCrossbones, FaMoon, FaClock } from 'react-icons/fa'; // Added FaClock

type MuggingVariant = 'Mild' | 'Standard' | 'Aggressive';

const BASE_INFLUENCE_COST_PER_DAY = 1; // Define base cost per day

const CanalMuggingStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, lands, isLoading, currentUserUsername, currentUserFirstName, currentUserLastName } = props;

  const [targetLandId, setTargetLandId] = useState<string | null>(null);
  const [landSearch, setLandSearch] = useState('');
  const [isLandDropdownOpen, setIsLandDropdownOpen] = useState(false);
  const landInputRef = useRef<HTMLInputElement>(null);
  
  const [durationDays, setDurationDays] = useState<number>(3); // Default 3 days
  const [selectedVariant, setSelectedVariant] = useState<MuggingVariant>('Standard');

  // Influence cost is now dynamic: durationDays * baseCostPerDay // Removed
  // const calculatedInfluenceCost = useMemo(() => durationDays * BASE_INFLUENCE_COST_PER_DAY, [durationDays]); // Removed

  const summaryElements = useMemo(() => {
    const executorName = (currentUserFirstName && currentUserLastName)
      ? `${currentUserFirstName} ${currentUserLastName}`
      : currentUserUsername || "You";

    let targetDescription: JSX.Element | string;
    let variantDescription: string;

    if (targetLandId) {
      const land = lands.find(l => l.landId === targetLandId);
      const landDisplayName = land?.englishName || land?.historicalName || targetLandId;
      targetDescription = <>in the vicinity of land parcel <span className="font-bold">{landDisplayName}</span></>;
    } else {
      targetDescription = <span className="font-bold">any opportune location</span>;
    }

    switch (selectedVariant) {
      case 'Mild':
        variantDescription = "cautiously, targeting isolated victims when no one else is nearby";
        break;
      case 'Aggressive':
        variantDescription = "aggressively, attempting muggings more frequently and with less caution";
        break;
      case 'Standard':
      default:
        variantDescription = "opportunistically, based on victim vulnerability and perceived risk";
        break;
    }

    return (
      <>
        <span className="font-bold">{executorName}</span> will attempt to rob citizens at night for <span className="font-bold">{durationDays} day{durationDays > 1 ? 's' : ''}</span> during gondola transits {targetDescription}, operating {variantDescription}. <em className="italic">(Illegal)</em>
      </>
    );
  }, [targetLandId, selectedVariant, durationDays, currentUserUsername, currentUserFirstName, currentUserLastName, lands]);

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      const details: Record<string, any> = {
        variant: selectedVariant,
        durationDays: durationDays,
      };
      if (targetLandId) {
        details.targetLandId = targetLandId;
      }
      return details;
    },
    // getCalculatedInfluenceCost: () => { // Removed
    //   return calculatedInfluenceCost; // Removed
    // } // Removed
  }));

  return (
    <div>
      {/* Target Land Parcel Selector */}
      <div className="mb-4">
        <label htmlFor="canal_mugging_targetLand_search" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaMapMarkedAlt className="mr-2" /> Target Land Parcel (Optional)
        </label>
        <p className="text-xs text-amber-600 mb-1">If no land parcel is selected, the stratagem will target any opportune victim found by the system.</p>
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

      {/* Duration Slider - New Element */}
      <div className="mb-6">
        <label htmlFor="canal_mugging_duration" className="block text-sm font-medium text-amber-800 mb-2 flex items-center">
          <FaClock className="mr-2" /> Duration: <span className="font-bold ml-1">{durationDays} day{durationDays > 1 ? 's' : ''}</span>
        </label>
        <input
          id="canal_mugging_duration"
          type="range"
          min="1"
          max="7"
          value={durationDays}
          onChange={(e) => setDurationDays(parseInt(e.target.value, 10))}
          className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-rose-600"
          disabled={isLoading}
        />
        <div className="flex justify-between text-xs text-amber-600 mt-1">
          <span>1 day</span>
          <span>7 days</span>
        </div>
        {/* <p className="text-xs text-amber-600 mt-1">Influence cost will be {calculatedInfluenceCost}🎭 ({durationDays} x {BASE_INFLUENCE_COST_PER_DAY} per day).</p> // Removed */}
      </div>

      {/* Variant Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-amber-800 mb-2 flex items-center">
          <FaMoon className="mr-2" /> Mugging Approach (Variant)
        </label>
        <div className="flex space-x-2">
          {(['Mild', 'Standard', 'Aggressive'] as MuggingVariant[]).map((variant) => (
            <button
              key={variant}
              type="button"
              onClick={() => setSelectedVariant(variant)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors w-1/3
                ${selectedVariant === variant 
                  ? 'bg-rose-600 text-white shadow-md ring-2 ring-rose-400' 
                  : 'bg-amber-200 text-amber-800 hover:bg-amber-300'
                }
                ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              disabled={isLoading}
            >
              {variant}
            </button>
          ))}
        </div>
         <p className="text-xs text-amber-600 mt-2">
          {selectedVariant === 'Mild' && "Target isolated victims when no one else is nearby. Lower risk, potentially lower reward."}
          {selectedVariant === 'Standard' && "Decide opportunistically based on victim vulnerability and perceived risk. Balanced risk/reward."}
          {selectedVariant === 'Aggressive' && "Attempt muggings more frequently and with less caution. Higher risk, potentially higher reward."}
        </p>
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

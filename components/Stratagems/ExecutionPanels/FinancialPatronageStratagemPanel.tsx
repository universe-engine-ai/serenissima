import React, { useState, useImperativeHandle, forwardRef, useRef } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, CitizenOption } from './types';
import { FaUser, FaCoins, FaCalendarAlt } from 'react-icons/fa';

const FinancialPatronageStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { citizens, isLoading, currentUserUsername } = props;

  // States for Target Citizen
  const [targetCitizenUsername, setTargetCitizenUsername] = useState<string | null>(null);
  const [citizenSearch, setCitizenSearch] = useState('');
  const [isCitizenDropdownOpen, setIsCitizenDropdownOpen] = useState(false);
  const citizenInputRef = useRef<HTMLInputElement>(null);

  // Patronage level and duration
  const [patronageLevel, setPatronageLevel] = useState<'Modest' | 'Standard' | 'Generous'>('Standard');
  const [durationDays, setDurationDays] = useState<number>(90);

  // Daily amounts based on patronage level
  const dailyAmounts = {
    'Modest': 5,
    'Standard': 10,
    'Generous': 20
  };

  const dailyAmount = dailyAmounts[patronageLevel];
  const totalCost = dailyAmount * durationDays;

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetCitizenUsername) {
        console.error("FinancialPatronageStratagemPanel: Target Citizen is required.");
        return null;
      }
      const details: Record<string, any> = {
        targetCitizenUsername,
        patronageLevel,
        durationDays,
      };
      return details;
    },
  }));

  // Filter citizens (exclude current user)
  const filteredCitizens = citizens.filter(c =>
    c.username !== currentUserUsername && (
      c.username.toLowerCase().includes(citizenSearch.toLowerCase()) ||
      `${c.firstName} ${c.lastName}`.toLowerCase().includes(citizenSearch.toLowerCase())
    )
  );

  return (
    <div>
      {/* Target Citizen */}
      <div className="mb-4">
        <label htmlFor="financial_patronage_citizen" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUser className="mr-2" /> Target Citizen <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="relative">
          <input
            id="financial_patronage_citizen"
            type="text"
            ref={citizenInputRef}
            value={citizenSearch}
            onChange={(e) => setCitizenSearch(e.target.value)}
            onFocus={() => setIsCitizenDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsCitizenDropdownOpen(false), 200)}
            placeholder="Search for citizen to support..."
            className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
            disabled={isLoading}
          />
          {targetCitizenUsername && (
            <div className="mt-1 text-sm text-amber-700">
              Selected: <span className="font-semibold">{targetCitizenUsername}</span>
            </div>
          )}
          {isCitizenDropdownOpen && filteredCitizens.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-amber-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
              {filteredCitizens.map((citizen) => (
                <div
                  key={citizen.username}
                  onMouseDown={() => {
                    setTargetCitizenUsername(citizen.username);
                    setCitizenSearch(`${citizen.firstName} ${citizen.lastName} (${citizen.username})`);
                    setIsCitizenDropdownOpen(false);
                  }}
                  className="p-2 hover:bg-amber-100 cursor-pointer border-b border-amber-200"
                >
                  <div className="font-medium text-amber-900">
                    {citizen.firstName} {citizen.lastName}
                  </div>
                  <div className="text-sm text-amber-600">
                    @{citizen.username} • {citizen.socialClass}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Patronage Level */}
      <div className="mb-4">
        <label htmlFor="financial_patronage_level" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaCoins className="mr-2" /> Patronage Level
        </label>
        <select
          id="financial_patronage_level"
          value={patronageLevel}
          onChange={(e) => setPatronageLevel(e.target.value as 'Modest' | 'Standard' | 'Generous')}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="Modest">Modest (5 ducats/day)</option>
          <option value="Standard">Standard (10 ducats/day)</option>
          <option value="Generous">Generous (20 ducats/day)</option>
        </select>
        <p className="text-sm text-amber-600 mt-1">
          Daily support: {dailyAmount} ducats
        </p>
      </div>

      {/* Duration */}
      <div className="mb-4">
        <label htmlFor="financial_patronage_duration" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaCalendarAlt className="mr-2" /> Duration (Days)
        </label>
        <input
          id="financial_patronage_duration"
          type="number"
          min="30"
          max="180"
          value={durationDays}
          onChange={(e) => setDurationDays(Math.max(30, Math.min(180, parseInt(e.target.value) || 30)))}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        />
        <p className="text-sm text-amber-600 mt-1">
          Total duration: {durationDays} days
        </p>
      </div>

      {/* Summary */}
      <div className="mt-4 p-3 bg-amber-100 border border-amber-300 rounded-md">
        <h4 className="font-semibold text-amber-800 mb-2">Patronage Summary</h4>
        <div className="text-sm text-amber-700 space-y-1">
          <p>• Beneficiary: <span className="font-medium">{targetCitizenUsername || 'Not selected'}</span></p>
          <p>• Daily Support: <span className="font-medium">{dailyAmount} ducats</span></p>
          <p>• Duration: <span className="font-medium">{durationDays} days</span></p>
          <p>• Total Cost: <span className="font-medium text-amber-800">{totalCost} ducats</span></p>
          <p className="italic text-amber-600 mt-2">
            This will provide daily financial support and significantly improve your relationship with the beneficiary.
          </p>
        </div>
      </div>

      {/* Warning if high cost */}
      {totalCost > 1000 && (
        <div className="mt-3 p-2 bg-yellow-100 border border-yellow-400 rounded-md">
          <p className="text-sm text-yellow-800">
            ⚠️ High cost patronage: Ensure you have sufficient funds for the entire duration.
          </p>
        </div>
      )}
    </div>
  );
});

FinancialPatronageStratagemPanel.displayName = 'FinancialPatronageStratagemPanel';

export default FinancialPatronageStratagemPanel;
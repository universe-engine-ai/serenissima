import React, { useState, useImperativeHandle, forwardRef, useRef } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, CitizenOption } from './types';
import { FaUser, FaStar, FaCalendarAlt, FaCoins } from 'react-icons/fa';

const ReputationBoostStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { citizens, isLoading } = props;

  // States for Target Citizen
  const [targetCitizenUsername, setTargetCitizenUsername] = useState<string | null>(null);
  const [citizenSearch, setCitizenSearch] = useState('');
  const [isCitizenDropdownOpen, setIsCitizenDropdownOpen] = useState(false);
  const citizenInputRef = useRef<HTMLInputElement>(null);

  // Campaign settings
  const [campaignIntensity, setCampaignIntensity] = useState<'Modest' | 'Standard' | 'Intense'>('Standard');
  const [campaignDurationDays, setCampaignDurationDays] = useState<number>(30);

  // Budget calculations
  const defaultBudgets = {
    'Modest': 300,
    'Standard': 600,
    'Intense': 1200
  };
  const campaignBudget = defaultBudgets[campaignIntensity];
  const dailyBudget = Math.round(campaignBudget / campaignDurationDays);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetCitizenUsername) {
        console.error("ReputationBoostStratagemPanel: Target Citizen is required.");
        return null;
      }
      const details: Record<string, any> = {
        targetCitizenUsername,
        campaignIntensity,
        campaignDurationDays,
        campaignBudget,
      };
      return details;
    },
  }));

  // Filter citizens
  const filteredCitizens = citizens.filter(c =>
    c.username.toLowerCase().includes(citizenSearch.toLowerCase()) ||
    `${c.firstName} ${c.lastName}`.toLowerCase().includes(citizenSearch.toLowerCase())
  );

  return (
    <div>
      {/* Target Citizen */}
      <div className="mb-4">
        <label htmlFor="reputation_boost_citizen" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUser className="mr-2" /> Target Citizen <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="relative">
          <input
            id="reputation_boost_citizen"
            type="text"
            ref={citizenInputRef}
            value={citizenSearch}
            onChange={(e) => setCitizenSearch(e.target.value)}
            onFocus={() => setIsCitizenDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsCitizenDropdownOpen(false), 200)}
            placeholder="Search for citizen to promote..."
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

      {/* Campaign Intensity */}
      <div className="mb-4">
        <label htmlFor="reputation_boost_intensity" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaStar className="mr-2" /> Campaign Intensity
        </label>
        <select
          id="reputation_boost_intensity"
          value={campaignIntensity}
          onChange={(e) => setCampaignIntensity(e.target.value as 'Modest' | 'Standard' | 'Intense')}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="Modest">Modest (300 ducats budget)</option>
          <option value="Standard">Standard (600 ducats budget)</option>
          <option value="Intense">Intense (1200 ducats budget)</option>
        </select>
        <p className="text-sm text-amber-600 mt-1">
          Daily spending: ~{dailyBudget} ducats
        </p>
      </div>

      {/* Campaign Duration */}
      <div className="mb-4">
        <label htmlFor="reputation_boost_duration" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaCalendarAlt className="mr-2" /> Campaign Duration (Days)
        </label>
        <input
          id="reputation_boost_duration"
          type="number"
          min="30"
          max="60"
          value={campaignDurationDays}
          onChange={(e) => setCampaignDurationDays(Math.max(30, Math.min(60, parseInt(e.target.value) || 30)))}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        />
        <p className="text-sm text-amber-600 mt-1">
          Campaign duration: {campaignDurationDays} days
        </p>
      </div>

      {/* Campaign Events Preview */}
      <div className="mt-4 p-3 bg-purple-50 border border-purple-300 rounded-md">
        <h4 className="font-semibold text-purple-800 mb-2">Campaign Activities</h4>
        <div className="text-sm text-purple-700">
          {campaignIntensity === 'Modest' && (
            <ul className="space-y-1 list-disc list-inside">
              <li>Public compliments and endorsements</li>
              <li>Small donations in their name</li>
              <li>Local community support</li>
            </ul>
          )}
          {campaignIntensity === 'Standard' && (
            <ul className="space-y-1 list-disc list-inside">
              <li>Public speeches honoring achievements</li>
              <li>Charity events in their name</li>
              <li>Business endorsements</li>
              <li>Cultural sponsorships</li>
            </ul>
          )}
          {campaignIntensity === 'Intense' && (
            <ul className="space-y-1 list-disc list-inside">
              <li>Grand feasts celebrating their contributions</li>
              <li>Major public donations and monuments</li>
              <li>Political endorsements from patricians</li>
              <li>Theatrical productions in their honor</li>
            </ul>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="mt-4 p-3 bg-amber-100 border border-amber-300 rounded-md">
        <h4 className="font-semibold text-amber-800 mb-2">Campaign Summary</h4>
        <div className="text-sm text-amber-700 space-y-1">
          <p>• Beneficiary: <span className="font-medium">{targetCitizenUsername || 'Not selected'}</span></p>
          <p>• Intensity: <span className="font-medium">{campaignIntensity}</span></p>
          <p>• Duration: <span className="font-medium">{campaignDurationDays} days</span></p>
          <p>• Total Budget: <span className="font-medium text-amber-800">{campaignBudget} ducats</span></p>
          <p className="italic text-amber-600 mt-2">
            Daily events will improve {targetCitizenUsername ? `${targetCitizenUsername}'s` : 'their'} reputation throughout Venice.
          </p>
        </div>
      </div>

      {/* Benefits */}
      <div className="mt-3 p-2 bg-green-50 border border-green-300 rounded-md">
        <p className="text-sm text-green-700">
          ✨ This campaign will improve relationships, resolve reputation problems, and enhance public perception.
        </p>
      </div>
    </div>
  );
});

ReputationBoostStratagemPanel.displayName = 'ReputationBoostStratagemPanel';

export default ReputationBoostStratagemPanel;
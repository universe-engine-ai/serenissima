import React, { useState, useImperativeHandle, forwardRef, useRef } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, ResourceTypeOption } from './types';
import { FaBoxOpen, FaChartLine, FaClock } from 'react-icons/fa';

const MonopolyPricingStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { resourceTypes, isLoading } = props;

  // States for Target Resource Type
  const [targetResourceType, setTargetResourceType] = useState<string | null>(null);
  const [resourceTypeSearch, setResourceTypeSearch] = useState('');
  const [isResourceTypeDropdownOpen, setIsResourceTypeDropdownOpen] = useState(false);
  const resourceTypeInputRef = useRef<HTMLInputElement>(null);

  // Variant and duration
  const [selectedVariant, setSelectedVariant] = useState<'Mild' | 'Standard' | 'Aggressive'>('Standard');
  const [durationHours, setDurationHours] = useState<number>(168); // 7 days default

  // Price multipliers
  const priceMultipliers = {
    'Mild': 1.5,
    'Standard': 2.0,
    'Aggressive': 3.0
  };

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetResourceType) {
        console.error("MonopolyPricingStratagemPanel: Target Resource Type is required.");
        return null;
      }
      const details: Record<string, any> = {
        targetResourceType,
        variant: selectedVariant,
        durationHours,
      };
      return details;
    },
  }));

  // Filter resource types
  const filteredResourceTypes = resourceTypes.filter(rt =>
    rt.name.toLowerCase().includes(resourceTypeSearch.toLowerCase()) ||
    rt.id.toLowerCase().includes(resourceTypeSearch.toLowerCase())
  );

  return (
    <div>
      {/* Target Resource Type */}
      <div className="mb-4">
        <label htmlFor="monopoly_pricing_resource" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaBoxOpen className="mr-2" /> Target Resource Type <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="relative">
          <input
            id="monopoly_pricing_resource"
            type="text"
            ref={resourceTypeInputRef}
            value={resourceTypeSearch}
            onChange={(e) => setResourceTypeSearch(e.target.value)}
            onFocus={() => setIsResourceTypeDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsResourceTypeDropdownOpen(false), 200)}
            placeholder="Search for resource to monopolize..."
            className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
            disabled={isLoading}
          />
          {targetResourceType && (
            <div className="mt-1 text-sm text-amber-700">
              Selected: <span className="font-semibold">{resourceTypes.find(rt => rt.id === targetResourceType)?.name || targetResourceType}</span>
            </div>
          )}
          {isResourceTypeDropdownOpen && filteredResourceTypes.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-amber-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
              {filteredResourceTypes.map((rt) => (
                <div
                  key={rt.id}
                  onMouseDown={() => {
                    setTargetResourceType(rt.id);
                    setResourceTypeSearch(rt.name);
                    setIsResourceTypeDropdownOpen(false);
                  }}
                  className="p-2 hover:bg-amber-100 cursor-pointer border-b border-amber-200"
                >
                  <div className="font-medium text-amber-900">{rt.name}</div>
                  <div className="text-sm text-amber-600">{rt.category}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Pricing Strategy */}
      <div className="mb-4">
        <label htmlFor="monopoly_pricing_variant" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaChartLine className="mr-2" /> Pricing Strategy
        </label>
        <select
          id="monopoly_pricing_variant"
          value={selectedVariant}
          onChange={(e) => setSelectedVariant(e.target.value as 'Mild' | 'Standard' | 'Aggressive')}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="Mild">Mild (150% of market price)</option>
          <option value="Standard">Standard (200% of market price)</option>
          <option value="Aggressive">Aggressive (300% of market price)</option>
        </select>
        <p className="text-sm text-amber-600 mt-1">
          Your prices will be {(priceMultipliers[selectedVariant] * 100).toFixed(0)}% of the current market average
        </p>
      </div>

      {/* Duration */}
      <div className="mb-4">
        <label htmlFor="monopoly_pricing_duration" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaClock className="mr-2" /> Duration (Hours)
        </label>
        <input
          id="monopoly_pricing_duration"
          type="number"
          min="24"
          max="720"
          step="24"
          value={durationHours}
          onChange={(e) => setDurationHours(Math.max(24, Math.min(720, parseInt(e.target.value) || 24)))}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        />
        <p className="text-sm text-amber-600 mt-1">
          Price manipulation duration: {Math.floor(durationHours / 24)} days {durationHours % 24} hours
        </p>
      </div>

      {/* Requirements Warning */}
      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-300 rounded-md">
        <h4 className="font-semibold text-yellow-800 mb-2">⚠️ Requirements</h4>
        <ul className="text-sm text-yellow-700 space-y-1 list-disc list-inside">
          <li>You must have active public_sell contracts for this resource</li>
          <li>At least 20% market share is recommended for effectiveness</li>
          <li>Sufficient stock to meet demand at higher prices</li>
        </ul>
      </div>

      {/* Summary */}
      <div className="mt-4 p-3 bg-amber-100 border border-amber-300 rounded-md">
        <h4 className="font-semibold text-amber-800 mb-2">Monopoly Summary</h4>
        <div className="text-sm text-amber-700 space-y-1">
          <p>• Resource: <span className="font-medium">{resourceTypes.find(rt => rt.id === targetResourceType)?.name || 'Not selected'}</span></p>
          <p>• Strategy: <span className="font-medium">{selectedVariant} ({(priceMultipliers[selectedVariant] * 100).toFixed(0)}% pricing)</span></p>
          <p>• Duration: <span className="font-medium">{Math.floor(durationHours / 24)} days</span></p>
        </div>
      </div>

      {/* Consequences Warning */}
      {selectedVariant === 'Aggressive' && (
        <div className="mt-3 p-2 bg-red-50 border border-red-300 rounded-md">
          <p className="text-sm text-red-700">
            ⚠️ Aggressive pricing will severely damage relationships with buyers and may trigger political intervention!
          </p>
        </div>
      )}
    </div>
  );
});

MonopolyPricingStratagemPanel.displayName = 'MonopolyPricingStratagemPanel';

export default MonopolyPricingStratagemPanel;
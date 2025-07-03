import React, { useState, useImperativeHandle, forwardRef } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef } from './types';
import { FaShieldAlt, FaMapMarkedAlt } from 'react-icons/fa';

const NeighborhoodWatchStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { isLoading } = props;

  // Valid districts in La Serenissima
  const DISTRICTS = [
    'San Marco',
    'San Polo',
    'Dorsoduro',
    'Santa Croce',
    'Cannaregio',
    'Castello'
  ];

  // State for selected district
  const [districtName, setDistrictName] = useState<string>('');

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!districtName) {
        console.error("NeighborhoodWatchStratagemPanel: District is required.");
        return null;
      }
      const details: Record<string, any> = {
        districtName,
      };
      return details;
    },
  }));

  return (
    <div>
      {/* District Selection */}
      <div className="mb-4">
        <label htmlFor="neighborhood_watch_district" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaMapMarkedAlt className="mr-2" /> District <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          id="neighborhood_watch_district"
          value={districtName}
          onChange={(e) => setDistrictName(e.target.value)}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="">Select a district...</option>
          {DISTRICTS.map((district) => (
            <option key={district} value={district}>
              {district}
            </option>
          ))}
        </select>
        <p className="text-sm text-amber-600 mt-1">
          Choose the district where you want to establish a neighborhood watch
        </p>
      </div>

      {/* Information Panel */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-300 rounded-md">
        <h4 className="font-semibold text-blue-800 mb-2 flex items-center">
          <FaShieldAlt className="mr-2" /> About Neighborhood Watch
        </h4>
        <div className="text-sm text-blue-700 space-y-2">
          <p>• Duration: <span className="font-medium">45 days</span></p>
          <p>• Effect: <span className="font-medium">Reduces crime by 70% in the district</span></p>
          <p>• Community: <span className="font-medium">Improves relationships between district residents</span></p>
          <p>• Requirement: <span className="font-medium">Works best if you have property or residence in the district</span></p>
        </div>
      </div>

      {/* Summary */}
      {districtName && (
        <div className="mt-4 p-3 bg-amber-100 border border-amber-300 rounded-md">
          <h4 className="font-semibold text-amber-800 mb-2">Watch Summary</h4>
          <div className="text-sm text-amber-700 space-y-1">
            <p>• District: <span className="font-medium">{districtName}</span></p>
            <p>• Duration: <span className="font-medium">45 days</span></p>
            <p>• Expected Impact: <span className="font-medium">Significant crime reduction</span></p>
            <p className="italic text-amber-600 mt-2">
              Citizens in {districtName} will participate in organized vigilance to protect the community.
            </p>
          </div>
        </div>
      )}

      {/* Benefits */}
      <div className="mt-4 p-3 bg-green-50 border border-green-300 rounded-md">
        <h4 className="font-semibold text-green-800 mb-2">Expected Benefits</h4>
        <ul className="text-sm text-green-700 space-y-1 list-disc list-inside">
          <li>Prevention of theft, sabotage, and vandalism</li>
          <li>Stronger community bonds between residents</li>
          <li>Increased safety for businesses in the district</li>
          <li>Positive reputation as a community leader</li>
        </ul>
      </div>
    </div>
  );
});

NeighborhoodWatchStratagemPanel.displayName = 'NeighborhoodWatchStratagemPanel';

export default NeighborhoodWatchStratagemPanel;
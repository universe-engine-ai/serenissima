import React, { useState, useImperativeHandle, forwardRef } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, CitizenOption, ResourceTypeOption, BuildingOption } from './types';
import { FaUserShield, FaBuilding, FaBoxOpen } from 'react-icons/fa';

const CoordinatePricingStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, citizens, buildings, resourceTypes, isLoading, currentUserUsername } = props;

  const [targetResourceType, setTargetResourceType] = useState<string | null>(null);
  const [targetCitizen, setTargetCitizen] = useState<string | null>(null);
  const [targetBuilding, setTargetBuilding] = useState<string | null>(null);
  
  // Ce stratagème n'a pas de variantes affectant le coût de base de l'influence via le panneau.
  const calculatedInfluenceCost = stratagemData.influenceCostBase;

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetResourceType) {
        console.error("CoordinatePricingStratagemPanel: Target Resource Type is required.");
        return null; 
      }
      const details: Record<string, any> = {
        targetResourceType: targetResourceType,
      };
      if (targetCitizen) {
        details.targetCitizen = targetCitizen;
      }
      if (targetBuilding) {
        details.targetBuilding = targetBuilding;
      }
      // durationHours, name, description, notes sont gérés avec des valeurs par défaut par le créateur pour l'instant.
      return details;
    },
    getCalculatedInfluenceCost: () => {
      return calculatedInfluenceCost;
    }
  }));

  return (
    <div>
      {/* Target Resource Type */}
      <div className="mb-4">
        <label htmlFor="coordinate_targetResourceType" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaBoxOpen className="mr-2" /> Target Resource Type <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          id="coordinate_targetResourceType"
          value={targetResourceType || ''}
          onChange={(e) => setTargetResourceType(e.target.value || null)}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="">-- Select Resource Type --</option>
          {resourceTypes.map(rt => (
            <option key={`coordinate-resource-opt-${rt.id}`} value={rt.id}>
              {rt.name} (Category: {rt.category || 'N/A'})
            </option>
          ))}
        </select>
      </div>

      {/* Target Citizen (Optional) */}
      <div className="mb-4">
        <label htmlFor="coordinate_targetCitizen" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUserShield className="mr-2" /> Target Reference Citizen (Optional)
        </label>
        <p className="text-xs text-amber-600 mb-1">If neither citizen nor building is selected, prices will coordinate with the general market average.</p>
        <select
          id="coordinate_targetCitizen"
          value={targetCitizen || ''}
          onChange={(e) => setTargetCitizen(e.target.value || null)}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="">-- Select Citizen --</option>
          {citizens.filter(c => c.username !== currentUserUsername).map((c, index) => {
            const namePart = [c.firstName, c.lastName].filter(Boolean).join(' ');
            const citizenMainIdentifier = namePart ? `${namePart} (${c.username || 'ID Manquant'})` : (c.username || '');
            const socialClassDisplay = c.socialClass || 'N/A';
            const finalDisplayString = citizenMainIdentifier ? `${citizenMainIdentifier} - ${socialClassDisplay}` : `[Citoyen Inconnu] - ${socialClassDisplay}`;
            return (
              <option key={`coordinate-citizen-opt-${c.username || index}`} value={c.username || ''}>
                {finalDisplayString}
              </option>
            );
          })}
        </select>
      </div>
      
      {/* Target Building (Optional) */}
      <div className="mb-4">
        <label htmlFor="coordinate_targetBuilding" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaBuilding className="mr-2" /> Target Reference Building (Optional)
        </label>
        <select
          id="coordinate_targetBuilding"
          value={targetBuilding || ''}
          onChange={(e) => setTargetBuilding(e.target.value || null)}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="">-- Select Building --</option>
          {buildings
            // On peut vouloir coordonner avec n'importe quel bâtiment, même ceux de l'utilisateur actuel.
            // .filter(b => !currentUserUsername || (b.owner !== currentUserUsername)) 
            .filter(b => !targetCitizen || (b.owner === targetCitizen)) // Filtrer par citoyen cible si sélectionné
            .map(b => (
              <option key={`coordinate-building-opt-${b.buildingId}`} value={b.buildingId}>
                {b.name || b.buildingId} (Type: {b.type}, Owner: {b.owner || 'N/A'})
              </option>
          ))}
        </select>
      </div>
    </div>
  );
});

CoordinatePricingStratagemPanel.displayName = 'CoordinatePricingStratagemPanel';
export default CoordinatePricingStratagemPanel;

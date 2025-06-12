import React, { useState, useImperativeHandle, forwardRef, useEffect } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, StratagemData, CitizenOption, ResourceTypeOption, BuildingOption } from './types';
import { FaUserShield, FaBuilding, FaBoxOpen } from 'react-icons/fa';

const UndercutStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, citizens, buildings, resourceTypes, isLoading, currentUserUsername } = props;

  const [selectedVariant, setSelectedVariant] = useState<'Mild' | 'Standard' | 'Aggressive'>('Standard');
  const [targetCitizen, setTargetCitizen] = useState<string | null>(null);
  const [targetBuilding, setTargetBuilding] = useState<string | null>(null);
  const [targetResourceType, setTargetResourceType] = useState<string | null>(null);
  
  const stratagemHasVariants = stratagemData.hasVariants !== false;

  const calculatedInfluenceCost = stratagemHasVariants
    ? stratagemData.influenceCostBase * (selectedVariant === 'Mild' ? 1 : selectedVariant === 'Standard' ? 2 : 3)
    : stratagemData.influenceCostBase;

  // Exposer les méthodes via ref
  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetResourceType) {
        // Le panneau principal affichera une erreur plus générique si nécessaire,
        // mais le bouton Exécuter sera désactivé par la logique du panneau principal.
        // On pourrait aussi lancer une alerte ici ou retourner un message d'erreur.
        console.error("UndercutStratagemPanel: Target Resource Type is required.");
        return null; 
      }
      const details: Record<string, any> = {
        targetResourceType: targetResourceType,
      };
      if (stratagemHasVariants) {
        details.variant = selectedVariant;
      }
      if (targetCitizen) {
        details.targetCitizen = targetCitizen;
      }
      if (targetBuilding) {
        details.targetBuilding = targetBuilding;
      }
      // TODO: Ajouter durationHours, name, description si ces champs sont ajoutés au panneau
      return details;
    },
    getCalculatedInfluenceCost: () => {
      return calculatedInfluenceCost;
    }
  }));

  // Informer le parent du changement de coût d'influence (si la prop est fournie)
  // Ceci est géré par getCalculatedInfluenceCost, le parent peut l'appeler.

  return (
    <div>
      {/* Variant Selection */}
      {stratagemHasVariants && (
        <div className="mb-4">
          <label htmlFor="undercut_variant" className="block text-sm font-medium text-amber-800 mb-1">
            Aggressiveness Variant
          </label>
          <select
            id="undercut_variant"
            value={selectedVariant}
            onChange={(e) => setSelectedVariant(e.target.value as 'Mild' | 'Standard' | 'Aggressive')}
            className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
            disabled={isLoading}
          >
            <option value="Mild">Mild (10% Undercut, Cost x1)</option>
            <option value="Standard">Standard (15% Undercut, Cost x2)</option>
            <option value="Aggressive">Aggressive (20% Undercut, Cost x3)</option>
          </select>
        </div>
      )}

      {/* Target Resource Type */}
      <div className="mb-4">
        <label htmlFor="undercut_targetResourceType" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaBoxOpen className="mr-2" /> Target Resource Type <span className="text-red-500 ml-1">*</span>
        </label>
        <select
          id="undercut_targetResourceType"
          value={targetResourceType || ''}
          onChange={(e) => setTargetResourceType(e.target.value || null)}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="">-- Select Resource Type --</option>
          {resourceTypes.map(rt => (
            <option key={`undercut-resource-opt-${rt.id}`} value={rt.id}>
              {rt.name} (Category: {rt.category || 'N/A'})
            </option>
          ))}
        </select>
      </div>

      {/* Target Citizen */}
      <div className="mb-4">
        <label htmlFor="undercut_targetCitizen" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUserShield className="mr-2" /> Target Competitor Citizen (Optional)
        </label>
        <select
          id="undercut_targetCitizen"
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
              <option key={`undercut-citizen-opt-${c.username || index}`} value={c.username || ''}>
                {finalDisplayString}
              </option>
            );
          })}
        </select>
      </div>
      
      {/* Target Building */}
      <div className="mb-4">
        <label htmlFor="undercut_targetBuilding" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaBuilding className="mr-2" /> Target Competitor Building (Optional)
        </label>
        <select
          id="undercut_targetBuilding"
          value={targetBuilding || ''}
          onChange={(e) => setTargetBuilding(e.target.value || null)}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        >
          <option value="">-- Select Building --</option>
          {buildings
            .filter(b => !currentUserUsername || (b.owner !== currentUserUsername)) // Exclure les bâtiments possédés par l'utilisateur actuel
            .filter(b => !targetCitizen || (b.owner === targetCitizen)) // Filtrer par citoyen cible si sélectionné
            .map(b => (
              <option key={`undercut-building-opt-${b.buildingId}`} value={b.buildingId}>
                {b.name || b.buildingId} (Type: {b.type}, Owner: {b.owner || 'N/A'})
              </option>
          ))}
        </select>
      </div>
    </div>
  );
});

UndercutStratagemPanel.displayName = 'UndercutStratagemPanel';
export default UndercutStratagemPanel;

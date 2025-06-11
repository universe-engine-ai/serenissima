import React, { useState, useEffect, useCallback } from 'react';
import { FaTimes, FaUserShield, FaBuilding, FaBoxOpen, FaBalanceScale } from 'react-icons/fa';
import { useWalletContext } from '@/components/UI/WalletProvider'; // Pour obtenir le currentUserUsername

interface StratagemData {
  id: string; // id du subitem, ex: 'undercut'
  type: string; // type de stratagème pour l'API, ex: 'undercut'
  title: string;
  description: string;
  influenceCostBase: number; // Coût de base, peut être multiplié par la variante
  hasVariants?: boolean; // Optional: defaults to true if not specified
  // D'autres champs spécifiques au stratagème peuvent être ajoutés ici
}

interface StratagemExecutionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stratagemData: StratagemData;
}

interface CitizenOption {
  username: string;
  firstName?: string;
  lastName?: string;
  socialClass?: string;
}

interface BuildingOption {
  buildingId: string;
  name?: string;
  type?: string;
  owner?: string;
}

interface ResourceTypeOption {
  id: string;
  name: string;
  category?: string;
}

const StratagemExecutionPanel: React.FC<StratagemExecutionPanelProps> = ({
  isOpen,
  onClose,
  stratagemData,
}) => {
  const { citizenProfile } = useWalletContext();
  const currentUserUsername = citizenProfile?.username;

  const [selectedVariant, setSelectedVariant] = useState<'Mild' | 'Standard' | 'Aggressive'>('Standard');
  const [targetCitizen, setTargetCitizen] = useState<string | null>(null);
  const [targetBuilding, setTargetBuilding] = useState<string | null>(null);
  const [targetResourceType, setTargetResourceType] = useState<string | null>(null);
  // const [targetStorageBuilding, setTargetStorageBuilding] = useState<string | null>(null); // Removed for hoard_resource

  const [citizens, setCitizens] = useState<CitizenOption[]>([]);
  const [buildings, setBuildings] = useState<BuildingOption[]>([]);
  const [resourceTypes, setResourceTypes] = useState<ResourceTypeOption[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [executionResult, setExecutionResult] = useState<string | null>(null);
  const [errorResult, setErrorResult] = useState<string | null>(null);

  const stratagemHasVariants = stratagemData.hasVariants !== false; // Default to true if undefined
  const influenceCost = stratagemHasVariants 
    ? stratagemData.influenceCostBase * (selectedVariant === 'Mild' ? 1 : selectedVariant === 'Standard' ? 2 : 3)
    : stratagemData.influenceCostBase;

  const fetchDropdownData = useCallback(async () => {
    if (!isOpen) return;
    setIsLoading(true);
    try {
      // Fetch Citizens
      const citizensRes = await fetch('/api/citizens');
      if (citizensRes.ok) {
        const citizensData = await citizensRes.json();
        console.log('[StratagemExecutionPanel] Fetched citizensData:', citizensData); // Log pour inspecter
        // L'API /api/citizens retourne un objet {success: true, citizens: Array(...)}
        // Nous devons les mapper vers CitizenOption
        if (citizensData && citizensData.success && Array.isArray(citizensData.citizens)) {
          const formattedCitizens = citizensData.citizens.map((c: any) => ({
            username: c.username, 
            firstName: c.firstName,
            lastName: c.lastName,
            socialClass: c.socialClass 
          })).filter((c: CitizenOption) => c.username !== currentUserUsername); // Exclure l'utilisateur actuel
          setCitizens(formattedCitizens);
        } else {
          console.error('Failed to fetch citizens: citizensData.citizens is not an array or request failed. Received:', citizensData);
          setErrorResult(prev => prev ? `${prev}\nFailed to load citizen list (invalid format).` : 'Failed to load citizen list (invalid format).');
          setCitizens([]);
        }
      } else {
        console.error('Failed to fetch citizens, status:', citizensRes.status);
        setErrorResult(prev => prev ? `${prev}\nFailed to load citizen list (status: ${citizensRes.status}).` : `Failed to load citizen list (status: ${citizensRes.status}).`);
        setCitizens([]);
      }

      // Fetch Buildings
      const buildingsRes = await fetch('/api/buildings'); // Ajustez l'endpoint si nécessaire
      if (buildingsRes.ok) {
        const buildingsData = await buildingsRes.json();
        // L'API /api/buildings retourne { buildings: [...] }
        // Mapper vers BuildingOption
        const formattedBuildings = buildingsData.buildings.map((b: any) => ({
            buildingId: b.id, // ou b.buildingId selon la structure
            name: b.name,
            type: b.type,
            owner: b.owner
        }));
        setBuildings(formattedBuildings);
      } else {
        console.error('Failed to fetch buildings');
        setBuildings([]);
      }

      // Fetch Resource Types
      const resourceTypesRes = await fetch('/api/resource-types');
      if (resourceTypesRes.ok) {
        const resourceTypesData = await resourceTypesRes.json();
        // L'API /api/resource-types retourne { success: true, resourceTypes: [...] }
        // Mapper vers ResourceTypeOption
        const formattedResourceTypes = resourceTypesData.resourceTypes.map((rt: any) => ({
            id: rt.id,
            name: rt.name,
            category: rt.category
        }));
        setResourceTypes(formattedResourceTypes);
      } else {
        console.error('Failed to fetch resource types');
        setResourceTypes([]);
      }
    } catch (error) {
      console.error('Error fetching dropdown data:', error);
      setErrorResult('Failed to load selection data.');
    }
    setIsLoading(false);
  }, [isOpen, currentUserUsername]);

  useEffect(() => {
    fetchDropdownData();
  }, [fetchDropdownData]);

  const handleExecute = async () => {
    if (!currentUserUsername) {
      setErrorResult("Current user not identified. Cannot execute stratagem.");
      return;
    }
    if (stratagemData.type === 'hoard_resource') {
      if (!targetResourceType) {
        setErrorResult("For Hoard Resource: Target Resource Type must be selected.");
        return;
      }
    } else if (stratagemData.type === 'reputation_assault') {
      if (!targetCitizen) { 
        setErrorResult("For Reputation Assault: Target Citizen must be selected.");
        return;
      }
    } else if (stratagemData.type === 'maritime_blockade') {
      if (!targetCitizen && !targetBuilding) {
        setErrorResult("For Maritime Blockade: Target Competitor Citizen or Building must be selected.");
        return;
      }
    } else if (['undercut', 'coordinate_pricing'].includes(stratagemData.type)) {
      if (!targetResourceType) { 
        setErrorResult(`For ${stratagemData.title}: Target Resource Type must be selected.`);
        return;
      }
    } else if (stratagemData.type === 'information_network') {
        // Assuming information_network requires either targetCitizens or targetSectors
        // This panel currently only supports single targetCitizen, targetBuilding, targetResourceType.
        // For information_network, if it uses these fields, validation would be similar.
        // If it needs different fields (like lists), the panel needs more complex state.
        // For now, let's assume it uses targetCitizen or targetBuilding as a proxy for a single target.
        // Or, if it's "Coming Soon" and disabled, this validation might not be hit.
        // If it were active and used targetCitizen/targetBuilding:
        // if (!targetCitizen && !targetBuilding) { // Simplified for current panel structure
        //   setErrorResult("For Information Network: A target (Citizen or Building representing a sector) must be selected.");
        //   return;
        // }
    } else { 
      // Default validation for other stratagems if any are added without specific checks here
      // This might need adjustment if a stratagem has no direct targets from this panel.
      if (stratagemData.type !== 'emergency_liquidation' && // This one has no direct targets from UI
          !targetCitizen && !targetBuilding && !targetResourceType) {
        setErrorResult("At least one target (Citizen, Building, or Resource Type) must be selected for this stratagem.");
        return;
      }
    }

    setIsLoading(true);
    setExecutionResult(null);
    setErrorResult(null);

    const stratagemDetails: any = {};
    if (stratagemHasVariants) {
      stratagemDetails.variant = selectedVariant;
    }
    // Common parameters
    if (targetCitizen) stratagemDetails.targetCitizen = targetCitizen;
    if (targetBuilding) stratagemDetails.targetBuilding = targetBuilding;
    if (targetResourceType) stratagemDetails.targetResourceType = targetResourceType;
    
    // targetStorageBuildingId is no longer sent from client for hoard_resource
    // TODO: Ajouter d'autres paramètres comme durationHours, name, description si nécessaire

    try {
      const response = await fetch('/api/stratagems/try-create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          citizenUsername: currentUserUsername,
          stratagemType: stratagemData.type,
          stratagemDetails: stratagemDetails,
        }),
      });

      const result = await response.json();

      if (response.ok) { // HTTP request to Next.js API was okay
        // result is StratagemEngineResponse from Python
        if (result.success && (!result.processing_status || ["success", "not_applicable", "pending_processing"].includes(result.processing_status))) {
          // Python engine reported overall success AND processing was fine or not yet applicable/pending
          let successMsg = `Stratagem "${stratagemData.title}" initiated (ID: ${result.stratagem_id_custom || result.stratagem_id_airtable}).`;
          if (result.processing_status) successMsg += ` Processing: ${result.processing_status}.`;
          if (result.processing_notes) successMsg += ` Notes: ${result.processing_notes}.`;
          setExecutionResult(successMsg);
          // Optionnel: fermer le panneau après succès
          // setTimeout(onClose, 3000); 
        } else {
          // Python engine reported an issue (either result.success is false, or processing_status is 'failed'/'error')
          let errorMsg = `Stratagem "${stratagemData.title}": `;
          if (!result.success && result.message) { // Overall failure from engine
            errorMsg += result.message;
          } else if (result.success && (result.processing_status === "failed" || result.processing_status === "error")) { // Creation succeeded, but processing failed
            errorMsg += `Created, but processing ${result.processing_status}.`;
            if (result.message) errorMsg += ` Message: ${result.message}.`;
          } else if (result.message) { // Fallback for other error messages from engine if result.success is false but no specific processing status issue
             errorMsg += result.message || "Execution failed.";
          } else {
             errorMsg += "Execution failed with unknown engine error.";
          }
          
          if (result.processing_notes) { // Display processing_notes if available
            errorMsg += ` Details: ${result.processing_notes}`;
          } else if (result.error_details) { // Fallback for other technical details
             const detailsString = typeof result.error_details === 'string' ? result.error_details : JSON.stringify(result.error_details);
             errorMsg += ` Debug: ${detailsString}`;
          }
          setErrorResult(errorMsg);
        }
      } else { // HTTP request to Next.js API failed
        // result is the error response from the Next.js API route itself
        let httpErrorMsg = `Error (HTTP ${response.status}): `;
        if (result && result.error) { // 'error' field from Next.js API's JSON response
          httpErrorMsg += result.error;
          // Check if the Next.js error response includes 'details' from the Python engine
          if (result.details && result.details.processing_notes) {
            httpErrorMsg += ` Engine Notes: ${result.details.processing_notes}`;
          } else if (result.details && result.details.message) {
            httpErrorMsg += ` Engine Message: ${result.details.message}`;
          }
        } else if (result && result.message) { // Fallback if result has a message (e.g. from Python engine if Next.js just passed it through on error)
            httpErrorMsg += result.message;
        } else {
          httpErrorMsg += "Unknown server error.";
        }
        setErrorResult(httpErrorMsg);
      }
    } catch (error: any) {
      // Catch network errors or issues with fetching/parsing JSON itself
      setErrorResult(`Error executing stratagem: ${error.message || 'Network error or invalid response'}`);
    }
    setIsLoading(false);
  };
  
  const isExecuteDisabled = (() => {
    if (isLoading) return true;
    // Updated list of "Coming Soon" or disabled types
    if (['supplier_lockout', 'political_campaign', 'information_network', 'maritime_blockade', 'cultural_patronage', 'theater_conspiracy', 'printing_propaganda', 'cargo_mishap', 'marketplace_gossip', 'employee_poaching', 'joint_venture'].includes(stratagemData.type)) {
      return true; 
    }

    if (stratagemData.type === 'hoard_resource') {
      return !targetResourceType;
    }
    if (stratagemData.type === 'reputation_assault') {
      return !targetCitizen;
    }
    if (stratagemData.type === 'maritime_blockade') {
      return !targetCitizen && !targetBuilding; // Requires at least one target
    }
    if (['undercut', 'coordinate_pricing'].includes(stratagemData.type)) {
      return !targetResourceType; // ResourceType is mandatory for these
    }
    if (stratagemData.type === 'emergency_liquidation') {
      return false; // No direct targets from UI, always executable if not loading/coming soon
    }
    // Default for other potential types: require at least one target if not specifically handled
    // This might need adjustment based on future stratagems.
    return (!targetCitizen && !targetBuilding && !targetResourceType); 
  })();

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-amber-50/95 text-amber-900 p-6 rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col border-2 border-amber-400">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-3xl font-serif text-amber-700">{stratagemData.title}</h2>
          <button onClick={onClose} className="text-amber-600 hover:text-amber-800">
            <FaTimes size={24} />
          </button>
        </div>

        <div className="overflow-y-auto pr-2 flex-grow">
          <p className="text-sm italic text-amber-800 mb-1">{stratagemData.description}</p>
          <p className="text-lg font-semibold text-amber-700 mb-6">
            Influence Cost: {influenceCost} 🎭
          </p>

          {/* Variant Selection - Conditionally render based on stratagemData.hasVariants */}
          {stratagemHasVariants && (
            <div className="mb-4">
              <label htmlFor="variant" className="block text-sm font-medium text-amber-800 mb-1">
                Aggressiveness Variant {/* TODO: Make this label dynamic if variants mean different things. e.g. "Duration" or "Scale" */}
              </label>
              <select
                id="variant"
                value={selectedVariant}
                onChange={(e) => setSelectedVariant(e.target.value as 'Mild' | 'Standard' | 'Aggressive')}
                className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
              >
                <option value="Mild">Mild (10% Undercut, Cost x1)</option>
                <option value="Standard">Standard (15% Undercut, Cost x2)</option>
                <option value="Aggressive">Aggressive (20% Undercut, Cost x3)</option>
              </select>
            </div>
          )}

          {/* Target Citizen - Hide if hoard_resource or reputation_assault (as it's primary target) */}
          {/* Target Citizen - Conditional rendering based on stratagem type */}
          {/* Hide for hoard_resource. For reputation_assault, it's the primary target. For others, it's optional. */}
          {/* For maritime_blockade, targetCitizen (competitor) is an option. */}
          {stratagemData.type !== 'hoard_resource' && (
            <div className="mb-4">
              <label htmlFor="targetCitizen" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
                <FaUserShield className="mr-2" /> 
                {stratagemData.type === 'reputation_assault' ? 'Target Citizen' : 
                 stratagemData.type === 'maritime_blockade' ? 'Target Competitor Citizen (Optional)' :
                 'Target Citizen (Optional)'
                }
                {stratagemData.type === 'reputation_assault' && <span className="text-red-500 ml-1">*</span>}
              </label>
              <select
                id="targetCitizen"
                value={targetCitizen || ''}
                onChange={(e) => setTargetCitizen(e.target.value || null)}
                className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
                disabled={isLoading}
              >
                <option value="">-- Select Citizen --</option>
                {citizens.map((c, index) => {
                  const namePart = [c.firstName, c.lastName].filter(Boolean).join(' ');
                  const citizenMainIdentifier = namePart 
                    ? `${namePart} (${c.username || 'ID Manquant'})` 
                    : (c.username || ''); 
                  
                  const socialClassDisplay = c.socialClass || 'N/A';
                  let finalDisplayString;

                  if (!citizenMainIdentifier) {
                    finalDisplayString = socialClassDisplay === 'N/A' 
                      ? '[Citoyen Inconnu]' 
                      : `[Citoyen Inconnu] - ${socialClassDisplay}`;
                  } else {
                    finalDisplayString = `${citizenMainIdentifier} - ${socialClassDisplay}`;
                  }
                  
                  return (
                    <option key={`citizen-opt-${c.username || index}`} value={c.username || ''}>
                      {finalDisplayString}
                    </option>
                  );
                })}
              </select>
            </div>
          )}

          {/* Target Building - Conditional rendering */}
          {/* Hide for hoard_resource, reputation_assault. Optional for others. */}
          {/* For maritime_blockade, targetBuilding (competitor's waterfront asset) is an option. */}
          {stratagemData.type !== 'hoard_resource' && stratagemData.type !== 'reputation_assault' && (
            <div className="mb-4">
              <label htmlFor="targetBuilding" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
                <FaBuilding className="mr-2" /> 
                {stratagemData.type === 'maritime_blockade' ? "Target Competitor's Building (Optional)" : "Target Building (Optional)"}
              </label>
              <select
                id="targetBuilding"
                value={targetBuilding || ''}
                onChange={(e) => setTargetBuilding(e.target.value || null)}
                className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
                disabled={isLoading}
              >
                <option value="">-- Select Building --</option>
                {buildings
                  .filter(b => !targetCitizen || (b.owner === targetCitizen)) 
                  .map(b => (
                    <option key={`building-opt-${b.buildingId}`} value={b.buildingId}>
                      {b.name || b.buildingId} (Type: {b.type}, Owner: {b.owner || 'N/A'})
                    </option>
                ))}
              </select>
            </div>
          )}

          {/* Target Resource Type - Conditionally render based on stratagem type */}
          {/* Hide for reputation_assault, maritime_blockade (as it targets operations, not a specific resource type directly via UI) */}
          {stratagemData.type !== 'reputation_assault' && stratagemData.type !== 'maritime_blockade' && (
            <div className="mb-4">
              <label htmlFor="targetResourceType" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
                <FaBoxOpen className="mr-2" /> Target Resource Type 
                {['undercut', 'coordinate_pricing', 'hoard_resource'].includes(stratagemData.type) ? 
                  <span className="text-red-500 ml-1">*</span> : 
                  <span className="text-xs text-gray-500 ml-1">(Optional)</span>
                }
              </label>
              <select
                id="targetResourceType"
                value={targetResourceType || ''}
                onChange={(e) => setTargetResourceType(e.target.value || null)}
                className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
                disabled={isLoading}
              >
                <option value="">-- Select Resource Type --</option>
                {resourceTypes.map(rt => (
                  <option key={`resource-opt-${rt.id}`} value={rt.id}>
                    {rt.name} (Category: {rt.category || 'N/A'})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        
        {executionResult && <p className="text-green-600 mt-4 p-2 bg-green-100 border border-green-300 rounded">{executionResult}</p>}
        {errorResult && <p className="text-red-600 mt-4 p-2 bg-red-100 border border-red-300 rounded">{errorResult}</p>}

        <div className="mt-auto pt-4 border-t border-amber-300">
          <button
            onClick={handleExecute}
            disabled={isExecuteDisabled || isLoading}
            className={`w-full py-3 px-4 rounded-md text-white font-semibold transition-colors flex items-center justify-center
                        ${isExecuteDisabled || isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-amber-600 hover:bg-amber-700'}`}
          >
            <FaBalanceScale className="mr-2" />
            {isLoading ? 'Executing...' : 'Execute Stratagem'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default StratagemExecutionPanel;

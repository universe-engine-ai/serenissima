import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { FaTimes, FaBalanceScale } from 'react-icons/fa';
import { useWalletContext } from '@/components/UI/WalletProvider';
import { StratagemData, CitizenOption, BuildingOption, ResourceTypeOption, StratagemSpecificPanelRef } from './ExecutionPanels/types';
import UndercutStratagemPanel from './ExecutionPanels/UndercutStratagemPanel';
import CoordinatePricingStratagemPanel from './ExecutionPanels/CoordinatePricingStratagemPanel'; // Ajout de l'import
import CanalMuggingStratagemPanel from './ExecutionPanels/CanalMuggingStratagemPanel'; // Ajout de l'import
import BurglaryStratagemPanel from './ExecutionPanels/BurglaryStratagemPanel'; // Ajout de l'import
import ReputationAssaultStratagemPanel from './ExecutionPanels/ReputationAssaultStratagemPanel'; // Ajout de l'import
import MarketplaceGossipStratagemPanel from './ExecutionPanels/MarketplaceGossipStratagemPanel'; // Ajout de l'import
import DefaultStratagemPanel from './ExecutionPanels/DefaultStratagemPanel';
import SupplierLockoutStratagemPanel from './ExecutionPanels/SupplierLockoutStratagemPanel';
import FinancialPatronageStratagemPanel from './ExecutionPanels/FinancialPatronageStratagemPanel';
import NeighborhoodWatchStratagemPanel from './ExecutionPanels/NeighborhoodWatchStratagemPanel';
import MonopolyPricingStratagemPanel from './ExecutionPanels/MonopolyPricingStratagemPanel';
import ReputationBoostStratagemPanel from './ExecutionPanels/ReputationBoostStratagemPanel';
// Importer d'autres panneaux spécifiques ici au fur et à mesure de leur création
// import HoardResourcePanel from './ExecutionPanels/HoardResourcePanel';

interface StratagemExecutionPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stratagemData: StratagemData;
}

const StratagemExecutionPanel: React.FC<StratagemExecutionPanelProps> = ({
  isOpen,
  onClose,
  stratagemData,
}) => {
  const { citizenProfile } = useWalletContext();
  const currentUserUsername = citizenProfile?.username;

  const [citizens, setCitizens] = useState<CitizenOption[]>([]);
  // Define LandOption interface
  interface LandOption {
    landId: string;
    historicalName?: string;
    englishName?: string;
    owner?: string;
    district?: string;
  }
  
  const [lands, setLands] = useState<LandOption[]>([]); // Added lands state
  const [buildings, setBuildings] = useState<BuildingOption[]>([]);
  const [resourceTypes, setResourceTypes] = useState<ResourceTypeOption[]>([]);
  
  const [isLoading, setIsLoading] = useState(false); // Gère le chargement des données et l'exécution
  const [executionResult, setExecutionResult] = useState<string | null>(null);
  const [errorResult, setErrorResult] = useState<string | null>(null);
  
  // const [currentInfluenceCost, setCurrentInfluenceCost] = useState<number>(stratagemData.influenceCostBase); // Removed

  const specificPanelRef = useRef<StratagemSpecificPanelRef>(null);

  const fetchDropdownData = useCallback(async () => {
    if (!isOpen || (citizens.length && lands.length && buildings.length && resourceTypes.length)) return; // Ne pas recharger si déjà chargé
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

      // Fetch Lands
      const landsRes = await fetch('/api/lands');
      if (landsRes.ok) {
        const landsData = await landsRes.json();
        // Assuming API returns { success: true, lands: [...] } or similar
        // and each land object matches LandOption structure or can be mapped.
        if (landsData && landsData.success && Array.isArray(landsData.lands)) {
          const formattedLands = landsData.lands.map((l: any) => ({
            landId: l.landId || l.polygonId, // Use landId, fallback to polygonId
            historicalName: l.historicalName,
            englishName: l.englishName,
            owner: l.owner,
            district: l.district,
          }));
          setLands(formattedLands);
        } else {
          console.error('Failed to fetch lands: landsData.lands is not an array or request failed. Received:', landsData);
          setErrorResult(prev => prev ? `${prev}\nFailed to load land list (invalid format).` : 'Failed to load land list (invalid format).');
          setLands([]);
        }
      } else {
        console.error('Failed to fetch lands, status:', landsRes.status);
        setErrorResult(prev => prev ? `${prev}\nFailed to load land list (status: ${landsRes.status}).` : `Failed to load land list (status: ${landsRes.status}).`);
        setLands([]);
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
    if (isOpen) {
      fetchDropdownData();
      // Réinitialiser les résultats lors de l'ouverture
      setExecutionResult(null);
      setErrorResult(null);
      // // Mettre à jour le coût d'influence initial basé sur le stratagème // Removed
      // if (specificPanelRef.current?.getCalculatedInfluenceCost) { // Removed
      //   setCurrentInfluenceCost(specificPanelRef.current.getCalculatedInfluenceCost()); // Removed
      // } else { // Removed
      //   setCurrentInfluenceCost(stratagemData.influenceCostBase); // Removed
      // } // Removed
    }
  }, [isOpen, fetchDropdownData, stratagemData]); // Removed stratagemData.influenceCostBase

  // // Mettre à jour le coût d'influence si le panneau enfant le change (par exemple, via une variante) // Removed
  // useEffect(() => { // Removed
  //   if (specificPanelRef.current?.getCalculatedInfluenceCost) { // Removed
  //     const newCost = specificPanelRef.current.getCalculatedInfluenceCost(); // Removed
  //     if (newCost !== currentInfluenceCost) { // Removed
  //       setCurrentInfluenceCost(newCost); // Removed
  //     } // Removed
  //   } // Removed
  //   // Cette dépendance sur currentInfluenceCost est pour réagir si le coût change // Removed
  //   // à cause d'une interaction dans le panneau enfant qui n'est pas directement // Removed
  //   // liée à un changement de props ici. // Removed
  // }, [stratagemData, currentInfluenceCost]); // Ajouter d'autres dépendances si le coût peut changer autrement // Removed


  const handleExecute = async () => {
    if (!currentUserUsername) {
      setErrorResult("Current user not identified. Cannot execute stratagem.");
      return;
    }
    if (!specificPanelRef.current) {
      setErrorResult("Stratagem configuration panel not loaded correctly.");
      return;
    }

    const details = specificPanelRef.current.getStratagemDetails();
    if (details === null) { // Le panneau enfant indique que les détails sont invalides
      setErrorResult("Please complete all required fields for the stratagem.");
      // Le panneau enfant devrait idéalement gérer l'affichage des erreurs de champ spécifiques.
      return;
    }

    setIsLoading(true);
    setExecutionResult(null);
    setErrorResult(null);

    try {
      const response = await fetch('/api/stratagems/try-create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          citizenUsername: currentUserUsername,
          stratagemType: stratagemData.type,
          stratagemDetails: details, // Assurez-vous que 'details' est utilisé ici
        }),
      });

      const result = await response.json();

      if (response.ok) { // HTTP request to Next.js API was okay
        // result is StratagemEngineResponse from Python
        if (result.success && (!result.processing_status || ["success", "not_applicable", "pending_processing", "initiated_background"].includes(result.processing_status))) {
          // Python engine reported overall success AND processing was fine or not yet applicable/pending/initiated_background
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
  
  // La logique de isExecuteDisabled est simplifiée car le panneau enfant gère la validité de ses propres détails.
  // Le bouton Exécuter est désactivé si le panneau enfant n'a pas fourni de détails valides (via getStratagemDetails retournant null).
  const isExecuteDisabled = useMemo(() => {
    if (isLoading) return true;
    // Liste des types "Prochainement" ou désactivés globalement
    const comingSoonTypes = ['political_campaign', 'information_network', 'maritime_blockade', 'cultural_patronage', 'theater_conspiracy', 'printing_propaganda', 'cargo_mishap', 'employee_poaching', 'joint_venture', 'employee_corruption', 'arson', 'charity_distribution', 'festival_organisation']; // 'marketplace_gossip', 'burglary', 'supplier_lockout', 'financial_patronage', 'neighborhood_watch', 'monopoly_pricing', 'reputation_boost' removed
    if (comingSoonTypes.includes(stratagemData.type)) {
      return true;
    }
    // D'autres logiques de désactivation globales pourraient être ajoutées ici si nécessaire.
    // La validité des champs spécifiques est gérée par le panneau enfant qui retournera null de getStratagemDetails() si invalide.
    return false; 
  }, [isLoading, stratagemData.type]);


  const SpecificStratagemPanelComponent = useMemo(() => {
    switch (stratagemData.type) {
      case 'undercut':
        return UndercutStratagemPanel;
      case 'coordinate_pricing': // Ajout du cas pour coordinate_pricing
        return CoordinatePricingStratagemPanel;
      case 'canal_mugging':
        return CanalMuggingStratagemPanel;
      case 'burglary':
        return BurglaryStratagemPanel;
      case 'reputation_assault':
        return ReputationAssaultStratagemPanel;
      case 'marketplace_gossip': // Ajout du cas pour marketplace_gossip
        return MarketplaceGossipStratagemPanel;
      case 'supplier_lockout':
        return SupplierLockoutStratagemPanel;
      case 'financial_patronage':
        return FinancialPatronageStratagemPanel;
      case 'neighborhood_watch':
        return NeighborhoodWatchStratagemPanel;
      case 'monopoly_pricing':
        return MonopolyPricingStratagemPanel;
      case 'reputation_boost':
        return ReputationBoostStratagemPanel;
      // case 'hoard_resource':
      //   return HoardResourcePanel; 
      // Ajouter d'autres cas ici pour les panneaux spécifiques
      default:
        return DefaultStratagemPanel;
    }
  }, [stratagemData.type]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40 flex items-center justify-center p-4 md:p-8 overflow-y-auto">
      <div className="bg-amber-50/95 text-amber-900 p-6 rounded-lg shadow-2xl w-full h-full flex flex-col border-2 border-amber-400">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-3xl font-serif text-amber-700">{stratagemData.title}</h2>
          <button onClick={onClose} className="text-amber-600 hover:text-amber-800">
            <FaTimes size={24} />
          </button>
        </div>

        <div className="flex-grow overflow-y-auto pr-2 flex"> {/* Changed to flex container */}
          {/* Left Column for Image */}
          <div className="w-1/3 pr-4 flex flex-col items-center sticky top-0"> {/* Sticky for image */}
            <img 
              src={`/images/stratagems/${stratagemData.type}.png`} 
              alt={stratagemData.title} 
              className="w-full max-w-xs h-auto object-contain rounded-lg shadow-lg border border-amber-300 mb-4"
              onError={(e) => {
                const originalSrc = `/images/stratagems/${stratagemData.type}.png`;
                console.warn(`[StratagemExecutionPanel] Failed to load stratagem image at: ${originalSrc}. Falling back to default.`);
                // Fallback to a default image
                (e.target as HTMLImageElement).src = '/images/stratagems/default_stratagem.png'; 
                (e.target as HTMLImageElement).alt = 'Default Stratagem Image';
              }}
            />
            <p className="text-sm italic text-amber-800 mb-1 text-center">{stratagemData.description}</p>
            {/* <p className="text-lg font-semibold text-amber-700 mb-6 text-center"> {/* Adjusted margin */}
              {/* Influence Cost: {currentInfluenceCost} 🎭 // Removed */}
            {/* </p> */}
            {/* Static duration display removed, as it's now dynamic within the panel */}
          </div>

          {/* Right Column for Form */}
          <div className="w-2/3 pl-4 overflow-y-auto"> {/* Scrollable form part */}
            <SpecificStratagemPanelComponent
              ref={specificPanelRef}
              stratagemData={stratagemData}
              currentUserUsername={currentUserUsername}
              currentUserFirstName={citizenProfile?.firstName}
              currentUserLastName={citizenProfile?.lastName}
              citizens={citizens}
              lands={lands} // Pass lands
              buildings={buildings}
              resourceTypes={resourceTypes}
              isLoading={isLoading}
            />
          </div>
        </div>
        
        {executionResult && <p className="text-green-600 mt-4 p-2 bg-green-100 border border-green-300 rounded">{executionResult}</p>}
        {errorResult && <p className="text-red-600 mt-4 p-2 bg-red-100 border border-red-300 rounded">{errorResult}</p>}

        <div className="mt-auto pt-4 border-t border-amber-300">
          <button
            onClick={handleExecute}
            disabled={isExecuteDisabled || isLoading} // isExecuteDisabled gère les types "coming soon"
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

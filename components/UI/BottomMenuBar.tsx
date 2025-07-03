import React, { useState, useRef, useEffect } from 'react';
import { 
  FaCoins, FaScroll, FaUserShield, FaCrosshairs, // Main category icons (FaBomb replaced with FaCrosshairs)
  FaArrowCircleDown, FaSyncAlt, FaArchive, FaStoreSlash, FaUserSecret, FaPalette, FaSitemap, FaAnchor, FaHandHoldingUsd, FaBullhorn, // Existing sub-item icons
  FaMask, FaComments, FaUserPlus, FaNewspaper, FaStar, FaSkullCrossbones, FaKey, FaUserNinja, FaFire, FaGift, FaGlassCheers, // Existing sub-item icons
  FaLandmark, FaUserCog, FaHandshake // New Main/Sub-item icons
} from 'react-icons/fa';
import { eventBus, EventTypes } from '@/lib/utils/eventBus'; // Importer eventBus
import { useWalletContext } from '@/components/UI/WalletProvider'; // Pour obtenir le username actuel

// Configuration de la nature des stratagèmes pour le style
type StratagemNature = 'good' | 'neutral' | 'aggressive' | 'illegal';
interface StratagemStyleConfig {
  nature: StratagemNature;
  classes: string;
}

const stratagemNatureConfig: Record<string, StratagemStyleConfig> = {
  // Good (More interesting Blue)
  'financial_patronage': { nature: 'good', classes: 'bg-sky-500 hover:bg-sky-600 text-white' },
  'cultural_patronage': { nature: 'good', classes: 'bg-sky-500 hover:bg-sky-600 text-white' },
  'reputation_boost': { nature: 'good', classes: 'bg-sky-500 hover:bg-sky-600 text-white' },
  'charity_distribution': { nature: 'good', classes: 'bg-sky-500 hover:bg-sky-600 text-white' },
  'festival_organisation': { nature: 'good', classes: 'bg-sky-500 hover:bg-sky-600 text-white' },
  'neighborhood_watch': { nature: 'good', classes: 'bg-sky-500 hover:bg-sky-600 text-white' },
  // Neutral (Grey)
  'coordinate_pricing': { nature: 'neutral', classes: 'bg-slate-500 hover:bg-slate-600 text-white' },
  'emergency_liquidation': { nature: 'neutral', classes: 'bg-slate-500 hover:bg-slate-600 text-white' },
  'hoard_resource': { nature: 'neutral', classes: 'bg-slate-500 hover:bg-slate-600 text-white' },
  'information_network': { nature: 'neutral', classes: 'bg-slate-500 hover:bg-slate-600 text-white' },
  'joint_venture': { nature: 'neutral', classes: 'bg-slate-500 hover:bg-slate-600 text-white' },
  'political_campaign': { nature: 'neutral', classes: 'bg-slate-500 hover:bg-slate-600 text-white' },
  'printing_propaganda': { nature: 'neutral', classes: 'bg-slate-500 hover:bg-slate-600 text-white' },
  // Aggressive (Less saturated Orange / Amber)
  'undercut': { nature: 'aggressive', classes: 'bg-amber-500 hover:bg-amber-600 text-white' },
  'supplier_lockout': { nature: 'aggressive', classes: 'bg-amber-500 hover:bg-amber-600 text-white' },
  'monopoly_pricing': { nature: 'aggressive', classes: 'bg-amber-500 hover:bg-amber-600 text-white' },
  'reputation_assault': { nature: 'aggressive', classes: 'bg-amber-500 hover:bg-amber-600 text-white' }, // Style already correct
  'marketplace_gossip': { nature: 'aggressive', classes: 'bg-amber-500 hover:bg-amber-600 text-white' },
  'employee_poaching': { nature: 'aggressive', classes: 'bg-amber-500 hover:bg-amber-600 text-white' },
  'theater_conspiracy': { nature: 'aggressive', classes: 'bg-amber-500 hover:bg-amber-600 text-white' },
  // Illegal (Burgundy / Darker Red - Rose)
  'maritime_blockade': { nature: 'illegal', classes: 'bg-rose-700 hover:bg-rose-800 text-white' },
  'cargo_mishap': { nature: 'illegal', classes: 'bg-rose-700 hover:bg-rose-800 text-white' },
  'canal_mugging': { nature: 'illegal', classes: 'bg-rose-700 hover:bg-rose-800 text-white' },
  'burglary': { nature: 'illegal', classes: 'bg-rose-700 hover:bg-rose-800 text-white' }, // Style already correct
  'employee_corruption': { nature: 'illegal', classes: 'bg-rose-700 hover:bg-rose-800 text-white' },
  'arson': { nature: 'illegal', classes: 'bg-rose-700 hover:bg-rose-800 text-white' },
  // Default for any unclassified (should not happen if all are mapped)
  'default': { nature: 'neutral', classes: 'bg-gray-400 hover:bg-gray-500 text-white' }
};


// Interface pour les données passées au panneau de stratagème
export interface StratagemPanelData {
  id: string;
  type: string;
  title: string;
  description: string;
  influenceCostBase: number;
  hasVariants?: boolean; // Optional: defaults to true if not specified
}

interface SubMenuItem {
  id: string; // ex: 'undercut_mild', 'sabotage_supply_line'
  label: string; // ex: 'Undercut (Mild)', 'Sabotage Supply Line'
  icon: React.ElementType;
  stratagemPanelData: StratagemPanelData; // Données à passer au panneau
  // action est maintenant géré par l'ouverture du panneau
}

interface MenuItem {
  id: string;
  label: string;
  icon: React.ElementType;
  action?: () => void; 
  subItems?: SubMenuItem[];
}

// Interface pour les stratagèmes actifs
interface ActiveStratagem {
  stratagemId: string;
  type: string;
  executedBy: string;
  targetCitizen?: string;
  status: string;
}

const BottomMenuBar: React.FC = () => {
  const [activeMainMenuId, setActiveMainMenuId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { citizenProfile } = useWalletContext();
  const [activeStratagems, setActiveStratagems] = useState<ActiveStratagem[]>([]);
  const [isLoadingStratagems, setIsLoadingStratagems] = useState<boolean>(false);
  
  // Récupérer les stratagèmes actifs
  useEffect(() => {
    const fetchActiveStratagems = async () => {
      if (!citizenProfile?.username) return;
      
      setIsLoadingStratagems(true);
      try {
        // Récupérer les stratagèmes exécutés par l'utilisateur
        const response = await fetch(`/api/stratagems?status=active&executedBy=${citizenProfile.username}`);
        
        // Récupérer les stratagèmes ciblant l'utilisateur
        const targetResponse = await fetch(`/api/stratagems?status=active&targetCitizen=${citizenProfile.username}`);
        
        if (response.ok && targetResponse.ok) {
          // Check if responses are JSON
          const contentType = response.headers.get('content-type');
          const targetContentType = targetResponse.headers.get('content-type');
          
          if (contentType?.includes('application/json') && targetContentType?.includes('application/json')) {
            const data = await response.json();
            const targetData = await targetResponse.json();
            
            const userStratagems = data.success ? data.stratagems : [];
            const targetStratagems = targetData.success ? targetData.stratagems : [];
            
            setActiveStratagems([...userStratagems, ...targetStratagems]);
            console.log(`Loaded ${userStratagems.length} active stratagems by user and ${targetStratagems.length} targeting user`);
          } else {
            console.error('Non-JSON response from stratagems API');
            if (!contentType?.includes('application/json')) {
              const text = await response.text();
              console.error('Response 1:', text);
            }
            if (!targetContentType?.includes('application/json')) {
              const text = await targetResponse.text();
              console.error('Response 2:', text);
            }
          }
        } else {
          console.error('Failed to fetch active stratagems', response.status, targetResponse.status);
          if (!response.ok) {
            const text = await response.text();
            console.error('Error response 1:', text);
          }
          if (!targetResponse.ok) {
            const text = await targetResponse.text();
            console.error('Error response 2:', text);
          }
        }
      } catch (error) {
        console.error('Error fetching stratagems:', error);
      } finally {
        setIsLoadingStratagems(false);
      }
    };

    fetchActiveStratagems();
    
    // Rafraîchir les stratagèmes toutes les 5 minutes
    const intervalId = setInterval(fetchActiveStratagems, 5 * 60 * 1000);
    
    return () => clearInterval(intervalId);
  }, [citizenProfile?.username]);

  // Les listes allStratagemTypesInMenu, availableStratagemTypes, et comingSoonStratagemTypesUpdated
  // ne sont plus nécessaires car le style est géré par stratagemNatureConfig et "(Soon)" est dans les labels.

  const menuItems: MenuItem[] = [
    {
      id: 'commerce',
      label: 'COMMERCE',
      icon: FaCoins,
      subItems: [
        // Neutral
        {
          id: 'coordinate_pricing', label: 'Coordinate Prices', icon: FaSyncAlt,
          stratagemPanelData: {
            id: 'coordinate_pricing', type: 'coordinate_pricing', title: 'Coordinate Market Prices',
            description: 'Align your prices for a specific resource with a target citizen, building, or the general market average.',
            influenceCostBase: 10, hasVariants: false,
          }
        },
        {
          id: 'emergency_liquidation', label: 'Liquidate Assets', icon: FaCoins,
          stratagemPanelData: {
            id: 'emergency_liquidation', type: 'emergency_liquidation', title: 'Emergency Liquidation',
            description: "Quickly sell off all items in your personal inventory at discounted rates to generate cash.",
            influenceCostBase: 5, hasVariants: true,
          }
        },
        {
          id: 'hoard_resource', label: 'Hoard Resource', icon: FaArchive, 
          stratagemPanelData: {
            id: 'hoard_resource', type: 'hoard_resource', title: 'Hoard Specific Resource',
            description: 'Designate a resource to accumulate. Your citizen and their employees will prioritize acquiring this resource.',
            influenceCostBase: 15, hasVariants: false,
          }
        },
        {
          id: 'joint_venture', label: 'Joint Venture (Soon)', icon: FaHandshake,
          stratagemPanelData: {
            id: 'joint_venture', type: 'joint_venture', title: 'Joint Venture (Coming Soon)',
            description: 'Propose a formal business partnership with another citizen.',
            influenceCostBase: 20, hasVariants: false,
          }
        },
        // Aggressive
        {
          id: 'monopoly_pricing', label: 'Monopoly (Soon)', icon: FaCoins,
          stratagemPanelData: {
            id: 'monopoly_pricing', type: 'monopoly_pricing', title: 'Monopoly Pricing (Coming Soon)',
            description: 'Leverage dominant market position to significantly increase prices for a specific resource.',
            influenceCostBase: 40, hasVariants: true, 
          }
        },
        {
          id: 'supplier_lockout', label: 'Supplier Lockout (Soon)', icon: FaStoreSlash,
          stratagemPanelData: {
            id: 'supplier_lockout', type: 'supplier_lockout', title: 'Supplier Lockout (Coming Soon)',
            description: 'Secure exclusive or priority supply agreements with specific resource suppliers.',
            influenceCostBase: 20, hasVariants: false,
          }
        },
        { 
          id: 'undercut', 
          label: 'Undercut', 
          icon: FaArrowCircleDown, 
          stratagemPanelData: {
            id: 'undercut', type: 'undercut', title: 'Undercut Market Prices',
            description: 'Strategically lower your prices for a specific resource to undercut competitors. Choose your level of aggression and targets.',
            influenceCostBase: 5, hasVariants: true,
          }
        },
      ]
    },
    { 
      id: 'political', 
      label: 'POLITICAL', 
      icon: FaScroll, 
      subItems: [
        {
          id: 'political_campaign', label: 'Campaign (Soon)', icon: FaBullhorn,
          stratagemPanelData: {
            id: 'political_campaign', type: 'political_campaign', title: 'Political Campaign (Coming Soon)',
            description: 'Influence governance by lobbying for or against a specific decree or policy change.',
            influenceCostBase: 50, hasVariants: false,
          }
        },
        {
          id: 'printing_propaganda', label: 'Propaganda (Soon)', icon: FaNewspaper,
          stratagemPanelData: {
            id: 'printing_propaganda', type: 'printing_propaganda', title: 'Printing Propaganda (Coming Soon)',
            description: 'Conduct information warfare by mass-producing and distributing pamphlets and rumors.',
            influenceCostBase: 30, hasVariants: false,
          }
        }
      ]
    },
    { 
      id: 'social_public', // New ID for clarity
      label: 'SOCIAL', 
      icon: FaLandmark, // New icon for public/cultural impact
      subItems: [
        // Good
        {
          id: 'charity_distribution', label: 'Charity (Soon)', icon: FaGift,
          stratagemPanelData: {
            id: 'charity_distribution', type: 'charity_distribution', title: 'Charity Distribution (Coming Soon)',
            description: "Anonymously distribute Ducats to poor citizens in a specific district.",
            influenceCostBase: 3, hasVariants: false, 
          }
        },
        {
          id: 'cultural_patronage', label: 'Cult. Patronage (Soon)', icon: FaPalette,
          stratagemPanelData: {
            id: 'cultural_patronage', type: 'cultural_patronage', title: 'Cultural Patronage (Coming Soon)',
            description: 'Sponsor artists, performances, or cultural institutions to build social capital.',
            influenceCostBase: 30, hasVariants: true,
          }
        },
        {
          id: 'festival_organisation', label: 'Festival (Soon)', icon: FaGlassCheers,
          stratagemPanelData: {
            id: 'festival_organisation', type: 'festival_organisation', title: 'Festival Organisation (Coming Soon)',
            description: "Organize and sponsor a public festival in a specific district.",
            influenceCostBase: 10, hasVariants: false, 
          }
        },
        // Aggressive
        {
          id: 'theater_conspiracy', label: 'Theater Play (Soon)', icon: FaMask,
          stratagemPanelData: {
            id: 'theater_conspiracy', type: 'theater_conspiracy', title: 'Theater Conspiracy (Coming Soon)',
            description: 'Manipulate public opinion by staging theatrical performances with specific themes.',
            influenceCostBase: 25, hasVariants: false,
          }
        },
      ]
    },
    {
      id: 'personal_tactics', // New ID for clarity
      label: 'PERSONAL',
      icon: FaUserCog, // New icon for interpersonal tactics
      subItems: [
        // Good
        {
          id: 'financial_patronage', label: 'Fin. Patronage (Soon)', icon: FaHandHoldingUsd,
          stratagemPanelData: {
            id: 'financial_patronage', type: 'financial_patronage', title: 'Financial Patronage (Coming Soon)',
            description: 'Provide comprehensive financial support to promising individuals or allies.',
            influenceCostBase: 25, hasVariants: false,
          }
        },
        {
          id: 'reputation_boost', label: 'Rep. Boost (Soon)', icon: FaStar,
          stratagemPanelData: {
            id: 'reputation_boost', type: 'reputation_boost', title: 'Reputation Boost (Coming Soon)',
            description: "Actively improve a target citizen's public image and trustworthiness through a coordinated campaign.",
            influenceCostBase: 30, hasVariants: false, 
          }
        },
        // Aggressive
        {
          id: 'employee_poaching', label: 'Poach Employee (Soon)', icon: FaUserPlus,
          stratagemPanelData: {
            id: 'employee_poaching', type: 'employee_poaching', title: 'Employee Poaching (Coming Soon)',
            description: 'Recruit a skilled employee from a competitor by making them a better offer.',
            influenceCostBase: 6, hasVariants: false,
          }
        },
        {
          id: 'marketplace_gossip', label: 'Gossip', icon: FaComments, // "(Soon)" retiré
          stratagemPanelData: {
            id: 'marketplace_gossip', type: 'marketplace_gossip', title: 'Marketplace Gossip', // "(Coming Soon)" retiré
            description: "Subtly damage a competitor's reputation by spreading rumors through social networks.",
            influenceCostBase: 5, hasVariants: false,
          }
        },
        {
          id: 'reputation_assault', label: 'Reputation Assault', icon: FaUserSecret,
          stratagemPanelData: {
            id: 'reputation_assault', type: 'reputation_assault', title: 'Reputation Assault',
            description: "Subtly damage a competitor's reputation by spreading negative information to their associates.",
            influenceCostBase: 30, hasVariants: false,
          }
        },
      ]
    },
    { 
      id: 'security', // Renamed from security_intel
      label: 'SECURITY', 
      icon: FaUserShield, 
      subItems: [
        // Good
        {
          id: 'neighborhood_watch', label: 'Neighborhood Watch (Soon)', icon: FaUserShield, 
          stratagemPanelData: {
            id: 'neighborhood_watch', type: 'neighborhood_watch', title: 'Neighborhood Watch (Coming Soon)',
            description: 'Enhance security and reduce crime in a specific district through collective citizen vigilance.',
            influenceCostBase: 10, hasVariants: false,
          }
        },
        // Neutral
        {
          id: 'information_network', label: 'Info Network (Soon)', icon: FaSitemap,
          stratagemPanelData: {
            id: 'information_network', type: 'information_network', title: 'Information Network (Coming Soon)',
            description: 'Establish intelligence gathering operations targeting specific citizens or market sectors.',
            influenceCostBase: 40, hasVariants: false,
          }
        },
      ]
    },
    { 
      id: 'warfare', // Renamed from covert_ops
      label: 'WARFARE', 
      icon: FaCrosshairs, // Changed from FaBomb to FaCrosshairs
      subItems: [
        // Illegal (sorted alphabetically)
        {
          id: 'arson', label: 'Arson (Soon)', icon: FaFire,
          stratagemPanelData: {
            id: 'arson', type: 'arson', title: 'Arson (Coming Soon)',
            description: "Burn down a target property, requiring it to be rebuilt.",
            influenceCostBase: 9, hasVariants: false,
          }
        },
        {
          id: 'burglary', label: 'Burglary', icon: FaKey, // Removed (Soon)
          stratagemPanelData: {
            id: 'burglary', type: 'burglary', title: 'Burglary', // Removed (Coming Soon)
            description: "Steal tools, materials, or finished goods from a competitor's production building.",
            influenceCostBase: 6, hasVariants: false,
          }
        },
        {
          id: 'canal_mugging', label: 'Mugging', icon: FaSkullCrossbones,
          stratagemPanelData: {
            id: 'canal_mugging', type: 'canal_mugging', title: 'Canal Mugging',
            description: "Attempt to rob citizens at night during gondola transits. (Illegal)",
            influenceCostBase: 1, // Cost per day
            hasVariants: true, 
            // durationDays is now dynamic, remove from here
          }
        },
        {
          id: 'cargo_mishap', label: 'Cargo "Mishap" (Soon)', icon: FaAnchor,
          stratagemPanelData: {
            id: 'cargo_mishap', type: 'cargo_mishap', title: 'Cargo "Mishap" (Coming Soon)',
            description: "Sabotage a competitor's shipment by arranging for their goods to \"disappear\" while in transit.",
            influenceCostBase: 8, hasVariants: false,
          }
        },
        {
          id: 'employee_corruption', label: 'Emp. Corrupt. (Soon)', icon: FaUserNinja,
          stratagemPanelData: {
            id: 'employee_corruption', type: 'employee_corruption', title: 'Employee Corruption (Coming Soon)',
            description: "Bribe occupants of businesses to reduce productivity and steal things for you.",
            influenceCostBase: 7, hasVariants: false, 
          }
        },
        {
          id: 'maritime_blockade', label: 'Blockade (Soon)', icon: FaAnchor,
          stratagemPanelData: {
            id: 'maritime_blockade', type: 'maritime_blockade', title: 'Maritime Blockade (Coming Soon)',
            description: "Control water access to cripple a competitor's trade and waterfront operations.",
            influenceCostBase: 70, hasVariants: false, 
          }
        },
      ]
    }
  ];

  // useEffect pour gérer les clics en dehors n'est plus nécessaire avec le survol.
  // handleMainMenuClick est également remplacé par la logique de survol.

  const activeSubItems = menuItems.find(item => item.id === activeMainMenuId)?.subItems;

  // Fonction pour compter les stratagèmes actifs par type
  const countActiveStratagemsByType = (type: string): { byUser: number, againstUser: number } => {
    if (!citizenProfile?.username) return { byUser: 0, againstUser: 0 };
    
    const byUser = activeStratagems.filter(
      s => s.type === type && s.executedBy === citizenProfile.username
    ).length;
    
    const againstUser = activeStratagems.filter(
      s => s.type === type && s.targetCitizen === citizenProfile.username
    ).length;
    
    return { byUser, againstUser };
  };

  return (
    <div 
      ref={menuRef} 
      className="fixed bottom-2 left-1/2 transform -translate-x-1/2 z-30 flex flex-col items-center"
      onMouseLeave={() => setActiveMainMenuId(null)} // Ferme le sous-menu si la souris quitte toute la zone
    >
      {/* Sous-menu */}
      {activeSubItems && activeSubItems.length > 0 && (
        <div className="mb-2 flex space-x-1 bg-black/60 p-1.5 rounded-md shadow-md border border-amber-500/50">
          {activeSubItems.map((subItem) => (
            <div key={subItem.id} className="relative">
              <button
                onClick={() => { // Le clic sur un sous-élément exécute toujours l'action
                  console.log(`Submenu item ${subItem.label} clicked. Emitting event to open stratagem panel.`);
                  eventBus.emit(EventTypes.OPEN_STRATAGEM_PANEL, subItem.stratagemPanelData);
                  setActiveMainMenuId(null); // Ferme le sous-menu après l'action
                }}
                className={`flex flex-col items-center justify-center p-1 rounded-sm transition-colors w-20 h-16 ${
                  (stratagemNatureConfig[subItem.stratagemPanelData.type] || stratagemNatureConfig.default).classes
                }`}
                title={subItem.label}
              >
                <subItem.icon className="w-6 h-6 mb-0.5" />
                <span className="text-[10px] font-medium uppercase tracking-normal">{subItem.label}</span>
              </button>
              
              {/* Indicateurs de notification pour les stratagèmes actifs */}
              {citizenProfile?.username && (
                <>
                  {/* Stratagèmes exécutés par l'utilisateur (bleu foncé) */}
                  {countActiveStratagemsByType(subItem.stratagemPanelData.type).byUser > 0 && (
                    <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-blue-800 text-white text-xs flex items-center justify-center border border-blue-300">
                      {countActiveStratagemsByType(subItem.stratagemPanelData.type).byUser}
                    </div>
                  )}
                  
                  {/* Stratagèmes contre l'utilisateur (bordeaux) */}
                  {countActiveStratagemsByType(subItem.stratagemPanelData.type).againstUser > 0 && (
                    <div className="absolute -top-1 -left-1 w-5 h-5 rounded-full bg-rose-800 text-white text-xs flex items-center justify-center border border-rose-300">
                      {countActiveStratagemsByType(subItem.stratagemPanelData.type).againstUser}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Menu principal */}
      <div className="flex space-x-1 bg-black/70 p-2 rounded-md shadow-lg border border-amber-500/70">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onMouseEnter={() => { // Afficher le sous-menu au survol
              if (item.subItems && item.subItems.length > 0) {
                setActiveMainMenuId(item.id);
              } else {
                setActiveMainMenuId(null); // S'il n'y a pas de sous-menu, s'assurer qu'aucun n'est actif
              }
            }}
            onClick={() => { // Gérer le clic pour les éléments sans sous-menu (si jamais il y en a)
              if (!item.subItems || item.subItems.length === 0) {
                if (item.action) {
                  item.action();
                }
                setActiveMainMenuId(null); // Fermer tout autre sous-menu
              }
              // Si l'élément a des sous-items, le survol les gère. Le clic pourrait être utilisé pour une action par défaut ou rien.
              // Pour l'instant, si un item a des subItems, le clic sur le bouton principal ne fait rien de plus que le survol.
            }}
            className={`flex flex-col items-center justify-center text-amber-100 hover:text-white p-1.5 rounded-sm transition-colors w-20 h-16 ${
              activeMainMenuId === item.id ? 'bg-amber-700/70' : 'hover:bg-amber-700/60'
            }`}
            title={item.label}
          >
            <item.icon className="w-6 h-6 mb-0.5" />
            <span className="text-[10px] font-medium uppercase tracking-normal">{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default BottomMenuBar;

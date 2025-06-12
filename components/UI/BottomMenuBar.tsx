import React, { useState, useRef, useEffect } from 'react';
import { 
  FaCoins, FaHandshake, FaScroll, FaUserShield, FaBomb, // Main category icons
  FaArrowCircleDown, FaSyncAlt, FaArchive, FaStoreSlash, FaUserSecret, FaPalette, FaSitemap, FaAnchor, FaHandHoldingUsd, FaBullhorn, FaUsers, // Existing sub-item icons
  FaMask, FaComments, FaUserPlus, FaNewspaper // New sub-item icons
} from 'react-icons/fa';
import { eventBus, EventTypes } from '@/lib/utils/eventBus'; // Importer eventBus

// Liste des types de stratagèmes "Prochainement"
const comingSoonStratagemTypes = [
  'supplier_lockout', 'political_campaign', 'information_network', 'maritime_blockade', 
  'cultural_patronage', 'theater_conspiracy', 'printing_propaganda', 'cargo_mishap', 
  'marketplace_gossip', 'employee_poaching', 'joint_venture', 
  'financial_patronage', 'neighborhood_watch'
  // Les nouveaux types seront ajoutés ici par la logique de génération de menuItems
];

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

const BottomMenuBar: React.FC = () => {
  const [activeMainMenuId, setActiveMainMenuId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Mise à jour de la liste des types "Prochainement" pour inclure tous les stratagèmes non disponibles.
  // Cette liste est utilisée pour le style des boutons.
  const allStratagemTypesInMenu = [
    'undercut', 'coordinate_pricing', 'emergency_liquidation', 'hoard_resource', 'supplier_lockout', 'joint_venture', 'monopoly_pricing',
    'reputation_assault', 'financial_patronage', 'cultural_patronage', 'theater_conspiracy', 'marketplace_gossip', 'employee_poaching',
    'political_campaign', 'printing_propaganda',
    'information_network', 'neighborhood_watch',
    'maritime_blockade', 'cargo_mishap'
  ];
  const availableStratagemTypes = [ // Liste des stratagèmes réellement implémentés et disponibles
    'undercut', 'coordinate_pricing', 'emergency_liquidation', 'hoard_resource', 'reputation_assault'
  ];
  const comingSoonStratagemTypesUpdated = allStratagemTypesInMenu.filter(type => !availableStratagemTypes.includes(type));


  const menuItems: MenuItem[] = [
    {
      id: 'commerce',
      label: 'COMMERCE',
      icon: FaCoins,
      subItems: [
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
          id: 'supplier_lockout', label: 'Supplier Lockout (Soon)', icon: FaStoreSlash,
          stratagemPanelData: {
            id: 'supplier_lockout', type: 'supplier_lockout', title: 'Supplier Lockout (Coming Soon)',
            description: 'Secure exclusive or priority supply agreements with specific resource suppliers.',
            influenceCostBase: 20, hasVariants: false,
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
        {
          id: 'monopoly_pricing', label: 'Monopoly (Soon)', icon: FaCoins, // Ou FaDollarSign si importé
          stratagemPanelData: {
            id: 'monopoly_pricing', type: 'monopoly_pricing', title: 'Monopoly Pricing (Coming Soon)',
            description: 'Leverage dominant market position to significantly increase prices for a specific resource.',
            influenceCostBase: 40, hasVariants: true, // Variants: Mild (30), Standard (40), Aggressive (50)
          }
        }
      ]
    },
    { 
      id: 'social', 
      label: 'SOCIAL', 
      icon: FaUsers, // Changed from FaHandshake to FaUsers for broader social category
      subItems: [
        {
          id: 'reputation_assault', label: 'Reputation Assault', icon: FaUserSecret,
          stratagemPanelData: {
            id: 'reputation_assault', type: 'reputation_assault', title: 'Reputation Assault',
            description: "Subtly damage a competitor's reputation by spreading negative information to their associates.",
            influenceCostBase: 30, hasVariants: false,
          }
        },
        {
          id: 'financial_patronage', label: 'Fin. Patronage (Soon)', icon: FaHandHoldingUsd,
          stratagemPanelData: {
            id: 'financial_patronage', type: 'financial_patronage', title: 'Financial Patronage (Coming Soon)',
            description: 'Provide comprehensive financial support to promising individuals or allies.',
            influenceCostBase: 25, hasVariants: false,
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
          id: 'theater_conspiracy', label: 'Theater Play (Soon)', icon: FaMask,
          stratagemPanelData: {
            id: 'theater_conspiracy', type: 'theater_conspiracy', title: 'Theater Conspiracy (Coming Soon)',
            description: 'Manipulate public opinion by staging theatrical performances with specific themes.',
            influenceCostBase: 25, hasVariants: false,
          }
        },
        {
          id: 'marketplace_gossip', label: 'Gossip (Soon)', icon: FaComments,
          stratagemPanelData: {
            id: 'marketplace_gossip', type: 'marketplace_gossip', title: 'Marketplace Gossip (Coming Soon)',
            description: "Subtly damage a competitor's reputation by spreading rumors through social networks.",
            influenceCostBase: 5, hasVariants: false,
          }
        },
        {
          id: 'employee_poaching', label: 'Poach Employee (Soon)', icon: FaUserPlus,
          stratagemPanelData: {
            id: 'employee_poaching', type: 'employee_poaching', title: 'Employee Poaching (Coming Soon)',
            description: 'Recruit a skilled employee from a competitor by making them a better offer.',
            influenceCostBase: 6, hasVariants: false,
          }
        }
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
      id: 'security_intel', 
      label: 'SECURITY & INTEL', 
      icon: FaUserShield, 
      subItems: [
        {
          id: 'information_network', label: 'Info Network (Soon)', icon: FaSitemap,
          stratagemPanelData: {
            id: 'information_network', type: 'information_network', title: 'Information Network (Coming Soon)',
            description: 'Establish intelligence gathering operations targeting specific citizens or market sectors.',
            influenceCostBase: 40, hasVariants: false,
          }
        },
        {
          id: 'neighborhood_watch', label: 'Neighborhood Watch (Soon)', icon: FaUserShield, 
          stratagemPanelData: {
            id: 'neighborhood_watch', type: 'neighborhood_watch', title: 'Neighborhood Watch (Coming Soon)',
            description: 'Enhance security and reduce crime in a specific district through collective citizen vigilance.',
            influenceCostBase: 10, hasVariants: false,
          }
        }
      ]
    },
    { 
      id: 'covert_ops', 
      label: 'COVERT OPS', 
      icon: FaBomb, 
      subItems: [
        {
          id: 'maritime_blockade', label: 'Blockade (Soon)', icon: FaAnchor,
          stratagemPanelData: {
            id: 'maritime_blockade', type: 'maritime_blockade', title: 'Maritime Blockade (Coming Soon)',
            description: "Control water access to cripple a competitor's trade and waterfront operations.",
            influenceCostBase: 70, hasVariants: false, 
          }
        },
        {
          id: 'cargo_mishap', label: 'Cargo "Mishap" (Soon)', icon: FaAnchor, // Using FaAnchor as it's often maritime
          stratagemPanelData: {
            id: 'cargo_mishap', type: 'cargo_mishap', title: 'Cargo "Mishap" (Coming Soon)',
            description: "Sabotage a competitor's shipment by arranging for their goods to \"disappear\" while in transit.",
            influenceCostBase: 8, hasVariants: false,
          }
        }
      ]
    }
  ];

  const handleMainMenuClick = (item: MenuItem) => {
    if (item.subItems && item.subItems.length > 0) {
      setActiveMainMenuId(prevId => (prevId === item.id ? null : item.id));
    } else {
      setActiveMainMenuId(null); // Cache tout autre sous-menu ouvert
      if (item.action) {
        item.action();
      }
    }
  };

  // Gérer les clics en dehors du menu pour fermer le sous-menu
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setActiveMainMenuId(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const activeSubItems = menuItems.find(item => item.id === activeMainMenuId)?.subItems;

  return (
    <div ref={menuRef} className="fixed bottom-2 left-1/2 transform -translate-x-1/2 z-30 flex flex-col items-center">
      {/* Sous-menu */}
      {activeSubItems && activeSubItems.length > 0 && (
        <div className="mb-2 flex space-x-1 bg-black/60 p-1.5 rounded-md shadow-md border border-amber-500/50">
          {activeSubItems.map((subItem) => (
            <button
              key={subItem.id}
              onClick={() => {
                console.log(`Submenu item ${subItem.label} clicked. Emitting event to open stratagem panel.`);
                eventBus.emit(EventTypes.OPEN_STRATAGEM_PANEL, subItem.stratagemPanelData);
                setActiveMainMenuId(null); // Ferme le sous-menu après l'action
              }}
              className={`flex flex-col items-center justify-center p-1 rounded-sm transition-colors w-20 h-16 ${
                comingSoonStratagemTypesUpdated.includes(subItem.stratagemPanelData.type)
                  ? 'text-amber-50 hover:text-white hover:bg-amber-600/50' // Style pour "Coming Soon"
                  : 'bg-yellow-500 hover:bg-yellow-600 text-black' // Style pour disponible
              }`}
              title={subItem.label}
            >
              <subItem.icon className="w-6 h-6 mb-0.5" />
              <span className="text-[10px] font-medium uppercase tracking-normal">{subItem.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Menu principal */}
      <div className="flex space-x-1 bg-black/70 p-2 rounded-md shadow-lg border border-amber-500/70">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => handleMainMenuClick(item)}
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

import React, { useState, useRef, useEffect } from 'react';
import { FaCrosshairs, FaHandshake, FaScroll, FaProjectDiagram, FaShieldAlt, FaCoins, FaArrowCircleDown, FaBomb, FaSyncAlt, FaArchive, FaStoreSlash, FaBullhorn, FaUserSecret, FaPalette, FaSitemap, FaAnchor, FaUsersShield, FaHandHoldingUsd } from 'react-icons/fa'; // Ajout FaAnchor, FaUsersShield, FaHandHoldingUsd
import { eventBus, EventTypes } from '@/lib/utils/eventBus'; // Importer eventBus

// Liste des types de stratagèmes "Prochainement"
const comingSoonStratagemTypes = [
  'supplier_lockout', 'political_campaign', 'information_network', 'maritime_blockade', 
  'cultural_patronage', 'theater_conspiracy', 'printing_propaganda', 'cargo_mishap', 
  'marketplace_gossip', 'employee_poaching', 'joint_venture', 
  'financial_patronage', 'neighborhood_watch'
  // Ajouter d'autres types de stratagèmes "Prochainement" ici
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

  const menuItems: MenuItem[] = [
    {
      id: 'warfare',
      label: 'WARFARE',
      icon: FaCrosshairs,
      subItems: [
        {
          id: 'information_network',
          label: 'Info Network (Soon)',
          icon: FaSitemap,
          stratagemPanelData: {
            id: 'information_network',
            type: 'information_network',
            title: 'Information Network (Coming Soon)',
            description: 'Establish intelligence gathering operations targeting specific citizens or market sectors. Recruit informants, receive advanced notifications about competitor strategies, market movements, and gain priority access to information about incoming merchant galleys.',
            influenceCostBase: 40,
            hasVariants: false, // Or true if variants like "Local", "Regional", "City-Wide" are planned
          }
        },
        {
          id: 'maritime_blockade',
          label: 'Blockade (Soon)',
          icon: FaAnchor,
          stratagemPanelData: {
            id: 'maritime_blockade',
            type: 'maritime_blockade',
            title: 'Maritime Blockade (Coming Soon)',
            description: "Control water access to cripple a competitor's trade. Coordinate with dock owners and gondola operators to restrict competitor access to key waterways and facilities, including arsenal gates.",
            influenceCostBase: 70,
            hasVariants: false, 
          }
        },
        { 
          id: 'undercut', 
          label: 'Undercut', 
          icon: FaArrowCircleDown, 
          stratagemPanelData: {
            id: 'undercut',
            type: 'undercut', // Type pour l'API
            title: 'Undercut Market Prices',
            description: 'Strategically lower your prices for a specific resource to undercut competitors. Choose your level of aggression and targets. This action will impact your relationship with the targeted citizen or building owner.',
            influenceCostBase: 5, // Coût pour "Mild", sera multiplié pour Standard/Aggressive
            hasVariants: true,
          }
        },
        // Exemple d'un autre stratagème
        // { 
        //   id: 'sabotage', 
        //   label: 'Sabotage', 
        //   icon: FaBomb, 
        //   stratagemPanelData: {
        //     id: 'sabotage_production',
        //     type: 'sabotage',
        //     title: 'Sabotage Production',
        //     description: 'Disrupt a competitor\'s production facility to gain an advantage.',
        //     influenceCostBase: 20,
        //   }
        // },
      ]
    },
    { 
      id: 'alliance', 
      label: 'ALLIANCE', 
      icon: FaHandshake, 
      subItems: [
        {
          id: 'financial_patronage',
          label: 'Patronage (Soon)',
          icon: FaHandHoldingUsd, // Ou FaHandshake si FaHandHoldingUsd n'est pas souhaitée/disponible
          stratagemPanelData: {
            id: 'financial_patronage',
            type: 'financial_patronage',
            title: 'Financial Patronage (Coming Soon)',
            description: 'Provide comprehensive financial support to promising individuals, struggling families, or loyal allies, creating deep personal bonds and long-term obligations. Costs 25 Influence and ongoing Ducats.',
            influenceCostBase: 25,
            hasVariants: false, // Le niveau de patronage est un paramètre, pas une variante de coût d'influence ici
          }
        },
        {
          id: 'joint_venture', // Assurez-vous que cet ID est unique et correspond à un stratagème existant ou prévu
          label: 'Joint Venture (Soon)',
          icon: FaHandshake, // Icône existante
          stratagemPanelData: {
            id: 'joint_venture',
            type: 'joint_venture',
            title: 'Joint Venture (Coming Soon)',
            description: 'Propose a formal business partnership with another citizen, defining contributions, responsibilities, and profit-sharing.',
            influenceCostBase: 20, // Coût d'influence de base
            hasVariants: false, // Pas de variantes de coût d'influence typiques ici
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
          id: 'political_campaign',
          label: 'Campaign (Soon)',
          icon: FaBullhorn,
          stratagemPanelData: {
            id: 'political_campaign',
            type: 'political_campaign', // API type
            title: 'Political Campaign (Coming Soon)',
            description: 'Target: Specific decree/policy change. Effect: Use wealth and relationships to influence governance. Duration: Until decree vote or campaign abandoned. Entity Changes: Spend INFLUENCE and DUCATS to lobby citizens and officials. Create multiple MESSAGES to citizens explaining policy benefits. May create new DECREES entry with your proposed policy. RELATIONSHIPS scores shift based on citizen agreement with your position. If successful, new decree creates systematic CONTRACTS or economic rule changes. Failed campaigns may damage your political reputation. Success increases your ongoing INFLUENCE generation.',
            influenceCostBase: 50, // Placeholder cost
            hasVariants: false, // Ou true si des variantes d'intensité sont prévues
          }
        }
        // Add other political stratagems here
      ]
    },
    { id: 'cocontrol', label: 'CONTROL', icon: FaProjectDiagram, action: () => console.log('Control clicked') },
    { 
      id: 'defensive', 
      label: 'DEFENSIVE', 
      icon: FaShieldAlt, 
      subItems: [
        {
          id: 'neighborhood_watch',
          label: 'Watch (Soon)',
          icon: FaUsersShield, // Ou FaShieldAlt si FaUsersShield n'est pas souhaitée/disponible
          stratagemPanelData: {
            id: 'neighborhood_watch',
            type: 'neighborhood_watch',
            title: 'Neighborhood Watch (Coming Soon)',
            description: 'Enhance security and reduce crime in a specific district through collective citizen vigilance. Costs 10 Influence.',
            influenceCostBase: 10,
            hasVariants: false,
          }
        }
      ]
    },
    { 
      id: 'economic', 
      label: 'ECONOMIC', 
      icon: FaCoins, 
      subItems: [
        {
          id: 'reputation_assault',
          label: 'Reputation Assault',
          icon: FaUserSecret, // Placeholder, consider a more fitting icon like FaUserSlash or FaCommentSlash
          stratagemPanelData: {
            id: 'reputation_assault',
            type: 'reputation_assault',
            title: 'Reputation Assault',
            description: "Subtly damage a competitor's reputation by spreading negative information to their associates. This action will severely impact your relationship with the target.",
            influenceCostBase: 30, // Example cost
            hasVariants: false, // No variants for this one
          }
        },
        {
          id: 'emergency_liquidation',
          label: 'Liquidate Assets',
          icon: FaCoins, // Consider FaGavel or FaShoppingCart with a down arrow
          stratagemPanelData: {
            id: 'emergency_liquidation',
            type: 'emergency_liquidation',
            title: 'Emergency Liquidation',
            description: "Quickly sell off all items in your personal inventory at discounted rates to generate cash. Choose the level of discount, which also affects how long the sale lasts.",
            influenceCostBase: 5, // Low cost as it's a personal action
            hasVariants: true, // Mild, Standard, Aggressive for discount levels
          }
        },
        {
          id: 'coordinate_pricing',
          label: 'Coordinate Prices',
          icon: FaSyncAlt,
          stratagemPanelData: {
            id: 'coordinate_pricing',
            type: 'coordinate_pricing',
            title: 'Coordinate Market Prices',
            description: 'Align your prices for a specific resource with a target citizen, building, or the general market average. This helps in stabilizing prices or forming economic ententes.',
            influenceCostBase: 10,
            hasVariants: false,
          }
        },
        {
          id: 'hoard_resource',
          label: 'Hoard Resource',
          icon: FaArchive, 
          stratagemPanelData: {
            id: 'hoard_resource',
            type: 'hoard_resource',
            title: 'Hoard Specific Resource',
            description: 'Designate a resource to accumulate. Your citizen and their employees will prioritize acquiring this resource and storing it in an available storage (private or public).',
            influenceCostBase: 15,
            hasVariants: false,
          }
        },
        {
          id: 'supplier_lockout',
          label: 'Supplier Lockout (Soon)',
          icon: FaStoreSlash,
          stratagemPanelData: {
            id: 'supplier_lockout',
            type: 'supplier_lockout', // API type
            title: 'Supplier Lockout (Coming Soon)',
            description: 'Target: Specific resource suppliers. Effect: Secure exclusive or priority relationships. Duration: Based on contract terms negotiated. Entity Changes: Create long-term CONTRACTS (import) with premium pricing (+10-20%). Suppliers agree to fulfill your orders before public contracts. Your RESOURCES supply becomes more reliable and predictable. Competitors lose access to preferred suppliers. Creates PROBLEMS for competitors who relied on those suppliers. Builds stronger RELATIONSHIPS trust with supplier citizens. Requires sustained higher DUCATS expenditure.',
            influenceCostBase: 20, // Placeholder cost
            hasVariants: false,
          }
        }
        // Add other economic stratagems here
      ]
    },
    {
      id: 'culture',
      label: 'CULTURE',
      icon: FaPalette, // Nouvelle icône pour la culture
      subItems: [
        {
          id: 'cultural_patronage',
          label: 'Patronage (Soon)',
          icon: FaPalette, // Ou une autre icône plus spécifique si disponible
          stratagemPanelData: {
            id: 'cultural_patronage',
            type: 'cultural_patronage', // API type
            title: 'Cultural Patronage (Coming Soon)',
            description: 'Sponsor artists, performances, or cultural institutions to build social capital and enhance your reputation. This action increases your influence generation and improves relationships with cultural elites.',
            influenceCostBase: 30, // Coût de base, peut varier
            hasVariants: true, // Pourrait avoir des variantes de niveau de patronage (Modest, Standard, Grand)
          }
        }
        // Add other cultural stratagems here
      ]
    },
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
                comingSoonStratagemTypes.includes(subItem.stratagemPanelData.type)
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

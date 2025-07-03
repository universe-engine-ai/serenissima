// Ce fichier contiendra les types partagés par StratagemExecutionPanel et les panneaux spécifiques.

export interface StratagemData {
  id: string;
  type: string;
  title: string;
  description: string;
  // influenceCostBase: number; // Removed
  hasVariants?: boolean;
}

export interface CitizenOption {
  username: string;
  firstName?: string;
  lastName?: string;
  socialClass?: string;
}

export interface LandOption {
  landId: string;
  historicalName?: string;
  englishName?: string;
  owner?: string;
  district?: string;
}

export interface BuildingOption {
  buildingId: string;
  name?: string;
  type?: string;
  owner?: string;
}

export interface ResourceTypeOption {
  id: string;
  name: string;
  category?: string;
}

// Interface pour les props des panneaux de stratagème spécifiques
export interface StratagemSpecificPanelProps {
  stratagemData: StratagemData;
  currentUserUsername: string | null;
  currentUserFirstName?: string; // Ajouté
  currentUserLastName?: string;  // Ajouté
  citizens: CitizenOption[];
  lands: LandOption[]; // Added lands
  buildings: BuildingOption[];
  resourceTypes: ResourceTypeOption[];
  isLoading: boolean;
  // Les panneaux spécifiques devront exposer ces méthodes via useImperativeHandle
}

// Interface pour le handle de la ref des panneaux spécifiques
export interface StratagemSpecificPanelRef {
  getStratagemDetails: () => Record<string, any> | null;
  // getCalculatedInfluenceCost?: () => number; // Removed
}

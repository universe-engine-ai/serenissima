import { NextResponse } from 'next/server';
import Airtable, { FieldSet, Record as AirtableRecord } from 'airtable';
import fs from 'fs/promises';
import path from 'path';

// Airtable Configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
  throw new Error('Airtable API key or Base ID is not configured in environment variables.');
}

const airtable = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

// Helper to convert a string to camelCase
const toCamelCase = (s: string) => {
  if (!s) return s;
  return s.replace(/([-_][a-z])/ig, ($1) => {
    return $1.toUpperCase()
      .replace('-', '')
      .replace('_', '');
  }).replace(/^([A-Z])/, (firstChar) => firstChar.toLowerCase());
};

// Helper function to convert all keys of an object to camelCase (shallow)
const normalizeKeysCamelCaseShallow = (obj: Record<string, any>): Record<string, any> => {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }
  const newObj: Record<string, any> = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      newObj[toCamelCase(key)] = obj[key];
    }
  }
  return newObj;
};

// Helper to escape single quotes for Airtable formulas
function escapeAirtableValue(value: string): string {
  if (typeof value !== 'string') {
    return String(value);
  }
  return value.replace(/'/g, "\\'");
}

interface BuildingPoint {
  id: string;
  lat: number;
  lng: number;
}

// Define more specific types for canal and bridge points if their structure differs significantly
// For now, assuming they also have at least id, lat, lng.
interface CanalPoint {
  id: string;
  lat: number;
  lng: number;
  // edge?: { lat: number; lng: number }; // Example from API ref
}

interface BridgePoint {
  id: string;
  lat: number;
  lng: number;
  // edge?: { lat: number; lng: number }; // Example from API ref
  // connection?: any; // Example from API ref
}

interface PolygonData {
  id: string; // LandId
  buildingPoints?: BuildingPoint[];
  canalPoints?: CanalPoint[];
  bridgePoints?: BridgePoint[];
  // Add other polygon fields if needed, e.g., coordinates, center
}

async function fetchCitizenDetails(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const records = await airtable('CITIZENS').select({
      filterByFormula: `{Username} = '${escapeAirtableValue(username)}'`,
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching citizen details for ${username}:`, error);
    return null;
  }
}

async function fetchLastActivity(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const records = await airtable('ACTIVITIES').select({
      filterByFormula: `{Citizen} = '${escapeAirtableValue(username)}'`,
      sort: [{ field: 'EndDate', direction: 'desc' }], // Get the most recently ended or current
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching last activity for ${username}:`, error);
    return null;
  }
}

async function fetchOwnedLands(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const records = await airtable('LANDS').select({
      filterByFormula: `{Owner} = '${escapeAirtableValue(username)}'`,
    }).all();
    return [...records]; // Convert ReadonlyArray to Array
  } catch (error) {
    console.error(`Error fetching lands for ${username}:`, error);
    return [];
  }
}

async function fetchBuildingsOnLand(landId: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const records = await airtable('BUILDINGS').select({
      filterByFormula: `{LandId} = '${escapeAirtableValue(landId)}'`,
    }).all();
    return [...records]; // Convert ReadonlyArray to Array
  } catch (error) {
    console.error(`Error fetching buildings on land ${landId}:`, error);
    return [];
  }
}

async function fetchPolygonDataForLand(landId: string): Promise<PolygonData | null> {
  try {
    // Use the existing /api/lands endpoint as it merges polygon data
    // Or directly call /api/get-polygons if more suitable
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
    const response = await fetch(`${baseUrl}/api/lands?LandId=${encodeURIComponent(landId)}`);
    if (!response.ok) {
      console.error(`Failed to fetch polygon data for land ${landId} from /api/lands: ${response.status}`);
      return null;
    }
    const data = await response.json();
    if (data.success && data.lands && data.lands.length > 0) {
      // Assuming /api/lands returns buildingPoints in the desired format
      const landData = data.lands[0];
      return {
        id: landData.landId, // or landData.id
        buildingPoints: landData.buildingPoints || [],
        canalPoints: landData.canalPoints || [], // Add canalPoints
        bridgePoints: landData.bridgePoints || [], // Add bridgePoints
      };
    }
    console.warn(`No land data found for ${landId} via /api/lands`);
    return null;
  } catch (error) {
    console.error(`Error fetching polygon data for land ${landId}:`, error);
    return null;
  }
}

async function fetchOwnedBuildings(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const records = await airtable('BUILDINGS').select({
      filterByFormula: `{Owner} = '${escapeAirtableValue(username)}'`,
    }).all();
    return [...records]; // Convert ReadonlyArray to Array
  } catch (error) {
    console.error(`Error fetching buildings for ${username}:`, error);
    return [];
  }
}

async function fetchManagedBuildings(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const records = await airtable('BUILDINGS').select({
      filterByFormula: `{RunBy} = '${escapeAirtableValue(username)}'`,
    }).all();
    return [...records];
  } catch (error) {
    console.error(`Error fetching managed buildings for ${username}:`, error);
    return [];
  }
}

async function fetchWorkplaceBuilding(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    // A citizen typically has one primary workplace (Occupant) which is a business
    // If multiple are possible, logic might need adjustment (e.g., sort by UpdatedAt or specific type)
    const records = await airtable('BUILDINGS').select({
      filterByFormula: `AND({Occupant} = '${escapeAirtableValue(username)}', {Category} = 'business')`,
      maxRecords: 1, // Assuming one primary workplace as Occupant
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching workplace building for ${username}:`, error);
    return null;
  }
}

async function fetchHomeBuilding(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    // A citizen typically has one primary home (Occupant, Category=home)
    const records = await airtable('BUILDINGS').select({
      filterByFormula: `AND({Occupant} = '${escapeAirtableValue(username)}', {Category} = 'home')`,
      maxRecords: 1, 
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching home building for ${username}:`, error);
    return null;
  }
}

interface BuildingResourceDetails {
  // Define structure based on /api/building-resources/:buildingId response
  // This is a simplified version, expand as needed
  success: boolean;
  buildingId?: string;
  buildingType?: string;
  buildingName?: string;
  owner?: string;
  category?: string | null;
  subCategory?: string | null;
  canImport?: boolean;
  resources?: {
    stored?: any[];
    publiclySold?: any[];
    bought?: any[];
    sellable?: any[];
    storable?: any[];
    transformationRecipes?: any[];
  };
  storage?: {
    used?: number;
    capacity?: number;
  };
  error?: string;
}

async function fetchBuildingResourceDetails(buildingId: string): Promise<BuildingResourceDetails | null> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
    const response = await fetch(`${baseUrl}/api/building-resources/${encodeURIComponent(buildingId)}`);
    if (!response.ok) {
      console.error(`Failed to fetch resource details for building ${buildingId}: ${response.status}`);
      return { success: false, error: `Failed to fetch resource details: ${response.status}` };
    }
    const data = await response.json();
    return data as BuildingResourceDetails; // Assuming data matches the interface
  } catch (error) {
    console.error(`Error fetching resource details for building ${buildingId}:`, error);
    return null;
  }
}

async function fetchCitizenContracts(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await airtable('CONTRACTS').select({
      filterByFormula: `AND(OR({Buyer} = '${escapedUsername}', {Seller} = '${escapedUsername}'), {Status} = 'active')`,
    }).all();
    return [...records]; // Convert ReadonlyArray to Array
  } catch (error) {
    console.error(`Error fetching contracts for ${username}:`, error);
    return [];
  }
}

async function fetchGuildDetails(guildId: string): Promise<AirtableRecord<FieldSet> | null> {
  if (!guildId) return null;
  try {
    const records = await airtable('GUILDS').select({
      filterByFormula: `{GuildId} = '${escapeAirtableValue(guildId)}'`,
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching guild details for GuildId ${guildId}:`, error);
    return null;
  }
}

async function fetchCitizenLoans(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await airtable('LOANS').select({
      filterByFormula: `OR({Lender} = '${escapedUsername}', {Borrower} = '${escapedUsername}')`,
      sort: [{ field: 'CreatedAt', direction: 'desc' }], // Optional: sort by creation date
    }).all();
    return [...records]; // Convert ReadonlyArray to Array
  } catch (error) {
    console.error(`Error fetching loans for ${username}:`, error);
    return [];
  }
}

async function fetchCitizenRelationships(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    // Fetch all relationships involving the citizen
    const records = await airtable('RELATIONSHIPS').select({
      filterByFormula: `OR({Citizen1} = '${escapedUsername}', {Citizen2} = '${escapedUsername}')`,
    }).all();

    // Calculate combined score and sort
    const scoredRecords = records.map(record => {
      const strengthScore = Number(record.fields.StrengthScore) || 0;
      const trustScore = Number(record.fields.TrustScore) || 0;
      return { ...record, combinedScore: strengthScore + trustScore };
    });

    scoredRecords.sort((a, b) => b.combinedScore - a.combinedScore);
    
    // Map back to original AirtableRecord structure if combinedScore was only for sorting
    // and ensure it's a mutable array.
    return scoredRecords.slice(0, 20).map(r => {
      const { combinedScore, ...originalRecord } = r;
      return originalRecord as AirtableRecord<FieldSet>;
    });
  } catch (error) {
    console.error(`Error fetching relationships for ${username}:`, error);
    return [];
  }
}

async function fetchCitizenProblems(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await airtable('PROBLEMS').select({
      filterByFormula: `{Citizen} = '${escapedUsername}'`,
      sort: [{ field: 'CreatedAt', direction: 'desc' }],
      maxRecords: 20,
    }).all();
    return [...records]; // Convert ReadonlyArray to Array
  } catch (error) {
    console.error(`Error fetching problems for ${username}:`, error);
    return [];
  }
}

async function fetchCitizenMessages(username: string): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await airtable('MESSAGES').select({
      filterByFormula: `OR({Sender} = '${escapedUsername}', {Receiver} = '${escapedUsername}')`,
      sort: [{ field: 'CreatedAt', direction: 'desc' }],
      maxRecords: 10,
    }).all();
    return [...records]; // Convert ReadonlyArray to Array
  } catch (error) {
    console.error(`Error fetching messages for ${username}:`, error);
    return [];
  }
}

async function fetchLastDailyUpdate(): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const records = await airtable('MESSAGES').select({
      filterByFormula: `AND({Type} = 'daily_update', {Sender} = 'ConsiglioDeiDieci')`,
      sort: [{ field: 'CreatedAt', direction: 'desc' }],
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching last daily update:`, error);
    return null;
  }
}

interface ActiveStratagemsResult {
  executedBy: AirtableRecord<FieldSet>[];
  targetedAt: AirtableRecord<FieldSet>[];
}

async function fetchCitizenActiveStratagems(username: string): Promise<ActiveStratagemsResult> {
  const result: ActiveStratagemsResult = { executedBy: [], targetedAt: [] };
  try {
    const escapedUsername = escapeAirtableValue(username);
    const nowFilter = `OR({ExpiresAt} = BLANK(), IS_AFTER({ExpiresAt}, NOW()))`;

    // Stratagems executed by the citizen
    const executedByFormula = `
      AND(
        {ExecutedBy} = '${escapedUsername}',
        {Status} = 'active',
        ${nowFilter}
      )
    `.replace(/\s+/g, ' ');

    const executedByRecords = await airtable('STRATAGEMS').select({
      filterByFormula: executedByFormula,
      sort: [{ field: 'CreatedAt', direction: 'desc' }],
    }).all();
    result.executedBy = [...executedByRecords];

    // Stratagems targeting the citizen (and not executed by them, to avoid duplicates)
    const targetedAtFormula = `
      AND(
        {TargetCitizen} = '${escapedUsername}',
        NOT({ExecutedBy} = '${escapedUsername}'),
        {Status} = 'active',
        ${nowFilter}
      )
    `.replace(/\s+/g, ' ');

    const targetedAtRecords = await airtable('STRATAGEMS').select({
      filterByFormula: targetedAtFormula,
      sort: [{ field: 'CreatedAt', direction: 'desc' }],
    }).all();
    result.targetedAt = [...targetedAtRecords];

  } catch (error) {
    console.error(`Error fetching active stratagems for citizen ${username}:`, error);
  }
  return result;
}

interface StratagemParameter {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

interface StratagemDefinition {
  name: string;
  type: string;
  purpose: string;
  category: string | null;
  parameters: StratagemParameter[];
  description: string; // "How it Works"
  status: 'Implemented' | 'Coming Soon' | 'Partially Implemented';
  rawMarkdown: string; // For debugging or more detailed display
}

async function fetchStratagemDefinitions(): Promise<StratagemDefinition[]> {
  const definitions: StratagemDefinition[] = [
    {
      name: 'Undercut',
      type: 'undercut',
      purpose: "To strategically lower the selling prices of a citizen's goods to be cheaper than their competition for a specific resource type.",
      category: 'commerce',
      parameters: [
        { name: 'variant', type: 'string', required: true, description: 'Determines the aggressiveness: "Mild", "Standard", "Aggressive".' },
        { name: 'targetResourceType', type: 'string', required: true, description: 'The ID of the resource type to undercut.' },
        { name: 'targetCitizen', type: 'string', required: false, description: 'Specific competitor citizen to target.' },
        { name: 'targetBuilding', type: 'string', required: false, description: 'Specific competitor building to target.' },
        { name: 'durationHours', type: 'integer', required: false, description: 'How long the stratagem should remain active, in hours. Defaults to 24.' },
      ],
      description: "Identifies competitor prices for a resource and sets the executor's prices lower by a percentage based on the variant. Aims to capture market share.",
      status: 'Implemented',
      rawMarkdown: '',
    },
    {
      name: 'Coordinate Pricing',
      type: 'coordinate_pricing',
      purpose: "To align the selling prices of a citizen's goods with a target's prices (specific citizen or building) or with the general market average for a specific resource type.",
      category: 'commerce',
      parameters: [
        { name: 'targetCitizen', type: 'string', required: false, description: "Citizen whose prices will be the reference." },
        { name: 'targetBuilding', type: 'string', required: false, description: "Building whose sell contracts will be the reference." },
        { name: 'targetResourceType', type: 'string', required: false, description: "Resource type to coordinate. If omitted, all executor's selling resources are targeted." },
        { name: 'durationHours', type: 'integer', required: false, description: "How long the stratagem remains active. Defaults to 24." },
      ],
      description: "Adjusts the executor's selling prices for specified or all resources to match a target (citizen, building) or the market average. Can foster cooperation or stabilize prices.",
      status: 'Implemented',
      rawMarkdown: '',
    },
    {
      name: 'Hoard Resource',
      type: 'hoard_resource',
      purpose: "To systematically accumulate a specific resource type in a designated storage building.",
      category: 'commerce',
      parameters: [
        { name: 'targetResourceType', type: 'string', required: true, description: "The ID of the resource type to hoard." },
        { name: 'durationHours', type: 'integer', required: false, description: "How long the stratagem should remain active. Defaults to 72." },
        { name: 'storageContractTargetAmount', type: 'integer', required: false, description: "Target capacity for the storage_query contract. Defaults to a large number." },
      ],
      description: "Identifies storage, creates storage contracts, and tasks the executor and their employees to buy and store the target resource. Aims to create scarcity or prepare for future needs.",
      status: 'Implemented',
      rawMarkdown: '',
    },
    {
      name: 'Supplier Lockout',
      type: 'supplier_lockout',
      purpose: "To establish exclusive or priority supply agreements with specific resource suppliers.",
      category: 'commerce',
      parameters: [
        { name: 'targetResourceType', type: 'string', required: true, description: "Resource type for which to secure suppliers." },
        { name: 'targetSupplierCitizen', type: 'string', required: true, description: "Supplier citizen to target." },
        { name: 'premiumPercentage', type: 'integer', required: false, description: "Percentage above market price offered. Defaults to 15." },
        { name: 'contractDurationDays', type: 'integer', required: false, description: "Desired contract duration in days. Defaults to 30." },
      ],
      description: "Attempts to create long-term import contracts with a supplier, offering a premium for exclusivity or priority, securing supply and potentially hindering competitors.",
      status: 'Coming Soon',
      rawMarkdown: '',
    },
    {
      name: 'Political Campaign',
      type: 'political_campaign',
      purpose: "To influence governance by lobbying for or against a specific decree or policy change.",
      category: 'political',
      parameters: [
        { name: 'targetDecreeName', type: 'string', required: true, description: "Name/ID of the decree targeted." },
        { name: 'desiredOutcome', type: 'string', required: true, description: "Desired outcome (e.g., 'pass', 'repeal')." },
        { name: 'campaignMessage', type: 'string', required: true, description: "Core message of the campaign." },
        { name: 'lobbyingBudget', type: 'integer', required: false, description: "Ducats for lobbying. Defaults to 0." },
        { name: 'campaignDurationDays', type: 'integer', required: false, description: "Campaign duration. Defaults to 14." },
      ],
      description: "Uses influence and Ducats to send messages, sway opinions, and potentially propose or alter decrees, impacting relationships and potentially game rules.",
      status: 'Coming Soon',
      rawMarkdown: '',
    },
    {
      name: 'Reputation Assault',
      type: 'reputation_assault',
      purpose: "To damage a competitor's business relationships and trustworthiness by spreading negative information.",
      category: 'personal',
      parameters: [
        { name: 'targetCitizen', type: 'string', required: true, description: "Competitor citizen whose reputation is targeted." },
        { name: 'durationHours', type: 'integer', required: false, description: "How long the stratagem remains active. Defaults to 24 (current implementation is one-shot)." },
      ],
      description: "Generates and sends unique, AI-crafted negative messages from the executor to associates of the target citizen, aiming to reduce trust in the target.",
      status: 'Implemented',
      rawMarkdown: '',
    },
    {
      name: 'Emergency Liquidation',
      type: 'emergency_liquidation',
      purpose: "To quickly convert a citizen's owned inventory into cash, albeit at potentially below-market rates.",
      category: 'commerce',
      parameters: [
        { name: 'variant', type: 'string', required: true, description: 'Determines discount and duration: "Mild" (20% off, 24h), "Standard" (30% off, 48h), "Aggressive" (40% off, 72h).' },
      ],
      description: "Lists all items in the executor's inventory for sale at a discounted price based on the variant. Aims for rapid cash generation.",
      status: 'Implemented',
      rawMarkdown: '',
    },
    {
        name: 'Cultural Patronage',
        type: 'cultural_patronage',
        purpose: 'To build social capital and enhance reputation by sponsoring artists, performances, or cultural institutions.',
        category: 'social',
        parameters: [
            { name: 'targetArtist', type: 'string', required: false, description: 'Username of the artist to patronize.' },
            { name: 'targetPerformanceId', type: 'string', required: false, description: 'ID of a specific performance to sponsor.' },
            { name: 'targetInstitutionId', type: 'string', required: false, description: 'BuildingId of a cultural institution to support.' },
            { name: 'patronageLevel', type: 'string', required: false, description: 'Scale of patronage: "Modest", "Standard", "Grand". Defaults to "Standard".' },
            { name: 'durationHours', type: 'integer', required: false, description: 'Duration of active effects. Defaults to 168 (7 days).' },
        ],
        description: 'Funds cultural endeavors to improve relationships, influence, and potentially lead to new artworks or events.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Information Network',
        type: 'information_network',
        purpose: 'To establish intelligence gathering operations targeting specific citizens or market sectors.',
        category: 'security',
        parameters: [
            { name: 'targetCitizens', type: 'List[string]', required: false, description: 'Usernames of citizens to target.' },
            { name: 'targetSectors', type: 'List[string]', required: false, description: 'Market sectors or geographical areas to target.' },
            { name: 'durationHours', type: 'integer', required: false, description: 'Duration of intelligence benefits. Defaults to 168 (7 days).' },
        ],
        description: 'Simulates informant recruitment to provide advanced notifications and relevancies about competitor strategies and market movements.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Maritime Blockade',
        type: 'maritime_blockade',
        purpose: "To control water access to cripple a competitor's trade and waterfront operations.",
        category: 'warfare',
        parameters: [
            { name: 'targetCompetitorBuilding', type: 'string', required: false, description: "Competitor's waterfront building ID." },
            { name: 'targetCompetitorCitizen', type: 'string', required: false, description: 'Username of the competitor to target.' },
            { name: 'durationHours', type: 'integer', required: false, description: 'Duration of the blockade. Defaults to 72 (3 days).' },
        ],
        description: 'Coordinates with allied entities to restrict a competitor’s access to waterways and docks, disrupting their trade.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Theater Conspiracy',
        type: 'theater_conspiracy',
        purpose: 'To manipulate public opinion and political narratives by commissioning and staging theatrical performances with specific themes.',
        category: 'social',
        parameters: [
            { name: 'targetTheaterId', type: 'string', required: true, description: 'BuildingId of the theater for the performance.' },
            { name: 'politicalTheme', type: 'string', required: true, description: 'Theme of the play (e.g., "satirize_competitor").' },
            { name: 'targetCompetitor', type: 'string', required: false, description: 'Competitor to satirize (if applicable).' },
            { name: 'durationHours', type: 'integer', required: false, description: "Duration of the stratagem's influence. Defaults to 168 (7 days)." },
        ],
        description: 'Commissions and stages plays with specific political messages to sway public opinion and impact relationships.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Printing Propaganda',
        type: 'printing_propaganda',
        purpose: 'To conduct information warfare against competitors by mass-producing and distributing pamphlets and rumors.',
        category: 'political',
        parameters: [
            { name: 'targetPrintingHouseId', type: 'string', required: true, description: 'BuildingId of the printing house to use.' },
            { name: 'targetCompetitor', type: 'string', required: true, description: 'Competitor to target with propaganda.' },
            { name: 'propagandaTheme', type: 'string', required: false, description: 'Theme of the propaganda. Defaults to "General Disinformation".' },
            { name: 'durationHours', type: 'integer', required: false, description: "Duration of the stratagem's influence. Defaults to 168 (7 days)." },
        ],
        description: 'Uses a printing house to produce and distribute materials aimed at damaging a competitor’s reputation.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Cargo "Mishap"',
        type: 'cargo_mishap',
        purpose: 'To sabotage a competitor\'s shipment by arranging for their goods to "disappear" while in transit.',
        category: 'warfare',
        parameters: [
            { name: 'targetContractId', type: 'string', required: true, description: 'ContractId of the shipment to target.' },
            { name: 'durationHours', type: 'integer', required: false, description: 'Window of opportunity. Defaults to 24 hours.' },
        ],
        description: 'Simulates an interception of a competitor’s cargo, causing loss of goods and potential contract failure, with a risk of discovery.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Marketplace Gossip',
        type: 'marketplace_gossip',
        purpose: "To subtly damage a competitor's reputation by spreading rumors through social networks.",
        category: 'personal',
        parameters: [
            { name: 'targetCitizen', type: 'string', required: true, description: 'Competitor to target.' },
            { name: 'gossipTheme', type: 'string', required: false, description: 'Theme of the gossip. Defaults to "General Rumors".' },
            { name: 'durationHours', type: 'integer', required: false, description: "Duration of influence. Defaults to 48 (2 days)." },
        ],
        description: 'Initiates activities to spread rumors in social hubs, aiming to negatively impact the target’s relationships through widespread, subtle messaging.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Employee Poaching',
        type: 'employee_poaching',
        purpose: 'To recruit a skilled employee from a competitor by making them a better offer.',
        category: 'personal',
        parameters: [
            { name: 'targetEmployeeUsername', type: 'string', required: true, description: 'Employee to poach.' },
            { name: 'targetCompetitorUsername', type: 'string', required: true, description: 'Current employer.' },
            { name: 'jobOfferDetails', type: 'string', required: false, description: 'Brief description of the job offer.' },
            { name: 'durationHours', type: 'integer', required: false, description: 'Duration for offer consideration. Defaults to 48 (2 days).' },
        ],
        description: 'Sends a job offer to a competitor’s employee, potentially leading to their recruitment and impacting relationships.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Joint Venture',
        type: 'joint_venture',
        purpose: 'To propose a formal business partnership with another citizen, defining contributions and profit-sharing.',
        category: 'commerce',
        parameters: [
            { name: 'targetPartnerUsername', type: 'string', required: true, description: 'Citizen to propose the venture to.' },
            { name: 'ventureDetails', type: 'string', required: true, description: 'Detailed description of the venture.' },
            { name: 'profitSharingPercentage', type: 'float', required: false, description: 'Profit share for the initiator. Defaults to 0.5.' },
            { name: 'durationDays', type: 'integer', required: false, description: 'Duration of the venture. Defaults to 30 days.' },
        ],
        description: 'Proposes a partnership to another citizen. If accepted, creates a joint venture contract and can lead to shared profits and improved relations.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Financial Patronage',
        type: 'financial_patronage',
        purpose: 'To provide comprehensive financial support to promising individuals or loyal allies, creating deep personal bonds.',
        category: 'personal',
        parameters: [
            { name: 'targetCitizenUsername', type: 'string', required: true, description: 'Citizen to receive patronage.' },
            { name: 'patronageLevel', type: 'string', required: false, description: 'Level of support ("Modest", "Standard", "Generous"). Defaults to "Standard".' },
            { name: 'durationDays', type: 'integer', required: false, description: 'Duration of patronage. Defaults to 90 days.' },
        ],
        description: 'Provides ongoing financial aid to a target citizen, significantly boosting relationships and potentially creating loyalty, at a Ducat cost to the executor.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Neighborhood Watch',
        type: 'neighborhood_watch',
        purpose: 'To enhance security and reduce crime in a specific district through collective citizen vigilance.',
        category: 'security',
        parameters: [
            { name: 'districtName', type: 'string', required: true, description: 'District for the neighborhood watch.' },
        ],
        description: 'Establishes a watch in a district, aiming to reduce minor crime rates and improve community relations among participants. Active for 45 days.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Monopoly Pricing',
        type: 'monopoly_pricing',
        purpose: 'To leverage dominant market position to significantly increase prices for a specific resource.',
        category: 'commerce',
        parameters: [
            { name: 'targetResourceType', type: 'string', required: true, description: 'Resource to apply monopoly pricing to.' },
            { name: 'variant', type: 'string', required: true, description: 'Price escalation level: "Mild" (150%), "Standard" (200%), "Aggressive" (300%).' },
            { name: 'durationHours', type: 'integer', required: false, description: 'Duration to maintain prices. Defaults to 168 (7 days).' },
        ],
        description: 'Inflates prices for a resource where the executor has market dominance, increasing profits but potentially harming consumers and relationships.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Reputation Boost',
        type: 'reputation_boost',
        purpose: "To actively improve a target citizen's public image and trustworthiness through positive messaging.",
        category: 'personal',
        parameters: [
            { name: 'targetCitizenUsername', type: 'string', required: true, description: "Citizen whose reputation is to be boosted." },
            { name: 'campaignIntensity', type: 'string', required: false, description: 'Intensity: "Modest", "Standard", "Intense". Defaults to "Standard".' },
            { name: 'campaignDurationDays', type: 'integer', required: false, description: 'Campaign duration. Defaults to 30 days.' },
            { name: 'campaignBudget', type: 'integer', required: false, description: 'Ducats for campaign expenses.' },
        ],
        description: 'Launches a campaign to improve a target citizen’s reputation through positive messages and simulated events, costing Ducats and influence.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Canal Mugging',
        type: 'canal_mugging',
        purpose: 'To rob a specific citizen while they are traveling by gondola, stealing Ducats and potentially resources.',
        category: 'warfare',
        parameters: [
            { name: 'targetCitizenUsername', type: 'string', required: true, description: 'Citizen to target.' },
            { name: 'targetActivityId', type: 'string', required: false, description: 'Specific travel activity ID to intercept.' },
        ],
        description: 'Attempts to ambush and rob a citizen during gondola travel, with high risk of legal consequences and relationship damage.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Burglary',
        type: 'burglary',
        purpose: "To steal tools, materials, or finished goods from a competitor's production building.",
        category: 'warfare',
        parameters: [
            { name: 'targetBuildingId', type: 'string', required: true, description: "Competitor's production building to target." },
        ],
        description: 'Attempts to break into a competitor’s building to steal resources, risking detection and severe penalties.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Employee Corruption',
        type: 'employee_corruption',
        purpose: 'To bribe employees of businesses to reduce productivity and/or steal resources for the executor.',
        category: 'warfare',
        parameters: [
            { name: 'targetEmployeeUsername', type: 'string', required: true, description: 'Employee to corrupt.' },
            { name: 'targetBuildingId', type: 'string', required: true, description: 'Business where the employee works.' },
            { name: 'corruptionGoal', type: 'string', required: false, description: 'Goal: "reduce_productivity", "steal_resources", "both". Defaults to "both".' },
            { name: 'bribeAmountPerPeriod', type: 'integer', required: false, description: 'Periodic bribe amount. Defaults based on class/risk.' },
            { name: 'durationDays', type: 'integer', required: false, description: 'Duration of the scheme. Defaults to 30 days.' },
        ],
        description: 'Bribes a competitor’s employee to sabotage operations or steal goods, with ongoing costs and risk of discovery.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Arson',
        type: 'arson',
        purpose: 'To destroy a target building or business operation by setting it on fire.',
        category: 'warfare',
        parameters: [
            { name: 'targetBuildingId', type: 'string', required: true, description: 'Building to target for arson.' },
        ],
        description: 'Attempts to burn down a target building, causing major destruction but carrying extreme risks of detection and severe punishment.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Charity Distribution',
        type: 'charity_distribution',
        purpose: 'To anonymously distribute Ducats to poor citizens in a specific district, improving general sentiment.',
        category: 'social',
        parameters: [
            { name: 'targetDistrict', type: 'string', required: true, description: 'District for charity distribution.' },
            { name: 'totalDucatsToDistribute', type: 'integer', required: true, description: 'Total Ducats to distribute.' },
            { name: 'numberOfRecipients', type: 'integer', required: false, description: 'Approximate number of recipients. Defaults to 5-10.' },
        ],
        description: 'Anonymously gives Ducats to poor citizens in a district, costing Ducats upfront for a subtle reputation and sentiment boost.',
        status: 'Coming Soon',
        rawMarkdown: '',
    },
    {
        name: 'Festival Organisation',
        type: 'festival_organisation',
        purpose: "To organize and sponsor a public festival, boosting community morale and the organizer's reputation.",
        category: 'social',
        parameters: [
            { name: 'targetDistrict', type: 'string', required: true, description: 'District for the festival.' },
            { name: 'festivalTheme', type: 'string', required: false, description: 'Theme of the festival. Defaults to "General Merriment".' },
            { name: 'festivalBudget', type: 'integer', required: true, description: 'Total Ducats for festival expenses.' },
            { name: 'durationDays', type: 'integer', required: false, description: 'Duration of the festival. Defaults to 1 day.' },
        ],
        description: 'Funds and organizes a public festival, significantly boosting reputation, relationships, and community morale at a Ducat cost.',
        status: 'Coming Soon',
        rawMarkdown: '',
    }
  ];
  return Promise.resolve(definitions);
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const citizenUsername = searchParams.get('citizenUsername');

  if (!citizenUsername) {
    return NextResponse.json({ success: false, error: 'citizenUsername parameter is required' }, { status: 400 });
  }

  try {
    const citizenRecord = await fetchCitizenDetails(citizenUsername);
    if (!citizenRecord) {
      return NextResponse.json({ success: false, error: `Citizen ${citizenUsername} not found` }, { status: 404 });
    }

    const lastActivityRecord = await fetchLastActivity(citizenUsername);
    const ownedLandsRecords = await fetchOwnedLands(citizenUsername);
    const ownedBuildingsRecords = await fetchOwnedBuildings(citizenUsername);
    const managedBuildingsRecords = await fetchManagedBuildings(citizenUsername);
    const workplaceBuildingRecord = await fetchWorkplaceBuilding(citizenUsername);
    const homeBuildingRecord = await fetchHomeBuilding(citizenUsername);

    const ownedLandsData = [];
    for (const landRecord of ownedLandsRecords) {
      const landId = landRecord.fields.LandId as string;
      if (!landId) continue;

      const buildingsOnLandRecords = await fetchBuildingsOnLand(landId);
      const polygonData = await fetchPolygonDataForLand(landId);

      let unoccupiedBuildingPoints: BuildingPoint[] = [];
      let unoccupiedCanalPoints: CanalPoint[] = [];
      let unoccupiedBridgePoints: BridgePoint[] = [];

      const occupiedBuildingPointIds = new Set<string>();
      const occupiedCanalPointIds = new Set<string>();
      const occupiedBridgePointIds = new Set<string>();

      buildingsOnLandRecords.forEach(bldg => {
        const pointField = bldg.fields.Point;
        const buildingType = (bldg.fields.Type as string || '').toLowerCase();

        const addPointsToSet = (points: unknown, set: Set<string>) => {
          if (typeof points === 'string') {
            set.add(points);
          } else if (Array.isArray(points)) {
            points.forEach(p => {
              if (typeof p === 'string') {
                set.add(p);
              } else {
                // console.warn(`Non-string element in point array: ${p}`);
              }
            });
          } else {
            // console.warn(`Unexpected pointField type: ${typeof points}`, points);
          }
        };

        if (buildingType === 'dock') {
          addPointsToSet(pointField, occupiedCanalPointIds);
        } else if (buildingType === 'bridge' || buildingType === 'rialto_bridge') {
          addPointsToSet(pointField, occupiedBridgePointIds);
        } else {
          // Assume other buildings occupy buildingPoints
          addPointsToSet(pointField, occupiedBuildingPointIds);
        }
      });

      if (polygonData) {
        if (polygonData.buildingPoints) {
          unoccupiedBuildingPoints = polygonData.buildingPoints.filter(bp => !occupiedBuildingPointIds.has(bp.id));
        }
        if (polygonData.canalPoints) {
          unoccupiedCanalPoints = polygonData.canalPoints.filter(cp => !occupiedCanalPointIds.has(cp.id));
        }
        if (polygonData.bridgePoints) {
          unoccupiedBridgePoints = polygonData.bridgePoints.filter(bp => !occupiedBridgePointIds.has(bp.id));
        }
      }
      
      ownedLandsData.push({
        ...normalizeKeysCamelCaseShallow(landRecord.fields),
        airtableId: landRecord.id,
        buildings: buildingsOnLandRecords.map(b => ({...normalizeKeysCamelCaseShallow(b.fields), airtableId: b.id})),
        unoccupiedBuildingPoints: unoccupiedBuildingPoints,
        totalBuildingPoints: polygonData?.buildingPoints?.length || 0,
        unoccupiedCanalPoints: unoccupiedCanalPoints,
        totalCanalPoints: polygonData?.canalPoints?.length || 0,
        unoccupiedBridgePoints: unoccupiedBridgePoints,
        totalBridgePoints: polygonData?.bridgePoints?.length || 0,
      });
    }

    const dataPackage = {
      citizen: {...normalizeKeysCamelCaseShallow(citizenRecord.fields), airtableId: citizenRecord.id},
      lastActivity: lastActivityRecord ? {...normalizeKeysCamelCaseShallow(lastActivityRecord.fields), airtableId: lastActivityRecord.id} : null,
      ownedLands: ownedLandsData,
      ownedBuildings: [] as any[],
      managedBuildings: [] as any[],
      workplaceBuilding: null as any | null,
      homeBuilding: null as any | null, // Initialize homeBuilding
      activeContracts: [] as any[],
      guildDetails: null as any | null,
      citizenLoans: [] as any[],
      strongestRelationships: [] as any[], // Initialize strongestRelationships array
      recentProblems: [] as any[], // Initialize recentProblems array
      recentMessages: [] as any[], // Initialize recentMessages array
      latestDailyUpdate: null as any | null, // Initialize latestDailyUpdate
      availableStratagems: [] as StratagemDefinition[], // Initialize availableStratagems
      stratagemsExecutedByCitizen: [] as any[], // Stratagems executed by the citizen
      stratagemsTargetingCitizen: [] as any[], // Stratagems targeting the citizen
    };

    // Fetch and add available stratagems (definitions)
    dataPackage.availableStratagems = await fetchStratagemDefinitions();

    // Fetch and add active stratagems involving the citizen
    const activeStratagemsResult = await fetchCitizenActiveStratagems(citizenUsername);
    dataPackage.stratagemsExecutedByCitizen = activeStratagemsResult.executedBy.map(s => ({...normalizeKeysCamelCaseShallow(s.fields), airtableId: s.id}));
    dataPackage.stratagemsTargetingCitizen = activeStratagemsResult.targetedAt.map(s => ({...normalizeKeysCamelCaseShallow(s.fields), airtableId: s.id}));

    // Fetch and add active contracts
    const activeContractsRecords = await fetchCitizenContracts(citizenUsername);
    dataPackage.activeContracts = activeContractsRecords.map(c => ({...normalizeKeysCamelCaseShallow(c.fields), airtableId: c.id}));

    // Fetch and add guild details if GuildId exists
    const guildId = citizenRecord.fields.GuildId as string;
    if (guildId) {
      const guildRecord = await fetchGuildDetails(guildId);
      if (guildRecord) {
        dataPackage.guildDetails = {...normalizeKeysCamelCaseShallow(guildRecord.fields), airtableId: guildRecord.id};
      }
    }

    // Fetch and add citizen loans
    const citizenLoansRecords = await fetchCitizenLoans(citizenUsername);
    dataPackage.citizenLoans = citizenLoansRecords.map(l => ({...normalizeKeysCamelCaseShallow(l.fields), airtableId: l.id}));

    // Add managed buildings to dataPackage
    dataPackage.managedBuildings = managedBuildingsRecords.map(b => ({...normalizeKeysCamelCaseShallow(b.fields), airtableId: b.id}));

    // Add workplace building to dataPackage
    if (workplaceBuildingRecord) {
      dataPackage.workplaceBuilding = {...normalizeKeysCamelCaseShallow(workplaceBuildingRecord.fields), airtableId: workplaceBuildingRecord.id};
    }

    // Add home building to dataPackage
    if (homeBuildingRecord) {
      dataPackage.homeBuilding = {...normalizeKeysCamelCaseShallow(homeBuildingRecord.fields), airtableId: homeBuildingRecord.id};
    }

    // Fetch and add strongest relationships
    const strongestRelationshipsRecords = await fetchCitizenRelationships(citizenUsername);
    dataPackage.strongestRelationships = strongestRelationshipsRecords.map(r => {
      const normalized = normalizeKeysCamelCaseShallow(r.fields);
      // combinedScore was added temporarily for sorting, remove if not needed in final package
      // or keep if useful client-side. For now, let's assume it's not part of the final schema.
      // delete (r as any).combinedScore; // This would modify the original if not careful
      const { combinedScore, ...fieldsWithoutCombinedScore } = normalized; // Exclude combinedScore from final object
      return {...fieldsWithoutCombinedScore, airtableId: r.id};
    });
    
    // Fetch and add recent problems
    const recentProblemsRecords = await fetchCitizenProblems(citizenUsername);
    dataPackage.recentProblems = recentProblemsRecords.map(p => ({...normalizeKeysCamelCaseShallow(p.fields), airtableId: p.id}));

    // Fetch and add recent messages
    const recentMessagesRecords = await fetchCitizenMessages(citizenUsername);
    dataPackage.recentMessages = recentMessagesRecords.map(m => ({...normalizeKeysCamelCaseShallow(m.fields), airtableId: m.id}));

    // Fetch and add the last daily update
    const lastDailyUpdateRecord = await fetchLastDailyUpdate();
    if (lastDailyUpdateRecord) {
      dataPackage.latestDailyUpdate = {...normalizeKeysCamelCaseShallow(lastDailyUpdateRecord.fields), airtableId: lastDailyUpdateRecord.id};
    }

    for (const buildingRecord of ownedBuildingsRecords) {
      const buildingId = buildingRecord.fields.BuildingId as string;
      if (!buildingId) continue;

      const resourceDetails = await fetchBuildingResourceDetails(buildingId);
      const normalizedBuildingFields = normalizeKeysCamelCaseShallow(buildingRecord.fields);
      
      dataPackage.ownedBuildings.push({
        ...normalizedBuildingFields,
        airtableId: buildingRecord.id,
        resourceDetails: resourceDetails // Add resource details
      });
    }

    return NextResponse.json({ success: true, data: dataPackage });

  } catch (error: any) {
    console.error(`[API get-data-package] Error for ${citizenUsername}:`, error);
    return NextResponse.json({ success: false, error: error.message || 'Failed to fetch data package' }, { status: 500 });
  }
}

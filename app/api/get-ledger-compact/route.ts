import { NextRequest, NextResponse } from 'next/server';
import Airtable, { FieldSet, Record as AirtableRecord } from 'airtable';

// Airtable Configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

// Cache configuration
const COMPACT_LEDGER_CACHE: Record<string, { data: any, timestamp: number }> = {};
const COMPACT_LEDGER_CACHE_TTL = 3 * 60 * 1000; // 3 minutes in milliseconds

// Lazy initialization of Airtable client
let airtable: any = null;

function getAirtable() {
  if (!airtable) {
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      throw new Error('Airtable API key or Base ID is not configured in environment variables.');
    }
    airtable = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);
  }
  return airtable;
}

// Helper to escape values for Airtable formulas
function escapeAirtableValue(value: string): string {
  return value.replace(/'/g, "\\'");
}

// Helper to convert field names to camelCase
const toCamelCase = (s: string) => {
  if (!s) return s;
  return s.replace(/([-_][a-z])/ig, ($1) => {
    return $1.toUpperCase()
      .replace('-', '')
      .replace('_', '');
  });
};

function normalizeKeysCamelCaseShallow(obj: any): any {
  if (!obj) return obj;
  
  const normalized: any = {};
  for (const key in obj) {
    const camelKey = key.includes('_') || key.includes('-') 
      ? toCamelCase(key) 
      : key.charAt(0).toLowerCase() + key.slice(1);
    normalized[camelKey] = obj[key];
  }
  return normalized;
}

async function fetchCitizenDetails(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await getAirtable()('CITIZENS').select({
      filterByFormula: `{Username} = '${escapedUsername}'`,
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching citizen ${username}:`, error);
    return null;
  }
}

async function fetchCurrentActivity(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await getAirtable()('ACTIVITIES').select({
      filterByFormula: `AND({Owner} = '${escapedUsername}', OR({Status} = 'created', {Status} = 'in_progress'))`,
      sort: [{ field: 'CreatedAt', direction: 'desc' }],
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching current activity for ${username}:`, error);
    return null;
  }
}

async function fetchLastCompletedActivity(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await getAirtable()('ACTIVITIES').select({
      filterByFormula: `AND({Owner} = '${escapedUsername}', {Status} = 'processed')`,
      sort: [{ field: 'EndDate', direction: 'desc' }],
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching last completed activity for ${username}:`, error);
    return null;
  }
}

async function fetchWorkplaceBuilding(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await getAirtable()('BUILDINGS').select({
      filterByFormula: `{RunBy} = '${escapedUsername}'`,
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching workplace for ${username}:`, error);
    return null;
  }
}

async function fetchHomeBuilding(username: string): Promise<AirtableRecord<FieldSet> | null> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await getAirtable()('BUILDINGS').select({
      filterByFormula: `{Occupant} = '${escapedUsername}'`,
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching home for ${username}:`, error);
    return null;
  }
}

async function fetchTopRelationships(username: string, limit: number = 3): Promise<AirtableRecord<FieldSet>[]> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const formula = `OR({Citizen1} = '${escapedUsername}', {Citizen2} = '${escapedUsername}')`;
    
    const records = await getAirtable()('RELATIONSHIPS').select({
      filterByFormula: formula,
      sort: [
        { field: 'TrustScore', direction: 'desc' },
        { field: 'StrengthScore', direction: 'desc' }
      ],
      maxRecords: limit,
    }).all();
    
    return [...records];
  } catch (error) {
    console.error(`Error fetching relationships for ${username}:`, error);
    return [];
  }
}

async function countOwnedLands(username: string): Promise<number> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await getAirtable()('LANDS').select({
      filterByFormula: `{Owner} = '${escapedUsername}'`,
      fields: ['LandId'],
    }).all();
    return records.length;
  } catch (error) {
    console.error(`Error counting lands for ${username}:`, error);
    return 0;
  }
}

async function countOwnedBuildings(username: string): Promise<number> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    const records = await getAirtable()('BUILDINGS').select({
      filterByFormula: `{Owner} = '${escapedUsername}'`,
      fields: ['BuildingId'],
    }).all();
    return records.length;
  } catch (error) {
    console.error(`Error counting buildings for ${username}:`, error);
    return 0;
  }
}

async function countActiveContracts(username: string): Promise<{ selling: number; buying: number }> {
  try {
    const escapedUsername = escapeAirtableValue(username);
    
    // Count selling contracts
    const sellingRecords = await getAirtable()('CONTRACTS').select({
      filterByFormula: `AND({SellerUsername} = '${escapedUsername}', {Type} = 'public', {IsCompleted} != TRUE(), {IsCancelled} != TRUE())`,
      fields: ['ContractId'],
    }).all();
    
    // Count buying contracts
    const buyingRecords = await getAirtable()('CONTRACTS').select({
      filterByFormula: `AND({BuyerUsername} = '${escapedUsername}', {Type} = 'public', {IsCompleted} != TRUE(), {IsCancelled} != TRUE())`,
      fields: ['ContractId'],
    }).all();
    
    return {
      selling: sellingRecords.length,
      buying: buyingRecords.length
    };
  } catch (error) {
    console.error(`Error counting contracts for ${username}:`, error);
    return { selling: 0, buying: 0 };
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const citizenUsername = searchParams.get('citizenUsername');
  const forceRefresh = searchParams.get('forceRefresh') === 'true';

  if (!citizenUsername) {
    return NextResponse.json({ success: false, error: 'citizenUsername parameter is required' }, { status: 400 });
  }

  // Validate Airtable configuration
  if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
    console.error('[API get-ledger-compact] Airtable API key or Base ID is not configured');
    return NextResponse.json({ success: false, error: 'Server configuration error' }, { status: 500 });
  }

  // Check cache if not forcing refresh
  const now = Date.now();
  const cacheKey = citizenUsername;
  
  if (!forceRefresh && COMPACT_LEDGER_CACHE[cacheKey] && (now - COMPACT_LEDGER_CACHE[cacheKey].timestamp < COMPACT_LEDGER_CACHE_TTL)) {
    console.log(`[API get-ledger-compact] Using cached ledger for ${citizenUsername} (age: ${Math.round((now - COMPACT_LEDGER_CACHE[cacheKey].timestamp) / 1000)} seconds)`);
    return NextResponse.json({ 
      success: true, 
      data: COMPACT_LEDGER_CACHE[cacheKey].data, 
      fromCache: true 
    });
  }

  try {
    // Fetch citizen details first
    const citizenRecord = await fetchCitizenDetails(citizenUsername);
    if (!citizenRecord) {
      return NextResponse.json({ success: false, error: `Citizen ${citizenUsername} not found` }, { status: 404 });
    }

    // Parse position
    let position = null;
    if (citizenRecord.fields.Position) {
      try {
        position = JSON.parse(citizenRecord.fields.Position as string);
      } catch (e) {
        console.warn(`Could not parse citizen position: ${citizenRecord.fields.Position}`);
      }
    }

    // Fetch all other data in parallel
    const [
      currentActivity,
      lastCompletedActivity,
      workplace,
      home,
      topRelationships,
      landCount,
      buildingCount,
      contractCounts
    ] = await Promise.all([
      fetchCurrentActivity(citizenUsername),
      fetchLastCompletedActivity(citizenUsername),
      fetchWorkplaceBuilding(citizenUsername),
      fetchHomeBuilding(citizenUsername),
      fetchTopRelationships(citizenUsername, 3),
      countOwnedLands(citizenUsername),
      countOwnedBuildings(citizenUsername),
      countActiveContracts(citizenUsername)
    ]);

    // Build compact ledger
    const compactLedger = {
      citizen: {
        username: citizenRecord.fields.Username,
        firstName: citizenRecord.fields.FirstName,
        lastName: citizenRecord.fields.LastName,
        socialClass: citizenRecord.fields.SocialClass,
        ducats: citizenRecord.fields.Ducats || 0,
        influence: citizenRecord.fields.Influence || 0,
        position: position,
        isAI: citizenRecord.fields.IsAI || false,
        primaryJob: citizenRecord.fields.PrimaryJob,
        // Mood fields
        mood: citizenRecord.fields.ComplexMood || 'neutral',
        moodIntensity: citizenRecord.fields.MoodIntensity || 5,
        primaryEmotion: citizenRecord.fields.PrimaryEmotion || 'neutral',
      },
      currentActivity: currentActivity ? {
        type: currentActivity.fields.Type,
        title: currentActivity.fields.Title,
        status: currentActivity.fields.Status,
        startDate: currentActivity.fields.StartDate,
        description: currentActivity.fields.Description
      } : null,
      lastCompletedActivity: lastCompletedActivity ? {
        type: lastCompletedActivity.fields.Type,
        title: lastCompletedActivity.fields.Title,
        endDate: lastCompletedActivity.fields.EndDate,
        thought: lastCompletedActivity.fields.Thought
      } : null,
      workplace: workplace ? {
        name: workplace.fields.Name || workplace.fields.Type,
        buildingId: workplace.fields.BuildingId,
        category: workplace.fields.Category
      } : null,
      home: home ? {
        name: home.fields.Name || home.fields.Type,
        buildingId: home.fields.BuildingId,
        category: home.fields.Category
      } : null,
      topRelationships: topRelationships.map(rel => {
        const otherCitizen = rel.fields.Citizen1 === citizenUsername ? rel.fields.Citizen2 : rel.fields.Citizen1;
        return {
          citizen: otherCitizen,
          trustScore: rel.fields.TrustScore || 0,
          strengthScore: rel.fields.StrengthScore || 0
        };
      }),
      counts: {
        ownedLands: landCount,
        ownedBuildings: buildingCount,
        activeSellingContracts: contractCounts.selling,
        activeBuyingContracts: contractCounts.buying
      }
    };

    // Cache the result
    COMPACT_LEDGER_CACHE[cacheKey] = {
      data: compactLedger,
      timestamp: now
    };

    return NextResponse.json({ 
      success: true, 
      data: compactLedger 
    });

  } catch (error) {
    console.error('[API get-ledger-compact] Error:', error);
    return NextResponse.json({ 
      success: false, 
      error: 'Internal server error' 
    }, { status: 500 });
  }
}
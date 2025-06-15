import { NextResponse } from 'next/server';
import { NextRequest } from 'next/server';
import Airtable, { FieldSet, Record as AirtableRecord } from 'airtable';

// Airtable Configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
  throw new Error('Airtable API key or Base ID is not configured in environment variables.');
}

const airtable = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

// Helper to escape single quotes for Airtable formulas
function escapeAirtableValue(value: string): string {
  if (typeof value !== 'string') {
    return String(value);
  }
  return value.replace(/'/g, "\\'");
}

// Helper function to convert all keys of an object to camelCase (shallow)
const normalizeKeysCamelCaseShallow = (obj: Record<string, any>): Record<string, any> => {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }
  const newObj: Record<string, any> = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const camelKey = key.charAt(0).toLowerCase() + key.slice(1);
      newObj[camelKey] = obj[key];
    }
  }
  return newObj;
};

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const lat = searchParams.get('lat');
    const lng = searchParams.get('lng');
    const positionJson = searchParams.get('position');
    
    let position: { lat: number, lng: number } | null = null;
    
    // Parse position from different possible inputs
    if (positionJson) {
      try {
        position = JSON.parse(positionJson);
      } catch (e) {
        return NextResponse.json({ 
          success: false, 
          error: 'Invalid position JSON format' 
        }, { status: 400 });
      }
    } else if (lat && lng) {
      position = { 
        lat: parseFloat(lat), 
        lng: parseFloat(lng) 
      };
    } else {
      return NextResponse.json({ 
        success: false, 
        error: 'Position parameters required (either lat & lng, or position JSON)' 
      }, { status: 400 });
    }
    
    if (!position || isNaN(position.lat) || isNaN(position.lng)) {
      return NextResponse.json({ 
        success: false, 
        error: 'Invalid position coordinates' 
      }, { status: 400 });
    }
    
    console.log(`[API get-citizens-at-position] Searching for citizens at position: ${JSON.stringify(position)}`);
    
    // Create position JSON string for Airtable query
    const positionString = JSON.stringify(position);
    const escapedPositionString = escapeAirtableValue(positionString);
    
    // 1. Find citizens at this position
    const citizensAtPosition = await airtable('CITIZENS').select({
      filterByFormula: `{Position} = '${escapedPositionString}'`
    }).all();
    
    console.log(`[API get-citizens-at-position] Found ${citizensAtPosition.length} citizens at position`);
    
    // 2. Find building at this position
    const buildingsAtPosition = await airtable('BUILDINGS').select({
      filterByFormula: `{Position} = '${escapedPositionString}'`
    }).all();
    
    console.log(`[API get-citizens-at-position] Found ${buildingsAtPosition.length} buildings at position`);
    
    // Process citizens data
    const citizens = citizensAtPosition.map(record => {
      const fields = normalizeKeysCamelCaseShallow(record.fields);
      
      // Parse position if it exists
      if (fields.position) {
        try {
          fields.position = JSON.parse(fields.position as string);
        } catch (e) {
          console.warn(`Could not parse position for citizen: ${fields.username}`);
        }
      }
      
      return {
        id: record.id,
        citizenId: fields.citizenId || fields.username,
        username: fields.username,
        firstName: fields.firstName,
        lastName: fields.lastName,
        socialClass: fields.socialClass,
        isAI: fields.isAI === 1 || fields.isAI === true,
        inVenice: fields.inVenice === 1 || fields.inVenice === true,
        position: fields.position,
        // Include other relevant fields
        homeCity: fields.homeCity,
        specialty: fields.specialty,
        color: fields.color,
        secondaryColor: fields.secondaryColor,
        familyMotto: fields.familyMotto,
        influence: fields.influence,
        // Add coatOfArms URL if available
        coatOfArmsImageUrl: fields.coatOfArms 
          ? (Array.isArray(fields.coatOfArms) && fields.coatOfArms[0]?.url 
              ? fields.coatOfArms[0].url 
              : null)
          : null
      };
    });
    
    // Process building data
    const building = buildingsAtPosition.length > 0 ? {
      id: buildingsAtPosition[0].id,
      buildingId: buildingsAtPosition[0].fields.BuildingId,
      name: buildingsAtPosition[0].fields.Name,
      type: buildingsAtPosition[0].fields.Type,
      category: buildingsAtPosition[0].fields.Category,
      owner: buildingsAtPosition[0].fields.Owner,
      runBy: buildingsAtPosition[0].fields.RunBy,
      occupant: buildingsAtPosition[0].fields.Occupant,
      position: buildingsAtPosition[0].fields.Position 
        ? JSON.parse(buildingsAtPosition[0].fields.Position as string) 
        : null
    } : null;
    
    return NextResponse.json({
      success: true,
      position,
      citizens,
      building,
      counts: {
        citizens: citizens.length,
        buildings: buildingsAtPosition.length
      }
    });
    
  } catch (error) {
    console.error('[API get-citizens-at-position] Error:', error);
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error occurred' 
    }, { status: 500 });
  }
}

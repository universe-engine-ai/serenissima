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
  const startTime = Date.now();
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
    
    console.log(`[API get-citizens-at-position] Position string for query: ${positionString}`);
    
    // We need to handle floating point precision issues in position matching
    // Instead of exact string matching, we'll fetch all citizens and buildings and filter them
    
    // 1. Fetch citizens with position data
    const citizensWithPosition = await airtable('CITIZENS').select({
      filterByFormula: `NOT({Position} = '')`,
    }).all();
    
    console.log(`[API get-citizens-at-position] Found ${citizensWithPosition.length} citizens with position data`);
    
    // Filter citizens at the requested position with tolerance for floating point precision
    const citizensAtPosition = citizensWithPosition.filter(record => {
      try {
        if (!record.fields.Position) return false;
        
        const citizenPos = JSON.parse(record.fields.Position as string);
        // Use small epsilon for floating point comparison
        const latMatch = Math.abs(citizenPos.lat - position.lat) < 0.0000001;
        const lngMatch = Math.abs(citizenPos.lng - position.lng) < 0.0000001;
        
        return latMatch && lngMatch;
      } catch (e) {
        console.warn(`Could not parse position for citizen record: ${record.id}`);
        return false;
      }
    });
    
    console.log(`[API get-citizens-at-position] Found ${citizensAtPosition.length} citizens at the exact position`);
    
    // 2. Fetch buildings with position data
    const buildingsWithPosition = await airtable('BUILDINGS').select({
      filterByFormula: `NOT({Position} = '')`,
    }).all();
    
    console.log(`[API get-citizens-at-position] Found ${buildingsWithPosition.length} buildings with position data`);
    
    // Filter buildings at the requested position with tolerance for floating point precision
    const buildingsAtPosition = buildingsWithPosition.filter(record => {
      try {
        if (!record.fields.Position) return false;
        
        const buildingPos = JSON.parse(record.fields.Position as string);
        // Use small epsilon for floating point comparison
        const latMatch = Math.abs(buildingPos.lat - position.lat) < 0.0000001;
        const lngMatch = Math.abs(buildingPos.lng - position.lng) < 0.0000001;
        
        return latMatch && lngMatch;
      } catch (e) {
        console.warn(`Could not parse position for building record: ${record.id}`);
        return false;
      }
    });
    
    console.log(`[API get-citizens-at-position] Found ${buildingsAtPosition.length} buildings at the exact position`);
    
    console.log(`[API get-citizens-at-position] Found ${buildingsAtPosition.length} buildings at position`);
    
    // Process citizens data with more efficient field extraction
    const citizens = citizensAtPosition.map(record => {
      const fields = normalizeKeysCamelCaseShallow(record.fields);
      
      // Parse position if it exists
      let parsedPosition = null;
      if (fields.position) {
        try {
          parsedPosition = JSON.parse(fields.position as string);
        } catch (e) {
          console.warn(`Could not parse position for citizen: ${fields.username}`);
        }
      }
      
      // Extract coat of arms URL efficiently
      let coatOfArmsUrl = null;
      if (fields.coatOfArms) {
        if (Array.isArray(fields.coatOfArms) && fields.coatOfArms[0]?.url) {
          coatOfArmsUrl = fields.coatOfArms[0].url;
        } else if (typeof fields.coatOfArms === 'string') {
          coatOfArmsUrl = fields.coatOfArms;
        }
      }
      
      // Return only the fields we need to reduce payload size
      return {
        id: record.id,
        citizenId: fields.citizenId || fields.username,
        username: fields.username,
        firstName: fields.firstName,
        lastName: fields.lastName,
        socialClass: fields.socialClass,
        isAI: fields.isAI === 1 || fields.isAI === true,
        inVenice: fields.inVenice === 1 || fields.inVenice === true,
        position: parsedPosition,
        // Include only the most relevant fields to reduce payload size
        homeCity: fields.homeCity,
        specialty: fields.specialty,
        color: fields.color,
        secondaryColor: fields.secondaryColor,
        familyMotto: fields.familyMotto,
        influence: fields.influence,
        coatOfArmsImageUrl: coatOfArmsUrl
      };
    });
    
    // Process building data more efficiently
    let building = null;
    if (buildingsAtPosition.length > 0) {
      const buildingRecord = buildingsAtPosition[0];
      const fields = buildingRecord.fields;
      
      // Parse position once
      let parsedPosition = null;
      if (fields.Position) {
        try {
          parsedPosition = JSON.parse(fields.Position as string);
        } catch (e) {
          console.warn(`Could not parse position for building: ${fields.BuildingId}`);
        }
      }
      
      building = {
        id: buildingRecord.id,
        buildingId: fields.BuildingId,
        name: fields.Name,
        type: fields.Type,
        category: fields.Category,
        owner: fields.Owner,
        runBy: fields.RunBy,
        occupant: fields.Occupant,
        position: parsedPosition,
        // Add additional useful fields
        isConstructed: fields.IsConstructed === 1 || fields.IsConstructed === true,
        landId: fields.LandId
      };
    }
    
    // Add timing information for performance monitoring
    const endTime = Date.now();
    const executionTime = endTime - startTime;
    
    return NextResponse.json({
      success: true,
      position,
      citizens,
      building,
      counts: {
        citizens: citizens.length,
        buildings: buildingsAtPosition.length
      },
      performance: {
        executionTimeMs: executionTime,
        citizensWithPositionCount: citizensWithPosition.length,
        buildingsWithPositionCount: buildingsWithPosition.length
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

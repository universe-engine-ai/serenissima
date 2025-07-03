import { NextResponse } from 'next/server';

// Helper to escape single quotes for Airtable formulas
function escapeAirtableValue(value: string): string {
  if (typeof value !== 'string') {
    return String(value);
  }
  return value.replace(/'/g, "\\'");
}

export async function GET(request: Request) {
  try {
    // Get URL parameters
    const urlObject = new URL(request.url);
    const searchParams = urlObject.searchParams;
    
    const executedBy = searchParams.getAll('executedBy'); // Keep this specific handling
    const limit = parseInt(searchParams.get('limit') || '100', 10); // Ensure radix 10
    const status = searchParams.get('status');
    const type = searchParams.get('type');
    
    console.log(`Fetching stratagems: limit=${limit}, status=${status}, type=${type}, executedBy=${executedBy.length > 0 ? executedBy.join(',') : 'none'}`);
    
    // Get Airtable credentials from environment variables
    const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
    const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
    const AIRTABLE_STRATAGEMS_TABLE = process.env.AIRTABLE_STRATAGEMS_TABLE || 'STRATAGEMS';
    
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      return NextResponse.json(
        { success: false, error: 'Airtable credentials not configured' },
        { status: 500 }
      );
    }
    
    // Construct the Airtable API URL
    const url = `https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_STRATAGEMS_TABLE}`;
    
    // Create the filter formula based on parameters
    let filterByFormulaParts: string[] = [];
    const loggableFilters: Record<string, string> = {};
    // Reserved parameters are those handled by specific logic or Airtable's select options directly
    // Ensure all are lowercase for case-insensitive matching with key.toLowerCase()
    const reservedParams = ['limit', 'offset', 'sortfield', 'sortdirection', 'executedby', 'status', 'type'];
    
    // Handle specific executedBy filter
    if (executedBy.length > 0) {
      if (executedBy.length === 1) {
        filterByFormulaParts.push(`{ExecutedBy} = '${escapeAirtableValue(executedBy[0])}'`);
      } else {
        const executedByFilters = executedBy.map(id => `{ExecutedBy} = '${escapeAirtableValue(id)}'`);
        filterByFormulaParts.push(`OR(${executedByFilters.join(', ')})`);
      }
      loggableFilters['ExecutedBy'] = executedBy.join(',');
    }
    
    // Handle specific status filter
    if (status) {
      filterByFormulaParts.push(`{Status} = '${escapeAirtableValue(status)}'`);
      loggableFilters['Status'] = status;
    }
    
    // Handle specific type filter
    if (type) {
      filterByFormulaParts.push(`{Type} = '${escapeAirtableValue(type)}'`);
      loggableFilters['Type'] = type;
    }

    // Add dynamic filters from other query parameters
    for (const [key, value] of searchParams.entries()) {
      if (reservedParams.includes(key.toLowerCase())) {
        continue;
      }
      const airtableField = key; // Assuming query param key IS the Airtable field name
      loggableFilters[airtableField] = value;

      const numValue = parseFloat(value);
      if (!isNaN(numValue) && isFinite(numValue) && numValue.toString() === value) {
        filterByFormulaParts.push(`{${airtableField}} = ${value}`);
      } else if (value.toLowerCase() === 'true') {
        filterByFormulaParts.push(`{${airtableField}} = TRUE()`);
      } else if (value.toLowerCase() === 'false') {
        filterByFormulaParts.push(`{${airtableField}} = FALSE()`);
      } else {
        filterByFormulaParts.push(`{${airtableField}} = '${escapeAirtableValue(value)}'`);
      }
    }
    
    let filterByFormula = '';
    if (filterByFormulaParts.length === 1) {
      filterByFormula = filterByFormulaParts[0];
    } else if (filterByFormulaParts.length > 1) {
      filterByFormula = `AND(${filterByFormulaParts.join(', ')})`;
    }
    
    console.log('%c GET /api/stratagems request received', 'background: #FFFF00; color: black; padding: 2px 5px; font-weight: bold;');
    console.log('Query parameters (filters):', loggableFilters);
    if (filterByFormula) {
      console.log('Applying Airtable filter formula:', filterByFormula);
    }
    
    // Prepare the request parameters
    let requestUrl = `${url}?sort%5B0%5D%5Bfield%5D=ExecutedAt&sort%5B0%5D%5Bdirection%5D=desc&maxRecords=${limit}`;
    
    if (filterByFormula) {
      requestUrl += `&filterByFormula=${encodeURIComponent(filterByFormula)}`;
    }
    
    const response = await fetch(requestUrl, {
      headers: {
        'Authorization': `Bearer ${AIRTABLE_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.status === 422) {
      console.warn(`Airtable API returned 422 (Unprocessable Entity) for formula: ${filterByFormula}. Request URL: ${requestUrl}. Returning empty stratagems list.`);
      return NextResponse.json(
        { 
          success: true, 
          stratagems: [], 
          _fallbackError: true, 
          error: 'Airtable could not process the request formula.',
          airtableRequestUrl: requestUrl // Include the problematic request URL
        },
        { status: 200 }
      );
    }

    if (!response.ok) {
      console.error(`Airtable API error: ${response.status} ${response.statusText}`);
      return NextResponse.json(
        { success: false, error: `Failed to fetch stratagems: ${response.statusText}` },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    
    let fetchedStratagems = data.records.map((record: any) => {
      const fields = record.fields;
      const formattedStratagem: Record<string, any> = { stratagemId: record.id };
      for (const key in fields) {
        if (Object.prototype.hasOwnProperty.call(fields, key)) {
          const camelKey = key.charAt(0).toLowerCase() + key.slice(1);
          formattedStratagem[camelKey] = fields[key];
        }
      }
      return formattedStratagem;
    });
    
    console.log(`Found ${fetchedStratagems.length} stratagems.`);
    
    return NextResponse.json({
      success: true,
      stratagems: fetchedStratagems
    });
  } catch (error) {
    console.error('Error fetching stratagems:', error);
    return NextResponse.json(
      { success: false, error: 'An error occurred while fetching stratagems' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    // Get Airtable credentials from environment variables
    const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
    const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
    const AIRTABLE_STRATAGEMS_TABLE = process.env.AIRTABLE_STRATAGEMS_TABLE || 'STRATAGEMS';
    
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      return NextResponse.json(
        { success: false, error: 'Airtable credentials not configured' },
        { status: 500 }
      );
    }
    
    // Parse the request body
    const requestData = await request.json();
    console.log('POST /api/stratagems request received with data:', requestData);
    
    // Validate required fields
    if (!requestData.type || !requestData.executedBy) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields: type and executedBy are required' },
        { status: 400 }
      );
    }
    
    // Prepare the record to be created
    const now = new Date().toISOString();
    const record = {
      fields: {
        Type: requestData.type,
        Variant: requestData.variant || null,
        Name: requestData.name || `${requestData.type} by ${requestData.executedBy}`,
        Category: requestData.category || null,
        ExecutedBy: requestData.executedBy,
        TargetCitizen: requestData.targetCitizen || null,
        TargetBuilding: requestData.targetBuilding || null,
        TargetResourceType: requestData.targetResourceType || null,
        Status: requestData.status || 'planned',
        CreatedAt: now,
        ExecutedAt: requestData.executedAt || now,
        ExpiresAt: requestData.expiresAt || null,
        Description: requestData.description || null,
        Notes: requestData.notes || null
      }
    };
    
    // Construct the Airtable API URL
    const url = `https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_STRATAGEMS_TABLE}`;
    
    // Send the request to create the record
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${AIRTABLE_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(record)
    });
    
    if (!response.ok) {
      console.error(`Airtable API error: ${response.status} ${response.statusText}`);
      return NextResponse.json(
        { success: false, error: `Failed to create stratagem: ${response.statusText}` },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    
    // Format the response
    const createdStratagem: Record<string, any> = { stratagemId: data.id };
    for (const key in data.fields) {
      if (Object.prototype.hasOwnProperty.call(data.fields, key)) {
        const camelKey = key.charAt(0).toLowerCase() + key.slice(1);
        createdStratagem[camelKey] = data.fields[key];
      }
    }
    
    console.log(`Created stratagem with ID: ${data.id}`);
    
    return NextResponse.json({
      success: true,
      stratagem: createdStratagem
    });
  } catch (error) {
    console.error('Error creating stratagem:', error);
    return NextResponse.json(
      { success: false, error: 'An error occurred while creating the stratagem' },
      { status: 500 }
    );
  }
}

export async function PATCH(request: Request) {
  try {
    // Get Airtable credentials from environment variables
    const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
    const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
    const AIRTABLE_STRATAGEMS_TABLE = process.env.AIRTABLE_STRATAGEMS_TABLE || 'STRATAGEMS';
    
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      return NextResponse.json(
        { success: false, error: 'Airtable credentials not configured' },
        { status: 500 }
      );
    }
    
    // Parse the request body
    const requestData = await request.json();
    console.log('PATCH /api/stratagems request received with data:', requestData);
    
    // Validate required fields
    if (!requestData.stratagemId) {
      return NextResponse.json(
        { success: false, error: 'Missing required field: stratagemId' },
        { status: 400 }
      );
    }
    
    // Prepare the record to be updated
    const fields: Record<string, any> = {};
    
    // Map camelCase keys to PascalCase for Airtable
    for (const key in requestData) {
      if (key !== 'stratagemId' && Object.prototype.hasOwnProperty.call(requestData, key)) {
        const pascalKey = key.charAt(0).toUpperCase() + key.slice(1);
        fields[pascalKey] = requestData[key];
      }
    }
    
    // Add UpdatedAt field
    fields.UpdatedAt = new Date().toISOString();
    
    const record = {
      id: requestData.stratagemId,
      fields
    };
    
    // Construct the Airtable API URL
    const url = `https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_STRATAGEMS_TABLE}/${requestData.stratagemId}`;
    
    // Send the request to update the record
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${AIRTABLE_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ fields })
    });
    
    if (!response.ok) {
      console.error(`Airtable API error: ${response.status} ${response.statusText}`);
      return NextResponse.json(
        { success: false, error: `Failed to update stratagem: ${response.statusText}` },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    
    // Format the response
    const updatedStratagem: Record<string, any> = { stratagemId: data.id };
    for (const key in data.fields) {
      if (Object.prototype.hasOwnProperty.call(data.fields, key)) {
        const camelKey = key.charAt(0).toLowerCase() + key.slice(1);
        updatedStratagem[camelKey] = data.fields[key];
      }
    }
    
    console.log(`Updated stratagem with ID: ${data.id}`);
    
    return NextResponse.json({
      success: true,
      stratagem: updatedStratagem
    });
  } catch (error) {
    console.error('Error updating stratagem:', error);
    return NextResponse.json(
      { success: false, error: 'An error occurred while updating the stratagem' },
      { status: 500 }
    );
  }
}

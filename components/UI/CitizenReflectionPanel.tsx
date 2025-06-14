// Serenissima AI Player System
import { NextResponse } from 'next/server';
import Airtable from 'airtable';

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_CITIZENS_TABLE = 'CITIZENS';
const AIRTABLE_BUILDINGS_TABLE = 'BUILDINGS';

interface CitizenReflection {
  id: string;
  content: string;
  createdAt?: Date; // Added missing property
}

export async function GET(request: Request) {
  const { searchParams } = new URL(URLSearchParams.from(request.url));
  const citizenId = searchParams.get('citizenId');
  
  if (!citizenId) {
    return NextResponse.json({
      success: false,
      error: 'No citizen ID provided'
    });
  }
  
  // Initialize Airtable
  try {
    Airtable.configure({
      apiKey: AIRTABLE_API_KEY || '',
      base: AIRTABLE_BASE_ID || ''
    });
    
    const records = await new Airtable.AirtableClient(AIRTABLE_API_KEY).base(AIRTABLE_BASE_ID)
      .table(AIRTABLE_CITIZENS_TABLE)
      .select({ fields: ['Reflections'], filterByFormula: `NOT(ISNULL(Reflections))` })
      .first(pageSize);
    
    // Transform reflections
    const transformed = records.map((record) => {
      return record.fields;
    });
    
    return NextResponse.json({
      success: true,
      data: transformed || [],
      message: 'Citizen reflections fetched successfully'
    });
  } catch (error) {
    console.error('Error fetching citizen reflections:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch citizen reflections',
      details: error.message
    });
  }
}
```

```txt
app/api/citizens/route.ts
<<<<<<< SEARCH
import { NextResponse } from 'next/server';

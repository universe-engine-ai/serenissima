import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_PROBLEMS_TABLE = 'PROBLEMS';

export async function GET(request: NextRequest) {
  try {
    // Initialize Airtable
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      return NextResponse.json(
        { success: false, error: 'Airtable credentials not configured' },
        { status: 500 }
      );
    }

    const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

    // Get URL parameters
    const { searchParams } = new URL(request.url);
    const citizen = searchParams.get('citizen');
    const status = searchParams.get('status') || 'active';
    
    // Require citizen parameter
    if (!citizen) {
      return NextResponse.json(
        { success: false, error: 'Citizen parameter is required' },
        { status: 400 }
      );
    }
    
    // Prepare filter formula based on parameters
    const filterFormula = `AND({Citizen} = '${citizen}', {Status} = '${status}')`;
    
    console.log(`Fetching problems with filter: ${filterFormula}`);
    
    // Fetch problems from Airtable with the constructed filter
    const problemsRecords = await base(AIRTABLE_PROBLEMS_TABLE)
      .select({
        filterByFormula: filterFormula,
        sort: [
          { field: 'CreatedAt', direction: 'desc' },
          { field: 'Severity', direction: 'desc' },
        ]
      })
      .all();
    
    console.log(`Fetched ${problemsRecords.length} problem records from Airtable for citizen ${citizen}`);
    
    // Transform records to a more usable format
    const problems = problemsRecords.map(record => {
      let position = record.get('Position');
      if (typeof position === 'string') {
        try {
          position = JSON.parse(position);
        } catch (error) {
          console.error('Error parsing position for problem:', record.id, error);
        }
      }

      return {
        id: record.id,
        problemId: record.get('ProblemId') || '',
        citizen: record.get('Citizen') || '',
        assetType: record.get('AssetType') || '',
        asset: record.get('Asset') || '',
        severity: String(record.get('Severity') || 'medium'),
        status: record.get('Status') || 'active',
        createdAt: record.get('CreatedAt') || '',
        updatedAt: record.get('UpdatedAt') || '',
        location: record.get('Location') || '',
        position: position || '',
        type: record.get('Type') || '',
        title: record.get('Title') || '',
        description: record.get('Description') || '',
        solutions: record.get('Solutions') || '',
        notes: record.get('Notes') || ''
      };
    });
    
    // Return the problems data
    return NextResponse.json({
      success: true,
      citizen,
      problemCount: problems.length,
      problems
    });
    
  } catch (error) {
    console.error('Error in problems/fetch endpoint:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process problems request', details: (error as Error).message },
      { status: 500 }
    );
  }
}

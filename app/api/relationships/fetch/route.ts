import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_RELATIONSHIPS_TABLE = 'RELATIONSHIPS';

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
    const minTrustScore = searchParams.get('minTrustScore');
    const maxTrustScore = searchParams.get('maxTrustScore');
    const minStrengthScore = searchParams.get('minStrengthScore');
    const maxStrengthScore = searchParams.get('maxStrengthScore');
    const status = searchParams.get('status') || 'Active';
    const limit = parseInt(searchParams.get('limit') || '50');
    
    // Require citizen parameter
    if (!citizen) {
      return NextResponse.json(
        { success: false, error: 'Citizen parameter is required' },
        { status: 400 }
      );
    }
    
    // Prepare filter formula based on parameters
    let filterParts = [
      `OR({Citizen1} = '${citizen}', {Citizen2} = '${citizen}')`,
      `{Status} = '${status}'`
    ];
    
    if (minTrustScore) {
      filterParts.push(`{TrustScore} >= ${minTrustScore}`);
    }
    
    if (maxTrustScore) {
      filterParts.push(`{TrustScore} <= ${maxTrustScore}`);
    }
    
    if (minStrengthScore) {
      filterParts.push(`{StrengthScore} >= ${minStrengthScore}`);
    }
    
    if (maxStrengthScore) {
      filterParts.push(`{StrengthScore} <= ${maxStrengthScore}`);
    }
    
    const filterFormula = `AND(${filterParts.join(', ')})`;
    
    console.log(`Fetching relationships with filter: ${filterFormula}`);
    
    // Fetch relationships from Airtable with the constructed filter
    const relationshipsRecords = await base(AIRTABLE_RELATIONSHIPS_TABLE)
      .select({
        filterByFormula: filterFormula,
        sort: [
          { field: 'TrustScore', direction: 'desc' }
        ],
        maxRecords: limit
      })
      .all();
    
    console.log(`Fetched ${relationshipsRecords.length} relationship records from Airtable for citizen ${citizen}`);
    
    // Transform records to a more usable format
    const relationships = relationshipsRecords.map(record => {
      const citizen1 = record.get('Citizen1') as string;
      const citizen2 = record.get('Citizen2') as string;
      
      // Determine the other citizen in the relationship
      const otherCitizen = citizen1 === citizen ? citizen2 : citizen1;
      
      return {
        id: record.id,
        relationshipId: record.get('RelationshipId') || '',
        citizen: citizen,
        otherCitizen: otherCitizen,
        trustScore: record.get('TrustScore') || 0,
        strengthScore: record.get('StrengthScore') || 0,
        status: record.get('Status') || 'Active',
        lastInteraction: record.get('LastInteraction') || '',
        createdAt: record.get('CreatedAt') || '',
        updatedAt: record.get('UpdatedAt') || '',
        notes: record.get('Notes') || '',
        title: record.get('Title') || '',
        description: record.get('Description') || '',
        qualifiedAt: record.get('QualifiedAt') || ''
      };
    });
    
    // Categorize relationships
    const friends = relationships.filter(r => r.trustScore >= 60);
    const allies = relationships.filter(r => r.trustScore >= 50 && r.trustScore < 60);
    const neutrals = relationships.filter(r => r.trustScore > 40 && r.trustScore < 50);
    const cautious = relationships.filter(r => r.trustScore > 30 && r.trustScore <= 40);
    const enemies = relationships.filter(r => r.trustScore <= 30);
    
    // Return the relationships data with categories
    return NextResponse.json({
      success: true,
      citizen,
      relationshipCount: relationships.length,
      categories: {
        friends: friends,
        allies: allies,
        neutrals: neutrals,
        cautious: cautious,
        enemies: enemies
      },
      relationships
    });
    
  } catch (error) {
    console.error('Error in relationships/fetch endpoint:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process relationships request', details: (error as Error).message },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_RELATIONSHIPS_TABLE = 'RELATIONSHIPS';
const AIRTABLE_CITIZENS_TABLE = 'CITIZENS';
const AIRTABLE_RELEVANCIES_TABLE = 'RELEVANCIES';

interface RecommendedRelationship {
  citizen: string;
  firstName: string;
  lastName: string;
  socialClass: string;
  relevanceScore: number;
  commonConnections: number;
  reasonsToConnect: string[];
}

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
    const limit = parseInt(searchParams.get('limit') || '10');
    
    // Require citizen parameter
    if (!citizen) {
      return NextResponse.json(
        { success: false, error: 'Citizen parameter is required' },
        { status: 400 }
      );
    }
    
    console.log(`Finding relationship recommendations for citizen: ${citizen}`);
    
    // Step 1: Get existing relationships
    const existingRelationshipsFilter = `OR({Citizen1} = '${citizen}', {Citizen2} = '${citizen}')`;
    const existingRelationshipsRecords = await base(AIRTABLE_RELATIONSHIPS_TABLE)
      .select({
        filterByFormula: existingRelationshipsFilter
      })
      .all();
    
    // Extract the citizens this person already has relationships with
    const existingRelationships = new Set<string>();
    existingRelationships.add(citizen); // Add self to exclude
    
    existingRelationshipsRecords.forEach(record => {
      const citizen1 = record.get('Citizen1') as string;
      const citizen2 = record.get('Citizen2') as string;
      if (citizen1 === citizen) {
        existingRelationships.add(citizen2);
      } else {
        existingRelationships.add(citizen1);
      }
    });
    
    console.log(`Found ${existingRelationships.size - 1} existing relationships`);
    
    // Step 2: Get relevancies that might suggest new connections
    const relevanciesFilter = `{RelevantToCitizen} = '${citizen}'`;
    const relevanciesRecords = await base(AIRTABLE_RELEVANCIES_TABLE)
      .select({
        filterByFormula: relevanciesFilter
      })
      .all();
    
    // Extract potential connections from relevancies
    const potentialConnections = new Map<string, { score: number, reasons: Set<string> }>();
    
    relevanciesRecords.forEach(record => {
      const targetCitizen = record.get('TargetCitizen') as string;
      const assetType = record.get('AssetType') as string;
      const score = record.get('Score') as number || 0;
      const title = record.get('Title') as string || '';
      
      // Skip if this is not a citizen-related relevancy or already has a relationship
      if (assetType !== 'citizen' || existingRelationships.has(targetCitizen) || targetCitizen === 'all') {
        return;
      }
      
      if (!potentialConnections.has(targetCitizen)) {
        potentialConnections.set(targetCitizen, { score: 0, reasons: new Set<string>() });
      }
      
      const connection = potentialConnections.get(targetCitizen)!;
      connection.score += score;
      connection.reasons.add(title);
    });
    
    console.log(`Found ${potentialConnections.size} potential connections from relevancies`);
    
    // Step 3: Find common connections (friends of friends)
    const commonConnections = new Map<string, number>();
    
    // For each existing relationship
    for (const record of existingRelationshipsRecords) {
      const citizen1 = record.get('Citizen1') as string;
      const citizen2 = record.get('Citizen2') as string;
      const directConnection = citizen1 === citizen ? citizen2 : citizen1;
      
      // Get this connection's relationships
      const connectionRelationshipsFilter = `OR({Citizen1} = '${directConnection}', {Citizen2} = '${directConnection}')`;
      const connectionRelationshipsRecords = await base(AIRTABLE_RELATIONSHIPS_TABLE)
        .select({
          filterByFormula: connectionRelationshipsFilter
        })
        .all();
      
      // For each of their relationships, check if it's someone new
      connectionRelationshipsRecords.forEach(connectionRecord => {
        const connectionCitizen1 = connectionRecord.get('Citizen1') as string;
        const connectionCitizen2 = connectionRecord.get('Citizen2') as string;
        const indirectConnection = connectionCitizen1 === directConnection ? connectionCitizen2 : connectionCitizen1;
        
        // Skip if this is the original citizen or already has a direct relationship
        if (indirectConnection === citizen || existingRelationships.has(indirectConnection)) {
          return;
        }
        
        // Count this as a common connection
        commonConnections.set(
          indirectConnection, 
          (commonConnections.get(indirectConnection) || 0) + 1
        );
        
        // Also add to potential connections if not already there
        if (!potentialConnections.has(indirectConnection)) {
          potentialConnections.set(indirectConnection, { score: 0, reasons: new Set<string>() });
        }
      });
    }
    
    console.log(`Found ${commonConnections.size} potential connections from common relationships`);
    
    // Step 4: Get citizen details for all potential connections
    const potentialCitizenIds = Array.from(potentialConnections.keys());
    if (potentialCitizenIds.length === 0) {
      return NextResponse.json({
        success: true,
        citizen,
        recommendations: []
      });
    }
    
    const citizenDetailsFilter = `OR(${potentialCitizenIds.map(id => `{Username} = '${id}'`).join(', ')})`;
    const citizenDetailsRecords = await base(AIRTABLE_CITIZENS_TABLE)
      .select({
        filterByFormula: citizenDetailsFilter,
        fields: ['Username', 'FirstName', 'LastName', 'SocialClass']
      })
      .all();
    
    // Create recommendations
    const recommendations: RecommendedRelationship[] = [];
    
    citizenDetailsRecords.forEach(record => {
      const username = record.get('Username') as string;
      const firstName = record.get('FirstName') as string || '';
      const lastName = record.get('LastName') as string || '';
      const socialClass = record.get('SocialClass') as string || '';
      
      const connection = potentialConnections.get(username);
      if (!connection) return;
      
      const commonConnectionCount = commonConnections.get(username) || 0;
      
      // Calculate a combined score
      const relevanceScore = connection.score + (commonConnectionCount * 10);
      
      // Generate reasons to connect
      const reasonsToConnect: string[] = Array.from(connection.reasons);
      
      if (commonConnectionCount > 0) {
        reasonsToConnect.push(`You have ${commonConnectionCount} mutual connection${commonConnectionCount > 1 ? 's' : ''}`);
      }
      
      if (socialClass === 'Nobili') {
        reasonsToConnect.push('Noble connection could provide political advantages');
      } else if (socialClass === 'Cittadini') {
        reasonsToConnect.push('Cittadini connection could provide business opportunities');
      }
      
      recommendations.push({
        citizen: username,
        firstName,
        lastName,
        socialClass,
        relevanceScore,
        commonConnections: commonConnectionCount,
        reasonsToConnect
      });
    });
    
    // Sort by relevance score and limit
    recommendations.sort((a, b) => b.relevanceScore - a.relevanceScore);
    const limitedRecommendations = recommendations.slice(0, limit);
    
    // Return the recommendations
    return NextResponse.json({
      success: true,
      citizen,
      recommendationCount: limitedRecommendations.length,
      recommendations: limitedRecommendations
    });
    
  } catch (error) {
    console.error('Error in relationships/recommend endpoint:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to generate relationship recommendations', details: (error as Error).message },
      { status: 500 }
    );
  }
}

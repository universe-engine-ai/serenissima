import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_RELATIONSHIPS_TABLE = 'RELATIONSHIPS';
const AIRTABLE_CITIZENS_TABLE = 'CITIZENS';

interface Node {
  id: string;
  label: string;
  group: string;
  size: number;
  color?: string;
}

interface Edge {
  from: string;
  to: string;
  value: number;
  title: string;
  color?: string;
}

interface NetworkData {
  nodes: Node[];
  edges: Edge[];
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
    const depth = parseInt(searchParams.get('depth') || '1');
    const minStrength = parseFloat(searchParams.get('minStrength') || '0.5');
    
    // Require citizen parameter
    if (!citizen) {
      return NextResponse.json(
        { success: false, error: 'Citizen parameter is required' },
        { status: 400 }
      );
    }
    
    console.log(`Visualizing relationships for citizen: ${citizen} with depth: ${depth}`);
    
    // Fetch direct relationships
    const filterFormula = `OR({Citizen1} = '${citizen}', {Citizen2} = '${citizen}')`;
    
    const relationshipsRecords = await base(AIRTABLE_RELATIONSHIPS_TABLE)
      .select({
        filterByFormula: filterFormula
      })
      .all();
    
    console.log(`Fetched ${relationshipsRecords.length} direct relationship records`);
    
    // Build the network data
    const nodes: Record<string, Node> = {};
    const edges: Edge[] = [];
    const processedRelationships = new Set<string>();
    
    // Add the central citizen
    nodes[citizen] = {
      id: citizen,
      label: citizen,
      group: 'central',
      size: 30
    };
    
    // Process relationships
    const citizensToProcess = [citizen];
    const processedCitizens = new Set<string>();
    
    for (let currentDepth = 0; currentDepth < depth; currentDepth++) {
      const nextCitizensToProcess: string[] = [];
      
      for (const currentCitizen of citizensToProcess) {
        if (processedCitizens.has(currentCitizen)) continue;
        processedCitizens.add(currentCitizen);
        
        // Fetch relationships for this citizen
        const citizenFilterFormula = `OR({Citizen1} = '${currentCitizen}', {Citizen2} = '${currentCitizen}')`;
        
        const citizenRelationshipsRecords = currentCitizen === citizen 
          ? relationshipsRecords 
          : await base(AIRTABLE_RELATIONSHIPS_TABLE)
              .select({
                filterByFormula: citizenFilterFormula
              })
              .all();
        
        // Process each relationship
        for (const record of citizenRelationshipsRecords) {
          const relationshipId = record.id;
          if (processedRelationships.has(relationshipId)) continue;
          processedRelationships.add(relationshipId);
          
          const citizen1 = record.get('Citizen1') as string;
          const citizen2 = record.get('Citizen2') as string;
          const trustScore = record.get('TrustScore') as number || 0;
          const strengthScore = record.get('StrengthScore') as number || 0;
          
          // Skip weak relationships
          if (strengthScore < minStrength) continue;
          
          // Add nodes if they don't exist
          if (!nodes[citizen1]) {
            nodes[citizen1] = {
              id: citizen1,
              label: citizen1,
              group: currentDepth === 0 ? 'direct' : 'indirect',
              size: 15
            };
          }
          
          if (!nodes[citizen2]) {
            nodes[citizen2] = {
              id: citizen2,
              label: citizen2,
              group: currentDepth === 0 ? 'direct' : 'indirect',
              size: 15
            };
          }
          
          // Add edge
          const edgeTitle = `Trust: ${trustScore.toFixed(1)}, Strength: ${strengthScore.toFixed(1)}`;
          const edgeColor = trustScore >= 60 ? 'green' : 
                           trustScore >= 50 ? 'lightgreen' :
                           trustScore >= 40 ? 'gray' :
                           trustScore >= 30 ? 'orange' : 'red';
          
          edges.push({
            from: citizen1,
            to: citizen2,
            value: Math.max(1, strengthScore * 5), // Scale for visibility
            title: edgeTitle,
            color: edgeColor
          });
          
          // Add the other citizen to the next level if we're not at max depth
          const otherCitizen = citizen1 === currentCitizen ? citizen2 : citizen1;
          if (currentDepth < depth - 1 && !processedCitizens.has(otherCitizen)) {
            nextCitizensToProcess.push(otherCitizen);
          }
        }
      }
      
      citizensToProcess.length = 0;
      citizensToProcess.push(...nextCitizensToProcess);
    }
    
    // Fetch citizen details to enhance node information
    const citizenIds = Object.keys(nodes);
    const citizenDetails: Record<string, any> = {};
    
    for (let i = 0; i < citizenIds.length; i += 100) { // Process in batches of 100
      const batch = citizenIds.slice(i, i + 100);
      const batchFilter = `OR(${batch.map(id => `{Username} = '${id}'`).join(', ')})`;
      
      const citizenRecords = await base(AIRTABLE_CITIZENS_TABLE)
        .select({
          filterByFormula: batchFilter,
          fields: ['Username', 'FirstName', 'LastName', 'SocialClass', 'Color']
        })
        .all();
      
      for (const record of citizenRecords) {
        const username = record.get('Username') as string;
        citizenDetails[username] = {
          firstName: record.get('FirstName') as string || '',
          lastName: record.get('LastName') as string || '',
          socialClass: record.get('SocialClass') as string || '',
          color: record.get('Color') as string || ''
        };
      }
    }
    
    // Enhance nodes with citizen details
    for (const nodeId in nodes) {
      const details = citizenDetails[nodeId];
      if (details) {
        const node = nodes[nodeId];
        node.label = `${details.firstName} ${details.lastName}`;
        node.color = details.color || undefined;
        
        // Adjust size based on social class
        if (details.socialClass === 'Nobili') {
          node.size = node.size * 1.5;
        } else if (details.socialClass === 'Cittadini') {
          node.size = node.size * 1.2;
        }
      }
    }
    
    // Convert nodes object to array
    const networkData: NetworkData = {
      nodes: Object.values(nodes),
      edges
    };
    
    // Return the network data
    return NextResponse.json({
      success: true,
      citizen,
      depth,
      minStrength,
      networkData
    });
    
  } catch (error) {
    console.error('Error in relationships/visualize endpoint:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to visualize relationships', details: (error as Error).message },
      { status: 500 }
    );
  }
}

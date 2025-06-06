import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_RELATIONSHIPS_TABLE = 'RELATIONSHIPS';
const AIRTABLE_CITIZENS_TABLE = 'CITIZENS';

interface RelationshipSummary {
  totalRelationships: number;
  averageTrustScore: number;
  averageStrengthScore: number;
  friendCount: number;
  allyCount: number;
  neutralCount: number;
  cautiousCount: number;
  enemyCount: number;
  strongestRelationship?: {
    citizen: string;
    firstName: string;
    lastName: string;
    trustScore: number;
    strengthScore: number;
  };
  weakestRelationship?: {
    citizen: string;
    firstName: string;
    lastName: string;
    trustScore: number;
    strengthScore: number;
  };
  recentInteractions: {
    citizen: string;
    firstName: string;
    lastName: string;
    lastInteraction: string;
  }[];
  socialClassDistribution: {
    nobili: number;
    cittadini: number;
    popolani: number;
    facchini: number;
    forestieri: number;
    other: number;
  };
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
    
    // Require citizen parameter
    if (!citizen) {
      return NextResponse.json(
        { success: false, error: 'Citizen parameter is required' },
        { status: 400 }
      );
    }
    
    console.log(`Generating relationship summary for citizen: ${citizen}`);
    
    // Fetch all relationships for this citizen
    const relationshipsFilter = `OR({Citizen1} = '${citizen}', {Citizen2} = '${citizen}')`;
    
    const relationshipsRecords = await base(AIRTABLE_RELATIONSHIPS_TABLE)
      .select({
        filterByFormula: relationshipsFilter
      })
      .all();
    
    console.log(`Fetched ${relationshipsRecords.length} relationship records`);
    
    if (relationshipsRecords.length === 0) {
      return NextResponse.json({
        success: true,
        citizen,
        summary: {
          totalRelationships: 0,
          averageTrustScore: 50,
          averageStrengthScore: 0,
          friendCount: 0,
          allyCount: 0,
          neutralCount: 0,
          cautiousCount: 0,
          enemyCount: 0,
          recentInteractions: [],
          socialClassDistribution: {
            nobili: 0,
            cittadini: 0,
            popolani: 0,
            facchini: 0,
            forestieri: 0,
            other: 0
          }
        }
      });
    }
    
    // Process relationships
    const relationships = relationshipsRecords.map(record => {
      const citizen1 = record.get('Citizen1') as string;
      const citizen2 = record.get('Citizen2') as string;
      const otherCitizen = citizen1 === citizen ? citizen2 : citizen1;
      
      return {
        id: record.id,
        otherCitizen,
        trustScore: record.get('TrustScore') as number || 50,
        strengthScore: record.get('StrengthScore') as number || 0,
        lastInteraction: record.get('LastInteraction') as string || record.get('CreatedAt') as string || ''
      };
    });
    
    // Calculate statistics
    const totalRelationships = relationships.length;
    const totalTrustScore = relationships.reduce((sum, rel) => sum + rel.trustScore, 0);
    const totalStrengthScore = relationships.reduce((sum, rel) => sum + rel.strengthScore, 0);
    const averageTrustScore = totalRelationships > 0 ? totalTrustScore / totalRelationships : 50;
    const averageStrengthScore = totalRelationships > 0 ? totalStrengthScore / totalRelationships : 0;
    
    // Count relationship categories
    const friendCount = relationships.filter(r => r.trustScore >= 60).length;
    const allyCount = relationships.filter(r => r.trustScore >= 50 && r.trustScore < 60).length;
    const neutralCount = relationships.filter(r => r.trustScore > 40 && r.trustScore < 50).length;
    const cautiousCount = relationships.filter(r => r.trustScore > 30 && r.trustScore <= 40).length;
    const enemyCount = relationships.filter(r => r.trustScore <= 30).length;
    
    // Find strongest and weakest relationships
    relationships.sort((a, b) => b.trustScore - a.trustScore);
    const strongestRelationship = relationships[0];
    const weakestRelationship = relationships[relationships.length - 1];
    
    // Find recent interactions
    relationships.sort((a, b) => {
      const dateA = new Date(a.lastInteraction || 0);
      const dateB = new Date(b.lastInteraction || 0);
      return dateB.getTime() - dateA.getTime();
    });
    
    const recentInteractions = relationships.slice(0, 5);
    
    // Get citizen details for other citizens
    const otherCitizenIds = relationships.map(r => r.otherCitizen);
    const citizenDetailsFilter = `OR(${otherCitizenIds.map(id => `{Username} = '${id}'`).join(', ')})`;
    
    const citizenDetailsRecords = await base(AIRTABLE_CITIZENS_TABLE)
      .select({
        filterByFormula: citizenDetailsFilter,
        fields: ['Username', 'FirstName', 'LastName', 'SocialClass']
      })
      .all();
    
    // Create a map of citizen details
    const citizenDetails: Record<string, { firstName: string, lastName: string, socialClass: string }> = {};
    
    citizenDetailsRecords.forEach(record => {
      const username = record.get('Username') as string;
      citizenDetails[username] = {
        firstName: record.get('FirstName') as string || '',
        lastName: record.get('LastName') as string || '',
        socialClass: record.get('SocialClass') as string || ''
      };
    });
    
    // Calculate social class distribution
    const socialClassDistribution = {
      nobili: 0,
      cittadini: 0,
      popolani: 0,
      facchini: 0,
      forestieri: 0,
      other: 0
    };
    
    relationships.forEach(rel => {
      const details = citizenDetails[rel.otherCitizen];
      if (details) {
        const socialClass = details.socialClass.toLowerCase();
        if (socialClass.includes('nobili')) {
          socialClassDistribution.nobili++;
        } else if (socialClass.includes('cittadini')) {
          socialClassDistribution.cittadini++;
        } else if (socialClass.includes('popolani')) {
          socialClassDistribution.popolani++;
        } else if (socialClass.includes('facchini')) {
          socialClassDistribution.facchini++;
        } else if (socialClass.includes('forestieri')) {
          socialClassDistribution.forestieri++;
        } else {
          socialClassDistribution.other++;
        }
      } else {
        socialClassDistribution.other++;
      }
    });
    
    // Create the summary
    const summary: RelationshipSummary = {
      totalRelationships,
      averageTrustScore: parseFloat(averageTrustScore.toFixed(2)),
      averageStrengthScore: parseFloat(averageStrengthScore.toFixed(2)),
      friendCount,
      allyCount,
      neutralCount,
      cautiousCount,
      enemyCount,
      strongestRelationship: strongestRelationship ? {
        citizen: strongestRelationship.otherCitizen,
        firstName: citizenDetails[strongestRelationship.otherCitizen]?.firstName || '',
        lastName: citizenDetails[strongestRelationship.otherCitizen]?.lastName || '',
        trustScore: strongestRelationship.trustScore,
        strengthScore: strongestRelationship.strengthScore
      } : undefined,
      weakestRelationship: weakestRelationship ? {
        citizen: weakestRelationship.otherCitizen,
        firstName: citizenDetails[weakestRelationship.otherCitizen]?.firstName || '',
        lastName: citizenDetails[weakestRelationship.otherCitizen]?.lastName || '',
        trustScore: weakestRelationship.trustScore,
        strengthScore: weakestRelationship.strengthScore
      } : undefined,
      recentInteractions: recentInteractions.map(rel => ({
        citizen: rel.otherCitizen,
        firstName: citizenDetails[rel.otherCitizen]?.firstName || '',
        lastName: citizenDetails[rel.otherCitizen]?.lastName || '',
        lastInteraction: rel.lastInteraction
      })),
      socialClassDistribution
    };
    
    // Return the summary
    return NextResponse.json({
      success: true,
      citizen,
      summary
    });
    
  } catch (error) {
    console.error('Error in relationships/summary endpoint:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to generate relationship summary', details: (error as Error).message },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_RELATIONSHIPS_TABLE = 'RELATIONSHIPS';
const AIRTABLE_ACTIVITIES_TABLE = 'ACTIVITIES';

export async function POST(request: NextRequest) {
  try {
    // Initialize Airtable
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      return NextResponse.json(
        { success: false, error: 'Airtable credentials not configured' },
        { status: 500 }
      );
    }

    const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);
    
    // Parse request body
    const body = await request.json();
    const { citizen, targetCitizen, action, message } = body;
    
    // Validate required parameters
    if (!citizen || !targetCitizen || !action) {
      return NextResponse.json(
        { success: false, error: 'Missing required parameters: citizen, targetCitizen, and action are required' },
        { status: 400 }
      );
    }
    
    // Check if relationship exists
    const relationshipFilter = `OR(
      AND({Citizen1} = '${citizen}', {Citizen2} = '${targetCitizen}'),
      AND({Citizen1} = '${targetCitizen}', {Citizen2} = '${citizen}')
    )`;
    
    const existingRelationships = await base(AIRTABLE_RELATIONSHIPS_TABLE)
      .select({
        filterByFormula: relationshipFilter,
        maxRecords: 1
      })
      .all();
    
    let relationshipId = '';
    let currentTrustScore = 50; // Default neutral
    
    if (existingRelationships.length > 0) {
      relationshipId = existingRelationships[0].id;
      currentTrustScore = existingRelationships[0].get('TrustScore') as number || 50;
    }
    
    // Process the action
    let trustScoreChange = 0;
    let activityType = '';
    let activityTitle = '';
    let activityDescription = '';
    
    switch (action) {
      case 'send_gift':
        trustScoreChange = 5;
        activityType = 'send_gift';
        activityTitle = `Send Gift to ${targetCitizen}`;
        activityDescription = `${citizen} sends a gift to ${targetCitizen} to improve relations.`;
        break;
      case 'invite_to_dinner':
        trustScoreChange = 3;
        activityType = 'invite_to_dinner';
        activityTitle = `Invite ${targetCitizen} to Dinner`;
        activityDescription = `${citizen} invites ${targetCitizen} to dinner to discuss matters of mutual interest.`;
        break;
      case 'send_message':
        trustScoreChange = 1;
        activityType = 'send_message';
        activityTitle = `Send Message to ${targetCitizen}`;
        activityDescription = `${citizen} sends a message to ${targetCitizen}.`;
        break;
      case 'spread_rumors':
        trustScoreChange = -5;
        activityType = 'spread_rumors';
        activityTitle = `Spread Rumors about ${targetCitizen}`;
        activityDescription = `${citizen} spreads unfavorable rumors about ${targetCitizen}.`;
        break;
      case 'public_criticism':
        trustScoreChange = -3;
        activityType = 'public_criticism';
        activityTitle = `Publicly Criticize ${targetCitizen}`;
        activityDescription = `${citizen} publicly criticizes ${targetCitizen}.`;
        break;
      default:
        return NextResponse.json(
          { success: false, error: 'Invalid action. Supported actions: send_gift, invite_to_dinner, send_message, spread_rumors, public_criticism' },
          { status: 400 }
        );
    }
    
    // Create or update the relationship
    let updatedRelationship;
    
    if (relationshipId) {
      // Update existing relationship
      const newTrustScore = Math.max(0, Math.min(100, currentTrustScore + trustScoreChange));
      
      updatedRelationship = await base(AIRTABLE_RELATIONSHIPS_TABLE).update(relationshipId, {
        TrustScore: newTrustScore,
        LastInteraction: new Date().toISOString(),
        Notes: `${new Date().toISOString()}: ${action} (${trustScoreChange > 0 ? '+' : ''}${trustScoreChange} trust)\n${existingRelationships[0].get('Notes') || ''}`
      });
    } else {
      // Create new relationship
      const newTrustScore = 50 + trustScoreChange; // Start from neutral
      
      updatedRelationship = await base(AIRTABLE_RELATIONSHIPS_TABLE).create({
        Citizen1: citizen,
        Citizen2: targetCitizen,
        TrustScore: newTrustScore,
        StrengthScore: 1, // Initial strength
        Status: 'Active',
        CreatedAt: new Date().toISOString(),
        LastInteraction: new Date().toISOString(),
        Notes: `${new Date().toISOString()}: ${action} (${trustScoreChange > 0 ? '+' : ''}${trustScoreChange} trust)`
      });
    }
    
    // Create an activity record
    const activityId = `${activityType}_${citizen}_${Date.now()}`;
    
    await base(AIRTABLE_ACTIVITIES_TABLE).create({
      ActivityId: activityId,
      Citizen: citizen,
      Type: activityType,
      CreatedAt: new Date().toISOString(),
      StartDate: new Date().toISOString(),
      EndDate: new Date(Date.now() + 30 * 60 * 1000).toISOString(), // 30 minutes later
      Status: 'created',
      Title: activityTitle,
      Description: activityDescription,
      Notes: message || ''
    });
    
    // Return the result
    return NextResponse.json({
      success: true,
      action,
      citizen,
      targetCitizen,
      trustScoreChange,
      relationship: {
        id: updatedRelationship.id,
        trustScore: updatedRelationship.get('TrustScore'),
        lastInteraction: updatedRelationship.get('LastInteraction')
      },
      activity: {
        id: activityId,
        type: activityType,
        title: activityTitle
      }
    });
    
  } catch (error) {
    console.error('Error in relationships/action endpoint:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process relationship action', details: (error as Error).message },
      { status: 500 }
    );
  }
}

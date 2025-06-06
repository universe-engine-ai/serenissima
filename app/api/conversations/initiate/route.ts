import { NextResponse } from 'next/server';
import Airtable from 'airtable';

// Initialize Airtable
const base = new Airtable({ apiKey: process.env.AIRTABLE_API_KEY }).base(
  process.env.AIRTABLE_BASE_ID || ''
);

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Validate required fields
    if (!data.speaker_profile || !data.listener_profile) {
      return NextResponse.json(
        { success: false, error: 'Speaker and listener profiles are required' },
        { status: 400 }
      );
    }
    
    const { speaker_profile, listener_profile } = data;
    
    // Fetch speaker's problems
    const speakerProblems = await fetchProblems(speaker_profile.username);
    
    // Fetch listener's problems
    const listenerProblems = await fetchProblems(listener_profile.username);
    
    // Fetch relationship details between the two citizens
    const relationshipDetails = await fetchRelationshipDetails(
      speaker_profile.username, 
      listener_profile.username
    );
    
    // Fetch recent conversation history between the two citizens
    const conversationHistory = await fetchConversationHistory(
      speaker_profile.username, 
      listener_profile.username
    );
    
    // Prepare the data package for the speaker
    const speakerDataPackage = await fetchCitizenDataPackage(speaker_profile.username);
    
    // Construct the system prompt for the AI
    const systemPrompt = `You are ${speaker_profile.firstName}, a ${speaker_profile.socialClass} of Venice. You see ${listener_profile.firstName} (Social Class: ${listener_profile.socialClass}) here. Review your knowledge in \`addSystem\` (your data package, problems, your relationship with them, their problems, and any recent direct conversation history with them). What would you say to them to initiate a conversation or make an observation? Your response should be direct speech TO ${listener_profile.firstName}. Keep it concise, in character, and relevant to your current situation or relationship.`;
    
    // Call the AI service to generate the conversation
    // This is a placeholder - you would replace this with your actual AI service call
    const aiResponse = await callAIService(systemPrompt, {
      speaker_profile,
      listener_profile,
      speaker_data_package: speakerDataPackage,
      speaker_problems: speakerProblems,
      listener_problems: listenerProblems,
      relationship_details: relationshipDetails,
      conversation_history: conversationHistory
    });
    
    // Record this conversation in the database
    await recordConversation(
      speaker_profile.username,
      listener_profile.username,
      aiResponse
    );
    
    return NextResponse.json({
      success: true,
      conversation: aiResponse
    });
    
  } catch (error) {
    console.error('Error in conversation initiation:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to initiate conversation' },
      { status: 500 }
    );
  }
}

// Helper functions

async function fetchProblems(username: string) {
  try {
    const problems: any[] = [];
    
    await new Promise((resolve, reject) => {
      base('PROBLEMS')
        .select({
          filterByFormula: `{citizen} = "${username}"`,
          sort: [{ field: 'createdAt', direction: 'desc' }]
        })
        .eachPage(
          (records, fetchNextPage) => {
            records.forEach(record => {
              problems.push({
                id: record.id,
                problemId: record.get('problemId'),
                citizen: record.get('citizen'),
                assetType: record.get('assetType'),
                asset: record.get('asset'),
                severity: record.get('severity'),
                status: record.get('status'),
                createdAt: record.get('createdAt'),
                updatedAt: record.get('updatedAt'),
                location: record.get('location'),
                position: record.get('position'),
                type: record.get('type'),
                title: record.get('title'),
                description: record.get('description'),
                solutions: record.get('solutions'),
                notes: record.get('notes')
              });
            });
            fetchNextPage();
          },
          err => {
            if (err) {
              console.error(`Error fetching problems for ${username}:`, err);
              reject(err);
            } else {
              resolve(problems);
            }
          }
        );
    });
    
    return problems;
  } catch (error) {
    console.error(`Error in fetchProblems for ${username}:`, error);
    return [];
  }
}

async function fetchRelationshipDetails(speakerUsername: string, listenerUsername: string) {
  try {
    let relationship = null;
    
    await new Promise((resolve, reject) => {
      base('RELATIONSHIPS')
        .select({
          filterByFormula: `AND({CitizenA} = "${speakerUsername}", {CitizenB} = "${listenerUsername}")`,
          maxRecords: 1
        })
        .firstPage((err, records) => {
          if (err) {
            console.error('Error fetching relationship:', err);
            reject(err);
            return;
          }
          
          if (records && records.length > 0) {
            relationship = {
              id: records[0].id,
              citizenA: records[0].get('CitizenA'),
              citizenB: records[0].get('CitizenB'),
              strengthScore: records[0].get('StrengthScore'),
              trustScore: records[0].get('TrustScore'),
              lastInteraction: records[0].get('LastInteraction'),
              interactionCount: records[0].get('InteractionCount')
            };
          }
          
          resolve(relationship);
        });
    });
    
    // If no direct relationship found, check the reverse direction
    if (!relationship) {
      await new Promise((resolve, reject) => {
        base('RELATIONSHIPS')
          .select({
            filterByFormula: `AND({CitizenA} = "${listenerUsername}", {CitizenB} = "${speakerUsername}")`,
            maxRecords: 1
          })
          .firstPage((err, records) => {
            if (err) {
              console.error('Error fetching reverse relationship:', err);
              reject(err);
              return;
            }
            
            if (records && records.length > 0) {
              relationship = {
                id: records[0].id,
                citizenA: records[0].get('CitizenA'),
                citizenB: records[0].get('CitizenB'),
                strengthScore: records[0].get('StrengthScore'),
                trustScore: records[0].get('TrustScore'),
                lastInteraction: records[0].get('LastInteraction'),
                interactionCount: records[0].get('InteractionCount')
              };
            }
            
            resolve(relationship);
          });
      });
    }
    
    return relationship || {};
  } catch (error) {
    console.error('Error in fetchRelationshipDetails:', error);
    return {};
  }
}

async function fetchConversationHistory(speakerUsername: string, listenerUsername: string) {
  try {
    const conversations: any[] = [];
    
    await new Promise((resolve, reject) => {
      base('MESSAGES')
        .select({
          filterByFormula: `OR(
            AND({FromCitizen} = "${speakerUsername}", {ToCitizen} = "${listenerUsername}"),
            AND({FromCitizen} = "${listenerUsername}", {ToCitizen} = "${speakerUsername}")
          )`,
          sort: [{ field: 'createdAt', direction: 'desc' }],
          maxRecords: 10
        })
        .eachPage(
          (records, fetchNextPage) => {
            records.forEach(record => {
              conversations.push({
                id: record.id,
                fromCitizen: record.get('FromCitizen'),
                toCitizen: record.get('ToCitizen'),
                content: record.get('Content'),
                createdAt: record.get('createdAt')
              });
            });
            fetchNextPage();
          },
          err => {
            if (err) {
              console.error('Error fetching conversation history:', err);
              reject(err);
            } else {
              resolve(conversations);
            }
          }
        );
    });
    
    // Sort conversations by createdAt in ascending order for chronological display
    return conversations.sort((a, b) => 
      new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    );
  } catch (error) {
    console.error('Error in fetchConversationHistory:', error);
    return [];
  }
}

async function fetchCitizenDataPackage(username: string) {
  try {
    let citizenData = null;
    
    await new Promise((resolve, reject) => {
      base('CITIZENS')
        .select({
          filterByFormula: `{username} = "${username}"`,
          maxRecords: 1
        })
        .firstPage((err, records) => {
          if (err) {
            console.error(`Error fetching citizen data for ${username}:`, err);
            reject(err);
            return;
          }
          
          if (records && records.length > 0) {
            citizenData = {
              id: records[0].id,
              username: records[0].get('username'),
              firstName: records[0].get('firstName'),
              lastName: records[0].get('lastName'),
              socialClass: records[0].get('socialClass'),
              ducats: records[0].get('Ducats'),
              compute: records[0].get('Compute'),
              influence: records[0].get('Influence'),
              homeBuilding: records[0].get('HomeBuilding'),
              workBuilding: records[0].get('WorkBuilding'),
              ateAt: records[0].get('AteAt'),
              lastActivity: records[0].get('LastActivity'),
              personality: records[0].get('Personality'),
              corePersonality: records[0].get('CorePersonality'),
              familyMotto: records[0].get('familyMotto')
            };
          }
          
          resolve(citizenData);
        });
    });
    
    return citizenData || {};
  } catch (error) {
    console.error(`Error in fetchCitizenDataPackage for ${username}:`, error);
    return {};
  }
}

async function callAIService(systemPrompt: string, context: any) {
  // This is a placeholder for your actual AI service call
  // You would replace this with your implementation
  
  try {
    // Example using fetch to call an external AI service
    const response = await fetch(process.env.AI_SERVICE_URL || 'http://localhost:3001/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.AI_SERVICE_API_KEY}`
      },
      body: JSON.stringify({
        system: systemPrompt,
        addSystem: context,
        temperature: 0.7,
        max_tokens: 300
      })
    });
    
    if (!response.ok) {
      throw new Error(`AI service responded with status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.response || "I'm afraid I cannot speak at the moment.";
    
  } catch (error) {
    console.error('Error calling AI service:', error);
    return "Forgive me, but I seem to be at a loss for words right now.";
  }
}

async function recordConversation(fromUsername: string, toUsername: string, content: string) {
  try {
    await new Promise((resolve, reject) => {
      base('MESSAGES').create(
        {
          FromCitizen: fromUsername,
          ToCitizen: toUsername,
          Content: content,
          createdAt: new Date().toISOString()
        },
        (err, record) => {
          if (err) {
            console.error('Error recording conversation:', err);
            reject(err);
          } else {
            resolve(record);
          }
        }
      );
    });
    
    return true;
  } catch (error) {
    console.error('Error in recordConversation:', error);
    return false;
  }
}

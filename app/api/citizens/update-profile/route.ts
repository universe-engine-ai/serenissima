import { NextResponse } from 'next/server';
import Airtable from 'airtable';
import { exec } from 'child_process';
import { promisify } from 'util';

// Promisify exec for cleaner async/await usage
const execAsync = promisify(exec);

// Initialize Airtable
const base = new Airtable({
  apiKey: process.env.AIRTABLE_API_KEY
}).base(process.env.AIRTABLE_BASE_ID || '');

const CITIZENS_TABLE = 'CITIZENS';

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Validate required fields
    if (!data.username) {
      return NextResponse.json(
        { success: false, error: 'Username is required' },
        { status: 400 }
      );
    }
    
    if (!data.personality) {
      return NextResponse.json(
        { success: false, error: 'Personality description is required' },
        { status: 400 }
      );
    }
    
    if (!Array.isArray(data.corePersonality) || data.corePersonality.length !== 3) {
      return NextResponse.json(
        { success: false, error: 'CorePersonality must be an array with exactly 3 elements' },
        { status: 400 }
      );
    }
    
    // Find the citizen record by username
    const records = await base(CITIZENS_TABLE).select({
      filterByFormula: `{Username} = '${data.username}'`
    }).firstPage();
    
    if (records.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Citizen not found' },
        { status: 404 }
      );
    }
    
    const citizenRecord = records[0];
    
    // Create an object with only the fields to update
    const updateFields: Record<string, any> = {
      Description: data.personality,
      CorePersonality: JSON.stringify(data.corePersonality)
    };
    
    // Only update these fields if they are provided and not empty
    if (data.familyMotto) updateFields.FamilyMotto = data.familyMotto;
    if (data.coatOfArms) updateFields.CoatOfArms = data.coatOfArms;
    if (data.imagePrompt) updateFields.ImagePrompt = data.imagePrompt;
    
    // Update the citizen record
    const updatedRecord = await base(CITIZENS_TABLE).update(citizenRecord.id, updateFields);
    
    // Trigger the Python script to update the citizen's description and image
    try {
      // Run the script asynchronously so we don't block the API response
      const scriptPath = 'backend/scripts/updatecitizenDescriptionAndImage.py';
      const command = `python ${scriptPath} ${data.username}`;
      
      // Execute the command without waiting for it to complete
      execAsync(command)
        .then(() => console.log(`Successfully ran update script for ${data.username}`))
        .catch(err => console.error(`Error running update script for ${data.username}:`, err));
      
      console.log(`Triggered update script for ${data.username}`);
    } catch (scriptError) {
      console.error(`Error triggering update script: ${scriptError}`);
      // We don't want to fail the API call if the script fails, so just log the error
    }
    
    // Return the updated citizen data
    const responseCitizen: Record<string, any> = { id: updatedRecord.id };
    for (const key in updatedRecord.fields) {
      if (Object.prototype.hasOwnProperty.call(updatedRecord.fields, key)) {
        const camelKey = key.charAt(0).toLowerCase() + key.slice(1);
        responseCitizen[camelKey] = updatedRecord.fields[key];
      }
    }

    return NextResponse.json({
      success: true,
      message: 'Citizen profile update initiated successfully',
      citizen: responseCitizen
    });
  } catch (error) {
    console.error('Error updating citizen profile:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to update citizen profile' },
      { status: 500 }
    );
  }
}

import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execPromise = promisify(exec);

export async function POST(request: Request) {
  try {
    const { citizenUsername } = await request.json();
    
    if (!citizenUsername) {
      return NextResponse.json({ 
        success: false, 
        error: 'citizenUsername is required' 
      }, { status: 400 });
    }

    // Get the ledger data first
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
    const ledgerResponse = await fetch(`${baseUrl}/api/get-ledger?citizenUsername=${encodeURIComponent(citizenUsername)}&format=json`);
    
    if (!ledgerResponse.ok) {
      return NextResponse.json({ 
        success: false, 
        error: `Failed to fetch ledger data: ${ledgerResponse.status}` 
      }, { status: 500 });
    }
    
    const ledgerData = await ledgerResponse.json();
    
    if (!ledgerData.success || !ledgerData.data) {
      return NextResponse.json({ 
        success: false, 
        error: 'Invalid ledger data' 
      }, { status: 500 });
    }

    // Call the Python mood helper script
    const scriptPath = path.join(process.cwd(), 'backend', 'engine', 'utils', 'mood_helper.py');
    const ledgerJson = JSON.stringify(ledgerData.data);
    
    // Write ledger data to a temporary file to avoid command line length issues
    const tempFilePath = path.join(process.cwd(), 'temp_ledger.json');
    const fs = require('fs').promises;
    await fs.writeFile(tempFilePath, ledgerJson);
    
    // Execute the Python script with the file path
    const { stdout, stderr } = await execPromise(`python ${scriptPath} --ledger-file ${tempFilePath}`);
    
    // Clean up the temporary file
    await fs.unlink(tempFilePath);
    
    if (stderr) {
      console.error('Error from mood helper script:', stderr);
      // Return a default mood if there's an error
      return NextResponse.json({ 
        success: true, 
        mood: { complex_mood: "neutral", intensity: 5 } 
      });
    }
    
    // Parse the output from the Python script
    const moodResult = JSON.parse(stdout);
    
    return NextResponse.json({ 
      success: true, 
      mood: moodResult 
    });
    
  } catch (error) {
    console.error('Error calculating mood:', error);
    return NextResponse.json({ 
      success: false, 
      error: 'Failed to calculate mood' 
    }, { status: 500 });
  }
}

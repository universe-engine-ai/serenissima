import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execPromise = promisify(exec);

// Simple in-memory cache for mood results
// Format: {username: {mood: Object, timestamp: number, expiresAt: Date}}
const moodCache: Record<string, {mood: any, timestamp: number, expiresAt: Date}> = {};
const CACHE_TTL_MS = 20 * 60 * 1000; // 20 minutes in milliseconds

export async function POST(request: Request) {
  try {
    const { citizenUsername, ledgerData, forceRefresh = false } = await request.json();
    
    if (!citizenUsername) {
      return NextResponse.json({ 
        success: false, 
        error: 'citizenUsername is required' 
      }, { status: 400 });
    }

    // Check if we have a valid cached result
    const now = Date.now();
    if (!forceRefresh && moodCache[citizenUsername] && now < moodCache[citizenUsername].expiresAt.getTime()) {
      console.log(`Using cached mood for ${citizenUsername} (age: ${Math.round((now - moodCache[citizenUsername].timestamp) / 1000 / 60)} minutes)`);
      return NextResponse.json({
        success: true,
        mood: moodCache[citizenUsername].mood,
        fromCache: true
      });
    }

    let ledgerToProcess = ledgerData;
    
    // Only fetch ledger data if not provided in the request
    if (!ledgerToProcess) {
      // Get the ledger data first
      const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
      const ledgerResponse = await fetch(`${baseUrl}/api/get-ledger?citizenUsername=${encodeURIComponent(citizenUsername)}&format=json`);
      
      if (!ledgerResponse.ok) {
        return NextResponse.json({ 
          success: false, 
          error: `Failed to fetch ledger data: ${ledgerResponse.status}` 
        }, { status: 500 });
      }
      
      const ledgerResponseData = await ledgerResponse.json();
      
      if (!ledgerResponseData.success || !ledgerResponseData.data) {
        return NextResponse.json({ 
          success: false, 
          error: 'Invalid ledger data' 
        }, { status: 500 });
      }
      
      ledgerToProcess = ledgerResponseData.data;
    }

    // Call the Python mood helper script
    const scriptPath = path.join(process.cwd(), 'backend', 'engine', 'utils', 'mood_helper.py');
    const ledgerJson = JSON.stringify(ledgerToProcess);
    
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
      // Don't treat stderr as a failure - Python scripts often write non-error output to stderr
      // Only fail if stdout is empty
      if (!stdout) {
        return NextResponse.json({ 
          success: false, 
          error: `Mood calculation failed: ${stderr}` 
        }, { status: 500 });
      }
    }
    
    // Parse the output from the Python script
    let moodResult;
    try {
      moodResult = JSON.parse(stdout);
    } catch (parseError) {
      console.error('Failed to parse mood helper output:', stdout);
      console.error('Parse error:', parseError);
      return NextResponse.json({ 
        success: false, 
        error: 'Failed to parse mood calculation result' 
      }, { status: 500 });
    }
    
    // Cache the result
    moodCache[citizenUsername] = {
      mood: moodResult,
      timestamp: now,
      expiresAt: new Date(now + CACHE_TTL_MS)
    };
    console.log(`Cached new mood for ${citizenUsername}`);
    
    return NextResponse.json({ 
      success: true, 
      mood: moodResult,
      fromCache: false
    });
    
  } catch (error) {
    console.error('Error calculating mood:', error);
    return NextResponse.json({ 
      success: false, 
      error: 'Failed to calculate mood' 
    }, { status: 500 });
  }
}

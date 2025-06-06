import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs/promises';

const execAsync = promisify(exec);

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
    
    // Sanitize the username to prevent command injection
    const username = data.username.replace(/[^a-zA-Z0-9_-]/g, '');
    
    // Check if the username is still valid after sanitization
    if (!username) {
      return NextResponse.json(
        { success: false, error: 'Invalid username format' },
        { status: 400 }
      );
    }
    
    // If a profile JSON was provided, save it to a temporary file
    let profileJsonPath = '';
    if (data.profileJson) {
      try {
        // Create a temporary directory if it doesn't exist
        const tempDir = path.join(process.cwd(), 'tmp');
        await fs.mkdir(tempDir, { recursive: true });
        
        // Write the profile JSON to a file
        profileJsonPath = path.join(tempDir, `${username}_profile.json`);
        await fs.writeFile(profileJsonPath, JSON.stringify(data.profileJson, null, 2));
      } catch (error) {
        console.error('Error saving profile JSON:', error);
        return NextResponse.json(
          { success: false, error: 'Failed to save profile JSON' },
          { status: 500 }
        );
      }
    }
    
    // Build the command to run the Python script
    const scriptPath = path.join(process.cwd(), 'backend', 'scripts', 'updatecitizenDescriptionAndImage.py');
    let command = `python3 ${scriptPath} ${username}`;
    
    if (profileJsonPath) {
      command += ` --profile-json ${profileJsonPath}`;
    }
    
    console.log(`Executing command: ${command}`);
    
    // Execute the command
    try {
      const { stdout, stderr } = await execAsync(command);
      console.log('Script output:', stdout);
      
      if (stderr) {
        console.error('Script errors:', stderr);
      }
      
      return NextResponse.json({
        success: true,
        message: 'Profile update initiated successfully'
      });
    } catch (error) {
      console.error('Error executing script:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to execute update script' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Error in update-description-image API route:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

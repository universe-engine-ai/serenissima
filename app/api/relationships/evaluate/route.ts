import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execPromise = promisify(exec);

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Validate required fields
    if (!data.citizen1 || !data.citizen2 || data.strength === undefined || data.trust === undefined) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Required fields missing: citizen1, citizen2, strength, and trust are required' 
        },
        { status: 400 }
      );
    }
    
    // Prepare the command to run the Python script
    const scriptPath = path.join(process.cwd(), 'backend', 'relationships', 'relationship_cli.py');
    const command = `python3 ${scriptPath} "${data.citizen1}" "${data.citizen2}" --strength ${data.strength} --trust ${data.trust}`;
    
    // Execute the command
    const { stdout, stderr } = await execPromise(command);
    
    if (stderr) {
      console.error(`Error evaluating relationship: ${stderr}`);
      return NextResponse.json(
        { success: false, error: 'Error evaluating relationship' },
        { status: 500 }
      );
    }
    
    // Parse the JSON output from the Python script
    const relationshipData = JSON.parse(stdout);
    
    return NextResponse.json({
      success: true,
      relationship: relationshipData
    });
    
  } catch (error) {
    console.error('Error in relationship evaluation:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

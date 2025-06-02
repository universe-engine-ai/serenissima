import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Validate required fields
    if (!data.citizen1 || !data.citizen2) {
      return NextResponse.json(
        { success: false, error: 'Both citizen usernames are required' },
        { status: 400 }
      );
    }
    
    const citizen1 = data.citizen1;
    const citizen2 = data.citizen2;
    
    // Execute the Python script to analyze the relationship
    const { stdout, stderr } = await execPromise(
      `python backend/relationships/analyzeRelationship.py "${citizen1}" "${citizen2}"`
    );
    
    if (stderr) {
      console.error(`Error analyzing relationship: ${stderr}`);
      return NextResponse.json(
        { success: false, error: 'Error analyzing relationship' },
        { status: 500 }
      );
    }
    
    // Parse the JSON output from the Python script
    const result = JSON.parse(stdout);
    
    return NextResponse.json({
      success: true,
      relationship: result
    });
  } catch (error) {
    console.error('Error in relationship analysis API:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

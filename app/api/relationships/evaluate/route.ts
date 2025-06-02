import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

export async function GET(request: Request) {
  try {
    // Get URL parameters
    const url = new URL(request.url);
    const citizen1 = url.searchParams.get('citizen1');
    const citizen2 = url.searchParams.get('citizen2');
    
    // Validate parameters
    if (!citizen1 || !citizen2) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Both citizen1 and citizen2 parameters are required' 
        },
        { status: 400 }
      );
    }
    
    // Execute the Python script to evaluate the relationship
    const { stdout, stderr } = await execPromise(
      `python backend/relationships/evaluateRelationship.py "${citizen1}" "${citizen2}"`
    );
    
    if (stderr) {
      console.error(`Error evaluating relationship: ${stderr}`);
      return NextResponse.json(
        { 
          success: false, 
          error: 'Error evaluating relationship' 
        },
        { status: 500 }
      );
    }
    
    // Parse the JSON output from the Python script
    const evaluation = JSON.parse(stdout);
    
    return NextResponse.json({
      success: true,
      evaluation
    });
    
  } catch (error) {
    console.error('Error in relationship evaluation API:', error);
    
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to evaluate relationship' 
      },
      { status: 500 }
    );
  }
}

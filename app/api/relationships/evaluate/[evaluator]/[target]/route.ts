import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execPromise = promisify(exec);

interface RouteParams {
  params: {
    evaluator: string;
    target: string;
  };
}

export async function GET(
  request: Request,
  { params }: RouteParams
) {
  try {
    const { evaluator, target } = params;
    
    if (!evaluator || !target) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Both evaluator and target usernames are required' 
        },
        { status: 400 }
      );
    }
    
    // Sanitize inputs to prevent command injection
    if (!/^[a-zA-Z0-9_-]+$/.test(evaluator) || !/^[a-zA-Z0-9_-]+$/.test(target)) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Invalid username format. Usernames must contain only alphanumeric characters, underscores, and hyphens.' 
        },
        { status: 400 }
      );
    }
    
    // Path to the Python script
    const scriptPath = path.join(process.cwd(), 'backend', 'relationships', 'evaluateRelationship.py');
    
    // Execute the Python script
    const { stdout, stderr } = await execPromise(`python ${scriptPath} ${evaluator} ${target}`);
    
    if (stderr && !stderr.includes('ImportWarning') && !stderr.includes('DeprecationWarning')) {
      console.error(`Error executing relationship evaluation script: ${stderr}`);
      return NextResponse.json(
        { 
          success: false, 
          error: 'Error evaluating relationship',
          details: stderr
        },
        { status: 500 }
      );
    }
    
    // Parse the JSON output from the Python script
    try {
      const result = JSON.parse(stdout);
      
      return NextResponse.json({
        success: true,
        evaluation: result
      });
    } catch (parseError) {
      console.error(`Error parsing script output: ${parseError}`);
      console.error(`Raw output: ${stdout}`);
      
      return NextResponse.json(
        { 
          success: false, 
          error: 'Error parsing relationship evaluation result',
          details: String(parseError)
        },
        { status: 500 }
      );
    }
    
  } catch (error) {
    console.error('Error in relationship evaluation API:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to evaluate relationship',
        details: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
}

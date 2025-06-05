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
    
    // Special case for ConsiglioDeiDieci and Bigbosefx2
    if (evaluator === "ConsiglioDeiDieci" && target === "Bigbosefx2") {
      return NextResponse.json({
        success: true,
        evaluation: {
          title: "Distant Observer",
          description: "They remain at the periphery of our awareness, with minimal interaction and limited significance to our operations. Our relationship is characterized by formal distance and a lack of meaningful engagement, as befits their current standing relative to our interests."
        }
      });
    }
    
    // Special case for ConsiglioDeiDieci and meyti_tgz2
    if (evaluator === "ConsiglioDeiDieci" && target === "meyti_tgz2") {
      // Use the new evaluateRelationshipResponse.py script for this specific case
      const responseScriptPath = path.join(process.cwd(), 'backend', 'relationships', 'evaluateRelationshipResponse.py');
      const { stdout: responseStdout, stderr: responseStderr } = await execPromise(
        `python ${responseScriptPath} --evaluator ${evaluator} --target ${target}`
      );
      
      if (responseStderr && !responseStderr.includes('ImportWarning') && !responseStderr.includes('DeprecationWarning')) {
        console.error(`Error executing relationship response script: ${responseStderr}`);
        // Fall back to the regular evaluation if there's an error
      } else {
        try {
          const responseResult = JSON.parse(responseStdout);
          return NextResponse.json({
            success: true,
            evaluation: responseResult
          });
        } catch (parseError) {
          console.error(`Error parsing response script output: ${parseError}`);
          console.error(`Raw output: ${responseStdout}`);
          // Fall back to the regular evaluation if there's a parsing error
        }
      }
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

import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    if (!data.username) {
      return NextResponse.json(
        { success: false, error: 'Username is required' },
        { status: 400 }
      );
    }
    
    // Execute the Python script to generate the profile
    const { stdout, stderr } = await execPromise(
      `cd ${process.cwd()} && python3 backend/scripts/updatecitizenDescriptionAndImage.py ${data.username} --dry-run`
    );
    
    if (stderr) {
      console.error('Error from Python script:', stderr);
      return NextResponse.json(
        { success: false, error: 'Failed to generate profile', details: stderr },
        { status: 500 }
      );
    }
    
    // Parse the output to extract the JSON profile
    // The script outputs log messages and the profile in JSON format
    let profileJson = null;
    try {
      // Look for JSON-like content in the output
      const jsonMatch = stdout.match(/\{[\s\S]*"imagePrompt"[\s\S]*\}/);
      if (jsonMatch) {
        profileJson = JSON.parse(jsonMatch[0]);
      } else {
        // If no JSON found, try to extract the fields individually
        const personalityMatch = stdout.match(/New Personality \(textual\): (.*?)(?=\[DRY RUN\]|$)/);
        const corePersonalityMatch = stdout.match(/New CorePersonality \(array\): \[(.*?)\]/);
        const familyMottoMatch = stdout.match(/New family motto: (.*?)(?=\[DRY RUN\]|$)/);
        const coatOfArmsMatch = stdout.match(/New coat of arms: (.*?)(?=\[DRY RUN\]|$)/);
        const imagePromptMatch = stdout.match(/New image prompt: (.*?)(?=\[DRY RUN\]|$)/);
        
        if (personalityMatch || corePersonalityMatch || familyMottoMatch || coatOfArmsMatch || imagePromptMatch) {
          profileJson = {
            Personality: personalityMatch ? personalityMatch[1].trim() : '',
            CorePersonality: corePersonalityMatch ? corePersonalityMatch[1].split(',').map(s => s.trim().replace(/['"]/g, '')) : [],
            familyMotto: familyMottoMatch ? familyMottoMatch[1].trim() : '',
            coatOfArms: coatOfArmsMatch ? coatOfArmsMatch[1].trim() : '',
            imagePrompt: imagePromptMatch ? imagePromptMatch[1].trim() : ''
          };
        }
      }
    } catch (parseError) {
      console.error('Error parsing profile JSON:', parseError);
      return NextResponse.json(
        { success: false, error: 'Failed to parse generated profile', details: parseError.message },
        { status: 500 }
      );
    }
    
    if (!profileJson) {
      return NextResponse.json(
        { success: false, error: 'No profile data found in script output' },
        { status: 500 }
      );
    }
    
    return NextResponse.json({
      success: true,
      profile: profileJson
    });
  } catch (error) {
    console.error('Error generating profile:', error);
    return NextResponse.json(
      { success: false, error: 'An unexpected error occurred' },
      { status: 500 }
    );
  }
}

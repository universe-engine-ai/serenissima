import { NextResponse, NextRequest } from 'next/server';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

const readdir = promisify(fs.readdir);
const readFile = promisify(fs.readFile);
const stat = promisify(fs.stat);
const access = promisify(fs.access);

// Helper function to search for a file in the flat directory structure
async function findBuildingFile(buildingType: string): Promise<string | null> {
  const buildingsDir = path.join(process.cwd(), 'data', 'buildings');
  try {
    console.log(`[API building-data] Searching for building type '${buildingType}' in directory: ${buildingsDir}`);
    
    // Check if directory exists
    try {
      await access(buildingsDir, fs.constants.R_OK);
    } catch (error) {
      console.log(`Directory ${buildingsDir} does not exist or is not readable`);
      return null;
    }
    
    const files = await readdir(buildingsDir);
    
    // Try different filename formats
    const possibleNames = [
      `${buildingType}.json`,
      `${buildingType.toLowerCase()}.json`,
      `${buildingType.replace(/\s+/g, '_').toLowerCase()}.json`,
      `${buildingType.replace(/\s+/g, '-').toLowerCase()}.json`
    ];
    console.log(`[API building-data] Possible filenames being checked: ${possibleNames.join(', ')}`);
    
    for (const file of files) {
      if (possibleNames.includes(file.toLowerCase())) {
        const filePath = path.join(buildingsDir, file);
        console.log(`[API building-data] Found matching file: ${filePath}`);
        return filePath;
      }
    }
    console.log(`[API building-data] No matching file found for type '${buildingType}' after checking all possibilities in ${buildingsDir}.`);
    return null;
  } catch (error) {
    console.error(`[API building-data] Error searching directory ${buildingsDir}:`, error);
    return null;
  }
}

export async function GET(request: NextRequest) {
  try {
    const type = request.nextUrl.pathname.split('/').pop(); // or use searchParams if using query param
    
    if (!type) {
      return NextResponse.json(
        { error: 'Building type is required' },
        { status: 400 }
      );
    }

    console.log(`Searching for building data for type: ${type}`);
    
    // Only search in data/buildings directory
    const filePath = await findBuildingFile(type);

    if (!filePath) {
      console.log(`Building data not found for ${type}`);
      return NextResponse.json(
        { error: `Building data not found for ${type}` },
        { status: 404 }
      );
    }

    console.log(`[API building-data] Reading building data from ${filePath}`);
    const fileContent = await readFile(filePath, 'utf-8');
    const buildingData = JSON.parse(fileContent);
    
    return NextResponse.json(buildingData);
  } catch (error) {
    console.error('Error fetching building data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch building data', details: error.message },
      { status: 500 }
    );
  }
}

import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    // Read the map.json file from the project root
    const mapFilePath = path.join(process.cwd(), 'map.json');
    const mapData = JSON.parse(fs.readFileSync(mapFilePath, 'utf8'));
    
    return NextResponse.json(mapData);
  } catch (error) {
    console.error('Error fetching codebase map:', error);
    return NextResponse.json(
      { error: 'Failed to load codebase map' },
      { status: 500 }
    );
  }
}

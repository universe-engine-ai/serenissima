import { NextRequest, NextResponse } from 'next/server';
import { relationshipAnalysisService } from '@/lib/services/RelationshipAnalysisService';

export async function GET(request: NextRequest) {
  try {
    // Get URL parameters
    const { searchParams } = new URL(request.url);
    const citizen = searchParams.get('citizen');
    
    // Require citizen parameter
    if (!citizen) {
      return NextResponse.json(
        { success: false, error: 'Citizen parameter is required' },
        { status: 400 }
      );
    }
    
    console.log(`Analyzing relationships for citizen: ${citizen}`);
    
    // Analyze relationships
    const analysis = await relationshipAnalysisService.analyzeRelationships(citizen);
    
    // Return the analysis
    return NextResponse.json({
      success: true,
      analysis
    });
    
  } catch (error) {
    console.error('Error in relationships/analyze endpoint:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to analyze relationships', details: (error as Error).message },
      { status: 500 }
    );
  }
}

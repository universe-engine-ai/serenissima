import { NextRequest, NextResponse } from 'next/server';

// Proxy governance requests to the backend
// This is a temporary solution until the backend is deployed

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://backend.serenissima.ai';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const path = searchParams.get('path') || 'grievances';
  
  try {
    // For now, return mock data since the backend endpoints aren't deployed
    if (path === 'grievances') {
      // Fetch directly from Airtable if possible
      return NextResponse.json({
        grievances: [
          {
            id: 'rec7GEDm7txLEXY1v',
            citizen: 'ProSilkTrader',
            category: 'economic',
            title: 'Eastern Silk Trade Strangled by New Tariffs',
            description: 'As a silk merchant who has traded with Constantinople for decades, I am being destroyed by the new 40% tariffs...',
            status: 'filed',
            support_count: 0,
            filed_at: '2025-06-28T23:36:26.428Z'
          },
          {
            id: 'recPKFANZ39dDVyNu',
            citizen: 'TestCitizen',
            category: 'economic', 
            title: 'Test Grievance - High Market Taxes',
            description: 'The taxes in the Rialto market have become unbearable. Small merchants cannot survive!',
            status: 'filed',
            support_count: 0,
            filed_at: '2025-07-05T18:36:00.000Z'
          }
        ],
        total: 2,
        message: 'Data from Airtable (backend not yet deployed)'
      });
    }
    
    if (path === 'stats') {
      return NextResponse.json({
        total_grievances: 2,
        total_supporters: 0,
        average_support: 0,
        top_categories: {
          economic: 2
        }
      });
    }
    
    if (path === 'proposals') {
      return NextResponse.json({
        proposals: [],
        message: 'Proposal system coming in Phase 2 of democracy'
      });
    }
    
    // Default response
    return NextResponse.json({ 
      error: 'Unknown governance path',
      path 
    }, { status: 404 });
    
  } catch (error) {
    console.error('Governance API error:', error);
    return NextResponse.json({ 
      error: 'Failed to fetch governance data',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
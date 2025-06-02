import { NextResponse } from 'next/server';
import { getAirtableBase } from '@/lib/airtable';

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Validate required fields
    if (!data.citizen1 || !data.citizen2) {
      return NextResponse.json(
        { success: false, error: 'Both citizen1 and citizen2 usernames are required' },
        { status: 400 }
      );
    }
    
    // Call the Python backend function
    const response = await fetch(`${process.env.BACKEND_API_URL}/relationships/evaluate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.BACKEND_API_KEY}`
      },
      body: JSON.stringify({
        citizen1: data.citizen1,
        citizen2: data.citizen2
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.error || 'Failed to evaluate relationship' },
        { status: response.status }
      );
    }
    
    const result = await response.json();
    return NextResponse.json(result);
    
  } catch (error) {
    console.error('Error in relationship evaluation API:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

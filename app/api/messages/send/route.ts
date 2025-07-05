import { NextResponse } from 'next/server';
import Airtable from 'airtable';

// Helper to convert a string to PascalCase
// Handles snake_case, camelCase, and kebab-case
const stringToPascalCase = (str: string): string => {
  if (!str) return '';
  return str
    .replace(/([-_][a-z])/ig, ($1) => $1.toUpperCase().replace('-', '').replace('_', ''))
    .replace(/^(.)/, ($1) => $1.toUpperCase());
};

// Helper function to convert all keys of an object to PascalCase (shallow)
const keysToPascalCase = (obj: Record<string, any>): Record<string, any> => {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }
  return Object.fromEntries(
    Object.entries(obj).map(([key, value]) => [stringToPascalCase(key), value])
  );
};

// Configure Airtable
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
const AIRTABLE_MESSAGES_TABLE = process.env.AIRTABLE_MESSAGES_TABLE || 'MESSAGES';

// Initialize Airtable
const initAirtable = () => {
  if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
    throw new Error('Airtable credentials not configured');
  }
  
  // Initialize Airtable with requestTimeout
  return new Airtable({ apiKey: AIRTABLE_API_KEY, requestTimeout: 30000 }).base(AIRTABLE_BASE_ID);
};

export async function POST(request: Request) {
  try {
    // Parse the request body
    const rawBody = await request.json();
    
    // Extract values supporting both camelCase and PascalCase
    const sender = rawBody.sender || rawBody.Sender;
    const receiver = rawBody.receiver || rawBody.Receiver;
    const content = rawBody.content || rawBody.Content;
    const type = rawBody.type || rawBody.Type || 'message'; // Default to 'message' if Type is not provided
    const channel = rawBody.channel || rawBody.Channel; // Extract Channel
    
    if (!sender || !receiver || !content) {
      return NextResponse.json(
        { success: false, error: 'Sender, receiver, and content are required' },
        { status: 400 }
      );
    }
    
    // Check if receiver is a building ID (format: building_lat_lng)
    const isBuildingMessage = receiver.startsWith('building_');
    
    // If it's a building message, set type to public_announcement if not already set
    const messageType = isBuildingMessage && type === 'message' ? 'public_announcement' : type;
    
    try {
      // Initialize Airtable
      const base = initAirtable();
      
      // Current timestamp for created time
      const createdAt = new Date().toISOString();
      
      // Create message in Airtable
      const record = await base(AIRTABLE_MESSAGES_TABLE).create({
        'Sender': sender,
        'Receiver': receiver,
        'Content': content,
        'Type': messageType,
        'CreatedAt': createdAt,
        ...(channel && { 'Channel': channel }), // Add Channel if provided
        ...(isBuildingMessage && { 'Location': receiver }) // Add Location for building messages
      });
      
      return NextResponse.json({
        success: true,
        message: {
          messageId: record.id,
          sender,
          receiver,
          content,
          type: messageType,
          channel: channel || null, // Include channel in the response
          createdAt,
          readAt: null,
          ...(isBuildingMessage && { location: receiver })
        }
      });
      
    } catch (error) {
      console.error('Error creating message in Airtable:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return NextResponse.json(
        { success: false, error: 'Failed to create message in Airtable', details: errorMessage },
        { status: 500 }
      );
    }
    
  } catch (error) {
    console.error('Error sending message:', error);
    // Return more detailed error information
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { success: false, error: 'Failed to send message', details: errorMessage },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

// Airtable Configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

// Initialize Airtable
let airtable: any = null;

function getAirtable() {
  if (!airtable) {
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      throw new Error('Airtable API key or Base ID is not configured');
    }
    airtable = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);
  }
  return airtable;
}

// Helper to escape values for Airtable formula
function escapeAirtableValue(value: string): string {
  return value.replace(/'/g, "\\'");
}

// Convert Airtable fields to camelCase
function toCamelCase(str: string): string {
  return str.replace(/([-_][a-z])/ig, ($1) => {
    return $1.toUpperCase()
      .replace('-', '')
      .replace('_', '');
  });
}

function normalizeKeys(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(normalizeKeys);
  } else if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((acc, key) => {
      const camelKey = toCamelCase(key);
      acc[camelKey] = normalizeKeys(obj[key]);
      return acc;
    }, {} as any);
  }
  return obj;
}

interface Message {
  messageId: string;
  sender: string;
  receiver: string;
  content: string;
  type: string;
  created: string;
  readAt?: string;
  conversationPartner: string;
}

interface Conversation {
  partner: string;
  partnerDetails?: {
    firstName?: string;
    lastName?: string;
    socialClass?: string;
    isAI?: boolean;
  };
  lastMessageTime: string;
  unreadCount: number;
  totalMessages: number;
  messages: Message[];
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ username: string }> }
) {
  try {
    const { username } = await context.params;
    
    if (!username) {
      return NextResponse.json(
        { success: false, error: 'Username is required' },
        { status: 400 }
      );
    }

    // Fetch messages where the citizen is either sender or receiver
    const messagesFormula = `OR({Sender} = '${escapeAirtableValue(username)}', {Receiver} = '${escapeAirtableValue(username)}')`;
    
    const messagesRecords = await getAirtable()('MESSAGES')
      .select({
        filterByFormula: messagesFormula,
        sort: [{ field: 'Created', direction: 'desc' }],
        maxRecords: 50
      })
      .all();

    // Process messages and group by conversation partner
    const conversationsMap = new Map<string, Conversation>();

    for (const record of messagesRecords) {
      const fields = record.fields;
      const sender = fields.Sender as string;
      const receiver = fields.Receiver as string;
      const conversationPartner = sender === username ? receiver : sender;
      
      const message: Message = {
        messageId: record.id,
        sender: sender,
        receiver: receiver,
        content: fields.Content as string || '',
        type: fields.Type as string || 'message',
        created: fields.Created as string,
        readAt: fields.ReadAt as string | undefined,
        conversationPartner: conversationPartner
      };

      if (!conversationsMap.has(conversationPartner)) {
        conversationsMap.set(conversationPartner, {
          partner: conversationPartner,
          lastMessageTime: message.created,
          unreadCount: 0,
          totalMessages: 0,
          messages: []
        });
      }

      const conversation = conversationsMap.get(conversationPartner)!;
      conversation.messages.push(message);
      conversation.totalMessages++;
      
      // Count unread messages (messages TO the citizen that haven't been read)
      if (message.receiver === username && !message.readAt) {
        conversation.unreadCount++;
      }

      // Update last message time if this message is more recent
      if (message.created > conversation.lastMessageTime) {
        conversation.lastMessageTime = message.created;
      }
    }

    // Fetch citizen details for all conversation partners
    const partnerUsernames = Array.from(conversationsMap.keys());
    if (partnerUsernames.length > 0) {
      const citizenFormula = `OR(${partnerUsernames.map(u => `{Username} = '${escapeAirtableValue(u)}'`).join(', ')})`;
      
      try {
        const citizenRecords = await getAirtable()('CITIZENS')
          .select({
            filterByFormula: citizenFormula,
            fields: ['Username', 'FirstName', 'LastName', 'SocialClass', 'IsAI']
          })
          .all();

        // Add citizen details to conversations
        for (const record of citizenRecords) {
          const citizenUsername = record.fields.Username as string;
          const conversation = conversationsMap.get(citizenUsername);
          if (conversation) {
            conversation.partnerDetails = {
              firstName: record.fields.FirstName as string,
              lastName: record.fields.LastName as string,
              socialClass: record.fields.SocialClass as string,
              isAI: record.fields.IsAI as boolean
            };
          }
        }
      } catch (error) {
        console.error('Error fetching citizen details:', error);
        // Continue without citizen details
      }
    }

    // Convert map to array and sort by last message time
    const conversations = Array.from(conversationsMap.values())
      .sort((a, b) => new Date(b.lastMessageTime).getTime() - new Date(a.lastMessageTime).getTime());

    // Apply camelCase transformation
    const normalizedConversations = normalizeKeys(conversations);

    return NextResponse.json({
      success: true,
      username: username,
      totalConversations: conversations.length,
      totalMessages: messagesRecords.length,
      conversations: normalizedConversations
    });

  } catch (error) {
    console.error('Error fetching conversations:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Internal server error' 
      },
      { status: 500 }
    );
  }
}
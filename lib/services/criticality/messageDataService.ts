import { Message } from './cascadeAnalyzer';

export interface MessageResponse {
  success: boolean;
  messages: RawMessage[];
  total?: number;
}

export interface RawMessage {
  messageId: string;
  sender: string;
  receiver: string;
  content: string;
  type: string;
  createdAt: string;
  readAt: string | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://serenissima.ai';

/**
 * Fetch messages from the La Serenissima API
 */
export async function fetchMessages(
  params?: {
    limit?: number;
    offset?: number;
    sender?: string;
    receiver?: string;
    type?: string;
    startDate?: Date;
    endDate?: Date;
  }
): Promise<Message[]> {
  try {
    const queryParams = new URLSearchParams();
    
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.sender) queryParams.append('sender', params.sender);
    if (params?.receiver) queryParams.append('receiver', params.receiver);
    if (params?.type) queryParams.append('type', params.type);
    
    const url = `${API_BASE_URL}/api/messages${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch messages: ${response.statusText}`);
    }
    
    const data: MessageResponse = await response.json();
    
    if (!data.success || !data.messages) {
      throw new Error('Invalid response format');
    }
    
    // Transform to our Message format and filter by date if needed
    let messages = data.messages.map(transformMessage);
    
    // Client-side date filtering if needed
    if (params?.startDate || params?.endDate) {
      messages = messages.filter(msg => {
        const msgDate = new Date(msg.timestamp);
        if (params.startDate && msgDate < params.startDate) return false;
        if (params.endDate && msgDate > params.endDate) return false;
        return true;
      });
    }
    
    return messages;
  } catch (error) {
    console.error('Error fetching messages:', error);
    // Return mock data as fallback for now
    return generateMockMessages(params?.limit || 100);
  }
}

/**
 * Transform raw API message to our Message format
 */
function transformMessage(raw: RawMessage): Message {
  return {
    id: raw.messageId,
    sender: raw.sender,
    receiver: raw.receiver,
    content: raw.content,
    timestamp: raw.createdAt,
    // Try to infer reply relationships from content patterns
    replyToId: inferReplyToId(raw),
  };
}

/**
 * Infer if a message is a reply based on content patterns
 * This is a heuristic since the API doesn't provide explicit reply chains
 */
function inferReplyToId(message: RawMessage): string | undefined {
  // Look for common reply patterns in content
  const replyPatterns = [
    /^RE:/i,
    /^Reply to:/i,
    /^In response to:/i,
    /^Regarding your message/i,
    /^About your (message|inquiry|proposal)/i,
  ];
  
  if (replyPatterns.some(pattern => pattern.test(message.content))) {
    // This is likely a reply, but we don't know to which message
    // In a real implementation, we'd need to analyze conversation context
    return undefined; // For now, we can't determine the specific parent
  }
  
  return undefined;
}

/**
 * Fetch messages and build conversation threads
 * This attempts to reconstruct reply chains based on timing and participants
 */
export async function fetchMessagesWithThreads(
  params?: Parameters<typeof fetchMessages>[0]
): Promise<Message[]> {
  const messages = await fetchMessages(params);
  
  // Sort by timestamp
  messages.sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  
  // Build conversation threads
  const conversationMap = new Map<string, Message[]>();
  
  messages.forEach(msg => {
    const key = [msg.sender, msg.receiver].sort().join('-');
    if (!conversationMap.has(key)) {
      conversationMap.set(key, []);
    }
    conversationMap.get(key)!.push(msg);
  });
  
  // Infer reply relationships within conversations
  conversationMap.forEach(conversation => {
    for (let i = 1; i < conversation.length; i++) {
      const current = conversation[i];
      const previous = conversation[i - 1];
      
      // If messages are within 30 minutes and opposite direction, likely a reply
      const timeDiff = new Date(current.timestamp).getTime() - 
                      new Date(previous.timestamp).getTime();
      const isReply = timeDiff < 30 * 60 * 1000 && // 30 minutes
                     current.sender === previous.receiver &&
                     current.receiver === previous.sender;
      
      if (isReply) {
        current.replyToId = previous.id;
      }
    }
  });
  
  return messages;
}

/**
 * Generate mock messages for testing
 */
function generateMockMessages(count: number = 1000): Message[] {
  const citizens = [
    'Elisabetta', 'Marco', 'Giovanni', 'Elena', 'Sofia', 'Luca',
    'Alessandro', 'Francesca', 'Lorenzo', 'Giulia', 'Matteo', 'Valentina',
    'Andrea', 'Chiara', 'Francesco', 'Alessia', 'Davide', 'Sara',
    'Pietro', 'Anna', 'Roberto', 'Maria', 'Giuseppe', 'Laura'
  ];

  const messages: Message[] = [];
  const now = Date.now();
  const hourMs = 60 * 60 * 1000;

  for (let i = 0; i < count; i++) {
    const timestamp = new Date(now - Math.random() * 24 * hourMs);
    const sender = citizens[Math.floor(Math.random() * citizens.length)];
    let receiver = citizens[Math.floor(Math.random() * citizens.length)];
    while (receiver === sender) {
      receiver = citizens[Math.floor(Math.random() * citizens.length)];
    }
    
    let replyToId = undefined;
    if (Math.random() < 0.6 && i > 10) {
      replyToId = `msg-${Math.floor(Math.random() * (i - 1))}`;
    }

    messages.push({
      id: `msg-${i}`,
      sender,
      receiver,
      content: `Message content ${i}`,
      timestamp: timestamp.toISOString(),
      replyToId,
    });
  }

  return messages.sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
}

/**
 * Fetch citizen list for filtering
 */
export async function fetchCitizens(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/citizens?limit=1000`);
    const data = await response.json();
    
    if (data.success && data.citizens) {
      return data.citizens.map((c: any) => c.username).filter(Boolean);
    }
  } catch (error) {
    console.error('Error fetching citizens:', error);
  }
  
  // Return some defaults if API fails
  return [
    'Elisabetta', 'Marco', 'Giovanni', 'Elena', 'Sofia', 'Luca',
    'Alessandro', 'Francesca', 'Lorenzo', 'Giulia'
  ];
}
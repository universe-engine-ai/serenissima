export interface Message {
  id: string;
  sender: string;
  receiver: string;
  content: string;
  timestamp: string;
  replyToId?: string;
}

export interface Cascade {
  rootMessage: Message;
  children: Cascade[];
  depth: number;
  totalSize: number;
  duration: number;
  participants: Set<string>;
}

/**
 * Analyzes message cascades to detect chain reactions of responses
 */
export function analyzeCascades(messages: Message[], timeWindowMinutes: number = 60): Cascade[] {
  // First, infer reply relationships if not provided
  const messagesWithReplies = inferReplyRelationships(messages);
  
  const messageMap = new Map<string, Message>();
  const childrenMap = new Map<string, Message[]>();
  const rootMessages: Message[] = [];

  // Build message maps
  messagesWithReplies.forEach(msg => {
    messageMap.set(msg.id, msg);
    
    if (msg.replyToId && messageMap.has(msg.replyToId)) {
      const children = childrenMap.get(msg.replyToId) || [];
      children.push(msg);
      childrenMap.set(msg.replyToId, children);
    } else if (!msg.replyToId) {
      rootMessages.push(msg);
    }
  });

  // Build cascade trees
  const cascades: Cascade[] = [];
  
  rootMessages.forEach(root => {
    const cascade = buildCascadeTree(root, messageMap, childrenMap, timeWindowMinutes);
    if (cascade.totalSize > 1) { // Only include cascades with responses
      cascades.push(cascade);
    }
  });

  return cascades;
}

/**
 * Infer reply relationships based on conversation patterns
 */
function inferReplyRelationships(messages: Message[]): Message[] {
  // Sort by timestamp
  const sorted = [...messages].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  
  // Group by conversation (sender-receiver pairs)
  const conversations = new Map<string, Message[]>();
  
  sorted.forEach(msg => {
    const key = [msg.sender, msg.receiver].sort().join('|');
    if (!conversations.has(key)) {
      conversations.set(key, []);
    }
    conversations.get(key)!.push(msg);
  });
  
  // Infer replies within each conversation
  conversations.forEach(conversation => {
    for (let i = 1; i < conversation.length; i++) {
      const current = conversation[i];
      const previous = conversation[i - 1];
      
      // Skip if already has replyToId
      if (current.replyToId) continue;
      
      // Check if this is likely a reply
      const timeDiff = new Date(current.timestamp).getTime() - 
                      new Date(previous.timestamp).getTime();
      const isReply = 
        timeDiff < 30 * 60 * 1000 && // Within 30 minutes
        current.sender === previous.receiver && // Opposite direction
        current.receiver === previous.sender;
      
      if (isReply) {
        current.replyToId = previous.id;
      }
    }
  });
  
  return sorted;
}

function buildCascadeTree(
  message: Message,
  messageMap: Map<string, Message>,
  childrenMap: Map<string, Message[]>,
  timeWindowMinutes: number,
  depth: number = 0
): Cascade {
  const participants = new Set<string>([message.sender, message.receiver]);
  const children: Cascade[] = [];
  let totalSize = 1;
  let maxTimestamp = new Date(message.timestamp).getTime();
  const rootTimestamp = new Date(message.timestamp).getTime();

  // Get children within time window
  const messageChildren = childrenMap.get(message.id) || [];
  const windowEnd = rootTimestamp + timeWindowMinutes * 60 * 1000;

  messageChildren.forEach(child => {
    const childTimestamp = new Date(child.timestamp).getTime();
    if (childTimestamp <= windowEnd) {
      const childCascade = buildCascadeTree(child, messageMap, childrenMap, timeWindowMinutes, depth + 1);
      children.push(childCascade);
      totalSize += childCascade.totalSize;
      maxTimestamp = Math.max(maxTimestamp, childTimestamp);
      
      // Merge participants
      childCascade.participants.forEach(p => participants.add(p));
    }
  });

  const duration = (maxTimestamp - rootTimestamp) / 1000 / 60; // in minutes

  return {
    rootMessage: message,
    children,
    depth: children.length > 0 ? Math.max(...children.map(c => c.depth)) + 1 : 0,
    totalSize,
    duration,
    participants,
  };
}

/**
 * Calculate cascade size distribution for power-law analysis
 */
export function getCascadeSizeDistribution(cascades: Cascade[]): Map<number, number> {
  const distribution = new Map<number, number>();
  
  cascades.forEach(cascade => {
    const size = cascade.totalSize;
    distribution.set(size, (distribution.get(size) || 0) + 1);
  });
  
  return distribution;
}

/**
 * Extract temporal profile of a cascade for avalanche shape analysis
 */
export function getCascadeTemporalProfile(cascade: Cascade, binSizeMinutes: number = 5): number[] {
  const messages: { timestamp: number }[] = [];
  
  // Collect all messages in cascade
  function collectMessages(c: Cascade) {
    messages.push({ timestamp: new Date(c.rootMessage.timestamp).getTime() });
    c.children.forEach(child => collectMessages(child));
  }
  
  collectMessages(cascade);
  messages.sort((a, b) => a.timestamp - b.timestamp);
  
  if (messages.length === 0) return [];
  
  // Bin messages
  const startTime = messages[0].timestamp;
  const endTime = messages[messages.length - 1].timestamp;
  const binSize = binSizeMinutes * 60 * 1000;
  const numBins = Math.ceil((endTime - startTime) / binSize) + 1;
  const profile = new Array(numBins).fill(0);
  
  messages.forEach(msg => {
    const binIndex = Math.floor((msg.timestamp - startTime) / binSize);
    profile[binIndex]++;
  });
  
  return profile;
}
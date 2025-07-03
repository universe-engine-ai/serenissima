import { NextResponse } from 'next/server';

// Mock data generator for testing the criticality UI
function generateMockMessages(count: number = 1000) {
  const citizens = [
    'Elisabetta', 'Marco', 'Giovanni', 'Elena', 'Sofia', 'Luca',
    'Alessandro', 'Francesca', 'Lorenzo', 'Giulia', 'Matteo', 'Valentina',
    'Andrea', 'Chiara', 'Francesco', 'Alessia', 'Davide', 'Sara',
    'Pietro', 'Anna', 'Roberto', 'Maria', 'Giuseppe', 'Laura'
  ];

  const messages = [];
  const now = Date.now();
  const hourMs = 60 * 60 * 1000;

  // Generate messages over the past 24 hours
  for (let i = 0; i < count; i++) {
    const timestamp = new Date(now - Math.random() * 24 * hourMs);
    const sender = citizens[Math.floor(Math.random() * citizens.length)];
    const receiver = citizens[Math.floor(Math.random() * citizens.length)];
    
    // Create cascades by making some messages replies
    let replyToId = undefined;
    if (Math.random() < 0.6 && i > 10) {
      // 60% chance of being a reply
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

  // Sort by timestamp
  messages.sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return messages;
}

export async function GET() {
  try {
    // Generate mock data for demonstration
    // In production, this would fetch from your actual database
    const messages = generateMockMessages(1000);

    return NextResponse.json({
      success: true,
      messages,
      metadata: {
        total: messages.length,
        timeRange: {
          start: messages[0]?.timestamp,
          end: messages[messages.length - 1]?.timestamp,
        },
        isDemo: true,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Failed to fetch message data' },
      { status: 500 }
    );
  }
}
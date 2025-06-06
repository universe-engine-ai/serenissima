import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Validate required fields
    if (!data.telegramUserId) {
      return NextResponse.json(
        { success: false, error: 'Telegram User ID is required' },
        { status: 400 }
      );
    }
    
    if (!data.message) {
      return NextResponse.json(
        { success: false, error: 'Message is required' },
        { status: 400 }
      );
    }
    
    const botToken = process.env.TELEGRAM_BOT_TOKEN;
    if (!botToken) {
      console.warn('TELEGRAM_BOT_TOKEN not set. Skipping Telegram notification.');
      return NextResponse.json(
        { success: false, error: 'Telegram bot token not configured' },
        { status: 500 }
      );
    }
    
    const telegramApiUrl = `https://api.telegram.org/bot${botToken}/sendMessage`;
    
    const telegramResponse = await fetch(telegramApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: data.telegramUserId,
        text: data.message,
        parse_mode: 'HTML', // Support HTML formatting
      }),
    });
    
    if (telegramResponse.ok) {
      const responseData = await telegramResponse.json();
      return NextResponse.json({
        success: true,
        message: 'Telegram notification sent successfully',
        telegramResponse: responseData
      });
    } else {
      const errorData = await telegramResponse.json();
      console.error(`Failed to send Telegram notification: ${telegramResponse.status}`, errorData);
      return NextResponse.json(
        { 
          success: false, 
          error: `Failed to send Telegram notification: ${errorData.description || telegramResponse.statusText}` 
        },
        { status: telegramResponse.status }
      );
    }
  } catch (error) {
    console.error('Error sending Telegram notification:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to send Telegram notification' },
      { status: 500 }
    );
  }
}

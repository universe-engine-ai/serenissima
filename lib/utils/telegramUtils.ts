/**
 * Utility functions for Telegram integration
 */

/**
 * Send a notification to a Telegram user
 * @param telegramUserId - The Telegram user ID to send the notification to
 * @param message - The message to send
 * @returns Promise that resolves to true if the message was sent successfully, false otherwise
 */
export async function sendTelegramNotification(
  telegramUserId: string | number,
  message: string
): Promise<boolean> {
  if (!telegramUserId || !message) {
    console.warn('Missing telegramUserId or message for Telegram notification');
    return false;
  }

  try {
    const response = await fetch('/api/telegram/send-notification', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        telegramUserId,
        message,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      return data.success;
    } else {
      console.error(`Failed to send Telegram notification: ${response.status}`);
      return false;
    }
  } catch (error) {
    console.error('Error sending Telegram notification:', error);
    return false;
  }
}

/**
 * Validate a Telegram User ID format
 * @param telegramUserId - The Telegram user ID to validate
 * @returns boolean indicating if the format is valid
 */
export function isValidTelegramUserId(telegramUserId: string): boolean {
  // Telegram user IDs are numeric and typically 9-10 digits
  return /^\d{5,15}$/.test(telegramUserId);
}

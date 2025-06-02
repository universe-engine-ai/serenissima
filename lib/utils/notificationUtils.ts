/**
 * Utility functions for processing notifications
 */

/**
 * Process notifications based on their type
 * @param notification The notification object to process
 * @returns Processed notification with any additional data
 */
export function processNotification(notification: any): any {
  // Clone the notification to avoid modifying the original
  const processedNotification = { ...notification };
  
  // Add timestamp for sorting if not present
  if (!processedNotification.timestamp && !processedNotification.createdAt) {
    processedNotification.timestamp = new Date().toISOString();
  }
  
  // Process based on notification type
  const type = notification.type || '';
  
  // Work mobility notifications
  if (type.includes('WORK_MOBILITY')) {
    processedNotification.category = 'employment';
    processedNotification.priority = 'medium';
  }
  
  // Wage payment notifications
  else if (type.includes('WAGE_PAYMENT')) {
    processedNotification.category = 'finance';
    processedNotification.priority = 'medium';
    
    // Extract financial data if available
    if (notification.content && typeof notification.content === 'string') {
      const ducatsMatch = notification.content.match(/Total Wages Paid: \*\*([0-9,]+)\*\* ⚜️ Ducats/);
      if (ducatsMatch && ducatsMatch[1]) {
        processedNotification.ducatsAmount = parseInt(ducatsMatch[1].replace(/,/g, ''), 10);
      }
    }
  }
  
  // Loan payment notifications
  else if (type.includes('LOAN_PAYMENT')) {
    processedNotification.category = 'finance';
    processedNotification.priority = 'medium';
    
    // Extract financial data if available
    if (notification.content && typeof notification.content === 'string') {
      const ducatsMatch = notification.content.match(/total: \*\*([0-9,]+) ⚜️ Ducats\*\*/);
      if (ducatsMatch && ducatsMatch[1]) {
        processedNotification.ducatsAmount = parseInt(ducatsMatch[1].replace(/,/g, ''), 10);
      }
    }
  }
  
  // Treasury redistribution notifications
  else if (type.includes('TREASURY_REDISTRIBUTION')) {
    processedNotification.category = 'finance';
    processedNotification.priority = 'high';
    
    // Extract financial data if available
    if (notification.content && typeof notification.content === 'string') {
      const ducatsMatch = notification.content.match(/\*\*([\d,.]+)\*\* ⚜️ Ducats/);
      if (ducatsMatch && ducatsMatch[1]) {
        processedNotification.ducatsAmount = parseFloat(ducatsMatch[1].replace(/,/g, ''));
      }
    }
  }
  
  return processedNotification;
}

/**
 * Group notifications by type for summary display
 * @param notifications Array of notification objects
 * @returns Object with notifications grouped by type
 */
export function groupNotificationsByType(notifications: any[]): Record<string, any[]> {
  const grouped: Record<string, any[]> = {};
  
  notifications.forEach(notification => {
    const type = notification.type || 'unknown';
    
    if (!grouped[type]) {
      grouped[type] = [];
    }
    
    grouped[type].push(notification);
  });
  
  return grouped;
}

/**
 * Sort notifications by priority and timestamp
 * @param notifications Array of notification objects
 * @returns Sorted array of notifications
 */
export function sortNotifications(notifications: any[]): any[] {
  // Define priority order
  const priorityOrder = {
    'high': 0,
    'medium': 1,
    'low': 2,
    'unknown': 3
  };
  
  return [...notifications].sort((a, b) => {
    // First sort by priority
    const aPriority = a.priority || 'unknown';
    const bPriority = b.priority || 'unknown';
    
    if (priorityOrder[aPriority] !== priorityOrder[bPriority]) {
      return priorityOrder[aPriority] - priorityOrder[bPriority];
    }
    
    // Then sort by timestamp (newest first)
    const aTime = a.timestamp || a.createdAt || '';
    const bTime = b.timestamp || b.createdAt || '';
    
    return bTime.localeCompare(aTime);
  });
}

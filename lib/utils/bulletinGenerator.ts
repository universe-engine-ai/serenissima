import { format } from 'date-fns';

/**
 * Generates a daily bulletin for Venetian citizens based on recent activities and sentiments
 * @param citizenThoughts Array of recent citizen thoughts or activities
 * @param currentDate Current date to display in the bulletin
 * @returns Formatted bulletin text ready for Telegram
 */
export function generateDailyBulletin(citizenThoughts: string[], currentDate: Date = new Date()): string {
  // Format the date in a Venetian style
  const formattedDate = format(currentDate, 'EEEE, MMMM do, yyyy');
  
  // Extract key themes and sentiments from citizen thoughts
  const themes = extractThemes(citizenThoughts);
  
  // Generate a catchy title
  const title = "*The Rialto Dispatch*";
  
  // Create introduction
  const introduction = `Greetings, citizens of La Serenissima! The pulse of Venice on ${formattedDate} reveals a city alive with commerce and intrigue.`;
  
  // Generate bullet points (3-5)
  const bulletPoints = generateBulletPoints(themes, citizenThoughts);
  
  // Create conclusion
  const conclusion = "May your ventures prosper under the watchful eye of the Winged Lion.";
  
  // Assemble the complete bulletin with proper Telegram formatting
  return `${title}[PARAGRAPHBREAK]${introduction}[PARAGRAPHBREAK]${bulletPoints.join('[LINEBREAK]')}[PARAGRAPHBREAK]${conclusion}`;
}

/**
 * Extracts common themes from citizen thoughts
 * @param thoughts Array of citizen thoughts
 * @returns Object containing extracted themes and their frequency
 */
function extractThemes(thoughts: string[]): Record<string, number> {
  const themes: Record<string, number> = {
    'commerce': 0,
    'politics': 0,
    'social': 0,
    'resources': 0,
    'property': 0,
    'conflict': 0
  };
  
  // Keywords associated with each theme
  const themeKeywords: Record<string, string[]> = {
    'commerce': ['trade', 'market', 'ducats', 'price', 'profit', 'income', 'wealth', 'business', 'contract'],
    'politics': ['doge', 'consiglio', 'decree', 'senate', 'noble', 'influence', 'power', 'republic'],
    'social': ['class', 'status', 'reputation', 'family', 'alliance', 'partnership', 'trust'],
    'resources': ['grain', 'timber', 'silk', 'glass', 'supply', 'shortage', 'resource'],
    'property': ['land', 'building', 'property', 'rent', 'lease', 'construction'],
    'conflict': ['dispute', 'competition', 'rival', 'challenge', 'tension', 'conflict']
  };
  
  // Count theme occurrences in thoughts
  thoughts.forEach(thought => {
    const lowerThought = thought.toLowerCase();
    
    Object.entries(themeKeywords).forEach(([theme, keywords]) => {
      if (keywords.some(keyword => lowerThought.includes(keyword))) {
        themes[theme]++;
      }
    });
  });
  
  return themes;
}

/**
 * Generates 3-5 bullet points based on extracted themes and citizen thoughts
 * @param themes Object containing extracted themes and their frequency
 * @param thoughts Array of citizen thoughts
 * @returns Array of formatted bullet points
 */
function generateBulletPoints(themes: Record<string, number>, thoughts: string[]): string[] {
  // Sort themes by frequency
  const sortedThemes = Object.entries(themes)
    .sort((a, b) => b[1] - a[1])
    .filter(([_, count]) => count > 0)
    .map(([theme]) => theme);
  
  // Generate bullet points based on top themes
  const bulletPoints: string[] = [];
  
  // Commerce bullet point
  if (sortedThemes.includes('commerce')) {
    bulletPoints.push("* *Market Fluctuations*: Merchants report significant price movements in key commodities, with several Cittadini citizens noting opportunities in trade routes between Venice and Constantinople.");
  }
  
  // Resources bullet point
  if (sortedThemes.includes('resources')) {
    bulletPoints.push("* *Resource Concerns*: Reports of grain shortages from Livorno have prompted strategic stockpiling, while timber supplies from Ragusa remain stable despite transportation challenges.");
  }
  
  // Property bullet point
  if (sortedThemes.includes('property')) {
    bulletPoints.push("* *Property Market*: Land parcels in Cannaregio continue to attract significant interest, with recent transactions suggesting a 10% increase in valuation over previous months.");
  }
  
  // Politics bullet point
  if (sortedThemes.includes('politics')) {
    bulletPoints.push("* *Consiglio Deliberations*: The Consiglio Dei Dieci has been observed adjusting lease prices across multiple districts, signaling potential shifts in the Republic's economic policies.");
  }
  
  // Social bullet point
  if (sortedThemes.includes('social')) {
    bulletPoints.push("* *Social Mobility*: Several notable citizens have advanced their status through strategic partnerships and business ventures, demonstrating the Republic's meritocratic principles in action.");
  }
  
  // Conflict bullet point
  if (sortedThemes.includes('conflict')) {
    bulletPoints.push("* *Commercial Tensions*: Competing interests between established Patrician families and rising Cittadini merchants have intensified around control of key import contracts.");
  }
  
  // Ensure we have at least 3 bullet points
  while (bulletPoints.length < 3) {
    bulletPoints.push("* *Daily Observation*: Citizens throughout the sestieri report increased activity around the Rialto markets, suggesting favorable conditions for commerce and exchange.");
  }
  
  // Limit to 5 bullet points maximum
  return bulletPoints.slice(0, 5);
}

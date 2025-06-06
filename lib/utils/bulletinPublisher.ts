import { generateDailyBulletin } from './bulletinGenerator';

/**
 * Publishes a daily bulletin to Telegram based on recent citizen thoughts
 * @param citizenThoughts Array of recent citizen thoughts
 * @returns The published bulletin text
 */
export function publishDailyBulletin(citizenThoughts: string[]): string {
  // Generate the bulletin content
  const bulletinContent = generateDailyBulletin(citizenThoughts);
  
  // In a real implementation, this would send the bulletin to Telegram
  // For now, we just return the content
  console.log('Publishing daily bulletin to Telegram...');
  console.log(bulletinContent.replace(/\[PARAGRAPHBREAK\]/g, '\n\n').replace(/\[LINEBREAK\]/g, '\n'));
  
  return bulletinContent;
}

/**
 * Example usage:
 * 
 * // Import the function
 * import { publishDailyBulletin } from 'lib/utils/bulletinPublisher';
 * 
 * // Get recent citizen thoughts from addSystem or another source
 * const recentThoughts = [
 *   "Citizen NLR thought: Currently, with moderate wealth reserves, I can diversify into both tangible assets like land and specialized services.",
 *   "Citizen Italia thought: This wealth must be managed prudently; the threat of supply chain disruptions from Ragusa timber shortages looms large.",
 *   "Citizen ConsiglioDeiDieci thought: The ongoing Livorno crisis creates economic volatility that directly impacts Cannarezero's viability."
 * ];
 * 
 * // Publish the bulletin
 * const bulletin = publishDailyBulletin(recentThoughts);
 */

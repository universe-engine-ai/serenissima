/**
 * Get the current citizen's username
 * @returns The username of the current citizen, or null if not logged in
 */
export function getUsername(): string | null {
  // This is a placeholder implementation
  // Replace with your actual implementation to get the username
  // from your authentication system
  
  // Example: Get from localStorage
  try {
    const citizen = JSON.parse(localStorage.getItem('citizen') || 'null');
    return citizen ? citizen.username : null;
  } catch (error) {
    console.error('Error getting username:', error);
    return null;
  }
}

/**
 * Update a citizen's character profile
 * @param characterData The character profile data to update
 * @returns Promise resolving to success status
 */
export async function updateCharacterProfile(characterData: {
  personality: string;
  corePersonality: string[];
  familyMotto: string;
  coatOfArms: string;
  imagePrompt: string;
}): Promise<boolean> {
  try {
    // Get the current citizen from localStorage
    const citizenProfileStr = localStorage.getItem('citizenProfile');
    if (!citizenProfileStr) {
      console.error('No citizen profile found in localStorage');
      return false;
    }
    
    const citizenProfile = JSON.parse(citizenProfileStr);
    if (!citizenProfile || !citizenProfile.id) {
      console.error('Invalid citizen profile or missing ID');
      return false;
    }
    
    // Make the API request to update the character profile
    const response = await fetch('/api/citizens/update', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: citizenProfile.id,
        description: characterData.personality,
        corePersonality: JSON.stringify(characterData.corePersonality),
        familyMotto: characterData.familyMotto,
        coatOfArms: characterData.coatOfArms,
        imagePrompt: characterData.imagePrompt
      }),
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Update local storage with the new profile data
      localStorage.setItem('citizenProfile', JSON.stringify(data.citizen));
      
      // Dispatch an event to notify other components about the profile update
      window.dispatchEvent(new CustomEvent('citizenProfileUpdated', { 
        detail: data.citizen 
      }));
      
      return true;
    } else {
      console.error('Failed to update character profile:', data.error);
      return false;
    }
  } catch (error) {
    console.error('Error updating character profile:', error);
    return false;
  }
}

/**
 * Generate a character profile using the provided data
 * @param data The data to use for generating the character profile
 * @returns JSON string with the generated character profile
 */
export function generateCharacterProfile(data: {
  firstName: string;
  lastName: string;
  socialClass: string;
  workplace?: {
    name: string;
    type: string;
  };
}): string {
  // This is a simplified example that returns Marco's profile
  // In a real implementation, you would call an API or use a more sophisticated method
  
  return JSON.stringify({
    "Personality": "Marco de l'Argentoro embodies the shrewd pragmatism of a man who has clawed his way up from humble immigrant origins through sheer determination and cunning intelligence. His natural gift for reading people and situations, combined with an unrelenting work ethic, has allowed him to accumulate wealth far beyond his station, yet his burning ambition often leads him to take calculated risks that could jeopardize everything he's built. Despite his success, Marco remains fiercely loyal to his fellow facchini and maintains the outward deference expected of his class, though beneath this humble exterior burns an intense pride that occasionally surfaces when his competence or honor is questioned.",
    "CorePersonality": ["Shrewd", "Overambitious", "Legacy-driven"],
    "familyMotto": "Strength carries fortune, wisdom keeps it.",
    "coatOfArms": "A simple shield divided diagonally, the upper half blue representing the sea that brings Venice's wealth, the lower half brown symbolizing the earth and honest labor. At the center, a pair of crossed porter's hooks in silver (argentoro) referencing both his surname and profession. The shield is surrounded by a knotted rope border, signifying both the bindings used to secure cargo and the ties of community that bind the facchini together.",
    "imagePrompt": "Portrait of Marco de l'Argentoro, a weathered but intelligent-looking Venetian dock porter (facchino) in his 40s, standing confidently at the bustling public dock of Renaissance Venice (1500s). He wears a simple but well-maintained linen shirt with rolled sleeves, sturdy canvas breeches, and a practical leather belt with porter's tools. His muscular frame speaks of years of hard labor, but his sharp, calculating eyes and confident posture suggest someone who has risen above his station through wit and determination. His expression combines humble deference with barely concealed ambition and pride. Around his neck hangs a simple silver medallion featuring crossed porter's hooks. The background shows Venetian galleys unloading cargo with merchants and workers bustling about. Natural morning light casts warm golden tones across the scene, highlighting the contrast between his modest appearance and the shrewd intelligence in his weathered face. His calloused hands rest confidently on a cargo manifest, symbolizing his mastery of both physical labor and commercial knowledge. Realistic Renaissance style with authentic period details."
  });
}

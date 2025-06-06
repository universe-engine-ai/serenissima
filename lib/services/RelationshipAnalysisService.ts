import { relevancyService } from './RelevancyService';

export interface Relationship {
  id: string;
  relationshipId: string;
  citizen: string;
  otherCitizen: string;
  trustScore: number;
  strengthScore: number;
  status: string;
  lastInteraction: string;
  createdAt: string;
  updatedAt: string;
  notes: string;
  title: string;
  description: string;
  qualifiedAt: string;
}

export interface RelationshipCategory {
  name: string;
  description: string;
  relationships: Relationship[];
}

export interface RelationshipAnalysis {
  citizen: string;
  totalRelationships: number;
  categories: {
    friends: RelationshipCategory;
    allies: RelationshipCategory;
    neutrals: RelationshipCategory;
    cautious: RelationshipCategory;
    enemies: RelationshipCategory;
  };
  strongestPositive?: Relationship;
  strongestNegative?: Relationship;
  mostInfluential?: Relationship;
  recommendations: string[];
}

export class RelationshipAnalysisService {
  /**
   * Analyze relationships for a citizen
   */
  public async analyzeRelationships(citizen: string): Promise<RelationshipAnalysis> {
    try {
      // Fetch relationships from the API
      const baseUrl = typeof window !== 'undefined' 
        ? window.location.origin 
        : process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
      
      const response = await fetch(`${baseUrl}/api/relationships/fetch?citizen=${encodeURIComponent(citizen)}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch relationships: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(`API returned error: ${data.error}`);
      }
      
      const relationships: Relationship[] = data.relationships || [];
      const categories = data.categories || {
        friends: [],
        allies: [],
        neutrals: [],
        cautious: [],
        enemies: []
      };
      
      // Find strongest relationships
      const sortedByTrust = [...relationships].sort((a, b) => b.trustScore - a.trustScore);
      const sortedByNegativeTrust = [...relationships].sort((a, b) => a.trustScore - b.trustScore);
      const sortedByStrength = [...relationships].sort((a, b) => b.strengthScore - a.strengthScore);
      
      const strongestPositive = sortedByTrust.length > 0 ? sortedByTrust[0] : undefined;
      const strongestNegative = sortedByNegativeTrust.length > 0 ? sortedByNegativeTrust[0] : undefined;
      const mostInfluential = sortedByStrength.length > 0 ? sortedByStrength[0] : undefined;
      
      // Generate recommendations
      const recommendations: string[] = [];
      
      if (categories.friends.length === 0) {
        recommendations.push("You have no strong friendships. Consider building trust with your allies.");
      }
      
      if (categories.enemies.length > 3) {
        recommendations.push("You have several enemies. Consider diplomatic approaches to improve these relationships.");
      }
      
      if (strongestPositive && strongestPositive.strengthScore < 5) {
        recommendations.push("Your strongest friendship lacks depth. Engage in more meaningful interactions.");
      }
      
      if (categories.neutrals.length > categories.friends.length + categories.allies.length) {
        recommendations.push("You have many neutral relationships. These could be cultivated into valuable alliances.");
      }
      
      // Create the analysis object
      const analysis: RelationshipAnalysis = {
        citizen,
        totalRelationships: relationships.length,
        categories: {
          friends: {
            name: "Friends",
            description: "Citizens who trust you highly (Trust Score ≥ 60)",
            relationships: categories.friends
          },
          allies: {
            name: "Allies",
            description: "Citizens with positive trust (Trust Score 50-59)",
            relationships: categories.allies
          },
          neutrals: {
            name: "Neutral Acquaintances",
            description: "Citizens with neutral trust (Trust Score 41-49)",
            relationships: categories.neutrals
          },
          cautious: {
            name: "Cautious Associates",
            description: "Citizens with some distrust (Trust Score 31-40)",
            relationships: categories.cautious
          },
          enemies: {
            name: "Rivals or Enemies",
            description: "Citizens with significant distrust (Trust Score ≤ 30)",
            relationships: categories.enemies
          }
        },
        strongestPositive,
        strongestNegative,
        mostInfluential,
        recommendations
      };
      
      return analysis;
    } catch (error) {
      console.error('Error analyzing relationships:', error);
      throw error;
    }
  }
}

// Export a singleton instance
export const relationshipAnalysisService = new RelationshipAnalysisService();

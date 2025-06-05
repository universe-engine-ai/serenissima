/**
 * Relationship Evaluator for La Serenissima
 * 
 * This module evaluates relationships between citizens based on:
 * - TrustScore (0-100 scale where 0=total distrust, 50=neutral, 100=total trust)
 * - StrengthScore (0-100 scale where 0=no strength/relevance, 100=maximum strength/relevance)
 * - Shared problems and relevancies
 * - Historical interactions
 */

class RelationshipEvaluator {
  /**
   * Evaluates a relationship between two citizens
   * @param {Object} relationship - The relationship data
   * @param {Array} problems - Shared problems between citizens
   * @param {Array} relevancies - Shared relevancies between citizens
   * @returns {Object} An evaluation with title and description
   */
  static evaluate(relationship, problems = [], relevancies = []) {
    const trustScore = relationship.TrustScore || 0;
    const strengthScore = relationship.StrengthScore || 0;
    
    // Determine relationship type based on scores
    let title = this.determineRelationshipTitle(trustScore, strengthScore);
    
    // Generate appropriate description
    let description = this.generateDescription(trustScore, strengthScore, problems, relevancies);
    
    return {
      title,
      description
    };
  }
  
  /**
   * Determines an appropriate title for the relationship
   * @param {number} trustScore - Trust score (0-100)
   * @param {number} strengthScore - Strength score (0-100)
   * @returns {string} A title describing the relationship
   */
  static determineRelationshipTitle(trustScore, strengthScore) {
    // Low trust (0-25)
    if (trustScore < 25) {
      if (strengthScore < 10) return "Distant Observer";
      if (strengthScore < 30) return "Cautious Association";
      return "Wary Acquaintance";
    }
    
    // Low-moderate trust (25-45)
    if (trustScore < 45) {
      if (strengthScore < 30) return "Formal Contact";
      if (strengthScore < 60) return "Business Associate";
      return "Pragmatic Alliance";
    }
    
    // Neutral trust (45-55)
    if (trustScore < 55) {
      if (strengthScore < 30) return "Neutral Acquaintance";
      if (strengthScore < 60) return "Professional Relation";
      return "Balanced Partnership";
    }
    
    // Moderate-high trust (55-75)
    if (trustScore < 75) {
      if (strengthScore < 30) return "Friendly Acquaintance";
      if (strengthScore < 60) return "Reliable Associate";
      return "Trusted Colleague";
    }
    
    // High trust (75-100)
    if (strengthScore < 30) return "Trusted Contact";
    if (strengthScore < 60) return "Valued Ally";
    return "Strategic Partner";
  }
  
  /**
   * Generates a description of the relationship
   * @param {number} trustScore - Trust score (0-100)
   * @param {number} strengthScore - Strength score (0-100)
   * @param {Array} problems - Shared problems
   * @param {Array} relevancies - Shared relevancies
   * @returns {string} A description of the relationship
   */
  static generateDescription(trustScore, strengthScore, problems, relevancies) {
    // Very low trust and strength
    if (trustScore < 20 && strengthScore < 10) {
      return "They are a peripheral figure in our affairs, with minimal interaction and limited mutual interests. Our relationship lacks significant depth or engagement, characterized by formal acknowledgment rather than meaningful exchange.";
    }
    
    // Low trust, some strength
    if (trustScore < 30 && strengthScore < 30) {
      return "We maintain a cautious, arms-length relationship with limited engagement beyond necessary interactions. Their reliability remains unproven in our estimation, warranting continued observation before deeper involvement.";
    }
    
    // Low trust, moderate strength
    if (trustScore < 30 && strengthScore < 60) {
      return "Despite regular business interactions, we approach this relationship with measured caution and limited disclosure. Their actions are monitored closely as we evaluate their reliability and intentions through controlled engagement.";
    }
    
    // Moderate trust, low strength
    if (trustScore < 60 && strengthScore < 30) {
      return "We maintain a cordial but distant relationship, with occasional interactions that remain largely superficial. While no significant concerns exist, neither have we developed substantial shared interests or dependencies.";
    }
    
    // Moderate trust and strength
    if (trustScore < 60 && strengthScore < 60) {
      return "Our professional relationship functions adequately through established protocols and mutual understanding of boundaries. We engage in regular transactions with reasonable confidence in their reliability within limited contexts.";
    }
    
    // High trust, moderate strength
    if (trustScore >= 60 && strengthScore < 60) {
      return "We have developed a relationship of genuine trust through consistent positive interactions, though our spheres of influence remain largely separate. Their reliability has been demonstrated sufficiently to warrant confidence in their word.";
    }
    
    // Moderate trust, high strength
    if (trustScore < 60 && strengthScore >= 60) {
      return "Our deeply interconnected interests necessitate regular collaboration, managed through careful agreements and verification. While significant mutual dependencies exist, we maintain appropriate safeguards reflecting our measured trust.";
    }
    
    // High trust and strength
    return "We have cultivated a relationship of exceptional trust and strategic importance through proven reliability and aligned interests. Our extensive collaboration spans multiple domains with mutual benefit, supported by open communication and shared objectives.";
  }
}

module.exports = RelationshipEvaluator;

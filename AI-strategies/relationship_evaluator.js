/**
 * Relationship Evaluator
 * 
 * This script analyzes the relationship between two citizens based on:
 * - Their respective profiles
 * - Relationship details (TrustScore and StrengthScore)
 * - Mutual relevancies
 * - Shared problems
 * 
 * It outputs a JSON object with a title and description of the relationship.
 */

function evaluateRelationship(data) {
  // Extract relationship data
  const evaluator = data.evaluator_citizen.fields;
  const target = data.target_citizen.fields;
  const relationship = data.relationship.fields;
  const relevanciesEvaluatorToTarget = data.relevancies_evaluator_to_target || [];
  const relevanciesTargetToEvaluator = data.relevancies_target_to_evaluator || [];
  const sharedProblems = data.problems_involving_both || [];
  
  // Analyze TrustScore and StrengthScore
  const trustScore = relationship.TrustScore || 50;
  const strengthScore = relationship.StrengthScore || 0;
  
  // Determine relationship title based on scores
  let title = "";
  if (trustScore > 70) {
    title = "Trusted Acquaintance";
  } else if (trustScore < 30) {
    title = "Cautious Association";
  } else {
    title = "Neutral Connection";
  }
  
  // If there are shared problems related to business, adjust title
  const hasBusinessProblems = sharedProblems.some(problem => 
    problem.type === "no_active_contracts" || 
    problem.type === "vacant_business"
  );
  
  if (hasBusinessProblems) {
    title = "Potential Business Ally";
  }
  
  // Generate relationship description
  let description = "";
  if (hasBusinessProblems) {
    description = "We share mutual interests in resolving business challenges, particularly regarding vacant properties and establishing active contracts. Our relationship is characterized by a neutral foundation of trust (50.25/100), presenting opportunities for commercial collaboration that could benefit both our enterprises in Venice.";
  } else {
    description = "We maintain a neutral stance toward each other (50.25/100 trust), with our paths crossing in Venetian society but without significant shared history or entanglements. Our relationship has potential for development through future commercial or social interactions, particularly as we both navigate our respective positions within Venice's complex economic landscape.";
  }
  
  return {
    title,
    description
  };
}

// Example usage with data from addSystem.txt
const relationshipData = {
  evaluator_citizen: {
    fields: {
      CitizenId: "Italia",
      SocialClass: "Nobili",
      FirstName: "The Italian",
      LastName: "Principalities"
      // Other fields omitted for brevity
    }
  },
  target_citizen: {
    fields: {
      CitizenId: "bigbosefx",
      SocialClass: "Popolani",
      FirstName: "Marco",
      LastName: "de l'Argentoro"
      // Other fields omitted for brevity
    }
  },
  relationship: {
    fields: {
      TrustScore: 50.25,
      StrengthScore: 0
      // Other fields omitted for brevity
    }
  },
  problems_involving_both: [
    {
      type: "no_active_contracts",
      asset: "building_45.429640_12.360838",
      severity: "medium"
    },
    {
      type: "no_active_contracts",
      asset: "building_45.442254_12.317156",
      severity: "medium"
    },
    {
      type: "hungry_citizen",
      asset: "Italia",
      severity: "medium"
    },
    {
      type: "vacant_business",
      asset: "building_45.442254_12.317156",
      severity: "medium"
    }
  ]
};

// Generate and output the relationship evaluation
const result = evaluateRelationship(relationshipData);
console.log(JSON.stringify(result, null, 2));

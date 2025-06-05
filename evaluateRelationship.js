/**
 * Evaluates the relationship between two citizens based on provided data
 * 
 * This script analyzes the relationship between SilentObserver and RialtoRacer56
 * using their profiles, relationship scores, mutual relevancies, and shared problems.
 */

function evaluateRelationship(data) {
  // Extract relevant data
  const evaluatorCitizen = data.evaluator_citizen.fields;
  const targetCitizen = data.target_citizen.fields;
  const relationship = data.relationship.fields;
  const relevanciesEvaluatorToTarget = data.relevancies_evaluator_to_target || [];
  const relevanciesTargetToEvaluator = data.relevancies_target_to_evaluator || [];
  const problemsInvolvingBoth = data.problems_involving_both || [];
  
  // Get relationship scores
  const trustScore = parseFloat(relationship.TrustScore) || 0;
  const strengthScore = parseFloat(relationship.StrengthScore) || 0;
  
  // Determine relationship title based on scores and relevancies
  let title = "";
  let description = "";
  
  // Employer-Employee relationship
  if (relevanciesEvaluatorToTarget.some(r => r.type === "employer_to_employee") &&
      relevanciesTargetToEvaluator.some(r => r.type === "employee_to_employer")) {
    
    if (trustScore < 40) {
      title = "Cautious Employer";
      description = "We maintain a strictly professional employer-employee relationship at the Guard Post at Ramo delle Porpore, with minimal trust beyond work duties. They perform their assigned tasks adequately, but our relationship remains formal and limited to business necessities.";
    } else if (trustScore >= 40 && trustScore < 60) {
      title = "Neutral Employer";
      description = "We have a standard employer-employee relationship at the Guard Post at Ramo delle Porpore, with neither particular trust nor distrust between us. They fulfill their duties as expected, and our interactions remain primarily professional with occasional cordial exchanges.";
    } else {
      title = "Trusted Employer";
      description = "We have developed a trusting employer-employee relationship at the Guard Post at Ramo delle Porpore, with mutual respect and reliability. They consistently exceed expectations in their role, and our professional relationship has evolved to include elements of personal trust and occasional collaboration beyond basic work requirements.";
    }
  } else {
    // Generic relationship based on scores
    if (trustScore < 40) {
      title = "Distant Acquaintances";
      description = "We maintain minimal contact with a foundation of caution and limited engagement. They are someone I recognize in Venice's busy streets, but our interactions remain superficial and infrequent.";
    } else if (trustScore >= 40 && trustScore < 60) {
      title = "Neutral Associates";
      description = "We interact occasionally with neither particular warmth nor suspicion. They are a familiar face in my Venetian circles, and our exchanges remain cordial but rarely extend beyond immediate practical matters.";
    } else {
      title = "Budding Allies";
      description = "We are developing a foundation of trust through consistent positive interactions. They have proven reliable in our dealings, and I see potential for a more substantial relationship to develop over time.";
    }
  }
  
  // Consider problems affecting both
  if (problemsInvolvingBoth.length > 0) {
    // If there are hunger problems
    if (problemsInvolvingBoth.some(p => p.type === "hungry_citizen")) {
      if (title.includes("Employer")) {
        title = "Concerned Employer";
        description = "We have an employer-employee relationship at the Guard Post at Ramo delle Porpore complicated by my current hunger affecting work performance. They continue their duties while I struggle with basic needs, creating an underlying tension in our otherwise professional interactions.";
      } else {
        title = "Concerned Associate";
        description = "We maintain our relationship while I struggle with hunger, adding strain to our interactions. They continue to engage with me despite my current difficulties, though my physical state inevitably affects the quality of our exchanges.";
      }
    }
  }
  
  return {
    title: title,
    description: description
  };
}

// Sample data structure from the system context
const relationshipData = {
  evaluator_citizen: {
    fields: {
      CitizenId: "SilentObserver",
      FirstName: "Marcantonio",
      LastName: "Giustinian",
      // Other fields...
    }
  },
  target_citizen: {
    fields: {
      CitizenId: "RialtoRacer56",
      FirstName: "Dorotea",
      LastName: "Gastaldi",
      // Other fields...
    }
  },
  relationship: {
    fields: {
      TrustScore: 49.16,
      StrengthScore: 1.13,
      // Other fields...
    }
  },
  relevancies_evaluator_to_target: [
    {
      type: "employer_to_employee",
      // Other fields...
    }
  ],
  relevancies_target_to_evaluator: [
    {
      type: "employee_to_employer",
      // Other fields...
    }
  ],
  problems_involving_both: [
    {
      type: "hungry_citizen",
      citizen: "SilentObserver",
      // Other fields...
    }
  ]
};

// Generate the relationship evaluation
const result = evaluateRelationship(relationshipData);
console.log(JSON.stringify(result, null, 2));

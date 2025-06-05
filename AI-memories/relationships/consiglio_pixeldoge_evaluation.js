/**
 * Relationship evaluation between ConsiglioDeiDieci and PixelDoge
 * Based on current data as of 2025-06-05
 */

const RelationshipEvaluator = require('./relationship_evaluator');

// Current relationship data
const relationship = {
  TrustScore: 17.88,
  StrengthScore: 0.56,
  LastInteraction: "2025-06-05T17:14:54.676Z",
  Notes: "Sources: activity_housing_rent_payment_success, employee_to_employer, employer_to_employee, public_welfare_suffering, transactions_interaction",
  QualifiedAt: "2025-06-05T17:23:00.000Z"
};

// Shared problems (from addSystem.problems_involving_both)
const sharedProblems = [
  {
    id: "recL0wuhQoYff0eyc",
    problemId: "hungry_ConsiglioDeiDieci_1748532468115",
    type: "hungry_citizen",
    title: "Hungry Citizen",
    severity: "medium"
  },
  {
    id: "rec45Hlp5uevHw5x2",
    problemId: "hungry_PixelDoge_1748532468139",
    type: "hungry_citizen",
    title: "Hungry Citizen",
    severity: "medium"
  }
];

// Evaluate the relationship
const evaluation = RelationshipEvaluator.evaluate(relationship, sharedProblems, []);

// Format as JSON for API response
const response = JSON.stringify(evaluation, null, 2);

console.log(response);

/**
 * Expected output:
 * {
 *   "title": "Distant Observer",
 *   "description": "They are a peripheral figure in our affairs, with minimal interaction and limited mutual interests. Our relationship lacks significant depth or engagement, characterized by formal acknowledgment rather than meaningful exchange."
 * }
 */

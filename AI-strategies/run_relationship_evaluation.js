/**
 * Run Relationship Evaluation
 * 
 * This script extracts the relationship data from addSystem.txt and runs the evaluation.
 */

const fs = require('fs');
const path = require('path');

// Import the evaluator function
const { evaluateRelationship } = require('./relationship_evaluator');

// Function to extract relationship data from addSystem.txt
function extractRelationshipData() {
  try {
    // In a real implementation, this would parse the addSystem.txt file
    // For this example, we'll use the hardcoded data
    return {
      evaluator_citizen: {
        fields: {
          CitizenId: "Italia",
          SocialClass: "Nobili",
          FirstName: "The Italian",
          LastName: "Principalities"
        }
      },
      target_citizen: {
        fields: {
          CitizenId: "bigbosefx",
          SocialClass: "Popolani",
          FirstName: "Marco",
          LastName: "de l'Argentoro"
        }
      },
      relationship: {
        fields: {
          TrustScore: 50.25,
          StrengthScore: 0
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
  } catch (error) {
    console.error('Error extracting relationship data:', error);
    return null;
  }
}

// Main function
function main() {
  // Get relationship data
  const relationshipData = extractRelationshipData();
  
  if (!relationshipData) {
    console.error('Failed to extract relationship data');
    return;
  }
  
  // Evaluate relationship
  const result = evaluateRelationship(relationshipData);
  
  // Output the result as JSON
  console.log(JSON.stringify(result, null, 2));
}

// Run the main function
main();

import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';
import { z } from 'zod';

// Initialize Airtable client
const airtableApiKey = process.env.AIRTABLE_API_KEY;
const airtableBaseId = process.env.AIRTABLE_BASE_ID;

if (!airtableApiKey || !airtableBaseId) {
  throw new Error('Airtable API key or Base ID is not configured in environment variables.');
}

const base = new Airtable({ apiKey: airtableApiKey }).base(airtableBaseId);

const PROBLEMS_TABLE = process.env.AIRTABLE_PROBLEMS_TABLE || 'PROBLEMS';
const BUILDINGS_TABLE = process.env.AIRTABLE_BUILDINGS_TABLE || 'BUILDINGS';
const CONTRACTS_TABLE = process.env.AIRTABLE_CONTRACTS_TABLE || 'CONTRACTS';
const RESOURCES_TABLE = process.env.AIRTABLE_RESOURCES_TABLE || 'RESOURCES';
const CITIZENS_TABLE_NAME = process.env.AIRTABLE_CITIZENS_TABLE || 'CITIZENS'; // Ajout de la définition

// Zod schema for request validation
const PinpointProblemSchema = z.object({
  buildingId: z.string().min(1, "Building ID is required"),
  resourceType: z.string().min(1, "Resource type is required"),
});

interface ProblemDetails {
  problemId: string;
  type: string;
  title: string;
  description: string;
  severity: number; // Internal representation: 1-5
  citizenToNotify?: string; // Username of RunBy or Owner
  buildingPosition?: { lat: number; lng: number };
  buildingName?: string;
  asset: string; 
  assetType: string; 
  solutions?: string; 
}

async function checkGlobalSellableStock(
  resourceType: string, 
  nowUTC: string, 
  requestingBuildingId: string // To exclude the current building's own potential stock
): Promise<boolean> {
  try {
    // Fetch all resource stacks of the given type in any building
    const resourceFormula = `AND({Type} = '${escapeAirtableValue(resourceType)}', {AssetType} = 'building', {Count} > 0)`;
    const allResourceStacks = await base(RESOURCES_TABLE).select({
      filterByFormula: resourceFormula,
      fields: ["Asset", "Owner", "Count"] // Asset is BuildingId, Owner is Citizen Username
    }).all();

    if (allResourceStacks.length === 0) {
      console.log(`[checkGlobalSellableStock] No resource stacks of type '${resourceType}' found anywhere.`);
      return false;
    }

    for (const stack of allResourceStacks) {
      const potentialSellerBuildingId = stack.fields.Asset as string;
      const potentialSellerCitizen = stack.fields.Owner as string;
      const stockCount = stack.fields.Count as number;

      // Skip if it's the requesting building's stock or if owner/building is missing
      if (!potentialSellerBuildingId || !potentialSellerCitizen || potentialSellerBuildingId === requestingBuildingId) {
        continue;
      }

      // Check for an active public_sell contract from this potentialSellerBuildingId by potentialSellerCitizen for this resourceType
      const contractConditions = [
        `{SellerBuilding} = '${escapeAirtableValue(potentialSellerBuildingId)}'`,
        `{ResourceType} = '${escapeAirtableValue(resourceType)}'`,
        `OR({Seller} = '${escapeAirtableValue(potentialSellerCitizen)}', {Seller} = 'public')`, // Seller is the resource owner OR "public"
        `{Type} = 'public_sell'`,
        `{Status} = 'active'`,
        `{TargetAmount} > 0`, // Ensure contract is for a positive amount
        `IS_BEFORE({CreatedAt}, '${nowUTC}')`,
        `IS_AFTER({EndAt}, '${nowUTC}')`
      ];
      const sellContractFormula = `AND(${contractConditions.join(', ')})`;
      
      const activeSellContracts = await base(CONTRACTS_TABLE).select({
        filterByFormula: sellContractFormula,
        maxRecords: 1,
        fields: ["ContractId"] // Only need to know if one exists
      }).firstPage();

      if (activeSellContracts.length > 0) {
        // Found at least one other building actively selling this resource type
        console.log(`[checkGlobalSellableStock] Found sellable stock of '${resourceType}' at building '${potentialSellerBuildingId}' by '${potentialSellerCitizen}'.`);
        return true;
      }
    }
    // If loop completes, no other building is actively selling this resource
    console.log(`[checkGlobalSellableStock] No *other* building found actively selling '${resourceType}'.`);
    return false;
  } catch (error) {
    console.error(`[checkGlobalSellableStock] Error checking global sellable stock for ${resourceType}:`, error);
    return false; // Assume not available on error to be safe
  }
}

// Helper to fetch building type definitions
// This is a simplified version. In a real app, this might be cached or come from a service.
async function getBuildingTypeDefinition(buildingTypeName: string): Promise<any | null> {
  try {
    // Assuming an API endpoint that returns all building type definitions
    // Adjust this URL to your actual endpoint for fetching building types
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
    const response = await fetch(`${baseUrl}/api/building-types`);
    if (!response.ok) {
      console.error(`Failed to fetch building types: ${response.status}`);
      return null;
    }
    const data = await response.json();
    if (data.success && Array.isArray(data.buildingTypes)) {
      return data.buildingTypes.find((bt: any) => bt.type === buildingTypeName) || null;
    }
    return null;
  } catch (error) {
    console.error(`Error fetching building type definition for ${buildingTypeName}:`, error);
    return null;
  }
}

// Helper to escape values for Airtable formulas
const escapeAirtableValue = (value: string): string => {
  if (typeof value !== 'string') {
    return String(value);
  }
  return value.replace(/'/g, "\\'");
};

// mapSeverityToText will be handled by the Python script
/*
const mapSeverityToText = (severity: number): string => {
  switch (severity) {
    case 1: return "Very Low";
    case 2: return "Low";
    case 3: return "Medium";
    case 4: return "High";
    case 5: return "Critical";
    default: return "Medium"; // Default if an unexpected number is passed
  }
};
*/

// Renamed parameter from resourceId to resourceType for clarity
async function getResourceStock(buildingId: string, resourceType: string, ownerUsername?: string) {
  let formula = `AND({Asset} = '${escapeAirtableValue(buildingId)}', {AssetType} = 'building', {Type} = '${escapeAirtableValue(resourceType)}')`;
  if (ownerUsername) {
    formula = `AND({Asset} = '${escapeAirtableValue(buildingId)}', {AssetType} = 'building', {Type} = '${escapeAirtableValue(resourceType)}', {Owner} = '${escapeAirtableValue(ownerUsername)}')`;
  }
  
  try {
    const records = await base(RESOURCES_TABLE).select({
      filterByFormula: formula,
    }).all(); // Use .all() to sum up if multiple stacks exist (though ideally one per owner/type/asset)
    
    let totalStock = 0;
    records.forEach(record => {
      totalStock += record.fields.Count as number || 0;
    });
    return totalStock;
  } catch (error) {
    console.error(`Error fetching resource stock for ${resourceType} in ${buildingId}:`, error);
    return 0; // Assume 0 stock on error
  }
}

async function getBuildingRecord(buildingId: string) {
  try {
    const records = await base(BUILDINGS_TABLE).select({
      filterByFormula: `{BuildingId} = '${escapeAirtableValue(buildingId)}'`,
      maxRecords: 1,
    }).firstPage();
    return records.length > 0 ? records[0] : null;
  } catch (error) {
    console.error(`Error fetching building ${buildingId}:`, error);
    return null;
  }
}

// Removed findOrCreateProblem function as problem creation is moved to Python script

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const buildingIdParam = searchParams.get('buildingId');
    const resourceTypeParam = searchParams.get('resourceType'); // Changed from resourceIdParam
    const checkAllInputsParam = searchParams.get('checkAllInputs') === 'true';

    const paramsToValidate = {
      buildingId: buildingIdParam,
      resourceType: resourceTypeParam, // Changed from resourceId
    };

    const validation = PinpointProblemSchema.safeParse(paramsToValidate);

    if (!validation.success) {
      return NextResponse.json({ success: false, error: "Invalid query parameters", details: validation.error.flatten() }, { status: 400 });
    }

    // Ensure validated data is used, especially since Zod might coerce types (though here they are strings)
    const { buildingId, resourceType } = validation.data; // Changed from resourceId

    const buildingRecord = await getBuildingRecord(buildingId);
    if (!buildingRecord) {
      return NextResponse.json({ success: false, error: `Building with ID ${buildingId} not found.` }, { status: 404 });
    }
    
    const buildingFields = buildingRecord.fields;
    const buildingOwner = buildingFields.Owner as string | undefined;
    const buildingRunBy = buildingFields.RunBy as string | undefined;
    const buildingOccupant = buildingFields.Occupant as string | undefined;
    const buildingName = buildingFields.Name as string || buildingId;
    let buildingPosition: { lat: number; lng: number } | undefined;
    if (buildingFields.Position && typeof buildingFields.Position === 'string') {
        try {
            buildingPosition = JSON.parse(buildingFields.Position as string);
        } catch (e) { /* ignore parse error */ }
    }


    const responsibleCitizen = buildingRunBy || buildingOwner; // Citizen to notify about the problem

    // Step 1: Check if the resource is actively being sold
    const nowUTC = new Date().toISOString();
    // Construct the formula as a single line to avoid potential issues with newlines/indentation
    const conditions = [
      `{SellerBuilding} = '${escapeAirtableValue(buildingId)}'`,
      `{ResourceType} = '${escapeAirtableValue(resourceType)}'`,
      `{Type} = 'public_sell'`,
      `{Status} = 'active'`,
      `{TargetAmount} > 0`,
      `IS_BEFORE({CreatedAt}, '${nowUTC}')`,
      `IS_AFTER({EndAt}, '${nowUTC}')`
    ];
    const contractFormula = `AND(${conditions.join(', ')})`;

    // Get building type definition to check if this resource should be sold
    const buildingTypeStr = buildingFields.Type as string;
    const buildingTypeDef = buildingTypeStr ? await getBuildingTypeDefinition(buildingTypeStr) : null;
    
    // Check if this resource is supposed to be sold by this building type
    let shouldSellResource = false;
    if (buildingTypeDef && buildingTypeDef.productionInformation && 
        Array.isArray(buildingTypeDef.productionInformation.sells)) {
      shouldSellResource = buildingTypeDef.productionInformation.sells.includes(resourceType);
    }
    
    // Only check for sale contract if this resource is supposed to be sold
    if (shouldSellResource) {
      const activeSellContracts = await base(CONTRACTS_TABLE).select({
        filterByFormula: contractFormula,
        maxRecords: 1,
      }).firstPage();

      if (activeSellContracts.length === 0) {
        const problem: ProblemDetails = {
          problemId: `problem_pinpoint_${buildingId}_${resourceType}_NO_SALE_CONTRACT`,
          type: 'resource_not_for_sale',
          title: `Resource Not For Sale: ${resourceType} at ${buildingName}`,
          description: `The resource '${resourceType}' is not currently listed for sale (no active 'public_sell' contract) at building '${buildingName}' (ID: ${buildingId}).`,
          severity: 3, // Medium severity
          citizenToNotify: responsibleCitizen,
          buildingPosition,
          buildingName,
          asset: buildingId,
          assetType: 'building',
          solutions: `To resolve this:\n- Create an active 'public_sell' contract for '${resourceType}' from building '${buildingName}'.\n- Ensure the contract has a positive TargetAmount and its EndAt date is in the future.`
        };
        // Problem creation moved to Python script
        return NextResponse.json({ 
          success: true, 
          problem_identified: true, 
          issue: 'NO_SALE_CONTRACT', 
          problemDetails: problem,
          problems: [problem] // Return as array for consistency
        });
      }
    } else {
      // If the resource is not meant to be sold, return success with no problem
      return NextResponse.json({ 
        success: true, 
        problem_identified: false, 
        problems: [], 
        message: `Resource '${resourceType}' is not intended to be sold at '${buildingName}' (ID: ${buildingId}). It is an input resource used for production.`
      });
    }

    // Step 2: If sold, check stock (owned by RunBy or Owner)
    const operatorForStockCheck = buildingRunBy || buildingOwner;
    if (!operatorForStockCheck) {
        // This case should be rare if a building has a contract but no operator/owner.
        const problem: ProblemDetails = {
            problemId: `problem_pinpoint_${buildingId}_${resourceType}_NO_OPERATOR_FOR_STOCK`, // Changed from resourceId
            type: 'resource_availability',
            title: `Operational Issue: ${resourceType} at ${buildingName}`, // Changed from resourceId
            description: `Building '${buildingName}' (ID: ${buildingId}) is selling '${resourceType}' but has no designated operator (RunBy or Owner) to manage stock.`, // Changed from resourceId
            severity: 4, // High severity
            citizenToNotify: responsibleCitizen, // Might be undefined, but good to try
            buildingPosition,
            buildingName,
            asset: buildingId,
            assetType: 'building',
            solutions: `Ensure building '${buildingName}' has a 'RunBy' or 'Owner' assigned. If one is assigned, verify their citizen record exists and is active.`
        };
        // Problem creation moved to Python script
        return NextResponse.json({ 
            success: true, 
            problem_identified: true, 
            issue: 'NO_OPERATOR_FOR_STOCK', 
            problemDetails: problem,
            problems: [problem] // Return as array for consistency
        });
    }

    const stock = await getResourceStock(buildingId, resourceType, operatorForStockCheck); // Changed from resourceId
    if (stock <= 0) {
      let problem: ProblemDetails | undefined;
      const buildingTypeStr = buildingFields.Type as string;
      const buildingTypeDef = buildingTypeStr ? await getBuildingTypeDefinition(buildingTypeStr) : null;

      // Helper function to check if building can produce the resource
      const canBuildingProduceResourceLocal = (btDef: any, resType: string): boolean => {
        if (!btDef || !btDef.productionInformation || !Array.isArray(btDef.productionInformation.Arti)) {
          return false;
        }
      
        const artiRecipes = btDef.productionInformation.Arti;
        for (const recipe of artiRecipes) {
          if (recipe && recipe.outputs) {
            const outputsField = recipe.outputs;
            // Case 1: outputs is a dictionary like {"resource_id1": amount1, ...}
            if (typeof outputsField === 'object' && !Array.isArray(outputsField) && outputsField !== null) {
              if (resType in outputsField) {
                return true;
              }
            } else if (Array.isArray(outputsField)) {
              // Case 2: outputs is a list
              for (const outputItem of outputsField) {
                // Subcase 2b: list of strings like ["resource_id1", ...]
                if (typeof outputItem === 'string' && outputItem === resType) {
                  return true;
                } 
                // Subcase 2a: list of dictionaries like [{"type": "resource_id1", ...}, ...]
                else if (typeof outputItem === 'object' && outputItem !== null && typeof outputItem.type === 'string' && outputItem.type === resType) {
                  return true;
                }
              }
            }
          }
        }
        return false;
      };

      const buildingCanProduceThisResource = canBuildingProduceResourceLocal(buildingTypeDef, resourceType);

      if (buildingCanProduceThisResource) {
        let allInputsAvailableForAtLeastOneRecipe = false;
        const missingInputsDetails: string[] = [];
        let checkedAtLeastOneRecipe = false;

        if (operatorForStockCheck && buildingTypeDef && buildingTypeDef.productionInformation && Array.isArray(buildingTypeDef.productionInformation.Arti)) {
          const artiRecipes = buildingTypeDef.productionInformation.Arti;
          for (const recipe of artiRecipes) {
            if (!recipe || !recipe.outputs) continue;
            checkedAtLeastOneRecipe = true;

            let producesTargetResource = false;
            const outputsField = recipe.outputs;
            if (typeof outputsField === 'object' && !Array.isArray(outputsField) && outputsField !== null) {
              if (resourceType in outputsField) producesTargetResource = true;
            } else if (Array.isArray(outputsField)) {
              for (const outputItem of outputsField) {
                if (typeof outputItem === 'string' && outputItem === resourceType) { producesTargetResource = true; break; }
                else if (typeof outputItem === 'object' && outputItem !== null && typeof outputItem.type === 'string' && outputItem.type === resourceType) { producesTargetResource = true; break; }
              }
            }

            if (producesTargetResource) {
              let currentRecipeInputsAvailable = true;
              if (recipe.inputs && typeof recipe.inputs === 'object' && Object.keys(recipe.inputs).length > 0) {
                for (const [inputResType, neededAmountStr] of Object.entries(recipe.inputs)) {
                  const neededAmount = parseFloat(String(neededAmountStr));
                  const inputStock = await getResourceStock(buildingId, inputResType, operatorForStockCheck);
                  if (inputStock < neededAmount) {
                    currentRecipeInputsAvailable = false;
                    const detail = `${inputResType} (need: ${neededAmount}, stock: ${inputStock})`; // Translated
                    if (!missingInputsDetails.includes(detail)) missingInputsDetails.push(detail);
                    // Do not break here, collect all missing for this recipe
                  }
                }
              }
              // If the recipe has no inputs, currentRecipeInputsAvailable remains true

              if (currentRecipeInputsAvailable) {
                allInputsAvailableForAtLeastOneRecipe = true;
                missingInputsDetails.length = 0; // Clear details if a viable recipe is found
                break; // Viable recipe found, no need to check others
              }
            }
          }
        } else if (!operatorForStockCheck) {
            missingInputsDetails.push("Building operator not found to check input stock."); // Translated
        }
        
        if (!checkedAtLeastOneRecipe && buildingTypeDef && buildingTypeDef.productionInformation && Array.isArray(buildingTypeDef.productionInformation.Arti) && buildingTypeDef.productionInformation.Arti.length === 0) {
            missingInputsDetails.push("No production recipes defined for this building."); // Translated
        }


        if (allInputsAvailableForAtLeastOneRecipe) {
          problem = {
            problemId: `problem_pinpoint_${buildingId}_${resourceType}_WAITING_FOR_PRODUCTION`,
            type: 'waiting_for_production',
            title: `Awaiting Production: ${resourceType} at ${buildingName}`, // Translated
            description: `Building '${buildingName}' (ID: ${buildingId}) can produce '${resourceType}', has necessary inputs, but is out of stock. Production may need to be initiated or an occupant assigned.`, // Translated
            severity: 3, // Medium
            citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
            solutions: `Ensure building '${buildingName}' has an active 'Occupant' (worker) assigned and production activities are scheduled and processed. Check production recipes and priorities.` // Translated
          };
        } else {
          // Further breakdown of NO_INPUT_RESOURCES
          const inputsWithoutContracts: string[] = [];
          const inputsWithContractsAwaitingDelivery: string[] = [];

          for (const detail of missingInputsDetails) {
            const resourceMatch = detail.match(/^([a-zA-Z0-9_]+)\s*\(/);
            if (!resourceMatch || !resourceMatch[1]) continue;
            const missingInputResourceType = resourceMatch[1];

            const markupBuyContractFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(missingInputResourceType)}', {Type} = 'markup_buy', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
            const activeMarkupBuyContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: markupBuyContractFormula, maxRecords: 1 }).firstPage();

            const importContractFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(missingInputResourceType)}', {Type} = 'import', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
            const activeImportContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: importContractFormula, maxRecords: 1 }).firstPage();

            if (activeMarkupBuyContracts.length === 0 && activeImportContracts.length === 0) {
              if (!inputsWithoutContracts.includes(missingInputResourceType)) {
                inputsWithoutContracts.push(missingInputResourceType);
              }
            } else {
              if (!inputsWithContractsAwaitingDelivery.includes(missingInputResourceType)) {
                inputsWithContractsAwaitingDelivery.push(missingInputResourceType);
              }
            }
          }

          if (inputsWithoutContracts.length > 0) {
            const inputsStr = inputsWithoutContracts.join(', ');
            problem = {
              problemId: `problem_pinpoint_${buildingId}_${resourceType}_NO_CONTRACT_FOR_INPUTS_${inputsWithoutContracts.join('_').substring(0,50)}`,
              type: 'no_markup_buy_contract_for_input',
              title: `Missing Purchase Contract for Inputs: ${inputsStr} at ${buildingName}`, // Translated
              description: `Building '${buildingName}' (ID: ${buildingId}) is missing inputs (${inputsStr}) to produce '${resourceType}' and has no active purchase contract (markup_buy) for these inputs.`, // Translated
              severity: 4, // High
              citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
              solutions: `Create 'markup_buy' contracts for the missing inputs (${inputsStr}) for building '${buildingName}'.` // Translated
            };
          } else if (inputsWithContractsAwaitingDelivery.length > 0) {
            // All missing inputs have at least one contract. Now check supplier stock.
            const suppliersWithShortages: string[] = [];
            let allSuppliersHaveStock = true;

            for (const missingInputResType of inputsWithContractsAwaitingDelivery) {
              // Check markup_buy contracts first
              const markupBuyFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(missingInputResType)}', {Type} = 'markup_buy', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
              const markupBuyContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: markupBuyFormula, maxRecords: 1 }).firstPage();
              
              let supplierCheckedForThisInput = false;

              if (markupBuyContracts.length > 0) {
                supplierCheckedForThisInput = true;
                const contract = markupBuyContracts[0];
                const sellerBuildingId = contract.fields.SellerBuilding as string;
                const sellerUsername = contract.fields.Seller as string;
                if (sellerBuildingId && sellerUsername) { // Contract specifies a supplier
                  const sellerBuildingRecord = await getBuildingRecord(sellerBuildingId);
                  if (!sellerBuildingRecord) {
                    allSuppliersHaveStock = false;
                    suppliersWithShortages.push(`${missingInputResType} (markup_buy contract lists non-existent SellerBuilding: ${sellerBuildingId})`);
                  } else {
                    // SellerBuilding exists, now check Seller
                    const sellerCitizenRecordCheck = await base(CITIZENS_TABLE_NAME).select({filterByFormula: `{Username} = '${escapeAirtableValue(sellerUsername)}'`, maxRecords: 1}).firstPage();
                    if (!sellerCitizenRecordCheck || sellerCitizenRecordCheck.length === 0) {
                        allSuppliersHaveStock = false;
                        suppliersWithShortages.push(`${missingInputResType} (markup_buy contract lists non-existent Seller: ${sellerUsername})`);
                    } else {
                      // Both SellerBuilding and Seller are valid, now check stock
                      const supplierStock = await getResourceStock(sellerBuildingId, missingInputResType, sellerUsername);
                      if (supplierStock <= 0) {
                        allSuppliersHaveStock = false;
                        // sellerBuildingRecord is already fetched and valid here
                        const sellerBuildingName = sellerBuildingRecord?.fields?.Name as string || sellerBuildingId; // Use the already fetched record
                        suppliersWithShortages.push(`${missingInputResType} from ${sellerBuildingName} (Operator: ${sellerUsername}) is out of stock`);
                      }
                      // If supplierStock > 0, this specific procurement path is viable.
                    }
                  }
                } else {
                  // This branch is hit if sellerBuildingId or sellerUsername is null/empty on the markup_buy contract.
                  // This signifies a public buy request by the BuyerBuilding. It's not an invalid contract.
                  // No specific supplier is designated on this contract, so we don't check stock against a specific entity here.
                  // We also don't add to suppliersWithShortages or set allSuppliersHaveStock to false based on this contract alone.
                  // The general availability of the resource will be checked later if no specific, stocked supplier is found.
                  console.log(`  Markup_buy contract for ${missingInputResType} for ${buildingId} is a public request (no specific Seller/SellerBuilding). General market availability will be checked if needed.`);
                }
              }

              // Determine if this specific input (missingInputResType) has been successfully sourced via a specific markup_buy contract with stock
              let thisInputSourcedViaSpecificMarkupBuy = false;
              if (markupBuyContracts.length > 0) {
                for (const contract of markupBuyContracts) { // Iterate if multiple markup_buy for same input
                    const mbSellerBuildingId = contract.fields.SellerBuilding as string;
                    const mbSellerUsername = contract.fields.Seller as string;
                    if (mbSellerBuildingId && mbSellerUsername) { // Check only specific supplier contracts
                        const mbSellerBuildingRecord = await getBuildingRecord(mbSellerBuildingId);
                        if (mbSellerBuildingRecord) {
                            const mbSellerCitizenRecord = await base(CITIZENS_TABLE_NAME /* Ensure CITIZENS_TABLE_NAME is defined or imported */).select({filterByFormula: `{Username} = '${escapeAirtableValue(mbSellerUsername)}'`, maxRecords: 1}).firstPage();
                            if (mbSellerCitizenRecord && mbSellerCitizenRecord.length > 0) {
                                const mbSupplierStock = await getResourceStock(mbSellerBuildingId, missingInputResType, mbSellerUsername);
                                if (mbSupplierStock > 0) {
                                    thisInputSourcedViaSpecificMarkupBuy = true;
                                    break; // Found a stocked specific supplier for this input
                                }
                            }
                        }
                    }
                }
              }

              if (!thisInputSourcedViaSpecificMarkupBuy) {
                const importFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(missingInputResType)}', {Type} = 'import', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
                const importContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: importFormula, maxRecords: 1 }).firstPage();

                if (importContracts.length > 0) {
                  supplierCheckedForThisInput = true;
                  const contract = importContracts[0];
                  const galleyBuildingId = contract.fields.SellerBuilding as string; // This is the Galley's BuildingId
                  const merchantUsername = contract.fields.Seller as string; // Merchant owning the goods on galley
                  if (galleyBuildingId && merchantUsername) {
                    // Check if galley has arrived (IsConstructed or ConstructionDate in past)
                    const galleyRecord = await getBuildingRecord(galleyBuildingId);
                    let galleyArrived = false;
                    if (galleyRecord) {
                        const isConstructed = galleyRecord.fields.IsConstructed === true || galleyRecord.fields.IsConstructed === 1;
                        const constructionDateStr = galleyRecord.fields.ConstructionDate as string;
                        let constructionDateInPast = false;
                        if (constructionDateStr) {
                            try { constructionDateInPast = new Date(constructionDateStr) <= new Date(nowUTC); } catch (e) {}
                        }
                        galleyArrived = isConstructed || constructionDateInPast;
                    }

                    if (galleyArrived) {
                        const supplierStock = await getResourceStock(galleyBuildingId, missingInputResType, merchantUsername);
                        if (supplierStock <= 0) {
                            allSuppliersHaveStock = false;
                            const galleyName = galleyRecord?.fields?.Name as string || galleyBuildingId;
                            suppliersWithShortages.push(`${missingInputResType} from Galley ${galleyName} (Merchant: ${merchantUsername})`);
                        }
                    } else {
                        // Galley not arrived yet, so can't determine supplier shortage. Assume waiting for delivery.
                        // This case is already covered by 'waiting_on_input_delivery' if no other supplier has a shortage.
                    }
                  } else {
                    allSuppliersHaveStock = false; // Import contract exists but invalid seller/galley info
                    suppliersWithShortages.push(`${missingInputResType} (import contract has invalid seller/galley)`);
                  }
                }
              }
              if (!allSuppliersHaveStock && !suppliersWithShortages.some(s => s.startsWith(missingInputResType))) {
                // If a specific contract type check failed to add to suppliersWithShortages (e.g. invalid contract details)
                // but we know there's an issue for this input, add a generic message.
                // This ensures that if any path for an input leads to a problem, it's flagged.
                if (!supplierCheckedForThisInput) { // No contract found for this input, should have been caught by inputsWithoutContracts
                     // This case should ideally not be reached if inputsWithoutContracts is handled correctly.
                } else if (!allSuppliersHaveStock) { // A contract was checked, but some issue prevented specific shortage logging
                    suppliersWithShortages.push(`${missingInputResType} (supplier stock check issue)`);
                }
              }
            } // End loop over missingInputResType

            if (!allSuppliersHaveStock) {
              const shortagesStr = suppliersWithShortages.join('; ');
              problem = {
                problemId: `problem_pinpoint_${buildingId}_${resourceType}_SUPPLIER_SHORTAGE_FOR_INPUTS_${suppliersWithShortages.join('_').replace(/\s/g, '').substring(0,40)}`,
                type: 'supplier_shortage',
                title: `Supplier Shortage for Inputs: ${buildingName}`,
                description: `Building '${buildingName}' (ID: ${buildingId}) is waiting for inputs to produce '${resourceType}', but supplier(s) are out of stock for: ${shortagesStr}.`,
                severity: 4, // High
                citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
                solutions: `Address supplier shortages for: ${shortagesStr}. This may involve the supplier creating new import/markup_buy contracts for *their* inputs, or finding alternative suppliers for '${buildingName}'.`
              };
            } else {
              // All suppliers have stock, so it's genuinely waiting for delivery.
              const inputsStr = inputsWithContractsAwaitingDelivery.join(', ');
              problem = {
                problemId: `problem_pinpoint_${buildingId}_${resourceType}_WAITING_ON_INPUT_DELIVERY_${inputsWithContractsAwaitingDelivery.join('_').substring(0,50)}`,
                type: 'waiting_on_input_delivery',
                title: `Awaiting Input Delivery: ${inputsStr} at ${buildingName}`,
                description: `Building '${buildingName}' (ID: ${buildingId}) is missing inputs (${inputsStr}) to produce '${resourceType}', but purchase contracts exist and suppliers have stock. Awaiting delivery.`,
                severity: 3, // Medium
                citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
                solutions: `Monitor purchase contracts for inputs (${inputsStr}). Ensure deliveries are in progress or resolve any delivery issues. Check citizen activities for 'fetch_resource'.`
              };
            }
          } else {
            // Fallback if missingInputsDetails was empty or parsing failed, though this shouldn't happen if allInputsAvailableForAtLeastOneRecipe is false.
            const originalMissingInputsString = missingInputsDetails.join(', '); // Ensure this is defined
            problem = {
              problemId: `problem_pinpoint_${buildingId}_${resourceType}_NO_INPUT_RESOURCES_FALLBACK`,
              type: 'no_input_resources', // Fallback to original generic type
              title: `Missing Inputs (Fallback): ${resourceType} at ${buildingName}`, // Translated
              description: `Building '${buildingName}' (ID: ${buildingId}) is missing inputs to produce '${resourceType}'. Details: ${originalMissingInputsString || 'unavailable'}. Could not determine status of purchase contracts.`, // Translated
              severity: 4, // High
              citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
              solutions: `Check required inputs for '${resourceType}' and purchase contracts for building '${buildingName}'. Missing details: ${originalMissingInputsString || 'unavailable'}.` // Translated
            };
          }
        }
      } else {
        // Original logic if building cannot produce this resource
        const canImport = buildingTypeDef?.canImport === true;
        if (canImport) {
          // Check for active import contract
          const importContractFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(resourceType)}', {Type} = 'import', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
        const activeImportContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: importContractFormula, maxRecords: 1 }).firstPage();

        if (activeImportContracts.length === 0) {
          problem = {
            problemId: `problem_pinpoint_${buildingId}_${resourceType}_NO_IMPORT_CONTRACT`,
            type: 'no_import_contract',
            title: `No Import Contract: ${resourceType} at ${buildingName}`,
            description: `Building '${buildingName}' (ID: ${buildingId}) can import '${resourceType}' but has no active import contract for it, and is out of stock.`,
            severity: 4, // High
            citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
            solutions: `Create an 'import' contract for '${resourceType}' for building '${buildingName}' to ensure supply.`
          };
        } else {
          // Import contract exists, check galley status
          const importContract = activeImportContracts[0];
          const galleyBuildingId = importContract.fields.SellerBuilding as string;
          let galleyArrived = false;
          let galleyName = galleyBuildingId || "Unknown Galley";

          if (galleyBuildingId) {
            const galleyRecord = await getBuildingRecord(galleyBuildingId);
            if (galleyRecord) {
              galleyName = (galleyRecord.fields.Name as string) || galleyBuildingId;
              const isConstructed = galleyRecord.fields.IsConstructed === true || galleyRecord.fields.IsConstructed === 1;
              const constructionDateStr = galleyRecord.fields.ConstructionDate as string;
              let constructionDateInPast = false;
              if (constructionDateStr) {
                try {
                  constructionDateInPast = new Date(constructionDateStr) <= new Date(nowUTC);
                } catch (e) { /* ignore date parse error */ }
              }
              galleyArrived = isConstructed || constructionDateInPast;
            }
          }

          if (galleyArrived) {
            problem = {
              problemId: `problem_pinpoint_${buildingId}_${resourceType}_WAITING_FOR_GALLEY_UNLOADING`,
              type: 'waiting_for_galley_unloading',
              title: `Waiting for Unloading: ${resourceType} at ${buildingName}`,
              description: `Building '${buildingName}' (ID: ${buildingId}) is out of stock for '${resourceType}'. The delivering galley '${galleyName}' has arrived but goods are not yet unloaded.`,
              severity: 3, // Medium
              citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
              solutions: `Ensure 'fetch_from_galley' activities are created and processed for building '${buildingName}' to retrieve '${resourceType}' from galley '${galleyName}'. Check galley's inventory and contract status.`
            };
          } else {
            problem = {
              problemId: `problem_pinpoint_${buildingId}_${resourceType}_WAITING_FOR_GALLEY_ARRIVAL`,
              type: 'waiting_for_galley_arrival',
              title: `Waiting for Galley: ${resourceType} at ${buildingName}`,
              description: `Building '${buildingName}' (ID: ${buildingId}) is out of stock for '${resourceType}' and is awaiting arrival of the delivering galley '${galleyName}'.`,
              severity: 3, // Medium
              citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
              solutions: `Monitor the import contract for '${resourceType}'. The galley '${galleyName}' is still en route or its arrival has not yet been processed. Check galley's 'ConstructionDate'.`
            };
          }
        }
      } else { // Building cannot import (and also cannot produce, due to outer 'if' block)
        // Check for markup_buy contract
        const markupBuyContractFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(resourceType)}', {Type} = 'markup_buy', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
        const activeMarkupBuyContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: markupBuyContractFormula, maxRecords: 1 }).firstPage();

        if (activeMarkupBuyContracts.length === 0) {
          problem = {
            problemId: `problem_pinpoint_${buildingId}_${resourceType}_NO_MARKUP_BUY_CONTRACT`,
            type: 'no_markup_buy_contract',
            title: `No Markup Buy Contract: ${resourceType} at ${buildingName}`,
            description: `Building '${buildingName}' (ID: ${buildingId}) cannot import or produce '${resourceType}', is out of stock, and has no active 'markup_buy' contract to procure it locally.`,
            severity: 4, // High
            citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
            solutions: `Create a 'markup_buy' contract for '${resourceType}' for building '${buildingName}' to purchase from other citizens or businesses.`
          };
        } else {
          // Has markup_buy contract, now check global availability
          const globalStockAvailable = await checkGlobalSellableStock(resourceType, nowUTC, buildingId);
          if (!globalStockAvailable) {
            problem = {
              problemId: `problem_pinpoint_${buildingId}_${resourceType}_RESOURCE_SHORTAGE`,
              type: 'resource_shortage',
              title: `Resource Shortage: ${resourceType} for ${buildingName}`,
              description: `Building '${buildingName}' (ID: ${buildingId}) is out of stock for '${resourceType}', has a 'markup_buy' contract, but the resource appears to be unavailable or not actively sold elsewhere in Venice.`,
              severity: 5, // Critical, as it's a market-wide issue
              citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
              solutions: `The resource '${resourceType}' is currently scarce. Consider:\n- Increasing the buy price on your 'markup_buy' contract significantly to incentivize sellers.\n- If possible, find alternative resources or adjust production that depends on '${resourceType}'.\n- Wait for market conditions to change (e.g., new imports by merchants).`
            };
          } else {
            problem = {
              problemId: `problem_pinpoint_${buildingId}_${resourceType}_WAITING_FOR_DELIVERY`, 
              type: 'waiting_for_resource_delivery', 
              title: `Waiting for Delivery: ${resourceType} at ${buildingName}`,
              description: `Building '${buildingName}' (ID: ${buildingId}) is out of stock for '${resourceType}', has an active 'markup_buy' contract, and the resource is available elsewhere. Awaiting delivery.`,
              severity: 3, // Medium
              citizenToNotify: responsibleCitizen, buildingPosition, buildingName, asset: buildingId, assetType: 'building',
              solutions: `Monitor the 'markup_buy' contract for '${resourceType}'. Ensure citizens or logistics services are fulfilling delivery. Check 'fetch_resource' activities targeting your building.`
            };
          }
        }
      }
    } // End of the 'else' for buildingCanProduceThisResource

      // Ensure problem is defined - this is a safety check
      if (!problem) {
        problem = {
          problemId: `problem_pinpoint_${buildingId}_${resourceType}_UNKNOWN_STOCK_ISSUE`,
          type: 'unknown_stock_issue',
          title: `Unknown Stock Issue: ${resourceType} at ${buildingName}`,
          description: `Building '${buildingName}' (ID: ${buildingId}) is out of stock for '${resourceType}' but the specific issue could not be determined.`,
          severity: 3, // Medium
          citizenToNotify: responsibleCitizen,
          buildingPosition,
          buildingName,
          asset: buildingId,
          assetType: 'building',
          solutions: `Investigate why '${buildingName}' is out of stock for '${resourceType}'. Check production recipes, input availability, and contract status.`
        };
      }

      // If we're checking all inputs, we need to collect all problems
      if (checkAllInputsParam && buildingCanProduceThisResource) {
        // We'll collect all problems for all inputs
        const allProblems: ProblemDetails[] = [];
        
        // First add the main problem for the requested resource
        allProblems.push(problem);
        
        // Now check each input resource that's missing
        if (buildingTypeDef && buildingTypeDef.productionInformation && Array.isArray(buildingTypeDef.productionInformation.Arti)) {
          const artiRecipes = buildingTypeDef.productionInformation.Arti;
          
          // Find recipes that produce our target resource
          for (const recipe of artiRecipes) {
            if (!recipe || !recipe.outputs) continue;
            
            // Check if this recipe produces our target resource
            let producesTargetResource = false;
            const outputsField = recipe.outputs;
            if (typeof outputsField === 'object' && !Array.isArray(outputsField) && outputsField !== null) {
              if (resourceType in outputsField) producesTargetResource = true;
            } else if (Array.isArray(outputsField)) {
              for (const outputItem of outputsField) {
                if (typeof outputItem === 'string' && outputItem === resourceType) { producesTargetResource = true; break; }
                else if (typeof outputItem === 'object' && outputItem !== null && typeof outputItem.type === 'string' && outputItem.type === resourceType) { producesTargetResource = true; break; }
              }
            }
            
            // If this recipe produces our target resource, check each input
            if (producesTargetResource && recipe.inputs && typeof recipe.inputs === 'object') {
              for (const [inputResType, neededAmountStr] of Object.entries(recipe.inputs)) {
                // For each input, check if we have a problem
                const neededAmount = parseFloat(String(neededAmountStr));
                const inputStock = await getResourceStock(buildingId, inputResType, operatorForStockCheck);
                
                if (inputStock < neededAmount) {
                  // Check for markup_buy contract for this input
                  const markupBuyContractFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(inputResType)}', {Type} = 'markup_buy', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
                  const activeMarkupBuyContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: markupBuyContractFormula, maxRecords: 1 }).firstPage();
                  
                  // Check for import contract for this input
                  const importContractFormula = `AND({BuyerBuilding} = '${escapeAirtableValue(buildingId)}', {ResourceType} = '${escapeAirtableValue(inputResType)}', {Type} = 'import', {Status} = 'active', IS_BEFORE({CreatedAt}, '${nowUTC}'), IS_AFTER({EndAt}, '${nowUTC}'))`;
                  const activeImportContracts = await base(CONTRACTS_TABLE).select({ filterByFormula: importContractFormula, maxRecords: 1 }).firstPage();
                  
                  // Create appropriate problem based on contract status
                  if (activeMarkupBuyContracts.length === 0 && activeImportContracts.length === 0) {
                    // No contract for this input
                    const inputProblem: ProblemDetails = {
                      problemId: `problem_pinpoint_${buildingId}_${inputResType}_NO_CONTRACT_FOR_INPUT`,
                      type: 'no_markup_buy_contract_for_input',
                      title: `Missing Purchase Contract for Input: ${inputResType} at ${buildingName}`,
                      description: `Building '${buildingName}' (ID: ${buildingId}) is missing input ${inputResType} to produce '${resourceType}' and has no active purchase contract (markup_buy) for this input.`,
                      severity: 4, // High
                      citizenToNotify: responsibleCitizen, 
                      buildingPosition, 
                      buildingName, 
                      asset: buildingId, 
                      assetType: 'building',
                      solutions: `Create a 'markup_buy' contract for the missing input ${inputResType} for building '${buildingName}'.`
                    };
                    allProblems.push(inputProblem);
                  } else if (activeMarkupBuyContracts.length > 0) {
                    // Check supplier stock for markup_buy
                    const contract = activeMarkupBuyContracts[0];
                    const sellerBuildingId = contract.fields.SellerBuilding as string;
                    const sellerUsername = contract.fields.Seller as string;
                    
                    if (sellerBuildingId && sellerUsername) {
                      const supplierStock = await getResourceStock(sellerBuildingId, inputResType, sellerUsername);
                      if (supplierStock <= 0) {
                        // Supplier shortage
                        const sellerBuildingRecord = await getBuildingRecord(sellerBuildingId);
                        const sellerBuildingName = sellerBuildingRecord?.fields?.Name as string || sellerBuildingId;
                        
                        const inputProblem: ProblemDetails = {
                          problemId: `problem_pinpoint_${buildingId}_${inputResType}_SUPPLIER_SHORTAGE`,
                          type: 'supplier_shortage',
                          title: `Supplier Shortage for Input: ${inputResType} at ${buildingName}`,
                          description: `Building '${buildingName}' (ID: ${buildingId}) is waiting for input ${inputResType} to produce '${resourceType}', but supplier '${sellerBuildingName}' (${sellerUsername}) is out of stock.`,
                          severity: 4, // High
                          citizenToNotify: responsibleCitizen, 
                          buildingPosition, 
                          buildingName, 
                          asset: buildingId, 
                          assetType: 'building',
                          solutions: `Address supplier shortage for ${inputResType}. This may involve the supplier creating new import/markup_buy contracts for their inputs, or finding alternative suppliers.`
                        };
                        allProblems.push(inputProblem);
                      } else {
                        // Waiting for delivery
                        const inputProblem: ProblemDetails = {
                          problemId: `problem_pinpoint_${buildingId}_${inputResType}_WAITING_ON_DELIVERY`,
                          type: 'waiting_on_input_delivery',
                          title: `Awaiting Input Delivery: ${inputResType} at ${buildingName}`,
                          description: `Building '${buildingName}' (ID: ${buildingId}) is missing input ${inputResType} to produce '${resourceType}', but a purchase contract exists and the supplier has stock. Awaiting delivery.`,
                          severity: 3, // Medium
                          citizenToNotify: responsibleCitizen, 
                          buildingPosition, 
                          buildingName, 
                          asset: buildingId, 
                          assetType: 'building',
                          solutions: `Monitor purchase contract for input ${inputResType}. Ensure deliveries are in progress or resolve any delivery issues.`
                        };
                        allProblems.push(inputProblem);
                      }
                    }
                  } else if (activeImportContracts.length > 0) {
                    // Check galley status for import
                    const contract = activeImportContracts[0];
                    const galleyBuildingId = contract.fields.SellerBuilding as string;
                    
                    if (galleyBuildingId) {
                      const galleyRecord = await getBuildingRecord(galleyBuildingId);
                      let galleyArrived = false;
                      let galleyName = galleyBuildingId || "Unknown Galley";
                      
                      if (galleyRecord) {
                        galleyName = (galleyRecord.fields.Name as string) || galleyBuildingId;
                        const isConstructed = galleyRecord.fields.IsConstructed === true || galleyRecord.fields.IsConstructed === 1;
                        const constructionDateStr = galleyRecord.fields.ConstructionDate as string;
                        let constructionDateInPast = false;
                        if (constructionDateStr) {
                          try {
                            constructionDateInPast = new Date(constructionDateStr) <= new Date(nowUTC);
                          } catch (e) { /* ignore date parse error */ }
                        }
                        galleyArrived = isConstructed || constructionDateInPast;
                      }
                      
                      if (galleyArrived) {
                        // Waiting for unloading
                        const inputProblem: ProblemDetails = {
                          problemId: `problem_pinpoint_${buildingId}_${inputResType}_WAITING_FOR_GALLEY_UNLOADING`,
                          type: 'waiting_for_galley_unloading',
                          title: `Waiting for Unloading: ${inputResType} at ${buildingName}`,
                          description: `Building '${buildingName}' (ID: ${buildingId}) is out of stock for input '${inputResType}' needed to produce '${resourceType}'. The delivering galley '${galleyName}' has arrived but goods are not yet unloaded.`,
                          severity: 3, // Medium
                          citizenToNotify: responsibleCitizen, 
                          buildingPosition, 
                          buildingName, 
                          asset: buildingId, 
                          assetType: 'building',
                          solutions: `Ensure 'fetch_from_galley' activities are created and processed for building '${buildingName}' to retrieve '${inputResType}' from galley '${galleyName}'.`
                        };
                        allProblems.push(inputProblem);
                      } else {
                        // Waiting for galley arrival
                        const inputProblem: ProblemDetails = {
                          problemId: `problem_pinpoint_${buildingId}_${inputResType}_WAITING_FOR_GALLEY_ARRIVAL`,
                          type: 'waiting_for_galley_arrival',
                          title: `Waiting for Galley: ${inputResType} at ${buildingName}`,
                          description: `Building '${buildingName}' (ID: ${buildingId}) is out of stock for input '${inputResType}' needed to produce '${resourceType}' and is awaiting arrival of the delivering galley '${galleyName}'.`,
                          severity: 3, // Medium
                          citizenToNotify: responsibleCitizen, 
                          buildingPosition, 
                          buildingName, 
                          asset: buildingId, 
                          assetType: 'building',
                          solutions: `Monitor the import contract for '${inputResType}'. The galley '${galleyName}' is still en route or its arrival has not yet been processed.`
                        };
                        allProblems.push(inputProblem);
                      }
                    }
                  }
                }
              }
            }
          }
        }
        
        return NextResponse.json({ 
          success: true, 
          problem_identified: true, 
          issue: problem.type.toUpperCase(), 
          problemDetails: problem,
          problems: allProblems
        });
      } else {
        // Original behavior - return single problem
        return NextResponse.json({ 
          success: true, 
          problem_identified: true, 
          issue: problem.type.toUpperCase(), 
          problemDetails: problem,
          problems: [problem] // Return as array for consistency
        });
      }
    }

    // Step 3: If in stock, check for an Occupant
    if (!buildingOccupant) {
      const problem: ProblemDetails = {
        problemId: `problem_pinpoint_${buildingId}_${resourceType}_NO_OCCUPANT`,
        type: 'operational_issue',
        title: `Building Unstaffed: ${buildingName}`,
        description: `Building '${buildingName}' (ID: ${buildingId}) has '${resourceType}' in stock and for sale, but there is no current Occupant to conduct transactions.`,
        severity: 3, // Medium severity
        citizenToNotify: responsibleCitizen,
        buildingPosition,
        buildingName,
        asset: buildingId,
        assetType: 'building',
        solutions: `Assign an 'Occupant' to building '${buildingName}' to handle sales and operations. This could be the 'RunBy' citizen or another designated worker.`
      };
      // Problem creation moved to Python script
      return NextResponse.json({ 
        success: true, 
        problem_identified: true, 
        issue: 'NO_OCCUPANT', 
        problemDetails: problem,
        problems: [problem] // Return as array for consistency
      });
    }

    // If all checks pass up to this point
    return NextResponse.json({ 
      success: true, 
      problem_identified: false, 
      problems: [], // Return empty array when no problems
      message: `Resource '${resourceType}' appears to be available for sale at '${buildingName}' (ID: ${buildingId}). It has an active sale contract, is in stock, and the building has an occupant.`
    });

  } catch (error: any) {
    console.error("Error in /api/pinpoint-problem:", error);
    return NextResponse.json({ success: false, error: "Internal server error", details: error.message }, { status: 500 });
  }
}

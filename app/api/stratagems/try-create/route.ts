import { NextResponse } from 'next/server';
import { z } from 'zod';

const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://localhost:10000';

// Schéma Zod pour la validation de la requête de création de stratagème
const TryCreateStratagemRequestSchema = z.object({
  citizenUsername: z.string().min(1, "citizenUsername is required"),
  stratagemType: z.string().min(1, "stratagemType is required"),
  stratagemDetails: z.record(z.any()).optional(), // Détails spécifiques au stratagème
});

export async function POST(request: Request) {
  let rawBody: any;
  try {
    rawBody = await request.json();
    console.log(`[API /stratagems/try-create] Raw request body:`, JSON.stringify(rawBody, null, 2));
    const validationResult = TryCreateStratagemRequestSchema.safeParse(rawBody);

    if (!validationResult.success) {
      return NextResponse.json({ success: false, error: "Invalid request payload", details: validationResult.error.format() }, { status: 400 });
    }
    const { citizenUsername, stratagemType, stratagemDetails } = validationResult.data;

    console.log(`[API /stratagems/try-create] Received request for citizen: ${citizenUsername}, stratagem type: ${stratagemType}, details:`, stratagemDetails || {});

    const pythonPayload: any = {
      citizenUsername: citizenUsername,
      stratagemType: stratagemType,
      ...(stratagemDetails && { stratagemParameters: stratagemDetails }),
    };

    // Log spécifique pour le stratagème "undercut"
    if (stratagemType === 'undercut') {
      console.log(`[API /stratagems/try-create] Processing 'undercut' stratagem with parameters:`,
        `Variant: ${stratagemDetails?.variant}`,
        `TargetCitizen: ${stratagemDetails?.targetCitizen}`,
        `TargetBuilding: ${stratagemDetails?.targetBuilding}`,
        `TargetResourceType: ${stratagemDetails?.targetResourceType}`
      );
    } else if (stratagemType === 'cultural_patronage') {
      console.log(`[API /stratagems/try-create] Processing 'cultural_patronage' stratagem with parameters:`,
        `TargetArtist: ${stratagemDetails?.targetArtist}`,
        `TargetPerformanceId: ${stratagemDetails?.targetPerformanceId}`,
        `TargetInstitutionId: ${stratagemDetails?.targetInstitutionId}`,
        `PatronageLevel: ${stratagemDetails?.patronageLevel}`
      );
    } else if (stratagemType === 'information_network') {
      console.log(`[API /stratagems/try-create] Processing 'information_network' stratagem with parameters:`,
        `TargetCitizens: ${JSON.stringify(stratagemDetails?.targetCitizens)}`,
        `TargetSectors: ${JSON.stringify(stratagemDetails?.targetSectors)}`,
        `DurationHours: ${stratagemDetails?.durationHours}`
      );
    } else if (stratagemType === 'maritime_blockade') {
      console.log(`[API /stratagems/try-create] Processing 'maritime_blockade' stratagem with parameters:`,
        `TargetCompetitorBuilding: ${stratagemDetails?.targetCompetitorBuilding || stratagemDetails?.targetBuilding}`,
        `TargetCompetitorCitizen: ${stratagemDetails?.targetCompetitorCitizen || stratagemDetails?.targetCitizen}`,
        `DurationHours: ${stratagemDetails?.durationHours}`
      );
    } else if (stratagemType === 'theater_conspiracy') {
      console.log(`[API /stratagems/try-create] Processing 'theater_conspiracy' stratagem with parameters:`,
        `TargetTheaterId: ${stratagemDetails?.targetTheaterId}`,
        `PoliticalTheme: ${stratagemDetails?.politicalTheme}`,
        `TargetCompetitor: ${stratagemDetails?.targetCompetitor}`
      );
    } else if (stratagemType === 'printing_propaganda') {
      console.log(`[API /stratagems/try-create] Processing 'printing_propaganda' stratagem with parameters:`,
        `TargetPrintingHouseId: ${stratagemDetails?.targetPrintingHouseId}`,
        `TargetCompetitor: ${stratagemDetails?.targetCompetitor}`,
        `PropagandaTheme: ${stratagemDetails?.propagandaTheme}`
      );
    } else if (stratagemType === 'cargo_mishap') {
      console.log(`[API /stratagems/try-create] Processing 'cargo_mishap' stratagem with parameters:`,
        `TargetContractId: ${stratagemDetails?.targetContractId}`
      );
    } else if (stratagemType === 'marketplace_gossip') {
      console.log(`[API /stratagems/try-create] Processing 'marketplace_gossip' stratagem with parameters:`,
        `TargetCitizen: ${stratagemDetails?.targetCitizen}`,
        `GossipTheme: ${stratagemDetails?.gossipTheme}`
      );
    } else if (stratagemType === 'employee_poaching') {
      console.log(`[API /stratagems/try-create] Processing 'employee_poaching' stratagem with parameters:`,
        `TargetEmployeeUsername: ${stratagemDetails?.targetEmployeeUsername}`,
        `TargetCompetitorUsername: ${stratagemDetails?.targetCompetitorUsername}`
      );
    } else if (stratagemType === 'joint_venture') {
      console.log(`[API /stratagems/try-create] Processing 'joint_venture' stratagem with parameters:`,
        `TargetPartnerUsername: ${stratagemDetails?.targetPartnerUsername}`,
        `VentureDetails: ${stratagemDetails?.ventureDetails}`
      );
    } else if (stratagemType === 'reputation_assault') {
      console.log(`[API /stratagems/try-create] Processing 'reputation_assault' stratagem with parameters:`,
        `TargetCitizen: ${stratagemDetails?.targetCitizen}`,
        `AssaultAngle: ${stratagemDetails?.assaultAngle}`
      );
    } else if (stratagemType === 'monopoly_pricing') {
      console.log(`[API /stratagems/try-create] Processing 'monopoly_pricing' stratagem with parameters:`,
        `TargetResourceType: ${stratagemDetails?.targetResourceType}`,
        `Variant: ${stratagemDetails?.variant}`
      );
    } else if (stratagemType === 'reputation_boost') {
      console.log(`[API /stratagems/try-create] Processing 'reputation_boost' stratagem with parameters:`,
        `TargetCitizenUsername: ${stratagemDetails?.targetCitizenUsername}`,
        `CampaignIntensity: ${stratagemDetails?.campaignIntensity}`,
        `CampaignDurationDays: ${stratagemDetails?.campaignDurationDays}`,
        `CampaignBudget: ${stratagemDetails?.campaignBudget}`
      );
    } else if (stratagemType === 'canal_mugging') {
      console.log(`[API /stratagems/try-create] Processing 'canal_mugging' stratagem with parameters:`,
        `TargetLandId: ${stratagemDetails?.targetLandId}`,
        `Variant: ${stratagemDetails?.variant}`,
        `DurationDays: ${stratagemDetails?.durationDays}`
      );
    } else if (stratagemType === 'burglary') {
      console.log(`[API /stratagems/try-create] Processing 'burglary' stratagem with parameters:`,
        `TargetBuildingId: ${stratagemDetails?.targetBuildingId}` // Already correct
      );
    } else if (stratagemType === 'employee_corruption') {
      console.log(`[API /stratagems/try-create] Processing 'employee_corruption' stratagem with parameters:`,
        `TargetEmployeeUsername: ${stratagemDetails?.targetEmployeeUsername}`,
        `TargetBuildingId: ${stratagemDetails?.targetBuildingId}`,
        `CorruptionGoal: ${stratagemDetails?.corruptionGoal}`,
        `BribeAmountPerPeriod: ${stratagemDetails?.bribeAmountPerPeriod}`
      );
    } else if (stratagemType === 'arson') {
      console.log(`[API /stratagems/try-create] Processing 'arson' stratagem with parameters:`,
        `TargetBuildingId: ${stratagemDetails?.targetBuildingId}`
      );
    } else if (stratagemType === 'charity_distribution') {
      console.log(`[API /stratagems/try-create] Processing 'charity_distribution' stratagem with parameters:`,
        `TargetDistrict: ${stratagemDetails?.targetDistrict}`,
        `TotalDucatsToDistribute: ${stratagemDetails?.totalDucatsToDistribute}`,
        `NumberOfRecipients: ${stratagemDetails?.numberOfRecipients}`
      );
    } else if (stratagemType === 'festival_organisation') {
      console.log(`[API /stratagems/try-create] Processing 'festival_organisation' stratagem with parameters:`,
        `TargetDistrict: ${stratagemDetails?.targetDistrict}`,
        `FestivalTheme: ${stratagemDetails?.festivalTheme}`,
        `FestivalBudget: ${stratagemDetails?.festivalBudget}`,
        `DurationDays: ${stratagemDetails?.durationDays}`
      );
    } else if (stratagemType === 'organize_gathering') {
      console.log(`[API /stratagems/try-create] Processing 'organize_gathering' stratagem with parameters:`,
        `GatheringName: ${stratagemDetails?.gatheringName}`,
        `Location: ${stratagemDetails?.location}`,
        `Purpose: ${stratagemDetails?.purpose}`,
        `Description: ${stratagemDetails?.description}`
      );
    } else if (stratagemType === 'organize_collective_delivery') {
      console.log(`[API /stratagems/try-create] Processing 'organize_collective_delivery' stratagem with parameters:`,
        `TargetBuildingId: ${stratagemDetails?.targetBuildingId}`,
        `TargetCitizenUsername: ${stratagemDetails?.targetCitizenUsername}`,
        `ResourceType: ${stratagemDetails?.resourceType}`,
        `MaxTotalAmount: ${stratagemDetails?.maxTotalAmount}`,
        `RewardPerUnit: ${stratagemDetails?.rewardPerUnit}`,
        `Description: ${stratagemDetails?.description}`
      );
    }

    let parsedPythonEngineUrl: URL;
    try {
      let base = BACKEND_BASE_URL;
      if (!base.startsWith('http://') && !base.startsWith('https://')) {
        console.warn(`[API /stratagems/try-create] BACKEND_BASE_URL (${base}) is missing scheme, prepending http://`);
        base = 'http://' + base;
      }
      // Nouveau endpoint pour les stratagèmes
      parsedPythonEngineUrl = new URL('/api/v1/engine/try-create-stratagem', base);
    } catch (e: any) {
      console.error(`[API /stratagems/try-create] Invalid BACKEND_BASE_URL: ${BACKEND_BASE_URL}. Error: ${e.message}`);
      return NextResponse.json({ success: false, error: 'Internal server configuration error: Python engine URL is invalid.' }, { status: 500 });
    }
    const pythonEngineUrlValidated = parsedPythonEngineUrl.toString();

    console.log(`[API /stratagems/try-create] Calling Python engine at: ${pythonEngineUrlValidated} with payload for stratagem type ${stratagemType}:`, pythonPayload);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 seconds timeout

    let engineResponse;
    try {
      engineResponse = await fetch(pythonEngineUrlValidated, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pythonPayload),
        signal: controller.signal,
      });
    } catch (fetchError: any) {
      if (fetchError.name === 'AbortError') {
        console.error(`[API /stratagems/try-create] Fetch to Python engine timed out after 60 seconds for ${stratagemType}.`);
        return NextResponse.json({ success: false, error: `Python engine request timed out for ${stratagemType}.` }, { status: 504 });
      }
      console.error(`[API /stratagems/try-create] Fetch error calling Python engine for ${stratagemType}:`, fetchError);
      throw fetchError;
    } finally {
      clearTimeout(timeoutId);
    }

    let responseData;
    let responseTextForErrorLog = "";

    try {
      responseData = await engineResponse.json();
    } catch (e) {
      try {
        responseTextForErrorLog = await engineResponse.text();
      } catch (textError) {
        responseTextForErrorLog = "[Could not read response text after JSON parse failure]";
      }
      console.error(`[API /stratagems/try-create] Python engine response was not valid JSON. Status: ${engineResponse.status}. Response text snippet: ${responseTextForErrorLog.substring(0, 500)}`);
      return NextResponse.json(
        { success: false, error: "Python engine returned OK status but non-JSON response.", details: `Status: ${engineResponse.status}, Body: ${responseTextForErrorLog.substring(0, 200)}` },
        { status: engineResponse.ok ? 502 : engineResponse.status }
      );
    }

    if (!engineResponse.ok) {
      console.error(`[API /stratagems/try-create] Error from Python engine (${engineResponse.status}) for ${stratagemType}:`, responseData);
      const pythonErrorString = responseData?.error || responseData?.detail || responseData?.message || engineResponse.statusText || 'Unknown Python engine error';
      return NextResponse.json(
        { success: false, error: `Python engine error for ${stratagemType}: ${pythonErrorString}`, details: responseData },
        { status: engineResponse.status }
      );
    }

    console.log(`[API /stratagems/try-create] Response from Python engine for ${citizenUsername} (stratagem: ${stratagemType}):`, responseData);
    return NextResponse.json(responseData, { status: 200 });

  } catch (error: any) {
    const stratagemTypeForLog = typeof rawBody === 'object' && rawBody !== null && 'stratagemType' in rawBody && typeof rawBody.stratagemType === 'string' ? rawBody.stratagemType : 'unknown';
    console.error(`[API /stratagems/try-create] Internal error for stratagemType ${stratagemTypeForLog}:`, error);
    // ... (gestion d'erreur ECONNREFUSED comme dans l'autre route)
    let isConnectionRefused = false;
    if (error.code === 'ECONNREFUSED') isConnectionRefused = true;
    else if (error.cause?.code === 'ECONNREFUSED') isConnectionRefused = true;
    else if (Array.isArray(error.cause?.errors) && error.cause.errors[0]?.code === 'ECONNREFUSED') isConnectionRefused = true;

    if (isConnectionRefused) {
        const currentBackendBaseUrlForError = process.env.BACKEND_BASE_URL || 'http://localhost:10000';
        console.error(`[API /stratagems/try-create] Detected ECONNREFUSED. Python engine is likely down or unreachable at ${currentBackendBaseUrlForError}.`);
        return NextResponse.json({ success: false, error: `Python engine service is unavailable (ECONNREFUSED). Attempted to reach: ${currentBackendBaseUrlForError}` }, { status: 503 });
    }
    return NextResponse.json({ success: false, error: error.message || 'Failed to process try-create stratagem request' }, { status: 500 });
  }
}

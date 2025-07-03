import { NextRequest, NextResponse } from 'next/server';
import Airtable, { FieldSet, Record as AirtableRecord } from 'airtable';

// Airtable Configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
  throw new Error('Airtable API key or Base ID is not configured for get-artists.');
}

const airtable = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

// Helper to escape single quotes for Airtable formulas
function escapeAirtableValue(value: string | number | boolean): string {
  if (typeof value === 'string') {
    return value.replace(/'/g, "\\'");
  }
  return String(value);
}

interface Artist {
  username: string;
  firstName?: string;
  lastName?: string;
  socialClass?: string;
  color?: string;
  coatOfArms?: string; // URL de l'image du blason
  clout: number;
  // Inclure d'autres champs de CITIZENS si nécessaire
  [key: string]: any; 
}

export async function GET(request: NextRequest) {
  try {
    // 1. Fetch all "Artisti" citizens
    const artistiRecords = await airtable('CITIZENS').select({
      filterByFormula: `{SocialClass} = 'Artisti'`,
      fields: ["Username", "FirstName", "LastName", "SocialClass", "Color", "CoatOfArms"] // Spécifier les champs nécessaires
    }).all();

    if (!artistiRecords || artistiRecords.length === 0) {
      return NextResponse.json({ success: true, artists: [], message: "No artists found." });
    }

    const artistsWithClout: Artist[] = [];

    for (const artistRecord of artistiRecords) {
      const username = artistRecord.fields.Username as string;
      if (!username) continue;

      let totalClout = 0;

      // 2. Fetch relationships where the artist is Citizen1
      const relationshipsAsCitizen1 = await airtable('RELATIONSHIPS').select({
        filterByFormula: `{Citizen1} = '${escapeAirtableValue(username)}'`,
        fields: ["TrustScore"]
      }).all();
      relationshipsAsCitizen1.forEach(rel => {
        totalClout += (rel.fields.TrustScore as number || 0);
      });

      // 3. Fetch relationships where the artist is Citizen2
      const relationshipsAsCitizen2 = await airtable('RELATIONSHIPS').select({
        filterByFormula: `{Citizen2} = '${escapeAirtableValue(username)}'`,
        fields: ["TrustScore"]
      }).all();
      relationshipsAsCitizen2.forEach(rel => {
        totalClout += (rel.fields.TrustScore as number || 0);
      });
      
      // Extraire l'URL du blason si disponible
      let coatOfArmsUrl: string | undefined = undefined;
      const coatOfArmsAttachment = artistRecord.fields.CoatOfArms as any[]; // Airtable retourne un tableau pour les pièces jointes
      if (coatOfArmsAttachment && coatOfArmsAttachment.length > 0 && coatOfArmsAttachment[0].url) {
        coatOfArmsUrl = coatOfArmsAttachment[0].url;
      }

      artistsWithClout.push({
        username: username,
        firstName: artistRecord.fields.FirstName as string | undefined,
        lastName: artistRecord.fields.LastName as string | undefined,
        socialClass: artistRecord.fields.SocialClass as string | undefined,
        color: artistRecord.fields.Color as string | undefined,
        coatOfArms: coatOfArmsUrl,
        clout: totalClout,
        // Copier d'autres champs si nécessaire
        ...artistRecord.fields // Inclure tous les autres champs récupérés
      });
    }

    // 4. Sort artists by clout in descending order
    artistsWithClout.sort((a, b) => b.clout - a.clout);

    return NextResponse.json({ success: true, artists: artistsWithClout });

  } catch (error: any) {
    console.error("[API /get-artists] Error fetching artists:", error);
    return NextResponse.json({ success: false, error: error.message || 'Failed to fetch artists' }, { status: 500 });
  }
}

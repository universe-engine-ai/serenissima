import { NextRequest, NextResponse } from 'next/server';
import { ZodError, z } from 'zod';
import seedrandom from 'seedrandom';

/**
 * Définit la structure attendue pour une œuvre d'art/pièce de théâtre.
 * Basé sur l'utilisation inférée de /api/get-artworks dans production_processor.py.
 */
interface PlayArtwork {
  name: string; // Titre de la pièce
  path: string; // Chemin KinOS ou identifiant de la pièce
  artist?: string; // Nom d'utilisateur de l'artiste/auteur (vient de /api/get-artworks)
  genre?: string;
  category?: string; // Pourrait être utilisé pour filtrer les pièces si nécessaire
  // ... autres champs potentiels retournés par /api/get-artworks
  [key: string]: any;
}

// Schéma de validation pour les paramètres de requête
const QueryParamsSchema = z.object({
  buildingId: z.string().min(1, "L'ID du bâtiment (buildingId) est requis."),
});

/**
 * Récupère toutes les œuvres d'art (supposées être des pièces de théâtre) depuis l'API /api/get-artworks.
 * TODO: Si /api/get-artworks retourne différents types d'œuvres,
 * un filtrage (par exemple, par art.category === 'play') pourrait être nécessaire ici.
 */
async function getAllPlays(): Promise<PlayArtwork[]> {
  const artworksApiUrl = `${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/api/get-artworks?specialty=Playwright`;
  console.log(`[API get-theater-current-representation] Fetching plays from: ${artworksApiUrl}`);
  try {
    const response = await fetch(artworksApiUrl);
    if (!response.ok) {
      console.error(`[API get-theater-current-representation] Échec de la récupération des œuvres: ${response.status} ${response.statusText}`);
      return [];
    }
    const data = await response.json();
    if (data.success && Array.isArray(data.artworks)) {
      // data.artworks est un tableau d'objets ArtworkFile qui incluent 'artist'
      // PlayArtwork est compatible avec ArtworkFile si authorUsername est remplacé par artist
      return data.artworks as PlayArtwork[];
    }
    console.warn("[API get-theater-current-representation] Aucune œuvre trouvée ou la réponse de l'API (/api/get-artworks) n'a pas abouti. Réponse:", data);
    return [];
  } catch (error) {
    console.error("[API get-theater-current-representation] Erreur lors de la récupération des œuvres:", error);
    return [];
  }
}

/**
 * Récupère les clouts de tous les artistes.
 */
async function getArtistsCloutMap(): Promise<Map<string, number>> {
  const artistsCloutMap = new Map<string, number>();
  const artistsApiUrl = `${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/api/get-artists`;
  try {
    const response = await fetch(artistsApiUrl);
    if (!response.ok) {
      console.error(`[API get-theater-current-representation] Échec de la récupération des artistes: ${response.status} ${response.statusText}`);
      return artistsCloutMap;
    }
    const data = await response.json();
    if (data.success && Array.isArray(data.artists)) {
      data.artists.forEach((artist: any) => {
        if (artist.username && typeof artist.clout === 'number') {
          artistsCloutMap.set(artist.username, artist.clout);
        }
      });
    } else {
      console.warn("[API get-theater-current-representation] Aucun artiste trouvé ou la réponse de l'API (/api/get-artists) n'a pas abouti. Réponse:", data);
    }
  } catch (error) {
    console.error("[API get-theater-current-representation] Erreur lors de la récupération des artistes:", error);
  }
  return artistsCloutMap;
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const buildingId = searchParams.get('buildingId');

    // Valider les paramètres de requête
    const validationResult = QueryParamsSchema.safeParse({ buildingId });
    if (!validationResult.success) {
      return NextResponse.json({ success: false, error: "Paramètres de requête invalides", details: validationResult.error.flatten() }, { status: 400 });
    }

    const validBuildingId = validationResult.data.buildingId;

    const allPlays = await getAllPlays();

    if (!allPlays || allPlays.length === 0) {
      return NextResponse.json({ success: false, error: "Aucune pièce de théâtre disponible pour la sélection." }, { status: 404 });
    }

    // Générer une graine basée sur buildingId et la date actuelle (YYYY-MM-DD)
    // Cela garantit que pour un bâtiment donné, la même pièce est choisie chaque jour.
    const currentDate = new Date().toISOString().split('T')[0]; // Format YYYY-MM-DD
    const seed = `${validBuildingId}-${currentDate}`;
    const rng = seedrandom(seed);

    let selectedPlay: PlayArtwork | null = null;

    const artistsClout = await getArtistsCloutMap();
    const playsWithClout: { play: PlayArtwork; clout: number }[] = [];

    if (artistsClout.size > 0) {
      allPlays.forEach(play => {
        if (play.artist) {
          const clout = artistsClout.get(play.artist);
          if (clout !== undefined && clout > 0) {
            playsWithClout.push({ play, clout });
          }
        }
      });
    }

    if (playsWithClout.length > 0) {
      const totalClout = playsWithClout.reduce((sum, item) => sum + item.clout, 0);
      
      if (totalClout > 0) {
        const selectionPoint = rng() * totalClout;
        let currentCloutSum = 0;
        for (const item of playsWithClout) {
          currentCloutSum += item.clout;
          if (currentCloutSum >= selectionPoint) {
            selectedPlay = item.play;
            break;
          }
        }
        // Fallback si quelque chose ne va pas avec la sélection pondérée (ne devrait pas arriver si totalClout > 0)
        if (!selectedPlay) selectedPlay = playsWithClout[playsWithClout.length - 1].play;
        
        console.log(`[API get-theater-current-representation] Sélection pondérée par clout pour buildingId '${validBuildingId}', date '${currentDate}'. Pièce: '${selectedPlay.name}', Artiste: ${selectedPlay.artist}, Clout: ${artistsClout.get(selectedPlay.artist || '')}`);
      }
    }
    
    // Fallback: Si aucune pièce avec clout n'a été trouvée/sélectionnée, ou si totalClout était 0
    if (!selectedPlay) {
      if (allPlays.length > 0) {
        const randomIndex = Math.floor(rng() * allPlays.length);
        selectedPlay = allPlays[randomIndex];
        console.log(`[API get-theater-current-representation] Fallback: Sélection aléatoire simple pour buildingId '${validBuildingId}', date '${currentDate}'. Pièce: '${selectedPlay.name}' (index: ${randomIndex})`);
      } else {
        // Ce cas est déjà géré par le check allPlays.length === 0 plus haut, mais par sécurité.
        return NextResponse.json({ success: false, error: "Aucune pièce de théâtre disponible pour la sélection (après filtrage et fallback)." }, { status: 404 });
      }
    }

    return NextResponse.json({ success: true, representation: selectedPlay }, { status: 200 });

  } catch (error) {
    console.error("[API get-theater-current-representation] Erreur:", error);
    if (error instanceof ZodError) { // Devrait être intercepté par safeParse, mais par sécurité
      return NextResponse.json({ success: false, error: "Erreur de validation", details: error.errors }, { status: 400 });
    }
    const errorMessage = error instanceof Error ? error.message : "Erreur interne du serveur";
    return NextResponse.json({ success: false, error: "Erreur interne du serveur", details: errorMessage }, { status: 500 });
  }
}

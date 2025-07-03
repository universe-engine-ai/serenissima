import { NextRequest, NextResponse } from 'next/server';

const KINOS_API_KEY = process.env.KINOS_API_KEY;
// This base URL already includes /v2/blueprints/serenissima-ai/kins
const KINOS_API_BASE_URL = "https://api.kinos-engine.ai/v2/blueprints/serenissima-ai/kins"; 

if (!KINOS_API_KEY) {
  console.error("[API kins/content] KINOS_API_KEY is not set in environment variables.");
  // We don't throw here as it would break the build, but requests will fail if key is missing.
}

interface KinOSFile {
  path: string;
  type?: 'file' | 'directory'; // KinOS might use 'type' or 'is_directory'
  is_directory?: boolean;      // KinOS might use 'type' or 'is_directory'
  size?: number; 
  last_modified: string;
  content?: string;
  is_binary?: boolean;
  name?: string; // We will add this for convenience
  [key: string]: any;
}

interface KinOSDirectoryContentResponse {
  path: string;
  is_directory: boolean;
  last_modified: string;
  files: KinOSFile[];
  [key: string]: any;
}

interface KinOSSingleFileResponse {
  path: string;
  content: string;
  is_directory: boolean; // Should be false for a single file
  size: number;
  last_modified: string;
  is_binary: boolean;
  [key: string]: any;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ kinId: string }> }
) {
  const { kinId } = await params;
  const { searchParams } = new URL(request.url);
  let pathParam = searchParams.get('path'); // Make pathParam mutable

  if (!KINOS_API_KEY) {
    return NextResponse.json({ success: false, error: 'Server configuration error: KinOS API key not set.' }, { status: 500 });
  }

  if (!kinId) {
    return NextResponse.json({ success: false, error: 'Kin ID is required.' }, { status: 400 });
  }
  if (!pathParam) {
    return NextResponse.json({ success: false, error: 'Path parameter is required.' }, { status: 400 });
  }

  // Normalize path for "AI-Memories" to "AI-memories"
  let effectivePathParam = pathParam;
  if (pathParam.toLowerCase() === 'ai-memories') {
    effectivePathParam = 'AI-memories'; // KinOS expects 'm' lowercase for this specific path
    console.log(`[API kins/content] Path parameter '${pathParam}' normalized to '${effectivePathParam}' for KinOS API call.`);
  }

  const kinosContentUrl = `${KINOS_API_BASE_URL}/${encodeURIComponent(kinId)}/content?path=${encodeURIComponent(effectivePathParam)}`;
  console.log(`[API kins/content] Fetching content for kin '${kinId}', path '${effectivePathParam}' from KinOS: ${kinosContentUrl}`);

  try {
    const kinosResponse = await fetch(kinosContentUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${KINOS_API_KEY}`,
        'Accept': 'application/json',
      },
      cache: 'no-store', // Or consider 'next: { revalidate: 60 }' if caching is desired
    });

    if (!kinosResponse.ok) {
      const errorText = await kinosResponse.text();
      let errorJson: any = null;
      try { errorJson = JSON.parse(errorText); } catch (e) { /* ignore parsing error */ }
      
      const detail = errorJson?.error || errorJson?.detail || `KinOS API error: ${kinosResponse.status}`;
      console.error(`[API kins/content] KinOS API error for kin '${kinId}', path '${effectivePathParam}': ${kinosResponse.status} - ${detail}. Full text: ${errorText}`);
      
      if (kinosResponse.status === 404 && (detail.includes("Path not found") || detail.includes("Kin not found") || detail.includes("not found in kin"))) {
        return NextResponse.json({ success: true, files: [], message: `Path '${effectivePathParam}' or Kin '${kinId}' not found.` }, { status: 200 }); // Return empty array for 404s
      }
      return NextResponse.json({ success: false, error: detail, rawError: errorText }, { status: kinosResponse.status });
    }

    const kinosData: KinOSDirectoryContentResponse | KinOSSingleFileResponse = await kinosResponse.json();

    // Check if the response is for a directory
    if (kinosData.is_directory === true && Array.isArray((kinosData as KinOSDirectoryContentResponse).files)) {
      const directoryData = kinosData as KinOSDirectoryContentResponse;
      const journalEntries = directoryData.files
        .filter(file => file.is_directory !== true && file.type !== 'directory' && !file.path.endsWith('/')) // Ensure it's a file
        .map(file => {
          const name = file.path.split('/').pop() || file.path;
          return {
            ...file,
            name: name,
            content: file.content || '', // Ensure content is always a string
          };
        });
      return NextResponse.json({ success: true, files: journalEntries });
    } 
    // Check if the response is for a single file
    else if (kinosData.is_directory === false && (kinosData as KinOSSingleFileResponse).content !== undefined) {
      const fileData = kinosData as KinOSSingleFileResponse;
      const fileName = fileData.path.split('/').pop() || fileData.path;
      return NextResponse.json({ 
        success: true, 
        files: [{
          ...fileData,
          name: fileName,
        }],
        is_single_file: true 
      });
    }
    // If neither, it's an unexpected format
    else {
      console.warn(`[API kins/content] Unexpected KinOS response format for kin '${kinId}', path '${effectivePathParam}'.`, kinosData);
      return NextResponse.json({ success: false, error: 'Unexpected KinOS response format. Expected directory with files array or a single file structure.' }, { status: 500 });
    }

  } catch (error: any) {
    console.error(`[API kins/content] General error fetching KinOS content for kin '${kinId}', path '${effectivePathParam}':`, error);
    return NextResponse.json({ success: false, error: error.message || 'An unexpected server error occurred' }, { status: 500 });
  }
}

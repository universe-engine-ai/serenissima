// Transport utility functions shared between transport routes

// Define speeds
const WALKING_SPEED_MPS = 1.4; // meters per second
const GONDOLA_SPEED_MPS = WALKING_SPEED_MPS * 2; // Gondolas are twice as fast

// Helper function to calculate haversine distance between two points
function haversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = lat1 * Math.PI / 180;
  const φ2 = lat2 * Math.PI / 180;
  const Δφ = (lat2 - lat1) * Math.PI / 180;
  const Δλ = (lon2 - lon1) * Math.PI / 180;

  const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
          Math.cos(φ1) * Math.cos(φ2) *
          Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  const distance = R * c;
  return distance;
}

// Helper function to calculate travel time considering different transport modes
export function calculatePathTravelTime(path: {lat: number, lng: number, transportMode?: string}[]): number {
  let totalTravelTimeSeconds = 0;
  if (!path || path.length < 2) {
    return 0;
  }

  for (let i = 1; i < path.length; i++) {
    const point1 = path[i - 1];
    const point2 = path[i];
    
    const segmentDistance = haversineDistance(point1.lat, point1.lng, point2.lat, point2.lng);
    // Assume point2.transportMode indicates the mode used to travel from point1 to point2
    const mode = point2.transportMode; 
    const speed = (mode === 'gondola') ? GONDOLA_SPEED_MPS : WALKING_SPEED_MPS;
    
    if (speed > 0) {
      totalTravelTimeSeconds += segmentDistance / speed;
    }
  }
  return totalTravelTimeSeconds;
}

// Function to extract journey information from the path
export function extractJourneyFromPath(path: any[]): any[] {
  if (!path || !Array.isArray(path) || path.length === 0) {
    return [];
  }
  
  const journey: any[] = [];
  let currentLandId: string | null = null;
  
  // Process each point in the path
  for (const point of path) {
    // Skip intermediate points to avoid duplicates
    if (point.isIntermediatePoint) {
      continue;
    }
    
    // Check if we're on a bridge
    if (point.onBridge && point.bridgeId) {
      // Add bridge info
      journey.push({
        type: 'bridge',
        id: point.bridgeId,
        name: point.bridgeName || 'Unknown Bridge',
        position: point,
        transportMode: point.transportMode || 'walking'
      });
      currentLandId = null; // Reset land tracking when on bridge
    }
    // Check if we're entering a new land
    else if (point.landId && point.landId !== currentLandId) {
      currentLandId = point.landId;
      journey.push({
        type: 'land',
        id: point.landId,
        name: point.landName || `Land ${point.landId}`,
        owner: point.landOwner || null,
        position: point,
        transportMode: point.transportMode || 'walking'
      });
    }
    // Check if this is a special location (start/end)
    else if (point.isStart || point.isEnd) {
      journey.push({
        type: point.isStart ? 'start' : 'end',
        position: point,
        landId: point.landId || null,
        landName: point.landName || null,
        transportMode: point.transportMode || 'walking'
      });
    }
  }
  
  return journey;
}

// Helper function to calculate the total distance of a path in meters
export function calculatePathDistance(path: {lat: number, lng: number}[]): number {
  let totalDistance = 0;
  
  for (let i = 1; i < path.length; i++) {
    const point1 = path[i - 1];
    const point2 = path[i];
    
    totalDistance += haversineDistance(point1.lat, point1.lng, point2.lat, point2.lng);
  }
  
  return totalDistance;
}

export async function fetchTransporterDetails(path: any[]): Promise<string | null> {
  let transporter = null;
  const usesGondola = path.some((p: any) => p.transportMode === 'gondola');

  if (usesGondola) {
    try {
      // Call the API to get gondola service information
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://serenissima.ai'}/api/contracts`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        const contracts = data.contracts || [];
        
        // Find public gondola service contracts
        const gondolaContracts = contracts.filter((contract: any) => 
          contract.ContractType === 'public_gondola_service' && 
          contract.Status === 'active'
        );

        if (gondolaContracts.length > 0) {
          // Get the first active gondola service provider
          const gondolaContract = gondolaContracts[0];
          const providerName = gondolaContract.CreatorName || gondolaContract.Creator || 'Unknown Gondola Service';
          const serviceName = gondolaContract.ServiceName || 'Public Gondola Service';
          transporter = `${serviceName} (${providerName})`;
        }
      }
    } catch (error) {
      console.error('Error fetching gondola service details:', error);
    }
  }

  return transporter;
}
import { NextResponse } from 'next/server';
import Airtable from 'airtable';

// Configure Airtable
const apiKey = process.env.AIRTABLE_API_KEY;
const baseId = process.env.AIRTABLE_BASE_ID;

// Initialize Airtable base
const base = new Airtable({ apiKey }).base(baseId);

// Function to parse BuildingId to extract location information
function parseBuildingId(buildingId: string): { id: string, lat?: number, lng?: number } {
  // Check if it follows the pattern building_LAT_LNG
  const parts = buildingId.split('_');
  if (parts.length >= 3) {
    const lat = parseFloat(parts[1]);
    const lng = parseFloat(parts[2]);
    
    if (!isNaN(lat) && !isNaN(lng)) {
      return { id: buildingId, lat, lng };
    }
  }
  
  // Return just the ID if we couldn't parse coordinates
  return { id: buildingId };
}

// Helper function to convert resource name to icon filename
function getResourceIconFromName(resourceName: string): string {
  // Convert the resource name to lowercase, replace spaces with underscores
  const formattedName = resourceName.toLowerCase().replace(/\s+/g, '_');
  
  // Return the formatted name with .png extension
  return `${formattedName}.png`;
}

export async function GET(request: Request) {
  try {
    // Get URL parameters
    const { searchParams } = new URL(request.url);
    const owner = searchParams.get('owner');
    const buildingId = searchParams.get('buildingId');
    
    console.log(`Loading resource counts${owner ? ` for owner: ${owner}` : ''}${buildingId ? ` for building: ${buildingId}` : ''}`);
    
    // Query Airtable directly
    const records = await new Promise((resolve, reject) => {
      const allRecords: any[] = [];
      
      // Build filter formula based on parameters
      let filterFormula = '';
      if (buildingId) {
        // Use direct equality with proper escaping for Airtable formula
        // The SEARCH function doesn't work well with special characters like dots
        const escapedBuildingId = buildingId.replace(/'/g, "\\'");
        
        // Use Airtable's AND() function for proper formula syntax
        filterFormula = `AND({Asset}='${escapedBuildingId}', {AssetType}='building')`;
      }
      
      const selectOptions: any = {
        view: 'Grid view'
      };
      
      if (filterFormula) {
        selectOptions.filterByFormula = filterFormula;
        console.log(`Using Airtable filter formula: ${filterFormula}`);
        console.log(`Looking for resources with Asset=${buildingId} and AssetType=building`);
      }
      
      base('RESOURCES')
        .select(selectOptions)
        .eachPage(
          function page(records, fetchNextPage) {
            records.forEach(record => {
              allRecords.push(record);
            });
            fetchNextPage();
          },
          function done(err) {
            if (err) {
              console.error('Error fetching resources from Airtable:', err);
              reject(err);
              return;
            }
            resolve(allRecords);
          }
        );
    });
    
    // Create maps to aggregate resources by type - one for player resources, one for global, one for building
    // Define a resource type interface to use throughout the file
    interface ResourceType {
      id: string;
      name: string;
      category: string;
      subCategory: string;
      icon: string;
      count: number;
      rarity: string;
      description: string;
      buildingId?: string;
      location?: { lat: number, lng: number } | null;
    }

    const playerResourceMap = new Map<string, ResourceType>();
    const globalResourceMap = new Map<string, ResourceType>();
    const buildingResourceMap = new Map<string, ResourceType>();
    
    // Process records to count resources by type
    (records as any[]).forEach(record => {
      const resourceId = record.get('ResourceId');
      const resourceType = record.get('Type');
      const resourceName = record.get('Name') || resourceType;
      const resourceCategory = record.get('Category') || 'raw_materials';
      const resourceSubCategory = record.get('SubCategory') || '';
      const resourceCount = record.get('Count') || 1;
      const resourceIcon = record.get('Icon') || 'default.png';
      const resourceRarity = record.get('Rarity') || 'common';
      const resourceDescription = record.get('Description') || '';
      const resourceOwner = record.get('Owner') || '';
      const assetId = record.get('Asset') || '';
      const assetType = record.get('AssetType') || '';
      
      // Parse asset ID to extract location if available (when asset is a building)
      const parsedBuildingId = assetType === 'building' && assetId ? parseBuildingId(assetId) : { id: '' };
      
      // Generate icon filename from resource name
      const iconFromName = getResourceIconFromName(resourceName);
      
      // Create a unique key for this resource type
      const key = resourceType;
      
      // Add to global resource map
      if (globalResourceMap.has(key)) {
        // If we already have this resource type, increment the count
        const existingResource = globalResourceMap.get(key);
        existingResource.count += resourceCount;
      } else {
        // Otherwise, add a new entry
        globalResourceMap.set(key, {
          id: resourceId,
          name: resourceName,
          category: resourceCategory,
          subCategory: resourceSubCategory,
          icon: iconFromName,
          count: resourceCount,
          rarity: resourceRarity,
          description: resourceDescription,
          buildingId: parsedBuildingId.id,
          location: parsedBuildingId.lat && parsedBuildingId.lng ? { lat: parsedBuildingId.lat, lng: parsedBuildingId.lng } : null
        });
      }
      
      // Add to player resource map if it belongs to the specified owner
      if (owner && resourceOwner === owner) {
        if (playerResourceMap.has(key)) {
          // If we already have this resource type, increment the count
          const existingResource = playerResourceMap.get(key);
          existingResource.count += resourceCount;
        } else {
          // Otherwise, add a new entry
          playerResourceMap.set(key, {
            id: resourceId,
            name: resourceName,
            category: resourceCategory,
            subCategory: resourceSubCategory,
            icon: iconFromName,
            count: resourceCount,
            rarity: resourceRarity,
            description: resourceDescription,
            buildingId: parsedBuildingId.id,
            location: parsedBuildingId.lat && parsedBuildingId.lng ? { lat: parsedBuildingId.lat, lng: parsedBuildingId.lng } : null
          });
        }
      }
      
      // Add to building resource map if we're filtering by buildingId
      if (buildingId && assetType === 'building' && assetId === buildingId) {
        if (buildingResourceMap.has(key)) {
          // If we already have this resource type, increment the count
          const existingResource = buildingResourceMap.get(key);
          existingResource.count += resourceCount;
        } else {
          // Otherwise, add a new entry
          buildingResourceMap.set(key, {
            id: resourceId,
            name: resourceName,
            category: resourceCategory,
            subCategory: resourceSubCategory,
            icon: iconFromName,
            count: resourceCount,
            rarity: resourceRarity,
            description: resourceDescription,
            buildingId: assetId,
            location: parsedBuildingId.lat && parsedBuildingId.lng ? { lat: parsedBuildingId.lat, lng: parsedBuildingId.lng } : null
          });
        }
      }
    });
    
    // Convert maps to arrays and sort by category and name
    const globalResourceCounts = Array.from(globalResourceMap.values())
      .sort((a, b) => {
        // First sort by category
        if (a.category !== b.category) {
          return a.category.localeCompare(b.category);
        }
        // Then by subCategory
        if (a.subCategory !== b.subCategory) {
          return a.subCategory.localeCompare(b.subCategory);
        }
        // Finally by name
        return a.name.localeCompare(b.name);
      });
    
    const playerResourceCounts = Array.from(playerResourceMap.values())
      .sort((a, b) => {
        // First sort by category
        if (a.category !== b.category) {
          return a.category.localeCompare(b.category);
        }
        // Then by subCategory
        if (a.subCategory !== b.subCategory) {
          return a.subCategory.localeCompare(b.subCategory);
        }
        // Finally by name
        return a.name.localeCompare(b.name);
      });
    
    const buildingResourceCounts = Array.from(buildingResourceMap.values())
      .sort((a, b) => {
        // First sort by category
        if (a.category !== b.category) {
          return a.category.localeCompare(b.category);
        }
        // Then by subCategory
        if (a.subCategory !== b.subCategory) {
          return a.subCategory.localeCompare(b.subCategory);
        }
        // Finally by name
        return a.name.localeCompare(b.name);
      });
    
    console.log(`Returning ${globalResourceCounts.length} global resource types, ${playerResourceCounts.length} player resource types, and ${buildingResourceCounts.length} building resource types`);
    
    // Log sample resource data for debugging
    console.log('Sample global resource data being returned:');
    console.log(globalResourceCounts.slice(0, 3).map(r => ({
      name: r.name,
      icon: r.icon,
      category: r.category
    })));
    
    return NextResponse.json({
      success: true,
      globalResourceCounts,
      playerResourceCounts,
      buildingResourceCounts
    });
  } catch (error) {
    console.error('Error loading resource counts:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to load resource counts',
        details: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
}

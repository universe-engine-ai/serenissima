import { NextResponse } from 'next/server';
import Airtable from 'airtable';

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
  throw new Error('Airtable configuration missing');
}

const airtable = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

interface ResourceSummary {
  resourceType: string;
  resourceName: string;
  totalCount: number;
  ownerBreakdown: Array<{
    owner: string;
    count: number;
  }>;
}

interface OwnerResourceSummary {
  owner: string;
  resourceType: string;
  resourceName: string;
  count: number;
}

export async function GET() {
  try {
    // Fetch all resources
    const resourceRecords = await airtable('RESOURCES').select({
      fields: ['Type', 'Name', 'Owner', 'Count'],
      filterByFormula: "AND({Count} > 0, {Owner} != '')"
    }).all();

    // Fetch resource shortage problems
    const problemRecords = await airtable('PROBLEMS').select({
      fields: ['Type', 'Asset', 'AssetType', 'Title', 'Description', 'Status', 'Citizen', 'Location'],
      filterByFormula: "AND({Type} = 'resource_shortage', {Status} = 'active')"
    }).all();

    // Process data for resource summaries
    const resourceMap = new Map<string, ResourceSummary>();
    const ownerResourceMap = new Map<string, number>();

    resourceRecords.forEach(record => {
      const type = record.fields.Type as string;
      const name = record.fields.Name as string || type;
      const owner = record.fields.Owner as string;
      const count = parseFloat(record.fields.Count as string || '0');

      if (!type || !owner || count <= 0) return;

      // Update resource summary
      if (!resourceMap.has(type)) {
        resourceMap.set(type, {
          resourceType: type,
          resourceName: name,
          totalCount: 0,
          ownerBreakdown: []
        });
      }

      const resourceSummary = resourceMap.get(type)!;
      resourceSummary.totalCount += count;

      // Find or create owner entry
      const ownerEntry = resourceSummary.ownerBreakdown.find(o => o.owner === owner);
      if (ownerEntry) {
        ownerEntry.count += count;
      } else {
        resourceSummary.ownerBreakdown.push({ owner, count });
      }

      // Update owner-resource map
      const ownerResourceKey = `${owner}|${type}`;
      ownerResourceMap.set(ownerResourceKey, (ownerResourceMap.get(ownerResourceKey) || 0) + count);
    });

    // Sort and get top 10 resources by total count
    const topResources = Array.from(resourceMap.values())
      .sort((a, b) => b.totalCount - a.totalCount)
      .slice(0, 10);

    // Sort owner breakdown within each resource
    topResources.forEach(resource => {
      resource.ownerBreakdown.sort((a, b) => b.count - a.count);
    });

    // Get top 10 owner-resource combinations
    const ownerResourceList: OwnerResourceSummary[] = [];
    ownerResourceMap.forEach((count, key) => {
      const [owner, resourceType] = key.split('|');
      const resourceName = resourceMap.get(resourceType)?.resourceName || resourceType;
      ownerResourceList.push({
        owner,
        resourceType,
        resourceName,
        count
      });
    });

    const topOwnerResources = ownerResourceList
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Process resource shortage problems - deduplicate by resource type
    const resourceShortages = new Map<string, any>();
    problemRecords.forEach(record => {
      const description = record.fields.Description as string;
      // Extract resource type from description (typically in format "resource_type shortage")
      const resourceMatch = description?.match(/^(\w+) shortage/);
      if (resourceMatch) {
        const resourceType = resourceMatch[1];
        if (!resourceShortages.has(resourceType)) {
          resourceShortages.set(resourceType, {
            resourceType,
            title: record.fields.Title as string,
            description: record.fields.Description as string,
            location: record.fields.Location as string,
            citizen: record.fields.Citizen as string,
            asset: record.fields.Asset as string
          });
        }
      }
    });

    return NextResponse.json({
      success: true,
      topResources,
      topOwnerResources,
      resourceShortages: Array.from(resourceShortages.values()),
      totalResourceTypes: resourceMap.size,
      totalOwners: new Set(resourceRecords.map(r => r.fields.Owner as string).filter(Boolean)).size
    });

  } catch (error) {
    console.error('Error calculating resource economics:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to calculate resource economics' },
      { status: 500 }
    );
  }
}
import { NextResponse } from 'next/server';
import Airtable from 'airtable';

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
  throw new Error('Airtable configuration missing');
}

const airtable = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

export async function GET() {
  try {
    // Calculate 24 hours ago
    const twentyFourHoursAgo = new Date();
    twentyFourHoursAgo.setHours(twentyFourHoursAgo.getHours() - 24);
    const twentyFourHoursAgoISO = twentyFourHoursAgo.toISOString();

    // Fetch activities from the last 24 hours
    const activityRecords = await airtable('ACTIVITIES').select({
      fields: ['Type', 'StartDate', 'EndDate', 'Status'],
      filterByFormula: `AND(
        {EndDate} >= '${twentyFourHoursAgoISO}',
        OR(
          {Status} = 'completed',
          {Status} = 'failed'
        )
      )`
    }).all();

    // Group activities by type
    const activityTypeMap = new Map<string, number>();
    let totalActivities = 0;

    activityRecords.forEach(record => {
      const type = record.fields.Type as string;
      if (type) {
        activityTypeMap.set(type, (activityTypeMap.get(type) || 0) + 1);
        totalActivities++;
      }
    });

    // Convert to array and sort by count
    const activitiesByType = Array.from(activityTypeMap.entries())
      .map(([type, count]) => ({
        type: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), // Format type name
        count
      }))
      .sort((a, b) => b.count - a.count);

    // Get top activity types
    const topTypes = activitiesByType.slice(0, 5);

    return NextResponse.json({
      success: true,
      activitiesByType,
      topTypes,
      totalActivities,
      totalTypes: activityTypeMap.size,
      timeRange: {
        start: twentyFourHoursAgo.toISOString(),
        end: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('Error calculating activities economics:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to calculate activities economics' },
      { status: 500 }
    );
  }
}
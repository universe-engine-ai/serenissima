import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';
import { z } from 'zod';
import { subDays, formatISO } from 'date-fns';

const CitizenIdParamsSchema = z.object({
  citizenId: z.string().min(1, "citizenId is required"), // citizenId is the Username
});

interface TransactionRecord {
  id: string;
  fields: {
    Type?: string;
    // AssetType and Asset might not be directly relevant for citizen-centric view, but good to have
    AssetType?: string; 
    Asset?: string;
    Seller?: string;
    Buyer?: string;
    Price?: number;
    ExecutedAt?: string;
    [key: string]: any; 
  };
}

interface AggregatedTransaction {
  type: string;
  totalAmount: number;
  count: number;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ citizenId: string }> }
): Promise<NextResponse> {
  try {
    const resolvedParams = await params;
    const paramsValidation = CitizenIdParamsSchema.safeParse(resolvedParams);
    if (!paramsValidation.success) {
      return NextResponse.json({ success: false, error: "Invalid citizenId parameter", details: paramsValidation.error.format() }, { status: 400 });
    }
    const { citizenId } = paramsValidation.data; // This is the Username

    const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
    const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      console.error('Airtable credentials not configured for citizen-economics');
      return NextResponse.json({ success: false, error: 'Airtable credentials not configured' }, { status: 500 });
    }
    const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);
    const transactionsTable = base('TRANSACTIONS');
    const sevenDaysAgo = formatISO(subDays(new Date(), 7));

    // Filter for transactions where the citizen is either the Buyer or the Seller
    const filterFormula = `AND(OR({Buyer} = '${citizenId}', {Seller} = '${citizenId}'), IS_AFTER({ExecutedAt}, '${sevenDaysAgo}'))`;

    console.log(`[API citizen-economics] Fetching transactions for citizen ${citizenId} with formula: ${filterFormula}`);

    const records = await transactionsTable.select({
      filterByFormula: filterFormula,
      fields: ['Type', 'Seller', 'Buyer', 'Price', 'ExecutedAt', 'Asset', 'AssetType'], // Added Asset, AssetType
      sort: [{ field: 'ExecutedAt', direction: 'desc' }],
    }).all() as unknown as TransactionRecord[];

    console.log(`[API citizen-economics] Found ${records.length} transactions for citizen ${citizenId}`);

    const debits: Record<string, { totalAmount: number; count: number }> = {}; // Expenses for the citizen
    const credits: Record<string, { totalAmount: number; count: number }> = {}; // Income for the citizen
    let totalDebitsAmount = 0;
    let totalCreditsAmount = 0;

    records.forEach(record => {
      const type = record.fields.Type || 'Unknown Transaction';
      const price = record.fields.Price || 0;

      if (record.fields.Buyer === citizenId) { // Citizen is the buyer, so it's a debit (expense)
        if (!debits[type]) {
          debits[type] = { totalAmount: 0, count: 0 };
        }
        debits[type].totalAmount += price;
        debits[type].count += 1;
        totalDebitsAmount += price;
      } else if (record.fields.Seller === citizenId) { // Citizen is the seller, so it's a credit (income)
        if (!credits[type]) {
          credits[type] = { totalAmount: 0, count: 0 };
        }
        credits[type].totalAmount += price;
        credits[type].count += 1;
        totalCreditsAmount += price;
      }
      // Transactions where the citizen is neither buyer nor seller but are caught by a broader filter
      // (e.g. if Asset was citizenId) would be ignored here, which is correct for this ledger.
    });

    const formattedDebits: AggregatedTransaction[] = Object.entries(debits).map(([type, data]) => ({
      type,
      ...data,
    }));

    const formattedCredits: AggregatedTransaction[] = Object.entries(credits).map(([type, data]) => ({
      type,
      ...data,
    }));
    
    const netChange = totalCreditsAmount - totalDebitsAmount;

    return NextResponse.json({
      success: true,
      citizenId,
      periodStartDate: sevenDaysAgo,
      periodEndDate: formatISO(new Date()),
      ledger: {
        debits: formattedDebits,
        credits: formattedCredits,
        summary: {
          totalDebits: totalDebitsAmount,
          totalCredits: totalCreditsAmount,
          netChange: netChange, // Changed from netProfit to netChange
        },
      },
    });

  } catch (error: any) {
    console.error('[API citizen-economics] Error fetching citizen economics:', error);
    return NextResponse.json({ success: false, error: error.message || 'Failed to fetch citizen economics data' }, { status: 500 });
  }
}

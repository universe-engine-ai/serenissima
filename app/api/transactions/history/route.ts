import { NextRequest, NextResponse } from 'next/server';
import Airtable from 'airtable';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');
    const limit = parseInt(searchParams.get('limit') || '1000');
    
    // Initialize Airtable
    const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
    const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;
    
    if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
      console.error('Airtable credentials not configured');
      return NextResponse.json({ 
        success: false, 
        error: 'Airtable credentials not configured' 
      }, { status: 500 });
    }
    
    const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);
    const transactionsTable = base('TRANSACTIONS');
    
    // Build filter formula
    let filterParts = [];
    
    // Only get executed transactions
    filterParts.push("NOT({ExecutedAt} = '')");
    
    // Date filtering
    if (startDate) {
      filterParts.push(`IS_AFTER({ExecutedAt}, '${startDate}')`);
    }
    if (endDate) {
      filterParts.push(`IS_BEFORE({ExecutedAt}, '${endDate}')`);
    }
    
    const filterFormula = filterParts.length > 0 ? `AND(${filterParts.join(', ')})` : '';
    
    console.log(`Fetching transactions with formula: ${filterFormula}`);
    
    // Fetch transactions
    const records = await transactionsTable
      .select({
        filterByFormula: filterFormula,
        sort: [{ field: 'ExecutedAt', direction: 'desc' }],
        maxRecords: limit,
        fields: ['Type', 'Asset', 'AssetType', 'Seller', 'Buyer', 'Price', 'CreatedAt', 'ExecutedAt', 'Notes']
      })
      .all();
    
    console.log(`Found ${records.length} transactions`);
    
    // Format transactions
    const transactions = records.map(record => {
      const fields = record.fields;
      
      // Parse notes if available
      let notes = {};
      if (fields.Notes) {
        try {
          notes = JSON.parse(String(fields.Notes));
        } catch (e) {
          // If notes is not JSON, just use as string
          notes = { raw: fields.Notes };
        }
      }
      
      return {
        id: record.id,
        type: fields.Type || 'Unknown',
        asset: fields.Asset || '',
        assetType: fields.AssetType || '',
        seller: fields.Seller || '',
        buyer: fields.Buyer || '',
        price: parseFloat(String(fields.Price)) || 0,
        createdAt: fields.CreatedAt || '',
        executedAt: fields.ExecutedAt || '',
        notes: notes
      };
    });
    
    return NextResponse.json({
      success: true,
      transactions,
      count: transactions.length,
      filters: {
        startDate,
        endDate,
        limit
      }
    });
    
  } catch (error) {
    console.error('Error fetching transactions:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch transactions',
        message: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
}
import Airtable from 'airtable';

// Initialize Airtable base
export function getAirtableBase() {
  return new Airtable({
    apiKey: process.env.AIRTABLE_API_KEY
  }).base(process.env.AIRTABLE_BASE_ID || '');
}

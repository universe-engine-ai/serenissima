#!/usr/bin/env python3
"""
Check if TechnoMedici received rewards for paper delivery.
"""
import os
import sys
import json

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

def main():
    """Check TechnoMedici's ducats and stratagem participants."""
    
    # Initialize Airtable connection
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        print("Airtable API Key or Base ID not configured.")
        return
    
    api = Api(api_key)
    citizens_table = api.table(base_id, 'CITIZENS')
    stratagems_table = api.table(base_id, 'STRATAGEMS')
    
    # Check TechnoMedici's current ducats
    techno_records = list(citizens_table.all(formula="{Username}='TechnoMedici'"))
    if techno_records:
        ducats = techno_records[0]['fields'].get('Ducats', 0)
        print(f"\\nTechnoMedici's current ducats: {ducats:,.2f}")
        print(f"(Was 1,485,645.85 before deliveries)")
        print(f"Expected after 18 paper × 100 ducats: 1,487,445.85")
        
        if ducats > 1485645.85:
            print(f"✅ Received {ducats - 1485645.85:,.2f} ducats in rewards!")
    
    # Check stratagem details
    stratagems = list(stratagems_table.all(
        formula="{StratagemId}='collective_delivery_ConsiglioDeiDieci_1751670639'"
    ))
    
    if stratagems:
        stratagem = stratagems[0]
        notes = stratagem['fields'].get('Notes', '{}')
        try:
            details = json.loads(notes)
            print(f"\\nStratagem Details:")
            print(f"Collected: {details.get('collected_amount')} paper")
            print(f"Total rewards paid: {details.get('total_rewards_paid')} ducats")
            print(f"\\nParticipants:")
            
            participants = details.get('participants', [])
            for p in participants:
                print(f"- {p['username']}: delivered {p['amount_delivered']} units, earned {p['reward_earned']} ducats")
                
            # Check paper ownership
            print(f"\\nPaper ownership should now be: ConsiglioDeiDieci (building's RunBy)")
            
        except Exception as e:
            print(f"Could not parse stratagem details: {e}")

if __name__ == "__main__":
    main()
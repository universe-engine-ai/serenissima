#!/usr/bin/env python3
"""
Create welfare-related decrees in Airtable based on citizen_welfare_analysis.md
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from pyairtable import Api

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def create_decree(decrees_table, decree_data):
    """Create a single decree and return success status"""
    try:
        result = decrees_table.create(decree_data)
        print(f"✅ Created: {result['fields']['Title']}")
        return True
    except Exception as e:
        print(f"❌ Failed to create {decree_data['Title']}: {e}")
        return False

def create_welfare_decrees():
    """Create multiple welfare-related decrees"""
    
    # Initialize Airtable API
    api = Api(os.getenv('AIRTABLE_API_KEY'))
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not api or not base_id:
        print("❌ Error: Missing Airtable credentials")
        return False
    
    # Access the DECREES table
    decrees_table = api.table(base_id, 'DECREES')
    
    # Current timestamp for decree IDs
    timestamp = datetime.now().strftime("%Y%m%d")
    
    # Define all welfare decrees
    decrees = [
        {
            'DecreeId': f'decree_emergency_food_{timestamp}',
            'Type': 'emergency_relief',
            'Title': 'Emergency Food Distribution Act',
            'Description': """By order of the Consiglio dei Dieci, an emergency food distribution system is hereby established to prevent mass starvation in our Republic.

This decree mandates:
1. When more than 10% of citizens have not eaten for over 12 hours, emergency food rations shall be distributed
2. The Treasury shall fund the creation of bread and fish at designated distribution centers
3. Each hungry citizen shall receive one day's ration of food
4. Distribution shall occur daily until hunger levels fall below 5%

Distribution centers shall be established at:
- Public wells and cisterns (for easy citizen access)
- Treasury buildings
- Churches and charitable institutions

This measure is temporary and shall be reviewed when economic conditions improve.""",
            'Rationale': """Our analysis reveals that 112 citizens are currently starving due to complete breakdown of the food supply chain. With 37 flour shortages and 34 bread shortages, bakeries cannot produce. This emergency measure ensures basic survival while we repair the underlying economic systems.""",
            'Status': 'active',
            'Category': 'economic',
            'Proposer': 'ConsiglioDeiDieci',
            'FlavorText': '"Let no Venetian perish from hunger while the Republic stands."',
            'HistoricalInspiration': 'Based on Venice\'s historical grain reserves (the Fontego dei Tedeschi) and charitable food distributions during times of crisis.',
            'Notes': 'Implements emergency_food_distribution.py to inject food resources when hunger exceeds 10% of population.',
            'CreatedAt': datetime.now().isoformat(),
            'EnactedAt': datetime.now().isoformat()
        },
        
        {
            'DecreeId': f'decree_primary_production_{timestamp}',
            'Type': 'economic_reform',
            'Title': 'Primary Resource Generation Edict',
            'Description': """The Consiglio dei Dieci hereby establishes designated primary production zones to ensure steady supply of essential resources.

This decree establishes:
1. Farms shall generate daily supplies of vegetables, grain, and grapes
2. Fisheries shall produce fresh fish catches daily
3. Forest areas shall yield timber for construction
4. Mines shall extract iron ore and stone

Each primary production site shall:
- Generate resources automatically at dawn
- Be exempt from certain taxes to encourage production
- Receive priority protection from the state
- Have dedicated transport routes for distribution

Citizens operating these facilities shall be considered essential workers and receive production bonuses.""",
            'Rationale': """With 182 critical resource shortages paralyzing the economy, we must establish reliable primary resource generation. The current closed-loop economy has no mechanism to inject new resources when supplies deplete, leading to cascading failures throughout all economic sectors.""",
            'Status': 'active',
            'Category': 'economic',
            'Proposer': 'ConsiglioDeiDieci',
            'FlavorText': '"From the earth and sea comes Venice\'s strength."',
            'HistoricalInspiration': 'Modeled after Venice\'s historical terra firma territories that supplied raw materials to the city.',
            'Notes': 'Implements resource_generation.py for daily primary resource creation at designated buildings.',
            'CreatedAt': datetime.now().isoformat(),
            'EnactedAt': datetime.now().isoformat()
        },
        
        {
            'DecreeId': f'decree_porter_welfare_{timestamp}',
            'Type': 'social_welfare',
            'Title': 'Porter Welfare Employment Act',
            'Description': """The Consiglio dei Dieci establishes an emergency employment program through the Porter\'s Guild.

This decree mandates:
1. Citizens who have not eaten for over 8 hours may apply for temporary porter work
2. The Porter\'s Guild shall provide immediate work assignments carrying goods
3. Workers receive immediate payment sufficient to purchase food
4. After completing deliveries, workers receive a basic food ration

Eligibility:
- Any citizen experiencing hunger (AteAt > 8 hours)
- Must be physically able to carry goods
- Priority given to unemployed citizens
- No social class restrictions

This provides dignity through work rather than charity alone.""",
            'Rationale': """With mass starvation affecting 112 citizens and delivery systems paralyzed with 145 waiting deliveries, this program addresses both crises simultaneously. Hungry citizens gain immediate income and food while helping clear the delivery backlog.""",
            'Status': 'active',
            'Category': 'social',
            'Proposer': 'ConsiglioDeiDieci',
            'FlavorText': '"Through honest labor comes both bread and honor."',
            'HistoricalInspiration': 'Based on Venice\'s historical porter guilds (bastazi) and public works employment during economic downturns.',
            'Notes': 'Already implemented via welfare_porter_handler.py - provides work-for-food program.',
            'CreatedAt': datetime.now().isoformat(),
            'EnactedAt': datetime.now().isoformat()
        },
        
        {
            'DecreeId': f'decree_housing_assistance_{timestamp}',
            'Type': 'social_welfare',
            'Title': 'Transitional Housing Assistance Decree',
            'Description': """The Consiglio dei Dieci establishes a transitional housing program for employed but homeless citizens.

This decree provides:
1. Employed citizens without homes shall receive housing subsidies
2. Rent assistance limited to 30% of the citizen\'s daily wage
3. Priority given to citizens with steady employment
4. Subsidies reviewed monthly based on income changes

Eligible citizens must:
- Be actively employed with regular wages
- Have been homeless for at least 3 days
- Maintain their employment to keep assistance
- Accept assigned housing matching their social class

The Treasury shall fund the difference between market rent and the citizen\'s contribution.""",
            'Rationale': """13+ citizens are homeless despite having employment, causing cascading productivity losses across 8 businesses. This program ensures workers can maintain stable housing while rebuilding their financial stability.""",
            'Status': 'active',
            'Category': 'social',
            'Proposer': 'ConsiglioDeiDieci',
            'FlavorText': '"A citizen with shelter is a productive citizen."',
            'HistoricalInspiration': 'Inspired by Venice\'s Scuole Piccole that provided housing assistance to guild members in need.',
            'Notes': 'Implements housing_assistance.py for subsidized leases based on 30% of income.',
            'CreatedAt': datetime.now().isoformat(),
            'EnactedAt': datetime.now().isoformat()
        },
        
        {
            'DecreeId': f'decree_galley_inspection_{timestamp}',
            'Type': 'maritime_regulation',
            'Title': 'Mandatory Galley Cargo Transfer Protocol',
            'Description': """The Consiglio dei Dieci mandates immediate cargo transfer upon merchant galley arrival.

This decree requires:
1. All arriving galleys must transfer cargo within 2 hours of docking
2. Port authorities shall inspect and enforce cargo unloading
3. Stuck cargo shall be confiscated and distributed after 6 hours
4. Galley captains failing to unload face heavy fines

Port inspectors shall:
- Board each arriving galley immediately
- Verify cargo manifests match actual goods
- Oversee transfer to destination buildings
- Report any irregularities to authorities

Penalties for non-compliance include loss of trading privileges.""",
            'Rationale': """62 merchant galleys sit in port with undelivered cargo while citizens desperately need these resources. Import system failures trap goods on vessels instead of reaching markets, contributing to 182 resource shortages.""",
            'Status': 'active',
            'Category': 'economic',
            'Proposer': 'ConsiglioDeiDieci',
            'FlavorText': '"Swift ships make for swift commerce."',
            'HistoricalInspiration': 'Based on Venice\'s historical Customs House (Dogana da Mar) regulations for merchant vessels.',
            'Notes': 'Fixes galley_arrival.py handler to ensure resources transfer from ships to buildings.',
            'CreatedAt': datetime.now().isoformat(),
            'EnactedAt': datetime.now().isoformat()
        }
    ]
    
    # Create each decree
    success_count = 0
    for decree in decrees:
        if create_decree(decrees_table, decree):
            success_count += 1
    
    return success_count, len(decrees)

def main():
    print("=== Creating Welfare Decrees ===")
    print("Based on citizen_welfare_analysis.md findings\n")
    
    success, total = create_welfare_decrees()
    
    print(f"\n{'='*50}")
    print(f"Created {success} out of {total} decrees successfully")
    
    if success == total:
        print("\n✅ All welfare decrees have been enacted!")
        print("   The Consiglio dei Dieci's emergency measures are now in effect.")
    else:
        print(f"\n⚠️  Some decrees failed to create. Please check the errors above.")

if __name__ == "__main__":
    main()
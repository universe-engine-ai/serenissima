#!/usr/bin/env python3
"""
Create a decree in Airtable for the new homeless notification rule
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

def create_homeless_notification_decree():
    """Create a decree for the homeless notification system"""
    
    # Initialize Airtable API
    api = Api(os.getenv('AIRTABLE_API_KEY'))
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    if not api or not base_id:
        print("❌ Error: Missing Airtable credentials")
        return False
    
    # Access the DECREES table
    decrees_table = api.table(base_id, 'DECREES')
    
    # Create the decree
    decree_data = {
        'DecreeId': f'decree_homeless_notification_{datetime.now().strftime("%Y%m%d")}',
        'Type': 'social_welfare',
        'Title': 'Decree on the Notification of Homeless Citizens to Wealthy Patrons',
        'Description': """By order of the Consiglio dei Dieci, a new system is hereby established to address the crisis of homeless citizens in our Most Serene Republic.

This decree mandates that wealthy citizens (those possessing fortunes exceeding 2,000,000 ducats) shall be regularly notified of the plight of homeless citizens and encouraged to construct appropriate housing.

The notification system shall operate as follows:
- Daily, the Consiglio dei Dieci shall identify all citizens lacking proper housing
- A message shall be sent to one wealthy citizen per day, rotating through available patrons
- The message shall detail the homeless citizens by social class and suggest appropriate building types:
  • For Nobili: canal_house (luxury waterfront homes)
  • For Cittadini, Artisti, Scientisti, or Clero: merchant_s_house (comfortable middle-class homes)
  • For Popolani, Artisti, Scientisti, or Clero: artisan_s_house (modest but decent homes)
  • For Facchini: fisherman_s_cottage (basic housing)

This system aims to leverage the civic responsibility of our wealthiest citizens to address the housing crisis through voluntary construction projects.""",
        'Rationale': """The increasing number of homeless citizens poses a threat to public order, health, and the reputation of our Republic. 

By engaging wealthy citizens in solving this crisis, we:
1. Mobilize private resources for public good
2. Encourage civic responsibility among the wealthy
3. Provide systematic solutions to homelessness
4. Maintain social harmony across all classes
5. Demonstrate the Republic's care for all its citizens

The voluntary nature of this system respects private property rights while appealing to the nobility and civic virtue of our wealthy citizens.""",
        'Status': 'active',
        'Category': 'social',
        'Proposer': 'ConsiglioDeiDieci',
        'FlavorText': '"For the glory of Venice lies not in its palaces alone, but in the welfare of all who call her home."',
        'HistoricalInspiration': 'Inspired by Renaissance Venice\'s various charitable institutions (Scuole Grandi) and the tradition of wealthy merchants funding public works and housing for the poor.',
        'Notes': 'Implemented via backend/arsenale/daily_homeless_notifier.py. Runs daily and tracks notification history to ensure fair rotation among wealthy citizens.',
        'CreatedAt': datetime.now().isoformat(),
        'EnactedAt': datetime.now().isoformat()
    }
    
    try:
        # Create the decree
        result = decrees_table.create(decree_data)
        print(f"✅ Successfully created decree: {result['fields']['Title']}")
        print(f"   Decree ID: {result['fields']['DecreeId']}")
        print(f"   Status: {result['fields']['Status']}")
        return True
    except Exception as e:
        print(f"❌ Error creating decree: {e}")
        return False

def main():
    print("=== Creating Homeless Notification Decree ===")
    success = create_homeless_notification_decree()
    if success:
        print("\n✅ Decree has been successfully enacted!")
        print("   The Consiglio dei Dieci's new social welfare policy is now in effect.")
    else:
        print("\n❌ Failed to create decree.")

if __name__ == "__main__":
    main()
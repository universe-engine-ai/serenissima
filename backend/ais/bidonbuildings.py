import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from pyairtable import Api, Table

# Add the parent directory to the path to import citizen_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.citizen_utils import find_citizen_by_identifier

def initialize_airtable():
    """Initialize connection to Airtable."""
    load_dotenv()
    
    airtable_api_key = os.getenv("AIRTABLE_API_KEY")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
    
    if not airtable_api_key or not airtable_base_id:
        print("Error: Airtable credentials not found in environment variables")
        sys.exit(1)
    
    api = Api(airtable_api_key)
    
    AIRTABLE_CONTRACTS_TABLE_NAME = os.getenv("AIRTABLE_CONTRACTS_TABLE", "CONTRACTS")
    tables = {
        "citizens": Table(airtable_api_key, airtable_base_id, "CITIZENS"),
        "buildings": Table(airtable_api_key, airtable_base_id, "BUILDINGS"),
        "contracts": Table(airtable_api_key, airtable_base_id, AIRTABLE_CONTRACTS_TABLE_NAME),
        "notifications": Table(airtable_api_key, airtable_base_id, "NOTIFICATIONS")
    }
    
    return tables

def get_ai_citizens(tables) -> List[Dict]:
    """Get all citizens that are marked as AI, are in Venice, and have appropriate social class."""
    try:
        # Query citizens with IsAI=true, InVenice=true, and SocialClass is either Nobili or Cittadini
        formula = "AND({IsAI}=1, {InVenice}=1, OR({SocialClass}='Nobili', {SocialClass}='Cittadini'))"
        ai_citizens = tables["citizens"].all(formula=formula)
        print(f"Found {len(ai_citizens)} AI citizens in Venice with Nobili or Cittadini social class")
        return ai_citizens
    except Exception as e:
        print(f"Error getting AI citizens: {str(e)}")
        return []

def get_profitable_buildings(tables) -> List[Dict]:
    """Get buildings that are profitable (have RentPrice > LeasePrice)."""
    try:
        # Query buildings where RentPrice > LeasePrice and IsConstructed=true
        formula = "AND({RentPrice}>{LeasePrice}, {IsConstructed}=1)"
        buildings = tables["buildings"].all(formula=formula)
        print(f"Found {len(buildings)} profitable buildings")
        return buildings
    except Exception as e:
        print(f"Error getting profitable buildings: {str(e)}")
        return []

def get_existing_bids(tables, ai_username: str) -> Dict[str, Dict]:
    """Get existing bids (building_bid contracts) from an AI citizen, indexed by building_id."""
    try:
        # Query contracts where the buyer is the AI citizen, type is 'building_bid', and status is 'active'
        formula = f"AND({{Buyer}}='{ai_username}', {{Type}}='building_bid', {{Status}}='active')"
        contracts = tables["contracts"].all(formula=formula)
        
        # Index by Asset (building_id)
        bids_by_building = {}
        for contract in contracts:
            asset = contract["fields"].get("Asset")
            if asset:
                bids_by_building[asset] = contract
        
        print(f"Found {len(bids_by_building)} existing building_bid contracts for AI citizen {ai_username}")
        return bids_by_building
    except Exception as e:
        print(f"Error getting existing building bids: {str(e)}")
        return {}

def create_or_update_bid(tables, ai_citizen: Dict, building: Dict, existing_bid: Optional[Dict] = None) -> bool:
    """Create a new bid or update an existing one."""
    try:
        building_id = building["fields"].get("BuildingId")
        rent_price = building["fields"].get("RentPrice", 0)
        lease_price = building["fields"].get("LeasePrice", 0)
        
        if not building_id or rent_price <= 0:
            print(f"Building missing required fields or not profitable: {building}")
            return False
        
        # Calculate profit margin
        profit_margin = rent_price - lease_price
        
        # Calculate bid amount (25x the annual profit)
        annual_profit = profit_margin * 365
        bid_amount = annual_profit * 25
        
        # Get AI citizen's ducats balance
        ai_username = ai_citizen["fields"].get("Username")
        ai_ducats = ai_citizen["fields"].get("Ducats", 0)
        
        # Check if AI has enough ducats (2x the bid amount)
        if ai_ducats < bid_amount * 2:
            print(f"AI {ai_username} doesn't have enough ducats for bid on {building_id}. Needs {bid_amount * 2}, has {ai_ducats}")
            return False
        
        # Get current building owner
        building_owner = building["fields"].get("Owner")
        
        if existing_bid:
            # Increase existing bid by 15% if AI has enough ducats
            current_bid = existing_bid["fields"].get("PricePerResource", 0)
            new_bid = current_bid * 1.15
            
            if ai_ducats < new_bid * 2:
                print(f"AI {ai_username} doesn't have enough ducats to increase bid on {building_id}. Needs {new_bid * 2}, has {ai_ducats}")
                return False
            
            # Update the contract with the new bid price
            now = datetime.now().isoformat()
            tables["contracts"].update(existing_bid["id"], {
                "PricePerResource": new_bid,
                "UpdatedAt": now
            })
            
            print(f"Updated building_bid contract for {building_id} from {current_bid} to {new_bid} by AI {ai_username}")
            
            # Send notification to building owner about the updated bid
            if building_owner:
                try:
                    notification_content = f"AI {ai_username} has increased their bid on your building {building_id} from {current_bid} to {new_bid} ducats."
                    tables["notifications"].create({
                        "Citizen": building_owner,
                        "Type": "bid_update",
                        "Content": notification_content,
                        "CreatedAt": now,
                        "ReadAt": None,
                        "Details": json.dumps({
                            "building_id": building_id,
                            "bidder": ai_username,
                            "previous_bid": current_bid,
                            "new_bid": new_bid,
                            "timestamp": now
                        })
                    })
                    print(f"Sent bid update notification to building owner {building_owner}")
                except Exception as e:
                    print(f"Error sending notification to building owner: {str(e)}")
            
            return True
        else:
            # Create a new bid
            now = datetime.now().isoformat()
            contract_id = f"building_bid_{building_id}_{ai_username}_{int(datetime.now().timestamp())}"
            
            # Create a new building_bid contract
            contract_data = {
                "ContractId": contract_id,
                "Type": "building_bid",
                "Asset": building_id,
                "AssetType": "building",
                "Buyer": ai_username, # AI is offering to buy
                "Seller": building_owner, # Current building owner
                "PricePerResource": bid_amount,
                "TargetAmount": 1, # For the building itself
                "Status": "active",
                "CreatedAt": now,
                "UpdatedAt": now,
                "Notes": json.dumps({
                    "bidder_ai": ai_username, 
                    "building_owner_at_bid_time": building_owner,
                    "annual_profit_estimate": annual_profit,
                    "bid_multiplier": 25
                })
            }
            
            tables["contracts"].create(contract_data)
            print(f"Created new building_bid contract for {building_id} at {bid_amount} by AI {ai_username} to {building_owner}")
            
            # Send notification to building owner about the new bid
            if building_owner:
                try:
                    notification_content = f"AI {ai_username} has placed a bid of {bid_amount} ducats on your building {building_id}."
                    tables["notifications"].create({
                        "Citizen": building_owner,
                        "Type": "new_bid",
                        "Content": notification_content,
                        "CreatedAt": now,
                        "ReadAt": None,
                        "Details": json.dumps({
                            "building_id": building_id,
                            "bidder": ai_username,
                            "bid_amount": bid_amount,
                            "timestamp": now
                        })
                    })
                    print(f"Sent new bid notification to building owner {building_owner}")
                except Exception as e:
                    print(f"Error sending notification to building owner: {str(e)}")
            
            return True
    except Exception as e:
        print(f"Error creating/updating building bid: {str(e)}")
        return False

def create_admin_notification(tables, ai_bid_counts: Dict[str, int]) -> None:
    """Create a notification for admins with the bidding summary."""
    try:
        now = datetime.now().isoformat()
        
        # Create a summary message
        message = "AI Building Bidding Summary:\n\n"
        
        for ai_name, bid_count in ai_bid_counts.items():
            message += f"- {ai_name}: {bid_count} bids\n"
        
        # Create the notification
        notification = {
            "Citizen": "ConsiglioDeiDieci",
            "Type": "ai_building_bidding",
            "Content": message,
            "CreatedAt": now,
            "ReadAt": None,
            "Details": json.dumps({
                "ai_bid_counts": ai_bid_counts,
                "timestamp": now
            })
        }
        
        tables["notifications"].create(notification)
        print("Created admin notification with building bidding summary")
    except Exception as e:
        print(f"Error creating admin notification: {str(e)}")

def process_ai_building_bidding(dry_run: bool = False):
    """Main function to process AI bidding on buildings."""
    print(f"Starting AI building bidding process (dry_run={dry_run})")
    
    # Initialize Airtable connection
    tables = initialize_airtable()
    
    # Get AI citizens
    ai_citizens = get_ai_citizens(tables)
    if not ai_citizens:
        print("No AI citizens found, exiting")
        return
    
    # Filter AI citizens to only those with sufficient ducats for bidding (minimum 1,000,000)
    filtered_ai_citizens = []
    for ai_citizen in ai_citizens:
        ai_username = ai_citizen["fields"].get("Username")
        ducats = ai_citizen["fields"].get("Ducats", 0)
        
        if ducats >= 1000000:
            filtered_ai_citizens.append(ai_citizen)
            print(f"AI citizen {ai_username} has {ducats} ducats, including in processing")
        else:
            print(f"AI citizen {ai_username} has insufficient ducats ({ducats}) for bidding, skipping")
    
    # Replace the original list with the filtered list
    ai_citizens = filtered_ai_citizens
    print(f"Filtered down to {len(ai_citizens)} AI citizens with sufficient ducats for bidding")
    
    if not ai_citizens:
        print("No AI citizens with sufficient ducats for bidding, exiting")
        return
    
    # Get profitable buildings
    buildings = get_profitable_buildings(tables)
    if not buildings:
        print("No profitable buildings found, exiting")
        return
    
    # Track bid counts for each AI
    ai_bid_counts = {}
    total_ai_for_bidding = len(ai_citizens)
    print(f"Processing {total_ai_for_bidding} AI citizens for building bidding.")
    
    # Process each AI citizen
    for i, ai_citizen in enumerate(ai_citizens):
        ai_username = ai_citizen["fields"].get("Username")
        if not ai_username:
            continue
        
        ai_bid_counts[ai_username] = 0
        
        # Get existing bids for this AI
        existing_bids = get_existing_bids(tables, ai_username)
        
        # Process each building
        for building in buildings:
            building_id = building["fields"].get("BuildingId")
            if not building_id:
                continue
            
            # Skip buildings owned by this AI
            building_owner = building["fields"].get("Owner")
            if building_owner == ai_username:
                continue
            
            # Check if AI already has a bid on this building
            existing_bid = existing_bids.get(building_id)
            
            # Create or update bid
            if not dry_run:
                success = create_or_update_bid(tables, ai_citizen, building, existing_bid)
                if success:
                    ai_bid_counts[ai_username] += 1
            else:
                # In dry run mode, just log what would happen
                if existing_bid:
                    print(f"[DRY RUN] Would update bid for {building_id} by AI {ai_username}")
                else:
                    print(f"[DRY RUN] Would create new bid for {building_id} by AI {ai_username}")
                ai_bid_counts[ai_username] += 1
    
    # Create admin notification with summary
    if not dry_run and sum(ai_bid_counts.values()) > 0:
        create_admin_notification(tables, ai_bid_counts)
    else:
        print(f"[DRY RUN] Would create admin notification with bid counts: {ai_bid_counts}")
    
    print("AI building bidding process completed")

if __name__ == "__main__":
    # Check if this is a dry run
    dry_run = "--dry-run" in sys.argv
    
    # Run the process
    process_ai_building_bidding(dry_run)

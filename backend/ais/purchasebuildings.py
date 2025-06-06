import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
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
    AIRTABLE_TRANSACTIONS_TABLE_NAME = os.getenv("AIRTABLE_TRANSACTIONS_TABLE", "TRANSACTIONS") # For logging
    tables = {
        "citizens": Table(airtable_api_key, airtable_base_id, "CITIZENS"),
        "contracts": Table(airtable_api_key, airtable_base_id, AIRTABLE_CONTRACTS_TABLE_NAME),
        "transactions_log_table": Table(airtable_api_key, airtable_base_id, AIRTABLE_TRANSACTIONS_TABLE_NAME),
        "buildings": Table(airtable_api_key, airtable_base_id, "BUILDINGS"),
        "notifications": Table(airtable_api_key, airtable_base_id, "NOTIFICATIONS")
    }
    
    return tables

def get_ai_citizens(tables) -> List[Dict]:
    """Get all citizens that are marked as AI, excluding ConsiglioDeiDieci, ordered by Ducats DESC."""
    try:
        # Query citizens with IsAI=true and Username is not ConsiglioDeiDieci
        formula = "AND({IsAI}=1, {Username}!='ConsiglioDeiDieci')"
        ai_citizens = tables["citizens"].all(formula=formula)
        
        # Sort by Ducats in descending order
        ai_citizens.sort(key=lambda x: x["fields"].get("Ducats", 0), reverse=True)
        
        print(f"Found {len(ai_citizens)} AI citizens (excluding ConsiglioDeiDieci)")
        return ai_citizens
    except Exception as e:
        print(f"Error getting AI citizens: {str(e)}")
        return []

def get_available_building_bids(tables) -> List[Dict]:
    """Get all active building_bid contracts."""
    try:
        # Query contracts with Type='building_bid' and Status='active'
        formula = "AND({Type}='building_bid', {Status}='active')"
        contracts = tables["contracts"].all(formula=formula)
        
        # Sort by PricePerResource in descending order (highest bids first)
        contracts.sort(key=lambda x: x["fields"].get("PricePerResource", 0), reverse=True)
        
        print(f"Found {len(contracts)} active building_bid contracts")
        return contracts
    except Exception as e:
        print(f"Error getting available building bids: {str(e)}")
        return []

def execute_building_purchase_contract(tables, contract_id: str, seller_username: str) -> Optional[Dict]:
    """Update a building_bid contract, marking it as executed."""
    try:
        now = datetime.now().isoformat()
        
        # Update the contract
        updated_contract = tables["contracts"].update(contract_id, {
            "Seller": seller_username,
            "Status": "executed",
            "ExecutedAt": now,
            "UpdatedAt": now
        })
        
        print(f"Executed building_bid contract {contract_id} with seller {seller_username}")
        return updated_contract
    except Exception as e:
        print(f"Error executing building_bid contract {contract_id}: {str(e)}")
        return None

def update_building_with_owner(tables, building_id: str, new_owner: str) -> bool:
    """Update a building with a new owner."""
    try:
        # Find the building record
        formula = f"{{BuildingId}}='{building_id}'"
        buildings = tables["buildings"].all(formula=formula)
        
        if not buildings:
            print(f"Building {building_id} not found")
            return False
        
        # Update the building with the new owner
        tables["buildings"].update(buildings[0]["id"], {
            "Owner": new_owner
        })
        
        print(f"Updated building {building_id} with owner {new_owner}")
        return True
    except Exception as e:
        print(f"Error updating building {building_id}: {str(e)}")
        return False

def create_notification(tables, citizen: str, building_id: str, price: float) -> bool:
    """Create a notification for the citizen about the building purchase."""
    try:
        now = datetime.now().isoformat()
        
        # Create the notification
        notification = {
            "Citizen": citizen,
            "Type": "building_purchase",
            "Content": f"You have successfully purchased building {building_id} for {price} ducats.",
            "CreatedAt": now,
            "ReadAt": None,
            "Details": json.dumps({
                "building_id": building_id,
                "price": price,
                "timestamp": now
            })
        }
        
        tables["notifications"].create(notification)
        print(f"Created notification for {citizen} about building purchase")
        return True
    except Exception as e:
        print(f"Error creating notification: {str(e)}")
        return False

def create_admin_notification(tables, purchases: List[Dict]) -> None:
    """Create a notification for admins with the AI building purchase summary."""
    try:
        if not purchases:
            return
            
        now = datetime.now().isoformat()
        
        # Create a summary message
        message = "AI Building Purchase Summary:\n\n"
        
        for purchase in purchases:
            message += f"- {purchase['buyer']}: Purchased building {purchase['building_id']} from {purchase['seller']} for {purchase['price']} ducats\n"
        
        # Create the notification
        notification = {
            "Citizen": "ConsiglioDeiDieci",
            "Type": "ai_building_purchases",
            "Content": message,
            "CreatedAt": now,
            "ReadAt": None,
            "Details": json.dumps({
                "purchases": purchases,
                "timestamp": now
            })
        }
        
        tables["notifications"].create(notification)
        print("Created admin notification with AI building purchase summary")
    except Exception as e:
        print(f"Error creating admin notification: {str(e)}")

def process_ai_building_purchases(dry_run: bool = False):
    """Main function to process AI building purchases from bids."""
    print(f"Starting AI building purchase process (dry_run={dry_run})")
    
    # Initialize Airtable connection
    tables = initialize_airtable()
    
    # Get AI citizens sorted by Ducats DESC
    ai_citizens = get_ai_citizens(tables)
    if not ai_citizens:
        print("No AI citizens found, exiting")
        return
    
    # Get available building bids
    available_bids = get_available_building_bids(tables)
    if not available_bids:
        print("No available building bids found, exiting")
        return
    
    # Track purchases for admin notification
    purchases = []
    
    # Process each building bid
    for bid in available_bids:
        contract_id = bid["id"]
        building_id = bid["fields"].get("Asset")
        buyer_username = bid["fields"].get("Buyer")
        bid_amount = bid["fields"].get("PricePerResource", 0)
        
        if not building_id or not buyer_username or bid_amount <= 0:
            print(f"Skipping invalid bid: {bid}")
            continue
        
        # Find the building to get current owner
        formula = f"{{BuildingId}}='{building_id}'"
        buildings = tables["buildings"].all(formula=formula)
        
        if not buildings:
            print(f"Building {building_id} not found, skipping bid")
            continue
        
        building = buildings[0]
        current_owner = building["fields"].get("Owner")
        
        if not current_owner:
            print(f"Building {building_id} has no owner, skipping bid")
            continue
        
        # Check if the current owner is an AI
        owner_record = find_citizen_by_identifier(tables, current_owner)
        if not owner_record:
            print(f"Owner {current_owner} not found, skipping bid")
            continue
        
        is_owner_ai = owner_record["fields"].get("IsAI", 0) == 1
        
        # Only process if the owner is an AI (for now, to avoid affecting human players without consent)
        if not is_owner_ai:
            print(f"Owner {current_owner} is not an AI, skipping bid")
            continue
        
        # Check if the bid is at least 20x the annual profit (if RentPrice and LeasePrice are available)
        rent_price = building["fields"].get("RentPrice", 0)
        lease_price = building["fields"].get("LeasePrice", 0)
        
        if rent_price > 0 and lease_price > 0:
            annual_profit = (rent_price - lease_price) * 365
            min_acceptable_bid = annual_profit * 20
            
            if bid_amount < min_acceptable_bid:
                print(f"Bid amount {bid_amount} is less than minimum acceptable {min_acceptable_bid} for building {building_id}, skipping")
                continue
        
        print(f"Processing bid for building {building_id}: {buyer_username} offering {bid_amount} to {current_owner}")
        
        if not dry_run:
            # Execute the building_bid contract
            executed_contract = execute_building_purchase_contract(tables, contract_id, current_owner)
            
            if executed_contract:
                # Update the building with the new owner
                building_update_success = update_building_with_owner(tables, building_id, buyer_username)
                
                if building_update_success:
                    # Get buyer and seller records
                    buyer_record = find_citizen_by_identifier(tables, buyer_username)
                    
                    if not buyer_record:
                        print(f"Buyer {buyer_username} not found, cannot complete transaction")
                        continue
                    
                    # Update the buyer's ducats
                    buyer_ducats = buyer_record["fields"].get("Ducats", 0)
                    new_buyer_ducats = buyer_ducats - bid_amount
                    tables["citizens"].update(buyer_record["id"], {"Ducats": new_buyer_ducats})
                    print(f"Updated buyer {buyer_username}'s ducats from {buyer_ducats} to {new_buyer_ducats}")
                    
                    # Update the seller's ducats
                    seller_ducats = owner_record["fields"].get("Ducats", 0)
                    new_seller_ducats = seller_ducats + bid_amount
                    tables["citizens"].update(owner_record["id"], {"Ducats": new_seller_ducats})
                    print(f"Updated seller {current_owner}'s ducats from {seller_ducats} to {new_seller_ducats}")
                    
                    # Create a transaction log for the ducat transfer
                    try:
                        tables["transactions_log_table"].create({
                            "Type": "building_sale",
                            "Asset": building_id,
                            "AssetType": "building",
                            "Seller": current_owner,
                            "Buyer": buyer_username,
                            "Price": bid_amount,
                            "CreatedAt": datetime.now().isoformat(),
                            "ExecutedAt": datetime.now().isoformat(),
                            "Notes": json.dumps({
                                "contract_id": contract_id,
                                "building_id": building_id,
                                "purchase_by_ai": True
                            })
                        })
                        print(f"Created transaction log for building purchase: {buyer_username} paid {bid_amount} to {current_owner} for {building_id}")
                    except Exception as e:
                        print(f"Error creating transaction log for building purchase: {str(e)}")
                    
                    # Create notification for the buyer
                    create_notification(tables, buyer_username, building_id, bid_amount)
                    
                    # Create notification for the seller
                    try:
                        notification_content = f"Your building {building_id} has been sold to {buyer_username} for {bid_amount} ducats."
                        tables["notifications"].create({
                            "Citizen": current_owner,
                            "Type": "building_sold",
                            "Content": notification_content,
                            "CreatedAt": datetime.now().isoformat(),
                            "ReadAt": None,
                            "Details": json.dumps({
                                "building_id": building_id,
                                "buyer": buyer_username,
                                "price": bid_amount,
                                "timestamp": datetime.now().isoformat()
                            })
                        })
                        print(f"Sent building sold notification to {current_owner}")
                    except Exception as e:
                        print(f"Error sending building sold notification: {str(e)}")
                    
                    # Add to purchases list for admin notification
                    purchases.append({
                        "buyer": buyer_username,
                        "seller": current_owner,
                        "building_id": building_id,
                        "price": bid_amount
                    })
        else:
            print(f"[DRY RUN] Would purchase building {building_id} for {bid_amount} ducats from {current_owner} to {buyer_username}")
    
    # Create admin notification with summary
    if not dry_run and purchases:
        create_admin_notification(tables, purchases)
    else:
        print(f"[DRY RUN] Would create admin notification with purchases: {purchases}")
    
    print("AI building purchase process completed")

if __name__ == "__main__":
    # Check if this is a dry run
    dry_run = "--dry-run" in sys.argv
    
    # Run the process
    process_ai_building_purchases(dry_run)

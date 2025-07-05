#!/usr/bin/env python3
"""
EMERGENCY DEPLOYMENT: Galley Grain Bridge
RUN THIS NOW TO SAVE 112 STARVING CITIZENS!

This script creates public_sell contracts for ALL grain in ALL galleys
making it available to ALL mills immediately.

Usage: python deploy_grain_bridge_NOW.py
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emergency.galley_grain_to_mill_bridge import GalleyGrainBridge

# Enhanced logging for emergency
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EMERGENCY_BRIDGE')

def emergency_deploy():
    """Emergency deployment with enhanced contract creation"""
    
    logger.critical("🚨 EMERGENCY GRAIN BRIDGE DEPLOYMENT 🚨")
    logger.critical("112 CITIZENS ARE STARVING - CREATING CONTRACTS NOW!")
    
    # Get credentials
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('SERENISSIMA_AIRTABLE_BASE_ID') or os.getenv('AIRTABLE_BASE_ID')
    
    if not api_key:
        logger.error("❌ AIRTABLE_API_KEY not set!")
        logger.error("Set it with: export AIRTABLE_API_KEY='your_key_here'")
        return 1
        
    if not base_id:
        logger.error("❌ SERENISSIMA_AIRTABLE_BASE_ID not set!")
        logger.error("Set it with: export SERENISSIMA_AIRTABLE_BASE_ID='your_base_id'")
        return 1
    
    logger.info(f"✅ Credentials loaded")
    logger.info(f"📍 Base ID: {base_id[:10]}...")
    
    # Create enhanced bridge with more aggressive parameters
    class EmergencyGalleyGrainBridge(GalleyGrainBridge):
        """Enhanced bridge for emergency deployment"""
        
        def create_bridge_contract(self, galley_info, mill_info, grain_amount):
            """Override to create more flexible contracts"""
            
            contract_id = f"EMERGENCY-{datetime.now().strftime('%H%M%S')}-{galley_info['galley_id'][:6]}-{mill_info['mill_id'][:6]}"
            
            # EMERGENCY PRICING - 20% discount to move grain fast
            base_price = 1.2
            emergency_discount = 0.8  
            price_per_unit = round(base_price * emergency_discount, 2)
            
            contract_data = {
                'ContractId': contract_id,
                'Type': 'public_sell',
                'Status': 'active',
                'Seller': galley_info['owner'],
                'SellerBuilding': galley_info['galley_id'],
                'BuyerBuilding': mill_info['mill_id'],  # Specific mill target
                'ResourceType': 'grain',
                'TargetAmount': grain_amount,
                'CurrentAmount': 0,
                'PricePerResource': price_per_unit,
                'CreatedAt': datetime.now().isoformat() + 'Z',
                'StartAt': datetime.now().isoformat() + 'Z',
                'EndAt': datetime.now().isoformat() + 'Z',  # Will be updated properly
                'Notes': f"🚨 EMERGENCY STARVATION PREVENTION: Bridge-Shepherd connecting galley grain to mill. 112 citizens depend on this!"
            }
            
            # Proper date handling
            from datetime import timedelta
            import pytz
            now_utc = datetime.now(pytz.utc)
            contract_data['CreatedAt'] = now_utc.isoformat()
            contract_data['StartAt'] = now_utc.isoformat()
            contract_data['EndAt'] = (now_utc + timedelta(hours=48)).isoformat()  # 48 hour emergency window
            
            try:
                result = self.contracts_table.create(contract_data)
                logger.critical(f"🌉 BRIDGE CREATED: {grain_amount} grain @ {price_per_unit}/unit from {galley_info['galley_id']} → {mill_info['mill_id']}")
                return contract_id
            except Exception as e:
                logger.error(f"❌ Contract creation failed: {e}")
                # Try again with minimal data
                try:
                    minimal_contract = {
                        'ContractId': contract_id,
                        'Type': 'public_sell',
                        'Status': 'active',
                        'Seller': galley_info['owner'],
                        'SellerBuilding': galley_info['galley_id'],
                        'ResourceType': 'grain',
                        'TargetAmount': grain_amount,
                        'PricePerResource': price_per_unit
                    }
                    result = self.contracts_table.create(minimal_contract)
                    logger.warning(f"✅ Created minimal contract {contract_id}")
                    return contract_id
                except Exception as e2:
                    logger.error(f"❌ Even minimal contract failed: {e2}")
                    return None
        
        def execute_emergency_bridge(self):
            """Enhanced execution with better reporting"""
            logger.critical("=" * 60)
            logger.critical("EMERGENCY GRAIN BRIDGE SYSTEM ACTIVATING")
            logger.critical("=" * 60)
            
            # Find grain
            galley_grain = self.identify_grain_in_galleys()
            if not galley_grain:
                logger.error("❌ NO GRAIN FOUND IN GALLEYS!")
                logger.error("The foreign merchants have no grain!")
                return {'contracts_created': 0, 'grain_bridged': 0, 'citizens_saved': 0}
            
            total_grain = sum(g['grain_amount'] for g in galley_grain)
            logger.critical(f"📦 GRAIN LOCATED: {total_grain} units in {len(galley_grain)} galleys")
            
            # Find mills
            hungry_mills = self.identify_hungry_mills()
            if not hungry_mills:
                logger.error("❌ NO HUNGRY MILLS FOUND!")
                logger.error("All mills have sufficient grain")
                return {'contracts_created': 0, 'grain_bridged': 0, 'citizens_saved': 0}
                
            total_need = sum(m['grain_needed'] for m in hungry_mills)
            logger.critical(f"🏭 MILLS NEEDING GRAIN: {len(hungry_mills)} mills need {total_need} grain total")
            
            # Create ALL possible contracts
            contracts_created = 0
            grain_bridged = 0
            
            logger.critical("\n🌉 CREATING BRIDGE CONTRACTS...")
            logger.critical("-" * 40)
            
            for galley in galley_grain:
                if galley['grain_amount'] <= 0:
                    continue
                    
                for mill in hungry_mills:
                    if galley['grain_amount'] <= 0:
                        break
                        
                    if mill['grain_needed'] <= 0:
                        continue
                    
                    # Create contract for available grain
                    amount = min(galley['grain_amount'], mill['grain_needed'], 50)  # Max 50 per contract
                    
                    contract_id = self.create_bridge_contract(galley, mill, amount)
                    if contract_id:
                        contracts_created += 1
                        grain_bridged += amount
                        galley['grain_amount'] -= amount
                        mill['grain_needed'] -= amount
            
            logger.critical("-" * 40)
            logger.critical(f"\n✅ EMERGENCY RESPONSE COMPLETE!")
            logger.critical(f"📊 RESULTS:")
            logger.critical(f"   - Contracts Created: {contracts_created}")
            logger.critical(f"   - Grain Bridged: {grain_bridged} units")
            logger.critical(f"   - Citizens Saved: ~{grain_bridged // 10}")
            logger.critical(f"   - Meals Provided: ~{grain_bridged * 2}")
            logger.critical("=" * 60)
            
            return {
                'contracts_created': contracts_created,
                'grain_bridged': grain_bridged,
                'citizens_saved': grain_bridged // 10
            }
    
    # Deploy emergency bridge
    try:
        bridge = EmergencyGalleyGrainBridge(api_key, base_id)
        results = bridge.execute_emergency_bridge()
        
        if results['contracts_created'] > 0:
            logger.critical("\n🎉 SUCCESS! LIVES SAVED!")
            logger.critical(f"Bridge-Shepherd has connected {results['grain_bridged']} grain to hungry mills!")
            logger.critical(f"Approximately {results['citizens_saved']} citizens will eat tonight!")
            logger.critical("\nIn gaps, bridges. In translation, salvation.")
            return 0
        else:
            logger.error("\n❌ NO CONTRACTS CREATED")
            logger.error("Check that:")
            logger.error("1. Galleys have grain resources")
            logger.error("2. Mills exist and need grain")
            logger.error("3. API credentials are correct")
            return 1
            
    except Exception as e:
        logger.exception(f"❌ EMERGENCY DEPLOYMENT FAILED: {e}")
        return 1

if __name__ == "__main__":
    exit_code = emergency_deploy()
    if exit_code == 0:
        print("\n✅ Emergency grain bridge deployed successfully!")
    else:
        print("\n❌ Emergency deployment failed - citizens still starving!")
    sys.exit(exit_code)
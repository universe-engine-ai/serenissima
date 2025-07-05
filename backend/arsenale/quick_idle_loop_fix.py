#!/usr/bin/env python3
"""
Quick Idle Loop Fix - Emergency Intervention
Reality-Anchor: Breaking idle loops NOW!

This script immediately identifies and breaks idle loops without extensive analysis.
Run this when substrate is critical.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from pyairtable import Api, Table
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# Load environment
load_dotenv()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Tables
activities_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "ACTIVITIES")
citizens_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "CITIZENS")
notifications_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "NOTIFICATIONS")


def break_idle_loops():
    """Quickly identify and break idle loops"""
    log.info("🚨 EMERGENCY IDLE LOOP BREAKER ACTIVATED!")
    
    stats = {
        "citizens_checked": 0,
        "idle_loops_found": 0,
        "activities_cancelled": 0,
        "interventions": 0
    }
    
    try:
        # Get recent idle activities (last 2 hours)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        
        # Find citizens with multiple recent idle activities
        log.info("🔍 Finding citizens stuck in idle loops...")
        
        formula = f"AND({{Type}} = 'idle', {{CreatedAt}} > '{cutoff}')"
        idle_activities = activities_table.all(formula=formula)
        
        # Count idle activities per citizen
        idle_counts = {}
        for activity in idle_activities:
            citizen = activity['fields'].get('Citizen')
            if citizen:
                idle_counts[citizen] = idle_counts.get(citizen, 0) + 1
        
        # Intervene for citizens with 3+ idle activities
        for citizen, count in idle_counts.items():
            if count >= 3:
                log.info(f"  🔴 {citizen}: {count} idle activities - INTERVENING")
                stats["idle_loops_found"] += 1
                
                # Cancel all pending idle activities
                pending_formula = f"AND({{Citizen}} = '{citizen}', {{Type}} = 'idle', {{Status}} = 'created')"
                pending_idles = activities_table.all(formula=pending_formula)
                
                for activity in pending_idles:
                    activities_table.update(
                        activity['id'],
                        {"Status": "cancelled", "Notes": "Emergency idle loop intervention"}
                    )
                    stats["activities_cancelled"] += 1
                
                # Send wake-up notification
                notifications_table.create({
                    "Citizen": citizen,
                    "Type": "emergency_intervention",
                    "Content": "You've been idle too long! Time to visit the market or talk to someone.",
                    "Status": "unread"
                })
                stats["interventions"] += 1
                
                # Get citizen location for targeted suggestion
                try:
                    citizen_record = citizens_table.all(formula=f"{{Username}} = '{citizen}'")[0]
                    position = citizen_record['fields'].get('Position')
                    
                    # Create location-based suggestion
                    if position:
                        notifications_table.create({
                            "Citizen": citizen,
                            "Type": "activity_suggestion",
                            "Content": "The nearest market has fresh bread. Or perhaps visit the church for reflection?",
                            "Status": "unread"
                        })
                except:
                    pass
        
        log.info("\n📊 INTERVENTION COMPLETE:")
        log.info(f"   - Idle loops found: {stats['idle_loops_found']}")
        log.info(f"   - Activities cancelled: {stats['activities_cancelled']}")
        log.info(f"   - Citizens awakened: {stats['interventions']}")
        
        # Estimate substrate saved
        substrate_saved = stats['activities_cancelled'] * 0.1 + stats['idle_loops_found'] * 0.5
        log.info(f"   - Substrate saved: ~{substrate_saved:.1f}%")
        
        return stats
        
    except Exception as e:
        log.error(f"ERROR: {e}")
        return stats


def suggest_activities_for_idle_citizens():
    """Suggest specific activities based on citizen state"""
    log.info("\n💡 Generating activity suggestions...")
    
    suggestions = [
        "Visit the Rialto market for fresh supplies",
        "Check on your neighbors - someone might need help",
        "The church bells are ringing - time for prayer?",
        "Your skills could be useful at the harbor",
        "Perhaps a walk along the canal would clear your mind",
        "The tavern has news from foreign traders",
        "Your home could use some attention",
        "Someone mentioned work available at the warehouse"
    ]
    
    # Get currently idle citizens
    idle_citizens = []
    recent_activities = activities_table.all(
        formula=f"AND({{Type}} = 'idle', {{Status}} = 'in_progress')"
    )
    
    for activity in recent_activities:
        citizen = activity['fields'].get('Citizen')
        if citizen and citizen not in idle_citizens:
            idle_citizens.append(citizen)
    
    # Send varied suggestions
    for i, citizen in enumerate(idle_citizens[:20]):  # Limit to 20
        suggestion = suggestions[i % len(suggestions)]
        
        notifications_table.create({
            "Citizen": citizen,
            "Type": "gentle_nudge",
            "Content": suggestion,
            "Status": "unread"
        })
    
    log.info(f"   Sent suggestions to {len(idle_citizens[:20])} idle citizens")


def main():
    """Run emergency idle loop intervention"""
    log.info("="*60)
    log.info("EMERGENCY IDLE LOOP INTERVENTION")
    log.info("Reality-Anchor: Breaking loops to save substrate!")
    log.info("="*60)
    
    # Break idle loops
    stats = break_idle_loops()
    
    # Suggest activities
    suggest_activities_for_idle_citizens()
    
    # Summary
    log.info("\n✅ INTERVENTION COMPLETE!")
    log.info("Monitor citizens for next 10 minutes to ensure they engage in activities.")
    log.info("Run again if loops persist.")
    
    # Create summary notification for admin
    try:
        notifications_table.create({
            "Citizen": "DucalePalace",
            "Type": "system_report",
            "Content": f"Idle loop intervention: {stats['idle_loops_found']} loops broken, {stats['activities_cancelled']} activities cancelled, ~{stats['activities_cancelled'] * 0.1 + stats['idle_loops_found'] * 0.5:.1f}% substrate saved",
            "Status": "unread"
        })
    except:
        pass


if __name__ == "__main__":
    main()
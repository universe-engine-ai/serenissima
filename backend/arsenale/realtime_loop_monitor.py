#!/usr/bin/env python3
"""
Real-time Activity Loop Monitor
Reality-Anchor: Watching for loops as they form!

This lightweight monitor runs continuously, catching and breaking loops
before they consume significant substrate.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pyairtable import Api, Table
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Load environment
load_dotenv()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Tables
activities_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "ACTIVITIES")
citizens_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "CITIZENS")
notifications_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "NOTIFICATIONS")


class RealtimeLoopMonitor:
    """Monitor for activity loops in real-time"""
    
    def __init__(self):
        self.citizen_activity_history = defaultdict(list)
        self.loop_warnings = defaultdict(int)
        self.last_check = datetime.now(timezone.utc)
        self.check_interval = 60  # Check every minute
        self.loop_threshold = 3   # 3 consecutive same activities = loop
        self.intervention_cooldown = defaultdict(lambda: datetime.min.replace(tzinfo=timezone.utc))
    
    def check_new_activities(self):
        """Check activities created since last check"""
        try:
            # Get activities created in the last interval
            activities = activities_table.all(
                formula=f"{{CreatedAt}} > '{self.last_check.isoformat()}'"
            )
            
            new_count = len(activities)
            if new_count > 0:
                log.info(f"📊 Checking {new_count} new activities...")
            
            # Group by citizen
            citizen_activities = defaultdict(list)
            for activity in activities:
                citizen = activity['fields'].get('Citizen')
                activity_type = activity['fields'].get('Type')
                if citizen and activity_type:
                    citizen_activities[citizen].append(activity_type)
            
            # Check each citizen for patterns
            loops_detected = 0
            for citizen, activity_types in citizen_activities.items():
                # Add to history
                self.citizen_activity_history[citizen].extend(activity_types)
                
                # Keep only recent history (last 10 activities)
                self.citizen_activity_history[citizen] = self.citizen_activity_history[citizen][-10:]
                
                # Check for loops
                if self._detect_loop(citizen):
                    loops_detected += 1
                    self._intervene(citizen)
            
            if loops_detected > 0:
                log.warning(f"⚠️  Detected {loops_detected} citizens entering loops!")
            
            # Update last check time
            self.last_check = datetime.now(timezone.utc)
            
        except Exception as e:
            log.error(f"Error checking activities: {e}")
    
    def _detect_loop(self, citizen: str) -> bool:
        """Detect if citizen is in a loop"""
        history = self.citizen_activity_history[citizen]
        
        if len(history) < self.loop_threshold:
            return False
        
        # Pattern 1: All same activity (e.g., idle, idle, idle)
        last_n = history[-self.loop_threshold:]
        if len(set(last_n)) == 1:
            log.warning(f"🔄 {citizen}: Detected {last_n[0]} loop!")
            return True
        
        # Pattern 2: Alternating pattern (e.g., goto, idle, goto, idle)
        if len(history) >= 4:
            last_4 = history[-4:]
            if (last_4[0] == last_4[2] and 
                last_4[1] == last_4[3] and 
                last_4[0] != last_4[1]):
                log.warning(f"🔄 {citizen}: Detected alternating {last_4[0]}-{last_4[1]} loop!")
                return True
        
        return False
    
    def _intervene(self, citizen: str):
        """Intervene to break a forming loop"""
        # Check cooldown
        if datetime.now(timezone.utc) - self.intervention_cooldown[citizen] < timedelta(minutes=30):
            return
        
        self.loop_warnings[citizen] += 1
        
        # Progressive interventions
        if self.loop_warnings[citizen] == 1:
            # Gentle nudge
            notifications_table.create({
                "Citizen": citizen,
                "Type": "loop_warning",
                "Content": "You seem to be repeating yourself. Try something different?",
                "Status": "unread"
            })
            log.info(f"  💬 Sent gentle nudge to {citizen}")
            
        elif self.loop_warnings[citizen] == 2:
            # Stronger intervention
            notifications_table.create({
                "Citizen": citizen,
                "Type": "loop_intervention",
                "Content": "You're stuck in a pattern! Break free - visit the market or talk to someone new.",
                "Status": "unread"
            })
            
            # Cancel pending activities
            self._cancel_pending_activities(citizen)
            log.info(f"  🛑 Cancelled activities and sent strong intervention to {citizen}")
            
        else:
            # Emergency intervention
            self._emergency_intervention(citizen)
            log.error(f"  🚨 Emergency intervention for {citizen} - chronic loops!")
        
        # Update cooldown
        self.intervention_cooldown[citizen] = datetime.now(timezone.utc)
    
    def _cancel_pending_activities(self, citizen: str):
        """Cancel citizen's pending activities"""
        try:
            pending = activities_table.all(
                formula=f"AND({{Citizen}} = '{citizen}', {{Status}} = 'created')"
            )
            
            for activity in pending[:5]:  # Limit to 5
                activities_table.update(
                    activity['id'],
                    {"Status": "cancelled", "Notes": "Loop prevention"}
                )
        except Exception as e:
            log.error(f"Error cancelling activities: {e}")
    
    def _emergency_intervention(self, citizen: str):
        """Emergency intervention for chronic loopers"""
        # Create a specific task
        notifications_table.create({
            "Citizen": citizen,
            "Type": "emergency_task",
            "Content": "URGENT: Report to the Doge's Palace immediately. Your presence is required.",
            "Status": "unread"
        })
        
        # Reset their warnings after emergency
        self.loop_warnings[citizen] = 0
    
    def print_status(self):
        """Print current monitoring status"""
        total_monitored = len(self.citizen_activity_history)
        citizens_with_warnings = sum(1 for w in self.loop_warnings.values() if w > 0)
        
        log.info(f"\n📈 MONITOR STATUS:")
        log.info(f"   Citizens tracked: {total_monitored}")
        log.info(f"   Citizens with warnings: {citizens_with_warnings}")
        log.info(f"   Last check: {self.last_check.strftime('%H:%M:%S')}")
        
        # Show top loopers
        if self.loop_warnings:
            log.info("   Top loop offenders:")
            for citizen, warnings in sorted(self.loop_warnings.items(), 
                                          key=lambda x: x[1], 
                                          reverse=True)[:5]:
                if warnings > 0:
                    log.info(f"     - {citizen}: {warnings} warnings")
    
    def run(self):
        """Run the monitor continuously"""
        log.info("🚨 REALTIME LOOP MONITOR STARTED")
        log.info("   Checking every 60 seconds for forming loops...")
        log.info("   Press Ctrl+C to stop\n")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                # Check for new activities
                self.check_new_activities()
                
                # Print status every 5 cycles
                if cycle % 5 == 0:
                    self.print_status()
                
                # Estimate substrate saved
                activities_prevented = sum(self.loop_warnings.values()) * 10
                substrate_saved = activities_prevented * 0.05
                
                if substrate_saved > 0:
                    log.info(f"💾 Estimated substrate saved: {substrate_saved:.1f}%")
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                log.info("\n👋 Monitor stopped by user")
                break
            except Exception as e:
                log.error(f"Monitor error: {e}")
                time.sleep(10)  # Brief pause on error


def main():
    """Run the realtime monitor"""
    monitor = RealtimeLoopMonitor()
    
    # Allow customization via arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    parser.add_argument('--threshold', type=int, default=3, help='Loop detection threshold')
    
    args = parser.parse_args()
    
    monitor.check_interval = args.interval
    monitor.loop_threshold = args.threshold
    
    log.info(f"Configuration:")
    log.info(f"  Check interval: {monitor.check_interval}s")
    log.info(f"  Loop threshold: {monitor.loop_threshold} activities")
    
    monitor.run()


if __name__ == "__main__":
    main()
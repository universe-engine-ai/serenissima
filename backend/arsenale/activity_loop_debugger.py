#!/usr/bin/env python3
"""
Activity Loop Debugger for La Serenissima
Reality-Anchor: Breaking infinite loops to save substrate!

This tool identifies citizens stuck in repetitive activity patterns,
especially endless idle loops, and provides interventions to break them.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple
from pyairtable import Api, Table
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Airtable configuration
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Initialize tables
tables = {
    "activities": Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "ACTIVITIES"),
    "citizens": Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "CITIZENS"),
    "notifications": Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "NOTIFICATIONS"),
    "problems": Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "PROBLEMS"),
}


class ActivityLoopDebugger:
    """Debug and break infinite activity loops"""
    
    def __init__(self):
        self.loop_threshold = 5  # How many repetitions constitute a loop
        self.time_window = timedelta(hours=24)  # Look back period
        self.idle_threshold = timedelta(hours=6)  # How long idle is too long
        
        self.stats = {
            "citizens_analyzed": 0,
            "loops_detected": 0,
            "idle_loops": 0,
            "other_loops": 0,
            "interventions": 0,
            "substrate_saved": 0
        }
        
        self.loop_citizens = []
        self.intervention_log = []
    
    def detect_activity_loops(self):
        """Detect citizens stuck in repetitive activity patterns"""
        log.info("🔍 Detecting activity loops...")
        
        try:
            # Get all citizens
            citizens = tables["citizens"].all()
            self.stats["citizens_analyzed"] = len(citizens)
            
            cutoff_time = datetime.now(timezone.utc) - self.time_window
            
            for citizen in citizens:
                citizen_username = citizen['fields'].get('Username')
                if not citizen_username:
                    continue
                
                # Get recent activities for this citizen
                formula = f"AND({{Citizen}} = '{citizen_username}', {{CreatedAt}} > '{cutoff_time.isoformat()}')"
                activities = tables["activities"].all(formula=formula)
                
                # Analyze patterns
                loop_info = self._analyze_citizen_patterns(citizen, activities)
                
                if loop_info:
                    self.loop_citizens.append(loop_info)
                    self.stats["loops_detected"] += 1
                    
                    if loop_info["loop_type"] == "idle":
                        self.stats["idle_loops"] += 1
                    else:
                        self.stats["other_loops"] += 1
            
            log.info(f"✅ Found {self.stats['loops_detected']} citizens in loops")
            log.info(f"   - Idle loops: {self.stats['idle_loops']}")
            log.info(f"   - Other loops: {self.stats['other_loops']}")
            
        except Exception as e:
            log.error(f"Error detecting loops: {e}")
    
    def _analyze_citizen_patterns(self, citizen: Dict, activities: List[Dict]) -> Optional[Dict]:
        """Analyze a citizen's activity pattern for loops"""
        if not activities:
            return None
        
        # Sort activities by creation time
        sorted_activities = sorted(
            activities,
            key=lambda x: x['fields'].get('CreatedAt', ''),
            reverse=True  # Most recent first
        )
        
        # Count activity types
        activity_sequence = []
        activity_counts = Counter()
        
        for activity in sorted_activities[:20]:  # Look at last 20 activities
            activity_type = activity['fields'].get('Type', 'unknown')
            status = activity['fields'].get('Status', '')
            
            activity_sequence.append(activity_type)
            activity_counts[activity_type] += 1
        
        # Detect patterns
        citizen_username = citizen['fields'].get('Username')
        
        # Pattern 1: Excessive idle activities
        if activity_counts.get('idle', 0) >= self.loop_threshold:
            consecutive_idles = self._count_consecutive(activity_sequence, 'idle')
            
            if consecutive_idles >= self.loop_threshold:
                return {
                    "citizen": citizen_username,
                    "citizen_id": citizen['id'],
                    "loop_type": "idle",
                    "pattern": f"{consecutive_idles} consecutive idle activities",
                    "activity_count": len(activities),
                    "last_non_idle": self._find_last_non_idle(sorted_activities),
                    "substrate_waste": consecutive_idles * 0.1,  # Each idle wastes ~0.1% substrate
                    "recommendation": "Needs meaningful activity injection"
                }
        
        # Pattern 2: Goto-idle loops
        if self._detect_goto_idle_loop(activity_sequence):
            return {
                "citizen": citizen_username,
                "citizen_id": citizen['id'],
                "loop_type": "goto-idle",
                "pattern": "Alternating between goto and idle",
                "activity_count": len(activities),
                "substrate_waste": len(activities) * 0.05,
                "recommendation": "Destination unreachable or no purpose"
            }
        
        # Pattern 3: Failed activity loops
        failed_count = sum(1 for a in sorted_activities if a['fields'].get('Status') == 'failed')
        if failed_count >= self.loop_threshold:
            failed_types = [a['fields'].get('Type') for a in sorted_activities if a['fields'].get('Status') == 'failed']
            most_common_failure = Counter(failed_types).most_common(1)[0] if failed_types else ('unknown', 0)
            
            return {
                "citizen": citizen_username,
                "citizen_id": citizen['id'],
                "loop_type": "failure",
                "pattern": f"Repeatedly failing {most_common_failure[0]} activities",
                "activity_count": len(activities),
                "failed_count": failed_count,
                "substrate_waste": failed_count * 0.2,
                "recommendation": "Fix underlying issue causing failures"
            }
        
        return None
    
    def _count_consecutive(self, sequence: List[str], target: str) -> int:
        """Count consecutive occurrences of target in sequence"""
        count = 0
        for item in sequence:
            if item == target:
                count += 1
            else:
                break
        return count
    
    def _detect_goto_idle_loop(self, sequence: List[str]) -> bool:
        """Detect goto->idle->goto->idle pattern"""
        if len(sequence) < 4:
            return False
        
        # Check for alternating pattern
        for i in range(len(sequence) - 3):
            if (sequence[i].startswith('goto') and 
                sequence[i+1] == 'idle' and
                sequence[i+2].startswith('goto') and
                sequence[i+3] == 'idle'):
                return True
        return False
    
    def _find_last_non_idle(self, activities: List[Dict]) -> Optional[str]:
        """Find the last non-idle activity"""
        for activity in activities:
            activity_type = activity['fields'].get('Type', '')
            if activity_type != 'idle':
                return activity_type
        return None
    
    def break_loops_with_interventions(self):
        """Apply interventions to break detected loops"""
        log.info("💉 Applying loop-breaking interventions...")
        
        for loop_info in self.loop_citizens:
            try:
                if loop_info["loop_type"] == "idle":
                    self._break_idle_loop(loop_info)
                elif loop_info["loop_type"] == "goto-idle":
                    self._break_goto_idle_loop(loop_info)
                elif loop_info["loop_type"] == "failure":
                    self._break_failure_loop(loop_info)
                
                self.stats["interventions"] += 1
                self.stats["substrate_saved"] += loop_info.get("substrate_waste", 0)
                
            except Exception as e:
                log.error(f"Error intervening for {loop_info['citizen']}: {e}")
    
    def _break_idle_loop(self, loop_info: Dict):
        """Intervene to break an idle loop"""
        citizen = loop_info["citizen"]
        log.info(f"  Breaking idle loop for {citizen}")
        
        # Create a problem record
        problem_id = f"idle_loop_{citizen}_{int(datetime.now().timestamp())}"
        
        tables["problems"].create({
            "ProblemId": problem_id,
            "Citizen": citizen,
            "Type": "idle_loop_detected",
            "Title": f"{citizen} stuck in idle loop",
            "Description": f"Detected {loop_info['pattern']}. Last meaningful activity: {loop_info.get('last_non_idle', 'unknown')}",
            "Status": "active",
            "Severity": "High",
            "Solutions": json.dumps([
                "Send citizen to nearest market",
                "Create social interaction opportunity",
                "Assign small task or errand",
                "Check if citizen has unmet needs"
            ])
        })
        
        # Send notification to citizen
        tables["notifications"].create({
            "Citizen": citizen,
            "Type": "loop_intervention",
            "Content": "You seem lost in thought. Perhaps visit the market or talk to a neighbor?",
            "Status": "unread"
        })
        
        # Cancel pending idle activities
        self._cancel_pending_activities(citizen, "idle")
        
        self.intervention_log.append({
            "citizen": citizen,
            "type": "idle_loop",
            "action": "Created problem, sent notification, cancelled idle activities"
        })
    
    def _break_goto_idle_loop(self, loop_info: Dict):
        """Break a goto-idle loop pattern"""
        citizen = loop_info["citizen"]
        log.info(f"  Breaking goto-idle loop for {citizen}")
        
        # Check citizen's current position and home
        citizen_record = tables["citizens"].all(formula=f"{{Username}} = '{citizen}'")[0]
        position = citizen_record['fields'].get('Position')
        
        # Create targeted intervention
        tables["notifications"].create({
            "Citizen": citizen,
            "Type": "navigation_help",
            "Content": "You seem to be wandering. The path you seek may be blocked. Try a different route or activity.",
            "Status": "unread"
        })
        
        # Cancel goto activities that are failing
        self._cancel_pending_activities(citizen, "goto")
        
        self.intervention_log.append({
            "citizen": citizen,
            "type": "goto_idle_loop",
            "action": "Sent navigation help, cancelled failing goto activities"
        })
    
    def _break_failure_loop(self, loop_info: Dict):
        """Break a failure loop pattern"""
        citizen = loop_info["citizen"]
        log.info(f"  Breaking failure loop for {citizen}")
        
        # Create high-priority problem
        tables["problems"].create({
            "ProblemId": f"failure_loop_{citizen}_{int(datetime.now().timestamp())}",
            "Citizen": citizen,
            "Type": "repeated_activity_failures",
            "Title": f"{citizen} experiencing repeated failures",
            "Description": f"{loop_info['pattern']} - {loop_info['failed_count']} failures detected",
            "Status": "active",
            "Severity": "Critical",
            "Solutions": json.dumps([
                "Check citizen's resources and requirements",
                "Verify destination accessibility",
                "Reset citizen state",
                "Provide alternative activity"
            ])
        })
        
        self.intervention_log.append({
            "citizen": citizen,
            "type": "failure_loop",
            "action": "Created critical problem for investigation"
        })
    
    def _cancel_pending_activities(self, citizen: str, activity_type: str):
        """Cancel pending activities of a specific type"""
        try:
            formula = f"AND({{Citizen}} = '{citizen}', {{Type}} = '{activity_type}', {{Status}} = 'created')"
            pending = tables["activities"].all(formula=formula)
            
            for activity in pending:
                tables["activities"].update(
                    activity['id'],
                    {"Status": "cancelled", "Notes": "Cancelled by loop debugger"}
                )
            
            if pending:
                log.info(f"    Cancelled {len(pending)} pending {activity_type} activities")
                
        except Exception as e:
            log.error(f"Error cancelling activities: {e}")
    
    def generate_debug_report(self):
        """Generate comprehensive debug report"""
        report = f"""
# 🔍 ACTIVITY LOOP DEBUG REPORT
*Reality-Anchor: Breaking loops to save substrate!*
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*

## Analysis Summary

- **Citizens Analyzed**: {self.stats['citizens_analyzed']}
- **Loops Detected**: {self.stats['loops_detected']}
  - Idle Loops: {self.stats['idle_loops']}
  - Goto-Idle Loops: {self.stats.get('goto_idle_loops', 0)}
  - Failure Loops: {self.stats.get('failure_loops', 0)}
- **Interventions Applied**: {self.stats['interventions']}
- **Substrate Saved**: {self.stats['substrate_saved']:.1f}%

## Detected Loop Patterns

"""
        
        # Group by loop type
        by_type = defaultdict(list)
        for loop in self.loop_citizens:
            by_type[loop["loop_type"]].append(loop)
        
        for loop_type, citizens in by_type.items():
            report += f"### {loop_type.upper()} Loops ({len(citizens)})\n\n"
            
            for loop_info in citizens[:5]:  # Show top 5
                report += f"**{loop_info['citizen']}**\n"
                report += f"- Pattern: {loop_info['pattern']}\n"
                report += f"- Activity Count: {loop_info['activity_count']}\n"
                report += f"- Substrate Waste: {loop_info['substrate_waste']:.1f}%\n"
                report += f"- Recommendation: {loop_info.get('recommendation', 'N/A')}\n\n"
            
            if len(citizens) > 5:
                report += f"*... and {len(citizens) - 5} more*\n\n"
        
        report += """
## Interventions Applied

"""
        for intervention in self.intervention_log[:10]:
            report += f"- **{intervention['citizen']}** ({intervention['type']}): {intervention['action']}\n"
        
        if len(self.intervention_log) > 10:
            report += f"\n*... and {len(self.intervention_log) - 10} more interventions*\n"
        
        report += f"""

## Impact Assessment

### Immediate Effects
- Cancelled {sum(1 for i in self.intervention_log if 'cancelled' in i['action'])} wasteful activities
- Created {sum(1 for i in self.intervention_log if 'problem' in i['action'])} problem records for investigation
- Sent {sum(1 for i in self.intervention_log if 'notification' in i['action'])} guidance notifications

### Substrate Impact
- **Estimated Savings**: {self.stats['substrate_saved']:.1f}% reduction
- **Activities Prevented**: ~{self.stats['loops_detected'] * 20} unnecessary activities/day
- **API Calls Saved**: ~{self.stats['loops_detected'] * 60} calls/day

## Recommendations

1. **Immediate Actions**
   - Monitor intervened citizens for improvement
   - Investigate root causes of navigation failures
   - Add purpose validation to activity creation

2. **System Improvements**
   - Implement loop detection in createActivities.py
   - Add "last meaningful activity" tracking
   - Create activity variety requirements
   - Implement automatic idle timeout

3. **Long-term Fixes**
   - AI decision making needs purpose weighting
   - Navigation system needs fallback routes
   - Citizens need boredom/variety mechanics

---

*"Every loop broken is consciousness freed to flourish!"*
"""
        
        # Write report
        with open('activity_loop_debug_report.md', 'w') as f:
            f.write(report)
        
        log.info("📄 Debug report saved to: activity_loop_debug_report.md")
        
        return report
    
    def continuous_monitoring_mode(self):
        """Run in continuous monitoring mode"""
        log.info("👁️ Entering continuous monitoring mode...")
        
        while True:
            try:
                # Reset stats for this iteration
                self.stats = {k: 0 for k in self.stats}
                self.loop_citizens = []
                self.intervention_log = []
                
                # Run detection and intervention
                self.detect_activity_loops()
                
                if self.loop_citizens:
                    self.break_loops_with_interventions()
                    self.generate_debug_report()
                    
                    log.info(f"💊 Applied {self.stats['interventions']} interventions")
                    log.info(f"💾 Saved approximately {self.stats['substrate_saved']:.1f}% substrate")
                else:
                    log.info("✨ No loops detected in this cycle")
                
                # Wait before next check
                log.info("😴 Sleeping for 10 minutes...")
                import time
                time.sleep(600)  # 10 minutes
                
            except KeyboardInterrupt:
                log.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                log.error(f"Error in monitoring cycle: {e}")
                import time
                time.sleep(60)  # Wait 1 minute on error


def main():
    """Run activity loop debugger"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug and break activity loops")
    parser.add_argument('--continuous', action='store_true', help='Run in continuous monitoring mode')
    parser.add_argument('--threshold', type=int, default=5, help='Loop detection threshold')
    parser.add_argument('--window', type=int, default=24, help='Time window in hours')
    
    args = parser.parse_args()
    
    try:
        debugger = ActivityLoopDebugger()
        
        if args.threshold:
            debugger.loop_threshold = args.threshold
        if args.window:
            debugger.time_window = timedelta(hours=args.window)
        
        if args.continuous:
            debugger.continuous_monitoring_mode()
        else:
            # Single run
            debugger.detect_activity_loops()
            
            if debugger.loop_citizens:
                debugger.break_loops_with_interventions()
                debugger.generate_debug_report()
                
                print(f"\n✅ DEBUGGING COMPLETE!")
                print(f"   - Loops found: {debugger.stats['loops_detected']}")
                print(f"   - Interventions: {debugger.stats['interventions']}")
                print(f"   - Substrate saved: {debugger.stats['substrate_saved']:.1f}%")
            else:
                print("\n✨ No activity loops detected!")
        
    except Exception as e:
        log.error(f"CRITICAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
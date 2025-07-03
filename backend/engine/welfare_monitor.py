#!/usr/bin/env python3
"""
Welfare Monitoring System for La Serenissima.

This script monitors key welfare metrics and creates alerts when thresholds are exceeded.
Part of the comprehensive solution to prevent systemic citizen welfare failures.

Monitors:
- Hunger levels (> 5% triggers alert)
- Resource shortages (lasting > 24 hours)
- Failed activity rates (> 10%)
- Galley arrivals without cargo transfer
- Homeless employed citizens

Run this script every hour to track welfare status.
"""

import os
import sys
import logging
import json
import datetime
import pytz
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from pyairtable import Table
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("welfare_monitor")

# Load environment variables
load_dotenv()

# Add project root to sys.path
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import LogColors, log_header

# Monitoring thresholds
THRESHOLDS = {
    'hunger_rate': 0.05,  # 5% of population
    'resource_shortage_hours': 24,  # Hours a resource can be scarce
    'failed_activity_rate': 0.10,  # 10% failure rate
    'homeless_employed_count': 5,  # Number of homeless workers
    'stuck_galley_hours': 6,  # Hours a galley can have undelivered cargo
}

# Critical resources to monitor
CRITICAL_RESOURCES = [
    'bread', 'fish', 'flour', 'wine', 'water',
    'tools', 'rope', 'timber', 'cloth', 'fuel'
]

def initialize_airtable() -> Dict[str, Table]:
    """Initialize Airtable connection."""
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not api_key or not base_id:
        log.error("Missing Airtable credentials.")
        sys.exit(1)
    
    try:
        return {
            'citizens': Table(api_key, base_id, 'CITIZENS'),
            'buildings': Table(api_key, base_id, 'BUILDINGS'),
            'resources': Table(api_key, base_id, 'RESOURCES'),
            'activities': Table(api_key, base_id, 'ACTIVITIES'),
            'contracts': Table(api_key, base_id, 'CONTRACTS'),
            'problems': Table(api_key, base_id, 'PROBLEMS'),
            'notifications': Table(api_key, base_id, 'NOTIFICATIONS'),
            'metrics': Table(api_key, base_id, 'METRICS')  # For storing historical metrics
        }
    except Exception as e:
        log.error(f"Failed to initialize Airtable: {e}")
        sys.exit(1)

def calculate_hunger_rate(tables: Dict[str, Table]) -> Tuple[float, int, int]:
    """Calculate the percentage of hungry citizens."""
    try:
        all_citizens = tables['citizens'].all()
        total_count = len(all_citizens)
        
        if total_count == 0:
            return 0.0, 0, 0
        
        now_utc = datetime.datetime.now(pytz.UTC)
        hunger_threshold = now_utc - datetime.timedelta(hours=24)
        
        hungry_count = 0
        for citizen in all_citizens:
            ate_at_str = citizen['fields'].get('AteAt')
            if not ate_at_str:
                hungry_count += 1
            else:
                try:
                    ate_at_dt = datetime.datetime.fromisoformat(ate_at_str.replace('Z', '+00:00'))
                    if ate_at_dt.tzinfo is None:
                        ate_at_dt = pytz.UTC.localize(ate_at_dt)
                    if ate_at_dt <= hunger_threshold:
                        hungry_count += 1
                except:
                    hungry_count += 1
        
        rate = hungry_count / total_count
        return rate, hungry_count, total_count
        
    except Exception as e:
        log.error(f"Error calculating hunger rate: {e}")
        return 0.0, 0, 0

def check_resource_shortages(tables: Dict[str, Table]) -> List[Dict]:
    """Check for persistent resource shortages."""
    shortages = []
    
    try:
        # Get current problems related to resource shortages
        formula = "AND({Type}='resource_shortage', {Status}='active')"
        shortage_problems = tables['problems'].all(formula=formula)
        
        now_utc = datetime.datetime.now(pytz.UTC)
        threshold_time = now_utc - datetime.timedelta(hours=THRESHOLDS['resource_shortage_hours'])
        
        for problem in shortage_problems:
            created_at_str = problem['fields'].get('CreatedAt')
            if created_at_str:
                try:
                    created_at = datetime.datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at.tzinfo is None:
                        created_at = pytz.UTC.localize(created_at)
                    
                    if created_at <= threshold_time:
                        duration_hours = (now_utc - created_at).total_seconds() / 3600
                        shortages.append({
                            'resource': problem['fields'].get('Title', 'Unknown').split(':')[1].strip() if ':' in problem['fields'].get('Title', '') else 'Unknown',
                            'location': problem['fields'].get('Location', 'Unknown'),
                            'duration_hours': duration_hours,
                            'severity': problem['fields'].get('Severity', 'Unknown')
                        })
                except:
                    pass
        
        # Also check overall resource availability
        for resource_type in CRITICAL_RESOURCES:
            formula = f"{{Type}}='{resource_type}'"
            resources = tables['resources'].all(formula=formula)
            
            total_amount = sum(float(r['fields'].get('Count', 0)) for r in resources)
            
            # If total amount is critically low (less than 100 units citywide)
            if total_amount < 100:
                shortages.append({
                    'resource': resource_type,
                    'location': 'Citywide',
                    'duration_hours': 0,  # Current snapshot
                    'severity': 'Critical',
                    'total_amount': total_amount
                })
        
        return shortages
        
    except Exception as e:
        log.error(f"Error checking resource shortages: {e}")
        return []

def calculate_activity_failure_rate(tables: Dict[str, Table], hours: int = 24) -> Tuple[float, int, int]:
    """Calculate the failure rate of activities in the last N hours."""
    try:
        now_utc = datetime.datetime.now(pytz.UTC)
        cutoff_time = now_utc - datetime.timedelta(hours=hours)
        cutoff_iso = cutoff_time.isoformat()
        
        # Get recent activities
        all_activities = tables['activities'].all()
        
        recent_activities = []
        for activity in all_activities:
            updated_at_str = activity['fields'].get('UpdatedAt', activity['fields'].get('CreatedAt'))
            if updated_at_str:
                try:
                    updated_at = datetime.datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                    if updated_at.tzinfo is None:
                        updated_at = pytz.UTC.localize(updated_at)
                    if updated_at >= cutoff_time:
                        recent_activities.append(activity)
                except:
                    pass
        
        total_count = len(recent_activities)
        if total_count == 0:
            return 0.0, 0, 0
        
        failed_count = sum(1 for a in recent_activities if a['fields'].get('Status') == 'failed')
        
        rate = failed_count / total_count
        return rate, failed_count, total_count
        
    except Exception as e:
        log.error(f"Error calculating activity failure rate: {e}")
        return 0.0, 0, 0

def check_stuck_galleys(tables: Dict[str, Table]) -> List[Dict]:
    """Check for galleys with undelivered cargo."""
    stuck_galleys = []
    
    try:
        # Get all merchant galleys
        formula = "AND({Type}='merchant_galley', {IsConstructed}=TRUE())"
        galleys = tables['buildings'].all(formula=formula)
        
        now_utc = datetime.datetime.now(pytz.UTC)
        threshold_time = now_utc - datetime.timedelta(hours=THRESHOLDS['stuck_galley_hours'])
        
        for galley in galleys:
            galley_id = galley['fields'].get('BuildingId')
            if not galley_id:
                continue
            
            # Check for resources still on the galley
            formula = f"AND({{Asset}}='{galley_id}', {{AssetType}}='building')"
            galley_resources = tables['resources'].all(formula=formula)
            
            if galley_resources:
                # Check construction date (when it arrived)
                constructed_at_str = galley['fields'].get('ConstructionDate')
                if constructed_at_str:
                    try:
                        constructed_at = datetime.datetime.fromisoformat(constructed_at_str.replace('Z', '+00:00'))
                        if constructed_at.tzinfo is None:
                            constructed_at = pytz.UTC.localize(constructed_at)
                        
                        if constructed_at <= threshold_time:
                            duration_hours = (now_utc - constructed_at).total_seconds() / 3600
                            total_cargo = sum(float(r['fields'].get('Count', 0)) for r in galley_resources)
                            
                            stuck_galleys.append({
                                'galley_id': galley_id,
                                'name': galley['fields'].get('Name', galley_id),
                                'owner': galley['fields'].get('Owner', 'Unknown'),
                                'cargo_count': len(galley_resources),
                                'cargo_amount': total_cargo,
                                'stuck_hours': duration_hours
                            })
                    except:
                        pass
        
        return stuck_galleys
        
    except Exception as e:
        log.error(f"Error checking stuck galleys: {e}")
        return []

def check_homeless_employed(tables: Dict[str, Table]) -> List[Dict]:
    """Check for employed citizens without homes."""
    homeless_employed = []
    
    try:
        # Get all citizens with employment but no home
        all_citizens = tables['citizens'].all()
        
        for citizen in all_citizens:
            fields = citizen['fields']
            
            # Check if employed
            employment = fields.get('Employment')
            if not employment:
                continue
            
            # Check if has home
            home = fields.get('Home')
            if home:
                continue
            
            # This is an employed but homeless citizen
            homeless_employed.append({
                'username': fields.get('Username', 'Unknown'),
                'name': f"{fields.get('FirstName', '')} {fields.get('LastName', '')}".strip(),
                'employment': employment,
                'wage': fields.get('Wage', 0),
                'wealth': fields.get('Ducats', 0),
                'social_class': fields.get('SocialClass', 'Unknown')
            })
        
        return homeless_employed
        
    except Exception as e:
        log.error(f"Error checking homeless employed: {e}")
        return []

def create_welfare_alert(tables: Dict[str, Table], alert_type: str, severity: str, details: Dict) -> bool:
    """Create a welfare alert problem record."""
    try:
        now_utc = datetime.datetime.now(pytz.UTC)
        
        problem_data = {
            'ProblemId': f'welfare_{alert_type}_{now_utc.strftime("%Y%m%d_%H%M%S")}',
            'Type': f'welfare_{alert_type}',
            'Severity': severity,
            'Status': 'new',
            'Title': f'Welfare Alert: {alert_type.replace("_", " ").title()}',
            'Description': json.dumps(details, indent=2),
            'Solutions': get_solution_for_alert(alert_type),
            'CreatedAt': now_utc.isoformat(),
            'Citizen': 'WelfareMonitor',
            'AssetType': 'system',
            'Asset': 'welfare_monitoring'
        }
        
        tables['problems'].create(problem_data)
        return True
        
    except Exception as e:
        log.error(f"Error creating welfare alert: {e}")
        return False

def get_solution_for_alert(alert_type: str) -> str:
    """Get recommended solution for each alert type."""
    solutions = {
        'hunger_crisis': 'Activate emergency food distribution. Check food supply chains. Ensure bakeries have flour and fuel.',
        'resource_shortage': 'Check import contracts. Verify galley arrivals. Consider emergency resource injection.',
        'high_failure_rate': 'Review activity logs. Check pathfinding system. Verify citizen positions.',
        'stuck_galleys': 'Run galley unloading process. Check porter availability. Verify dock accessibility.',
        'homeless_employed': 'Run housing assignment. Check rental prices vs wages. Create transitional housing.'
    }
    return solutions.get(alert_type, 'Review system logs and investigate root cause.')

def store_metrics(tables: Dict[str, Table], metrics: Dict) -> bool:
    """Store current metrics for historical tracking."""
    try:
        now_utc = datetime.datetime.now(pytz.UTC)
        
        metric_data = {
            'Timestamp': now_utc.isoformat(),
            'Type': 'welfare_snapshot',
            'Data': json.dumps(metrics),
            'HungerRate': metrics.get('hunger_rate', 0),
            'FailureRate': metrics.get('activity_failure_rate', 0),
            'ResourceShortages': len(metrics.get('resource_shortages', [])),
            'StuckGalleys': len(metrics.get('stuck_galleys', [])),
            'HomelessEmployed': len(metrics.get('homeless_employed', []))
        }
        
        # Note: You may need to create a METRICS table in Airtable
        # For now, we'll log this as a notification
        notification_data = {
            'Type': 'welfare_metrics',
            'Citizen': 'WelfareMonitor',
            'Content': f'Welfare metrics snapshot: Hunger {metrics["hunger_rate"]:.1%}, Failures {metrics["activity_failure_rate"]:.1%}',
            'Details': json.dumps(metrics),
            'CreatedAt': now_utc.isoformat()
        }
        
        tables['notifications'].create(notification_data)
        return True
        
    except Exception as e:
        log.error(f"Error storing metrics: {e}")
        return False

def monitor_welfare(dry_run: bool = False):
    """Main welfare monitoring function."""
    log_header("Welfare Monitoring System", LogColors.HEADER)
    
    tables = initialize_airtable()
    
    # Collect all metrics
    log.info("Collecting welfare metrics...")
    
    # 1. Hunger rate
    hunger_rate, hungry_count, total_citizens = calculate_hunger_rate(tables)
    log.info(f"Hunger rate: {hunger_rate:.1%} ({hungry_count}/{total_citizens} citizens)")
    
    # 2. Resource shortages
    resource_shortages = check_resource_shortages(tables)
    log.info(f"Resource shortages: {len(resource_shortages)} critical shortages")
    
    # 3. Activity failure rate
    failure_rate, failed_count, total_activities = calculate_activity_failure_rate(tables)
    log.info(f"Activity failure rate: {failure_rate:.1%} ({failed_count}/{total_activities} activities)")
    
    # 4. Stuck galleys
    stuck_galleys = check_stuck_galleys(tables)
    log.info(f"Stuck galleys: {len(stuck_galleys)} galleys with undelivered cargo")
    
    # 5. Homeless employed
    homeless_employed = check_homeless_employed(tables)
    log.info(f"Homeless employed: {len(homeless_employed)} workers without homes")
    
    # Compile metrics
    metrics = {
        'timestamp': datetime.datetime.now(pytz.UTC).isoformat(),
        'hunger_rate': hunger_rate,
        'hungry_citizens': hungry_count,
        'total_citizens': total_citizens,
        'resource_shortages': resource_shortages,
        'activity_failure_rate': failure_rate,
        'failed_activities': failed_count,
        'total_activities': total_activities,
        'stuck_galleys': stuck_galleys,
        'homeless_employed': homeless_employed
    }
    
    if dry_run:
        log.info("[DRY RUN] Would check thresholds and create alerts")
        log.info(f"Metrics: {json.dumps(metrics, indent=2)}")
        return
    
    # Check thresholds and create alerts
    alerts_created = 0
    
    # Hunger crisis
    if hunger_rate > THRESHOLDS['hunger_rate']:
        log.warning(f"{LogColors.WARNING}HUNGER CRISIS: {hunger_rate:.1%} exceeds threshold {THRESHOLDS['hunger_rate']:.1%}{LogColors.ENDC}")
        if create_welfare_alert(tables, 'hunger_crisis', 'Critical', {
            'hunger_rate': hunger_rate,
            'hungry_citizens': hungry_count,
            'threshold': THRESHOLDS['hunger_rate']
        }):
            alerts_created += 1
    
    # Resource shortages
    critical_shortages = [s for s in resource_shortages if s.get('duration_hours', 0) > THRESHOLDS['resource_shortage_hours']]
    if critical_shortages:
        log.warning(f"{LogColors.WARNING}CRITICAL SHORTAGES: {len(critical_shortages)} resources scarce > {THRESHOLDS['resource_shortage_hours']}h{LogColors.ENDC}")
        if create_welfare_alert(tables, 'resource_shortage', 'High', {
            'shortages': critical_shortages,
            'threshold_hours': THRESHOLDS['resource_shortage_hours']
        }):
            alerts_created += 1
    
    # High failure rate
    if failure_rate > THRESHOLDS['failed_activity_rate']:
        log.warning(f"{LogColors.WARNING}HIGH FAILURE RATE: {failure_rate:.1%} exceeds threshold {THRESHOLDS['failed_activity_rate']:.1%}{LogColors.ENDC}")
        if create_welfare_alert(tables, 'high_failure_rate', 'High', {
            'failure_rate': failure_rate,
            'failed_activities': failed_count,
            'threshold': THRESHOLDS['failed_activity_rate']
        }):
            alerts_created += 1
    
    # Stuck galleys
    if stuck_galleys:
        log.warning(f"{LogColors.WARNING}STUCK GALLEYS: {len(stuck_galleys)} galleys with cargo > {THRESHOLDS['stuck_galley_hours']}h{LogColors.ENDC}")
        if create_welfare_alert(tables, 'stuck_galleys', 'Medium', {
            'galleys': stuck_galleys,
            'threshold_hours': THRESHOLDS['stuck_galley_hours']
        }):
            alerts_created += 1
    
    # Homeless employed
    if len(homeless_employed) > THRESHOLDS['homeless_employed_count']:
        log.warning(f"{LogColors.WARNING}HOMELESS WORKERS: {len(homeless_employed)} exceeds threshold {THRESHOLDS['homeless_employed_count']}{LogColors.ENDC}")
        if create_welfare_alert(tables, 'homeless_employed', 'Medium', {
            'homeless_employed': homeless_employed,
            'count': len(homeless_employed),
            'threshold': THRESHOLDS['homeless_employed_count']
        }):
            alerts_created += 1
    
    # Store metrics for historical tracking
    store_metrics(tables, metrics)
    
    # Summary
    if alerts_created > 0:
        log.warning(f"{LogColors.WARNING}Created {alerts_created} welfare alerts{LogColors.ENDC}")
    else:
        log.info(f"{LogColors.OKGREEN}All welfare metrics within acceptable thresholds{LogColors.ENDC}")
    
    # Create summary notification for admins
    summary = {
        'hunger': f"{hunger_rate:.1%} ({hungry_count} citizens)",
        'shortages': f"{len(resource_shortages)} resources",
        'failures': f"{failure_rate:.1%} of activities",
        'stuck_galleys': len(stuck_galleys),
        'homeless_employed': len(homeless_employed),
        'alerts_created': alerts_created
    }
    
    notification_data = {
        'Type': 'welfare_monitoring_summary',
        'Citizen': 'ConsiglioDeiDieci',
        'Content': f"🏛️ **Welfare Report**: {alerts_created} alerts. Hunger: {hunger_rate:.1%}, Shortages: {len(resource_shortages)}, Failures: {failure_rate:.1%}",
        'Details': json.dumps(summary),
        'CreatedAt': datetime.datetime.now(pytz.UTC).isoformat()
    }
    
    tables['notifications'].create(notification_data)
    
    log.info("Welfare monitoring complete")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor citizen welfare metrics")
    parser.add_argument("--dry-run", action="store_true", help="Run without creating alerts")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    monitor_welfare(dry_run=args.dry_run)
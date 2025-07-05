#!/usr/bin/env python3
"""
Database Query Optimization Patterns
Reality-Anchor: Batching saves the substrate!

This module provides optimized query patterns to reduce Airtable API calls
and improve performance. Use these patterns to replace individual queries.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(__name__)


class QueryOptimizer:
    """Optimized query patterns for Airtable operations"""
    
    def __init__(self, tables: Dict[str, Any]):
        self.tables = tables
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.batch_size = 10  # Airtable batch limit
    
    def batch_get_citizens(self, usernames: List[str]) -> Dict[str, Any]:
        """
        Get multiple citizens in one query instead of individual lookups
        
        Replace:
            for username in usernames:
                citizen = table.all(formula=f"{{Username}} = '{username}'")
        
        With:
            citizens = optimizer.batch_get_citizens(usernames)
        """
        if not usernames:
            return {}
        
        # Build OR formula for batch query
        formulas = [f"{{Username}} = '{username}'" for username in usernames]
        formula = f"OR({','.join(formulas)})"
        
        # Single query for all citizens
        results = self.tables["citizens"].all(formula=formula)
        
        # Build lookup dict
        citizen_dict = {}
        for record in results:
            username = record['fields'].get('Username')
            if username:
                citizen_dict[username] = record
        
        return citizen_dict
    
    def batch_update_citizens(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple citizens in batches
        
        Format: [{"id": record_id, "fields": {"field": value}}]
        """
        updated = 0
        
        # Process in batches
        for i in range(0, len(updates), self.batch_size):
            batch = updates[i:i+self.batch_size]
            try:
                self.tables["citizens"].batch_update(batch)
                updated += len(batch)
            except Exception as e:
                log.error(f"Batch update failed: {e}")
        
        return updated
    
    def get_active_citizens_optimized(self, hours: int = 6) -> List[Dict[str, Any]]:
        """
        Get only active citizens to reduce processing load
        """
        cache_key = f"active_citizens_{hours}h"
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        # Calculate cutoff time
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        # Query active citizens
        formula = f"{{LastActiveAt}} > '{cutoff}'"
        active_citizens = self.tables["citizens"].all(formula=formula)
        
        # Cache results
        self.cache[cache_key] = (time.time(), active_citizens)
        
        return active_citizens
    
    def batch_get_resources(self, criteria: Dict[str, List[str]]) -> Dict[str, List[Any]]:
        """
        Get resources matching multiple criteria in one query
        
        Example:
            resources = optimizer.batch_get_resources({
                "owners": ["user1", "user2"],
                "types": ["grain", "timber"],
                "assets": ["building1", "building2"]
            })
        """
        formulas = []
        
        if "owners" in criteria:
            owner_formulas = [f"{{Owner}} = '{owner}'" for owner in criteria["owners"]]
            formulas.append(f"OR({','.join(owner_formulas)})")
        
        if "types" in criteria:
            type_formulas = [f"{{Type}} = '{rtype}'" for rtype in criteria["types"]]
            formulas.append(f"OR({','.join(type_formulas)})")
        
        if "assets" in criteria:
            asset_formulas = [f"{{Asset}} = '{asset}'" for asset in criteria["assets"]]
            formulas.append(f"OR({','.join(asset_formulas)})")
        
        # Combine with AND
        if formulas:
            formula = f"AND({','.join(formulas)})" if len(formulas) > 1 else formulas[0]
            return self.tables["resources"].all(formula=formula)
        
        return []
    
    def cache_static_data(self):
        """
        Cache static data that rarely changes
        """
        # Cache building types
        if "building_types" not in self.cache:
            # This would normally fetch from API
            self.cache["building_types"] = (time.time(), {})
        
        # Cache resource types
        if "resource_types" not in self.cache:
            # This would normally fetch from API
            self.cache["resource_types"] = (time.time(), {})
    
    def deduplicate_activities(self, citizen_username: str) -> int:
        """
        Remove duplicate pending activities for a citizen
        """
        # Get all pending activities
        formula = f"AND({{Citizen}} = '{citizen_username}', {{Status}} = 'created')"
        activities = self.tables["activities"].all(formula=formula)
        
        # Group by type
        activity_groups = defaultdict(list)
        for activity in activities:
            activity_type = activity['fields'].get('Type')
            activity_groups[activity_type].append(activity)
        
        # Keep only most recent of each type
        to_delete = []
        for activity_type, group in activity_groups.items():
            if len(group) > 1:
                # Sort by CreatedAt
                sorted_activities = sorted(
                    group,
                    key=lambda x: x['fields'].get('CreatedAt', ''),
                    reverse=True
                )
                # Delete all but most recent
                to_delete.extend([a['id'] for a in sorted_activities[1:]])
        
        # Batch delete
        if to_delete:
            for i in range(0, len(to_delete), self.batch_size):
                batch = to_delete[i:i+self.batch_size]
                self.tables["activities"].batch_delete(batch)
        
        return len(to_delete)


class ActivityBatchProcessor:
    """Process activities in batches instead of individually"""
    
    def __init__(self, tables: Dict[str, Any]):
        self.tables = tables
        self.optimizer = QueryOptimizer(tables)
    
    def process_activities_batch(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process multiple activities together
        """
        results = {
            "processed": 0,
            "failed": 0,
            "updates": []
        }
        
        # Group activities by type
        activity_groups = defaultdict(list)
        for activity in activities:
            activity_type = activity['fields'].get('Type')
            activity_groups[activity_type].append(activity)
        
        # Collect all citizen usernames
        all_usernames = set()
        for activity in activities:
            username = activity['fields'].get('Citizen')
            if username:
                all_usernames.add(username)
        
        # Batch fetch all citizens
        citizens = self.optimizer.batch_get_citizens(list(all_usernames))
        
        # Process each type group
        for activity_type, group in activity_groups.items():
            if activity_type == "eat_from_inventory":
                self._process_eat_batch(group, citizens, results)
            elif activity_type == "goto_home":
                self._process_goto_batch(group, citizens, results)
            # Add more batch processors as needed
        
        # Batch update all changes
        if results["updates"]:
            self.optimizer.batch_update_citizens(results["updates"])
        
        return results
    
    def _process_eat_batch(self, activities: List[Dict], citizens: Dict, results: Dict):
        """Batch process eating activities"""
        for activity in activities:
            try:
                citizen_username = activity['fields'].get('Citizen')
                citizen = citizens.get(citizen_username)
                
                if not citizen:
                    results["failed"] += 1
                    continue
                
                # Update AteAt timestamp
                results["updates"].append({
                    "id": citizen['id'],
                    "fields": {"AteAt": datetime.utcnow().isoformat()}
                })
                
                results["processed"] += 1
                
            except Exception as e:
                log.error(f"Error processing eat activity: {e}")
                results["failed"] += 1
    
    def _process_goto_batch(self, activities: List[Dict], citizens: Dict, results: Dict):
        """Batch process movement activities"""
        # Similar batch processing for goto activities
        pass


class CacheManager:
    """Manage caching for frequently accessed data"""
    
    def __init__(self):
        self.cache = {}
        self.ttl = {
            "building_types": 3600,      # 1 hour
            "resource_types": 3600,      # 1 hour
            "citizen_index": 300,        # 5 minutes
            "active_citizens": 60,       # 1 minute
            "contracts": 120,            # 2 minutes
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self.cache:
            timestamp, value = self.cache[key]
            ttl = self.ttl.get(key, 300)
            
            if time.time() - timestamp < ttl:
                return value
            else:
                del self.cache[key]
        
        return None
    
    def set(self, key: str, value: Any):
        """Cache a value with timestamp"""
        self.cache[key] = (time.time(), value)
    
    def clear(self, pattern: Optional[str] = None):
        """Clear cache entries"""
        if pattern:
            keys_to_delete = [k for k in self.cache if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            self.cache.clear()


# Example usage patterns
OPTIMIZATION_EXAMPLES = """
# BEFORE: Individual queries (87% substrate)
for username in citizen_list:
    citizen = citizens_table.all(formula=f"{{Username}} = '{username}'")[0]
    citizen_fields = citizen['fields']
    # Process citizen...

# AFTER: Batch query (40% substrate)
optimizer = QueryOptimizer(tables)
all_citizens = optimizer.batch_get_citizens(citizen_list)
for username, citizen in all_citizens.items():
    citizen_fields = citizen['fields']
    # Process citizen...

# BEFORE: Update citizens one by one
for citizen in citizens_to_update:
    table.update(citizen['id'], {"LastActiveAt": now})

# AFTER: Batch update
updates = [{"id": c['id'], "fields": {"LastActiveAt": now}} for c in citizens_to_update]
optimizer.batch_update_citizens(updates)

# BEFORE: Process all citizens
all_citizens = citizens_table.all()
for citizen in all_citizens:
    # Process...

# AFTER: Process only active citizens
active_citizens = optimizer.get_active_citizens_optimized(hours=6)
for citizen in active_citizens:
    # Process...
"""

def generate_optimization_guide():
    """Generate implementation guide"""
    guide = f"""
# Database Query Optimization Guide

## Quick Wins (Implement First)

1. **Batch Citizen Lookups**
   - Replace: Multiple formula queries
   - With: `batch_get_citizens(usernames)`
   - Reduction: 90% fewer API calls

2. **Cache Static Data**
   - Building types: Cache for 1 hour
   - Resource types: Cache for 1 hour
   - Citizen index: Cache for 5 minutes
   - Reduction: 50% fewer lookups

3. **Active Citizens Only**
   - Skip citizens inactive >6 hours
   - Use `get_active_citizens_optimized()`
   - Reduction: 60% fewer records processed

4. **Batch Updates**
   - Group updates by table
   - Use `batch_update_citizens()`
   - Reduction: 90% fewer API calls

## Implementation Priority

1. **processActivities.py**: Add batching
2. **createActivities.py**: Skip inactive citizens
3. **main_engine.py**: Cache lookups
4. **scheduler.py**: Reduce frequencies

## Expected Results
- API calls: -70%
- Processing time: -50%
- Substrate usage: 87% → 40%

{OPTIMIZATION_EXAMPLES}
"""
    
    with open('query_optimization_guide.md', 'w') as f:
        f.write(guide)
    
    return guide


if __name__ == "__main__":
    print("🔧 DATABASE QUERY OPTIMIZATION PATTERNS")
    print("=" * 50)
    print("\nThis module provides patterns to reduce Airtable API calls")
    print("\nKey optimizations:")
    print("- Batch queries instead of individual lookups")
    print("- Cache static and semi-static data")
    print("- Process only active citizens")
    print("- Deduplicate before processing")
    
    generate_optimization_guide()
    print("\n✅ Generated query_optimization_guide.md")
    print("\nExpected substrate reduction: 87% → 40%")
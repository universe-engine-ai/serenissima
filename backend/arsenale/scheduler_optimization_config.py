#!/usr/bin/env python3
"""
Scheduler Optimization Configurations
Reality-Anchor: Reducing the heartbeat to save the body!

This file provides optimized scheduler configurations to reduce substrate load.
Choose based on crisis severity:
- NORMAL: Current config (87% substrate usage)
- OPTIMIZED: 50% reduction in task frequency
- EMERGENCY: 70% reduction for crisis situations
"""

# CURRENT CONFIGURATION (87% substrate usage)
NORMAL_CONFIG = {
    "frequent_tasks": [
        {"minute_mod": 0, "script": "engine/createActivities.py", "interval_minutes": 5},
        {"minute_mod": 1, "script": "engine/processActivities.py", "interval_minutes": 5},
        {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "interval_minutes": 15},
        {"minute_mod": 4, "script": "forge-communication/forge_message_processor.py", "interval_minutes": 5},
    ],
    "hourly_tasks": {
        "emergency_food": ":15",
        "welfare_monitor": ":30",
        "other_tasks": "every hour"
    }
}

# OPTIMIZED CONFIGURATION (~50% substrate usage)
OPTIMIZED_CONFIG = {
    "frequent_tasks": [
        # Double intervals for main processors
        {"minute_mod": 0, "script": "engine/createActivities.py", "interval_minutes": 10},
        {"minute_mod": 2, "script": "engine/processActivities.py", "interval_minutes": 10},
        # Reduce delivery retries
        {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "interval_minutes": 30},
        # Slow forge communication
        {"minute_mod": 4, "script": "forge-communication/forge_message_processor.py", "interval_minutes": 15},
    ],
    "hourly_tasks": {
        # Run emergency food less frequently
        "emergency_food": "every 2 hours at :15",
        "welfare_monitor": "every 2 hours at :30",
        "other_tasks": "stagger throughout day"
    },
    "notes": """
    Optimizations:
    - Main activity loops run every 10 min instead of 5
    - Delivery retries check every 30 min instead of 15
    - Forge communication every 15 min instead of 5
    - Welfare systems run every 2 hours
    - Expected 40-50% substrate reduction
    """
}

# EMERGENCY CONFIGURATION (~30% substrate usage)
EMERGENCY_CONFIG = {
    "frequent_tasks": [
        # Minimal activity processing
        {"minute_mod": 0, "script": "engine/createActivities.py", "interval_minutes": 20},
        {"minute_mod": 5, "script": "engine/processActivities.py", "interval_minutes": 20},
        # Disable non-critical tasks
        # {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "interval_minutes": 60},
        {"minute_mod": 10, "script": "forge-communication/forge_message_processor.py", "interval_minutes": 30},
    ],
    "hourly_tasks": {
        # Only critical welfare
        "emergency_food": "every 4 hours at :15",
        "welfare_monitor": "disabled",
        "other_tasks": "disabled except critical"
    },
    "notes": """
    Emergency Mode:
    - Activity processing every 20 minutes
    - Delivery retries disabled
    - Forge communication every 30 minutes
    - Only emergency food distribution active
    - Expected 70% substrate reduction
    - USE ONLY DURING CRISIS
    """
}

# Implementation guide for scheduler.py
IMPLEMENTATION_GUIDE = """
# How to Apply Optimization to scheduler.py

## For OPTIMIZED_CONFIG (Recommended):

Replace the frequent_tasks_definitions with:

```python
frequent_tasks_definitions = [
    {"minute_mod": 0, "script": "engine/createActivities.py", "name": "Create activities", "interval_minutes": 10},
    {"minute_mod": 2, "script": "engine/processActivities.py", "name": "Process activities", "interval_minutes": 10},
    {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "name": "Delivery retry handler", "interval_minutes": 30},
    {"minute_mod": 4, "script": "forge-communication/forge_message_processor.py", "name": "Process Forge messages", "interval_minutes": 15},
]
```

And modify hourly tasks to run less frequently:
- Change emergency food distribution to run every 2 hours
- Change welfare monitoring to run every 2 hours
- Consider disabling non-critical hourly tasks

## For EMERGENCY_CONFIG (Crisis Only):

Use the emergency frequent_tasks_definitions and disable most hourly tasks.
Monitor closely and return to optimized config once crisis passes.

## Additional Optimizations:

1. Add activity filtering in createActivities.py:
   - Skip citizens who are sleeping (night time)
   - Skip citizens who already have pending activities
   - Skip citizens who haven't moved in 6+ hours

2. Batch process in processActivities.py:
   - Process activities in batches of 50
   - Use concurrent processing where safe
   - Cache building and resource lookups

3. Optimize database queries:
   - Create lookup indices for common queries
   - Cache static data (building types, resource types)
   - Use batch updates instead of individual calls
"""

def generate_scheduler_patch():
    """Generate a patch file for scheduler.py"""
    patch = """--- scheduler.py.original
+++ scheduler.py.optimized
@@ -150,10 +150,10 @@
 # Define frequent tasks with their minute modulo and interval
 frequent_tasks_definitions = [
-    {"minute_mod": 0, "script": "engine/createActivities.py", "name": "Create activities", "interval_minutes": 5},
-    {"minute_mod": 1, "script": "engine/processActivities.py", "name": "Process activities", "interval_minutes": 5},
-    {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "name": "Delivery retry handler", "interval_minutes": 15},
-    {"minute_mod": 4, "script": "forge-communication/forge_message_processor.py", "name": "Process Forge messages", "interval_minutes": 5},
+    {"minute_mod": 0, "script": "engine/createActivities.py", "name": "Create activities", "interval_minutes": 10},
+    {"minute_mod": 2, "script": "engine/processActivities.py", "name": "Process activities", "interval_minutes": 10},
+    {"minute_mod": 3, "script": "engine/delivery_retry_handler.py", "name": "Delivery retry handler", "interval_minutes": 30},
+    {"minute_mod": 4, "script": "forge-communication/forge_message_processor.py", "name": "Process Forge messages", "interval_minutes": 15},
 ]
 
 # Schedule hourly tasks with reduced frequency
@@ -165,8 +165,10 @@
         tasks.append(task_entry)
     
     # Emergency Food Distribution - Every 2 hours instead of every hour
-    for hour in range(24):
+    for hour in range(0, 24, 2):  # Every 2 hours
         task_name = f"Emergency Food Distribution ({hour:02d}:15 VT)"
         tasks.append({
"""
    
    with open('scheduler_optimization.patch', 'w') as f:
        f.write(patch)
    
    return patch

def estimate_substrate_reduction(config_name):
    """Estimate substrate usage reduction for each config"""
    reductions = {
        "NORMAL": 0,
        "OPTIMIZED": 47,  # ~50% reduction
        "EMERGENCY": 70   # 70% reduction
    }
    
    current_usage = 87
    reduction = reductions.get(config_name, 0)
    new_usage = current_usage * (1 - reduction/100)
    
    return {
        "config": config_name,
        "current_substrate": current_usage,
        "reduction_percent": reduction,
        "new_substrate": new_usage,
        "sustainable": new_usage < 60
    }

if __name__ == "__main__":
    print("🔧 SCHEDULER OPTIMIZATION CONFIGURATIONS")
    print("=" * 50)
    
    for config in ["NORMAL", "OPTIMIZED", "EMERGENCY"]:
        result = estimate_substrate_reduction(config)
        print(f"\n{config} Configuration:")
        print(f"  Current Usage: {result['current_substrate']}%")
        print(f"  Reduction: {result['reduction_percent']}%")
        print(f"  New Usage: {result['new_substrate']:.1f}%")
        print(f"  Sustainable: {'✅ YES' if result['sustainable'] else '❌ NO'}")
    
    print("\n" + "=" * 50)
    print("\n📋 IMPLEMENTATION GUIDE:")
    print(IMPLEMENTATION_GUIDE)
    
    # Generate patch file
    generate_scheduler_patch()
    print("\n✅ Generated scheduler_optimization.patch")
    print("\nTo apply: patch scheduler.py < scheduler_optimization.patch")
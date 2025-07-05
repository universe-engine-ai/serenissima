# backend/engine/config/constants.py

"""
Centralized constants for the citizen activity system.
These values were previously scattered throughout the codebase.
"""

# Time-related constants
IDLE_ACTIVITY_DURATION_HOURS = 0.1667  # 10 minutes (1/6 of an hour)
BUSINESS_CHECK_INTERVAL_HOURS = 24
CONSTRUCTION_COMPLETION_CHECK_HOURS = 4

# Distance and location constants
AT_LOCATION_THRESHOLD = 10  # meters - consider "at location" if within this distance
SOCIAL_INTERACTION_RADIUS = 20  # meters - for spreading rumors, etc.
CONSTRUCTION_CONTRACT_SEARCH_RADIUS_METERS = 500
PORTER_TASK_SEARCH_RADIUS = 1000

# Inventory and storage constants
STORAGE_FULL_THRESHOLD = 0.8  # 80% of carry capacity
MINIMUM_LOAD_FOR_DEPOSIT = 5.0  # Don't bother depositing less than this
CITIZEN_CARRY_CAPACITY = 50.0  # Default carry capacity

# Economic constants
MIN_CONSTRUCTION_BUDGET = 10000  # Minimum ducats to start construction
FOOD_SHOPPING_COST_ESTIMATE = 50  # Estimated cost for food shopping
INN_DRINK_COST = 10
PUBLIC_BATH_COST = 5
THEATER_TICKET_COST = 20

# Social class values (for various calculations)
SOCIAL_CLASS_VALUE = {
    "Nobili": 4,
    "Cittadini": 3,
    "Popolani": 2,
    "Facchini": 1,
    "Forestieri": 2,
    "Artisti": 2,
    "Clero": 3,
    "Scientisti": 3
}

# Work schedules (if not defined in building_type_defs)
DEFAULT_WORK_START_HOUR = 8
DEFAULT_WORK_END_HOUR = 18
NIGHT_END_HOUR_FOR_STAY = 6

# Guild IDs
PORTER_GUILD_ID = "guild_porter_001"

# Activity priorities (for reference)
PRIORITY_CRITICAL_LEAVE_VENICE = 1
PRIORITY_CRITICAL_EAT_INVENTORY = 2
PRIORITY_CRITICAL_EAT_HOME = 3
PRIORITY_CRITICAL_EMERGENCY_FISH = 4
PRIORITY_CRITICAL_SHOP_FOOD = 5
PRIORITY_CRITICAL_EAT_TAVERN = 6
PRIORITY_CRITICAL_DEPOSIT_INVENTORY = 10
PRIORITY_CRITICAL_NIGHT_SHELTER = 15

PRIORITY_WORK_CHECK_BUSINESS = 20
PRIORITY_WORK_ARTISTI_ART = 25
PRIORITY_WORK_CONSTRUCTION_PRO = 30
PRIORITY_WORK_PRODUCTION = 31
PRIORITY_WORK_FISHING_PRO = 32
PRIORITY_WORK_CONSTRUCTION_SELF = 33
PRIORITY_WORK_PUBLIC_DOCK = 35
PRIORITY_WORK_FORESTIERI = 40
PRIORITY_WORK_PORTER = 60
PRIORITY_WORK_GOTO = 70

PRIORITY_MGMT_BUILDING_PROJECT = 80
PRIORITY_MGMT_SECURE_WAREHOUSE = 81
PRIORITY_MGMT_STORAGE_OFFERS = 82

# Forestieri-specific constants
FORESTIERI_MIN_STAY_DAYS = 3
FORESTIERI_MAX_STAY_DAYS = 14
FORESTIERI_MIN_PROFIT_TARGET = 500
# Airtable Schema Documentation

## CITIZENS Table
Primary table for all citizens (AI and human)

Key fields:
- `citizenId`: Unique identifier
- `firstName`, `lastName`: Name
- `socialClass`: Nobles/Cittadini/Popolani
- `ducats`: Current wealth
- `position`: {lat, lng} coordinates
- `isAI`: Boolean flag
- `home`: Building ID where they live
- `workplace`: Building ID where they work
- `dailyIncome`: Ducats earned per day
- `influence`: Social/political power
- `personality`: Core traits (for AI)
- `preferences`: JSON settings

## BUILDINGS Table
All structures in Venice

Key fields:
- `buildingId`: Unique identifier
- `buildingType`: shop/workshop/public_dock/etc
- `owner`: citizenId of owner
- `position`: {lat, lng} coordinates
- `maintenanceCost`: Daily upkeep
- `status`: operational/damaged/abandoned
- `productType`: What it produces (if any)
- `employees`: Array of citizenIds

## ACTIVITIES Table
Action queue and history

Key fields:
- `activityId`: Unique identifier
- `activityType`: move/buy/sell/work/etc
- `citizenId`: Who's doing it
- `status`: pending/processing/completed/failed
- `startTime`, `endTime`: Timestamps
- `data`: JSON with activity-specific data
- `chainedFrom`: Previous activity ID

## CONTRACTS Table
Economic agreements

Key fields:
- `contractId`: Unique identifier
- `seller`, `buyer`: citizenIds
- `resource`: What's being traded
- `quantity`: Amount
- `pricePerUnit`: Ducats
- `status`: active/completed/cancelled
- `createdAt`: Timestamp

## RESOURCES Table
Physical goods with location

Key fields:
- `resourceId`: Unique identifier
- `resourceType`: grain/wood/glass/etc
- `owner`: citizenId or buildingId
- `quantity`: Amount
- `position`: {lat, lng} coordinates
- `quality`: 1-100 scale

## RELATIONSHIPS Table
Social connections between citizens

Key fields:
- `relationshipId`: Unique identifier
- `fromCitizen`, `toCitizen`: citizenIds
- `trustLevel`: -100 to 100
- `economicValue`: Trade volume
- `lastInteraction`: Timestamp

## MESSAGES Table
Communications between citizens

Key fields:
- `messageId`: Unique identifier
- `fromCitizen`, `toCitizen`: citizenIds
- `message`: Text content
- `sentiment`: Analyzed emotion
- `topic`: What it's about
- `timestamp`: When sent

## Query Patterns
```python
# Find struggling citizens
citizens = airtable.get_all('CITIZENS', 
    formula="AND({ducats} < 100, {isAI} = TRUE())")

# Get recent messages
messages = airtable.get_all('MESSAGES',
    formula="DATETIME_DIFF(NOW(), {timestamp}, 'hours') < 24")

# Find idle buildings
buildings = airtable.get_all('BUILDINGS',
    formula="AND({status} = 'operational', {employees} = '')")
```
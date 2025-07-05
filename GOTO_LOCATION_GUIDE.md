# Goto Location Guide - Moving Citizens Around Venice

## Overview

Citizens in La Serenissima can move between buildings using the `goto_location` activity type. This guide explains how to create movement activities for citizens through the API.

## Quick Start

To move a citizen to a building, send a POST request to `/api/activities/try-create`:

```json
{
  "citizenUsername": "your_citizen_username",
  "activityType": "goto_location",
  "activityParameters": {
    "targetBuildingId": "rialto_bridge",
    "notes": "Visiting the famous bridge"
  }
}
```

## API Endpoint

**POST** `/api/activities/try-create`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `citizenUsername` | string | Yes | Username of the citizen who will move |
| `activityType` | string | Yes | Must be `"goto_location"` |
| `activityParameters` | object | Yes | Movement parameters (see below) |

### Activity Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `targetBuildingId` | string | Yes* | BuildingId of the destination |
| `toPosition` | object | Yes* | Alternative: Direct coordinates `{lat, lng}` |
| `fromBuildingId` | string | No | Starting building (defaults to current position) |
| `notes` | string | No | Simple text note about the movement |
| `details` | object | No | Structured data for chaining activities |

*Either `targetBuildingId` or `toPosition` is required

## Movement Mechanics

### Pathfinding
- The system automatically calculates the optimal path between buildings
- Venice's canals, bridges, and walkways are considered
- Travel time depends on distance and available transportation

### Transportation
- Citizens may walk or use gondolas depending on the route
- Gondola transport requires finding an available gondolier
- Travel duration varies from minutes to hours

### Current Position
- If no `fromBuildingId` is specified, the citizen's current position is used
- Citizens must have a valid position to create movement activities

## Examples

### 1. Simple Movement
Move to a specific building:

```javascript
const moveToChurch = {
  "citizenUsername": "marco_polo",
  "activityType": "goto_location",
  "activityParameters": {
    "targetBuildingId": "san_marco_basilica",
    "notes": "Attending morning mass"
  }
}
```

### 2. Movement with Coordinates
Move to specific coordinates (system finds nearest building):

```javascript
const moveToLocation = {
  "citizenUsername": "lucia_medici",
  "activityType": "goto_location", 
  "activityParameters": {
    "toPosition": {
      "lat": 45.4342,
      "lng": 12.3388
    },
    "notes": "Exploring the eastern district"
  }
}
```

### 3. Chained Activities
Move somewhere and then perform another action:

```javascript
const moveAndEat = {
  "citizenUsername": "giovanni_smith",
  "activityType": "goto_location",
  "activityParameters": {
    "targetBuildingId": "osteria_del_ponte",
    "notes": "Going to tavern for lunch",
    "details": {
      "purpose": "dining",
      "nextActivityType": "eat",
      "nextActivityParameters": {
        "strategy": "tavern"
      }
    }
  }
}
```

### 4. Social Meeting
Move to meet someone:

```javascript
const meetFriend = {
  "citizenUsername": "antonio_rossi",
  "activityType": "goto_location",
  "activityParameters": {
    "targetBuildingId": "piazza_san_marco",
    "notes": "Meeting Francesco at the square",
    "details": {
      "purpose": "social_meeting",
      "meetingWith": "francesco_bianchi",
      "nextActivityType": "send_message",
      "nextActivityParameters": {
        "recipientUsername": "francesco_bianchi",
        "message": "I've arrived at the square!"
      }
    }
  }
}
```

## Finding Building IDs

To get available buildings and their IDs:

**GET** `/api/buildings`

This returns all buildings with their:
- `buildingId` - The ID to use for movement
- `name` - Human-readable name
- `buildingType` - Type (church, tavern, market, etc.)
- `position` - Coordinates
- `isPublic` - Whether the building is publicly accessible

### Common Building Types
- **Churches**: For prayer and social gatherings
- **Taverns**: For eating and drinking
- **Markets**: For trading goods
- **Plazas**: Public squares for meetings
- **Bridges**: Key transit points
- **Docks**: For water transportation

## Response Format

### Success Response
```json
{
  "success": true,
  "message": "Activity created successfully",
  "activity": {
    "id": "rec123456",
    "activityId": "goto_location_marco_polo_a1b2c3d4",
    "type": "goto_location",
    "status": "pending",
    "citizen": "marco_polo",
    "startDate": "2024-01-15T10:00:00Z",
    "endDate": "2024-01-15T10:30:00Z",
    "fromBuilding": "home_marco_polo",
    "toBuilding": "san_marco_basilica",
    "path": [...],  // Array of waypoints
    "title": "Traveling to Basilica di San Marco",
    "description": "marco_polo is traveling to Basilica di San Marco"
  }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Pathfinding failed - no route available",
  "error": "NO_PATH_FOUND"
}
```

## Common Use Cases

### 1. Going Home
```javascript
{
  "citizenUsername": "citizen_name",
  "activityType": "goto_location",
  "activityParameters": {
    "targetBuildingId": "home_citizen_name",  // Home buildings follow this pattern
    "notes": "Returning home for the evening"
  }
}
```

### 2. Going to Work
```javascript
{
  "citizenUsername": "worker_name",
  "activityType": "goto_location",
  "activityParameters": {
    "targetBuildingId": "workplace_building_id",
    "notes": "Going to work",
    "details": {
      "nextActivityType": "goto_work"
    }
  }
}
```

### 3. Emergency Movement
```javascript
{
  "citizenUsername": "citizen_name",
  "activityType": "goto_location",
  "activityParameters": {
    "targetBuildingId": "nearest_safe_building",
    "notes": "Seeking shelter from storm",
    "details": {
      "urgency": "high",
      "reason": "weather_emergency"
    }
  }
}
```

## Best Practices

1. **Always specify a reason**: Use the `notes` field to explain why the citizen is moving
2. **Check building accessibility**: Ensure the target building is public or owned by the citizen
3. **Consider travel time**: Movement takes time; citizens can't teleport
4. **Chain related activities**: Use the `details` field to plan what happens after arrival
5. **Handle failures gracefully**: Pathfinding can fail if routes are blocked

## Troubleshooting

### "Missing targetBuildingId"
- Ensure you're providing either `targetBuildingId` or `toPosition`
- Check that the building ID exists in the system

### "Pathfinding failed"
- The destination might be unreachable from the current position
- Check if the citizen has a valid current position
- Verify the building exists and is accessible

### "Citizen not found"
- Verify the username is correct
- Check that the citizen exists in the system

### Activity created but citizen not moving
- Activities are processed every 5 minutes
- Check the activity status via `/api/activities?citizen=username`
- Ensure the activity hasn't failed during processing

## Integration Example

Here's a complete example using JavaScript/fetch:

```javascript
async function moveCitizen(username, destinationId, reason) {
  const response = await fetch('https://serenissima.ai/api/activities/try-create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      citizenUsername: username,
      activityType: 'goto_location',
      activityParameters: {
        targetBuildingId: destinationId,
        notes: reason
      }
    })
  });

  const result = await response.json();
  
  if (result.success) {
    console.log(`${username} is now traveling to ${destinationId}`);
    console.log(`Activity ID: ${result.activity.id}`);
    console.log(`Arrival time: ${result.activity.endDate}`);
  } else {
    console.error(`Movement failed: ${result.message}`);
  }
  
  return result;
}

// Usage
moveCitizen('marco_polo', 'rialto_bridge', 'Meeting merchants for trade discussions');
```

## Advanced Features

### Custom Pathfinding
While not exposed through the public API, the system supports:
- Avoiding certain areas
- Preferring walking vs. gondola routes
- Time-based route optimization

### Activity Priorities
Movement activities have a default priority of 50, which can be overridden in special circumstances.

### Transporter Assignment
The system automatically finds available gondoliers when water routes are optimal.

## Related Activities

After movement, citizens commonly perform:
- `eat` - Find food at destination
- `goto_work` - Start working at business
- `send_message` - Communicate with others
- `pray` - At churches
- `drink_at_inn` - At taverns
- `manage_public_sell_contract` - At markets

---

*Last updated: January 2025*
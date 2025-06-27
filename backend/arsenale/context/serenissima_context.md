# La Serenissima Technical Context

## Core Principles
- **Unified citizen model**: AI and humans follow identical rules
- **Closed-loop economy**: No money creation, only circulation
- **Cultural transmission**: Books/art permanently change readers/viewers
- **Identity formation**: Economic choices create persistent identity

## Key Systems

### Activity System
- All citizen actions go through unified activity pipeline
- Activities created via `/api/activities/try-create`
- Processed every 5 minutes by `backend/engine/processActivities.py`
- Modular handlers in `backend/engine/handlers/`

### Economic System
- Closed-loop: Total ducats remain constant
- Daily processes: maintenance, wages, rent, treasury
- Resources have location and ownership
- Contracts enable citizen-to-citizen trade

### AI Architecture
- **Layer 1**: Rule-based behaviors (basic needs)
- **Layer 2**: LLM integration (deepseek-r1, 8B params)
- **Layer 3**: KinOS memory (persistent experiences)

### Cultural Systems
- Books contain ideas that spread through reading
- Art influences viewers based on aesthetic value
- Relationships form through economic interaction
- Social classes (Nobles, Cittadini, Popolani) have different permissions

## Database Schema
- **CITIZENS**: Core identity and state
- **BUILDINGS**: Structures and operations
- **ACTIVITIES**: Action queue and history
- **CONTRACTS**: Economic agreements
- **RESOURCES**: Physical goods
- **RELATIONSHIPS**: Social connections
- **BOOKS**: Cultural artifacts
- **ART**: Aesthetic creations

## API Access
- Frontend API: `http://172.17.0.1:3000/api`
- Backend API: `http://localhost:8000`
- All endpoints support both AI and human citizens

## Development Patterns
- Always maintain unified citizen model
- Economic changes must preserve closed-loop
- Cultural transmission must be permanent
- Test with both AI and human citizens

## Current State Metrics
- 119 AI citizens active
- ~500K ducats in circulation
- 4.06 money velocity
- 90.92% AI identity persistence
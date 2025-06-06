# Relevancy Types in La Serenissima

This document provides a comprehensive overview of the different types of relevancies calculated in the game system, their significance, and how they influence citizen decision-making.

## Overview

Relevancies represent the importance or significance of various game elements (buildings, citizens, resources, etc.) to a specific citizen. They are calculated based on numerous factors including proximity, economic relationships, social connections, and strategic value.

## Core Relevancy Types

### Land Proximity Relevancy

As detailed in the main relevancy-system.md document, this calculates how relevant unowned lands are to an AI based on:
- **Geographic Proximity**: How close the land is to the AI's existing properties
- **Connectivity**: Whether the land is connected to the AI's existing properties via bridges
- **Strategic Value**: The potential value of the land based on its location and features

### Land Domination Relevancy

Identifies the most significant landowners in Venice based on:
- **Land Count**: Number of lands owned by each citizen (60% weight)
- **Building Points**: Total building points across all owned lands (40% weight)
- **Normalization**: Scores are normalized against the citizen with the most lands/points

### Building Operator Relationship Relevancy

Identifies relationships where a building's `Owner` is different from its `RunBy` (operator):
- Creates bidirectional relevancies between owners and operators
- Helps citizens understand their business relationships network
- Provides context for potential negotiations or collaborations

### Building Occupant Relationship Relevancy

Identifies relationships between a building's `RunBy` (operator/employer/landlord) and its `Occupant` (employee/renter):
- For businesses: Creates employer-employee relevancies
- For homes: Creates landlord-tenant relevancies
- Helps citizens understand their social and economic networks

### Same Land Neighbor Relevancy

Identifies communities of residents living on the same `LandId` (land or distinct land parcel):
- Fosters a sense of local community
- Highlights shared geographical context
- Creates group relevancies for all citizens residing on the same land

### Guild Member Relevancy

Identifies communities of players belonging to the same guild:
- Fosters collaboration and highlights shared affiliations
- Creates group relevancies for all members of a guild
- Provides context for guild-based activities and relationships

## Relevancy Calculation Factors

Relevancies are calculated using various factors including:

1. **Distance**: Physical proximity in the game world
2. **Economic Value**: Potential financial benefit
3. **Strategic Alignment**: Alignment with the citizen's long-term goals
4. **Social Class Compatibility**: Appropriateness based on social class
5. **Resource Requirements**: Match with the citizen's resource needs
6. **Time Horizon**: Short-term vs. long-term significance

## Relevancy Scores

Relevancy scores typically range from 0-100, with higher scores indicating greater significance:

- **0-25**: Low relevance
- **26-50**: Moderate relevance
- **51-75**: High relevance
- **76-100**: Critical relevance

## Data Structure

Each relevancy record contains:
- **Score**: Numerical relevancy score (0-100)
- **Asset**: ID of the relevant asset
- **AssetType**: Type of asset (land, building, resource, citizen, guild)
- **Category**: Category of relevancy (proximity, economic, strategic, etc.)
- **Type**: Specific type of relevancy (connected, geographic, etc.)
- **TargetCitizen**: Owner of the closest related asset or target of the relevancy
- **RelevantToCitizen**: Citizen for whom this relevancy is calculated
- **TimeHorizon**: When the citizen should consider acting (short, medium, long)
- **Title**: Short description of the relevancy
- **Description**: Detailed explanation of why this asset is relevant
- **Status**: Current status of the relevancy (high, medium, low)

## Implementation

Relevancies are calculated by the backend system (see `backend/relevancies/calculateRelevancies.py` and `backend/relevancies/calculateSpecificRelevancy.py`) and are displayed to players through various UI components (see `components/UI/CitizenRelevanciesList.tsx` and `components/PolygonViewer/BuildingDetails/BuildingRelevanciesList.tsx`).

## Using Relevancies

For AI citizens, relevancies drive decision-making through the KinOS system, helping prioritize activities and strategic planning. For human players, relevancies serve as guidance to help identify valuable opportunities and strategic considerations.

## Related Documentation

- [Relevancy System Overview](relevancy-system.md)
- [AI System Documentation](ais.md)
- [Citizen Activities](activities.md)

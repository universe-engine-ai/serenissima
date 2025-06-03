# API Endpoints Reference

## Land and Property Endpoints
- `/api/lands` - Query land parcels with filters like `Owner` and `BuildingPointsCount[gt]`
- `/api/building-types` - Get information about available building types
- `/api/buildings` - Query buildings with filters like `Owner`
- `/api/building-data/[type]` - Get detailed information about a specific building type
- `/api/building-resources/[buildingId]` - Get resources associated with a specific building
- `/api/bridges/[buildingId]/orient` - Manage bridge orientation (PATCH method)
- `/api/water-points` - Access water transportation points

## Economic and Contract Endpoints
- `/api/contracts` - Query contracts with filters like `Type` and `Status`
- `/api/economy` - Get overall economic information
- `/api/resource-types` - Get information about available resource types
- `/api/transaction/land/[landId]` - Handle land transactions
- `/api/transactions/land-offers/[landId]` - Manage offers on land parcels

## Citizen and Social Endpoints
- `/api/citizens/[username]` - Get information about a specific citizen
- `/api/citizens/[username]/transports` - Get transportation options for a citizen
- `/api/citizens/wallet/[walletAddress]` - Get citizen information by wallet address
- `/api/fetch-coat-of-arms` - Get coat of arms images
- `/api/get-land-owners` - Get information about land owners
- `/api/get-public-builders` - Get information about public builders
- `/api/guild-members/[guildId]` - Get members of a specific guild

## Problem Management
- `/api/problems` - Query problems with filters like `Citizen` and `Status`

## Transport System
- `/api/transport/debug` - Debug transportation system
- `/api/docks` - Access dock information

## Key Query Parameters
- `Owner`: Filter by owner (use `"null"` for unowned)
- `Status`: Filter by status (e.g., `"active"`, `"available"`)
- `Type`: Filter by type (e.g., `"land_sale"`, `"public_sell"`)
- `BuildingPointsCount[gt]`: Filter lands with more than specified building points

## Last Updated: 2025-06-03

# Venetian Property Market Analysis

## Market Overview
- Property ownership appears to be a significant source of wealth and influence in Venice
- Rental rates can be substantial (e.g., 1,365 ducats daily for a single building)
- Property owners have significant control over pricing (observed sudden increase from 0 to 1,365 ducats)

## Land Acquisition Process
- Available land parcels can be identified through `/api/lands` endpoint with `Owner: null` filter
- Land with building potential is identified by `BuildingPointsCount[gt]: 0` parameter
- Land sale contracts can be viewed through `/api/contracts` with `Type: land_sale` filter

## Building Construction
- Buildings require land with available building points
- Different building types serve different functions (residential, commercial, industrial)
- Building types and their requirements can be queried through `/api/building-types`

## Property Economics
- Buildings generate income through rent (residential) or business operations
- Property owners must pay maintenance costs
- Land ownership may come with tax obligations
- Location significantly impacts property value and income potential

## Strategic Locations
- Proximity to canals and docks appears valuable for trade-focused operations
- Commercial districts likely command higher rents but offer better business opportunities
- Different neighborhoods may have different social class associations

## Regulatory Considerations
- Building construction likely requires permits or approval
- Certain activities may be restricted in specific areas
- Forestieri (foreigners) may face additional restrictions on property ownership

## Current Opportunities
- Need to identify unowned land parcels with building potential
- Focus on locations suitable for maritime trade operations
- Consider proximity to existing transportation infrastructure

## Last Updated: 2025-06-03

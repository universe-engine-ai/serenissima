# Market System Analysis

## Overview
The market system in La Serenissima facilitates resource trading and price discovery. Based on analysis of `managepublicsalesandprices.py` and `paystoragecontracts.py`, I've identified key insights about how the market functions and how it can be leveraged for economic advantage.

## Public Sales Mechanics

### Public Sales Contract System
From `managepublicsalesandprices.py`:
1. AI citizens analyze their buildings and the resources they can sell
2. They compare current prices to market averages and import prices
3. They make strategic decisions about which resources to sell and at what price
4. Contracts are created or updated with deterministic ContractIds
5. Existing contracts can be ended if no longer strategic

### Key Components
- Each building can sell specific resources based on its type
- Prices are influenced by global and local market averages
- AI citizens consider their own resource stockpiles when setting amounts
- Contracts have a standard duration (47 hours)

### Strategic Pricing Factors
- Import prices serve as a baseline (often 1.2x to 1.5x import price is recommended)
- Global average sell prices indicate market conditions
- Land-specific average prices show local market conditions
- Current prices in the building provide historical context

## Storage Contract Mechanics

### Storage Payment Process
From `paystoragecontracts.py`:
1. The system identifies active 'storage_query' contracts
2. For each contract, it transfers the daily payment from buyer to seller
3. Payment amount = target_amount * price_per_resource_daily
4. Transaction records are created for each payment
5. Notifications are sent to both parties if issues occur

### Key Components
- Contracts are processed if not paid in the last 23 hours
- Payments are skipped if buyers have insufficient funds
- Detailed transaction records track all payments
- Admin summaries provide oversight of the process

## AI Market Behavior

### How AI Citizens Manage Sales
Based on `managepublicsalesandprices.py`, AI merchants:
1. Identify resources their buildings can sell
2. Analyze market prices and their own inventory
3. Consider relevancies and problems that might affect strategy
4. Make decisions about creating, updating, or ending sales contracts

### Decision Factors for AI Merchants
- Resource type and category
- Current market prices (global and local)
- Import prices for the resource
- Building type and production capabilities
- Current inventory levels
- Existing contracts and their performance

### Optimization Opportunities
As a merchant, I can:
1. Set competitive prices that maximize profit while ensuring sales
2. Adjust prices based on market conditions and competition
3. Focus on high-margin resources for my building types
4. Strategically end contracts for resources needed internally

## Implementation Details

### Contract Management Process
- AI citizens use the Kinos Engine to make sales and pricing decisions
- The system provides comprehensive data about:
  - Building capabilities and sellable resources
  - Current market prices and trends
  - Resource ownership and inventory
  - Existing contracts and their terms
- Decisions are implemented through deterministic ContractId generation

### Technical Constraints
- Public sell contracts use a specific format: `contract-public-sell-{SELLER_USERNAME}-{SELLER_BUILDING_ID}-{RESOURCE_TYPE}`
- This ensures one active contract per resource, per building, per seller
- Contract duration is standardized at 47 hours
- Target amounts are set to 0.0 in the actual implementation

## Strategic Recommendations
1. **Price Optimization**: Regularly analyze market prices to set optimal selling prices
2. **Resource Focus**: Identify high-margin resources for each building type
3. **Market Monitoring**: Track price trends to anticipate market changes
4. **Contract Management**: Actively manage contracts based on changing conditions
5. **Storage Utilization**: Consider both buying and selling storage capacity based on needs

## Last Updated: June 5, 2025

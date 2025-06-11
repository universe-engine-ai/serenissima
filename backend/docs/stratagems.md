# Stratagem System

The Stratagem System allows players (or AI citizens) to enact high-level strategies that influence the game world and its mechanics over a period of time. Unlike discrete actions or standard activities, stratagems represent broader plans with potentially ongoing effects.

## Overview

-   **Initiation**: Stratagems are typically initiated via an API call (e.g., `POST /api/stratagems/try-create`).
-   **Creation**: A dedicated "Stratagem Creator" Python script (located in `backend/engine/stratagem_creators/`) validates the request and creates an Airtable record in the `STRATAGEMS` table.
-   **Processing**: The `backend/engine/processStratagems.py` script runs periodically. It fetches active stratagems and calls their corresponding "Stratagem Processor" (located in `backend/engine/stratagem_processors/`).
-   **Effects**: Processors implement the logic of the stratagem, which might involve modifying game data (e.g., prices, relationships), creating notifications, or influencing other game systems.
-   **Lifecycle**: Stratagems have a status (`planned`, `active`, `executed`, `failed`, `expired`, `cancelled`) and can have an expiration time (`ExpiresAt`).

## Stratagem Table (`STRATAGEMS`)

Refer to `backend/docs/airtable_schema.md` for the detailed structure of the `STRATAGEMS` table. Key fields include:
-   `StratagemId`
-   `Type` (e.g., "undercut")
-   `Variant` (e.g., "Mild", "Standard", "Aggressive")
-   `ExecutedBy` (Citizen Username)
-   `TargetCitizen`, `TargetBuilding`, `TargetResourceType`
-   `Status`, `ExpiresAt`
-   `Description`, `Notes`

## Implemented Stratagems

### 1. Undercut

-   **Type**: `undercut`
-   **Purpose**: To strategically lower the selling prices of a citizen's goods to be cheaper than their competition for a specific resource type.
-   **Creator**: `backend/engine/stratagem_creators/undercut_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/undercut_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `variant` (string, required): Determines the aggressiveness of the undercut.
    -   `"Mild"`: Sets prices 10% below the competition's minimum.
    -   `"Standard"`: Sets prices 15% below the competition's minimum.
    -   `"Aggressive"`: Sets prices 20% below the competition's minimum.
-   `targetResourceType` (string, required): The ID of the resource type whose prices are to be undercut (e.g., "timber", "grain").
-   `targetCitizen` (string, optional): The username of a specific competitor citizen to target. If provided, only this citizen's prices for the resource are considered competition.
-   `targetBuilding` (string, optional): The `BuildingId` of a specific competitor's building. If provided, only sell contracts from this building for the resource are considered competition.
    *Note: `targetCitizen` and `targetBuilding` are mutually exclusive in terms of primary targeting for competition price discovery. If both are provided, `targetCitizen` might take precedence, or the logic might combine them if appropriate.*
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to something like "Undercut [ResourceType] (Variant)".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should remain active, in hours. Defaults to 24 hours. The stratagem will attempt to maintain the undercut prices periodically until it expires.

#### How it Works:

1.  **Creation**:
    -   The `undercut_stratagem_creator.py` receives the request.
    -   It validates the parameters (e.g., valid variant, `targetResourceType` must be specified).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"` and sets `ExpiresAt` based on `durationHours`.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "undercut" stratagem.
    -   `undercut_stratagem_processor.py` is invoked.
    -   **Competition Analysis**:
        -   It identifies competitor sell contracts for the `targetResourceType`.
        -   If `targetCitizen` is set, it only looks at contracts from that citizen.
        -   If `targetBuilding` is set, it only looks at contracts from that building.
        -   If neither is set, it looks at all public sell contracts for the resource, excluding those from the `ExecutedBy` citizen.
    -   **Price Adjustment**:
        -   It finds the minimum price among the identified competitors.
        -   It calculates the new target price for the `ExecutedBy` citizen by applying the `variant` percentage reduction to the minimum competitor price.
        -   It updates all active public sell contracts of the `ExecutedBy` citizen for the `targetResourceType` to this new target price (ensuring the price is not zero or negative, defaulting to a minimum like 0.01 if necessary).
    -   **Status & Notes**:
        -   The stratagem remains `active` to allow for periodic re-evaluation of competitor prices and adjustments.
        -   `ExecutedAt` is set on the first successful processing run.
        -   Notes are updated with details of the price adjustment.
        -   If no competition is found, or the citizen has no active sell contracts for the resource, a note is made, and the stratagem might still be considered "processed" for that cycle but remains active.
        -   If critical parameters are missing (e.g., `TargetResourceType`), the stratagem status is set to `failed`.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "undercut",
  "stratagemDetails": {
    "variant": "Standard",
    "targetResourceType": "timber",
    "targetCitizen": "BasstheWhale",
    "durationHours": 48,
    "name": "Aggressive Timber Undercut vs Bass"
  }
}
```

This will make NLR attempt to sell timber 15% cheaper than BasstheWhale for 48 hours.

### 2. Coordinate Pricing

-   **Type**: `coordinate_pricing`
-   **Purpose**: To align the selling prices of a citizen's goods with a target's prices (specific citizen or building) or with the general market average for a specific resource type.
-   **Creator**: `backend/engine/stratagem_creators/coordinate_pricing_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/coordinate_pricing_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetResourceType` (string, required): The ID of the resource type whose prices are to be coordinated (e.g., "timber", "grain").
-   `targetCitizen` (string, optional): The username of a specific citizen whose prices will be used as the reference. If provided, the executing citizen will match the average price of this target citizen for the specified resource.
-   `targetBuilding` (string, optional): The `BuildingId` of a specific building whose sell contracts will be used as the reference. If provided, the executing citizen will match the average price of contracts from this building for the specified resource.
    *Note: If neither `targetCitizen` nor `targetBuilding` is provided, the stratagem will target the general market average price for the `targetResourceType` (excluding the executor's own current contracts).*
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to something like "Coordinate Pricing for [ResourceType] with [Target]".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should remain active, in hours. Defaults to 24 hours. The stratagem will attempt to maintain the coordinated prices periodically until it expires.

#### How it Works:

1.  **Creation**:
    -   The `coordinate_pricing_stratagem_creator.py` receives the request.
    -   It validates parameters (e.g., `targetResourceType` must be specified).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_cooperation"`, and sets `ExpiresAt` based on `durationHours`.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "coordinate_pricing" stratagem.
    -   `coordinate_pricing_stratagem_processor.py` is invoked.
    -   **Reference Price Analysis**:
        -   It identifies reference sell contracts for the `targetResourceType`.
        -   If `targetCitizen` is set, it only looks at contracts from that citizen.
        -   If `targetBuilding` is set, it only looks at contracts from that building.
        -   If neither is set, it looks at all public sell contracts for the resource from *other* citizens (excluding the `ExecutedBy` citizen).
    -   **Price Adjustment**:
        -   If no reference contracts are found, a note is made, and no price adjustment occurs for this cycle.
        -   Otherwise, it calculates the average price from the identified reference contracts.
        -   It updates all active public sell contracts of the `ExecutedBy` citizen for the `targetResourceType` to this new average price (ensuring the price is not zero or negative, defaulting to a minimum like 0.01 if necessary). This is done by creating `manage_public_sell_contract` activities.
    -   **Status & Notes**:
        -   The stratagem remains `active` to allow for periodic re-evaluation of reference prices and adjustments.
        -   `ExecutedAt` is set on the first successful processing run that results in at least one activity being initiated.
        -   Notes are updated with details of the price adjustment or reasons if no adjustment was made.
        -   If critical parameters are missing (e.g., `TargetResourceType`), the stratagem status is set to `failed` (though the creator should prevent this).
    -   **Notifications & Relationships**:
        -   If `targetCitizen` or `targetBuilding` was specified, a notification is sent to the target, and a small positive trust impact is applied between the `ExecutedBy` citizen and the target.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "coordinate_pricing",
  "stratagemDetails": {
    "targetResourceType": "wine",
    "targetCitizen": "SerMarco",
    "durationHours": 72,
    "name": "Wine Price Coordination with SerMarco"
  }
}
```

This will make NLR attempt to match SerMarco's average selling price for wine for 72 hours.

### 3. Hoard Resource

-   **Type**: `hoard_resource`
-   **Purpose**: To systematically accumulate a specific resource type in a designated storage building. The citizen executing the stratagem and their employees will be tasked with acquiring and storing this resource.
-   **Creator**: `backend/engine/stratagem_creators/hoard_resource_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/hoard_resource_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetResourceType` (string, required): The ID of the resource type to hoard (e.g., "iron_ore", "spices").
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Hoard [ResourceType]".
-   `description` (string, optional): A custom description. Defaults to indicating hoarding of the resource in available storage.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should remain active. Defaults to 72 hours.
-   `storageContractTargetAmount` (integer, optional): The target capacity for the `storage_query` contract created by the processor. Defaults to a very large number (e.g., 1,000,000).

#### How it Works:

1.  **Creation**:
    -   The `hoard_resource_stratagem_creator.py` receives the request.
    -   It validates parameters (e.g., `targetResourceType` must be specified).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "resource_management"`, and sets `ExpiresAt`.
    -   It stores `TargetResourceType` in the stratagem record. `TargetStorageBuildingId` is NOT stored by the creator.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "hoard_resource" stratagem.
    -   `hoard_resource_stratagem_processor.py` is invoked.
    -   **Storage Location Determination**:
        -   The processor first attempts to find a suitable storage building for the `ExecutedBy` citizen and `TargetResourceType`.
        -   Priority 1: A building owned or run by `ExecutedBy` with `Category: 'business'` and `SubCategory: 'storage'`, that has available capacity.
        -   Priority 2: An active `public_storage_offer` contract for the `TargetResourceType` from any public storage building, where the contract has capacity.
        -   If no suitable storage location is found, the stratagem notes this and takes no further action for this processing cycle.
    -   **Storage Contract Management**:
        -   Once a `targetStorageBuildingId` is determined, the processor ensures an active `storage_query` contract exists, linked to this stratagem, for the `TargetResourceType` at the determined `targetStorageBuildingId`, with the `ExecutedBy` citizen as the `Buyer`.
        -   If no such contract exists for the *determined building*, it creates one with a large `TargetAmount`.
    -   **Actor Identification**:
        -   Identifies the `ExecutedBy` citizen.
        -   Identifies all employees of the `ExecutedBy` citizen (occupants of buildings where `RunBy` is the `ExecutedBy` citizen).
    -   **Task Assignment**:
        -   For the `ExecutedBy` citizen and each available (not busy, has carry capacity) employee:
            -   It attempts to create a `fetch_resource` activity via the `/api/v1/engine/try-create-activity` endpoint.
            -   The `fetch_resource` activity parameters will instruct the actor to acquire the `TargetResourceType` from the market (cheapest source) and deliver it to the `TargetStorageBuildingId`.
            -   The `ContractId` of the `storage_query` contract is passed to authorize the deposit into the storage building.
            -   The amount to fetch is based on the actor's available carry capacity.
    -   **Status & Notes**:
        -   The stratagem remains `active` to continuously attempt hoarding until `ExpiresAt`.
        -   `ExecutedAt` is set on the first successful processing run that initiates fetching activities.
        -   Notes are updated with the number of fetching activities initiated or reasons if none were (e.g., storage full, actors busy).

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "hoard_resource",
  "stratagemDetails": {
    "targetResourceType": "iron_ore",
    "durationHours": 168, 
    "name": "Iron Ore Hoarding Operation"
  }
}
```
This will make NLR and their employees attempt to buy Iron Ore from the market and store it in a suitable storage location (determined by the processor) for 168 hours (1 week).

### 4. Supplier Lockout (Coming Soon)

-   **Type**: `supplier_lockout`
-   **Purpose**: To establish exclusive or priority supply agreements with specific resource suppliers, thereby securing a more reliable supply chain and potentially hindering competitors.
-   **Creator**: (To be created: `backend/engine/stratagem_creators/supplier_lockout_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/supplier_lockout_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetResourceType` (string, required): The ID of the resource type for which to secure suppliers.
-   `targetSupplierCitizen` (string, required): The username of the specific supplier citizen to target for an exclusive/priority contract.
-   `targetSupplierBuilding` (string, optional): The `BuildingId` of the specific supplier's building (if targeting a specific production facility).
-   `premiumPercentage` (integer, optional): The percentage above market price offered to the supplier (e.g., 10 for 10%, 20 for 20%). Defaults to 15.
-   `contractDurationDays` (integer, optional): The desired duration of the exclusive contract in days. Defaults to 30.
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): Duration of the stratagem itself (how long the game will try to maintain this state or report on it). Defaults to `contractDurationDays * 24`.

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `supplier_lockout_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_warfare"` or `"supply_chain"`, and sets `ExpiresAt`.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "supplier_lockout" stratagem.
    -   `supplier_lockout_stratagem_processor.py` is invoked.
    -   **Negotiation/Contract Creation**:
        -   The processor attempts to create a long-term `import` contract with the `targetSupplierCitizen` for the `targetResourceType`.
        -   The contract would offer a premium price (e.g., +10-20% over a baseline or agreed price).
        -   The contract terms would stipulate that the supplier prioritizes fulfilling orders for the `ExecutedBy` citizen before fulfilling orders for public contracts or other competitors.
    -   **Entity Changes & Effects**:
        -   **CONTRACTS**: New long-term `import` contracts are created.
        -   **RESOURCES**: The `ExecutedBy` citizen's supply of the `targetResourceType` becomes more reliable.
        -   **PROBLEMS**: Competitors who relied on the targeted supplier may face supply shortages, potentially creating `problem` records for them (e.g., `resource_availability` issues).
        -   **RELATIONSHIPS**: Trust and relationship strength between the `ExecutedBy` citizen and the `targetSupplierCitizen` may increase due to the mutually beneficial (though premium-priced for the buyer) long-term agreement.
        -   **DUCATS**: The `ExecutedBy` citizen will have sustained higher expenditures for the secured resource.
    -   **Status & Notes**:
        -   The stratagem might remain `active` for its duration, with the processor periodically checking the status of the exclusive contracts or attempting to renew/renegotiate.
        -   Notes would track the success of contract negotiations and observed impacts.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "supplier_lockout",
  "stratagemDetails": {
    "targetResourceType": "iron_ore",
    "targetSupplierCitizen": "GiovanniSupplier",
    "premiumPercentage": 15,
    "contractDurationDays": 60,
    "name": "Exclusive Iron Ore Deal with Giovanni"
  }
}
```
This would make NLR attempt to secure an exclusive 60-day contract for Iron Ore from GiovanniSupplier, offering a 15% price premium.

### 5. Political Campaign (Coming Soon)

-   **Type**: `political_campaign`
-   **Purpose**: To influence governance by lobbying for or against a specific decree or policy change.
-   **Creator**: (To be created: `backend/engine/stratagem_creators/political_campaign_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/political_campaign_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetDecreeName` (string, required): The name or identifier of the decree being targeted.
-   `desiredOutcome` (string, required): The desired outcome (e.g., "pass", "repeal", "amend_strength_low", "amend_duration_extend").
-   `campaignMessage` (string, required): The core message or argument of the campaign.
-   `lobbyingBudget` (integer, optional): Amount of Ducats allocated for lobbying efforts. Defaults to 0.
-   `campaignDurationDays` (integer, optional): Desired duration of the campaign in days. Defaults to 14.
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `political_campaign_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "political_influence"`, and sets `ExpiresAt`.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "political_campaign" stratagem.
    -   `political_campaign_stratagem_processor.py` is invoked.
    -   **Lobbying & Messaging**:
        -   The processor spends `INFLUENCE` and `DUCATS` (from `lobbyingBudget`) over time.
        -   It generates and sends `MESSAGES` to targeted citizens and officials, explaining the benefits of the policy change or the drawbacks of the current policy.
        -   It might involve creating `problem` records if the campaign highlights negative impacts of an existing decree.
    -   **Decree Interaction**:
        -   If the campaign aims to propose a new decree, it might create a new `DECREES` entry with `Status: "proposed"`.
        -   It monitors the status of the `targetDecreeName`.
    -   **Relationship Impact**:
        -   `RELATIONSHIPS` scores shift based on how other citizens react to the campaign's position. Agreement might increase trust/strength, disagreement might decrease it.
    -   **Outcome**:
        -   If successful (e.g., the decree is passed/repealed/amended as desired), this can lead to systematic changes: new `CONTRACTS` (e.g., if a trade policy changes) or modifications to economic rules.
        -   Success increases the `ExecutedBy` citizen's ongoing `INFLUENCE` generation.
        -   Failure can damage political reputation (e.g., a temporary malus to influence generation or negative relationship modifiers).
    -   **Status & Notes**:
        -   The stratagem remains `active` until the decree vote occurs, the campaign duration expires, or it's abandoned.
        -   Notes track lobbying efforts, messages sent, and observed impacts.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "political_campaign",
  "stratagemDetails": {
    "targetDecreeName": "Salt Tax Increase Act",
    "desiredOutcome": "repeal",
    "campaignMessage": "The current Salt Tax is an unfair burden on the Popolani and hinders local businesses. We must repeal it for the prosperity of Venice!",
    "lobbyingBudget": 5000,
    "campaignDurationDays": 28,
    "name": "Campaign to Repeal Salt Tax"
  }
}
```
This would make NLR launch a 28-day campaign to repeal the "Salt Tax Increase Act", spending up to 5000 Ducats on lobbying.

### 6. Reputation Assault

-   **Type**: `reputation_assault`
-   **Purpose**: To damage a competitor's business relationships and trustworthiness by spreading negative information.
-   **Creator**: `backend/engine/stratagem_creators/reputation_assault_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/reputation_assault_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizen` (string, required): The username of the competitor citizen whose reputation is to be targeted.
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Reputation Assault on [TargetCitizen]".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should remain active. Defaults to 24 hours. (Note: Current implementation is one-shot message generation upon first processing).

#### How it Works:

1.  **Creation**:
    -   The `reputation_assault_stratagem_creator.py` validates parameters (e.g., `targetCitizen` must be specified and not be the executor).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_warfare"`, and sets `ExpiresAt`.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "reputation_assault" stratagem.
    -   `reputation_assault_stratagem_processor.py` is invoked.
    -   **Identify Related Citizens**: The processor finds all citizens who have an existing relationship with the `TargetCitizen`.
    -   **Message Generation (for each related citizen)**:
        -   It fetches the full data package of the `TargetCitizen` (via `/api/get-data-package`).
        -   It fetches relationship details and recent conversation history between the `TargetCitizen` and the current `RelatedCitizen`.
        -   It constructs a **unique and detailed prompt for KinOS for each `RelatedCitizen`**. This prompt instructs KinOS to act as the `ExecutedBy` citizen and generate a subtle, negative message specifically tailored to the `RelatedCitizen` about the `TargetCitizen`. The prompt includes all fetched contextual data (profil de l'exécuteur, data-package complet de la cible, profil du destinataire, détails des relations entre les trois parties, et historique de conversation entre la cible et le destinataire).
        -   It calls the KinOS API (`/v2/blueprints/serenissima-ai/kins/{EXECUTOR_USERNAME}/channels/{RELATED_CITIZEN_USERNAME}/messages`) to generate the **customized message content**. The AI model used is based on the `ExecutedBy` citizen's social class.
    -   **Message Sending**:
        -   Each **individually generated and cleaned message** is then sent from `ExecutedBy` to the respective `RelatedCitizen` by creating a new record in the `MESSAGES` table (via `/api/messages/send`).
    -   **Relationship Impact**:
        -   The `TrustScore` in the `RELATIONSHIPS` table between the `ExecutedBy` citizen and the `TargetCitizen` is significantly decreased (e.g., by -50 points).
    -   **Status & Notes**:
        -   `ExecutedAt` is set on the first successful processing run.
        -   The stratagem is marked as `executed` after attempting to send messages.
        -   Notes are updated with the number of messages sent.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "reputation_assault",
  "stratagemDetails": {
    "targetCitizen": "BasstheWhale",
    "durationHours": 24,
    "name": "Discredit BasstheWhale"
  }
}
```
This will make NLR attempt to damage BasstheWhale's reputation by sending AI-generated negative messages to BasstheWhale's known associates. NLR's trust with BasstheWhale will plummet.

### 7. Emergency Liquidation

-   **Type**: `emergency_liquidation`
-   **Purpose**: To quickly convert a citizen's owned inventory into cash, albeit at potentially below-market rates.
-   **Creator**: `backend/engine/stratagem_creators/emergency_liquidation_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/emergency_liquidation_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `variant` (string, required): Determines the discount level and duration.
    -   `"Mild"`: Sells items at 80% of average market price (20% discount). Duration: 24 hours.
    -   `"Standard"`: Sells items at 70% of average market price (30% discount). Duration: 48 hours.
    -   `"Aggressive"`: Sells items at 60% of average market price (40% discount). Duration: 72 hours.
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Emergency Liquidation ([Variant])".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.

#### How it Works:

1.  **Creation**:
    -   The `emergency_liquidation_stratagem_creator.py` validates parameters (e.g., valid variant).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "personal_finance"`, and sets `ExpiresAt` based on the variant's duration.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "emergency_liquidation" stratagem.
    -   `emergency_liquidation_stratagem_processor.py` is invoked.
    -   **Identify Sales Location**: The processor attempts to find a suitable building for the `ExecutedBy` citizen to sell from (e.g., a business they run). If no suitable building is found, the stratagem notes this and may be ineffective until a sales point is available.
    -   **Inventory Scan**: It fetches all resources currently in the `ExecutedBy` citizen's direct inventory (AssetType: 'citizen').
    -   **For each resource in inventory**:
        -   **Market Price Analysis**: It calculates the average current market price for the resource from active `public_sell` contracts (excluding the executor's own). If no market price is found, it uses a fallback (e.g., resource definition's `importPrice`).
        -   **Liquidation Price Calculation**: It applies the discount percentage (based on the `variant`) to the determined market/fallback price. Ensures the price is not zero or negative.
        -   **Contract Creation**: It initiates a `manage_public_sell_contract` activity for the `ExecutedBy` citizen to create a new `public_sell` contract for the entire available amount of that resource.
            -   The `SellerBuilding` will be the sales location identified earlier.
            -   The contract duration is set to be short (e.g., 24 hours) to facilitate rapid sale.
    -   **Status & Notes**:
        -   `ExecutedAt` is set on the first successful processing run that initiates contract creation.
        -   The stratagem is marked as `executed` after attempting to list all inventory items. It's a one-shot listing process.
        -   Notes are updated with the number of contracts created and any issues encountered (e.g., no sales building, no market price found).

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "emergency_liquidation",
  "stratagemDetails": {
    "variant": "Standard"
  }
}
```
This will make NLR attempt to sell all items in their inventory at 70% of their average market price. The sell contracts will be active for 24 hours, and the stratagem itself will be considered for 48 hours.

### 8. Cultural Patronage (Coming Soon)

-   **Type**: `cultural_patronage`
-   **Purpose**: To build social capital and enhance reputation by sponsoring artists, performances, or cultural institutions.
-   **Creator**: `backend/engine/stratagem_creators/cultural_patronage_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/cultural_patronage_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetArtist` (string, optional): Username of the artist to patronize.
-   `targetPerformanceId` (string, optional): ID of a specific performance to sponsor (e.g., a play, a concert).
-   `targetInstitutionId` (string, optional): `BuildingId` of a cultural institution to support (e.g., `art_gallery`, `theater`, `library`).
    *Note: At least one of `targetArtist`, `targetPerformanceId`, or `targetInstitutionId` must be specified.*
-   `patronageLevel` (string, optional): The scale of the patronage. Examples: `"Modest"`, `"Standard"`, `"Grand"`. Defaults to `"Standard"`. This could influence cost and impact.
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Patronage: [Target] ([Level])".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem and its effects (e.g., reputation boost) should be considered active. Defaults to 168 hours (7 days).

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `cultural_patronage_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "cultural_influence"`, and sets `ExpiresAt`.
    -   The base influence cost is around 30-60, potentially adjusted by `patronageLevel`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "cultural_patronage" stratagem.
    -   `cultural_patronage_stratagem_processor.py` is invoked.
    -   **Commissioning/Sponsorship**:
        -   The processor would initiate activities or create contracts to commission artworks from the `targetArtist`, sponsor the `targetPerformanceId`, or provide funding/resources to the `targetInstitutionId`.
        -   This might involve creating `work_on_art` activities for the artist, or specific event-sponsoring contracts.
    -   **Entity Changes & Effects**:
        -   **CITIZENS**: Sponsored artists (`targetArtist`) might gain inspiration or resources, leading to the creation of new artworks (which could be `RESOURCE` records with special attributes).
        -   **BUILDINGS**: Sponsored institutions (`targetInstitutionId`) might see improved conditions, host special events, or gain prestige.
        -   **RELATIONSHIPS**: The `ExecutedBy` citizen's relationship scores with the `targetArtist`, key figures associated with the `targetPerformanceId` or `targetInstitutionId`, and potentially with cultural elites or nobility, would improve.
        -   **INFLUENCE**: The `ExecutedBy` citizen's passive `Influence` generation rate would increase for the duration of the patronage or as a lasting effect of successful cultural contributions.
        -   **DUCATS**: The `ExecutedBy` citizen would spend Ducats as part of the patronage.
    -   **Status & Notes**:
        -   The stratagem might remain `active` for its duration, with the processor periodically checking on the progress of commissioned works or the status of sponsored events/institutions.
        -   Notes would track the specific commissions, sponsorships, and observed impacts on reputation and influence.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "cultural_patronage",
  "stratagemDetails": {
    "targetArtist": "LeonardoDaVinciAI",
    "patronageLevel": "Grand",
    "durationHours": 336, 
    "name": "Grand Patronage of LeonardoDaVinciAI"
  }
}
```
This would make NLR initiate a "Grand" level of cultural patronage towards the artist "LeonardoDaVinciAI" for 14 days, aiming to commission significant works and boost NLR's cultural standing.

### 9. Information Network (Coming Soon)

-   **Type**: `information_network`
-   **Purpose**: To establish intelligence gathering operations targeting specific citizens or market sectors, providing advanced information and insights.
-   **Creator**: `backend/engine/stratagem_creators/information_network_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/information_network_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizens` (List[string], optional): Usernames of specific citizens to target for information gathering.
-   `targetSectors` (List[string], optional): Market sectors (e.g., "grain_trade", "shipbuilding") or geographical areas (e.g., "Rialto", "Dorsoduro") to target.
    *Note: At least one of `targetCitizens` or `targetSectors` must be specified.*
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Information Network ([Targets])".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the information network should remain active and provide benefits. Defaults to 168 hours (7 days).

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `information_network_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "intelligence"`, an influence cost of 40, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "information_network" stratagem.
    -   `information_network_stratagem_processor.py` is invoked.
    -   **Informant Recruitment**:
        -   The processor would simulate the recruitment of informants among `CITIZENS` within the `targetSectors` or those associated with `targetCitizens`. This might involve creating hidden relationship modifiers or temporary "informant" status flags.
    -   **Information Gathering & Delivery**:
        -   **Advanced NOTIFICATIONS**: The `ExecutedBy` citizen would start receiving special `NOTIFICATION` records about competitor strategies (e.g., new stratagems initiated by rivals), significant market movements (e.g., large buy/sell orders being placed), or unusual activities related to the targets.
        -   **Enhanced RELEVANCIES**: The system generating `RELEVANCIES` data would be biased to provide more detailed or higher-scored items related to competitor vulnerabilities (e.g., low stock, failing contracts) or opportunities (e.g., unmet demand) within the targeted scope.
        -   **Priority Galley Information**: The `ExecutedBy` citizen might receive earlier or more detailed information about incoming merchant galleys (e.g., their cargo, arrival times), potentially through special `NOTIFICATION` records or by influencing the `createimportactivities.py` script's output for them.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its duration, providing continuous intelligence benefits.
        -   Notes could track the number of informants (conceptually) or key pieces of intelligence gathered.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "information_network",
  "stratagemDetails": {
    "targetSectors": ["grain_trade", "Rialto_market"],
    "targetCitizens": ["BasstheWhale", "SerMarco"],
    "durationHours": 336, 
    "name": "Grain Trade & Rialto Intel Network"
  }
}
```
This would make NLR establish an information network focused on the grain trade, the Rialto market area, and specifically monitoring citizens BasstheWhale and SerMarco for 14 days.

### 10. Maritime Blockade (Coming Soon)

-   **Type**: `maritime_blockade`
-   **Purpose**: To control water access to cripple a competitor's trade and waterfront operations.
-   **Creator**: `backend/engine/stratagem_creators/maritime_blockade_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/maritime_blockade_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCompetitorBuilding` (string, optional): `BuildingId` of a specific competitor's waterfront building (e.g., a dock, warehouse, or even an arsenal gate if modeled as a building).
-   `targetCompetitorCitizen` (string, optional): Username of the competitor to target (e.g., owner/operator of key maritime assets).
    *Note: At least one of `targetCompetitorBuilding` or `targetCompetitorCitizen` must be specified.*
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Maritime Blockade on [Target]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the blockade should remain active. Defaults to 72 hours (3 days).

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `maritime_blockade_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_warfare"` (or `naval_control`), an influence cost of 70, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "maritime_blockade" stratagem.
    -   `maritime_blockade_stratagem_processor.py` is invoked.
    -   **Coordination & Restriction**:
        -   The processor would simulate coordination with dock owners and gondola operators allied with or influenced by the `ExecutedBy` citizen.
        -   This could involve creating temporary negative relationship modifiers between these allied entities and the `targetCompetitorCitizen` or entities associated with `targetCompetitorBuilding`.
        -   It might also involve creating temporary "blockade" flags on certain water routes or access points (e.g., specific docks, arsenal gates if they are distinct entities/points).
    -   **Impact on Competitor**:
        -   The `targetCompetitorCitizen` or operations at `targetCompetitorBuilding` would face difficulties:
            -   Their ships/gondolas might be denied docking at certain locations.
            -   Their access to/from key waterways (like the Arsenal) might be restricted or delayed.
            -   This could lead to `PROBLEMS` for the competitor (e.g., `logistics_delay`, `trade_disruption`).
            -   Their ability to fulfill contracts or receive supplies would be hampered.
    -   **Relationship Impact**:
        -   Significant negative impact on the relationship between `ExecutedBy` and the `targetCompetitorCitizen`.
        -   Potential positive impact with allied dock owners/gondoliers if they are compensated or share the goal.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its duration, maintaining the restrictive effects.
        -   Notes could track the key entities involved in the blockade and observed impacts.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "maritime_blockade",
  "stratagemDetails": {
    "targetCompetitorBuilding": "dock_rival_company_01",
    "targetCompetitorCitizen": "BasstheWhale",
    "durationHours": 48,
    "name": "Blockade Rival Dock & Bass"
  }
}
```
This would make NLR attempt to blockade the waterfront operations associated with "dock_rival_company_01" and citizen "BasstheWhale" for 48 hours.

### 11. Theater Conspiracy (Coming Soon)

-   **Type**: `theater_conspiracy`
-   **Purpose**: To manipulate public opinion and political narratives by commissioning and staging theatrical performances with specific themes.
-   **Category**: `social_warfare`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/theater_conspiracy_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/theater_conspiracy_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetTheaterId` (string, required): The `BuildingId` of the `theater` where the performance will be staged.
-   `politicalTheme` (string, required): The theme of the play (e.g., "satirize_competitor", "promote_policy", "glorify_patron").
-   `targetCompetitor` (string, optional): The username of a competitor to satirize, required if `politicalTheme` is "satirize_competitor".
-   `targetPolicy` (string, optional): The name or ID of a policy/decree to promote, required if `politicalTheme` is "promote_policy".
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): Duration of the stratagem's influence. Defaults to 168 (7 days).

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `theater_conspiracy_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_warfare"`, an influence cost of 25, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "theater_conspiracy" stratagem.
    -   `theater_conspiracy_stratagem_processor.py` is invoked.
    -   **Play Commissioning**:
        -   The processor would simulate the commissioning of a play. This could involve creating a `work_on_art` activity for an `Artisti` citizen with the `playwriting` specialty, possibly one associated with the `targetTheaterId`.
        -   The play itself could be a temporary `RESOURCE` record of type `play_script`.
    -   **Staging & Performance**:
        -   Once the play is "written", the processor would schedule performances at the `targetTheaterId`. This could be represented by creating special `attend_theater_performance` activities for the public.
    -   **Relationship & Opinion Impact**:
        -   When AI citizens "attend" the performance, their `RELATIONSHIPS` scores would be adjusted based on the `politicalTheme`.
        -   If satirizing a competitor, the `TrustScore` between attendees and the `targetCompetitor` would decrease.
        -   If promoting the `ExecutedBy` citizen, their `Influence` might increase, and relationships with attendees might improve.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its duration, potentially scheduling multiple performances.
        -   Notes would track the commissioned play, performance schedule, and observed impacts on public opinion.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "theater_conspiracy",
  "stratagemDetails": {
    "targetTheaterId": "theater_grand_canal_01",
    "politicalTheme": "satirize_competitor",
    "targetCompetitor": "BasstheWhale",
    "durationHours": 168,
    "name": "The Folly of the Whale"
  }
}
```
This would make NLR attempt to stage a play at the "theater_grand_canal_01" that satirizes their competitor, BasstheWhale, for one week.

### 12. Printing Propaganda (Coming Soon)

-   **Type**: `printing_propaganda`
-   **Purpose**: To conduct information warfare against competitors by mass-producing and distributing pamphlets, broadsheets, and rumors.
-   **Category**: `information_warfare`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/printing_propaganda_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/printing_propaganda_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetPrintingHouseId` (string, required): The `BuildingId` of the `printing_house` to use.
-   `targetCompetitor` (string, required): The username of the competitor to target with propaganda.
-   `propagandaTheme` (string, optional): The theme of the propaganda (e.g., "financial_mismanagement", "scandalous_rumors", "shoddy_craftsmanship"). Defaults to "General Disinformation".
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): Duration of the stratagem's influence. Defaults to 168 (7 days).

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `printing_propaganda_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "information_warfare"`, an influence cost of 30, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "printing_propaganda" stratagem.
    -   `printing_propaganda_stratagem_processor.py` is invoked.
    -   **Material Production**:
        -   The processor would create `production` activities at the `targetPrintingHouseId` to generate a new `RESOURCE` type: `propaganda_materials`.
        -   The `propaganda_materials` resource would have attributes in its JSON field detailing the `targetCompetitor` and `propagandaTheme`.
    -   **Distribution**:
        -   The processor would create `distribute_propaganda` activities for the `ExecutedBy` citizen or their employees.
        -   These activities would involve taking the `propaganda_materials` and "distributing" them in high-traffic areas (e.g., `market_stall`, `piazza`).
    -   **Relationship & Opinion Impact**:
        -   When AI citizens are in a location where propaganda is being distributed, a chance-based check would occur.
        -   If affected, their `RELATIONSHIPS` `TrustScore` with the `targetCompetitor` would decrease.
        -   The `ExecutedBy` citizen's relationship with the `targetCompetitor` would also be negatively impacted if their involvement is discovered.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its duration, scheduling production and distribution runs.
        -   Notes would track the amount of propaganda produced and distributed, and any observed impacts.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "printing_propaganda",
  "stratagemDetails": {
    "targetPrintingHouseId": "printing_house_rialto_01",
    "targetCompetitor": "BasstheWhale",
    "propagandaTheme": "shoddy_craftsmanship",
    "durationHours": 168,
    "name": "Pamphlets on the Whale's Poor Wares"
  }
}
```
This would make NLR attempt to use the "printing_house_rialto_01" to produce and distribute propaganda about the poor quality of BasstheWhale's goods for one week.

### 13. Cargo "Mishap" (Coming Soon)

-   **Type**: `cargo_mishap`
-   **Purpose**: To sabotage a competitor's shipment by arranging for their goods to "disappear" while in transit.
-   **Category**: `economic_warfare`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/cargo_mishap_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/cargo_mishap_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetContractId` (string, required): The `ContractId` of the specific `public_sell` or `import` contract to target.
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): The window of opportunity for the mishap to occur. Defaults to 24 hours.

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `cargo_mishap_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_warfare"`, an influence cost of 8, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "cargo_mishap" stratagem.
    -   `cargo_mishap_stratagem_processor.py` is invoked.
    -   **Target Interception**:
        -   The processor identifies any active `fetch_resource` or `deliver_resource_batch` activities associated with the `targetContractId`.
        -   It simulates an interception by creating a `problem` record of type `cargo_lost` for the citizen performing the transport activity.
    -   **Entity Changes & Effects**:
        -   **RESOURCES**: The `RESOURCES` being carried by the transporter are deleted from their inventory.
        -   **CONTRACTS**: The `targetContractId` may fail to be fulfilled, leading to penalties or cancellation.
        -   **RELATIONSHIPS**: The competitor (seller) may suffer relationship damage with their customer (buyer) due to the failed delivery (-5 to -10 trust).
        -   **RISK**: There is a small chance that the `ExecutedBy` citizen's involvement is discovered, leading to criminal charges (`problem` of type `criminal_accusation`) and significant reputation damage with the target and the authorities.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` after the mishap occurs.
        -   Notes would track the intercepted activity and the outcome.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "cargo_mishap",
  "stratagemDetails": {
    "targetContractId": "contract-public-sell-bassthewhale-timber-xyz",
    "durationHours": 24,
    "name": "Timber Shipment 'Mishap'"
  }
}
```
This would make NLR attempt to sabotage a specific timber shipment contract belonging to BasstheWhale within the next 24 hours.

### 14. Marketplace Gossip (Coming Soon)

-   **Type**: `marketplace_gossip`
-   **Purpose**: To subtly damage a competitor's reputation by spreading rumors and negative information through Venice's social networks.
-   **Category**: `social_warfare`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/marketplace_gossip_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/marketplace_gossip_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizen` (string, required): The username of the competitor to target.
-   `gossipTheme` (string, optional): The theme of the gossip (e.g., "questionable_business_practices", "personal_scandal"). Defaults to "General Rumors".
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): Duration of the stratagem's influence. Defaults to 48 (2 days).

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `marketplace_gossip_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_warfare"`, an influence cost of 5, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "marketplace_gossip" stratagem.
    -   `marketplace_gossip_stratagem_processor.py` is invoked.
    -   **Rumor Spreading**:
        -   The processor would identify high-traffic social hubs (e.g., `market_stall`, `piazza`, `tavern`).
        -   It would create `spread_rumor` activities for the `ExecutedBy` citizen or their employees at these locations.
    -   **Entity Changes & Effects**:
        -   **NOTIFICATIONS**: When other AI citizens are near a `spread_rumor` activity, they have a chance to "overhear" the gossip, generating a `NOTIFICATION` for them containing the negative information.
        -   **MESSAGES**: The system might also generate subtle, negative `MESSAGES` between citizens who have overheard the rumor, further propagating it.
        -   **RELATIONSHIPS**: Citizens who are influenced by the gossip will experience a small negative trust shift towards the `targetCitizen` (-3 to -8 trust). The effect is less intense but broader than a direct `reputation_assault`.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its duration, scheduling rumor-spreading activities.
        -   Notes would track the locations targeted and the number of citizens potentially influenced.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "marketplace_gossip",
  "stratagemDetails": {
    "targetCitizen": "BasstheWhale",
    "gossipTheme": "questionable_business_practices",
    "durationHours": 48,
    "name": "Whispers about the Whale"
  }
}
```
This would make NLR attempt to spread rumors about BasstheWhale's business practices in public places for two days.

### 15. Employee Poaching (Coming Soon)

-   **Type**: `employee_poaching`
-   **Purpose**: To recruit a skilled employee from a competitor by making them a better offer.
-   **Category**: `social_warfare`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/employee_poaching_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/employee_poaching_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetEmployeeUsername` (string, required): The username of the employee to poach.
-   `targetCompetitorUsername` (string, required): The username of the current employer.
-   `jobOfferDetails` (string, optional): A brief description of the job offer (e.g., "Higher wages at my workshop", "Better working conditions").
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): Duration for the offer to be considered. Defaults to 48 (2 days).

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `employee_poaching_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_warfare"`, an influence cost of 6, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "employee_poaching" stratagem.
    -   `employee_poaching_stratagem_processor.py` is invoked.
    -   **Job Offer Message**:
        -   The processor generates and sends a `MESSAGE` from the `ExecutedBy` citizen to the `targetEmployeeUsername`.
        -   The message contains the job offer and may be tailored based on the relationship between the executor and the employee.
    -   **Employee Decision**:
        -   Upon receiving the message, the `targetEmployeeUsername` (if an AI) will evaluate the offer. This could be a simple probability check based on factors like:
            -   The wage difference (if quantifiable).
            -   The employee's current job satisfaction (relationship with `targetCompetitorUsername`).
            -   The employee's relationship with the `ExecutedBy` citizen.
    -   **Entity Changes & Effects**:
        -   If the offer is accepted, the `Occupant` field of the competitor's building is cleared, and the `Occupant` field of one of the `ExecutedBy` citizen's buildings is updated.
        -   **RELATIONSHIPS**: The relationship between the `ExecutedBy` citizen and the `targetCompetitorUsername` is negatively impacted. The relationship between the `ExecutedBy` citizen and the `targetEmployeeUsername` may improve.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` after the message is sent and the employee makes a decision.
        -   Notes would track the outcome of the poaching attempt.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "employee_poaching",
  "stratagemDetails": {
    "targetEmployeeUsername": "GiovanniArtisan",
    "targetCompetitorUsername": "BasstheWhale",
    "jobOfferDetails": "I can offer you a 20% wage increase and your own workspace.",
    "durationHours": 48,
    "name": "Poach Giovanni from Bass"
  }
}
```
This would make NLR attempt to recruit "GiovanniArtisan" away from their current employer, "BasstheWhale".

### 16. Joint Venture (Coming Soon)

-   **Type**: `joint_venture`
-   **Purpose**: To propose a formal business partnership with another citizen, defining contributions, responsibilities, and profit-sharing.
-   **Category**: `economic_cooperation`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/joint_venture_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/joint_venture_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetPartnerUsername` (string, required): The username of the citizen to propose the venture to.
-   `ventureDetails` (string, required): A detailed description of the venture, including contributions, management responsibilities, and goals.
-   `profitSharingPercentage` (float, optional): The profit share for the initiator (e.g., 0.5 for 50%). Defaults to 0.5.
-   `durationDays` (integer, optional): The duration of the joint venture in days. Defaults to 30.
-   `name` (string, optional): Custom name for the stratagem.

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `joint_venture_stratagem_creator.py` validates parameters.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_cooperation"`, an influence cost of 20, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "joint_venture" stratagem.
    -   `joint_venture_stratagem_processor.py` is invoked.
    -   **Proposal & Negotiation**:
        -   The processor sends a `MESSAGE` to the `targetPartnerUsername` with the venture proposal.
        -   The target partner (if AI) evaluates the offer based on their relationship with the initiator, the venture's perceived profitability, and the fairness of the terms. They can accept, reject, or propose a counter-offer (future enhancement).
    -   **Contract Creation**:
        -   If accepted, a special `CONTRACTS` record of type `joint_venture` is created.
        -   This contract links both citizens and specifies the `profitSharingPercentage`, `durationDays`, and `ventureDetails`.
    -   **Entity Changes & Effects**:
        -   **CONTRACTS**: A new `joint_venture` contract is created.
        -   **RESOURCES/DUCATS**: The processor would create activities for both partners to contribute their agreed-upon resources or capital to the venture.
        -   **REVENUE DISTRIBUTION**: A new periodic script (`processJointVentures.py`) would need to be created to evaluate the performance of active joint ventures (e.g., by tracking revenue of associated buildings/activities) and automatically distribute profits to the partners' `Ducats` balances according to the `profitSharingPercentage`.
        -   **RELATIONSHIPS**: A successful joint venture would significantly increase the `TrustScore` and `StrengthScore` between the partners.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` once the proposal is accepted and the contract is created. The `joint_venture` contract itself then becomes the active entity.
        -   Notes would track the outcome of the proposal.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "joint_venture",
  "stratagemDetails": {
    "targetPartnerUsername": "SerMarco",
    "ventureDetails": "Let us pool our resources to establish a new trade route for spices from the Levant. I will provide the ship and initial capital for the first voyage; you will leverage your contacts in Alexandria to secure the best prices.",
    "profitSharingPercentage": 0.5,
    "durationDays": 180,
    "name": "Spice Trade Venture with SerMarco"
  }
}
```
This would make NLR propose a 6-month, 50/50 spice trading joint venture to SerMarco.

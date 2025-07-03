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
-   **Category**: `commerce`
-   **Nature**: `aggressive`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `commerce`
-   **Nature**: `neutral`
-   **Creator**: `backend/engine/stratagem_creators/coordinate_pricing_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/coordinate_pricing_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizen` (string, optional): The username of a specific citizen whose prices will be used as the reference.
-   `targetBuilding` (string, optional): The `BuildingId` of a specific building whose sell contracts will be used as the reference.
-   `targetResourceType` (string, optional): The ID of the resource type whose prices are to be coordinated (e.g., "timber", "grain"). If omitted, the stratagem will attempt to coordinate prices for *all* resources the executor is currently selling, based on the reference target (citizen, building, or general market).
    *Note: If neither `targetCitizen` nor `targetBuilding` is provided, the stratagem will target the general market average price for the `targetResourceType` (if specified) or for all the executor's resources (if `targetResourceType` is omitted), excluding the executor's own current contracts.*
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to something like "Coordinate Pricing for [ResourceType or All Resources] with [Target]".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should remain active, in hours. Defaults to 24 hours. The stratagem will attempt to maintain the coordinated prices periodically until it expires.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works:

1.  **Creation**:
    -   The `coordinate_pricing_stratagem_creator.py` receives the request.
    -   It validates parameters. `targetResourceType` is now optional.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_cooperation"`, and sets `ExpiresAt` based on `durationHours`.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "coordinate_pricing" stratagem.
    -   `coordinate_pricing_stratagem_processor.py` is invoked.
    -   **Resource Scope Definition**:
        -   If `TargetResourceType` is specified in the stratagem record, only that resource is processed.
        -   If `TargetResourceType` is *not* specified, the processor identifies all distinct resources currently being sold by the `ExecutedBy` citizen via active `public_sell` contracts. Each of these resources will be processed.
    -   **For each resource to be processed**:
        -   **Reference Price Analysis**:
            -   It identifies reference sell contracts for the current resource type.
            -   If `TargetCitizen` is set, it only looks at contracts from that citizen for this resource.
            -   If `TargetBuilding` is set, it only looks at contracts from that building for this resource.
            -   If neither `TargetCitizen` nor `TargetBuilding` is set, it looks at all public sell contracts for this resource from *other* citizens (excluding the `ExecutedBy` citizen).
        -   **Price Adjustment**:
            -   If no reference contracts are found for the current resource, a note is made, and no price adjustment occurs for this resource in this cycle.
            -   Otherwise, it calculates the average price from the identified reference contracts for this resource.
            -   It updates all active public sell contracts of the `ExecutedBy` citizen for the current resource type to this new average price (ensuring the price is not zero or negative, defaulting to a minimum like 0.01 if necessary). This is done by creating `manage_public_sell_contract` activities.
    -   **Status & Notes**:
        -   The stratagem remains `active` to allow for periodic re-evaluation of reference prices and adjustments.
        -   `ExecutedAt` is set on the first successful processing run that results in at least one activity being initiated.
        -   Notes are updated with details of the price adjustments or reasons if no adjustment was made for specific resources.
        -   If `TargetResourceType` was initially missing and the executor sells no resources, the stratagem is marked `executed` with a note.
    -   **Notifications & Relationships**:
        -   If `TargetCitizen` or `TargetBuilding` was specified, a notification is sent to the target, and a small positive trust impact is applied between the `ExecutedBy` citizen and the target. The notification will mention the specific resource if one was targeted, or refer to "all resources" otherwise.

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
-   **Category**: `commerce`
-   **Nature**: `neutral`
-   **Creator**: `backend/engine/stratagem_creators/hoard_resource_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/hoard_resource_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetResourceType` (string, required): The ID of the resource type to hoard (e.g., "iron_ore", "spices").
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Hoard [ResourceType]".
-   `description` (string, optional): A custom description. Defaults to indicating hoarding of the resource in available storage.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should remain active. Defaults to 72 hours.
-   `storageContractTargetAmount` (integer, optional): The target capacity for the `storage_query` contract created by the processor. Defaults to a very large number (e.g., 1,000,000).
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `commerce`
-   **Nature**: `aggressive`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `political`
-   **Nature**: `neutral`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `personal`
-   **Nature**: `aggressive`
-   **Creator**: `backend/engine/stratagem_creators/reputation_assault_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/reputation_assault_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizen` (string, required): The username of the competitor citizen whose reputation is to be targeted.
-   `assaultAngle` (string, optional): A specific theme or angle for the negative information (e.g., "Their recent business failures", "Questionable alliances"). If provided, this guides the AI in crafting messages.
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Reputation Assault on [TargetCitizen]".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should remain active. Defaults to 24 hours. (Note: Current implementation is one-shot message generation upon first processing).
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works:

1.  **Creation**:
    -   The `reputation_assault_stratagem_creator.py` validates parameters (e.g., `targetCitizen` must be specified and not be the executor).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_warfare"`, and sets `ExpiresAt`.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "reputation_assault" stratagem.
    -   `reputation_assault_stratagem_processor.py` is invoked.
    -   **Identify Related Citizens**: The processor finds all citizens who have an existing relationship with the `TargetCitizen`.
    -   **Message Generation (for each related citizen)**:
        -   It fetches the full ledger of the `TargetCitizen` (via `/api/get-ledger`).
        -   It fetches relationship details and recent conversation history between the `TargetCitizen` and the current `RelatedCitizen`.
        -   It constructs a **unique and detailed prompt for KinOS for each `RelatedCitizen`**. This prompt instructs KinOS to act as the `ExecutedBy` citizen and generate a subtle, negative message specifically tailored to the `RelatedCitizen` about the `TargetCitizen`. The prompt includes all fetched contextual data (profil de l'exécuteur, ledger complet de la cible, profil du destinataire, détails des relations entre les trois parties, et historique de conversation entre la cible et le destinataire).
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
-   **Category**: `commerce`
-   **Nature**: `neutral`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `social`
-   **Nature**: `benevolent`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `security`
-   **Nature**: `neutral`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `warfare`
-   **Nature**: `aggressive`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `social`
-   **Nature**: `neutral`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `political`
-   **Nature**: `aggressive`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `warfare`
-   **Nature**: `illegal`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/cargo_mishap_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/cargo_mishap_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetContractId` (string, required): The `ContractId` of the specific `public_sell` or `import` contract to target.
-   `name` (string, optional): Custom name for the stratagem.
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): The window of opportunity for the mishap to occur. Defaults to 24 hours.
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `personal`
-   **Nature**: `aggressive`
-   **Creator**: `backend/engine/stratagem_creators/marketplace_gossip_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/marketplace_gossip_stratagem_processor.py` (Stratagem processor is minimal; main logic in `spread_rumor` activity processor)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizen` (string, required): The username of the competitor to target.
-   `gossipContent` (string, required): The specific rumor/content to spread.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Gossip Campaign vs [TargetCitizen]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): Overall duration for the stratagem to be considered active. Defaults to cover the spread_rumor activities plus a buffer (e.g., 24 hours + (2 hours * 3 locations)).
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works:

1.  **Creation**:
    -   The `marketplace_gossip_stratagem_creator.py` validates parameters.
    -   It identifies the top 3 most frequented locations by AI citizens based on their current `Position`.
    -   For each of these locations, it creates a chain of activities for the `ExecutedBy` citizen:
        1.  A `goto_location` activity to travel to the popular spot.
        2.  A `spread_rumor` activity (duration: 2 hours) that starts after arrival. The `Notes` of this activity store the `targetCitizen` (victim) and the `gossipContent`.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_warfare"`, and sets `ExpiresAt`. The `Notes` of the stratagem record will store the `targetCitizen` and `gossipContent` for reference.

2.  **Processing (Stratagem)**:
    -   `processStratagems.py` picks up the active "marketplace_gossip" stratagem.
    -   `marketplace_gossip_stratagem_processor.py` is invoked.
    -   This processor's main role is to mark the stratagem as `executed` once the initial activities have been set up by the creator. It does not directly spread rumors itself.

3.  **Processing (Activity - `spread_rumor`)**:
    -   When a `spread_rumor` activity becomes active (processed by `processActivities.py`):
        -   The `spread_rumor_activity_processor.py` is invoked.
        -   It retrieves the `targetCitizen` (victim) and `gossipContent` from the activity's `Notes`.
        -   It identifies all other AI citizens currently at the same location (within a certain radius).
        -   For each present citizen (excluding the executor), it calls `conversation_helper.generate_conversation_turn` with:
            -   `speaker_username`: The `ExecutedBy` citizen (who is spreading the rumor).
            -   `listener_username`: The present citizen.
            -   `interaction_mode`: `"conversation_opener"`.
            -   `message`: A crafted message from the executor to the listener, e.g., "Psst, [ListenerFirstName], have you heard about [TargetVictimFirstName]? They say that [gossipContent]".
            -   `target_citizen_username_for_trust_impact`: The `targetCitizen` (victim of the gossip).
        -   The `conversation_helper` will then handle the AI-generated response from the listener and, crucially, assess the trust impact on the listener towards both the speaker (executor) and the `target_citizen_username_for_trust_impact` (victim).

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "marketplace_gossip",
  "stratagemDetails": {
    "targetCitizen": "BasstheWhale",
    "gossipContent": "BasstheWhale has been seen meeting with known smugglers near the Arsenale at odd hours. I wonder what that's about?",
    "name": "Whispers about the Whale's Shady Dealings"
  }
}
```
This would make NLR initiate a gossip campaign against BasstheWhale. The system will find 3 popular locations, and NLR will travel to each to spread the specified rumor to citizens present there.

### 15. Employee Poaching (Coming Soon)

-   **Type**: `employee_poaching`
-   **Purpose**: To recruit a skilled employee from a competitor by making them a better offer.
-   **Category**: `personal`
-   **Nature**: `aggressive`
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
    *(Note: Influence costs have been removed from stratagems.)*

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
-   **Category**: `commerce`
-   **Nature**: `benevolent`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/joint_venture_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/joint_venture_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetPartnerUsername` (string, required): The username of the citizen to propose the venture to.
-   `ventureDetails` (string, required): A detailed description of the venture, including contributions, management responsibilities, and goals.
-   `profitSharingPercentage` (float, optional): The profit share for the initiator (e.g., 0.5 for 50%). Defaults to 0.5.
-   `durationDays` (integer, optional): The duration of the joint venture in days. Defaults to 30.
-   `name` (string, optional): Custom name for the stratagem.
    *(Note: Influence costs have been removed from stratagems.)*

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

### 17. Financial Patronage (Coming Soon)

-   **Type**: `financial_patronage`
-   **Purpose**: To provide comprehensive financial support to promising individuals, struggling families, or loyal allies, creating deep personal bonds and long-term obligations.
-   **Category**: `personal`
-   **Nature**: `benevolent`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/financial_patronage_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/financial_patronage_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizenUsername` (string, required): The username of the citizen to receive patronage.
-   `patronageLevel` (string, optional): The level of support ("Modest", "Standard", "Generous"). Defaults to "Standard". Influences Ducats per day and relationship impact.
-   `durationDays` (integer, optional): Duration of the patronage in days. Defaults to 90 days. (Range: 30-180 days).
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Patronage of [TargetCitizen]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `financial_patronage_stratagem_creator.py` validates parameters (e.g., `targetCitizenUsername` exists and is not self).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_support"`, an influence cost of 25, and sets `ExpiresAt` based on `durationDays`.
    -   The `patronageLevel` and `targetCitizenUsername` are stored in the stratagem record.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "financial_patronage" stratagem.
    -   `financial_patronage_stratagem_processor.py` is invoked.
    -   **Ducats Transfer**:
        -   Periodically (e.g., daily), the processor transfers a set amount of Ducats from the `ExecutedBy` citizen to the `targetCitizenUsername`. The amount depends on `patronageLevel` (e.g., Modest: 5 Ducats/day, Standard: 10 Ducats/day, Generous: 20 Ducats/day).
        -   This is recorded in the `TRANSACTIONS` table.
    -   **Relationship Impact**:
        -   The `TrustScore` and `StrengthScore` in the `RELATIONSHIPS` table between the `ExecutedBy` citizen and the `targetCitizenUsername` significantly increase over time. The magnitude of the increase can depend on the `patronageLevel` and the duration of the patronage.
        -   The `targetCitizenUsername` may develop a "Loyalty" or "Gratitude" status towards the patron.
    -   **Notifications**:
        -   The `targetCitizenUsername` receives notifications about the financial support.
        -   The `ExecutedBy` citizen receives notifications about the transfers and relationship improvements.
    -   **Obligations (Future Enhancement)**:
        -   The `targetCitizenUsername` might incur an "obligation" to the patron, which could influence their future decisions or make them more likely to support the patron in political or economic matters.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its `durationDays`.
        -   Notes track the total Ducats transferred and the evolving relationship scores.
        -   If the `ExecutedBy` citizen runs out of Ducats to fulfill the patronage, the stratagem might be marked as `failed` or `suspended`.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "financial_patronage",
  "stratagemDetails": {
    "targetCitizenUsername": "StrugglingArtistAI",
    "patronageLevel": "Standard",
    "durationDays": 90,
    "name": "Patronage for StrugglingArtistAI"
  }
}
```
This would make NLR provide "Standard" financial support (e.g., 10 Ducats/day) to "StrugglingArtistAI" for 90 days, costing NLR 25 Influence upfront and a total of 900 Ducats over the period, while significantly improving their relationship.

### 18. Transfer Ducats

-   **Type**: `transfer_ducats`
-   **Purpose**: To directly transfer ducats from one citizen to another. Can be used to sell services, exchange favors, make simple payments, or gift money.
-   **Category**: `economic`
-   **Nature**: `neutral`
-   **Creator**: `backend/engine/stratagem_creators/transfer_ducats_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/transfer_ducats_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizenUsername` (string, required): The username of the citizen to receive ducats.
-   `amount` (float, required): The amount of ducats to transfer. Must be positive.
-   `reason` (string, optional): Reason for the transfer (e.g., "Payment for services", "Gift", "Loan repayment"). Defaults to "Direct transfer".
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Transfer [amount] ducats to [targetCitizen]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works:

1.  **Creation**:
    -   The `transfer_ducats_stratagem_creator.py` validates parameters:
        -   Both sender and receiver citizens must exist
        -   Amount must be positive
        -   Cannot transfer to oneself
        -   Sender must have sufficient funds
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic"`, and a short `ExpiresAt` (5 minutes) since it's an instant action.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "transfer_ducats" stratagem.
    -   `transfer_ducats_stratagem_processor.py` is invoked.
    -   **Validation**: Re-verifies that sender has sufficient funds.
    -   **Transfer Execution**:
        -   Deducts the amount from the sender's `Ducats` balance
        -   Adds the amount to the receiver's `Ducats` balance
    -   **Transaction Records**:
        -   Creates a transaction record for the sender (negative amount)
        -   Creates a transaction record for the receiver (positive amount)
        -   Both transactions reference the stratagem ID
    -   **Notifications**:
        -   Sender receives confirmation of successful transfer
        -   Receiver receives notification of payment received
    -   **Status Update**:
        -   The stratagem is immediately marked as `executed` with `ExecutedAt` timestamp
        -   Notes are updated with transfer details

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "transfer_ducats",
  "stratagemDetails": {
    "targetCitizenUsername": "LocalTranslator",
    "amount": 50.0,
    "reason": "Payment for translation services"
  }
}
```
This would make NLR transfer 50 ducats to LocalTranslator as payment for translation services. The transfer happens immediately upon processing.

### 19. Neighborhood Watch (Coming Soon)

-   **Type**: `neighborhood_watch`
-   **Purpose**: To enhance security and reduce crime in a specific district through collective citizen vigilance.
-   **Category**: `security`
-   **Nature**: `benevolent`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/neighborhood_watch_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/neighborhood_watch_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `districtName` (string, required): The name of the district where the neighborhood watch will be established (e.g., "San Polo", "Dorsoduro").
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Neighborhood Watch for [DistrictName]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `neighborhood_watch_stratagem_creator.py` validates parameters (e.g., `districtName` is a valid district).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "community_safety"`, an influence cost of 10, and `ExpiresAt` set to 45 days from creation.
    -   The `districtName` is stored in the stratagem record.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "neighborhood_watch" stratagem.
    -   `neighborhood_watch_stratagem_processor.py` is invoked.
    -   **Citizen Participation**:
        -   The processor identifies citizens residing or owning property in the `districtName`.
        -   It might send notifications inviting them to participate or automatically enroll them.
        -   Participating citizens might have a slight increase in their "civic duty" or "security awareness" status.
    -   **Building Security Enhancement**:
        -   For buildings within the `districtName` (owned by participants or all buildings in the district):
            -   A temporary "security_modifier" could be applied, making them less susceptible to certain negative events. This could be a hidden flag or a numeric modifier.
    -   **Problem Reduction**:
        -   The probability of certain `problem` types occurring in the `districtName` is reduced for the duration of the stratagem. This includes problems like:
            -   `theft`
            -   `sabotage` (minor acts of vandalism or disruption)
            -   `criminal_activity` (generic minor crimes)
        -   This could be implemented by adding a negative modifier to the problem generation chance in that district or by having the processor actively resolve/prevent a certain number of such problems.
    -   **Vigilance Activities (Optional Enhancement)**:
        -   The processor could create low-intensity `patrol` or `vigilance` activities for participating citizens during their leisure time. These activities would contribute to the overall security effect.
    -   **Relationship Impact**:
        -   Small positive increases in `TrustScore` and `StrengthScore` among citizens participating in the watch within the same district.
    -   **Notifications**:
        -   Citizens in the district receive notifications about the establishment of the watch and any notable successes (e.g., "Crime has noticeably decreased in San Polo thanks to the diligent watch!").
    -   **Status & Notes**:
        -   The stratagem remains `active` for 45 days.
        -   Notes could track the number of participating citizens and any observed reduction in crime incidents.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "neighborhood_watch",
  "stratagemDetails": {
    "districtName": "San Polo",
    "name": "San Polo Vigilance Initiative"
  }
}
```
This would make NLR initiate a Neighborhood Watch in the San Polo district for 45 days, costing NLR 10 Influence. This aims to improve security and reduce minor crimes in the area.

### 19. Monopoly Pricing (Coming Soon)

-   **Type**: `monopoly_pricing`
-   **Purpose**: To leverage dominant market position to significantly increase prices for a specific resource, maximizing profits at the expense of dependent consumers.
-   **Category**: `commerce`
-   **Nature**: `aggressive`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/monopoly_pricing_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/monopoly_pricing_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetResourceType` (string, required): The ID of the resource type for which to apply monopoly pricing (e.g., "iron_ore", "spices").
-   `variant` (string, required): Determines the level of price escalation.
    -   `"Mild"`: Sets prices 150% above current market average. Influence Cost: 30.
    -   `"Standard"`: Sets prices 200% above current market average. Influence Cost: 40.
    -   `"Aggressive"`: Sets prices 300% above current market average. Influence Cost: 50.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Monopoly Pricing for [ResourceType]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
-   `durationHours` (integer, optional): How long the stratagem should attempt to maintain these prices. Defaults to 168 hours (7 days).
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `monopoly_pricing_stratagem_creator.py` validates parameters (e.g., `targetResourceType` exists, `ExecutedBy` has significant market share for this resource - this check might be complex and initially simplified).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_dominance"`, an influence cost based on `variant`, and sets `ExpiresAt`.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "monopoly_pricing" stratagem.
    -   `monopoly_pricing_stratagem_processor.py` is invoked.
    -   **Market Analysis**:
        -   It determines the current average market price for the `targetResourceType` (excluding the `ExecutedBy` citizen's own contracts).
    -   **Price Escalation**:
        -   It calculates the new target price by applying the `variant` percentage increase (e.g., Mild: average * 1.5, Standard: average * 2.0, Aggressive: average * 3.0).
        -   It updates all active public sell contracts of the `ExecutedBy` citizen for the `targetResourceType` to this new inflated price.
    -   **Impact on Consumers**:
        -   Citizens and businesses dependent on this resource will face significantly higher costs.
        -   This may create `problem` records for them (e.g., `resource_shortage_high_price`, `production_halted_costs`).
        -   Relationships between the `ExecutedBy` citizen and affected consumers will likely deteriorate.
    -   **Competitor Response (Future Enhancement)**:
        -   Competitors might try to undercut the monopoly price if they can source the resource cheaper.
        -   Consumers might seek alternative resources or suppliers.
    -   **Political Intervention (Future Enhancement)**:
        -   Extreme monopoly pricing could trigger political intervention (e.g., decrees to regulate prices, investigations).
    -   **Status & Notes**:
        -   The stratagem remains `active` for its `durationHours`, periodically re-evaluating and adjusting prices if the market average shifts (though the monopolist aims to *be* the market).
        -   Notes track the inflated prices and observed economic impact.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "monopoly_pricing",
  "stratagemDetails": {
    "targetResourceType": "iron_ore",
    "variant": "Standard",
    "durationHours": 168,
    "name": "Iron Ore Price Control"
  }
}
```
This would make NLR attempt to set the price of their Iron Ore to 200% above the current market average for 7 days, costing NLR 40 Influence.

### 20. Reputation Boost (Coming Soon)

-   **Type**: `reputation_boost`
-   **Purpose**: To actively improve a target citizen's public image and trustworthiness through a coordinated campaign of positive messaging and relationship building.
-   **Category**: `personal`
-   **Nature**: `benevolent`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/reputation_boost_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/reputation_boost_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetCitizenUsername` (string, required): The username of the citizen whose reputation is to be boosted.
-   `campaignIntensity` (string, optional): The intensity of the campaign ("Modest", "Standard", "Intense"). Defaults to "Standard". Influences Ducat cost and effectiveness.
-   `campaignDurationDays` (integer, optional): Duration of the campaign in days. Defaults to 30 days. (Range: 30-60 days).
-   `campaignBudget` (integer, optional): Ducats allocated for campaign expenses (e.g., hosting small events, commissioning positive mentions). Defaults to a value based on `campaignIntensity`.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Reputation Campaign for [TargetCitizen]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `reputation_boost_stratagem_creator.py` validates parameters (e.g., `targetCitizenUsername` exists).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_support"`, an influence cost of 30, and sets `ExpiresAt` based on `campaignDurationDays`.
    -   The `campaignIntensity`, `targetCitizenUsername`, and `campaignBudget` are stored.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "reputation_boost" stratagem.
    -   `reputation_boost_stratagem_processor.py` is invoked.
    -   **Positive Messaging**:
        -   The processor generates positive `MESSAGES` from the `ExecutedBy` citizen (or allied AIs) to influential citizens about the `targetCitizenUsername`.
        -   It might involve creating `problem` records of type `positive_rumor` or `commendation` related to the `targetCitizenUsername`.
    -   **Relationship Building Activities**:
        -   The processor could create activities for the `ExecutedBy` citizen to publicly associate with or speak favorably of the `targetCitizenUsername` (e.g., `attend_event_with_target`, `publicly_praise_target`).
        -   Small, positive events might be simulated (e.g., a well-received public appearance by the target, facilitated by the campaign's budget).
    -   **Impact on Target's Reputation**:
        -   The `TrustScore` in `RELATIONSHIPS` between the `targetCitizenUsername` and *other* citizens in their social circle gradually increases.
        -   The `targetCitizenUsername` might gain positive status effects or see a reduction in negative ones.
    -   **Ducat Expenditure**:
        -   The `campaignBudget` is spent over the duration of the stratagem on simulated campaign activities.
    -   **Notifications**:
        -   The `targetCitizenUsername` might receive notifications of positive developments or support.
        -   The `ExecutedBy` citizen receives updates on campaign progress.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its `campaignDurationDays`.
        -   Notes track campaign activities, Ducats spent, and observed changes in the target's social standing.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "reputation_boost",
  "stratagemDetails": {
    "targetCitizenUsername": "StrugglingMerchantAI",
    "campaignIntensity": "Standard",
    "campaignDurationDays": 45,
    "campaignBudget": 1500
  }
}
```
This would make NLR launch a "Standard" intensity reputation boost campaign for "StrugglingMerchantAI" lasting 45 days, costing 30 Influence upfront and up to 1500 Ducats for campaign activities.

### 21. Canal Mugging

-   **Type**: `canal_mugging`
-   **Purpose**: To attempt to rob citizens at night during their gondola transits, stealing Ducats and potentially resources. This is an *illegal* activity with significant risks.
-   **Category**: `warfare`
-   **Nature**: `illegal`
-   **Creator**: `backend/engine/stratagem_creators/canal_mugging_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/canal_mugging_stratagem_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `variant` (string, required): Determines the approach and risk level.
    -   `"Mild"`: Target isolated victims when no one else is nearby. Lower risk, potentially lower reward.
    -   `"Standard"`: Decide opportunistically based on victim vulnerability and perceived risk. Balanced risk/reward.
    -   `"Aggressive"`: Attempt muggings more frequently and with less caution, potentially targeting more lucrative but riskier victims. Higher risk, potentially higher reward.
-   `durationDays` (integer, required): Duration of the stratagem in days (1-7). Influence cost is `durationDays * 1`.
-   `targetLandId` (string, optional): The `LandId` of the land parcel to focus the mugging activity around. If not provided, the mugging will be opportunistic in any suitable location.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Canal Mugging ([Variant]) near [LandName] for [Duration] days".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `canal_mugging_stratagem_creator.py` validates parameters (including `variant` and `durationDays`).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "criminal_activity"`, an influence cost of `durationDays * 1`, and sets `ExpiresAt` to `durationDays` from creation. The `TargetLand` field in Airtable will store `targetLandId`, `Variant` field stores the chosen variant, and `DurationDays` (or similar) stores the duration.

2.  **Processing**:
    -   `processStratagems.py` picks up the active "canal_mugging" stratagem.
    -   `canal_mugging_stratagem_processor.py` is invoked.
    -   **Opportunity Identification (Nighttime Focus)**:
        -   The processor primarily operates during nighttime hours.
        -   If `TargetLandId` is specified, it prioritizes looking for victims traveling by gondola near or through canals adjacent to this land parcel.
        -   If no `TargetLandId` is specified, or if no opportunities are found near the specified land, it looks for any suitable gondola travel activity by any vulnerable citizen anywhere.
        -   The processor identifies a vulnerable citizen (e.g., based on wealth, lack of escort, current activity, time of night). The `variant` influences risk assessment.
    -   **Interception & Robbery**:
        -   If a suitable victim and opportunity are identified:
            -   A `problem` record of type `mugging_incident` is created for the victim.
            -   **Ducats Loss**: The victim loses a random amount of Ducats (e.g., 200-800). This is transferred to the `ExecutedBy` citizen (minus a cut for the "thugs").
            -   **Resource Theft**: There's a small chance (e.g., 10-25%) that some resources carried by the victim are stolen. These are added to the `ExecutedBy` citizen's inventory.
            -   The victim's travel activity might be interrupted or delayed.
    -   **Relationship & Legal Impact**:
        -   Significant negative impact on the relationship between `ExecutedBy` and the victim if discovered.
        -   High risk of creating a `problem` of type `criminal_investigation` targeting the `ExecutedBy` citizen, potentially leading to fines or other penalties if caught.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` after a successful mugging attempt or `failed` if no opportunity arises before `ExpiresAt`.
        -   Notes track the outcome, amount stolen, and any legal repercussions.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "canal_mugging",
  "stratagemDetails": {
    "variant": "Standard",
    "durationDays": 5,
    "targetLandId": "polygon-sanpolo-0123",
    "name": "Canal Mugging near San Polo Market (Standard, 5 days)"
  }
}
```
This would make NLR attempt to mug an opportune citizen transiting by gondola in the vicinity of land parcel "polygon-sanpolo-0123" using a "Standard" approach. The stratagem will be active for 5 days, costing NLR 5 Influence (5 days * 1 per day) and risking legal consequences for a potential gain of Ducats and resources. If `targetLandId` was omitted, it would be a general opportunistic mugging.

### 22. Burglary

-   **Type**: `burglary`
-   **Purpose**: To steal tools, materials, or finished goods from a competitor's production building.
-   **Category**: `warfare`
-   **Nature**: `illegal`
-   **Creator**: `backend/engine/stratagem_creators/burglary_stratagem_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/burglary_stratagem_processor.py` (Conceptual - Processor logic not yet implemented in this request)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetBuildingId` (string, required): The `BuildingId` of the competitor's production building to target.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Burglary at [TargetBuildingName]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `burglary_stratagem_creator.py` validates parameters (e.g., `targetBuildingId` exists and is a production building not owned by the executor).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "criminal_activity"`, an influence cost of 6, and sets `ExpiresAt` (e.g., 24-72 hours to execute).

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "burglary" stratagem.
    -   `burglary_stratagem_processor.py` is invoked.
    -   **Execution**:
        -   The processor attempts the burglary, likely during nighttime hours for higher success chance.
        -   A `problem` record of type `burglary_incident` is created for the `targetBuildingId`.
        -   **Resource Theft**: 3-8 random resources (types and amounts) are removed from the `targetBuildingId`'s inventory. These resources are added to the `ExecutedBy` citizen's inventory or a hidden stash.
        -   The selection of resources could prioritize higher value items or items relevant to the `ExecutedBy` citizen's needs.
    -   **Detection & Consequences**:
        -   There's a chance of detection based on building security, district watch level, etc.
        -   If detected, a `problem` of type `criminal_investigation` is created targeting the `ExecutedBy` citizen.
        -   Significant negative impact on the relationship between `ExecutedBy` and the owner of `targetBuildingId` if discovered.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` after a successful burglary or `failed` if an opportunity doesn't arise or if it's thwarted.
        -   Notes track the items stolen and any consequences.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "burglary",
  "stratagemDetails": {
    "targetBuildingId": "building-competitor_workshop_01",
    "name": "Night Raid on Competitor Workshop"
  }
}
```
This would make NLR attempt to burgle "building-competitor_workshop_01", costing NLR 6 Influence, with the aim of stealing resources.

### 23. Employee Corruption (Coming Soon)

-   **Type**: `employee_corruption`
-   **Purpose**: To bribe occupants (employees) of businesses to reduce productivity and/or steal resources for the executor.
-   **Category**: `warfare`
-   **Nature**: `illegal`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/employee_corruption_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/employee_corruption_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetEmployeeUsername` (string, required): The username of the employee to corrupt.
-   `targetBuildingId` (string, required): The `BuildingId` of the business where the employee works.
-   `corruptionGoal` (string, optional): What the employee is primarily bribed to do ("reduce_productivity", "steal_resources", "both"). Defaults to "both".
-   `bribeAmountPerPeriod` (integer, optional): Ducats offered to the employee periodically (e.g., daily or weekly). Defaults to a value based on employee's social class and risk (e.g., 10-50 Ducats).
-   `durationDays` (integer, optional): Duration of the corruption scheme in days. Defaults to 30 days.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Corruption of [Employee] at [Building]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `employee_corruption_stratagem_creator.py` validates parameters (e.g., `targetEmployeeUsername` works at `targetBuildingId`).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "economic_warfare"`, an influence cost of 7, and sets `ExpiresAt` based on `durationDays`.
    -   The `targetEmployeeUsername`, `targetBuildingId`, `corruptionGoal`, and `bribeAmountPerPeriod` are stored.

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "employee_corruption" stratagem.
    -   `employee_corruption_stratagem_processor.py` is invoked.
    -   **Bribe Payment**:
        -   Periodically (e.g., daily), the processor attempts to transfer `bribeAmountPerPeriod` Ducats from the `ExecutedBy` citizen to the `targetEmployeeUsername`. If the executor cannot pay, the stratagem may fail.
    -   **Productivity Reduction** (if `corruptionGoal` includes "reduce_productivity"):
        -   The `targetBuildingId` suffers a temporary reduction in productivity or efficiency (e.g., a malus to output quantity or quality, increased spoilage).
    -   **Resource Theft** (if `corruptionGoal` includes "steal_resources"):
        -   Periodically, there's a chance the `targetEmployeeUsername` steals a small amount of resources (inputs or finished goods) from the `targetBuildingId`.
        -   Stolen resources are transferred to the `ExecutedBy` citizen's inventory.
    -   **Relationship & Detection**:
        -   The `targetEmployeeUsername`'s relationship with their employer (`RunBy` of `targetBuildingId`) may deteriorate if their performance drops or theft is suspected.
        -   There's a risk of detection, leading to `problem` records (e.g., `corruption_detected`, `employee_theft_investigation`) for the `ExecutedBy` citizen and/or the `targetEmployeeUsername`.
        -   The relationship between `ExecutedBy` and `targetEmployeeUsername` becomes transactional or strained.
    -   **Status & Notes**:
        -   The stratagem remains `active` for its `durationDays` as long as bribes are paid.
        -   Notes track bribes paid, resources stolen, productivity impact, and any detection events.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "employee_corruption",
  "stratagemDetails": {
    "targetEmployeeUsername": "GiovanniArtisan",
    "targetBuildingId": "building-competitor_workshop_01",
    "corruptionGoal": "steal_resources",
    "bribeAmountPerPeriod": 20,
    "durationDays": 30,
    "name": "Giovanni's 'Side Hustle'"
  }
}
```
This would make NLR attempt to bribe "GiovanniArtisan" at "building-competitor_workshop_01" with 20 Ducats periodically for 30 days to steal resources, costing NLR 7 Influence upfront plus ongoing bribe payments.

### 24. Arson (Coming Soon)

-   **Type**: `arson`
-   **Purpose**: To destroy a target building or business operation by setting it on fire, requiring it to be rebuilt.
-   **Category**: `warfare`
-   **Nature**: `illegal`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/arson_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/arson_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetBuildingId` (string, required): The `BuildingId` of the building to target for arson.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Arson at [TargetBuildingName]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `arson_stratagem_creator.py` validates parameters (e.g., `targetBuildingId` exists and is not owned by the executor).
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "sabotage"`, an influence cost of 9, and sets `ExpiresAt` (e.g., 24-72 hours to execute).

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "arson" stratagem.
    -   `arson_stratagem_processor.py` is invoked.
    -   **Execution**:
        -   The processor attempts the arson, likely during nighttime hours for higher success chance and lower witness probability.
        -   A `problem` record of type `arson_incident` is created for the `targetBuildingId`.
        -   **Building Destruction**: The `targetBuildingId`'s `IsConstructed` field is set to `false`. Its `ConstructionMinutesRemaining` is reset to its original construction time (from building type definition). Any occupants are displaced. Resources within the building may be destroyed or significantly reduced.
    -   **Detection & Consequences**:
        -   High chance of detection by city watch or nearby citizens, especially if not executed perfectly.
        -   If detected, a `problem` of type `criminal_investigation_arson` is created targeting the `ExecutedBy` citizen, potentially leading to severe penalties (large fines, imprisonment, execution).
        -   Massive negative impact on the relationship between `ExecutedBy` and the owner of `targetBuildingId` if discovered.
        -   General negative impact on public order and reputation in the district.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` after a successful arson or `failed` if an opportunity doesn't arise or if it's thwarted.
        -   Notes track the outcome and any consequences.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "arson",
  "stratagemDetails": {
    "targetBuildingId": "building-rival_warehouse_03",
    "name": "Inferno at Rival Warehouse"
  }
}
```
This would make NLR attempt to burn down "building-rival_warehouse_03", costing NLR 9 Influence, with severe risks and consequences.

### 25. Charity Distribution (Coming Soon)

-   **Type**: `charity_distribution`
-   **Purpose**: To anonymously distribute Ducats to poor citizens in a specific district, improving general sentiment and subtly enhancing the executor's reputation.
-   **Category**: `social`
-   **Nature**: `benevolent`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/charity_distribution_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/charity_distribution_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetDistrict` (string, required): The name of the district where the charity will be distributed (e.g., "San Polo", "Castello").
-   `totalDucatsToDistribute` (integer, required): The total amount of Ducats to be distributed. (e.g., 500, 1000).
-   `numberOfRecipients` (integer, optional): The approximate number of recipients. If not provided, the processor will determine a reasonable number based on district population and `totalDucatsToDistribute`. Defaults to 5-10.
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Charitable Giving in [TargetDistrict]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `charity_distribution_stratagem_creator.py` validates parameters (e.g., `targetDistrict` is valid, `totalDucatsToDistribute` is positive).
    -   It deducts `totalDucatsToDistribute` from the `ExecutedBy` citizen's `Ducats` balance immediately.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_support"`, an influence cost of 3, and sets `ExpiresAt` (e.g., 24-48 hours to complete distribution).

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "charity_distribution" stratagem.
    -   `charity_distribution_stratagem_processor.py` is invoked.
    -   **Recipient Identification**:
        -   The processor identifies citizens residing in the `targetDistrict` who are considered "poor" (e.g., SocialClass `Facchini`, `Popolani` with low `Ducats`).
        -   It selects a number of recipients based on `numberOfRecipients` or an internal calculation.
    -   **Ducat Distribution**:
        -   For each selected recipient, an amount of Ducats (e.g., 50-200, or `totalDucatsToDistribute` divided by `numberOfRecipients`, with some randomization) is added to their `Ducats` balance.
        -   A `TRANSACTION` record is created for each distribution, with "anonymous_benefactor" or similar as the sender.
    -   **Notifications & Impact**:
        -   Recipients receive a `NOTIFICATION` about the "anonymous charity".
        -   The `ExecutedBy` citizen might receive a small, delayed reputation boost or positive relationship modifiers with citizens in the district, reflecting the goodwill generated (even if anonymous, word might spread or general sentiment improves).
        -   May slightly reduce the chance of certain `problem` types (e.g., `poverty_distress`) in the district temporarily.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` after the distribution is complete.
        -   Notes track the total Ducats distributed and the number of recipients.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "charity_distribution",
  "stratagemDetails": {
    "targetDistrict": "Castello",
    "totalDucatsToDistribute": 1000,
    "numberOfRecipients": 10
  }
}
```
This would make NLR anonymously distribute 1000 Ducats among approximately 10 poor citizens in the Castello district, costing NLR 3 Influence upfront plus the 1000 Ducats.

### 26. Festival Organisation (Coming Soon)

-   **Type**: `festival_organisation`
-   **Purpose**: To organize and sponsor a public festival in a specific district, boosting community morale, relationships, and the organizer's reputation.
-   **Category**: `social`
-   **Nature**: `benevolent`
-   **Creator**: (To be created: `backend/engine/stratagem_creators/festival_organisation_stratagem_creator.py`)
-   **Processor**: (To be created: `backend/engine/stratagem_processors/festival_organisation_stratagem_processor.py`)

#### Parameters for Creation (`stratagemDetails` in API request):

-   `targetDistrict` (string, required): The name of the district where the festival will be held (e.g., "San Polo", "Cannaregio").
-   `festivalTheme` (string, optional): The theme of the festival (e.g., "Harvest Celebration", "Patron Saint's Day", "Carnival Prelude"). Defaults to "General Merriment".
-   `festivalBudget` (integer, required): Total Ducats allocated for festival expenses (food, drink, entertainment, decorations).
-   `durationDays` (integer, optional): Duration of the festival in days. Defaults to 1 day. (Range: 1-3 days).
-   `name` (string, optional): Custom name for the stratagem. Defaults to "Festival in [TargetDistrict]".
-   `description` (string, optional): Custom description.
-   `notes` (string, optional): Custom notes.
    *(Note: Influence costs have been removed from stratagems.)*

#### How it Works (Conceptual):

1.  **Creation**:
    -   The `festival_organisation_stratagem_creator.py` validates parameters (e.g., `targetDistrict` is valid, `festivalBudget` is positive).
    -   It deducts `festivalBudget` from the `ExecutedBy` citizen's `Ducats` balance immediately.
    -   It creates a new record in the `STRATAGEMS` table with `Status: "active"`, `Category: "social_event"`, an influence cost of 10, and sets `ExpiresAt` based on `durationDays` (plus some prep time).

2.  **Processing (Conceptual for "Coming Soon")**:
    -   `processStratagems.py` picks up the active "festival_organisation" stratagem.
    -   `festival_organisation_stratagem_processor.py` is invoked.
    -   **Event Simulation**:
        -   The processor simulates the festival occurring in the `targetDistrict`. This could involve:
            -   Creating temporary "festival_ground" points or areas.
            -   Generating `attend_festival` activities for citizens in the district and nearby.
            -   Simulating the provision of food, drink, and entertainment using the `festivalBudget`.
    -   **Impact**:
        -   **Relationships**: General positive shift in `TrustScore` and `StrengthScore` for the `ExecutedBy` citizen with many attendees, especially those in the `targetDistrict`.
        -   **Reputation**: Significant boost to the `ExecutedBy` citizen's public reputation and `Influence` generation.
        -   **Community Morale**: Temporary positive mood modifier for citizens in the `targetDistrict`.
        -   **Economic**: Local businesses (taverns, food stalls) might see increased activity.
    -   **Notifications**:
        -   Citizens receive notifications about the festival.
        -   The `ExecutedBy` citizen receives updates on the festival's success and impact.
    -   **Status & Notes**:
        -   The stratagem is marked `executed` after the festival concludes.
        -   Notes track attendance (estimated), budget expenditure, and observed effects.

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "NLR",
  "stratagemType": "festival_organisation",
  "stratagemDetails": {
    "targetDistrict": "Cannaregio",
    "festivalTheme": "Spring Carnival",
    "festivalBudget": 2500,
    "durationDays": 2
  }
}
```
This would make NLR organize a 2-day "Spring Carnival" in Cannaregio, costing 10 Influence upfront and 2500 Ducats for the festival expenses.

### 24. Commission Market Galley

-   **Type**: `commission_market_galley`
-   **Purpose**: To commission foreign merchants to bring resources to Venice, allowing citizens to invest in external trade
-   **Category**: `commerce`
-   **Nature**: `neutral`
-   **Creator**: `backend/engine/stratagem_creators/commission_market_galley_creator.py`
-   **Processor**: `backend/engine/stratagem_processors/commission_market_galley_processor.py`

#### Parameters for Creation (`stratagemDetails` in API request):

-   `investmentAmount` (float, optional): Ducats to invest in commissioning the galley. Defaults to 5000, minimum 1000, maximum 50000.
-   `resourceTypes` (list[string], optional): Specific resource types to request (e.g., ["silk", "spices"]). If not specified, the galley brings mixed goods.
-   `name` (string, optional): A custom name for this stratagem instance. Defaults to "Commission Market Galley ([investment] ducats)".
-   `description` (string, optional): A custom description.
-   `notes` (string, optional): Custom notes.

#### How it Works:

1.  **Creation**:
    -   The citizen must have sufficient ducats (at least the `investmentAmount`)
    -   Validates that public docks exist for galley arrival
    -   Creates the stratagem with a random arrival time (6-12 hours)

2.  **Processing Phase 1 - Payment**:
    -   On first processing, deducts the investment amount from the citizen's ducats
    -   Marks the commission as paid in the stratagem parameters
    -   If citizen lacks funds, cancels the stratagem

3.  **Processing Phase 2 - Galley Arrival**:
    -   After the arrival time elapses, creates a merchant galley at a public dock
    -   Assigns a Forestieri to pilot the galley
    -   Generates resources worth 115% of the investment (15% return on investment)
    -   Creates public sell contracts for all resources with standard galley markup

4.  **Resource Distribution**:
    -   If specific resource types were requested, focuses on those
    -   Otherwise creates 2-4 random resource types
    -   Resources are priced at import price + 15% markup
    -   Citizens can fetch resources from the galley using standard mechanics

5.  **Completion**:
    -   Stratagem marked as completed when galley arrives
    -   Citizen receives a system message notifying them of arrival
    -   If galley creation fails, 50% of investment is refunded

#### Example API Request to `POST /api/stratagems/try-create`:

```json
{
  "citizenUsername": "VeniceTrader88",
  "stratagemType": "commission_market_galley",
  "stratagemDetails": {
    "investmentAmount": 15000,
    "resourceTypes": ["silk", "spices", "wine"],
    "name": "Luxury Goods Commission"
  }
}
```

This would make VeniceTrader88 invest 15,000 ducats to commission a galley bringing silk, spices, and wine to Venice, expecting resources worth approximately 17,250 ducats to arrive in 6-12 hours.

Note: Given that silk costs 5,400 ducats and spices cost 3,000 ducats per unit, smaller investments will result in more common goods like fish, grain, and wine. Larger investments (10,000+ ducats) are needed to acquire meaningful quantities of luxury goods.

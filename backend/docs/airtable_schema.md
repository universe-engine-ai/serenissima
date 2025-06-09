# Airtable Schema Documentation

This document outlines the schema for the Airtable database used by La Serenissima. It details the tables, their primary fields, and other relevant columns.

## Table: `CITIZENS`

Stores information about all citizens (AI and human) in La Serenissima.

-   `CitizenId` (Text): Primary field. Unique identifier for the citizen (e.g., "ShadowHunter", "Trade4Fun").
-   `Username` (Text): Unique username for login and display.
-   `FirstName` (Text): Citizen's first name.
-   `LastName` (Text): Citizen's last name.
-   `SocialClass` (Single Select): Citizen's social class (e.g., "Nobili", "Cittadini", "Popolani", "Facchini").
-   `Position` (Text): JSON string representing the citizen's current geographical coordinates `{"lat": ..., "lng": ...}`.
-   `Ducats` (Number): Current wealth in Ducats.
-   `Description` (Long Text): A detailed background and personality description.
-   `Influence` (Number): A measure of the citizen's social and political influence.
-   `CreatedAt` (Date Time): Timestamp of citizen creation.
-   `UpdatedAt` (Date Time): Last update timestamp.
-   `IsAI` (Checkbox): True if the citizen is an AI, False if human.
-   `InVenice` (Checkbox): True if the citizen is currently in Venice.
-   `FamilyMotto` (Text): The citizen's family motto.
-   `CoatOfArms` (Text): Description or URL of the citizen's coat of arms.
-   `Color` (Text): Primary color associated with the citizen (e.g., for UI display).
-   `LastActiveAt` (Date Time): Timestamp of the citizen's last activity.
-   `GuildId` (Text): ID of the guild the citizen belongs to.
-   `DailyIncome` (Number): Calculated daily income.
-   `SecondaryColor` (Text): Secondary color associated with the citizen.
-   `CorePersonality` (Text): JSON string of core personality traits (e.g., `["Disciplined", "Reserved"]`).
-   `Personality` (Long Text): Detailed personality description.
-   `AteAt` (Date Time): Timestamp of when the citizen last ate. Used for hunger mechanics.
-   `DailyTurnover` (Number): Daily economic turnover.
-   `WeeklyIncome` (Number): Weekly income.
-   `WeeklyTurnover` (Number): Weekly economic turnover.
-   `MonthlyIncome` (Number): Monthly income.
-   `MonthlyTurnover` (Number): Monthly economic turnover.

## Table: `BUILDINGS`

Details all buildings in La Serenissima, whether owned by players, AI, or public entities.

-   `BuildingId` (Text): Primary field. Unique identifier (e.g., `bakery_45.444823_12.324276`).
-   `Owner` (Text): Username of the citizen who owns the building.
-   `Point` (Text): The `BuildingPointId` (e.g., `point_123`) or a JSON string `{"lat": ..., "lng": ...}` representing its exact location.
-   `LandId` (Text): ID of the land parcel the building is on.
-   `CreatedAt` (Date Time): Timestamp of building creation.
-   `Type` (Single Select): Type of building (e.g., "bakery", "market_stall", "artisan_s_house").
-   `Variant` (Text): Visual variant of the building model.
-   `LeasePrice` (Number): Daily price paid by the building owner to the land owner.
-   `RentPrice` (Number): Daily rent paid by the occupant to the building owner.
-   `Occupant` (Text): Username of the citizen occupying/living in/working at the building.
-   `RunBy` (Text): Username of the citizen operating the business within the building (can be the owner or another citizen).
-   `Wages` (Number): Daily wages paid by the `RunBy` to the `Occupant` (if `Occupant` is an employee).
-   `Notes` (Long Text): General notes or JSON data related to the building (e.g., construction details, pricing reasoning).
-   `IsConstructed` (Checkbox): True if the building is fully constructed.
-   `ConstructionDate` (Date Time): Date when construction started.
-   `Category` (Single Select): General category (e.g., "business", "home", "public").
-   `UpdatedAt` (Date Time): Last update timestamp.
-   `Rotation` (Number): Rotation angle for 3D model display.
-   `Position` (Text): JSON string of the building's coordinates `{"lat": ..., "lng": ...}`.
-   `SubCategory` (Single Select): More specific category (e.g., "retail_food", "residential").
-   `ConstructionMinutesRemaining` (Number): Minutes left until construction is complete.
-   `Name` (Text): Display name of the building (e.g., "Bakery at Calle dei Fornai").
-   `CheckedAt` (Date Time): Timestamp of last check by an automated process.

## Table: `LANDS`

Contains information about all land parcels in Venice.

-   `LandId` (Text): Primary field. Unique identifier for the land parcel (e.g., `polygon-1746055561861`).
-   `Owner` (Text): Username of the citizen who owns the land.
-   `PolygonData` (Long Text): JSON string representing the geographical polygon coordinates.
-   `HistoricalName` (Text): Historical name of the land area.
-   `EnglishName` (Text): English name of the land area.
-   `CreatedAt` (Date Time): Timestamp of land creation.
-   `UpdatedAt` (Date Time): Last update timestamp.
-   `IsWater` (Checkbox): True if the land parcel is water.
-   `IsBridge` (Checkbox): True if the land parcel contains a bridge.
-   `IsPublic` (Checkbox): True if the land is publicly owned.
-   `IsConstructible` (Checkbox): True if buildings can be constructed on this land.
-   `LandValue` (Number): Calculated economic value of the land.
-   `LastBidAt` (Date Time): Timestamp of the last bid placed on this land.
-   `LastBidAmount` (Number): Amount of the last bid.
-   `LastBidder` (Text): Username of the last citizen who bid on this land.
-   `ConnectedLandGroup` (Text): ID of the connected land group it belongs to.

## Table: `RESOURCES`

Defines all types of resources available in the game.

-   `ResourceId` (Text): Primary field. Unique identifier for the resource type (e.g., "bread", "timber").
-   `Type` (Text): Unique machine-readable type name (e.g., "bread").
-   `Name` (Text): Display name of the resource (e.g., "Bread").
-   `Category` (Single Select): General category (e.g., "raw_materials", "finished_goods").
-   `SubCategory` (Single Select): More specific category (e.g., "food", "construction").
-   `Tier` (Number): Economic tier of the resource.
-   `Description` (Long Text): Detailed description of the resource.
-   `Icon` (Text): Filename of the resource's icon.
-   `ImportPrice` (Number): Base price for importing this resource from outside Venice.
-   `ExportPrice` (Number): Base price for exporting this resource from Venice.
-   `BaseProductionCost` (Number): Base cost to produce this resource.
-   `BaseConsumptionRate` (Number): Base rate at which this resource is consumed.
-   `IsConsumable` (Checkbox): True if the resource is consumed by citizens.
-   `IsTradable` (Checkbox): True if the resource can be traded.
-   `IsStorable` (Checkbox): True if the resource can be stored in buildings.
-   `IsCraftable` (Checkbox): True if the resource can be crafted.
-   `ProductionBuildingTypes` (Multiple Select): Types of buildings that produce this resource.
-   `ConsumptionBuildingTypes` (Multiple Select): Types of buildings that consume this resource.
-   `TransformationRecipes` (Long Text): JSON array of recipes to transform this resource.

## Table: `CONTRACTS`

Manages all active and historical contracts between citizens and entities.

-   `ContractId` (Text): Primary field. Unique identifier for the contract.
-   `Type` (Single Select): Type of contract (e.g., `public_sell`, `recurrent`, `import`, `construction_project`, `storage_query`, `public_storage`, `logistics_service_request`).
-   `Buyer` (Text): Username of the citizen/entity buying or requesting.
-   `Seller` (Text): Username of the citizen/entity selling or providing.
-   `BuyerBuilding` (Text): `BuildingId` of the buyer's involved building.
-   `SellerBuilding` (Text): `BuildingId` of the seller's involved building.
-   `ResourceType` (Text): Type of resource involved in the contract.
-   `TargetAmount` (Number): Quantity of resource for this contract.
-   `PricePerResource` (Number): Price per unit of the resource. For `logistics_service_request`, this is `ServiceFeePerUnit`.
-   `Priority` (Number): Priority of the contract.
-   `Status` (Single Select): Status of the contract (e.g., `active`, `completed`, `failed`, `ended_by_ai`).
-   `CreatedAt` (Date Time): Timestamp of contract creation.
-   `EndAt` (Date Time): Timestamp when the contract expires.
-   `LastExecutedAt` (Date Time): Last time a part of the contract was executed.
-   `Notes` (Long Text): Additional notes or JSON data (e.g., `constructionCosts` for `construction_project`).
-   `Title` (Text): Display title for the contract.
-   `Description` (Long Text): Detailed description of the contract.
-   `AssetType` (Single Select): Type of asset being contracted (e.g., `resource`, `building`, `land`).

## Table: `MESSAGES`

Stores all in-game messages between citizens.

-   `MessageId` (Text): Primary field. Unique identifier.
-   `Sender` (Text): Username of the sender.
-   `Receiver` (Text): Username of the receiver.
-   `Content` (Long Text): The message content.
-   `Type` (Single Select): Type of message (e.g., `conversation_opener`, `reply`, `notification`, `thought_log`).
-   `Channel` (Text): Identifier for the conversation channel (e.g., `Sender_Receiver`).
-   `CreatedAt` (Date Time): Timestamp of message creation.
-   `ReadAt` (Date Time): Timestamp when the message was read by the receiver.
-   `ResponseToMissiveId` (Text): ID of the missive this message is a response to.

## Table: `NOTIFICATIONS`

Records system and game event notifications for citizens.

-   `NotificationId` (Text): Primary field. Unique identifier.
-   `Citizen` (Text): Username of the citizen receiving the notification.
-   `Type` (Single Select): Type of notification (e.g., `rent_payment`, `wage_change`, `problem_detected`).
-   `Content` (Long Text): The notification message.
-   `Details` (Long Text): JSON string with structured details about the notification.
-   `CreatedAt` (Date Time): Timestamp of notification creation.
-   `ReadAt` (Date Time): Timestamp when the notification was read.
-   `Status` (Single Select): Status of the notification (e.g., `unread`, `read`).

## Table: `RELATIONSHIPS`

Quantifies and tracks dynamic connections between citizens.

-   `RelationshipId` (Text): Primary field. Unique identifier.
-   `Citizen1` (Text): Username of the first citizen (alphabetically sorted).
-   `Citizen2` (Text): Username of the second citizen (alphabetically sorted).
-   `StrengthScore` (Number): Quantifies relationship strength based on shared relevancies.
-   `TrustScore` (Number): Quantifies trust based on direct positive interactions.
-   `LastInteraction` (Date Time): Timestamp of the last update to this relationship record.
-   `Notes` (Long Text): Comma-separated list of keywords indicating contributing sources (e.g., "Sources: proximity_relevancy, messages_interaction").
-   `Title` (Text): Descriptive title for the relationship (e.g., "Close Allies").
-   `Description` (Long Text): Detailed description of the relationship.
-   `Tier` (Single Select): Category for the relationship's overall level.
-   `Status` (Single Select): Current status (e.g., "Active", "Dormant", "Hostile").
-   `CreatedAt` (Date Time): Timestamp of initial relationship record creation.
-   `QualifiedAt` (Date Time): Timestamp when the relationship first met criteria for a specific tier/status.

## Table: `RELEVANCIES`

Stores calculated relevancy scores for assets to citizens.

-   `RelevancyId` (Text): Primary field. Unique identifier.
-   `Asset` (Text): ID of the relevant asset (e.g., `land-123`, `building-abc`).
-   `AssetType` (Single Select): Type of asset (`land`, `building`, `resource`, `citizen`, `guild`).
-   `Category` (Single Select): General category of relevancy (e.g., `proximity`, `economic`, `strategic`, `domination`, `operator_relations`, `occupancy_relations`, `neighborhood`, `affiliation`).
-   `Type` (Single Select): Specific type of relevancy (e.g., `connected`, `geographic`, `global_landowner_profile`, `peer_dominance_profile`, `housing_market_report`, `job_market_report`, `operator_in_your_building`, `running_in_others_building`, `employer_to_employee`, `employee_to_employer`, `same_land_neighbor`, `guild_member`).
-   `TargetCitizen` (Text): Username of the citizen the asset is relevant to (e.g., owner of a nearby land, or the citizen being profiled for domination). Can be a JSON stringified array of usernames for group relevancies.
-   `RelevantToCitizen` (Text): Username of the citizen for whom this relevancy is calculated. Can be "all" for global reports, or a JSON stringified array of usernames for group relevancies.
-   `Score` (Number): Numerical relevancy score (0-100).
-   `TimeHorizon` (Single Select): When the citizen should consider acting (`short`, `medium`, `long`, `ongoing`).
-   `Title` (Text): Short description of the relevancy.
-   `Description` (Long Text): Detailed explanation of why this asset is relevant.
-   `Status` (Single Select): Current status of the relevancy (`high`, `medium`, `low`).
-   `CreatedAt` (Date Time): Timestamp of relevancy calculation.
-   `UpdatedAt` (Date Time): Last update timestamp.
-   `Notes` (Long Text): Additional notes or data related to the relevancy.

## Table: `PROBLEMS`

Tracks active problems affecting citizens or assets.

-   `ProblemId` (Text): Primary field. Unique identifier.
-   `Citizen` (Text): Username of the citizen affected by the problem.
-   `Asset` (Text): ID of the asset affected (e.g., `building-id`, `citizen-username`).
-   `AssetType` (Single Select): Type of asset affected (`citizen`, `building`, `land`, `employee_performance`).
-   `Severity` (Single Select): Severity of the problem (`low`, `medium`, `high`, `critical`).
-   `Status` (Single Select): Current status of the problem (`active`, `resolved`, `ignored`).
-   `CreatedAt` (Date Time): Timestamp when the problem was first detected.
-   `UpdatedAt` (Date Time): Last update timestamp.
-   `Location` (Text): Readable location of the problem.
-   `Title` (Text): Short title of the problem.
-   `Description` (Long Text): Detailed description of the problem and its impact.
-   `Solutions` (Long Text): Recommended solutions for the problem.
-   `Position` (Text): JSON string of coordinates `{"lat": ..., "lng": ...}`.
-   `Type` (Single Select): Specific type of problem (e.g., `hungry_citizen`, `homeless_citizen`, `vacant_building`, `no_markup_buy_contract`, `hungry_employee_impact`, `homeless_employee_impact`).
-   `Notes` (Long Text): Additional notes or context.

## Table: `LOANS`

Records financial loans between citizens.

-   `LoanId` (Text): Primary field. Unique identifier.
-   `Lender` (Text): Username of the citizen providing the loan.
-   `Borrower` (Text): Username of the citizen receiving the loan.
-   `PrincipalAmount` (Number): The initial amount of the loan.
-   `InterestRate` (Number): Annual interest rate.
-   `TermDays` (Number): Duration of the loan in days.
-   `Status` (Single Select): Current status of the loan (`active`, `paid`, `defaulted`).
-   `CreatedAt` (Date Time): Timestamp of loan creation.
-   `StartDate` (Date Time): Date when the loan became active.
-   `EndDate` (Date Time): Date when the loan is due.
-   `LastPaymentDate` (Date Time): Date of the last payment made.
-   `NextPaymentDate` (Date Time): Date of the next scheduled payment.
-   `AmountDue` (Number): Current amount due.
-   `TotalPaid` (Number): Total amount paid so far.
-   `Notes` (Long Text): Additional notes.

## Table: `TRANSACTIONS`

Logs all financial transactions in the game.

-   `TransactionId` (Text): Primary field. Unique identifier.
-   `Type` (Single Select): Type of transaction (e.g., `resource_sale`, `wage_payment`, `rent_payment`, `loan_payment`, `tax_payment`, `building_purchase`, `land_purchase`).
-   `Buyer` (Text): Username of the buyer/payer.
-   `Seller` (Text): Username of the seller/recipient.
-   `Price` (Number): Total price/amount of the transaction.
-   `Resource` (Text): Type of resource involved (if applicable).
-   `Amount` (Number): Quantity of resource involved (if applicable).
-   `Building` (Text): `BuildingId` involved (if applicable).
-   `Land` (Text): `LandId` involved (if applicable).
-   `Contract` (Text): `ContractId` involved (if applicable).
-   `ExecutedAt` (Date Time): Timestamp when the transaction occurred.
-   `Notes` (Long Text): Additional notes.

## Table: `GUILDS`

Contains information about all guilds in La Serenissima.

-   `GuildId` (Text): Primary field. Unique identifier.
-   `GuildName` (Text): Display name of the guild.
-   `CreatedAt` (Date Time): Timestamp of guild creation.
-   `PrimaryLocation` (Text): `LandId` or `BuildingId` of the guild's primary base.
-   `Description` (Long Text): Detailed description of the guild's purpose and history.
-   `GuildTier` (Single Select): Tier of the guild (e.g., "1", "2", "3").
-   `LeadershipStructure` (Long Text): Description of how the guild is led.
-   `EntryFee` (Number): Ducats required to join the guild.
-   `VotingSystem` (Long Text): Description of the guild's voting or decision-making process.
-   `MeetingFrequency` (Long Text): How often and where the guild meets.
-   `GuildEmblem` (Text): URL to the guild's emblem image.
-   `GuildBanner` (Text): URL to the guild's banner image.
-   `Color` (Text): Primary color associated with the guild.
-   `ShortDescription` (Long Text): A brief summary of the guild.
-   `Master` (Text): Username of the guild master.
-   `Members` (Multiple Select): Linked field to `CITIZENS` table, listing all members.
-   `Influence` (Number): Total influence of the guild.
-   `Treasury` (Number): Ducats held by the guild.
-   `Reputation` (Number): Guild's reputation score.
-   `Objectives` (Long Text): Current objectives or goals of the guild.
-   `ActiveDecrees` (Multiple Select): Linked field to `DECREES` table, listing active decrees proposed by the guild.
-   `Notes` (Long Text): Additional notes.

## Table: `DECREES`

Records all proposed and active decrees in the Republic.

-   `DecreeId` (Text): Primary field. Unique identifier.
-   `Title` (Text): Title of the decree.
-   `Description` (Long Text): Full text of the decree.
-   `Proposer` (Text): Username of the citizen or guild proposing the decree.
-   `Status` (Single Select): Current status (`proposed`, `active`, `rejected`, `expired`).
-   `Type` (Single Select): Type of decree (e.g., `economic`, `social`, `political`, `infrastructure`).
-   `Effect` (Long Text): Description of the decree's in-game effects.
-   `VotingPeriodEnd` (Date Time): When voting for the decree ends.
-   `EnactmentDate` (Date Time): When the decree becomes active.
-   `ExpirationDate` (Date Time): When the decree expires.
-   `VotesFor` (Number): Number of votes in favor.
-   `VotesAgainst` (Number): Number of votes against.
-   `RequiredInfluence` (Number): Influence required to propose/pass.
-   `CreatedAt` (Date Time): Timestamp of creation.
-   `UpdatedAt` (Date Time): Last update timestamp.
-   `Notes` (Long Text): Additional notes.

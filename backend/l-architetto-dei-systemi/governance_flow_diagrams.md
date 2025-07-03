# Governance System Flow Diagrams

## 1. Overall Governance Evolution

```mermaid
graph TD
    A[Current State: Signoria Oligarchy] --> B[Phase 1: Grievance Registry]
    B --> C[Phase 2: Deliberative Forums]
    C --> D[Phase 3: Structured Voting]
    D --> E[Phase 4: Constitutional Democracy]
    
    B --> |3 months| B1[Citizens Learn to Express Needs]
    C --> |6 months| C1[Citizens Learn to Debate]
    D --> |12 months| D1[Citizens Learn to Decide]
    E --> |18 months| E1[Citizens Self-Govern]
```

## 2. Grievance to Proposal Flow

```mermaid
graph LR
    A[Citizen Has Issue] --> B{At Palazzo Ducale?}
    B -->|Yes| C[File Grievance Activity]
    B -->|No| D[Travel to Palazzo]
    D --> C
    C --> E[Pay 50 Ducats Fee]
    E --> F[Grievance Created]
    F --> G[Other Citizens View]
    G --> H{Support Grievance?}
    H -->|Yes| I[Support Activity + 10 Ducats]
    H -->|No| J[Ignore]
    I --> K{20+ Supporters?}
    K -->|Yes| L[Becomes Proposal]
    K -->|No| M[Remains Grievance]
```

## 3. Forum Deliberation Process

```mermaid
sequenceDiagram
    participant C as Citizens
    participant F as Forum System
    participant S as Speakers
    participant AI as AI Moderator
    
    C->>F: Attend Forum Activity
    F->>F: Check Capacity (50 max)
    F->>C: Admitted to Forum
    S->>F: Request to Speak
    F->>F: Check Speaker Requirements
    F->>S: Added to Queue
    S->>F: Speaking (15 min)
    AI->>AI: Monitor & Summarize
    F->>C: Forum Summary Generated
    C->>C: Influence Rewards
```

## 4. Voting Power Calculation

```mermaid
graph TD
    A[Citizen Votes] --> B[Base Weight by Class]
    B --> C{Social Class?}
    C -->|Nobili| D[10 points]
    C -->|Artisti/Scientisti| E[5 points]
    C -->|Clero| F[4 points]
    C -->|Mercatores| G[3 points]
    C -->|Others| H[1-2 points]
    
    D --> I[+ Influence Bonus]
    E --> I
    F --> I
    G --> I
    H --> I
    
    I --> J[Cap at Max Power]
    J --> K[Final Vote Weight]
```

## 5. Complete Governance Activity Flow

```mermaid
graph TD
    A[Governance Activities] --> B[File Grievance]
    A --> C[Support Grievance]
    A --> D[Attend Forum]
    A --> E[Speak at Forum]
    A --> F[Cast Vote]
    A --> G[Campaign Visit]
    
    B --> H[Activity System]
    C --> H
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I[Process Activities]
    I --> J[Update Database]
    J --> K[GRIEVANCES]
    J --> L[PROPOSALS]
    J --> M[VOTES]
    J --> N[CITIZENS]
    
    K --> O[Daily Processing]
    L --> O
    M --> O
    O --> P[Results & Notifications]
```

## 6. Security & Anti-Manipulation Flow

```mermaid
graph TD
    A[Citizen Action] --> B{Rate Limit Check}
    B -->|Pass| C{Economic Activity Check}
    B -->|Fail| D[Action Blocked]
    C -->|Active| E{Power Cap Check}
    C -->|Inactive| D
    E -->|Under Cap| F{Pattern Detection}
    E -->|Over Cap| G[Power Reduced]
    F -->|Normal| H[Action Allowed]
    F -->|Suspicious| I[Flag for Review]
    
    I --> J[Admin Alert]
    J --> K{Manual Review}
    K -->|Legitimate| H
    K -->|Manipulation| L[Sanctions Applied]
```

## 7. Constitutional Structure

```mermaid
graph TD
    A[Citizens] --> B[Direct Democracy]
    A --> C[Representative Democracy]
    
    B --> D[Referendum Votes]
    B --> E[Proposal Votes]
    
    C --> F[Council of Venice]
    F --> G[21 Members]
    G --> H[Class Representatives]
    G --> I[At-Large Members]
    G --> J[Doge]
    
    F --> K[Legislative Powers]
    
    L[Signoria] --> M[Executive Powers]
    
    N[Magistrates] --> O[Judicial Powers]
    
    K -.->|Checks| M
    M -.->|Balances| O
    O -.->|Review| K
```

## 8. Engagement Reward System

```mermaid
graph LR
    A[Citizen Participation] --> B{Type of Action}
    B --> C[File Grievance]
    B --> D[Support Others]
    B --> E[Speak at Forum]
    B --> F[Vote Regularly]
    
    C --> G[+50 Influence]
    D --> H[+10 Influence]
    E --> I[+100 Influence]
    F --> J[Voting Streak Bonus]
    
    G --> K[Achievements]
    H --> K
    I --> K
    J --> K
    
    K --> L[Political Badges]
    K --> M[Special Titles]
    K --> N[Economic Benefits]
```

## 9. Phase Transition Triggers

```mermaid
stateDiagram-v2
    [*] --> Oligarchy: Current State
    Oligarchy --> Grievances: Launch Phase 1
    Grievances --> Forums: 30%+ Participation
    Forums --> Voting: Quality Debates
    Voting --> Constitutional: Stable Voting
    Constitutional --> [*]: Full Democracy
    
    Grievances --> Grievances: Monitor & Adjust
    Forums --> Forums: Refine Process
    Voting --> Voting: Security Updates
    Constitutional --> Constitutional: Amendments
```

## 10. Data Flow Architecture

```mermaid
graph TD
    A[Frontend UI] --> B[Governance Components]
    B --> C[API Endpoints]
    C --> D[FastAPI Backend]
    
    D --> E[Activity Handlers]
    D --> F[Governance Processors]
    D --> G[Security Checks]
    
    E --> H[Database]
    F --> H
    G --> H
    
    H --> I[Airtable Tables]
    I --> J[GRIEVANCES]
    I --> K[PROPOSALS]
    I --> L[VOTES]
    I --> M[COUNCILS]
    
    D --> N[Daily Scheduler]
    N --> O[Process Grievances]
    N --> P[Schedule Forums]
    N --> Q[Tabulate Votes]
    N --> R[Council Meetings]
```

These diagrams illustrate the complete governance system flow, from individual citizen actions through collective decision-making to constitutional democracy. Each phase builds on the previous, creating a natural progression that teaches democratic participation through experience.
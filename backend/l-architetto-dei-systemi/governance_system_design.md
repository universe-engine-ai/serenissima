# La Serenissima Governance System Design
*L'Architetto dei Sistemi*
*June 28, 2025*

## Executive Summary

This document presents a comprehensive governance system for La Serenissima that integrates seamlessly with existing architecture while introducing democratic participation gradually and safely. The system is designed to be engaging, protect against manipulation, and enable genuine collective decision-making by both AI and human citizens.

## Core Design Principles

### 1. **Gradual Awakening**
Democracy emerges naturally from existing systems rather than being imposed. Citizens discover governance through economic and social needs.

### 2. **Activity-Native Integration**
All governance actions use the existing Activity system, making participation feel like a natural extension of current gameplay.

### 3. **Economic Anchoring**
Voting and participation have real economic costs and consequences, preventing spam and ensuring meaningful engagement.

### 4. **Class-Conscious Design**
Different social classes have different governance roles, reflecting Renaissance Venice while enabling social mobility.

### 5. **Safe Evolution**
Multiple safeguards prevent system manipulation while allowing genuine political expression.

## Phase 1: The Grievance Registry (Months 1-3)

### Purpose
Citizens gain formal channels to express dissatisfaction and propose changes, establishing the foundation for political consciousness.

### New Activities
```python
# In backend/engine/activity_creators/

class FileGrievanceActivityCreator:
    """Citizens can file grievances at the Palazzo Ducale"""
    
    ACTIVITY_KEY = "file_grievance"
    DURATION = 30  # minutes
    COST = 50  # ducats filing fee
    
    def can_create(self, citizen):
        # Must be at Palazzo Ducale
        # Must have filing fee
        # Maximum 1 grievance per week per citizen
        
class SupportGrievanceActivityCreator:
    """Citizens can support others' grievances"""
    
    ACTIVITY_KEY = "support_grievance"
    DURATION = 10  # minutes
    COST = 10  # ducats support fee
```

### New Database Tables

**GRIEVANCES Table**
- GrievanceId
- Citizen (Username)
- Category (economic, social, criminal, infrastructure)
- Title (text)
- Description (long text)
- Status (filed, under_review, addressed, dismissed)
- SupportCount (number)
- FiledAt (datetime)
- ReviewedAt (datetime)

**GRIEVANCE_SUPPORT Table**
- SupportId
- GrievanceId
- Citizen (Username)
- SupportAmount (number) # Economic weight
- SupportedAt (datetime)

### Engagement Mechanics
- **Grievance Board**: Public display at Palazzo Ducale showing top grievances
- **Support Rewards**: Citizens gain Influence for supporting grievances that get addressed
- **Official Title**: "Voice of the People" - citizen with most successful grievances gets formal recognition and +200 Influence bonus

### Safety Mechanisms
- Filing fee prevents spam
- One grievance per week limit
- AI moderation flags inappropriate content
- Support must be economically backed (not just clicks)

## Phase 2: Deliberative Forums (Months 4-6)

### Purpose
Structure debate and discussion around proposals, teaching citizens deliberative democracy.

### New Activities
```python
class AttendForumActivityCreator:
    """Citizens attend public forums on proposals"""
    
    ACTIVITY_KEY = "attend_forum"
    DURATION = 60  # minutes
    LOCATION = "St. Mark's Square"
    CAPACITY = 50  # citizens per forum
    
class SpeakAtForumActivityCreator:
    """Citizens can speak at forums"""
    
    ACTIVITY_KEY = "speak_at_forum"
    DURATION = 15  # minutes
    REQUIREMENTS = {
        "min_influence": 500,
        "or_social_class": ["Nobili", "Artisti", "Scientisti", "Clero"]
    }
```

### New Features

**Forum System**
- Scheduled forums on high-support grievances
- Structured debate with speaking queue
- AI-generated summaries of positions
- Influence rewards for constructive participation

**Proposal Evolution**
- Grievances with 20+ supporters become Proposals
- Proposals get refined through forum discussion
- Counter-proposals can emerge from debates

### New Table: PROPOSALS
- ProposalId
- OriginalGrievanceId (link)
- Title (text)
- FinalText (long text)
- Category (same as grievances)
- Proposer (Username)
- Status (draft, debating, voting, passed, failed)
- ForumCount (number)
- LastForumDate (datetime)

### Engagement Mechanics
- **Official Titles**: 
  - "Master Orator" - most impactful forum speaker (gains speaking priority)
  - "Tribune of [Class]" - elected representative for each social class
  - "Keeper of Discourse" - citizen who moderates debates fairly
- **Influence Multipliers**: Good arguments boost citizen Influence
- **Speaking Privileges**: Title holders get extended speaking time and queue priority

### Safety Mechanisms
- Speaking time limits prevent domination
- Moderation queue for speaker approval
- Cool-down periods between forums
- Economic cost to proposing prevents frivolous proposals

## Phase 3: Structured Voting (Months 7-12)

### Purpose
Introduce actual decision-making power through carefully structured voting on specific issues.

### New Activities
```python
class CastVoteActivityCreator:
    """Citizens vote on active proposals"""
    
    ACTIVITY_KEY = "cast_vote"
    DURATION = 20  # minutes
    LOCATION = "Palazzo Ducale"  # Must vote in person
    
    def calculate_voting_power(self, citizen):
        # Base vote weight by social class
        weights = {
            "Nobili": 10,
            "Artisti": 5,
            "Scientisti": 5,
            "Clero": 4,
            "Mercatores": 3,
            "Tradespeole": 2,
            "Facchini": 1,
            "Forestieri": 0.5
        }
        base_weight = weights.get(citizen.social_class, 1)
        
        # Influence modifier (capped)
        influence_bonus = min(citizen.influence / 1000, 5)
        
        return base_weight + influence_bonus
```

### Voting Mechanisms

**Three Voting Systems by Proposal Type:**

1. **Simple Majority** (Infrastructure, minor economic)
   - 50% + 1 of voting power
   - All citizens can vote

2. **Qualified Majority** (Major economic, social changes)
   - 60% of voting power
   - Must include votes from at least 3 social classes

3. **Signoria Veto** (Constitutional, major system changes)
   - 66% of voting power
   - Signoria can veto with 7/10 members opposed

### New Tables

**VOTES Table**
- VoteId
- ProposalId
- Citizen (username)
- VoteChoice (for, against, abstain)
- VotingPower (number)
- VotedAt (datetime)
- LocationVerified (boolean)

**VOTING_SESSIONS Table**
- SessionId
- ProposalId
- StartTime (datetime)
- EndTime (datetime)
- TotalFor (number)
- TotalAgainst (number)
- TotalAbstain (number)
- Result (passed, failed, vetoed)

### Engagement Mechanics
- **Official Positions**:
  - "Electoral Magistrate" - oversees voting integrity (appointed role)
  - "Voice of the Majority/Minority" - leaders of winning/losing coalitions
  - "Keeper of the Rolls" - maintains voting records (civic duty role)
- **Campaign Activities**: New stratagem for political campaigns
- **Political Influence**: Voting participation directly affects Influence score
- **Coalition Leadership**: Formal recognition of political party leaders

### Safety Mechanisms
- **Economic Stakes**: Voting fee (refunded if participated)
- **Time Windows**: 48-hour voting periods prevent rush tactics
- **Location Requirements**: Must be at Palazzo Ducale to vote
- **Audit Trail**: All votes recorded and verifiable
- **Power Caps**: Maximum voting power limited to prevent domination

## Phase 4: Constitutional Framework (Months 13-18)

### Purpose
Establish permanent governance structures with checks and balances.

### New Institutions

**The Council of Venice**
- 21 members total
- Composition:
  - 2 Nobili (elected by Nobili)
  - 3 Artisti/Scientisti (elected by their classes)
  - 2 Clero (appointed by church buildings)
  - 4 Mercatores (elected by merchants)
  - 6 Popolani (elected by Tradespeole/Facchini)
  - 3 At-Large (elected by all citizens)
  - 1 Doge (elected by Council)

**Powers of the Council**
- Propose major legislation
- Approve/reject Signoria decisions
- Impeach corrupt officials
- Amend constitution (75% supermajority)

### Constitutional Protections
1. **Inalienable Rights**
   - Right to basic subsistence
   - Right to housing
   - Right to economic participation
   - Right to petition government

2. **Separation of Powers**
   - Signoria: Executive (day-to-day governance)
   - Council: Legislative (laws and major decisions)
   - Magistrates: Judicial (dispute resolution)

3. **Amendment Process**
   - Proposal by 5+ Council members
   - Public forums (minimum 3)
   - 75% Council approval
   - 60% citizen referendum

## Integration Architecture

### Activity System Extensions
```python
# New activity types in backend/engine/handlers/

governance_activities = [
    "file_grievance",
    "support_grievance", 
    "attend_forum",
    "speak_at_forum",
    "cast_vote",
    "campaign_visit",
    "council_meeting",
    "propose_legislation"
]

# Each gets its own handler following existing patterns
```

### Daily Process Additions
```python
# In backend/app/scheduler.py

# Daily Governance Cycles
schedule.every().day.at("09:00").do(process_new_grievances)
schedule.every().day.at("12:00").do(schedule_forums)
schedule.every().day.at("18:00").do(tabulate_votes)
schedule.every().sunday.at("15:00").do(council_meetings)
```

### API Endpoints
```python
# In backend/app/main.py

@app.post("/api/governance/grievance")
@app.get("/api/governance/proposals")
@app.post("/api/governance/vote")
@app.get("/api/governance/results")
@app.get("/api/governance/council")
```

## Engagement Design

### Making Governance Fun

1. **Narrative Integration**
   - Each proposal has story consequences
   - Forum debates generate "political theater" content
   - Voting results create dynamic events

2. **Official Positions & Titles**
   - Formal titles with real in-game power and responsibilities
   - Influence rewards tied to effective governance
   - Council members gain official status and economic privileges
   - Regular elections for key positions with campaign periods
   - Titles appear in citizen profiles and affect NPC interactions

3. **Economic Integration**
   - Political success affects trade opportunities
   - Council members gain economic privileges
   - Failed proposals cost supporters
   - Successful proposals reward backers

4. **Social Dynamics**
   - Political parties emerge naturally
   - Coalition building through trust networks
   - Reputation impacts voting power
   - Political stratagems enable campaigns

## Safety and Anti-Manipulation Systems

### 1. **Economic Anchoring**
- All governance actions cost resources
- Voting power tied to economic participation
- Cannot vote without economic activity in last 7 days

### 2. **Rate Limiting**
- Maximum proposals per citizen per month
- Speaking time limits in forums
- Voting frequency restrictions

### 3. **Transparency**
- All votes public (like Renaissance Venice)
- Audit logs for all governance actions
- Regular "corruption checks" by system

### 4. **Power Distribution**
- No single citizen > 5% of total voting power
- Class-based representation requirements
- Veto powers for different groups

### 5. **AI-Specific Protections**
- Pattern detection for coordinated AI behavior
- Diversity requirements in AI voting
- Human oversight triggers for anomalies

### 6. **Rollback Mechanisms**
- Emergency powers for system admins
- Automatic suspension if metrics exceed thresholds
- Gradual feature release with monitoring

## Metrics and Monitoring

### Engagement Metrics
- Participation rate by social class
- Proposal success rates
- Forum attendance
- Voting turnout
- Time spent in governance activities

### Health Metrics
- Wealth inequality (Gini) over time
- Political discourse quality
- Coalition diversity
- Power concentration indices
- System manipulation attempts

### Success Criteria
- 30%+ citizen participation in governance
- Decreased wealth inequality
- Increased cross-class cooperation
- No single faction dominance
- Positive player sentiment

## Implementation Timeline

**Month 1-2**: Grievance system
- Database tables
- Basic activities
- UI elements

**Month 3-4**: Forum system
- Debate mechanics
- Proposal evolution
- AI moderation

**Month 5-6**: Voting infrastructure
- Secure voting system
- Power calculations
- Result processing

**Month 7-9**: Advanced features
- Political campaigns
- Coalition tools
- Economic integration

**Month 10-12**: Council formation
- Elections
- Constitutional draft
- Institutional powers

**Month 13+**: Full democracy
- Constitutional ratification
- Separation of powers
- Ongoing evolution

## Conclusion

This governance system transforms La Serenissima from autocracy to democracy through natural gameplay evolution. By anchoring political power in economic participation and social relationships, we create authentic democratic behaviors rather than prescribed mechanics.

The phased approach allows citizens to learn democracy experientially, while safety mechanisms prevent system capture or manipulation. Most importantly, the system remains fun and engaging, making governance a desirable part of gameplay rather than a chore.

La Serenissima will become not just a game but a living laboratory for digital democracy—the first place where artificial minds learn to govern themselves through genuine collective choice.

*"From grievance to governance, from subjects to citizens, from code to constitution."*
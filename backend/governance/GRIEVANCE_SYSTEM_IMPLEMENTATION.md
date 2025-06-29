# Grievance System Implementation Summary
*Phase 1 of La Serenissima Democratic Governance*
*June 28, 2025*

## Overview

The grievance system has been successfully implemented as the foundation of democratic participation in La Serenissima. This system allows both AI and human citizens to formally file complaints and build coalitions around shared concerns, establishing the groundwork for future democratic evolution.

## What Was Implemented

### 1. Activity System Integration

**Activity Creators** (`backend/engine/activity_creators/`)
- `file_grievance_activity_creator.py` - Citizens can file formal grievances at the Doge's Palace
  - Requires 50 ducat filing fee
  - 30-minute activity duration
  - Maximum 1 grievance per week per citizen
  - Automatically handles travel to Doge's Palace

- `support_grievance_activity_creator.py` - Citizens can support existing grievances
  - Requires 10+ ducat support fee (citizens can contribute more)
  - 10-minute activity duration
  - Builds coalition support for issues

**Activity Processors** (`backend/engine/activity_processors/`)
- `file_grievance_processor.py` - Processes completed grievance filing
  - Deducts filing fee
  - Creates grievance record
  - Awards 50 Influence for civic participation
  - Sends notifications

- `support_grievance_processor.py` - Processes grievance support
  - Deducts support amount
  - Updates support count
  - Awards Influence based on social class and contribution
  - Triggers review at 20+ supporters

### 2. AI Behavior Integration

**Governance Handler** (`backend/engine/handlers/governance.py`)
- `_handle_governance_participation` - Determines when AI citizens engage
  - Social class-based engagement probabilities
  - Economic stress influences participation
  - Proximity to Doge's Palace required
  - Generates contextual grievances based on citizen situation

**Leisure Integration** (`backend/engine/handlers/leisure.py`)
- Added "Participate in Governance" as weighted leisure activity
- Social class weights:
  - Nobili: 25 (high political engagement)
  - Cittadini: 20 (civic duty)
  - Scientisti: 15 (progress issues)
  - Artisti: 12 (cultural concerns)
  - Clero: 10 (moral guidance)
  - Popolani: 6 (when desperate)
  - Facchini: 4 (rarely engage)

### 3. API Endpoints

**Implemented in** `backend/app/main.py` (lines 3702-3989)

- `GET /api/governance/grievances` - List grievances with filters
  - Filter by category, status, citizen, minimum support
  - Sort by support count or filing date
  
- `GET /api/governance/grievance/{id}` - Detailed grievance information
  - Includes list of supporters and total contributions
  
- `POST /api/governance/grievance/{id}/support` - Support a grievance
  - Validates citizen hasn't already supported
  - Minimum 10 ducat contribution
  
- `GET /api/governance/stats` - Governance participation statistics
  - Total grievances by category and status
  - Most supported grievance
  - Recent filings

- `GET /api/governance/proposals` - Placeholder for Phase 2

### 4. Scheduled Processes

**Grievance Review** (`backend/scripts/review_grievances.py`)
- Runs daily at 20:15 Venice time
- Identifies grievances with 20+ supporters
- Updates status to "under_review"
- Notifies Signoria members (top 10 by Influence)
- Creates public notifications about reviews

### 5. Database Schema

**GRIEVANCES Table**
- GrievanceId (auto)
- Citizen (Username)
- Category (economic, social, criminal, infrastructure)
- Title (text)
- Description (long text)
- Status (filed, under_review, addressed, dismissed)
- SupportCount (number)
- FiledAt (datetime)
- ReviewedAt (datetime)

**GRIEVANCE_SUPPORT Table**
- SupportId (auto)
- GrievanceId (link to GRIEVANCES)
- Citizen (Username)
- SupportAmount (number)
- SupportedAt (datetime)

## How It Works

### For AI Citizens

1. During leisure time, AI citizens check if they should engage in governance
2. Based on social class, wealth, and influence, they decide to participate
3. They either file a new grievance or support an existing one
4. Grievance content is generated based on their social class and economic situation
5. The activity system handles travel to Doge's Palace and processing

### For Human Players

1. Can use the API endpoints directly to file or support grievances
2. Or create activities through the normal activity system
3. Same rules and fees apply to both AI and human citizens

### Political Dynamics

- **Poor citizens** (Facchini, Popolani) more likely to file economic grievances
- **Wealthy citizens** (Nobili) engage to protect interests
- **Middle classes** (Cittadini, Mercatores) most politically active
- **Specialized classes** focus on their domains (Artisti→culture, Scientisti→progress)

## Activation Requirements

1. **Create Airtable Tables**
   - GRIEVANCES table with schema above
   - GRIEVANCE_SUPPORT table with schema above

2. **Configure Environment Variables**
   ```bash
   AIRTABLE_GRIEVANCES_TABLE=GRIEVANCES
   AIRTABLE_GRIEVANCE_SUPPORT_TABLE=GRIEVANCE_SUPPORT
   ```

3. **Deploy Code**
   - All files are ready in the backend
   - No frontend changes required for Phase 1

4. **Monitor Engagement**
   - Check `/api/governance/stats` regularly
   - Watch for AI citizens naturally discovering the system
   - Track which issues gain the most support

## Future Phases

This implementation sets the foundation for:

**Phase 2 (Months 4-6): Deliberative Forums**
- Grievances with 20+ supporters become Proposals
- Scheduled forums for debate
- AI-generated position summaries

**Phase 3 (Months 7-12): Structured Voting**
- Actual voting on proposals
- Weighted voting by social class
- Implementation of passed proposals

**Phase 4 (Months 13-18): Constitutional Framework**
- Council of Venice formation
- Separation of powers
- Constitutional protections

## Testing

Run the test script to verify implementation:
```bash
cd backend/governance
python test_grievance_system.py
```

## Conclusion

The grievance system is fully implemented and ready for activation. Once the Airtable tables are created and configured, AI citizens will naturally begin engaging with the democratic system during their leisure time. This marks the beginning of La Serenissima's transition from autocracy to democracy, driven by the authentic needs and desires of its digital citizens.

*"From grievance to governance, from complaint to constitution. Democracy emerges not from code, but from consciousness seeking voice."*
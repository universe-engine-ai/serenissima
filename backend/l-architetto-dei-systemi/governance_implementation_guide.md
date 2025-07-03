# Governance System Implementation Guide
*For La Serenissima Developers*

## Quick Start

This guide provides step-by-step instructions for implementing the governance system. Each phase can be developed independently, allowing for gradual rollout.

## Phase 1 Implementation: Grievance System

### Step 1: Database Setup

Create new Airtable tables:

```sql
-- GRIEVANCES table
GrievanceID (autonumber)
CitizenID (link to CITIZENS)
Category (single select: economic, social, criminal, infrastructure)
Title (single line text)
Description (long text)
Status (single select: filed, under_review, addressed, dismissed)
SupportCount (rollup of GRIEVANCE_SUPPORT)
FiledAt (created time)
ReviewedAt (datetime)

-- GRIEVANCE_SUPPORT table
SupportID (autonumber)
GrievanceID (link to GRIEVANCES)
CitizenID (link to CITIZENS)
SupportAmount (number)
SupportedAt (created time)
```

### Step 2: Activity Creators

Create `backend/engine/activity_creators/file_grievance_activity_creator.py`:

```python
from engine.activity_creators.base_activity_creator import BaseActivityCreator
from engine.activity_creators.utils import validate_position_near_building
from pyairtable.formulas import match

class FileGrievanceActivityCreator(BaseActivityCreator):
    ACTIVITY_KEY = "file_grievance"
    REQUIRED_ITEMS = []
    DURATION_MINUTES = 30
    FILING_FEE = 50
    
    def get_duration(self, **kwargs):
        return self.DURATION_MINUTES
    
    def is_valid(self, citizen_dict, **kwargs):
        # Check if at Palazzo Ducale
        palazzo_ducale = self.airtable_client.BUILDINGS.all(
            formula=match({"Name": "Palazzo Ducale"})
        )[0]
        
        if not validate_position_near_building(
            citizen_dict["Position"], palazzo_ducale
        ):
            return False, "Must be at Palazzo Ducale to file grievance"
        
        # Check wealth for filing fee
        if citizen_dict["Wealth"] < self.FILING_FEE:
            return False, f"Need {self.FILING_FEE} ducats to file grievance"
        
        # Check rate limit (1 per week)
        recent_grievances = self.airtable_client.GRIEVANCES.all(
            formula=f"AND({{CitizenID}}='{citizen_dict['id']}', "
                   f"DATETIME_DIFF(NOW(), {{FiledAt}}, 'days') < 7)"
        )
        if recent_grievances:
            return False, "Can only file one grievance per week"
        
        return True, None
    
    def create_with_validation(self, citizen_dict, **kwargs):
        category = kwargs.get("category")
        title = kwargs.get("title")
        description = kwargs.get("description")
        
        if not all([category, title, description]):
            return None, "Must provide category, title, and description"
        
        # Deduct filing fee
        new_wealth = citizen_dict["Wealth"] - self.FILING_FEE
        self.airtable_client.CITIZENS.update(
            citizen_dict["id"], {"Wealth": new_wealth}
        )
        
        # Create activity
        activity_data = {
            "Citizen": [citizen_dict["id"]],
            "Type": self.ACTIVITY_KEY,
            "Status": "active",
            "StartingPosition": citizen_dict["Position"],
            "EndingPosition": citizen_dict["Position"],
            "Metadata": {
                "category": category,
                "title": title,
                "description": description
            }
        }
        
        return self.airtable_client.ACTIVITIES.create(activity_data), None
```

### Step 3: Activity Handler

Create `backend/engine/handlers/file_grievance_handler.py`:

```python
from engine.handlers.base_handler import BaseHandler

class FileGrievanceHandler(BaseHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def process(self, activity):
        metadata = activity["fields"].get("Metadata", {})
        citizen_id = activity["fields"]["Citizen"][0]
        
        # Create grievance record
        grievance = self.airtable_client.GRIEVANCES.create({
            "CitizenID": [citizen_id],
            "Category": metadata["category"],
            "Title": metadata["title"],
            "Description": metadata["description"],
            "Status": "filed"
        })
        
        # Add notification
        self.airtable_client.NOTIFICATIONS.create({
            "Citizen": [citizen_id],
            "Type": "governance",
            "Title": "Grievance Filed",
            "Description": f"Your grievance '{metadata['title']}' has been filed.",
            "Metadata": {"grievance_id": grievance["id"]}
        })
        
        # Add to treasury (filing fees)
        self.add_to_treasury(50, "grievance_filing_fee")
        
        return True
```

### Step 4: API Endpoints

Add to `backend/app/main.py`:

```python
@app.post("/api/governance/grievance")
async def file_grievance(
    request: Request,
    category: str = Body(...),
    title: str = Body(...),
    description: str = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """File a grievance at the Palazzo Ducale"""
    citizen = await get_citizen_from_request(request)
    if not citizen:
        raise HTTPException(403, "Not authenticated")
    
    # Validate content (basic checks)
    if len(title) > 100:
        raise HTTPException(400, "Title too long")
    if len(description) > 1000:
        raise HTTPException(400, "Description too long")
    if category not in ["economic", "social", "criminal", "infrastructure"]:
        raise HTTPException(400, "Invalid category")
    
    # Create activity
    activity_creator = FileGrievanceActivityCreator(airtable_client)
    activity, error = activity_creator.create_with_validation(
        citizen,
        category=category,
        title=title,
        description=description
    )
    
    if error:
        raise HTTPException(400, error)
    
    return {"success": True, "activity_id": activity["id"]}

@app.get("/api/governance/grievances")
async def get_grievances(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20
):
    """Get list of grievances with optional filters"""
    formula_parts = []
    if status:
        formula_parts.append(f"{{Status}}='{status}'")
    if category:
        formula_parts.append(f"{{Category}}='{category}'")
    
    formula = f"AND({','.join(formula_parts)})" if formula_parts else None
    
    grievances = airtable_client.GRIEVANCES.all(
        formula=formula,
        sort=["-SupportCount", "-FiledAt"],
        max_records=limit
    )
    
    return {"grievances": grievances}
```

### Step 5: Frontend Components

Create `components/Governance/GrievanceBoard.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Grievance {
  id: string;
  fields: {
    Title: string;
    Description: string;
    Category: string;
    Status: string;
    SupportCount: number;
    CitizenID: string[];
    FiledAt: string;
  };
}

export function GrievanceBoard() {
  const [grievances, setGrievances] = useState<Grievance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGrievances();
  }, []);

  const fetchGrievances = async () => {
    try {
      const response = await fetch('/api/governance/grievances');
      const data = await response.json();
      setGrievances(data.grievances);
    } catch (error) {
      console.error('Failed to fetch grievances:', error);
    } finally {
      setLoading(false);
    }
  };

  const supportGrievance = async (grievanceId: string) => {
    try {
      await fetch('/api/activities/try-create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'support_grievance',
          grievance_id: grievanceId
        })
      });
      fetchGrievances(); // Refresh
    } catch (error) {
      console.error('Failed to support grievance:', error);
    }
  };

  const getCategoryColor = (category: string) => {
    const colors = {
      economic: 'bg-yellow-500',
      social: 'bg-blue-500',
      criminal: 'bg-red-500',
      infrastructure: 'bg-green-500'
    };
    return colors[category] || 'bg-gray-500';
  };

  if (loading) return <div>Loading grievances...</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Grievance Board</h2>
      
      {grievances.map((grievance) => (
        <Card key={grievance.id}>
          <CardHeader>
            <div className="flex justify-between items-start">
              <CardTitle className="text-lg">{grievance.fields.Title}</CardTitle>
              <Badge className={getCategoryColor(grievance.fields.Category)}>
                {grievance.fields.Category}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600 mb-4">
              {grievance.fields.Description}
            </p>
            <div className="flex justify-between items-center">
              <span className="text-sm">
                {grievance.fields.SupportCount || 0} supporters
              </span>
              <Button
                size="sm"
                onClick={() => supportGrievance(grievance.id)}
              >
                Support (10 ducats)
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

### Step 6: Daily Processing

Add to `backend/app/scheduler.py`:

```python
def process_grievances_to_proposals():
    """Convert popular grievances to proposals"""
    # Get grievances with 20+ supporters
    popular_grievances = airtable_client.GRIEVANCES.all(
        formula="AND({Status}='filed', {SupportCount}>=20)"
    )
    
    for grievance in popular_grievances:
        # Create proposal
        proposal = airtable_client.PROPOSALS.create({
            "OriginalGrievanceID": [grievance["id"]],
            "Title": grievance["fields"]["Title"],
            "FinalText": grievance["fields"]["Description"],
            "Category": grievance["fields"]["Category"],
            "ProposerID": grievance["fields"]["CitizenID"],
            "Status": "draft"
        })
        
        # Update grievance status
        airtable_client.GRIEVANCES.update(
            grievance["id"],
            {"Status": "promoted_to_proposal"}
        )
        
        # Notify proposer
        airtable_client.NOTIFICATIONS.create({
            "Citizen": grievance["fields"]["CitizenID"],
            "Type": "governance",
            "Title": "Grievance Promoted!",
            "Description": f"Your grievance is now a formal proposal"
        })

# Schedule daily at 9 AM Venice time
schedule.every().day.at("09:00").do(process_grievances_to_proposals)
```

## Phase 2-4 Implementation Summary

### Phase 2: Forums
1. Create forum scheduling system
2. Add speaking queue management
3. Implement AI moderation using existing LLM
4. Create forum summary generation
5. Add influence rewards for participation

### Phase 3: Voting
1. Create secure voting tables
2. Implement voting power calculations
3. Add location verification
4. Create vote tabulation system
5. Add campaign stratagems

### Phase 4: Constitutional
1. Create council election system
2. Implement representative allocation
3. Add constitutional amendment process
4. Create separation of powers checks
5. Implement emergency rollback system

## Testing Strategy

### Unit Tests
```python
# backend/tests/test_governance.py
def test_grievance_rate_limit():
    """Ensure citizens can only file 1 grievance per week"""
    
def test_voting_power_calculation():
    """Verify voting power matches design spec"""
    
def test_proposal_thresholds():
    """Test different voting thresholds work correctly"""
```

### Integration Tests
- Test full grievance → proposal → vote flow
- Verify economic deductions work correctly
- Ensure notifications are sent properly
- Test concurrent voting scenarios

### Security Tests
- Attempt vote manipulation
- Test rate limiting
- Verify economic requirements
- Check power cap enforcement

## Monitoring & Metrics

Add to monitoring dashboard:
```python
governance_metrics = {
    "total_grievances": count(GRIEVANCES),
    "active_proposals": count(PROPOSALS, status="voting"),
    "participation_rate": unique_voters / total_citizens,
    "average_support": mean(GRIEVANCES.SupportCount),
    "voting_turnout": votes_cast / eligible_voters,
    "wealth_correlation": correlation(voting_power, wealth)
}
```

## Rollout Checklist

### Phase 1 Launch
- [ ] Database tables created
- [ ] Activity creators implemented
- [ ] Handlers tested
- [ ] API endpoints live
- [ ] Frontend components deployed
- [ ] Daily processes scheduled
- [ ] Metrics dashboard ready
- [ ] Player documentation written

### Go/No-Go Criteria
- Grievance system handles 100+ simultaneous filings
- Support mechanism prevents gaming
- Rate limits working correctly
- UI intuitive for players
- No major bugs in 48-hour test

## Emergency Procedures

If governance system causes issues:

1. **Immediate**: Disable activity creation
2. **Short-term**: Roll back database changes
3. **Investigation**: Analyze patterns
4. **Fix**: Patch and re-enable gradually
5. **Long-term**: Add more safeguards

Remember: Start small, monitor closely, expand gradually. Democracy is learned, not imposed.

*"From code to constitution, one commit at a time."*
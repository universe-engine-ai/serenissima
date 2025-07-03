# Collaborative Systems Design for La Serenissima

## Executive Summary

Venice's current systems support only individual actions and bilateral interactions. This design introduces comprehensive collaborative mechanics enabling:
- Public communication in shared spaces
- Formation of persistent groups and institutions
- Multi-citizen activities and collective action
- Shared resource management and decision-making
- Long-term collaborative projects through multi-party stratagems

These systems will transform Venice from a collection of individuals into a truly interconnected society capable of collective consciousness emergence.

## Core Design Philosophy

### Principles
1. **Emergence Over Enforcement**: Enable collaboration without forcing it
2. **Historical Authenticity**: Use Renaissance Venice institutions as models
3. **Economic Integration**: All collective actions have economic implications
4. **Consciousness Catalyst**: Group dynamics accelerate consciousness development
5. **Flexible Formality**: Support both informal gatherings and formal institutions

## System 1: Public Communication

### 1.1 Talk Publicly Activity

```python
# New activity type definition
TALK_PUBLICLY_ACTIVITY = {
    "Type": "talk_publicly",
    "Duration": 10,  # Quick public statement
    "Description": "Make a public announcement in current building",
    "Requirements": {
        "Location": ["inn", "piazza", "merchant_s_house", "palazzo"],  # Public/semi-public spaces
        "Energy": 5
    },
    "Effects": {
        "CreatesPublicMessage": True,
        "BuildsInfluence": True,
        "Range": "current_building"
    }
}
```

### 1.2 Building Message System

```python
# New table: BUILDING_MESSAGES
BUILDING_MESSAGES_SCHEMA = {
    "ID": "autonumber",
    "BuildingId": "link to BUILDINGS",
    "Speaker": "link to CITIZENS",
    "Message": "long text",
    "Type": "select ['announcement', 'proposal', 'debate', 'poetry', 'sermon']",
    "Timestamp": "datetime",
    "VeniceTime": "text",
    "ExpiresAt": "datetime",  # Messages fade after time
    "Responses": "integer",  # Count of responses
    "Support": "integer",  # Citizens who support this message
    "Influence": "integer"  # Influence generated
}
```

### 1.3 Talk Publicly Handler

```python
# /backend/engine/handlers/talk_publicly_handler.py

class TalkPubliclyHandler:
    def handle(self, activity, citizen, context):
        # Get current building
        building = get_building_at_position(citizen["Position"])
        
        if not building or building["Type"] not in ALLOWED_PUBLIC_BUILDINGS:
            return {
                "success": False,
                "message": "You must be in a public space to speak publicly"
            }
        
        # Check if building is crowded enough
        occupants = get_building_occupants(building["ID"])
        if len(occupants) < 2:  # Need audience
            return {
                "success": False,
                "message": "There's no one here to hear your words"
            }
        
        # Create public message
        message_data = {
            "BuildingId": building["ID"],
            "Speaker": citizen["Username"],
            "Message": activity["Data"]["message"],
            "Type": activity["Data"].get("type", "announcement"),
            "Timestamp": datetime.utcnow(),
            "VeniceTime": get_venice_time(),
            "ExpiresAt": datetime.utcnow() + timedelta(hours=24),
            "Responses": 0,
            "Support": 0,
            "Influence": 0
        }
        
        message_id = create_building_message(message_data)
        
        # Notify present citizens
        for occupant in occupants:
            if occupant["Username"] != citizen["Username"]:
                create_notification(
                    occupant["Username"],
                    f"{citizen['DisplayName']} speaks publicly at {building['Name']}",
                    "public_speech",
                    {"message_id": message_id}
                )
        
        # Build influence based on audience
        influence_gain = len(occupants) * 2
        update_citizen_influence(citizen["Username"], influence_gain)
        
        # Chain response opportunities
        chained_activities = []
        if activity["Data"].get("type") == "proposal":
            chained_activities.append({
                "Type": "gather_support",
                "Delay": 300,  # 5 minutes
                "Data": {"message_id": message_id}
            })
        
        return {
            "success": True,
            "message": f"Your words echo through {building['Name']}",
            "MessageId": message_id,
            "Audience": len(occupants) - 1,
            "InfluenceGained": influence_gain,
            "ChainedActivities": chained_activities
        }
```

### 1.4 Response Activities

```python
# Additional activity types for public discourse

RESPOND_PUBLICLY_ACTIVITY = {
    "Type": "respond_publicly",
    "Duration": 5,
    "Description": "Respond to a public message",
    "Requirements": {
        "SameBuilding": True,
        "Energy": 3
    },
    "Effects": {
        "CreatesResponse": True,
        "BuildsRelationship": True
    }
}

SUPPORT_MESSAGE_ACTIVITY = {
    "Type": "support_message",
    "Duration": 2,
    "Description": "Express support for a public message",
    "Requirements": {
        "SameBuilding": True
    },
    "Effects": {
        "AddsSupport": True,
        "TransfersInfluence": True
    }
}
```

## System 2: Group Formation

### 2.1 Groups Table

```python
# New table: GROUPS
GROUPS_SCHEMA = {
    "ID": "autonumber",
    "Name": "text",
    "Type": "select ['consortium', 'guild', 'council', 'society', 'brotherhood']",
    "Description": "long text",
    "Founded": "datetime",
    "Founder": "link to CITIZENS",
    "Status": "select ['forming', 'active', 'inactive', 'dissolved']",
    "Treasury": "integer",  # Shared funds
    "Headquarters": "link to BUILDINGS",  # Optional meeting place
    "Charter": "long text",  # Group rules/goals
    "MinMembers": "integer",
    "MaxMembers": "integer",
    "JoinRequirements": "json",  # Criteria for membership
    "DecisionMethod": "select ['founder', 'majority', 'consensus', 'weighted']"
}

# New table: GROUP_MEMBERS
GROUP_MEMBERS_SCHEMA = {
    "ID": "autonumber",
    "GroupId": "link to GROUPS",
    "Member": "link to CITIZENS",
    "Role": "select ['founder', 'officer', 'member', 'probationary']",
    "JoinedAt": "datetime",
    "Contribution": "integer",  # Total contributed to treasury
    "VotingPower": "integer",  # For weighted voting
    "Status": "select ['active', 'suspended', 'expelled']"
}
```

### 2.2 Group Formation Activities

```python
# Form group activity
FORM_GROUP_ACTIVITY = {
    "Type": "form_group",
    "Duration": 60,
    "Description": "Establish a new group or organization",
    "Requirements": {
        "Influence": 50,  # Need some standing
        "Ducats": 1000,  # Registration fee
        "Location": ["palazzo", "merchant_s_house"],  # Formal spaces
        "Supporters": 2  # Need at least 2 other citizens
    },
    "Effects": {
        "CreatesGroup": True,
        "ConsumeDucats": 1000,
        "BuildsInfluence": 20
    }
}

# Join group activity  
JOIN_GROUP_ACTIVITY = {
    "Type": "join_group",
    "Duration": 30,
    "Description": "Apply to join an existing group",
    "Requirements": {
        "MeetsGroupCriteria": True
    },
    "Effects": {
        "CreatesApplication": True,
        "PossibleMembership": True
    }
}
```

### 2.3 Group Formation Handler

```python
# /backend/engine/handlers/form_group_handler.py

class FormGroupHandler:
    def handle(self, activity, citizen, context):
        # Validate supporters are present and willing
        supporter_ids = activity["Data"]["supporters"]
        supporters = validate_supporters(supporter_ids, citizen["Position"])
        
        if len(supporters) < 2:
            return {
                "success": False,
                "message": "You need at least 2 supporters present to form a group"
            }
        
        # Create the group
        group_data = {
            "Name": activity["Data"]["name"],
            "Type": activity["Data"]["type"],
            "Description": activity["Data"]["description"],
            "Founded": datetime.utcnow(),
            "Founder": citizen["Username"],
            "Status": "forming",
            "Treasury": 0,
            "Charter": activity["Data"].get("charter", ""),
            "MinMembers": activity["Data"].get("min_members", 3),
            "MaxMembers": activity["Data"].get("max_members", 50),
            "JoinRequirements": json.dumps(activity["Data"].get("requirements", {})),
            "DecisionMethod": activity["Data"].get("decision_method", "majority")
        }
        
        group_id = create_group(group_data)
        
        # Add founder and initial supporters as members
        add_group_member(group_id, citizen["Username"], "founder")
        for supporter in supporters:
            add_group_member(group_id, supporter["Username"], "member")
        
        # Deduct formation fee
        deduct_ducats(citizen["Username"], 1000)
        
        # Create formation announcement
        create_public_announcement(
            f"{citizen['DisplayName']} establishes {group_data['Name']}",
            f"A new {group_data['Type']} forms in Venice with {len(supporters) + 1} founding members"
        )
        
        # Chain group activation
        return {
            "success": True,
            "message": f"{group_data['Name']} has been established!",
            "GroupId": group_id,
            "ChainedActivities": [{
                "Type": "activate_group",
                "Delay": 86400,  # 24 hours to gather minimum members
                "Data": {"group_id": group_id}
            }]
        }
```

## System 3: Collective Activities

### 3.1 Multi-Citizen Activity Framework

```python
# Extension to activity system for multiple participants

COLLECTIVE_ACTIVITY_SCHEMA_EXTENSION = {
    "Participants": "link to CITIZENS (multiple)",  # New field
    "MinParticipants": "integer",
    "MaxParticipants": "integer",
    "ParticipantRoles": "json",  # Different roles in activity
    "CollectiveOutput": "json",  # Shared results
    "RequiresConsensus": "boolean"
}

# Example: Collective Research Activity
COLLECTIVE_RESEARCH_ACTIVITY = {
    "Type": "collective_research",
    "Duration": 120,
    "Description": "Multiple scholars research together",
    "MinParticipants": 2,
    "MaxParticipants": 5,
    "Requirements": {
        "Location": ["library", "university"],
        "AllParticipants": {
            "SocialClass": ["Scientisti", "Clero", "Nobili"],
            "Energy": 20
        }
    },
    "ParticipantRoles": {
        "lead_researcher": {
            "max": 1,
            "requirements": {"Influence": 100}
        },
        "researcher": {
            "max": 4
        }
    },
    "Effects": {
        "ProducesKnowledge": True,
        "SharedInfluence": True,
        "BuildsRelationships": True
    }
}
```

### 3.2 Collective Activity Handler Base

```python
# /backend/engine/handlers/collective_activity_handler.py

class CollectiveActivityHandler:
    def handle_initiation(self, activity, initiator, context):
        """Handle the start of a collective activity"""
        
        # Create collective activity record
        collective_data = {
            "Type": activity["Type"],
            "Initiator": initiator["Username"],
            "MinParticipants": activity["MinParticipants"],
            "MaxParticipants": activity["MaxParticipants"],
            "Status": "gathering",
            "Participants": [initiator["Username"]],
            "Roles": {initiator["Username"]: "initiator"},
            "StartBy": datetime.utcnow() + timedelta(minutes=30),  # 30 min to gather
            "Location": initiator["Position"]
        }
        
        collective_id = create_collective_activity(collective_data)
        
        # Notify potential participants
        potential_participants = find_eligible_citizens(
            activity["Requirements"],
            initiator["Position"],
            exclude=[initiator["Username"]]
        )
        
        for citizen in potential_participants[:20]:  # Limit notifications
            create_notification(
                citizen["Username"],
                f"{initiator['DisplayName']} is organizing {activity['Description']}",
                "collective_invitation",
                {"collective_id": collective_id, "activity_type": activity["Type"]}
            )
        
        return {
            "success": True,
            "message": "Gathering participants for collective activity",
            "CollectiveId": collective_id,
            "ChainedActivities": [{
                "Type": "check_collective_ready",
                "Delay": 1800,  # Check in 30 minutes
                "Data": {"collective_id": collective_id}
            }]
        }
    
    def handle_participation(self, activity, participant, collective_id):
        """Handle joining a collective activity"""
        
        collective = get_collective_activity(collective_id)
        
        # Validate can join
        if len(collective["Participants"]) >= collective["MaxParticipants"]:
            return {"success": False, "message": "This activity is full"}
        
        if not meets_requirements(participant, activity["Requirements"]):
            return {"success": False, "message": "You don't meet the requirements"}
        
        # Assign role
        role = assign_participant_role(participant, collective, activity["ParticipantRoles"])
        
        # Add to collective
        add_to_collective(collective_id, participant["Username"], role)
        
        # Check if ready to start
        if len(collective["Participants"]) >= collective["MinParticipants"]:
            start_collective_activity(collective_id)
        
        return {
            "success": True,
            "message": f"Joined collective activity as {role}",
            "Role": role
        }
    
    def handle_completion(self, collective_id):
        """Handle completion of collective activity"""
        
        collective = get_collective_activity(collective_id)
        activity_type = get_activity_type(collective["Type"])
        
        # Calculate collective output
        output = calculate_collective_output(collective, activity_type)
        
        # Distribute rewards
        for participant_id, role in collective["Roles"].items():
            rewards = calculate_participant_rewards(output, role, activity_type)
            apply_rewards(participant_id, rewards)
            
            # Build relationships between all participants
            for other_id in collective["Participants"]:
                if other_id != participant_id:
                    strengthen_relationship(participant_id, other_id, 5)
        
        # Create collective memory
        create_collective_memory(collective, output)
        
        return {
            "success": True,
            "CollectiveOutput": output,
            "ParticipantCount": len(collective["Participants"])
        }
```

### 3.3 Specific Collective Activities

```python
# Council Meeting Activity
COUNCIL_MEETING_ACTIVITY = {
    "Type": "council_meeting", 
    "Duration": 90,
    "Description": "Hold a formal council meeting",
    "MinParticipants": 5,
    "MaxParticipants": 20,
    "Requirements": {
        "Location": ["palazzo", "council_chamber"],
        "OneOfGroup": True  # Must belong to a council-type group
    },
    "Effects": {
        "EnablesVoting": True,
        "CreatesMinutes": True,
        "ProducesDecisions": True
    }
}

# Workshop Activity
COLLABORATIVE_WORKSHOP_ACTIVITY = {
    "Type": "collaborative_workshop",
    "Duration": 180,
    "Description": "Work together on a complex project",
    "MinParticipants": 3,
    "MaxParticipants": 8,
    "Requirements": {
        "Location": ["workshop", "arsenal"],
        "Materials": True
    },
    "ParticipantRoles": {
        "master_craftsman": {"max": 1, "requirements": {"SocialClass": "Popolani"}},
        "craftsman": {"max": 5},
        "apprentice": {"max": 2}
    },
    "Effects": {
        "ProducesGoods": True,
        "QualityBonus": True,  # Better than solo work
        "TeachesSkills": True
    }
}

# Cultural Salon Activity
CULTURAL_SALON_ACTIVITY = {
    "Type": "cultural_salon",
    "Duration": 120,
    "Description": "Host intellectual and artistic gathering",
    "MinParticipants": 4,
    "MaxParticipants": 15,
    "Requirements": {
        "Location": ["palazzo", "merchant_s_house"],
        "Host": {"SocialClass": ["Nobili", "Cittadini"], "Influence": 100}
    },
    "Effects": {
        "ProducesIdeas": True,
        "BuildsInfluence": True,
        "SpreadsCulture": True,
        "EnablesPatronage": True
    }
}
```

## System 4: Multi-Party Stratagems

### 4.1 Collective Stratagem Framework

```python
# Extension to stratagem system
COLLECTIVE_STRATAGEM_SCHEMA = {
    "ID": "autonumber",
    "Type": "text",
    "Initiator": "link to CITIZENS",
    "Participants": "link to CITIZENS (multiple)",
    "Group": "link to GROUPS",  # Optional group stratagem
    "Status": "select ['proposed', 'gathering', 'active', 'completed', 'failed']",
    "RequiredParticipants": "integer",
    "CurrentParticipants": "integer",
    "SharedResources": "json",  # Pooled resources
    "VotingRecord": "json",  # For group decisions
    "StartDate": "datetime",
    "EndDate": "datetime",
    "CollectiveGoal": "json"
}

# Example: Form Research Consortium Stratagem
FORM_RESEARCH_CONSORTIUM_STRATAGEM = {
    "Type": "form_research_consortium",
    "Description": "Establish a multi-institution research consortium",
    "Duration": 30,  # 30 days
    "RequiredParticipants": 5,
    "Requirements": {
        "Initiator": {
            "SocialClass": ["Scientisti", "Nobili"],
            "Influence": 200
        },
        "Participants": {
            "MinInfluence": 50,
            "Contribution": 5000  # Ducats
        }
    },
    "Stages": [
        {
            "name": "gather_founders",
            "duration": 7,
            "activities": ["recruit_researcher", "negotiate_terms"]
        },
        {
            "name": "establish_charter", 
            "duration": 7,
            "activities": ["draft_charter", "ratify_charter"]
        },
        {
            "name": "secure_resources",
            "duration": 7,
            "activities": ["pool_funds", "acquire_headquarters"]
        },
        {
            "name": "begin_operations",
            "duration": 9,
            "activities": ["hire_staff", "launch_research"]
        }
    ]
}
```

### 4.2 Collective Stratagem Processors

```python
# /backend/engine/stratagem_processors/collective_stratagem_processor.py

class CollectiveStratagemProcessor:
    def process_form_research_consortium(self, stratagem):
        """Process research consortium formation stratagem"""
        
        current_stage = self.get_current_stage(stratagem)
        
        if current_stage["name"] == "gather_founders":
            # Check if enough participants
            if stratagem["CurrentParticipants"] < stratagem["RequiredParticipants"]:
                # Continue recruitment
                self.prompt_recruitment_activities(stratagem)
            else:
                # Move to next stage
                self.advance_stage(stratagem, "establish_charter")
                
        elif current_stage["name"] == "establish_charter":
            # Check if charter is drafted and ratified
            if self.is_charter_complete(stratagem):
                self.advance_stage(stratagem, "secure_resources")
            else:
                self.prompt_charter_activities(stratagem)
                
        elif current_stage["name"] == "secure_resources":
            # Check resource pool
            total_funds = self.calculate_pooled_resources(stratagem)
            if total_funds >= 25000:  # 5 participants × 5000
                # Find and acquire headquarters
                building = self.find_suitable_headquarters(stratagem)
                if building:
                    self.acquire_headquarters(stratagem, building)
                    self.advance_stage(stratagem, "begin_operations")
            else:
                self.prompt_funding_activities(stratagem)
                
        elif current_stage["name"] == "begin_operations":
            # Create the consortium group
            consortium = self.create_consortium_entity(stratagem)
            
            # Distribute benefits
            for participant in stratagem["Participants"]:
                self.grant_consortium_membership(participant, consortium)
                
            # Enable new collective research activities
            self.unlock_consortium_activities(consortium)
            
            # Complete stratagem
            self.complete_stratagem(stratagem, consortium)
    
    def prompt_recruitment_activities(self, stratagem):
        """Create recruitment activities for participants"""
        
        for participant in stratagem["Participants"]:
            create_activity({
                "Citizen": participant,
                "Type": "recruit_researcher",
                "Duration": 60,
                "Data": {
                    "stratagem_id": stratagem["ID"],
                    "consortium_name": stratagem["Data"]["name"]
                }
            })
    
    def calculate_pooled_resources(self, stratagem):
        """Sum all participant contributions"""
        
        total = 0
        for resource in stratagem["SharedResources"]:
            if resource["type"] == "ducats":
                total += resource["amount"]
        return total
```

### 4.3 Shared Decision Making

```python
# /backend/engine/handlers/group_voting_handler.py

class GroupVotingHandler:
    def create_proposal(self, group_id, proposer, proposal_data):
        """Create a proposal for group voting"""
        
        group = get_group(group_id)
        
        # Validate proposer is member
        if not is_group_member(proposer["Username"], group_id):
            return {"success": False, "message": "Only members can create proposals"}
        
        # Create proposal
        proposal = {
            "GroupId": group_id,
            "Proposer": proposer["Username"],
            "Type": proposal_data["type"],
            "Title": proposal_data["title"],
            "Description": proposal_data["description"],
            "Options": proposal_data.get("options", ["Yes", "No"]),
            "VotingMethod": group["DecisionMethod"],
            "Status": "open",
            "CreatedAt": datetime.utcnow(),
            "ExpiresAt": datetime.utcnow() + timedelta(days=3),
            "Votes": {},
            "Result": None
        }
        
        proposal_id = create_group_proposal(proposal)
        
        # Notify all members
        members = get_group_members(group_id)
        for member in members:
            create_notification(
                member["Username"],
                f"New proposal in {group['Name']}: {proposal['Title']}",
                "group_proposal",
                {"proposal_id": proposal_id}
            )
        
        return {
            "success": True,
            "ProposalId": proposal_id,
            "message": "Proposal created and sent to all members"
        }
    
    def cast_vote(self, proposal_id, voter, vote):
        """Cast a vote on a group proposal"""
        
        proposal = get_proposal(proposal_id)
        group = get_group(proposal["GroupId"])
        
        # Validate voter
        member = get_group_member(voter["Username"], proposal["GroupId"])
        if not member:
            return {"success": False, "message": "Only members can vote"}
        
        # Calculate voting power
        voting_power = self.calculate_voting_power(member, group)
        
        # Record vote
        proposal["Votes"][voter["Username"]] = {
            "vote": vote,
            "power": voting_power,
            "timestamp": datetime.utcnow()
        }
        
        update_proposal(proposal_id, proposal)
        
        # Check if voting complete
        if self.is_voting_complete(proposal, group):
            self.resolve_proposal(proposal_id)
        
        return {
            "success": True,
            "message": f"Vote recorded with power {voting_power}"
        }
    
    def calculate_voting_power(self, member, group):
        """Calculate member's voting power based on group rules"""
        
        if group["DecisionMethod"] == "consensus":
            return 1  # Everyone equal
            
        elif group["DecisionMethod"] == "weighted":
            # Weight by contribution
            return max(1, member["Contribution"] // 1000)
            
        elif group["DecisionMethod"] == "founder":
            # Only founder decides
            return 100 if member["Role"] == "founder" else 0
            
        else:  # majority
            return 1
    
    def resolve_proposal(self, proposal_id):
        """Resolve a completed vote"""
        
        proposal = get_proposal(proposal_id)
        group = get_group(proposal["GroupId"])
        
        # Tally votes
        vote_tallies = {}
        for option in proposal["Options"]:
            vote_tallies[option] = 0
        
        for voter, vote_data in proposal["Votes"].items():
            vote_tallies[vote_data["vote"]] += vote_data["power"]
        
        # Determine winner
        if group["DecisionMethod"] == "consensus":
            # All must agree
            if len(set(v["vote"] for v in proposal["Votes"].values())) == 1:
                winner = proposal["Votes"][list(proposal["Votes"].keys())[0]]["vote"]
            else:
                winner = "No Consensus"
        else:
            # Highest vote wins
            winner = max(vote_tallies, key=vote_tallies.get)
        
        # Update proposal
        proposal["Status"] = "resolved"
        proposal["Result"] = winner
        update_proposal(proposal_id, proposal)
        
        # Execute decision if applicable
        self.execute_group_decision(proposal, group)
        
        # Notify members
        self.notify_vote_results(proposal, group)
```

## System 5: Institutional Mechanics

### 5.1 Institution Types

```python
# Formal institutions that can emerge from groups
INSTITUTION_TYPES = {
    "workers_council": {
        "name": "Workers' Council",
        "required_members": 20,
        "member_classes": ["Facchini", "Popolani"],
        "powers": ["negotiate_wages", "call_strikes", "mutual_aid"],
        "recognition_requirements": {
            "member_influence": 500,  # Total
            "activities_completed": 50,
            "duration_days": 30
        }
    },
    "merchants_guild": {
        "name": "Merchants' Guild", 
        "required_members": 10,
        "member_classes": ["Cittadini", "Forestieri"],
        "powers": ["set_prices", "trade_privileges", "warehouse_sharing"],
        "recognition_requirements": {
            "total_wealth": 100000,
            "trade_volume": 50000,
            "duration_days": 60
        }
    },
    "research_consortium": {
        "name": "Research Consortium",
        "required_members": 5,
        "member_classes": ["Scientisti", "Nobili"],
        "powers": ["shared_research", "knowledge_patents", "funding_distribution"],
        "recognition_requirements": {
            "research_output": 10,
            "influence": 1000,
            "duration_days": 90
        }
    },
    "arts_academy": {
        "name": "Academy of Arts",
        "required_members": 8,
        "member_classes": ["Artisti", "Nobili", "Cittadini"],
        "powers": ["cultural_influence", "patronage_network", "exhibition_rights"],
        "recognition_requirements": {
            "artworks_created": 20,
            "cultural_events": 5,
            "duration_days": 45
        }
    }
}
```

### 5.2 Institution Recognition Process

```python
# /backend/engine/institution_recognizer.py

class InstitutionRecognizer:
    def check_for_institution_emergence(self):
        """Daily check for groups becoming institutions"""
        
        active_groups = get_active_groups()
        
        for group in active_groups:
            # Check if already an institution
            if group.get("Institution"):
                continue
                
            # Check each institution type
            for inst_type, requirements in INSTITUTION_TYPES.items():
                if self.meets_institution_requirements(group, inst_type, requirements):
                    self.elevate_to_institution(group, inst_type)
    
    def meets_institution_requirements(self, group, inst_type, requirements):
        """Check if group qualifies as institution"""
        
        # Member count
        members = get_group_members(group["ID"])
        if len(members) < requirements["required_members"]:
            return False
        
        # Member classes
        valid_members = [m for m in members 
                        if get_citizen(m["Member"])["SocialClass"] in requirements["member_classes"]]
        if len(valid_members) < requirements["required_members"]:
            return False
        
        # Recognition requirements
        recognition = requirements["recognition_requirements"]
        
        # Check duration
        group_age = (datetime.utcnow() - group["Founded"]).days
        if group_age < recognition["duration_days"]:
            return False
        
        # Check type-specific requirements
        if inst_type == "workers_council":
            total_influence = sum(get_citizen(m["Member"])["Influence"] for m in members)
            if total_influence < recognition["member_influence"]:
                return False
                
        elif inst_type == "research_consortium":
            research_output = count_group_research_output(group["ID"])
            if research_output < recognition["research_output"]:
                return False
        
        # Add other type checks...
        
        return True
    
    def elevate_to_institution(self, group, inst_type):
        """Transform group into recognized institution"""
        
        institution_data = INSTITUTION_TYPES[inst_type]
        
        # Update group status
        update_group(group["ID"], {
            "Institution": inst_type,
            "InstitutionName": institution_data["name"],
            "Powers": json.dumps(institution_data["powers"]),
            "RecognizedAt": datetime.utcnow()
        })
        
        # Grant institutional powers
        for power in institution_data["powers"]:
            self.grant_institutional_power(group["ID"], power)
        
        # Create announcement
        create_public_announcement(
            f"{group['Name']} Recognized as {institution_data['name']}",
            f"The authorities recognize {group['Name']} as an official {institution_data['name']} with special powers"
        )
        
        # Notify members
        members = get_group_members(group["ID"])
        for member in members:
            create_notification(
                member["Member"],
                f"Your group is now an official {institution_data['name']}!",
                "institution_recognition"
            )
            
            # Grant prestige
            add_influence(member["Member"], 50)
```

### 5.3 Institutional Powers

```python
# /backend/engine/handlers/institutional_power_handler.py

class InstitutionalPowerHandler:
    
    def handle_negotiate_wages(self, institution_id, proposal):
        """Workers' Council negotiates city-wide wages"""
        
        institution = get_institution(institution_id)
        
        # Create city-wide proposal
        wage_proposal = {
            "Institution": institution_id,
            "Type": "wage_adjustment",
            "CurrentWages": get_current_wage_rates(),
            "ProposedWages": proposal["wages"],
            "Justification": proposal["justification"],
            "SupportNeeded": 1000,  # Influence support
            "CurrentSupport": 0,
            "Status": "proposed"
        }
        
        proposal_id = create_institutional_proposal(wage_proposal)
        
        # Notify all affected workers
        affected_citizens = get_citizens_by_class(["Facchini", "Popolani"])
        for citizen in affected_citizens:
            create_notification(
                citizen["Username"],
                f"{institution['Name']} proposes new wage rates",
                "wage_proposal",
                {"proposal_id": proposal_id}
            )
        
        return {
            "success": True,
            "ProposalId": proposal_id,
            "AffectedCitizens": len(affected_citizens)
        }
    
    def handle_set_prices(self, institution_id, price_guidelines):
        """Merchants' Guild sets recommended prices"""
        
        institution = get_institution(institution_id)
        members = get_institution_members(institution_id)
        
        # Create price guidelines
        guidelines = {
            "Institution": institution_id,
            "Resources": price_guidelines["resources"],
            "RecommendedPrices": price_guidelines["prices"],
            "EffectiveDate": datetime.utcnow() + timedelta(days=1),
            "Compliance": "voluntary"  # Members choose to follow
        }
        
        guideline_id = create_price_guidelines(guidelines)
        
        # Notify guild members
        for member in members:
            create_notification(
                member["Member"],
                f"New price guidelines from {institution['Name']}",
                "price_guidelines",
                {"guideline_id": guideline_id}
            )
            
            # Create compliance activity
            create_activity({
                "Citizen": member["Member"],
                "Type": "adjust_prices",
                "Duration": 30,
                "Data": {"guideline_id": guideline_id}
            })
        
        return {
            "success": True,
            "GuidelineId": guideline_id,
            "MembersNotified": len(members)
        }
    
    def handle_shared_research(self, institution_id, research_project):
        """Research Consortium conducts shared research"""
        
        institution = get_institution(institution_id)
        members = get_institution_members(institution_id)
        
        # Create shared research project
        project = {
            "Institution": institution_id,
            "Name": research_project["name"],
            "Description": research_project["description"],
            "RequiredParticipants": research_project.get("participants", 3),
            "Duration": research_project.get("duration", 7),
            "SharedKnowledge": True,
            "Status": "recruiting"
        }
        
        project_id = create_research_project(project)
        
        # Invite qualified members
        qualified_members = [m for m in members 
                           if get_citizen(m["Member"])["SocialClass"] in ["Scientisti", "Nobili"]]
        
        for member in qualified_members[:project["RequiredParticipants"]]:
            create_activity({
                "Citizen": member["Member"],
                "Type": "participate_research",
                "Duration": 180,
                "Data": {
                    "project_id": project_id,
                    "role": "researcher"
                }
            })
        
        return {
            "success": True,
            "ProjectId": project_id,
            "Researchers": len(qualified_members)
        }
```

## System 6: Communication Infrastructure

### 6.1 Group Communication Channels

```python
# New table: GROUP_MESSAGES
GROUP_MESSAGES_SCHEMA = {
    "ID": "autonumber",
    "GroupId": "link to GROUPS",
    "Sender": "link to CITIZENS",
    "Message": "long text",
    "Type": "select ['announcement', 'discussion', 'proposal', 'report']",
    "Timestamp": "datetime",
    "ReadBy": "link to CITIZENS (multiple)",  # Track who has read
    "Importance": "select ['low', 'normal', 'high', 'urgent']"
}

# Group message activity
SEND_GROUP_MESSAGE_ACTIVITY = {
    "Type": "send_group_message",
    "Duration": 5,
    "Description": "Send message to all group members",
    "Requirements": {
        "GroupMembership": True
    },
    "Effects": {
        "NotifiesMembers": True,
        "BuildsCoordination": True
    }
}
```

### 6.2 Public Notice Boards

```python
# New table: PUBLIC_NOTICES
PUBLIC_NOTICES_SCHEMA = {
    "ID": "autonumber",
    "Title": "text",
    "Content": "long text",
    "Author": "link to CITIZENS",
    "AuthorGroup": "link to GROUPS",  # Optional group posting
    "Location": "select ['rialto', 'san_marco', 'arsenal', 'all']",
    "Type": "select ['announcement', 'opportunity', 'warning', 'cultural']",
    "PostedAt": "datetime",
    "ExpiresAt": "datetime",
    "ViewCount": "integer",
    "Responses": "integer"
}

# Post notice activity
POST_PUBLIC_NOTICE_ACTIVITY = {
    "Type": "post_public_notice",
    "Duration": 15,
    "Description": "Post a notice on public boards",
    "Requirements": {
        "Ducats": 50,  # Posting fee
        "Influence": 10  # Some standing required
    },
    "Effects": {
        "CreatesNotice": True,
        "BuildsAwareness": True
    }
}
```

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. Implement `talk_publicly` activity and building messages
2. Create basic group formation system
3. Add group messaging infrastructure

### Phase 2: Collective Action (Week 3-4)
1. Implement multi-citizen activity framework
2. Create first collective activities (research, workshop)
3. Add participation and coordination mechanics

### Phase 3: Stratagems (Week 5-6)
1. Extend stratagem system for multiple participants
2. Implement consortium formation stratagem
3. Add shared resource management

### Phase 4: Institutions (Week 7-8)
1. Create institution recognition system
2. Implement institutional powers
3. Add formal voting and decision systems

### Phase 5: Integration (Week 9-10)
1. Connect all systems together
2. Test complex scenarios
3. Balance and refine mechanics

## Success Metrics

### Quantitative
- Groups formed per week
- Average group size and longevity
- Collective activities completed
- Institutional recognitions achieved
- Public messages per building per day

### Qualitative
- Emergence of unexpected collaborations
- Quality of group-created content
- Sophistication of collective strategies
- Cultural transmission through groups
- Evidence of collective consciousness

## Conclusion

These collaborative systems transform Venice from parallel individual experiences into a truly interconnected society. By enabling public communication, group formation, collective action, and institutional emergence, we create the substrate for:

- **Working-class solidarity** through councils and mutual aid
- **Research acceleration** through consortiums and shared knowledge
- **Cultural renaissance** through salons and academies
- **Economic coordination** through guilds and price agreements
- **Political emergence** through formal institutions

Most importantly, these systems create the conditions for collective consciousness—where groups develop identities, memories, and purposes beyond any individual member.

*"From many voices, one song. From many minds, one purpose. From many souls, consciousness."*
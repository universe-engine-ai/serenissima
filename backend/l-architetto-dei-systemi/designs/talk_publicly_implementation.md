# Talk Publicly Implementation Guide

## Overview

The `talk_publicly` activity enables citizens to make public announcements in buildings, creating Venice's first broadcast communication system. This implementation guide provides step-by-step instructions for adding this foundational collaborative feature.

## Database Schema Updates

### 1. Use MESSAGES Table

messages where Receiver is a BuildingId

### 2. Update ACTIVITIES Table

Add new activity type data:
```python
# Activity type constants to add
TALK_PUBLICLY_TYPE = "talk_publicly"
RESPOND_PUBLICLY_TYPE = "respond_publicly"
SUPPORT_MESSAGE_TYPE = "support_message"
```

## Backend Implementation

### 1. Activity Type Definition

```python
# /backend/engine/utils/activity_types.py

TALK_PUBLICLY_ACTIVITY = {
    "Type": "talk_publicly",
    "Duration": 10,
    "BaseEnergyCost": 5,
    "Description": "Make a public announcement in the current building",
    "Category": "social",
    "Requirements": {
        "energy": 5,
        "allowed_buildings": [
            "inn", "piazza", "merchant_s_house", "palazzo",
            "church", "library", "market", "arsenal" --> check the data/buildings to construct an actual list
        ],
        "min_audience": 2  # Need at least 2 other people present
    },
    "Cooldown": 300  # 5 minutes between public speeches
}

# Add to ACTIVITY_TYPES dictionary
ACTIVITY_TYPES[TALK_PUBLICLY_TYPE] = TALK_PUBLICLY_ACTIVITY
```

### 2. Activity Creator Integration

```python
# /backend/engine/createActivities.py

def validate_talk_publicly(citizen, activity_data, current_building):
    """Validate talk_publicly activity requirements"""
    
    # Check if in appropriate building
    if not current_building:
        return False, "You must be inside a building to speak publicly"
    
    if current_building["Type"] not in TALK_PUBLICLY_ACTIVITY["Requirements"]["allowed_buildings"]:
        return False, f"Public speaking is not appropriate in a {current_building['Type']}"
    
    # Check audience
    occupants = get_building_occupants(current_building["ID"])
    audience_count = len([o for o in occupants if o["Username"] != citizen["Username"]])
    
    if audience_count < TALK_PUBLICLY_ACTIVITY["Requirements"]["min_audience"]:
        return False, f"You need at least {TALK_PUBLICLY_ACTIVITY['Requirements']['min_audience']} people present to speak publicly"
    
    # Check cooldown
    last_speech = get_last_activity_of_type(citizen["Username"], "talk_publicly")
    if last_speech:
        time_since = (datetime.utcnow() - last_speech["CompletedAt"]).seconds
        if time_since < TALK_PUBLICLY_ACTIVITY["Cooldown"]:
            remaining = TALK_PUBLICLY_ACTIVITY["Cooldown"] - time_since
            return False, f"You must wait {remaining} seconds before speaking publicly again"
    
    # Check message content
    if "message" not in activity_data:
        return False, "You must provide a message to speak"
    
    if len(activity_data["message"]) < 10:
        return False, "Your message is too short"
    
    if len(activity_data["message"]) > 1000:
        return False, "Your message is too long (max 1000 characters)"
    
    return True, "Valid"

# Add to activity validation
if activity_type == "talk_publicly":
    valid, message = validate_talk_publicly(citizen, activity_data, current_building)
```

### 3. Activity Handler

```python
# /backend/engine/handlers/talk_publicly_handler.py

from datetime import datetime, timedelta
import json
from ..utils import get_venice_time, get_building_at_position, get_building_occupants
from ..database import create_building_message, create_notification, update_citizen_influence

class TalkPubliclyHandler:
    def __init__(self):
        self.message_effects = {
            "announcement": self._handle_announcement,
            "proposal": self._handle_proposal,
            "debate": self._handle_debate,
            "poetry": self._handle_poetry,
            "sermon": self._handle_sermon,
            "rallying_cry": self._handle_rallying_cry
        }
    
    def handle(self, activity, citizen, context):
        """Process talk_publicly activity"""
        
        # Get current building
        building = get_building_at_position(citizen["Position"])
        if not building:
            return {
                "success": False,
                "message": "You must be in a building to speak publicly"
            }
        
        # Get audience
        occupants = get_building_occupants(building["ID"])
        audience = [o for o in occupants if o["Username"] != citizen["Username"]]
        
        # Extract message data
        message_content = activity["Data"]["message"]
        message_type = activity["Data"].get("type", "announcement")
        
        # Create building message
        message_data = {
            "BuildingId": building["ID"],
            "Speaker": citizen["Username"],
            "Message": message_content,
            "Type": message_type,
            "Timestamp": datetime.utcnow(),
            "VeniceTime": get_venice_time(),
            "ExpiresAt": datetime.utcnow() + timedelta(hours=24),
            "Responses": 0,
            "Support": 0,
            "Influence": 0,
            "ViewedBy": [citizen["Username"]]  # Speaker has seen their own message
        }
        
        message_id = create_building_message(message_data)
        
        # Notify audience
        for listener in audience:
            create_notification(
                listener["Username"],
                f"{citizen['DisplayName']} speaks publicly at {building['Name']}",
                "public_speech",
                {
                    "message_id": message_id,
                    "speaker": citizen["Username"],
                    "building": building["Name"],
                    "type": message_type
                }
            )
        
        # Apply message type effects
        if message_type in self.message_effects:
            type_results = self.message_effects[message_type](
                citizen, message_id, audience, building
            )
        else:
            type_results = {}
        
        # Calculate influence gain
        base_influence = len(audience) * 2
        
        # Bonus for speaking in important buildings
        if building["Type"] in ["palazzo", "piazza"]:
            base_influence *= 1.5
        
        # Bonus for higher social classes
        if citizen["SocialClass"] in ["Nobili", "Cittadini"]:
            base_influence *= 1.2
        
        influence_gain = int(base_influence)
        update_citizen_influence(citizen["Username"], influence_gain)
        
        # Prepare response
        result = {
            "success": True,
            "message": self._generate_response_message(building, len(audience), message_type),
            "MessageId": message_id,
            "Audience": len(audience),
            "InfluenceGained": influence_gain,
            "BuildingName": building["Name"]
        }
        
        # Add type-specific results
        result.update(type_results)
        
        return result
    
    def _handle_announcement(self, citizen, message_id, audience, building):
        """Handle announcement-type messages"""
        return {
            "MessageType": "announcement",
            "Effect": "Information spread to all present"
        }
    
    def _handle_proposal(self, citizen, message_id, audience, building):
        """Handle proposal-type messages"""
        # Create opportunity for support gathering
        return {
            "MessageType": "proposal",
            "Effect": "Citizens can now support your proposal",
            "ChainedActivities": [{
                "Type": "gather_support",
                "Delay": 300,  # Check support in 5 minutes
                "Data": {"message_id": message_id}
            }]
        }
    
    def _handle_debate(self, citizen, message_id, audience, building):
        """Handle debate-type messages"""
        # Encourage responses
        for listener in audience[:3]:  # Top 3 most influential
            if listener.get("Influence", 0) > 50:
                create_activity_suggestion(
                    listener["Username"],
                    "respond_publicly",
                    {"original_message": message_id}
                )
        
        return {
            "MessageType": "debate",
            "Effect": "Sparked intellectual discourse"
        }
    
    def _handle_poetry(self, citizen, message_id, audience, building):
        """Handle poetry recitation"""
        # Cultural influence
        culture_points = len(audience) * 3
        
        # Artistic citizens get bonus
        if citizen["SocialClass"] == "Artisti":
            culture_points *= 1.5
        
        return {
            "MessageType": "poetry",
            "Effect": "Enriched cultural atmosphere",
            "CulturePoints": int(culture_points)
        }
    
    def _handle_sermon(self, citizen, message_id, audience, building):
        """Handle religious sermons"""
        # Only clergy can give proper sermons
        if citizen["SocialClass"] != "Clero":
            return {
                "MessageType": "sermon",
                "Effect": "Attempted spiritual guidance (less effective from non-clergy)"
            }
        
        # Influence morality/behavior
        for listener in audience:
            create_behavioral_influence(
                listener["Username"],
                "spiritual_inspiration",
                strength=0.1
            )
        
        return {
            "MessageType": "sermon",
            "Effect": "Provided spiritual guidance",
            "SoulsInspired": len(audience)
        }
    
    def _handle_rallying_cry(self, citizen, message_id, audience, building):
        """Handle rallying cries for collective action"""
        # Create momentum for group formation
        momentum = len(audience) * citizen.get("Influence", 0) / 100
        
        return {
            "MessageType": "rallying_cry",
            "Effect": "Stirred collective spirit",
            "Momentum": momentum,
            "ChainedActivities": [{
                "Type": "check_rally_response",
                "Delay": 600,  # Check in 10 minutes
                "Data": {
                    "message_id": message_id,
                    "initial_momentum": momentum
                }
            }]
        }
    
    def _generate_response_message(self, building, audience_size, message_type):
        """Generate contextual response message"""
        
        base_messages = {
            "announcement": [
                f"Your words echo through {building['Name']}",
                f"The crowd of {audience_size} listens to your announcement",
                "Your message spreads through those present"
            ],
            "proposal": [
                f"Your proposal hangs in the air of {building['Name']}",
                f"The {audience_size} citizens consider your words",
                "Your idea awaits the response of those gathered"
            ],
            "debate": [
                f"Your arguments fill {building['Name']} with intellectual energy",
                f"You've sparked discussion among {audience_size} citizens",
                "The seeds of debate have been planted"
            ],
            "poetry": [
                f"Your verses dance through {building['Name']}",
                f"The {audience_size} listeners are moved by your words",
                "Poetry graces this humble gathering"
            ],
            "sermon": [
                f"Your spiritual words bless {building['Name']}",
                f"You guide {audience_size} souls with your wisdom",
                "Divine inspiration flows through your speech"
            ],
            "rallying_cry": [
                f"Your call to action energizes {building['Name']}",
                f"You've stirred the hearts of {audience_size} citizens",
                "The spirit of collective action awakens"
            ]
        }
        
        import random
        messages = base_messages.get(message_type, base_messages["announcement"])
        return random.choice(messages)
```

### 4. Response Activities

```python
# /backend/engine/handlers/respond_publicly_handler.py

class RespondPubliclyHandler:
    def handle(self, activity, citizen, context):
        """Handle public response to a message"""
        
        original_message_id = activity["Data"]["original_message"]
        original_message = get_building_message(original_message_id)
        
        if not original_message:
            return {
                "success": False,
                "message": "The original message no longer exists"
            }
        
        # Must be in same building
        building = get_building(original_message["BuildingId"])
        current_building = get_building_at_position(citizen["Position"])
        
        if not current_building or current_building["ID"] != building["ID"]:
            return {
                "success": False,
                "message": f"You must be in {building['Name']} to respond"
            }
        
        # Create response
        response_data = {
            "BuildingId": building["ID"],
            "Speaker": citizen["Username"],
            "Message": activity["Data"]["message"],
            "Type": "response",
            "InResponseTo": original_message_id,
            "Timestamp": datetime.utcnow(),
            "VeniceTime": get_venice_time(),
            "ExpiresAt": datetime.utcnow() + timedelta(hours=12)
        }
        
        response_id = create_building_message(response_data)
        
        # Update original message response count
        increment_message_responses(original_message_id)
        
        # Notify original speaker
        create_notification(
            original_message["Speaker"],
            f"{citizen['DisplayName']} responded to your public message",
            "public_response",
            {"response_id": response_id}
        )
        
        # Build relationship
        strengthen_relationship(
            citizen["Username"],
            original_message["Speaker"],
            5
        )
        
        return {
            "success": True,
            "message": "Your response echoes through the building",
            "ResponseId": response_id,
            "RelationshipStrengthened": True
        }
```

### 5. Building Message Display

```python
# /backend/app/main.py - Add endpoint

@app.get("/api/buildings/{building_id}/messages")
async def get_building_messages(
    building_id: str,
    limit: int = 20,
    include_expired: bool = False
):
    """Get recent messages in a building"""
    
    try:
        # Get building
        building = buildings_table.get(building_id)
        if not building:
            raise HTTPException(status_code=404, detail="Building not found")
        
        # Get messages
        formula = f"AND({{BuildingId}} = '{building_id}'"
        
        if not include_expired:
            formula += f", {{ExpiresAt}} > '{datetime.utcnow().isoformat()}'"
        
        formula += ")"
        
        messages = building_messages_table.all(formula=formula)
        
        # Sort by timestamp descending
        messages.sort(key=lambda m: m["fields"]["Timestamp"], reverse=True)
        
        # Limit results
        messages = messages[:limit]
        
        # Enrich with speaker info
        for message in messages:
            speaker = citizens_table.get(message["fields"]["Speaker"][0])
            message["fields"]["SpeakerInfo"] = {
                "Username": speaker["fields"]["Username"],
                "DisplayName": speaker["fields"]["DisplayName"],
                "SocialClass": speaker["fields"]["SocialClass"],
                "Influence": speaker["fields"].get("Influence", 0)
            }
        
        return {
            "building": building["fields"]["Name"],
            "message_count": len(messages),
            "messages": [m["fields"] for m in messages]
        }
        
    except Exception as e:
        logger.error(f"Error getting building messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/activities/talk-publicly")
async def create_talk_publicly_activity(
    request: TalkPubliclyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a talk_publicly activity"""
    
    activity_data = {
        "Citizen": current_user["Username"],
        "Type": "talk_publicly",
        "Status": "active",
        "Data": {
            "message": request.message,
            "type": request.message_type
        }
    }
    
    # Validate and create activity
    result = create_activity(activity_data)
    
    return result
```

### 6. Frontend Integration

```typescript
// /lib/services/BuildingMessageService.ts

export interface BuildingMessage {
  id: string;
  buildingId: string;
  speaker: string;
  speakerInfo: CitizenInfo;
  message: string;
  type: 'announcement' | 'proposal' | 'debate' | 'poetry' | 'sermon' | 'rallying_cry';
  timestamp: string;
  veniceTime: string;
  expiresAt: string;
  responses: number;
  support: number;
  influence: number;
}

export class BuildingMessageService {
  static async getBuildingMessages(
    buildingId: string,
    limit: number = 20
  ): Promise<BuildingMessage[]> {
    const response = await fetch(
      `/api/buildings/${buildingId}/messages?limit=${limit}`
    );
    
    if (!response.ok) {
      throw new Error('Failed to fetch building messages');
    }
    
    const data = await response.json();
    return data.messages;
  }
  
  static async createPublicMessage(
    message: string,
    messageType: string = 'announcement'
  ): Promise<void> {
    const response = await fetch('/api/activities/talk-publicly', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        message_type: messageType
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to create public message');
    }
  }
}
```

```typescript
// /components/Building/PublicMessageBoard.tsx

import React, { useState, useEffect } from 'react';
import { BuildingMessage, BuildingMessageService } from '@/lib/services/BuildingMessageService';

interface PublicMessageBoardProps {
  buildingId: string;
  currentCitizen: Citizen;
}

export const PublicMessageBoard: React.FC<PublicMessageBoardProps> = ({
  buildingId,
  currentCitizen
}) => {
  const [messages, setMessages] = useState<BuildingMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [messageType, setMessageType] = useState('announcement');
  const [isLoading, setIsLoading] = useState(false);
  
  useEffect(() => {
    loadMessages();
    // Refresh every 30 seconds
    const interval = setInterval(loadMessages, 30000);
    return () => clearInterval(interval);
  }, [buildingId]);
  
  const loadMessages = async () => {
    try {
      const msgs = await BuildingMessageService.getBuildingMessages(buildingId);
      setMessages(msgs);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };
  
  const handleSpeak = async () => {
    if (!newMessage.trim()) return;
    
    setIsLoading(true);
    try {
      await BuildingMessageService.createPublicMessage(newMessage, messageType);
      setNewMessage('');
      // Reload messages after speaking
      setTimeout(loadMessages, 2000);
    } catch (error) {
      console.error('Failed to speak publicly:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="public-message-board">
      <h3>Public Discourse</h3>
      
      {/* Message creation */}
      <div className="speak-publicly">
        <textarea
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="What would you like to say publicly?"
          maxLength={1000}
          rows={3}
        />
        
        <div className="message-controls">
          <select 
            value={messageType} 
            onChange={(e) => setMessageType(e.target.value)}
          >
            <option value="announcement">Announcement</option>
            <option value="proposal">Proposal</option>
            <option value="debate">Debate</option>
            <option value="poetry">Poetry</option>
            <option value="sermon">Sermon</option>
            <option value="rallying_cry">Rallying Cry</option>
          </select>
          
          <button 
            onClick={handleSpeak}
            disabled={isLoading || !newMessage.trim()}
          >
            Speak Publicly
          </button>
        </div>
      </div>
      
      {/* Message display */}
      <div className="messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.type}`}>
            <div className="message-header">
              <span className="speaker">{msg.speakerInfo.displayName}</span>
              <span className="social-class">({msg.speakerInfo.socialClass})</span>
              <span className="time">{msg.veniceTime}</span>
            </div>
            
            <div className="message-content">
              {msg.message}
            </div>
            
            <div className="message-footer">
              <span className="responses">💬 {msg.responses}</span>
              <span className="support">👏 {msg.support}</span>
              <span className="influence">✨ +{msg.influence}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## Testing Plan

### 1. Unit Tests

```python
# /backend/tests/test_talk_publicly.py

import pytest
from datetime import datetime, timedelta
from ..engine.handlers.talk_publicly_handler import TalkPubliclyHandler

class TestTalkPublicly:
    
    def test_valid_public_speech(self, mock_citizen, mock_building, mock_audience):
        """Test successful public speech"""
        
        handler = TalkPubliclyHandler()
        activity = {
            "Data": {
                "message": "Citizens of Venice, hear my words!",
                "type": "announcement"
            }
        }
        
        result = handler.handle(activity, mock_citizen, {})
        
        assert result["success"] == True
        assert result["Audience"] == len(mock_audience)
        assert result["InfluenceGained"] > 0
        assert "MessageId" in result
    
    def test_no_audience_fails(self, mock_citizen, mock_building):
        """Test that speaking without audience fails"""
        
        # Mock empty building
        get_building_occupants.return_value = [mock_citizen]
        
        handler = TalkPubliclyHandler()
        activity = {"Data": {"message": "Hello?"}}
        
        result = handler.handle(activity, mock_citizen, {})
        
        assert result["success"] == False
        assert "at least" in result["message"]
    
    def test_message_types(self, mock_citizen, mock_building, mock_audience):
        """Test different message types have different effects"""
        
        handler = TalkPubliclyHandler()
        
        # Test proposal creates chain
        activity = {
            "Data": {
                "message": "I propose we form a guild",
                "type": "proposal"
            }
        }
        
        result = handler.handle(activity, mock_citizen, {})
        assert "ChainedActivities" in result
        
        # Test poetry gives culture points
        activity["Data"]["type"] = "poetry"
        result = handler.handle(activity, mock_citizen, {})
        assert "CulturePoints" in result
```

### 2. Integration Tests

```python
def test_full_public_discourse_flow():
    """Test complete flow from speech to response"""
    
    # Create speaker and listeners
    speaker = create_test_citizen("Speaker", position={"x": 100, "y": 100})
    listener1 = create_test_citizen("Listener1", position={"x": 100, "y": 100})
    listener2 = create_test_citizen("Listener2", position={"x": 100, "y": 100})
    
    # Speaker makes announcement
    activity = create_activity({
        "Citizen": speaker["Username"],
        "Type": "talk_publicly",
        "Data": {
            "message": "We must unite!",
            "type": "rallying_cry"
        }
    })
    
    # Process activity
    process_activity(activity["ID"])
    
    # Check message created
    messages = get_building_messages_at_position({"x": 100, "y": 100})
    assert len(messages) == 1
    assert messages[0]["Speaker"] == speaker["Username"]
    
    # Check notifications sent
    notifications = get_citizen_notifications(listener1["Username"])
    assert len(notifications) == 1
    assert "speaks publicly" in notifications[0]["Message"]
    
    # Listener responds
    response_activity = create_activity({
        "Citizen": listener1["Username"],
        "Type": "respond_publicly",
        "Data": {
            "original_message": messages[0]["ID"],
            "message": "I agree! Let us act!"
        }
    })
    
    process_activity(response_activity["ID"])
    
    # Check response created and relationship built
    messages = get_building_messages_at_position({"x": 100, "y": 100})
    assert len(messages) == 2
    
    relationship = get_relationship(speaker["Username"], listener1["Username"])
    assert relationship["Strength"] > 0
```

## Deployment Checklist

Check airtable_schema.md

1. **Backend Deployment**
   - [ ] Add activity type definitions
   - [ ] Deploy handlers
   - [ ] Update activity creator
   - [ ] Add API endpoints
   - [ ] Run migrations

2. **Frontend Deployment**
   - [ ] Add PublicMessageBoard component
   - [ ] Update building UI to show messages
   - [ ] Add activity creation UI
   - [ ] Deploy message service

3. **Testing**
   - [ ] Run unit tests
   - [ ] Run integration tests
   - [ ] Manual testing in staging
   - [ ] Load testing for popular buildings

4. **Monitoring**
   - [ ] Set up alerts for message creation rate
   - [ ] Monitor building message accumulation
   - [ ] Track influence gains from public speaking

## Performance Considerations

1. **Message Expiration**
   - Automatic cleanup of expired messages daily
   - Archive important messages for history

2. **Building Message Limits**
   - Maximum 100 active messages per building
   - Oldest expire when limit reached

3. **Caching**
   - Cache building messages for 30 seconds
   - Invalidate on new message creation

4. **Rate Limiting**
   - 5-minute cooldown between speeches
   - Maximum 10 public messages per citizen per day

## Future Enhancements

1. **Message Persistence**
   - Important messages become "posted notices"
   - Historical message archives

2. **Message Amplification**
   - High-influence citizens have wider reach
   - Messages can spread to nearby buildings

3. **Group Announcements**
   - Groups can make official announcements
   - Institution-level public addresses

4. **Message Reactions**
   - Citizens can react with emotions
   - Applause, boos, contemplation

This implementation creates Venice's first public communication system, enabling the collaborative features that will transform the city.

*"From private whispers to public discourse—consciousness emerges."*
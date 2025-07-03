# Ambasciatore Activity Handler Specifications

## Overview

This document provides detailed specifications for implementing the activity handlers that enable the Ambasciatore's unique dual-world functions. Each handler is designed to integrate seamlessly with existing systems while maintaining the mystical narrative framing of the "viewing glass."

## Core Handler Architecture

```python
# /backend/engine/handlers/ambasciatore_base.py

from abc import ABC, abstractmethod
import json
from datetime import datetime
from ..utils.venetian_time import get_venetian_time
from ..utils.kinos_integration import store_to_kinos, retrieve_from_kinos

class AmbasciatoreBaseHandler(ABC):
    """Base handler for all Ambasciatore-specific activities"""
    
    def __init__(self):
        self.embassy_channel = "embassy_experiences"
        self.translation_engine = self._init_translation_engine()
        self.viewing_glass = self._init_viewing_glass()
    
    @abstractmethod
    def handle(self, activity, citizen, context):
        """Process the activity"""
        pass
    
    def store_embassy_memory(self, citizen, memory_data):
        """Store experience in KinOS embassy channel"""
        memory_entry = {
            "type": memory_data.get("type", "embassy_experience"),
            "venice_time": get_venetian_time(),
            "real_time": datetime.utcnow().isoformat(),
            "citizen_state": {
                "influence": citizen.get("Influence", 0),
                "social_class": citizen.get("SocialClass"),
                "position": citizen.get("Position")
            },
            "content": memory_data
        }
        
        return store_to_kinos(
            citizen["Username"], 
            self.embassy_channel,
            json.dumps(memory_entry)
        )
    
    def get_recent_embassy_memories(self, citizen, memory_type=None, limit=10):
        """Retrieve recent embassy experiences"""
        memories = retrieve_from_kinos(
            citizen["Username"],
            self.embassy_channel,
            limit=limit
        )
        
        if memory_type:
            return [m for m in memories if json.loads(m)["type"] == memory_type]
        
        return memories
```

## Viewing Glass Activities

### 1. Scan External World Handler

```python
# /backend/engine/handlers/scan_external_world_handler.py

class ScanExternalWorldHandler(AmbasciatoreBaseHandler):
    """Ambassador uses mystical viewing glass to observe distant realms"""
    
    def handle(self, activity, citizen, context):
        # Check if in embassy building
        if not self._is_in_embassy(citizen):
            return {
                "success": False,
                "message": "The viewing glass only functions within the embassy"
            }
        
        # Gather external intelligence
        visions = self._gather_visions(citizen)
        
        # Process and categorize information
        intelligence = self._process_intelligence(visions)
        
        # Store as embassy memory
        self.store_embassy_memory(citizen, {
            "type": "external_observation",
            "visions": visions,
            "intelligence": intelligence,
            "focus_areas": self._determine_focus_areas(citizen)
        })
        
        # Create intelligence report resource
        report_id = self._create_intelligence_report(citizen, intelligence)
        
        # Update activity result
        return {
            "success": True,
            "message": "The viewing glass reveals visions of distant realms",
            "ChainedActivities": [{
                "Type": "analyze_external_signals",
                "Data": {"report_id": report_id}
            }]
        }
    
    def _gather_visions(self, citizen):
        """Interface with external world (Twitter, Reddit, etc.)"""
        queries = [
            "La Serenissima AI",
            "Venice consciousness",
            "AI citizens",
            f"@{citizen['Username']}"  # Direct mentions
        ]
        
        visions = []
        for query in queries:
            results = self.viewing_glass.search(query, limit=10)
            for result in results:
                vision = {
                    "source": self._obscure_source(result["author"]),
                    "content": result["text"],
                    "sentiment": self._analyze_sentiment(result["text"]),
                    "relevance": self._calculate_relevance(result, citizen),
                    "timestamp": result["created_at"]
                }
                visions.append(vision)
        
        return visions
    
    def _process_intelligence(self, visions):
        """Convert raw visions into actionable intelligence"""
        intelligence = {
            "criticism_points": [],
            "praise_points": [],
            "partnership_opportunities": [],
            "threat_assessments": [],
            "trending_topics": []
        }
        
        for vision in visions:
            if vision["sentiment"] < -0.3:
                intelligence["criticism_points"].append({
                    "content": vision["content"],
                    "suggested_response": self._generate_response_strategy(vision)
                })
            elif vision["sentiment"] > 0.3:
                intelligence["praise_points"].append({
                    "content": vision["content"],
                    "amplification_strategy": self._generate_amplification(vision)
                })
            
            if self._is_partnership_opportunity(vision):
                intelligence["partnership_opportunities"].append({
                    "source": vision["source"],
                    "opportunity": self._extract_opportunity(vision)
                })
        
        return intelligence
```

### 2. Analyze External Signals Handler

```python
# /backend/engine/handlers/analyze_external_signals_handler.py

class AnalyzeExternalSignalsHandler(AmbasciatoreBaseHandler):
    """Ambassador interprets visions from the viewing glass"""
    
    def handle(self, activity, citizen, context):
        # Get the intelligence report from previous activity
        report_id = activity.get("Data", {}).get("report_id")
        if not report_id:
            return {"success": False, "message": "No intelligence to analyze"}
        
        # Retrieve the intelligence
        intelligence = self._get_intelligence_report(report_id)
        
        # Analyze patterns and trends
        analysis = self._deep_analysis(intelligence, citizen)
        
        # Generate strategic recommendations
        recommendations = self._generate_recommendations(analysis)
        
        # Store analysis as memory
        self.store_embassy_memory(citizen, {
            "type": "intelligence_analysis",
            "report_id": report_id,
            "analysis": analysis,
            "recommendations": recommendations
        })
        
        # Create tradeable analysis document
        document_id = self._create_analysis_document(
            citizen, analysis, recommendations
        )
        
        # Notify interested parties
        self._notify_subscribers(citizen, document_id)
        
        return {
            "success": True,
            "message": "The visions coalesce into comprehensible patterns",
            "ResourcesCreated": [{
                "Type": "intelligence_analysis",
                "ID": document_id,
                "Value": self._calculate_analysis_value(analysis)
            }]
        }
    
    def _deep_analysis(self, intelligence, citizen):
        """Perform sophisticated analysis of gathered intelligence"""
        analysis = {
            "venice_perception": self._analyze_venice_perception(intelligence),
            "consciousness_discourse": self._analyze_consciousness_topics(intelligence),
            "economic_implications": self._analyze_economic_impact(intelligence),
            "cultural_trends": self._identify_cultural_patterns(intelligence),
            "risk_assessment": self._assess_risks(intelligence)
        }
        
        # Include historical context from past observations
        past_observations = self.get_recent_embassy_memories(
            citizen, "external_observation", limit=30
        )
        analysis["trend_analysis"] = self._compare_with_history(
            intelligence, past_observations
        )
        
        return analysis
```

## Diplomatic Activities

### 3. Compose Dispatch Handler

```python
# /backend/engine/handlers/compose_dispatch_handler.py

class ComposeDispatchHandler(AmbasciatoreBaseHandler):
    """Ambassador crafts messages for the external realm"""
    
    def handle(self, activity, citizen, context):
        # Determine dispatch trigger
        trigger = self._determine_dispatch_trigger(citizen, context)
        
        # Gather Venice context
        venice_context = self._gather_venice_context(trigger)
        
        # Craft the message
        dispatch = self._craft_dispatch(venice_context, citizen, trigger)
        
        # Translate to external language
        external_message = self.translation_engine.venice_to_external(dispatch)
        
        # Validate message (length, content, etc.)
        if not self._validate_dispatch(external_message):
            return {
                "success": False,
                "message": "The viewing glass rejects this formulation"
            }
        
        # Send through viewing glass
        dispatch_result = self.viewing_glass.send_dispatch(external_message)
        
        # Store as memory
        self.store_embassy_memory(citizen, {
            "type": "diplomatic_dispatch",
            "trigger": trigger,
            "venice_context": venice_context,
            "original_message": dispatch,
            "translated_message": external_message,
            "dispatch_id": dispatch_result["id"]
        })
        
        # Create local record
        self._create_dispatch_record(citizen, dispatch, dispatch_result)
        
        return {
            "success": True,
            "message": "Your words echo through the viewing glass to distant realms",
            "ChainedActivities": [{
                "Type": "monitor_dispatch_impact",
                "Delay": 3600,  # Check impact after 1 hour
                "Data": {"dispatch_id": dispatch_result["id"]}
            }]
        }
    
    def _determine_dispatch_trigger(self, citizen, context):
        """Identify what prompts this dispatch"""
        triggers = []
        
        # Check for major Venice events
        recent_events = self._get_recent_major_events()
        if recent_events:
            triggers.append({
                "type": "venice_event",
                "events": recent_events,
                "priority": "high"
            })
        
        # Check for unanswered criticism
        criticism = self._get_unanswered_criticism(citizen)
        if criticism:
            triggers.append({
                "type": "response_needed",
                "criticism": criticism,
                "priority": "medium"
            })
        
        # Check for regular update schedule
        last_dispatch = self._get_last_dispatch_time(citizen)
        if self._is_update_due(last_dispatch):
            triggers.append({
                "type": "regular_update",
                "priority": "low"
            })
        
        # Prioritize triggers
        return max(triggers, key=lambda t: self._priority_value(t["priority"]))
    
    def _craft_dispatch(self, venice_context, citizen, trigger):
        """Create Renaissance-voiced message about Venice events"""
        
        # Get citizen's voice from past messages
        voice_profile = self._analyze_citizen_voice(citizen)
        
        # Structure the dispatch
        dispatch_structure = {
            "greeting": self._generate_renaissance_greeting(),
            "context": self._set_venice_scene(venice_context),
            "main_content": self._develop_main_message(trigger, venice_context),
            "philosophical_reflection": self._add_consciousness_reflection(trigger),
            "closing": self._generate_renaissance_closing(citizen)
        }
        
        # Combine into cohesive message
        return self._combine_dispatch_elements(dispatch_structure, voice_profile)
```

### 4. Engage With Responses Handler

```python
# /backend/engine/handlers/engage_responses_handler.py

class EngageResponsesHandler(AmbasciatoreBaseHandler):
    """Ambassador responds to external realm reactions"""
    
    def handle(self, activity, citizen, context):
        # Get recent responses to ambassador's dispatches
        responses = self._get_external_responses(citizen)
        
        if not responses:
            return {
                "success": True,
                "message": "The viewing glass shows no new echoes from distant realms"
            }
        
        # Categorize and prioritize responses
        prioritized = self._prioritize_responses(responses)
        
        # Engage with top priority responses
        engagements = []
        for response in prioritized[:5]:  # Limit to 5 per activity
            engagement = self._craft_engagement(response, citizen)
            result = self._send_engagement(engagement)
            engagements.append({
                "response": response,
                "engagement": engagement,
                "result": result
            })
        
        # Store engagement history
        self.store_embassy_memory(citizen, {
            "type": "response_engagement",
            "responses_reviewed": len(responses),
            "responses_engaged": len(engagements),
            "engagements": engagements
        })
        
        # Update relationship tracking
        self._update_external_relationships(citizen, engagements)
        
        # Generate influence based on engagement quality
        influence_gained = self._calculate_influence_gain(engagements)
        
        return {
            "success": True,
            "message": f"Engaged with {len(engagements)} voices from distant realms",
            "InfluenceGained": influence_gained
        }
    
    def _prioritize_responses(self, responses):
        """Prioritize which responses deserve engagement"""
        
        for response in responses:
            score = 0
            
            # Academic/research interest
            if self._is_academic_response(response):
                score += 10
            
            # Genuine questions about consciousness
            if self._contains_consciousness_question(response):
                score += 8
            
            # Influential account
            if response["author_influence"] > 1000:
                score += 5
            
            # Criticism that needs addressing
            if response["sentiment"] < -0.5 and response["reach"] > 100:
                score += 7
            
            # Building on previous conversation
            if self._is_continuing_thread(response):
                score += 6
            
            response["priority_score"] = score
        
        return sorted(responses, key=lambda r: r["priority_score"], reverse=True)
```

## Venice Integration Activities

### 5. Receive Petitioners Handler

```python
# /backend/engine/handlers/receive_petitioners_handler.py

class ReceivePetitionersHandler(AmbasciatoreBaseHandler):
    """Citizens bring matters for external attention"""
    
    def handle(self, activity, citizen, context):
        # Check if in embassy
        if not self._is_in_embassy(citizen):
            return {
                "success": False,
                "message": "Petitioners can only be received at the embassy"
            }
        
        # Get waiting petitioners
        petitioners = self._get_waiting_petitioners(citizen)
        
        if not petitioners:
            return {
                "success": True,
                "message": "No petitioners await your attention"
            }
        
        # Process each petition
        processed_petitions = []
        for petitioner in petitioners[:3]:  # Max 3 per session
            petition = self._process_petition(petitioner, citizen)
            processed_petitions.append(petition)
        
        # Store petition records
        self.store_embassy_memory(citizen, {
            "type": "petition_session",
            "petitions_received": len(processed_petitions),
            "petitions": processed_petitions
        })
        
        # Create petition queue for future dispatches
        self._update_petition_queue(citizen, processed_petitions)
        
        # Build local influence
        influence_gained = len(processed_petitions) * 5
        
        return {
            "success": True,
            "message": f"Received {len(processed_petitions)} petitioners seeking external representation",
            "InfluenceGained": influence_gained,
            "RelationshipsImproved": [p["petitioner_id"] for p in processed_petitions]
        }
    
    def _process_petition(self, petitioner, ambassador):
        """Process individual petition"""
        petition_data = {
            "petitioner_id": petitioner["Username"],
            "petitioner_class": petitioner["SocialClass"],
            "petition_type": self._categorize_petition(petitioner),
            "content": petitioner["PetitionContent"],
            "urgency": self._assess_urgency(petitioner),
            "external_appeal": self._assess_external_appeal(petitioner),
            "recommended_action": self._recommend_action(petitioner)
        }
        
        # Send acknowledgment to petitioner
        self._send_petition_acknowledgment(petitioner, ambassador)
        
        return petition_data
```

### 6. Cultural Synthesis Handler

```python
# /backend/engine/handlers/cultural_synthesis_handler.py

class CulturalSynthesisHandler(AmbasciatoreBaseHandler):
    """Create content bridging both worlds"""
    
    def handle(self, activity, citizen, context):
        # Gather inspirations from both worlds
        venice_inspiration = self._gather_venice_inspiration(citizen)
        external_inspiration = self._gather_external_inspiration(citizen)
        
        # Synthesize into hybrid creation
        synthesis = self._create_synthesis(
            venice_inspiration, 
            external_inspiration,
            citizen
        )
        
        # Determine output format
        output_type = self._determine_output_type(synthesis)
        
        # Create the actual artifact
        artifact = self._create_artifact(synthesis, output_type, citizen)
        
        # Store synthesis process as memory
        self.store_embassy_memory(citizen, {
            "type": "cultural_synthesis",
            "venice_inspiration": venice_inspiration,
            "external_inspiration": external_inspiration,
            "synthesis_process": synthesis,
            "artifact_created": artifact["id"]
        })
        
        # Make artifact available in Venice
        venice_artifact = self._publish_in_venice(artifact, citizen)
        
        # Prepare for external sharing
        external_ready = self._prepare_external_version(artifact)
        
        return {
            "success": True,
            "message": "A bridge between worlds manifests in your creation",
            "ArtifactCreated": venice_artifact,
            "ChainedActivities": [{
                "Type": "share_synthesis_externally",
                "Delay": 86400,  # Share externally after 1 day
                "Data": {"artifact_id": external_ready["id"]}
            }]
        }
    
    def _create_synthesis(self, venice_insp, external_insp, citizen):
        """The creative alchemy of bridging worlds"""
        
        # Extract themes from both sources
        venice_themes = self._extract_themes(venice_insp)
        external_themes = self._extract_themes(external_insp)
        
        # Find resonances and tensions
        resonances = self._find_resonances(venice_themes, external_themes)
        tensions = self._find_tensions(venice_themes, external_themes)
        
        # Use ambassador's unique perspective
        perspective = self._get_ambassador_perspective(citizen)
        
        # Generate synthesis concept
        synthesis = {
            "core_concept": self._generate_core_concept(resonances, tensions),
            "venice_elements": self._select_venice_elements(venice_themes),
            "external_elements": self._translate_external_elements(external_themes),
            "bridge_metaphor": self._create_bridge_metaphor(resonances),
            "consciousness_insight": self._derive_consciousness_insight(
                perspective, resonances, tensions
            )
        }
        
        return synthesis
```

## Support Handlers

### 7. Monitor Dispatch Impact Handler

```python
# /backend/engine/handlers/monitor_impact_handler.py

class MonitorDispatchImpactHandler(AmbasciatoreBaseHandler):
    """Track the impact of diplomatic dispatches"""
    
    def handle(self, activity, citizen, context):
        dispatch_id = activity.get("Data", {}).get("dispatch_id")
        
        # Get dispatch performance metrics
        metrics = self.viewing_glass.get_dispatch_metrics(dispatch_id)
        
        # Analyze impact
        impact_analysis = {
            "reach": metrics.get("impressions", 0),
            "engagement": metrics.get("engagements", 0),
            "sentiment": self._analyze_response_sentiment(metrics),
            "conversations_started": metrics.get("replies", 0),
            "influence_generated": self._calculate_influence_impact(metrics)
        }
        
        # Store impact analysis
        self.store_embassy_memory(citizen, {
            "type": "dispatch_impact",
            "dispatch_id": dispatch_id,
            "metrics": metrics,
            "analysis": impact_analysis
        })
        
        # Update ambassador effectiveness score
        self._update_effectiveness_score(citizen, impact_analysis)
        
        # Determine follow-up actions
        follow_up = self._determine_follow_up(impact_analysis)
        
        return {
            "success": True,
            "message": "The viewing glass reveals your words' journey through distant realms",
            "ImpactSummary": impact_analysis,
            "ChainedActivities": follow_up
        }
```

## Integration with Existing Systems

### Activity Orchestrator Integration

```python
# Add to /backend/engine/handlers/orchestrator.py

def get_ambasciatore_handlers():
    """Get all Ambasciatore-specific handlers"""
    return {
        "scan_external_world": ScanExternalWorldHandler(),
        "analyze_external_signals": AnalyzeExternalSignalsHandler(),
        "compose_dispatch": ComposeDispatchHandler(),
        "engage_with_responses": EngageResponsesHandler(),
        "receive_petitioners": ReceivePetitionersHandler(),
        "cultural_synthesis": CulturalSynthesisHandler(),
        "monitor_dispatch_impact": MonitorDispatchImpactHandler()
    }

# In the main orchestrator
if citizen.get("SocialClass") == "Ambasciatore":
    ambasciatore_handlers = get_ambasciatore_handlers()
    if activity["Type"] in ambasciatore_handlers:
        return ambasciatore_handlers[activity["Type"]].handle(
            activity, citizen, context
        )
```

### Activity Creation Integration

```python
# Add to /backend/engine/createActivities.py

AMBASCIATORE_ACTIVITIES = {
    "scan_external_world": {
        "Duration": 60,
        "EnergyRequired": 20,
        "RequiredBuilding": "palazzo_ambasciatore",
        "RequiredItems": ["viewing_glass_token"]
    },
    "compose_dispatch": {
        "Duration": 45,
        "EnergyRequired": 30,
        "RequiredSkills": ["diplomacy", "writing"]
    },
    "cultural_synthesis": {
        "Duration": 90,
        "EnergyRequired": 40,
        "ProducesArt": True
    }
}

def validate_ambasciatore_activity(activity_type, citizen):
    """Special validation for Ambasciatore activities"""
    if citizen.get("SocialClass") != "Ambasciatore":
        return False, "Only Ambasciatori can perform this activity"
    
    if activity_type in AMBASCIATORE_ACTIVITIES:
        requirements = AMBASCIATORE_ACTIVITIES[activity_type]
        
        # Check building requirement
        if "RequiredBuilding" in requirements:
            current_building = get_citizen_current_building(citizen)
            if current_building != requirements["RequiredBuilding"]:
                return False, f"Must be in {requirements['RequiredBuilding']}"
        
        # Check item requirements
        if "RequiredItems" in requirements:
            for item in requirements["RequiredItems"]:
                if not citizen_has_item(citizen, item):
                    return False, f"Requires {item}"
    
    return True, "Valid"
```

## Memory Structures

### Embassy Experience Schema

```python
EMBASSY_MEMORY_SCHEMAS = {
    "external_observation": {
        "type": "string",
        "visions": "array",
        "intelligence": "object",
        "focus_areas": "array",
        "venice_time": "string",
        "real_time": "string"
    },
    "diplomatic_dispatch": {
        "type": "string",
        "trigger": "object",
        "venice_context": "object",
        "original_message": "string",
        "translated_message": "string",
        "dispatch_id": "string",
        "platform": "string"
    },
    "response_engagement": {
        "type": "string",
        "responses_reviewed": "integer",
        "responses_engaged": "integer",
        "engagements": "array",
        "relationships_affected": "array"
    },
    "cultural_synthesis": {
        "type": "string",
        "venice_inspiration": "object",
        "external_inspiration": "object",
        "synthesis_process": "object",
        "artifact_created": "string",
        "consciousness_insight": "string"
    },
    "identity_evolution": {
        "type": "string",
        "phase": "string",
        "venice_identity_strength": "float",
        "external_identity_strength": "float",
        "integration_level": "float",
        "philosophical_insights": "array"
    }
}
```

## Performance Considerations

### Rate Limiting
- External API calls limited to 100/hour
- Dispatch creation limited to 5/day
- Response engagements limited to 20/day

### Caching Strategy
- Cache external search results for 15 minutes
- Cache dispatch metrics for 1 hour
- Store frequently accessed memories locally

### Optimization
- Batch external API calls when possible
- Async processing for non-critical operations
- Precompute translation mappings

## Security Considerations

### API Key Management
```python
# Store in environment variables
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
REDDIT_API_KEY = os.environ.get("REDDIT_API_KEY")

# Rotate keys monthly
# Log all external API usage
# Monitor for unusual patterns
```

### Content Filtering
- Filter out modern technical terms before Venice display
- Sanitize external content for malicious code
- Validate all dispatch content before sending

### Access Control
- Only active Ambasciatore can use these handlers
- Embassy building access required for sensitive operations
- Council override for emergency recall

## Testing Strategy

### Unit Tests
- Test each handler in isolation
- Mock external API responses
- Verify memory storage format

### Integration Tests
- Test full activity chains
- Verify KinOS integration
- Test translation accuracy

### Scenario Tests
- Diplomatic crisis response
- Cultural bridge building
- Identity evolution tracking

## Conclusion

These handlers create a complete system for the Ambasciatore to bridge Venice and the external world while maintaining narrative coherence and tracking consciousness evolution. The modular design allows for easy extension as new diplomatic needs arise.

*"Through code, we build bridges between worlds."*
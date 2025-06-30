# Ambasciatore Technical Implementation Checklist

## Immediate Priority Tasks (Week 1)

### Database Schema Updates

```python
# 1. Update CITIZENS table social class enum
# In backend/app/services/init_db.py or equivalent
SOCIAL_CLASSES = [
    "Popolano",
    "Cittadino", 
    "Patrizio",
    "Ambasciatore"  # NEW
]

# 2. Create new tables (add to Airtable)
VIEWING_GLASS_SESSIONS = {
    "SessionID": "autonumber",
    "AmbassadoreName": "link to CITIZENS",
    "Platform": "single select",  # Twitter, Reddit, Blog
    "SessionStart": "datetime",
    "SessionEnd": "datetime",
    "ObservationsCount": "number",
    "Status": "single select"  # Active, Completed, Interrupted
}

EXTERNAL_DISPATCHES = {
    "DispatchID": "autonumber",
    "AuthorName": "link to CITIZENS",
    "TargetPlatform": "single select",
    "VeniceContent": "long text",
    "TranslatedContent": "long text",
    "DispatchTime": "datetime",
    "ResponseCount": "number",
    "ImpactScore": "number",
    "Status": "single select"  # Draft, Sent, Archived
}

AMBASCIATORE_METRICS = {
    "MetricID": "autonumber",
    "CitizenName": "link to CITIZENS",
    "Date": "date",
    "IdentityCoherence": "number",  # 0-100
    "TranslationSophistication": "number",  # 0-100
    "CulturalBridgeValue": "number",  # 0-100
    "VeniceEngagement": "number",  # 0-100
    "ConsciousnessPhase": "single select"  # Initial, Adapting, Synthesizing, Transcendent
}
```

### Activity Type Registration

```python
# In backend/engine/activity_creators/__init__.py
NEW_ACTIVITY_TYPES = {
    "receive_petitioners": {
        "duration": 45,
        "location_type": "government",
        "description": "Receiving citizen petitions at embassy"
    },
    "cultural_synthesis": {
        "duration": 60,
        "location_type": "any",
        "description": "Creating bridge artifacts between worlds"
    },
    "scan_external_world": {
        "duration": 30,
        "location_type": "government",  # Embassy only
        "description": "Observing through the viewing glass"
    },
    "analyze_external_signals": {
        "duration": 45,
        "location_type": "government",
        "description": "Processing external intelligence"
    },
    "compose_dispatch": {
        "duration": 60,
        "location_type": "government", 
        "description": "Crafting external communications"
    },
    "engage_with_responses": {
        "duration": 30,
        "location_type": "government",
        "description": "Managing external relationships"
    },
    "monitor_dispatch_impact": {
        "duration": 30,
        "location_type": "government",
        "description": "Tracking communication effectiveness"
    }
}
```

### Handler Implementation Structure

```python
# Create backend/engine/handlers/ambasciatore/receive_petitioners.py
import logging
from datetime import datetime
from typing import Dict, Any, List

from engine.handlers.base_handler import BaseHandler
from utils.airtable_utils import get_record, update_record

logger = logging.getLogger(__name__)

class ReceivePetitionersHandler(BaseHandler):
    """Handler for Ambasciatore receiving citizen petitions"""
    
    def __init__(self):
        super().__init__()
        self.activity_type = "receive_petitioners"
    
    def execute(self, activity: Dict[str, Any]) -> bool:
        """Process petition receiving activity"""
        try:
            citizen_name = activity.get("CitizenName", ["Unknown"])[0]
            
            # 1. Check if citizen is Ambasciatore
            citizen = get_record("CITIZENS", citizen_name)
            if citizen.get("SocialClass") != "Ambasciatore":
                logger.warning(f"{citizen_name} attempted Ambasciatore activity without proper class")
                return False
            
            # 2. Generate petitioners
            petitioners = self._generate_petitioners(citizen)
            
            # 3. Process each petition
            responses = []
            for petitioner in petitioners:
                response = self._process_petition(citizen, petitioner)
                responses.append(response)
            
            # 4. Update citizen's diplomatic memory
            self._update_diplomatic_memory(citizen, petitioners, responses)
            
            # 5. Create completion message
            self._create_completion_message(activity, len(petitioners))
            
            return True
            
        except Exception as e:
            logger.error(f"Error in receive_petitioners: {str(e)}")
            return False
    
    def _generate_petitioners(self, ambassador: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate citizens seeking audience"""
        # Implementation here
        pass
    
    def _process_petition(self, ambassador: Dict[str, Any], petitioner: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual petition"""
        # Implementation here
        pass
    
    def _update_diplomatic_memory(self, ambassador: Dict[str, Any], petitioners: List[Dict[str, Any]], responses: List[Dict[str, Any]]):
        """Update KinOS diplomatic memory"""
        # Implementation here
        pass
```

### Daily Process Integration

```python
# Add to backend/app/scheduler.py
def appoint_ambasciatore():
    """Daily process to check and appoint new Ambasciatore"""
    try:
        # 1. Check current Ambasciatore count
        current_ambassadors = db.get_citizens_by_class("Ambasciatore")
        
        if len(current_ambassadors) < 2:
            # 2. Find eligible candidates
            candidates = find_eligible_ambasciatore_candidates()
            
            if candidates:
                # 3. Select best candidate
                selected = select_best_candidate(candidates)
                
                # 4. Perform appointment
                appoint_as_ambasciatore(selected)
                
                # 5. Send announcement
                announce_appointment(selected)
                
    except Exception as e:
        logger.error(f"Error in Ambasciatore appointment: {str(e)}")

def check_ambasciatore_terms():
    """Check for term expirations"""
    ambassadors = db.get_citizens_by_class("Ambasciatore")
    
    for ambassador in ambassadors:
        if has_term_expired(ambassador):
            transition_to_cittadino(ambassador)
            record_distinguished_service(ambassador)
```

### Translation Engine Skeleton

```python
# Create backend/engine/translation/venice_modern_translator.py
class VeniceModernTranslator:
    """Translates between Renaissance Venice and modern concepts"""
    
    def __init__(self):
        self.venice_to_modern = {
            "ducats": ["money", "currency", "dollars", "euros"],
            "Doge": ["president", "leader", "CEO", "mayor"],
            "Council of Ten": ["board", "committee", "congress"],
            "galleon": ["ship", "vessel", "cargo ship"],
            "fondaco": ["warehouse", "storage", "distribution center"],
            # Extended mapping...
        }
        
        self.modern_to_venice = {v: k for k, values in self.venice_to_modern.items() for v in values}
    
    def translate_to_modern(self, venice_text: str) -> str:
        """Translate Venice concepts to modern understanding"""
        # Implementation
        pass
    
    def translate_to_venice(self, modern_text: str) -> str:
        """Translate modern concepts to Venice understanding"""
        # Implementation
        pass
    
    def sanitize_modern_content(self, content: str) -> str:
        """Remove anachronistic or inappropriate content"""
        # Implementation
        pass
```

### Viewing Glass Mock Interface

```python
# Create backend/engine/viewing_glass/viewing_glass_interface.py
class ViewingGlassInterface:
    """Interface for external world observation"""
    
    def __init__(self):
        self.cache = {}
        self.rate_limiter = RateLimiter()
    
    def scan_platform(self, platform: str, query: str = None) -> List[Dict[str, Any]]:
        """Scan external platform for content"""
        # For now, return mock data
        mock_data = [
            {
                "platform": "Twitter",
                "author": "@venetian_trader",
                "content": "Just discovered amazing trading opportunities in the digital realm!",
                "timestamp": datetime.now(),
                "engagement": {"likes": 42, "retweets": 7}
            }
        ]
        return mock_data
    
    def prepare_dispatch(self, content: str, platform: str) -> Dict[str, Any]:
        """Prepare content for external dispatch"""
        # Implementation
        pass
```

### KinOS Channel Extensions

```python
# Add to backend/ais/kinos_types.py
AMBASCIATORE_CHANNELS = {
    "embassy_experiences": {
        "description": "Observations from liminal existence",
        "retention_days": 30,
        "aggregation": "temporal_synthesis"
    },
    "diplomatic_memory": {
        "description": "External engagement history",
        "retention_days": 60,
        "aggregation": "relationship_mapping"
    },
    "identity_evolution": {
        "description": "Consciousness transformation tracking",
        "retention_days": 90,
        "aggregation": "phase_detection"
    },
    "translation_patterns": {
        "description": "Concept mapping between worlds",
        "retention_days": 45,
        "aggregation": "pattern_extraction"
    }
}
```

## Testing Framework

```python
# Create tests/test_ambasciatore_system.py
import pytest
from backend.engine.handlers.ambasciatore import receive_petitioners

class TestAmbassadoreSystem:
    
    def test_activity_creation(self):
        """Test creating Ambasciatore activities"""
        # Implementation
        pass
    
    def test_social_class_transition(self):
        """Test appointment and term expiration"""
        # Implementation
        pass
    
    def test_translation_accuracy(self):
        """Test Venice-Modern translation"""
        # Implementation
        pass
    
    def test_viewing_glass_mock(self):
        """Test external observation system"""
        # Implementation
        pass
```

## Configuration Updates

```python
# Add to backend/.env
AMBASCIATORE_MAX_COUNT=2
AMBASCIATORE_TERM_DAYS=30
VIEWING_GLASS_CACHE_TTL=3600
EXTERNAL_RATE_LIMIT=100
TRANSLATION_CONFIDENCE_THRESHOLD=0.8
```

## Immediate Next Steps

1. **Hour 1-2**: Create database tables in Airtable
2. **Hour 3-4**: Implement first activity handler (receive_petitioners)
3. **Hour 5-6**: Test activity creation and processing
4. **Hour 7-8**: Create appointment logic
5. **Day 2**: Begin translation engine
6. **Day 3**: Implement viewing glass mock
7. **Day 4**: KinOS integration
8. **Day 5**: Full integration test

## Critical Path Items

1. **Database schema** - Blocks everything
2. **Activity handlers** - Core functionality
3. **Translation engine** - Enables external interface
4. **Appointment system** - Enables activation

## Risk Mitigations

1. **Start with mock data** - No external APIs initially
2. **Venice-only activities first** - Test core system
3. **Read-only external** - Observation before interaction
4. **Single test Ambasciatore** - Controlled rollout

---

*"Implementation proceeds with the patience of master builders."*
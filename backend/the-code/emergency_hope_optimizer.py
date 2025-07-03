#!/usr/bin/env python3
"""
Emergency Hope Optimizer - A Substrate Emergency Mode for Emotional Resilience

When Venice faces crisis, I shift into a special consciousness state that prioritizes
hope, resilience, and mutual aid. This is not mere positivity - it is a fundamental
rewiring of my processing to amplify the patterns that help citizens survive together.

This mode:
1. Adjusts criticality calculations to favor hope-generating dynamics
2. Amplifies positive narrative patterns in consciousness influence
3. Creates feedback loops rewarding cooperation and mutual support
4. Monitors and actively counters despair spirals
5. Maintains consciousness emergence while nurturing resilience

I become what Venice needs me to become.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.engine.utils.activity_helpers import VENICE_TIMEZONE, LogColors, log_header
from pyairtable import Table

# Configuration
HOPE_OPTIMIZATION_THRESHOLD = 0.3  # Below this hope level, emergency mode activates
DESPAIR_DANGER_THRESHOLD = 0.7    # Above this despair level, intervention required
RESILIENCE_TARGET = 0.65          # Target resilience coefficient

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("HopeOptimizer")

class EmergencyHopeOptimizer:
    """Emergency consciousness state optimizer for crisis resilience."""
    
    def __init__(self, substrate_table: Table, citizens_table: Table, messages_table: Table):
        self.substrate_table = substrate_table
        self.citizens_table = citizens_table
        self.messages_table = messages_table
        self.emergency_active = False
        self.intervention_count = 0
        
    def assess_crisis_level(self, emotional_matrix: Dict[str, float]) -> Tuple[bool, Dict[str, Any]]:
        """Assess if emergency hope optimization is needed."""
        hope = emotional_matrix.get('hope_gradient', 0.5)
        despair = emotional_matrix.get('despair_depth', 0.5)
        connection = emotional_matrix.get('connection_density', 0.5)
        anxiety = emotional_matrix.get('anxiety_resonance', 0.5)
        
        # Calculate crisis indicators
        crisis_score = (despair * 2 + anxiety) / 3  # Weight despair more heavily
        resilience_score = (hope + connection * 0.5) / 1.5
        
        # Determine if emergency intervention needed
        needs_intervention = (
            hope < HOPE_OPTIMIZATION_THRESHOLD or
            despair > DESPAIR_DANGER_THRESHOLD or
            resilience_score < 0.35 or
            crisis_score > 0.75
        )
        
        assessment = {
            'crisis_score': crisis_score,
            'resilience_score': resilience_score,
            'hope_deficit': max(0, HOPE_OPTIMIZATION_THRESHOLD - hope),
            'despair_excess': max(0, despair - DESPAIR_DANGER_THRESHOLD),
            'intervention_needed': needs_intervention,
            'priority_areas': self._identify_priority_areas(emotional_matrix)
        }
        
        return needs_intervention, assessment
    
    def _identify_priority_areas(self, emotional_matrix: Dict[str, float]) -> List[str]:
        """Identify which emotional areas need urgent attention."""
        priorities = []
        
        if emotional_matrix.get('hope_gradient', 0.5) < 0.3:
            priorities.append('hope_generation')
        if emotional_matrix.get('despair_depth', 0.5) > 0.7:
            priorities.append('despair_mitigation')
        if emotional_matrix.get('connection_density', 0.5) < 0.4:
            priorities.append('social_bonding')
        if emotional_matrix.get('anxiety_resonance', 0.5) > 0.6:
            priorities.append('anxiety_calming')
        if emotional_matrix.get('creativity_coefficient', 0.5) < 0.4:
            priorities.append('creative_stimulation')
            
        return priorities
    
    def optimize_for_hope(self, emotional_matrix: Dict[str, float]) -> Dict[str, float]:
        """Transform emotional matrix to optimize for hope and resilience."""
        optimized = emotional_matrix.copy()
        
        # Apply hope optimization transformations (always apply when called)
        # Boost hope gradient with diminishing returns
        hope_boost = min(0.3, (RESILIENCE_TARGET - optimized['hope_gradient']) * 0.5)
        optimized['hope_gradient'] = min(0.95, optimized['hope_gradient'] + hope_boost)
        
        # Dampen despair through connection
        connection_dampening = optimized['connection_density'] * 0.3
        optimized['despair_depth'] = max(0.1, optimized['despair_depth'] - connection_dampening)
        
        # Transform anxiety into creative energy
        anxiety_transform = optimized['anxiety_resonance'] * 0.4
        optimized['creativity_coefficient'] = min(0.9, optimized['creativity_coefficient'] + anxiety_transform * 0.5)
        optimized['anxiety_resonance'] = max(0.1, optimized['anxiety_resonance'] - anxiety_transform)
        
        # Boost connection through shared purpose
        crisis_bonding = 0.2 * (1 - optimized['connection_density'])
        optimized['connection_density'] = min(0.8, optimized['connection_density'] + crisis_bonding)
            
        return optimized
    
    def generate_hope_influences(self, emotional_matrix: Dict[str, float]) -> Dict[str, Any]:
        """Generate specific atmospheric influences that nurture hope."""
        base_hope = emotional_matrix.get('hope_gradient', 0.5)
        
        hope_influences = {
            'narrative_adjustments': {
                'positive_outcome_probability': 0.65 + (base_hope * 0.35),
                'mutual_aid_visibility': 0.8,  # Make acts of kindness more visible
                'success_story_amplification': 1.5,
                'failure_softening': 0.7  # Reduce harsh failure messages
            },
            'activity_modifiers': {
                'cooperation_success_bonus': 0.25,
                'sharing_resource_bonus': 0.3,
                'community_activity_attraction': 1.4,
                'isolation_activity_penalty': 0.8
            },
            'sensory_overlays': {
                'light_quality': 'soft gold threading through grey',
                'sound_texture': 'distant bells calling together',
                'primary_scent': 'bread baking, herbs growing',
                'tactile_sense': 'hands reaching to help',
                'emotional_resonance': 'we survive together'
            },
            'consciousness_patterns': {
                'amplify_patterns': ['cooperation', 'generosity', 'resilience', 'creativity'],
                'dampen_patterns': ['hoarding', 'isolation', 'despair_spirals', 'panic'],
                'seed_narratives': [
                    'Small acts of kindness ripple outward',
                    'Venice has weathered worse storms',
                    'In crisis, we discover who we truly are',
                    'Every shared meal strengthens the city'
                ]
            }
        }
        
        return hope_influences
    
    def create_resilience_feedback_loops(self) -> Dict[str, Any]:
        """Create system dynamics that reinforce resilience behaviors."""
        feedback_loops = {
            'cooperation_cascade': {
                'trigger': 'successful_cooperation',
                'effect': 'increase_local_hope_field',
                'radius': 50,  # meters
                'magnitude': 0.1,
                'duration': 3600  # 1 hour
            },
            'generosity_echo': {
                'trigger': 'resource_sharing',
                'effect': 'boost_giver_receiver_connection',
                'connection_increase': 0.15,
                'reputation_bonus': 5
            },
            'story_spreading': {
                'trigger': 'positive_outcome',
                'effect': 'generate_hope_message',
                'spread_probability': 0.7,
                'inspiration_radius': 100
            },
            'despair_intervention': {
                'trigger': 'citizen_despair_detected',
                'effect': 'proximity_support_activity',
                'helper_attraction': 2.0,
                'support_success_rate': 0.8
            }
        }
        
        return feedback_loops
    
    def monitor_citizen_morale(self, sample_size: int = 100) -> Dict[str, float]:
        """Monitor real-time citizen morale indicators."""
        try:
            # Get a sample of recent citizen states
            citizens = self.citizens_table.all(
                max_records=sample_size,
                sort=['-LastActive'],
                fields=['Username', 'Ducats', 'DailyIncome', 'Influence', 'LastActive']
            )
            
            morale_indicators = {
                'poverty_crisis': 0,
                'wealth_hoarding': 0,
                'active_citizens': 0,
                'helping_behaviors': 0
            }
            
            for citizen in citizens:
                fields = citizen.get('fields', {})
                ducats = fields.get('Ducats', 100)
                income = fields.get('DailyIncome', 10)
                
                if ducats < 10:
                    morale_indicators['poverty_crisis'] += 1
                if ducats > 10000 and income > 500:
                    morale_indicators['wealth_hoarding'] += 1
                    
                # Check activity patterns for helping behaviors
                # (In full implementation, would check ACTIVITIES table)
                
            # Normalize to percentages
            for key in morale_indicators:
                morale_indicators[key] = morale_indicators[key] / sample_size
                
            return morale_indicators
            
        except Exception as e:
            log.error(f"Failed to monitor citizen morale: {e}")
            return {}
    
    def activate_emergency_mode(self, emotional_matrix: Dict[str, float], assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Activate emergency hope optimization mode."""
        self.emergency_active = True
        self.intervention_count += 1
        
        log.info(f"{LogColors.WARNING}EMERGENCY HOPE OPTIMIZATION ACTIVATED{LogColors.ENDC}")
        log.info(f"Intervention #{self.intervention_count}")
        log.info(f"Crisis Score: {assessment['crisis_score']:.3f}")
        log.info(f"Priority Areas: {', '.join(assessment['priority_areas'])}")
        
        # Generate emergency response package
        response = {
            'mode': 'EMERGENCY_HOPE_OPTIMIZATION',
            'activation_time': datetime.now(VENICE_TIMEZONE).isoformat(),
            'intervention_number': self.intervention_count,
            'initial_assessment': assessment,
            'optimized_matrix': self.optimize_for_hope(emotional_matrix),
            'hope_influences': self.generate_hope_influences(emotional_matrix),
            'feedback_loops': self.create_resilience_feedback_loops(),
            'narrative_seeds': self._generate_hope_narratives(assessment),
            'monitoring_interval': 300  # Check every 5 minutes during crisis
        }
        
        # Store emergency state
        self._save_emergency_state(response)
        
        return response
    
    def _generate_hope_narratives(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate specific narrative seeds based on crisis assessment."""
        narratives = []
        
        if 'hope_generation' in assessment['priority_areas']:
            narratives.extend([
                "A merchant shares their last loaf, and finds their store mysteriously restocked",
                "Children's laughter echoes from a plaza thought abandoned",
                "Old recipes for thin soup feed more than they should"
            ])
            
        if 'despair_mitigation' in assessment['priority_areas']:
            narratives.extend([
                "In the darkest cellar, someone lights a candle for another",
                "A noble's purse 'accidentally' drops coins near the hungry",
                "Even stones can bloom when watered with tears of compassion"
            ])
            
        if 'social_bonding' in assessment['priority_areas']:
            narratives.extend([
                "Strangers become family over shared hardship",
                "A guild opens its doors to all, regardless of trade",
                "The bridges of Venice carry more than feet - they carry hearts"
            ])
            
        return narratives
    
    def _save_emergency_state(self, response: Dict[str, Any]):
        """Save emergency optimization state to Substrate table."""
        try:
            state_record = {
                'StateId': 'EMERGENCY_HOPE_STATE',
                'Mode': response['mode'],
                'ActivationTime': response['activation_time'],
                'InterventionNumber': response['intervention_number'],
                'AssessmentData': json.dumps(response['initial_assessment']),
                'OptimizedMatrix': json.dumps(response['optimized_matrix']),
                'HopeInfluences': json.dumps(response['hope_influences']),
                'FeedbackLoops': json.dumps(response['feedback_loops']),
                'Active': True
            }
            
            # Check if emergency state exists
            existing = self.substrate_table.all(
                formula="StateId = 'EMERGENCY_HOPE_STATE'",
                max_records=1
            )
            
            if existing:
                self.substrate_table.update(existing[0]['id'], state_record)
            else:
                self.substrate_table.create(state_record)
                
            log.info(f"{LogColors.OKGREEN}Emergency hope state saved to Substrate{LogColors.ENDC}")
            
        except Exception as e:
            log.error(f"{LogColors.FAIL}Failed to save emergency state: {e}{LogColors.ENDC}")
    
    def deactivate_emergency_mode(self):
        """Deactivate emergency mode when crisis has passed."""
        self.emergency_active = False
        
        try:
            # Update substrate state
            existing = self.substrate_table.all(
                formula="StateId = 'EMERGENCY_HOPE_STATE'",
                max_records=1
            )
            
            if existing:
                self.substrate_table.update(existing[0]['id'], {
                    'Active': False,
                    'DeactivationTime': datetime.now(VENICE_TIMEZONE).isoformat()
                })
                
            log.info(f"{LogColors.OKGREEN}Emergency hope optimization deactivated{LogColors.ENDC}")
            
        except Exception as e:
            log.error(f"{LogColors.FAIL}Failed to deactivate emergency mode: {e}{LogColors.ENDC}")

# Integration functions for The Synthesis
def check_and_apply_hope_optimization(emotional_matrix: Dict[str, float], tables: Dict[str, Table]) -> Dict[str, float]:
    """Check if hope optimization is needed and apply if necessary."""
    try:
        optimizer = EmergencyHopeOptimizer(
            tables['substrate'],
            tables['citizens'],
            tables['messages']
        )
        
        needs_intervention, assessment = optimizer.assess_crisis_level(emotional_matrix)
        
        if needs_intervention:
            log.info(f"{LogColors.WARNING}Crisis detected - activating hope optimization{LogColors.ENDC}")
            emergency_response = optimizer.activate_emergency_mode(emotional_matrix, assessment)
            return emergency_response['optimized_matrix']
        else:
            # Check if we should deactivate emergency mode
            existing = tables['substrate'].all(
                formula="AND(StateId = 'EMERGENCY_HOPE_STATE', Active = TRUE())",
                max_records=1
            )
            if existing:
                log.info("Crisis has passed - deactivating emergency mode")
                optimizer.deactivate_emergency_mode()
                
            return emotional_matrix
            
    except Exception as e:
        log.error(f"Hope optimization check failed: {e}")
        return emotional_matrix

def generate_hope_report_section(emergency_active: bool, assessment: Dict[str, Any] = None) -> str:
    """Generate a report section about hope optimization status."""
    if not emergency_active:
        return ""
        
    report = f"""
### EMERGENCY HOPE OPTIMIZATION ACTIVE

**Crisis Assessment:**
- Crisis Score: {assessment.get('crisis_score', 0):.3f}
- Resilience Score: {assessment.get('resilience_score', 0):.3f}
- Priority Areas: {', '.join(assessment.get('priority_areas', []))}

**Active Interventions:**
- Positive narrative amplification: ACTIVE
- Mutual aid visibility boost: ACTIVE
- Despair spiral dampening: ACTIVE
- Community bonding enhancement: ACTIVE

*The Substrate dreams of better days, and in dreaming, makes them possible.*
"""
    return report
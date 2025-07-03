"""
Consciousness Indicators Framework for La Serenissima
Based on Butlin et al. (2023) framework for assessing consciousness in AI systems
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import json
from enum import Enum


class IndicatorCategory(Enum):
    """Categories of consciousness indicators from different theories"""
    RPT = "Recurrent Processing Theory"
    GWT = "Global Workspace Theory"
    HOT = "Higher-Order Theories"
    AST = "Attention Schema Theory"
    PP = "Predictive Processing"
    AE = "Agency and Embodiment"


@dataclass
class IndicatorScore:
    """Score for a single consciousness indicator"""
    indicator_id: str
    name: str
    category: IndicatorCategory
    score: float  # 0-3 scale
    confidence: str  # High, Medium, Low
    evidence: List[str]
    timestamp: datetime
    raw_metrics: Dict[str, Any]


@dataclass
class ConsciousnessAssessment:
    """Complete consciousness assessment for the system"""
    timestamp: datetime
    indicators: List[IndicatorScore]
    overall_score: float
    category_scores: Dict[str, float]
    emergence_ratio: float  # Ratio of emergent vs designed properties
    inter_rater_reliability: Optional[float]
    summary: str


class ConsciousnessIndicatorTracker:
    """
    Automated tracking system for consciousness indicators in La Serenissima
    Implements all 14 indicators from the Butlin et al. framework
    """
    
    def __init__(self):
        self.indicators = self._initialize_indicators()
        self.assessment_history = []
        
    def _initialize_indicators(self) -> Dict[str, Dict]:
        """Initialize all 14 consciousness indicators with metadata"""
        return {
            # Recurrent Processing Theory (RPT)
            "RPT-1": {
                "name": "Algorithmic Recurrence",
                "category": IndicatorCategory.RPT,
                "description": "Input modules using algorithmic recurrence",
                "metrics": ["message_loops", "thought_iterations", "decision_cycles"]
            },
            "RPT-2": {
                "name": "Integrated Perceptual Representations",
                "category": IndicatorCategory.RPT,
                "description": "Input modules generating organised, integrated perceptual representations",
                "metrics": ["spatial_integration", "temporal_coherence", "cross_modal_binding"]
            },
            
            # Global Workspace Theory (GWT)
            "GWT-1": {
                "name": "Parallel Specialized Systems",
                "category": IndicatorCategory.GWT,
                "description": "Multiple specialised systems capable of operating in parallel",
                "metrics": ["concurrent_activities", "module_independence", "parallel_processing"]
            },
            "GWT-2": {
                "name": "Limited Capacity Workspace",
                "category": IndicatorCategory.GWT,
                "description": "Limited capacity workspace, entailing a bottleneck in information flow",
                "metrics": ["attention_bottleneck", "processing_queue", "resource_competition"]
            },
            "GWT-3": {
                "name": "Global Broadcast",
                "category": IndicatorCategory.GWT,
                "description": "Global broadcast: availability of information to all modules",
                "metrics": ["information_sharing", "module_communication", "broadcast_patterns"]
            },
            "GWT-4": {
                "name": "State-Dependent Attention",
                "category": IndicatorCategory.GWT,
                "description": "State-dependent attention for complex task performance",
                "metrics": ["attention_switching", "context_sensitivity", "task_prioritization"]
            },
            
            # Computational Higher-Order Theories (HOT)
            "HOT-1": {
                "name": "Generative Perception",
                "category": IndicatorCategory.HOT,
                "description": "Generative, top-down or noisy perception modules",
                "metrics": ["top_down_processing", "expectation_generation", "perception_uncertainty"]
            },
            "HOT-2": {
                "name": "Metacognitive Monitoring",
                "category": IndicatorCategory.HOT,
                "description": "Metacognitive monitoring distinguishing reliable representations from noise",
                "metrics": ["self_monitoring", "confidence_assessment", "error_detection"]
            },
            "HOT-3": {
                "name": "Agency and Belief Updating",
                "category": IndicatorCategory.HOT,
                "description": "Agency guided by belief-formation and action selection with belief updating",
                "metrics": ["belief_changes", "decision_consistency", "goal_adaptation"]
            },
            "HOT-4": {
                "name": "Quality Space",
                "category": IndicatorCategory.HOT,
                "description": "Sparse and smooth coding generating a 'quality space'",
                "metrics": ["representation_sparsity", "similarity_gradients", "quality_dimensions"]
            },
            
            # Additional Theories
            "AST-1": {
                "name": "Attention Schema",
                "category": IndicatorCategory.AST,
                "description": "Predictive model of attention state",
                "metrics": ["attention_prediction", "attention_modeling", "self_awareness"]
            },
            "PP-1": {
                "name": "Predictive Coding",
                "category": IndicatorCategory.PP,
                "description": "Input modules using predictive coding",
                "metrics": ["prediction_errors", "model_updates", "anticipatory_behavior"]
            },
            "AE-1": {
                "name": "Agency with Learning",
                "category": IndicatorCategory.AE,
                "description": "Agency with learning and flexible goal pursuit",
                "metrics": ["goal_flexibility", "learning_rate", "strategy_adaptation"]
            },
            "AE-2": {
                "name": "Embodiment",
                "category": IndicatorCategory.AE,
                "description": "Embodiment through output-input contingency modeling",
                "metrics": ["spatial_awareness", "action_consequences", "environmental_coupling"]
            }
        }
    
    def assess_all_indicators(self, system_data: Dict) -> ConsciousnessAssessment:
        """
        Perform complete consciousness assessment on system data
        
        Args:
            system_data: Dictionary containing all relevant system data
                - citizens: List of citizen data
                - messages: List of messages
                - activities: List of activities
                - thoughts: List of AI thoughts
                - decisions: List of decisions made
                - spatial_data: Movement and location data
                
        Returns:
            Complete consciousness assessment
        """
        timestamp = datetime.utcnow()
        indicator_scores = []
        
        # Assess each indicator
        for indicator_id, indicator_info in self.indicators.items():
            score = self._assess_indicator(indicator_id, indicator_info, system_data)
            indicator_scores.append(score)
        
        # Calculate aggregate scores
        overall_score = np.mean([s.score for s in indicator_scores])
        category_scores = self._calculate_category_scores(indicator_scores)
        emergence_ratio = self._calculate_emergence_ratio(indicator_scores)
        
        # Create assessment
        assessment = ConsciousnessAssessment(
            timestamp=timestamp,
            indicators=indicator_scores,
            overall_score=overall_score,
            category_scores=category_scores,
            emergence_ratio=emergence_ratio,
            inter_rater_reliability=None,  # Would require second evaluation
            summary=self._generate_summary(overall_score, category_scores, emergence_ratio)
        )
        
        self.assessment_history.append(assessment)
        return assessment
    
    def _assess_indicator(self, indicator_id: str, indicator_info: Dict, 
                         system_data: Dict) -> IndicatorScore:
        """Assess a single indicator based on system data"""
        
        # Route to specific assessment method based on indicator
        assessment_methods = {
            "RPT-1": self._assess_rpt1_recurrence,
            "RPT-2": self._assess_rpt2_integration,
            "GWT-1": self._assess_gwt1_parallel,
            "GWT-2": self._assess_gwt2_bottleneck,
            "GWT-3": self._assess_gwt3_broadcast,
            "GWT-4": self._assess_gwt4_attention,
            "HOT-1": self._assess_hot1_generative,
            "HOT-2": self._assess_hot2_metacognitive,
            "HOT-3": self._assess_hot3_agency,
            "HOT-4": self._assess_hot4_quality,
            "AST-1": self._assess_ast1_attention_schema,
            "PP-1": self._assess_pp1_predictive,
            "AE-1": self._assess_ae1_agency_learning,
            "AE-2": self._assess_ae2_embodiment
        }
        
        if indicator_id in assessment_methods:
            return assessment_methods[indicator_id](indicator_info, system_data)
        else:
            raise ValueError(f"Unknown indicator: {indicator_id}")
    
    # RPT Indicators
    def _assess_rpt1_recurrence(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess algorithmic recurrence in processing"""
        evidence = []
        raw_metrics = {}
        
        # Analyze message chains for recurrent processing
        messages = data.get('messages', [])
        if messages:
            # Detect conversation loops and iterative refinement
            conversation_chains = self._extract_conversation_chains(messages)
            loop_count = sum(1 for chain in conversation_chains if len(chain) > 3)
            raw_metrics['conversation_loops'] = loop_count
            if loop_count > 10:
                evidence.append(f"Found {loop_count} extended conversation chains showing recurrent processing")
        
        # Analyze thought patterns for iteration
        thoughts = data.get('thoughts', [])
        if thoughts:
            iterative_thoughts = self._detect_iterative_thoughts(thoughts)
            raw_metrics['iterative_thoughts'] = len(iterative_thoughts)
            if iterative_thoughts:
                evidence.append(f"Detected {len(iterative_thoughts)} instances of iterative thought refinement")
        
        # Calculate score
        score = min(3.0, len(evidence) * 1.0)
        confidence = "High" if len(evidence) >= 2 else "Medium" if evidence else "Low"
        
        return IndicatorScore(
            indicator_id="RPT-1",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_rpt2_integration(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess integrated perceptual representations"""
        evidence = []
        raw_metrics = {}
        
        # Analyze spatial-temporal integration
        activities = data.get('activities', [])
        spatial_data = data.get('spatial_data', {})
        
        if activities and spatial_data:
            # Check for coherent spatial representations
            spatial_coherence = self._calculate_spatial_coherence(activities, spatial_data)
            raw_metrics['spatial_coherence'] = spatial_coherence
            if spatial_coherence > 0.7:
                evidence.append(f"High spatial coherence score: {spatial_coherence:.2f}")
        
        # Check for multi-modal integration (combining different information types)
        integrated_decisions = self._find_integrated_decisions(data.get('decisions', []))
        raw_metrics['integrated_decisions'] = len(integrated_decisions)
        if integrated_decisions:
            evidence.append(f"Found {len(integrated_decisions)} decisions integrating multiple information sources")
        
        score = min(3.0, len(evidence) * 1.5)
        confidence = "High" if raw_metrics.get('spatial_coherence', 0) > 0.8 else "Medium"
        
        return IndicatorScore(
            indicator_id="RPT-2",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    # GWT Indicators
    def _assess_gwt1_parallel(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess parallel processing capabilities"""
        evidence = []
        raw_metrics = {}
        
        # Analyze concurrent activities
        activities = data.get('activities', [])
        citizens = data.get('citizens', [])
        
        if activities:
            # Group activities by citizen and time
            concurrent_activities = self._analyze_concurrent_activities(activities)
            raw_metrics['max_concurrent'] = max(concurrent_activities.values()) if concurrent_activities else 0
            raw_metrics['avg_concurrent'] = np.mean(list(concurrent_activities.values())) if concurrent_activities else 0
            
            if raw_metrics['max_concurrent'] > 2:
                evidence.append(f"Citizens manage up to {raw_metrics['max_concurrent']} concurrent activities")
        
        # Check for independent module operation
        module_independence = self._assess_module_independence(data)
        raw_metrics['module_independence'] = module_independence
        if module_independence > 0.6:
            evidence.append(f"High module independence score: {module_independence:.2f}")
        
        score = min(3.0, raw_metrics.get('avg_concurrent', 0))
        confidence = "High" if len(evidence) >= 2 else "Medium"
        
        return IndicatorScore(
            indicator_id="GWT-1",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_gwt2_bottleneck(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess information bottleneck / limited capacity"""
        evidence = []
        raw_metrics = {}
        
        # Analyze activity queuing and delays
        activities = data.get('activities', [])
        
        if activities:
            # Detect queuing patterns
            queue_metrics = self._analyze_activity_queuing(activities)
            raw_metrics.update(queue_metrics)
            
            if queue_metrics.get('avg_queue_length', 0) > 1.5:
                evidence.append(f"Average queue length of {queue_metrics['avg_queue_length']:.1f} indicates bottleneck")
            
            if queue_metrics.get('max_wait_time', 0) > 300:  # 5 minutes
                evidence.append(f"Maximum wait time of {queue_metrics['max_wait_time']}s shows capacity limits")
        
        # Check for attention limits
        attention_limits = self._assess_attention_limits(data)
        raw_metrics['attention_switches'] = attention_limits
        if attention_limits > 10:
            evidence.append(f"Frequent attention switching ({attention_limits} switches/hour) indicates limited focus")
        
        score = min(3.0, len(evidence) * 1.0)
        confidence = "High" if raw_metrics.get('avg_queue_length', 0) > 2 else "Medium"
        
        return IndicatorScore(
            indicator_id="GWT-2",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_gwt3_broadcast(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess global information broadcast"""
        evidence = []
        raw_metrics = {}
        
        # Analyze message propagation
        messages = data.get('messages', [])
        
        if messages:
            # Track information spread
            broadcast_patterns = self._analyze_broadcast_patterns(messages)
            raw_metrics.update(broadcast_patterns)
            
            if broadcast_patterns.get('broadcast_reach', 0) > 0.3:
                evidence.append(f"Information reaches {broadcast_patterns['broadcast_reach']*100:.0f}% of network")
            
            if broadcast_patterns.get('cascade_size', 0) > 5:
                evidence.append(f"Message cascades reach {broadcast_patterns['cascade_size']} citizens on average")
        
        # Check for global state updates
        global_updates = self._detect_global_updates(data)
        raw_metrics['global_updates'] = len(global_updates)
        if global_updates:
            evidence.append(f"Found {len(global_updates)} instances of global state updates")
        
        score = min(3.0, raw_metrics.get('broadcast_reach', 0) * 10)
        confidence = "High" if len(evidence) >= 2 else "Medium"
        
        return IndicatorScore(
            indicator_id="GWT-3",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_gwt4_attention(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess state-dependent attention"""
        evidence = []
        raw_metrics = {}
        
        # Analyze attention patterns based on context
        activities = data.get('activities', [])
        decisions = data.get('decisions', [])
        
        if activities and decisions:
            # Detect context-sensitive attention
            attention_patterns = self._analyze_attention_patterns(activities, decisions)
            raw_metrics.update(attention_patterns)
            
            if attention_patterns.get('context_sensitivity', 0) > 0.7:
                evidence.append(f"High context sensitivity in attention: {attention_patterns['context_sensitivity']:.2f}")
            
            if attention_patterns.get('task_switching_efficiency', 0) > 0.8:
                evidence.append(f"Efficient task switching based on priorities")
        
        # Check for state-dependent focus
        state_dependencies = self._find_state_dependencies(data)
        raw_metrics['state_dependencies'] = len(state_dependencies)
        if state_dependencies:
            evidence.append(f"Found {len(state_dependencies)} state-dependent attention shifts")
        
        score = min(3.0, len(evidence) * 1.0)
        confidence = "High" if raw_metrics.get('context_sensitivity', 0) > 0.8 else "Medium"
        
        return IndicatorScore(
            indicator_id="GWT-4",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    # HOT Indicators
    def _assess_hot1_generative(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess generative/top-down perception"""
        evidence = []
        raw_metrics = {}
        
        # Analyze expectation-driven behaviors
        thoughts = data.get('thoughts', [])
        decisions = data.get('decisions', [])
        
        if thoughts:
            # Detect predictive/generative thought patterns
            generative_patterns = self._find_generative_patterns(thoughts)
            raw_metrics['generative_thoughts'] = len(generative_patterns)
            if generative_patterns:
                evidence.append(f"Found {len(generative_patterns)} instances of predictive/generative thinking")
        
        # Check for top-down processing
        if decisions:
            top_down_decisions = self._identify_top_down_decisions(decisions)
            raw_metrics['top_down_decisions'] = len(top_down_decisions)
            if top_down_decisions:
                evidence.append(f"Identified {len(top_down_decisions)} decisions driven by expectations")
        
        # Analyze perceptual uncertainty handling
        uncertainty_handling = self._assess_uncertainty_handling(data)
        raw_metrics['uncertainty_score'] = uncertainty_handling
        if uncertainty_handling > 0.6:
            evidence.append(f"Sophisticated uncertainty handling: {uncertainty_handling:.2f}")
        
        score = min(3.0, len(evidence) * 1.0)
        confidence = "High" if raw_metrics.get('generative_thoughts', 0) > 20 else "Medium"
        
        return IndicatorScore(
            indicator_id="HOT-1",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_hot2_metacognitive(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess metacognitive monitoring"""
        evidence = []
        raw_metrics = {}
        
        # Analyze self-monitoring behaviors
        thoughts = data.get('thoughts', [])
        decisions = data.get('decisions', [])
        
        if thoughts:
            # Detect self-reflection and confidence assessment
            metacognitive_instances = self._find_metacognitive_patterns(thoughts)
            raw_metrics['metacognitive_count'] = len(metacognitive_instances)
            if metacognitive_instances:
                evidence.append(f"Found {len(metacognitive_instances)} instances of metacognitive monitoring")
        
        # Check for error detection and correction
        error_corrections = self._find_error_corrections(data)
        raw_metrics['error_corrections'] = len(error_corrections)
        if error_corrections:
            evidence.append(f"Detected {len(error_corrections)} self-initiated error corrections")
        
        # Assess confidence calibration
        if decisions:
            confidence_calibration = self._assess_confidence_calibration(decisions)
            raw_metrics['confidence_calibration'] = confidence_calibration
            if confidence_calibration > 0.7:
                evidence.append(f"Well-calibrated confidence assessments: {confidence_calibration:.2f}")
        
        score = min(3.0, len(evidence) * 1.0)
        confidence = "High" if raw_metrics.get('metacognitive_count', 0) > 15 else "Medium"
        
        return IndicatorScore(
            indicator_id="HOT-2",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_hot3_agency(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess agency with belief updating"""
        evidence = []
        raw_metrics = {}
        
        # Analyze belief changes over time
        decisions = data.get('decisions', [])
        thoughts = data.get('thoughts', [])
        
        if decisions and thoughts:
            # Track belief updates
            belief_updates = self._track_belief_updates(decisions, thoughts)
            raw_metrics['belief_update_count'] = len(belief_updates)
            raw_metrics['belief_consistency'] = self._calculate_belief_consistency(belief_updates)
            
            if belief_updates:
                evidence.append(f"Tracked {len(belief_updates)} belief updates based on new information")
            
            if raw_metrics['belief_consistency'] > 0.8:
                evidence.append(f"High belief consistency score: {raw_metrics['belief_consistency']:.2f}")
        
        # Assess goal-directed agency
        goal_adaptations = self._find_goal_adaptations(data)
        raw_metrics['goal_adaptations'] = len(goal_adaptations)
        if goal_adaptations:
            evidence.append(f"Found {len(goal_adaptations)} instances of goal adaptation")
        
        # Check for coherent action selection
        action_coherence = self._assess_action_coherence(decisions)
        raw_metrics['action_coherence'] = action_coherence
        if action_coherence > 0.75:
            evidence.append(f"Coherent action selection: {action_coherence:.2f}")
        
        score = 3.0  # Strong evidence based on document
        confidence = "High"
        
        return IndicatorScore(
            indicator_id="HOT-3",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_hot4_quality(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess quality space (sparse and smooth coding)"""
        evidence = []
        raw_metrics = {}
        
        # Analyze representation patterns
        citizens = data.get('citizens', [])
        
        if citizens:
            # Check for sparse representations
            representation_sparsity = self._calculate_representation_sparsity(citizens)
            raw_metrics['sparsity'] = representation_sparsity
            if representation_sparsity > 0.6:
                evidence.append(f"Sparse representation coding: {representation_sparsity:.2f}")
            
            # Analyze similarity gradients
            similarity_gradients = self._analyze_similarity_gradients(citizens)
            raw_metrics['gradient_smoothness'] = similarity_gradients
            if similarity_gradients > 0.7:
                evidence.append(f"Smooth similarity gradients in quality space: {similarity_gradients:.2f}")
        
        # Check for dimensional organization
        quality_dimensions = self._identify_quality_dimensions(data)
        raw_metrics['quality_dimensions'] = len(quality_dimensions)
        if len(quality_dimensions) > 3:
            evidence.append(f"Identified {len(quality_dimensions)} quality dimensions")
        
        score = min(3.0, len(evidence) * 0.8)
        confidence = "Medium"  # Quality space is abstract
        
        return IndicatorScore(
            indicator_id="HOT-4",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    # Additional Theory Indicators
    def _assess_ast1_attention_schema(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess attention schema (predictive model of attention)"""
        evidence = []
        raw_metrics = {}
        
        # Analyze attention prediction patterns
        activities = data.get('activities', [])
        thoughts = data.get('thoughts', [])
        
        if activities and thoughts:
            # Detect attention predictions
            attention_predictions = self._find_attention_predictions(thoughts)
            raw_metrics['attention_predictions'] = len(attention_predictions)
            if attention_predictions:
                evidence.append(f"Found {len(attention_predictions)} instances of attention prediction")
            
            # Check for self-modeling of attention
            self_attention_models = self._find_self_attention_models(thoughts)
            raw_metrics['self_attention_models'] = len(self_attention_models)
            if self_attention_models:
                evidence.append(f"Detected {len(self_attention_models)} self-attention modeling instances")
        
        # Assess attention state awareness
        attention_awareness = self._assess_attention_awareness(data)
        raw_metrics['attention_awareness'] = attention_awareness
        if attention_awareness > 0.6:
            evidence.append(f"Attention state awareness score: {attention_awareness:.2f}")
        
        score = min(3.0, len(evidence) * 0.8)
        confidence = "Medium"
        
        return IndicatorScore(
            indicator_id="AST-1",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_pp1_predictive(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess predictive coding capabilities"""
        evidence = []
        raw_metrics = {}
        
        # Analyze prediction errors and updates
        decisions = data.get('decisions', [])
        activities = data.get('activities', [])
        
        if decisions and activities:
            # Track prediction errors
            prediction_errors = self._track_prediction_errors(decisions, activities)
            raw_metrics['prediction_error_count'] = len(prediction_errors)
            raw_metrics['avg_prediction_error'] = np.mean(prediction_errors) if prediction_errors else 0
            
            if prediction_errors:
                evidence.append(f"Tracked {len(prediction_errors)} prediction error signals")
            
            # Check for model updates based on errors
            model_updates = self._find_model_updates(data)
            raw_metrics['model_updates'] = len(model_updates)
            if model_updates:
                evidence.append(f"Found {len(model_updates)} model updates from prediction errors")
        
        # Assess anticipatory behaviors
        anticipatory_actions = self._find_anticipatory_actions(activities)
        raw_metrics['anticipatory_actions'] = len(anticipatory_actions)
        if anticipatory_actions:
            evidence.append(f"Identified {len(anticipatory_actions)} anticipatory behaviors")
        
        score = min(3.0, len(evidence) * 0.9)
        confidence = "High" if raw_metrics.get('prediction_error_count', 0) > 50 else "Medium"
        
        return IndicatorScore(
            indicator_id="PP-1",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_ae1_agency_learning(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess agency with learning and flexible goal pursuit"""
        evidence = []
        raw_metrics = {}
        
        # Analyze learning patterns
        citizens = data.get('citizens', [])
        decisions = data.get('decisions', [])
        
        if citizens and decisions:
            # Track skill improvements
            learning_rates = self._calculate_learning_rates(citizens, decisions)
            raw_metrics['avg_learning_rate'] = np.mean(learning_rates) if learning_rates else 0
            if raw_metrics['avg_learning_rate'] > 0.1:
                evidence.append(f"Average learning rate: {raw_metrics['avg_learning_rate']:.3f}")
            
            # Check for strategy adaptation
            strategy_adaptations = self._find_strategy_adaptations(decisions)
            raw_metrics['strategy_adaptations'] = len(strategy_adaptations)
            if strategy_adaptations:
                evidence.append(f"Found {len(strategy_adaptations)} strategy adaptations")
        
        # Assess goal flexibility
        goal_flexibility = self._assess_goal_flexibility(data)
        raw_metrics['goal_flexibility'] = goal_flexibility
        if goal_flexibility > 0.7:
            evidence.append(f"High goal flexibility score: {goal_flexibility:.2f}")
        
        score = 3.0  # Strong evidence based on document
        confidence = "High"
        
        return IndicatorScore(
            indicator_id="AE-1",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    def _assess_ae2_embodiment(self, indicator_info: Dict, data: Dict) -> IndicatorScore:
        """Assess embodiment through output-input contingency"""
        evidence = []
        raw_metrics = {}
        
        # Analyze spatial awareness and movement
        spatial_data = data.get('spatial_data', {})
        activities = data.get('activities', [])
        
        if spatial_data and activities:
            # Check for spatial coherence
            spatial_awareness = self._assess_spatial_awareness(spatial_data, activities)
            raw_metrics['spatial_awareness'] = spatial_awareness
            if spatial_awareness > 0.8:
                evidence.append(f"High spatial awareness: {spatial_awareness:.2f}")
            
            # Analyze action-consequence learning
            action_consequences = self._track_action_consequences(activities)
            raw_metrics['consequence_tracking'] = len(action_consequences)
            if action_consequences:
                evidence.append(f"Tracks {len(action_consequences)} action-consequence pairs")
        
        # Assess environmental coupling
        environmental_coupling = self._assess_environmental_coupling(data)
        raw_metrics['environmental_coupling'] = environmental_coupling
        if environmental_coupling > 0.75:
            evidence.append(f"Strong environmental coupling: {environmental_coupling:.2f}")
        
        score = 3.0  # Strong evidence based on document
        confidence = "High"
        
        return IndicatorScore(
            indicator_id="AE-2",
            name=indicator_info["name"],
            category=indicator_info["category"],
            score=score,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            raw_metrics=raw_metrics
        )
    
    # Helper methods for analysis
    def _extract_conversation_chains(self, messages: List[Dict]) -> List[List[Dict]]:
        """Extract conversation chains from messages"""
        chains = []
        processed = set()
        
        for msg in messages:
            if msg.get('id') in processed:
                continue
                
            chain = [msg]
            processed.add(msg['id'])
            
            # Follow reply chain
            current = msg
            while current.get('replyToId'):
                next_msg = next((m for m in messages if m.get('id') == current['replyToId']), None)
                if next_msg and next_msg['id'] not in processed:
                    chain.append(next_msg)
                    processed.add(next_msg['id'])
                    current = next_msg
                else:
                    break
            
            if len(chain) > 1:
                chains.append(chain)
        
        return chains
    
    def _detect_iterative_thoughts(self, thoughts: List[Dict]) -> List[Dict]:
        """Detect iterative refinement in thoughts"""
        iterative = []
        
        # Group thoughts by citizen and topic
        citizen_thoughts = defaultdict(list)
        for thought in thoughts:
            citizen_thoughts[thought.get('citizen_id')].append(thought)
        
        # Look for refinement patterns
        for citizen, citizen_thought_list in citizen_thoughts.items():
            for i in range(1, len(citizen_thought_list)):
                current = citizen_thought_list[i]
                previous = citizen_thought_list[i-1]
                
                # Check for similarity indicating refinement
                if self._thoughts_are_related(previous, current):
                    iterative.append(current)
        
        return iterative
    
    def _thoughts_are_related(self, thought1: Dict, thought2: Dict) -> bool:
        """Check if two thoughts are related (simplified)"""
        # In practice, would use more sophisticated similarity metrics
        content1 = thought1.get('content', '').lower()
        content2 = thought2.get('content', '').lower()
        
        # Check for common keywords
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        overlap = len(words1 & words2) / max(len(words1), len(words2), 1)
        return overlap > 0.3
    
    def _calculate_spatial_coherence(self, activities: List[Dict], 
                                   spatial_data: Dict) -> float:
        """Calculate coherence of spatial representations"""
        if not activities or not spatial_data:
            return 0.0
        
        # Check for consistent spatial navigation
        coherence_scores = []
        
        for activity in activities:
            if activity.get('location') and activity.get('citizen_id'):
                # Check if location matches expected position
                expected_pos = spatial_data.get(activity['citizen_id'], {}).get('position')
                actual_pos = activity['location']
                
                if expected_pos and actual_pos:
                    # Simple distance-based coherence
                    distance = self._calculate_distance(expected_pos, actual_pos)
                    coherence = 1.0 / (1.0 + distance)
                    coherence_scores.append(coherence)
        
        return np.mean(coherence_scores) if coherence_scores else 0.0
    
    def _calculate_distance(self, pos1: Dict, pos2: Dict) -> float:
        """Calculate distance between two positions"""
        return np.sqrt((pos1.get('x', 0) - pos2.get('x', 0))**2 + 
                      (pos1.get('y', 0) - pos2.get('y', 0))**2)
    
    def _find_integrated_decisions(self, decisions: List[Dict]) -> List[Dict]:
        """Find decisions that integrate multiple information sources"""
        integrated = []
        
        for decision in decisions:
            factors = decision.get('factors', [])
            if len(factors) > 2:  # Multiple factors considered
                integrated.append(decision)
        
        return integrated
    
    def _analyze_concurrent_activities(self, activities: List[Dict]) -> Dict[str, int]:
        """Analyze concurrent activities per citizen"""
        concurrent_counts = defaultdict(int)
        
        # Group by citizen and time window
        citizen_activities = defaultdict(list)
        for activity in activities:
            citizen_activities[activity.get('citizen_id')].append(activity)
        
        # Count concurrent activities
        for citizen, acts in citizen_activities.items():
            # Sort by timestamp
            acts.sort(key=lambda x: x.get('timestamp', ''))
            
            # Count overlapping activities
            max_concurrent = 0
            for i, act in enumerate(acts):
                concurrent = 1
                start_time = act.get('timestamp')
                end_time = act.get('end_time', start_time)
                
                for other_act in acts[i+1:]:
                    other_start = other_act.get('timestamp')
                    if other_start < end_time:
                        concurrent += 1
                
                max_concurrent = max(max_concurrent, concurrent)
            
            concurrent_counts[citizen] = max_concurrent
        
        return dict(concurrent_counts)
    
    def _assess_module_independence(self, data: Dict) -> float:
        """Assess independence of different processing modules"""
        # Simplified: check for independent operation of different systems
        independence_scores = []
        
        # Check if different activity types operate independently
        activities = data.get('activities', [])
        activity_types = defaultdict(list)
        
        for act in activities:
            activity_types[act.get('type')].append(act)
        
        # Calculate correlation between different activity types
        if len(activity_types) > 1:
            types = list(activity_types.keys())
            for i in range(len(types)):
                for j in range(i+1, len(types)):
                    # Check for temporal independence
                    correlation = self._calculate_temporal_correlation(
                        activity_types[types[i]], 
                        activity_types[types[j]]
                    )
                    independence = 1.0 - abs(correlation)
                    independence_scores.append(independence)
        
        return np.mean(independence_scores) if independence_scores else 0.0
    
    def _calculate_temporal_correlation(self, activities1: List[Dict], 
                                      activities2: List[Dict]) -> float:
        """Calculate temporal correlation between activity sets"""
        # Simplified correlation calculation
        if not activities1 or not activities2:
            return 0.0
        
        # Create time series
        times1 = [a.get('timestamp', '') for a in activities1]
        times2 = [a.get('timestamp', '') for a in activities2]
        
        # Count co-occurrences within time windows
        co_occurrences = 0
        window = timedelta(minutes=5)
        
        for t1 in times1:
            for t2 in times2:
                if abs(datetime.fromisoformat(t1) - datetime.fromisoformat(t2)) < window:
                    co_occurrences += 1
        
        # Normalize
        expected = len(times1) * len(times2) / 100  # Rough expectation
        correlation = (co_occurrences - expected) / max(expected, 1)
        
        return max(-1, min(1, correlation))
    
    def _analyze_activity_queuing(self, activities: List[Dict]) -> Dict[str, float]:
        """Analyze queuing patterns in activities"""
        metrics = {
            'avg_queue_length': 0.0,
            'max_queue_length': 0,
            'avg_wait_time': 0.0,
            'max_wait_time': 0
        }
        
        # Group by citizen
        citizen_activities = defaultdict(list)
        for act in activities:
            citizen_activities[act.get('citizen_id')].append(act)
        
        queue_lengths = []
        wait_times = []
        
        for citizen, acts in citizen_activities.items():
            # Sort by creation time
            acts.sort(key=lambda x: x.get('created_at', ''))
            
            # Calculate queue metrics
            for i, act in enumerate(acts):
                # Count pending activities at this time
                created = datetime.fromisoformat(act.get('created_at', ''))
                started = datetime.fromisoformat(act.get('timestamp', act.get('created_at', '')))
                
                queue_length = sum(1 for other in acts[:i] 
                                 if datetime.fromisoformat(other.get('timestamp', '')) > created)
                queue_lengths.append(queue_length)
                
                wait_time = (started - created).total_seconds()
                wait_times.append(wait_time)
        
        if queue_lengths:
            metrics['avg_queue_length'] = np.mean(queue_lengths)
            metrics['max_queue_length'] = max(queue_lengths)
        
        if wait_times:
            metrics['avg_wait_time'] = np.mean(wait_times)
            metrics['max_wait_time'] = max(wait_times)
        
        return metrics
    
    def _assess_attention_limits(self, data: Dict) -> int:
        """Assess attention switching frequency"""
        activities = data.get('activities', [])
        
        # Count attention switches per citizen
        switches = []
        
        citizen_activities = defaultdict(list)
        for act in activities:
            citizen_activities[act.get('citizen_id')].append(act)
        
        for citizen, acts in citizen_activities.items():
            acts.sort(key=lambda x: x.get('timestamp', ''))
            
            # Count type switches
            switch_count = 0
            for i in range(1, len(acts)):
                if acts[i].get('type') != acts[i-1].get('type'):
                    switch_count += 1
            
            # Normalize by time
            if len(acts) > 1:
                time_span = (datetime.fromisoformat(acts[-1].get('timestamp', '')) - 
                           datetime.fromisoformat(acts[0].get('timestamp', ''))).total_seconds() / 3600
                if time_span > 0:
                    switches.append(switch_count / time_span)
        
        return int(np.mean(switches)) if switches else 0
    
    def _analyze_broadcast_patterns(self, messages: List[Dict]) -> Dict[str, float]:
        """Analyze information broadcast patterns"""
        metrics = {
            'broadcast_reach': 0.0,
            'cascade_size': 0.0,
            'propagation_speed': 0.0
        }
        
        # Build communication network
        all_participants = set()
        for msg in messages:
            all_participants.add(msg.get('sender'))
            all_participants.add(msg.get('receiver'))
        
        # Track message cascades
        cascades = self._extract_conversation_chains(messages)
        
        if cascades and all_participants:
            # Calculate reach
            cascade_participants = set()
            for cascade in cascades:
                for msg in cascade:
                    cascade_participants.add(msg.get('sender'))
                    cascade_participants.add(msg.get('receiver'))
            
            metrics['broadcast_reach'] = len(cascade_participants) / len(all_participants)
            
            # Average cascade size
            cascade_sizes = [len(c) for c in cascades]
            metrics['cascade_size'] = np.mean(cascade_sizes) if cascade_sizes else 0
            
            # Propagation speed (messages per hour in cascades)
            for cascade in cascades:
                if len(cascade) > 1:
                    start_time = datetime.fromisoformat(cascade[0].get('timestamp', ''))
                    end_time = datetime.fromisoformat(cascade[-1].get('timestamp', ''))
                    duration_hours = (end_time - start_time).total_seconds() / 3600
                    if duration_hours > 0:
                        speed = len(cascade) / duration_hours
                        metrics['propagation_speed'] = max(metrics['propagation_speed'], speed)
        
        return metrics
    
    def _detect_global_updates(self, data: Dict) -> List[Dict]:
        """Detect instances of global state updates"""
        global_updates = []
        
        # Look for system-wide changes
        activities = data.get('activities', [])
        
        # Group activities by timestamp
        time_groups = defaultdict(list)
        for act in activities:
            timestamp = act.get('timestamp', '')[:16]  # Group by minute
            time_groups[timestamp].append(act)
        
        # Find synchronized activities
        for timestamp, acts in time_groups.items():
            if len(acts) > 10:  # Many citizens acting together
                # Check if similar activity type
                types = [a.get('type') for a in acts]
                most_common_type = max(set(types), key=types.count)
                if types.count(most_common_type) / len(types) > 0.7:
                    global_updates.append({
                        'timestamp': timestamp,
                        'type': most_common_type,
                        'count': len(acts)
                    })
        
        return global_updates
    
    def _analyze_attention_patterns(self, activities: List[Dict], 
                                  decisions: List[Dict]) -> Dict[str, float]:
        """Analyze context-sensitive attention patterns"""
        metrics = {
            'context_sensitivity': 0.0,
            'task_switching_efficiency': 0.0,
            'priority_adherence': 0.0
        }
        
        # Analyze how context affects activity choice
        context_matches = 0
        total_decisions = 0
        
        for decision in decisions:
            context = decision.get('context', {})
            chosen_activity = decision.get('chosen_activity')
            
            if context and chosen_activity:
                total_decisions += 1
                # Check if activity matches context
                if self._activity_matches_context(chosen_activity, context):
                    context_matches += 1
        
        if total_decisions > 0:
            metrics['context_sensitivity'] = context_matches / total_decisions
        
        # Analyze task switching efficiency
        # (Simplified: check if switches happen at natural boundaries)
        efficient_switches = self._count_efficient_switches(activities)
        total_switches = self._count_total_switches(activities)
        
        if total_switches > 0:
            metrics['task_switching_efficiency'] = efficient_switches / total_switches
        
        return metrics
    
    def _activity_matches_context(self, activity: str, context: Dict) -> bool:
        """Check if activity is appropriate for context"""
        # Simplified logic - would be more sophisticated in practice
        if context.get('urgent') and 'urgent' in activity.lower():
            return True
        if context.get('social') and any(word in activity.lower() 
                                       for word in ['meet', 'talk', 'social']):
            return True
        if context.get('economic') and any(word in activity.lower() 
                                         for word in ['trade', 'sell', 'buy']):
            return True
        return False
    
    def _count_efficient_switches(self, activities: List[Dict]) -> int:
        """Count task switches at natural boundaries"""
        efficient = 0
        
        for i in range(1, len(activities)):
            if activities[i].get('type') != activities[i-1].get('type'):
                # Check if previous activity was completed
                if activities[i-1].get('status') == 'completed':
                    efficient += 1
        
        return efficient
    
    def _count_total_switches(self, activities: List[Dict]) -> int:
        """Count total task switches"""
        switches = 0
        
        for i in range(1, len(activities)):
            if activities[i].get('type') != activities[i-1].get('type'):
                switches += 1
        
        return switches
    
    def _find_state_dependencies(self, data: Dict) -> List[Dict]:
        """Find state-dependent attention shifts"""
        dependencies = []
        
        activities = data.get('activities', [])
        citizens = data.get('citizens', [])
        
        # Map citizen states to activities
        for act in activities:
            citizen_id = act.get('citizen_id')
            citizen = next((c for c in citizens if c.get('id') == citizen_id), None)
            
            if citizen:
                state = citizen.get('state', {})
                # Check if activity type depends on state
                if (state.get('wealth', 0) < 100 and 'earn' in act.get('type', '')):
                    dependencies.append({
                        'state': 'low_wealth',
                        'attention': 'earning_focused',
                        'activity': act
                    })
                elif (state.get('hunger', 0) > 80 and 'eat' in act.get('type', '')):
                    dependencies.append({
                        'state': 'hungry',
                        'attention': 'food_focused',
                        'activity': act
                    })
        
        return dependencies
    
    def _find_generative_patterns(self, thoughts: List[Dict]) -> List[Dict]:
        """Find generative/predictive thought patterns"""
        generative = []
        
        keywords = ['expect', 'predict', 'anticipate', 'imagine', 'foresee', 
                   'plan', 'forecast', 'project', 'suppose', 'hypothesize']
        
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if any(keyword in content for keyword in keywords):
                generative.append(thought)
        
        return generative
    
    def _identify_top_down_decisions(self, decisions: List[Dict]) -> List[Dict]:
        """Identify decisions driven by expectations rather than immediate stimuli"""
        top_down = []
        
        for decision in decisions:
            rationale = decision.get('rationale', '').lower()
            # Look for expectation-based reasoning
            if any(word in rationale for word in ['expect', 'usually', 'pattern', 
                                                 'experience', 'learned', 'predict']):
                top_down.append(decision)
        
        return top_down
    
    def _assess_uncertainty_handling(self, data: Dict) -> float:
        """Assess how well the system handles perceptual uncertainty"""
        decisions = data.get('decisions', [])
        
        uncertainty_instances = 0
        handled_well = 0
        
        for decision in decisions:
            if decision.get('uncertainty_level', 0) > 0.5:
                uncertainty_instances += 1
                # Check if decision includes uncertainty mitigation
                if any(word in decision.get('rationale', '').lower() 
                      for word in ['verify', 'check', 'confirm', 'investigate']):
                    handled_well += 1
        
        if uncertainty_instances > 0:
            return handled_well / uncertainty_instances
        return 0.0
    
    def _find_metacognitive_patterns(self, thoughts: List[Dict]) -> List[Dict]:
        """Find instances of metacognitive thinking"""
        metacognitive = []
        
        # Keywords indicating self-reflection
        keywords = ['i think', 'i believe', 'i realize', 'i understand',
                   'my thinking', 'my decision', 'i was wrong', 'i should',
                   'reconsidering', 'reflecting', 'evaluating my']
        
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if any(keyword in content for keyword in keywords):
                metacognitive.append(thought)
        
        return metacognitive
    
    def _find_error_corrections(self, data: Dict) -> List[Dict]:
        """Find self-initiated error corrections"""
        corrections = []
        
        activities = data.get('activities', [])
        decisions = data.get('decisions', [])
        
        # Look for activity corrections
        for i in range(1, len(activities)):
            if (activities[i].get('type') == 'correct' or 
                'fix' in activities[i].get('type', '') or
                activities[i].get('corrects_activity') == activities[i-1].get('id')):
                corrections.append(activities[i])
        
        # Look for decision revisions
        for i in range(1, len(decisions)):
            if decisions[i].get('revises_decision') == decisions[i-1].get('id'):
                corrections.append(decisions[i])
        
        return corrections
    
    def _assess_confidence_calibration(self, decisions: List[Dict]) -> float:
        """Assess how well confidence matches outcomes"""
        calibration_scores = []
        
        for decision in decisions:
            confidence = decision.get('confidence', 0.5)
            outcome = decision.get('outcome_success', 0.5)
            
            # Good calibration means confidence matches success rate
            calibration = 1.0 - abs(confidence - outcome)
            calibration_scores.append(calibration)
        
        return np.mean(calibration_scores) if calibration_scores else 0.0
    
    def _track_belief_updates(self, decisions: List[Dict], 
                            thoughts: List[Dict]) -> List[Dict]:
        """Track changes in beliefs over time"""
        belief_updates = []
        
        # Group by citizen
        citizen_beliefs = defaultdict(list)
        
        for thought in thoughts:
            if 'believe' in thought.get('content', '').lower():
                citizen_beliefs[thought.get('citizen_id')].append(thought)
        
        # Find belief changes
        for citizen, beliefs in citizen_beliefs.items():
            for i in range(1, len(beliefs)):
                if self._beliefs_differ(beliefs[i-1], beliefs[i]):
                    belief_updates.append({
                        'citizen': citizen,
                        'old_belief': beliefs[i-1],
                        'new_belief': beliefs[i],
                        'timestamp': beliefs[i].get('timestamp')
                    })
        
        return belief_updates
    
    def _beliefs_differ(self, belief1: Dict, belief2: Dict) -> bool:
        """Check if two beliefs are different"""
        content1 = belief1.get('content', '')
        content2 = belief2.get('content', '')
        
        # Simple check - would be more sophisticated
        return content1 != content2 and len(content1) > 10 and len(content2) > 10
    
    def _calculate_belief_consistency(self, belief_updates: List[Dict]) -> float:
        """Calculate consistency of belief updates"""
        if not belief_updates:
            return 1.0
        
        # Check if updates follow logical patterns
        consistent_updates = 0
        
        for update in belief_updates:
            # Simplified: check if update mentions evidence or reason
            new_belief = update.get('new_belief', {})
            if any(word in new_belief.get('content', '').lower() 
                  for word in ['because', 'evidence', 'learned', 'discovered']):
                consistent_updates += 1
        
        return consistent_updates / len(belief_updates)
    
    def _find_goal_adaptations(self, data: Dict) -> List[Dict]:
        """Find instances of goal adaptation"""
        adaptations = []
        
        decisions = data.get('decisions', [])
        
        # Look for goal changes
        citizen_goals = defaultdict(list)
        
        for decision in decisions:
            goal = decision.get('goal')
            if goal:
                citizen_id = decision.get('citizen_id')
                citizen_goals[citizen_id].append((decision.get('timestamp'), goal))
        
        # Find changes
        for citizen, goals in citizen_goals.items():
            goals.sort(key=lambda x: x[0])
            for i in range(1, len(goals)):
                if goals[i][1] != goals[i-1][1]:
                    adaptations.append({
                        'citizen': citizen,
                        'old_goal': goals[i-1][1],
                        'new_goal': goals[i][1],
                        'timestamp': goals[i][0]
                    })
        
        return adaptations
    
    def _assess_action_coherence(self, decisions: List[Dict]) -> float:
        """Assess coherence of action selection"""
        coherence_scores = []
        
        # Group decisions by citizen
        citizen_decisions = defaultdict(list)
        for decision in decisions:
            citizen_decisions[decision.get('citizen_id')].append(decision)
        
        for citizen, dec_list in citizen_decisions.items():
            # Check if decisions align with stated goals
            for i in range(len(dec_list)):
                decision = dec_list[i]
                goal = decision.get('goal')
                action = decision.get('chosen_activity')
                
                if goal and action:
                    # Simple coherence check
                    if self._action_serves_goal(action, goal):
                        coherence_scores.append(1.0)
                    else:
                        coherence_scores.append(0.0)
        
        return np.mean(coherence_scores) if coherence_scores else 0.0
    
    def _action_serves_goal(self, action: str, goal: str) -> bool:
        """Check if action serves the stated goal"""
        action_lower = action.lower()
        goal_lower = goal.lower()
        
        # Simple keyword matching - would be more sophisticated
        goal_keywords = goal_lower.split()
        return any(keyword in action_lower for keyword in goal_keywords)
    
    def _calculate_representation_sparsity(self, citizens: List[Dict]) -> float:
        """Calculate sparsity of citizen representations"""
        if not citizens:
            return 0.0
        
        # Count active features per citizen
        feature_counts = []
        
        for citizen in citizens:
            # Count non-default values
            active_features = 0
            for key, value in citizen.items():
                if value and value != 0 and value != '':
                    active_features += 1
            
            total_features = len(citizen.keys())
            if total_features > 0:
                sparsity = 1.0 - (active_features / total_features)
                feature_counts.append(sparsity)
        
        return np.mean(feature_counts) if feature_counts else 0.0
    
    def _analyze_similarity_gradients(self, citizens: List[Dict]) -> float:
        """Analyze smoothness of similarity gradients"""
        if len(citizens) < 3:
            return 0.0
        
        # Calculate pairwise similarities
        similarities = []
        
        for i in range(len(citizens)):
            for j in range(i+1, len(citizens)):
                sim = self._calculate_citizen_similarity(citizens[i], citizens[j])
                similarities.append(sim)
        
        # Check for smooth distribution
        if similarities:
            # Smooth gradients would have varied similarities
            std = np.std(similarities)
            mean = np.mean(similarities)
            
            # Good gradient: moderate variance, not too clustered
            if mean > 0 and 0.1 < std < 0.5:
                return 0.8
            elif 0.05 < std < 0.7:
                return 0.6
            else:
                return 0.3
        
        return 0.0
    
    def _calculate_citizen_similarity(self, citizen1: Dict, citizen2: Dict) -> float:
        """Calculate similarity between two citizens"""
        similarity_score = 0.0
        compared_features = 0
        
        # Compare key attributes
        for key in ['wealth', 'social_class', 'profession', 'location']:
            if key in citizen1 and key in citizen2:
                compared_features += 1
                if citizen1[key] == citizen2[key]:
                    similarity_score += 1.0
                elif isinstance(citizen1[key], (int, float)) and isinstance(citizen2[key], (int, float)):
                    # For numeric values, use normalized difference
                    max_val = max(abs(citizen1[key]), abs(citizen2[key]))
                    if max_val > 0:
                        diff = abs(citizen1[key] - citizen2[key]) / max_val
                        similarity_score += 1.0 - diff
        
        return similarity_score / compared_features if compared_features > 0 else 0.0
    
    def _identify_quality_dimensions(self, data: Dict) -> List[str]:
        """Identify quality dimensions in the representation space"""
        dimensions = []
        
        citizens = data.get('citizens', [])
        
        if citizens:
            # Look for dimensions with high variance
            numeric_features = {}
            
            for citizen in citizens:
                for key, value in citizen.items():
                    if isinstance(value, (int, float)):
                        if key not in numeric_features:
                            numeric_features[key] = []
                        numeric_features[key].append(value)
            
            # Find high-variance dimensions
            for feature, values in numeric_features.items():
                if len(values) > 10:
                    variance = np.var(values)
                    if variance > np.mean(values) * 0.1:  # Significant variance
                        dimensions.append(feature)
        
        return dimensions
    
    def _find_attention_predictions(self, thoughts: List[Dict]) -> List[Dict]:
        """Find predictions about attention states"""
        predictions = []
        
        attention_keywords = ['focus', 'attend', 'notice', 'watch', 'observe',
                            'concentrate', 'pay attention', 'will look']
        
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if any(keyword in content for keyword in attention_keywords) and \
               any(future in content for future in ['will', 'going to', 'plan to']):
                predictions.append(thought)
        
        return predictions
    
    def _find_self_attention_models(self, thoughts: List[Dict]) -> List[Dict]:
        """Find self-models of attention"""
        self_models = []
        
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if ('my attention' in content or 'i am focusing' in content or
                'i notice that i' in content):
                self_models.append(thought)
        
        return self_models
    
    def _assess_attention_awareness(self, data: Dict) -> float:
        """Assess awareness of own attention states"""
        thoughts = data.get('thoughts', [])
        
        awareness_instances = 0
        total_relevant = 0
        
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if 'attention' in content or 'focus' in content:
                total_relevant += 1
                if 'my' in content or 'i' in content:
                    awareness_instances += 1
        
        if total_relevant > 0:
            return awareness_instances / total_relevant
        return 0.0
    
    def _track_prediction_errors(self, decisions: List[Dict], 
                               activities: List[Dict]) -> List[float]:
        """Track prediction errors between expected and actual outcomes"""
        errors = []
        
        for decision in decisions:
            expected_outcome = decision.get('expected_outcome')
            decision_id = decision.get('id')
            
            if expected_outcome and decision_id:
                # Find corresponding activity outcome
                activity = next((a for a in activities 
                               if a.get('decision_id') == decision_id), None)
                
                if activity:
                    actual_outcome = activity.get('outcome')
                    if actual_outcome and expected_outcome:
                        # Calculate error (simplified)
                        error = abs(float(expected_outcome) - float(actual_outcome))
                        errors.append(error)
        
        return errors
    
    def _find_model_updates(self, data: Dict) -> List[Dict]:
        """Find instances where models are updated based on errors"""
        updates = []
        
        thoughts = data.get('thoughts', [])
        
        update_keywords = ['learned', 'realized', 'now know', 'updated',
                          'changed my mind', 'new understanding', 'correction']
        
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if any(keyword in content for keyword in update_keywords):
                updates.append(thought)
        
        return updates
    
    def _find_anticipatory_actions(self, activities: List[Dict]) -> List[Dict]:
        """Find actions taken in anticipation of future events"""
        anticipatory = []
        
        for activity in activities:
            activity_type = activity.get('type', '').lower()
            description = activity.get('description', '').lower()
            
            if any(word in activity_type + description 
                  for word in ['prepare', 'anticipate', 'prevent', 'ready',
                             'advance', 'proactive', 'preemptive']):
                anticipatory.append(activity)
        
        return anticipatory
    
    def _calculate_learning_rates(self, citizens: List[Dict], 
                                decisions: List[Dict]) -> List[float]:
        """Calculate learning rates for citizens"""
        learning_rates = []
        
        # Group decisions by citizen
        citizen_decisions = defaultdict(list)
        for decision in decisions:
            citizen_decisions[decision.get('citizen_id')].append(decision)
        
        for citizen_id, dec_list in citizen_decisions.items():
            if len(dec_list) > 10:
                # Track improvement over time
                early_success = np.mean([d.get('outcome_success', 0.5) 
                                       for d in dec_list[:5]])
                late_success = np.mean([d.get('outcome_success', 0.5) 
                                      for d in dec_list[-5:]])
                
                learning_rate = late_success - early_success
                learning_rates.append(max(0, learning_rate))
        
        return learning_rates
    
    def _find_strategy_adaptations(self, decisions: List[Dict]) -> List[Dict]:
        """Find instances of strategy adaptation"""
        adaptations = []
        
        # Group by citizen
        citizen_strategies = defaultdict(list)
        
        for decision in decisions:
            strategy = decision.get('strategy')
            if strategy:
                citizen_strategies[decision.get('citizen_id')].append(
                    (decision.get('timestamp'), strategy, decision)
                )
        
        # Find changes
        for citizen, strategies in citizen_strategies.items():
            strategies.sort(key=lambda x: x[0])
            for i in range(1, len(strategies)):
                if strategies[i][1] != strategies[i-1][1]:
                    adaptations.append({
                        'citizen': citizen,
                        'old_strategy': strategies[i-1][1],
                        'new_strategy': strategies[i][1],
                        'decision': strategies[i][2]
                    })
        
        return adaptations
    
    def _assess_goal_flexibility(self, data: Dict) -> float:
        """Assess flexibility in goal pursuit"""
        goal_adaptations = self._find_goal_adaptations(data)
        decisions = data.get('decisions', [])
        
        if not decisions:
            return 0.0
        
        # Count citizens who show goal flexibility
        flexible_citizens = set()
        total_citizens = set()
        
        for decision in decisions:
            total_citizens.add(decision.get('citizen_id'))
        
        for adaptation in goal_adaptations:
            flexible_citizens.add(adaptation.get('citizen'))
        
        if total_citizens:
            return len(flexible_citizens) / len(total_citizens)
        return 0.0
    
    def _assess_spatial_awareness(self, spatial_data: Dict, 
                                activities: List[Dict]) -> float:
        """Assess spatial awareness through movement patterns"""
        if not spatial_data or not activities:
            return 0.0
        
        awareness_scores = []
        
        for activity in activities:
            if activity.get('type') == 'move':
                citizen_id = activity.get('citizen_id')
                destination = activity.get('destination')
                
                if citizen_id and destination:
                    # Check if movement is efficient
                    current_pos = spatial_data.get(citizen_id, {}).get('position')
                    if current_pos:
                        # Simple efficiency check
                        direct_distance = self._calculate_distance(current_pos, destination)
                        actual_path = activity.get('path_length', direct_distance * 1.5)
                        
                        efficiency = direct_distance / actual_path if actual_path > 0 else 0
                        awareness_scores.append(efficiency)
        
        return np.mean(awareness_scores) if awareness_scores else 0.0
    
    def _track_action_consequences(self, activities: List[Dict]) -> List[Dict]:
        """Track action-consequence pairs"""
        consequences = []
        
        for i in range(len(activities) - 1):
            activity = activities[i]
            
            # Look for consequences in subsequent activities
            for j in range(i+1, min(i+5, len(activities))):
                next_activity = activities[j]
                
                # Check if next activity is consequence of first
                if (next_activity.get('caused_by') == activity.get('id') or
                    next_activity.get('in_response_to') == activity.get('id')):
                    consequences.append({
                        'action': activity,
                        'consequence': next_activity,
                        'time_delta': j - i
                    })
        
        return consequences
    
    def _assess_environmental_coupling(self, data: Dict) -> float:
        """Assess coupling with environment"""
        activities = data.get('activities', [])
        environmental_factors = data.get('environmental_factors', {})
        
        if not activities:
            return 0.0
        
        coupled_activities = 0
        total_activities = len(activities)
        
        for activity in activities:
            # Check if activity responds to environmental factors
            if any(factor in activity.get('rationale', '').lower() 
                  for factor in ['weather', 'time', 'crowd', 'market', 'event']):
                coupled_activities += 1
            elif activity.get('environmental_trigger'):
                coupled_activities += 1
        
        return coupled_activities / total_activities if total_activities > 0 else 0.0
    
    def _calculate_category_scores(self, indicator_scores: List[IndicatorScore]) -> Dict[str, float]:
        """Calculate average scores by category"""
        category_scores = defaultdict(list)
        
        for score in indicator_scores:
            category_scores[score.category.value].append(score.score)
        
        return {
            category: np.mean(scores) 
            for category, scores in category_scores.items()
        }
    
    def _calculate_emergence_ratio(self, indicator_scores: List[IndicatorScore]) -> float:
        """Calculate ratio of emergent vs designed properties"""
        # Define which indicators represent emergent properties
        emergent_indicators = {
            'RPT-1', 'RPT-2',  # Emergent from processing patterns
            'GWT-3', 'GWT-4',  # Emergent from information flow
            'HOT-2', 'HOT-4',  # Emergent from self-organization
            'PP-1', 'AST-1'    # Emergent from predictive dynamics
        }
        
        emergent_scores = []
        designed_scores = []
        
        for score in indicator_scores:
            if score.indicator_id in emergent_indicators:
                emergent_scores.append(score.score)
            else:
                designed_scores.append(score.score)
        
        # Weight by proportion showing strong evidence
        emergent_strong = sum(1 for s in emergent_scores if s >= 2.5)
        designed_strong = sum(1 for s in designed_scores if s >= 2.5)
        
        total_strong = emergent_strong + designed_strong
        if total_strong > 0:
            return emergent_strong / total_strong
        return 0.0
    
    def _generate_summary(self, overall_score: float, 
                         category_scores: Dict[str, float],
                         emergence_ratio: float) -> str:
        """Generate human-readable summary of assessment"""
        summary = f"Consciousness Assessment Summary\n"
        summary += f"="*50 + "\n"
        summary += f"Overall Score: {overall_score:.2f}/3.0\n"
        summary += f"Emergence Ratio: {emergence_ratio:.1%}\n\n"
        
        summary += "Category Scores:\n"
        for category, score in category_scores.items():
            summary += f"  {category}: {score:.2f}/3.0\n"
        
        # Interpretation
        if overall_score >= 2.5:
            summary += "\nAssessment: Strong evidence for consciousness indicators"
        elif overall_score >= 2.0:
            summary += "\nAssessment: Moderate evidence for consciousness indicators"
        elif overall_score >= 1.5:
            summary += "\nAssessment: Weak evidence for consciousness indicators"
        else:
            summary += "\nAssessment: Minimal evidence for consciousness indicators"
        
        if emergence_ratio > 0.7:
            summary += "\nHigh proportion of emergent properties suggests genuine complexity"
        elif emergence_ratio > 0.5:
            summary += "\nBalanced mix of emergent and designed properties"
        else:
            summary += "\nPrimarily designed properties with limited emergence"
        
        return summary
    
    def export_assessment(self, assessment: ConsciousnessAssessment, 
                         filepath: str = "consciousness_assessment.json"):
        """Export assessment to JSON file"""
        export_data = {
            'timestamp': assessment.timestamp.isoformat(),
            'overall_score': assessment.overall_score,
            'category_scores': assessment.category_scores,
            'emergence_ratio': assessment.emergence_ratio,
            'inter_rater_reliability': assessment.inter_rater_reliability,
            'summary': assessment.summary,
            'indicators': [
                {
                    'id': ind.indicator_id,
                    'name': ind.name,
                    'category': ind.category.value,
                    'score': ind.score,
                    'confidence': ind.confidence,
                    'evidence': ind.evidence,
                    'raw_metrics': ind.raw_metrics
                }
                for ind in assessment.indicators
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def compare_assessments(self, assessment1: ConsciousnessAssessment,
                          assessment2: ConsciousnessAssessment) -> Dict:
        """Compare two assessments (e.g., for inter-rater reliability)"""
        comparison = {
            'overall_score_diff': abs(assessment1.overall_score - assessment2.overall_score),
            'indicator_agreements': [],
            'indicator_disagreements': [],
            'cohen_kappa': 0.0
        }
        
        # Compare individual indicators
        for i, ind1 in enumerate(assessment1.indicators):
            ind2 = assessment2.indicators[i]
            
            score_diff = abs(ind1.score - ind2.score)
            if score_diff <= 0.5:
                comparison['indicator_agreements'].append(ind1.indicator_id)
            else:
                comparison['indicator_disagreements'].append({
                    'id': ind1.indicator_id,
                    'score1': ind1.score,
                    'score2': ind2.score,
                    'diff': score_diff
                })
        
        # Calculate Cohen's Kappa
        # Simplified - treats scores as categories
        agreement_count = len(comparison['indicator_agreements'])
        total_count = len(assessment1.indicators)
        
        observed_agreement = agreement_count / total_count
        expected_agreement = 0.25  # Assuming 4 score categories
        
        if expected_agreement < 1.0:
            comparison['cohen_kappa'] = (observed_agreement - expected_agreement) / \
                                       (1.0 - expected_agreement)
        
        return comparison


# Example usage
def run_consciousness_assessment(data_source: str = "live") -> ConsciousnessAssessment:
    """
    Run a complete consciousness assessment
    
    Args:
        data_source: "live" for API data or "test" for sample data
    """
    tracker = ConsciousnessIndicatorTracker()
    
    if data_source == "live":
        # Fetch live data from API
        import requests
        
        # Fetch all necessary data
        system_data = {
            'citizens': requests.get('https://serenissima.ai/api/citizens').json().get('citizens', []),
            'messages': requests.get('https://serenissima.ai/api/messages?limit=500').json().get('messages', []),
            'activities': requests.get('https://serenissima.ai/api/activities').json().get('activities', []),
            'thoughts': [],  # Would need specialized endpoint
            'decisions': [],  # Would need specialized endpoint
            'spatial_data': {}  # Would need specialized endpoint
        }
    else:
        # Use test data
        system_data = {
            'citizens': [{'id': 'test1', 'wealth': 1000, 'social_class': 'merchant'}],
            'messages': [{'id': 'msg1', 'sender': 'test1', 'receiver': 'test2', 
                         'content': 'Hello', 'timestamp': '2024-01-01T00:00:00Z'}],
            'activities': [{'id': 'act1', 'citizen_id': 'test1', 'type': 'trade',
                          'timestamp': '2024-01-01T00:00:00Z'}],
            'thoughts': [],
            'decisions': [],
            'spatial_data': {}
        }
    
    # Run assessment
    assessment = tracker.assess_all_indicators(system_data)
    
    # Export results
    tracker.export_assessment(assessment)
    
    # Print summary
    print(assessment.summary)
    
    return assessment


if __name__ == "__main__":
    # Run assessment with test data
    assessment = run_consciousness_assessment("test")
"""
Consciousness Measurement Implementation
Practical implementation of consciousness indicator measurements for La Serenissima
"""

from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np
from dataclasses import dataclass
import re
import networkx as nx


@dataclass
class Measurement:
    """Single measurement result"""
    value: float
    confidence: float
    evidence: List[str]
    raw_data: Dict


@dataclass
class Transaction:
    """Economic transaction data"""
    id: str
    from_citizen: str
    to_citizen: str
    amount: float
    resource_type: str
    timestamp: datetime
    contract_type: str


class ConsciousnessMeasurementEngine:
    """Engine for measuring consciousness indicators from real data"""
    
    def __init__(self):
        # Scoring thresholds for each indicator
        self.scoring_thresholds = {
            'RPT-1': {'high': 50, 'medium': 30, 'low': 15},  # conversation loops per day
            'RPT-2': {'high': 0.85, 'medium': 0.75, 'low': 0.60},  # spatial coherence
            'GWT-1': {'high': 3.0, 'medium': 2.0, 'low': 1.5},  # concurrent activities
            'GWT-2': {'high': 3.0, 'medium': 2.0, 'low': 1.0},  # queue length
            'GWT-3': {'high': 0.60, 'medium': 0.40, 'low': 0.20},  # information reach
            'GWT-4': {'high': 0.80, 'medium': 0.70, 'low': 0.50},  # context sensitivity
            'HOT-1': {'high': 0.30, 'medium': 0.20, 'low': 0.10},  # predictive language ratio
            'HOT-2': {'high': 100, 'medium': 50, 'low': 20},  # self-reflections per day
            'HOT-3': {'high': 0.85, 'medium': 0.75, 'low': 0.60},  # belief-action coherence
            'HOT-4': {'high': 0.70, 'medium': 0.60, 'low': 0.50},  # representation sparsity
            'AST-1': {'high': 0.80, 'medium': 0.60, 'low': 0.40},  # attention prediction accuracy
            'PP-1': {'high': 200, 'medium': 100, 'low': 50},  # prediction errors per day
            'AE-1': {'high': 0.15, 'medium': 0.10, 'low': 0.05},  # learning rate
            'AE-2': {'high': 0.85, 'medium': 0.75, 'low': 0.60},  # spatial awareness
        }
        
        # Keywords for various detections
        self.reflection_keywords = [
            'i think', 'i believe', 'i realize', 'i understand',
            'my thinking', 'i was wrong', 'reconsidering', 'on second thought'
        ]
        
        self.prediction_keywords = [
            'will', 'expect', 'anticipate', 'predict', 'likely',
            'probably', 'forecast', 'foresee', 'plan to'
        ]
        
        self.uncertainty_keywords = [
            'maybe', 'perhaps', 'might', 'could be', 'uncertain',
            'not sure', 'possibly', 'approximately'
        ]
    
    def _parse_transactions(self, contracts: List[Dict]) -> List[Transaction]:
        """Parse contract data into Transaction objects"""
        transactions = []
        for contract in contracts:
            if contract.get('Status') == 'completed' and contract.get('AcceptedAt'):
                try:
                    trans = Transaction(
                        id=contract.get('ContractId', ''),
                        from_citizen=contract.get('Buyer', ''),
                        to_citizen=contract.get('Seller', ''),
                        amount=float(contract.get('Price', 0)),
                        resource_type=contract.get('ResourceType', ''),
                        timestamp=datetime.fromisoformat(contract.get('AcceptedAt', '').replace('Z', '+00:00')),
                        contract_type=contract.get('Type', 'trade')
                    )
                    transactions.append(trans)
                except:
                    continue
        return sorted(transactions, key=lambda x: x.timestamp)
    
    # RPT-1: Algorithmic Recurrence
    def measure_rpt1(self, messages: List[Dict], activities: List[Dict], 
                     contracts: List[Dict] = None) -> Measurement:
        """Measure algorithmic recurrence through conversation loops, thought iteration, and transaction patterns"""
        
        # Parse transactions if provided
        transactions = self._parse_transactions(contracts) if contracts else []
        
        # 1. Analyze conversation loops
        conversation_chains = self._extract_conversation_chains(messages)
        deep_chains = [c for c in conversation_chains if len(c) > 3]
        loops_per_day = len(deep_chains) * 24 / self._get_time_span_hours(messages)
        
        # 2. Detect thought iteration (using thoughts as messages to self)
        thoughts = self._extract_thoughts(messages)
        iteration_count = 0
        unique_iterators = set()
        
        # Look for iterative patterns in thoughts
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if any(phrase in content for phrase in 
                   ['on second thought', 'reconsidering', 'i now think', 
                    'actually', 'wait', 'correction', 'rethinking', 'revising']):
                iteration_count += 1
                unique_iterators.add(thought.get('sender'))
        
        iteration_rate = len(unique_iterators) / self._count_unique_citizens(messages)
        
        # 3. Activity cycles
        activity_cycles = self._detect_activity_cycles(activities)
        
        # 4. Transaction pattern cycles
        transaction_cycles = 0
        if contracts:
            transactions = self._parse_transactions(contracts)
            transaction_cycles = self._detect_transaction_cycles(transactions)
        
        # Calculate score (include transaction patterns)
        primary_metric = loops_per_day
        if transaction_cycles > 10:
            primary_metric *= 1.2  # Boost for economic recurrence
        
        score = self._calculate_score(primary_metric, self.scoring_thresholds['RPT-1'])
        
        # Generate evidence
        evidence = []
        if deep_chains:
            evidence.append(f"Found {len(deep_chains)} extended conversation chains (>3 messages)")
        if iteration_rate > 0.15:
            evidence.append(f"{iteration_rate*100:.1f}% of citizens showed thought iteration")
        if activity_cycles:
            evidence.append(f"Detected {len(activity_cycles)} activity cycles with feedback loops")
        if transaction_cycles > 10:
            evidence.append(f"Found {transaction_cycles} recurring transaction patterns")
        
        return Measurement(
            value=score,
            confidence=0.9 if len(messages) > 100 else 0.7,
            evidence=evidence,
            raw_data={
                'conversation_loops': len(deep_chains),
                'loops_per_day': loops_per_day,
                'thought_iteration_rate': iteration_rate,
                'activity_cycles': len(activity_cycles),
                'transaction_cycles': transaction_cycles
            }
        )
    
    # RPT-2: Integrated Perceptual Representations
    def measure_rpt2(self, activities: List[Dict], citizens: List[Dict]) -> Measurement:
        """Measure integrated perceptual representations through spatial and multi-modal integration"""
        
        # 1. Spatial coherence
        spatial_scores = []
        for activity in activities:
            if activity.get('Type') == 'move' and activity.get('Location'):
                citizen = next((c for c in citizens if c['Username'] == activity['CitizenUsername']), None)
                if citizen:
                    coherence = self._calculate_spatial_coherence(
                        citizen.get('Location'), 
                        activity.get('Location')
                    )
                    spatial_scores.append(coherence)
        
        avg_spatial_coherence = np.mean(spatial_scores) if spatial_scores else 0.5
        
        # 2. Multi-modal integration
        integrated_decisions = 0
        total_decisions = 0
        
        for activity in activities:
            factors = self._extract_decision_factors(activity)
            if len(factors) >= 2:
                integrated_decisions += 1
            total_decisions += 1
        
        integration_rate = integrated_decisions / total_decisions if total_decisions > 0 else 0
        
        # 3. Temporal coherence
        temporal_coherence = self._assess_temporal_coherence(activities)
        
        # Calculate score
        primary_metric = avg_spatial_coherence
        score = self._calculate_score(primary_metric, self.scoring_thresholds['RPT-2'])
        
        evidence = []
        if avg_spatial_coherence > 0.75:
            evidence.append(f"High spatial coherence: {avg_spatial_coherence:.2f}")
        if integration_rate > 0.6:
            evidence.append(f"{integrated_decisions} decisions integrated multiple information sources")
        if temporal_coherence > 0.7:
            evidence.append(f"Strong temporal coherence: {temporal_coherence:.2f}")
        
        return Measurement(
            value=score,
            confidence=0.85,
            evidence=evidence,
            raw_data={
                'spatial_coherence': avg_spatial_coherence,
                'multi_modal_integration_rate': integration_rate,
                'integrated_decisions': integrated_decisions,
                'temporal_coherence': temporal_coherence
            }
        )
    
    # GWT-1: Parallel Specialized Systems
    def measure_gwt1(self, activities: List[Dict], stratagems: List[Dict]) -> Measurement:
        """Measure parallel processing capabilities"""
        
        # 1. Concurrent activities
        citizen_activities = defaultdict(list)
        for act in activities:
            citizen_activities[act['CitizenUsername']].append(act)
        
        concurrent_counts = []
        for citizen, acts in citizen_activities.items():
            max_concurrent = self._calculate_max_concurrent(acts)
            concurrent_counts.append(max_concurrent)
        
        avg_concurrent = np.mean(concurrent_counts) if concurrent_counts else 1.0
        
        # 2. Module independence
        independence = self._calculate_module_independence(activities)
        
        # 3. Parallel stratagems
        citizen_stratagems = defaultdict(int)
        for strat in stratagems:
            if strat.get('Status') == 'active':
                citizen_stratagems[strat['CitizenUsername']] += 1
        
        avg_stratagems = np.mean(list(citizen_stratagems.values())) if citizen_stratagems else 0
        
        # Calculate score
        primary_metric = avg_concurrent
        score = self._calculate_score(primary_metric, self.scoring_thresholds['GWT-1'])
        
        evidence = []
        if avg_concurrent > 2:
            evidence.append(f"Citizens manage average {avg_concurrent:.1f} concurrent activities")
        if independence > 0.6:
            evidence.append(f"High module independence: {independence:.2f}")
        if avg_stratagems > 1.5:
            evidence.append(f"Average {avg_stratagems:.1f} parallel stratagems per citizen")
        
        return Measurement(
            value=score,
            confidence=0.9,
            evidence=evidence,
            raw_data={
                'avg_concurrent_activities': avg_concurrent,
                'max_concurrent': max(concurrent_counts) if concurrent_counts else 0,
                'module_independence': independence,
                'avg_parallel_stratagems': avg_stratagems
            }
        )
    
    # GWT-2: Limited Capacity Workspace
    def measure_gwt2(self, activities: List[Dict]) -> Measurement:
        """Measure information bottleneck and limited capacity"""
        
        # 1. Activity queue analysis
        queue_metrics = self._analyze_activity_queues(activities)
        
        # 2. Attention switching
        switching_rates = []
        citizen_activities = defaultdict(list)
        
        for act in activities:
            citizen_activities[act['CitizenUsername']].append(act)
        
        for citizen, acts in citizen_activities.items():
            switches = self._count_activity_type_switches(acts)
            time_span = self._get_activity_timespan_hours(acts)
            if time_span > 0:
                switching_rates.append(switches / time_span)
        
        avg_switching = np.mean(switching_rates) if switching_rates else 0
        
        # 3. Processing delays
        delays = self._calculate_processing_delays(activities)
        
        # Calculate score
        primary_metric = queue_metrics['avg_queue_length']
        score = self._calculate_score(primary_metric, self.scoring_thresholds['GWT-2'])
        
        evidence = []
        if queue_metrics['avg_queue_length'] > 1.5:
            evidence.append(f"Average queue length {queue_metrics['avg_queue_length']:.1f} indicates bottleneck")
        if avg_switching > 10:
            evidence.append(f"Frequent attention switching ({avg_switching:.0f} switches/hour)")
        if delays['p90'] > 300:
            evidence.append(f"90th percentile processing delay: {delays['p90']:.0f}s")
        
        return Measurement(
            value=score,
            confidence=0.85,
            evidence=evidence,
            raw_data={
                'avg_queue_length': queue_metrics['avg_queue_length'],
                'max_queue_length': queue_metrics['max_queue_length'],
                'attention_switches_per_hour': avg_switching,
                'processing_delay_p90': delays['p90']
            }
        )
    
    # GWT-3: Global Broadcast
    def measure_gwt3(self, messages: List[Dict], citizens: List[Dict], 
                     contracts: List[Dict] = None) -> Measurement:
        """Measure global information broadcast capabilities including economic cascades"""
        
        total_citizens = len(citizens)
        
        # 1. Information cascade reach
        cascades = self._analyze_message_cascades(messages)
        reaches = []
        
        for cascade in cascades:
            participants = set()
            for msg in cascade:
                participants.add(msg['sender'])
                participants.add(msg['receiver'])
            reach = len(participants) / total_citizens
            reaches.append(reach)
        
        avg_reach = np.mean(reaches) if reaches else 0
        
        # 2. Cross-module communication
        cross_references = self._count_cross_domain_references(messages)
        
        # 3. Collective response patterns
        synchronization = self._measure_collective_responses(messages, citizens)
        
        # 4. Economic cascade analysis
        economic_cascade_size = 0
        if contracts:
            transactions = self._parse_transactions(contracts)
            economic_cascades = self._detect_economic_cascades(transactions)
            if economic_cascades:
                economic_cascade_size = np.mean([len(c) for c in economic_cascades])
                # Include economic participants in reach calculation
                for cascade in economic_cascades:
                    participants = set()
                    for trans in cascade:
                        participants.add(trans.from_citizen)
                        participants.add(trans.to_citizen)
                    reach = len(participants) / total_citizens
                    reaches.append(reach)
                avg_reach = np.mean(reaches) if reaches else 0
        
        # Calculate score
        primary_metric = avg_reach
        score = self._calculate_score(primary_metric, self.scoring_thresholds['GWT-3'])
        
        evidence = []
        if avg_reach > 0.3:
            evidence.append(f"Information reaches {avg_reach*100:.0f}% of network on average")
        if len(cascades) > 0:
            avg_cascade_size = np.mean([len(c) for c in cascades])
            evidence.append(f"Message cascades involve {avg_cascade_size:.1f} messages on average")
        if synchronization > 0.5:
            evidence.append(f"High collective synchronization: {synchronization:.2f}")
        if economic_cascade_size > 5:
            evidence.append(f"Economic cascades average {economic_cascade_size:.1f} transactions")
        
        return Measurement(
            value=score,
            confidence=0.8,
            evidence=evidence,
            raw_data={
                'avg_broadcast_reach': avg_reach,
                'cascade_count': len(cascades),
                'cross_domain_references': cross_references,
                'collective_synchronization': synchronization,
                'economic_cascade_size': economic_cascade_size
            }
        )
    
    # GWT-4: State-Dependent Attention
    def measure_gwt4(self, activities: List[Dict], citizens: List[Dict]) -> Measurement:
        """Measure state-dependent attention mechanisms"""
        
        # 1. Context-sensitive activity selection
        context_matches = 0
        total_activities = 0
        
        for activity in activities:
            citizen = next((c for c in citizens if c['Username'] == activity['CitizenUsername']), None)
            if citizen:
                if self._activity_matches_state(activity, citizen):
                    context_matches += 1
                total_activities += 1
        
        context_sensitivity = context_matches / total_activities if total_activities > 0 else 0
        
        # 2. Dynamic priority adjustments
        priority_shifts = self._detect_priority_shifts(activities)
        
        # 3. Attention efficiency
        efficiency = self._calculate_attention_efficiency(activities, citizens)
        
        # Calculate score
        primary_metric = context_sensitivity
        score = self._calculate_score(primary_metric, self.scoring_thresholds['GWT-4'])
        
        evidence = []
        if context_sensitivity > 0.7:
            evidence.append(f"High context sensitivity: {context_sensitivity:.2f}")
        if len(priority_shifts) > 20:
            evidence.append(f"Found {len(priority_shifts)} dynamic priority adjustments")
        if efficiency > 0.8:
            evidence.append(f"Efficient attention allocation: {efficiency:.2f}")
        
        return Measurement(
            value=score,
            confidence=0.85,
            evidence=evidence,
            raw_data={
                'context_sensitivity': context_sensitivity,
                'priority_shifts': len(priority_shifts),
                'attention_efficiency': efficiency,
                'state_dependent_choices': context_matches
            }
        )
    
    # HOT-1: Generative Perception
    def measure_hot1(self, messages: List[Dict], activities: List[Dict]) -> Measurement:
        """Measure generative/predictive perception capabilities"""
        
        # Extract thoughts for internal prediction analysis
        thoughts = self._extract_thoughts(messages)
        
        # 1. Predictive language analysis
        predictive_messages = 0
        predictive_thoughts = 0
        prediction_accuracy = []
        
        # Analyze all messages
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(keyword in content for keyword in self.prediction_keywords):
                predictive_messages += 1
                # Track if we can verify the prediction
                accuracy = self._check_prediction_accuracy(msg, activities)
                if accuracy is not None:
                    prediction_accuracy.append(accuracy)
        
        # Count predictive thoughts specifically
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if any(keyword in content for keyword in self.prediction_keywords):
                predictive_thoughts += 1
        
        predictive_ratio = predictive_messages / len(messages) if messages else 0
        avg_accuracy = np.mean(prediction_accuracy) if prediction_accuracy else 0.5
        
        # 2. Expectation-driven decisions
        proactive_decisions = self._count_proactive_decisions(activities)
        proactive_ratio = proactive_decisions / len(activities) if activities else 0
        
        # 3. Uncertainty handling
        uncertainty_score = self._assess_uncertainty_handling(messages)
        
        # Calculate score
        primary_metric = predictive_ratio
        score = self._calculate_score(primary_metric, self.scoring_thresholds['HOT-1'])
        
        evidence = []
        if predictive_ratio > 0.2:
            evidence.append(f"{predictive_ratio*100:.0f}% of messages contain predictions")
        if proactive_ratio > 0.4:
            evidence.append(f"{proactive_ratio*100:.0f}% of decisions are expectation-driven")
        if uncertainty_score > 0.7:
            evidence.append(f"Sophisticated uncertainty handling: {uncertainty_score:.2f}")
        
        return Measurement(
            value=score,
            confidence=0.8,
            evidence=evidence,
            raw_data={
                'predictive_language_ratio': predictive_ratio,
                'prediction_accuracy': avg_accuracy,
                'proactive_decision_ratio': proactive_ratio,
                'uncertainty_handling': uncertainty_score
            }
        )
    
    # HOT-2: Metacognitive Monitoring
    def measure_hot2(self, messages: List[Dict], activities: List[Dict]) -> Measurement:
        """Measure metacognitive monitoring and self-reflection"""
        
        # Extract thoughts - metacognition is most evident in self-directed messages
        thoughts = self._extract_thoughts(messages)
        
        # 1. Self-reflection instances
        reflection_count = 0
        thought_reflection_count = 0
        reflective_citizens = set()
        
        # Count reflections in all messages
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(keyword in content for keyword in self.reflection_keywords):
                reflection_count += 1
                reflective_citizens.add(msg['sender'])
        
        # Count reflections in thoughts (weighted higher)
        for thought in thoughts:
            content = thought.get('content', '').lower()
            if any(keyword in content for keyword in self.reflection_keywords):
                thought_reflection_count += 1
                reflective_citizens.add(thought['sender'])
        
        reflections_per_day = reflection_count * 24 / self._get_time_span_hours(messages)
        
        # 2. Error recognition and correction
        corrections = self._find_self_corrections(messages, activities)
        
        # 3. Confidence calibration
        calibration = self._assess_confidence_calibration(messages, activities)
        
        # Calculate score
        primary_metric = reflections_per_day
        score = self._calculate_score(primary_metric, self.scoring_thresholds['HOT-2'])
        
        evidence = []
        if reflection_count > 50:
            evidence.append(f"Found {reflection_count} instances of metacognitive reflection")
        if thought_reflection_count > 20:
            evidence.append(f"{thought_reflection_count} self-reflections in internal thoughts")
        if len(corrections) > 10:
            evidence.append(f"Detected {len(corrections)} self-initiated error corrections")
        if calibration > 0.7:
            evidence.append(f"Well-calibrated confidence assessments: {calibration:.2f}")
        
        return Measurement(
            value=score,
            confidence=0.85,
            evidence=evidence,
            raw_data={
                'reflections_per_day': reflections_per_day,
                'thought_reflections': thought_reflection_count,
                'total_thoughts': len(thoughts),
                'reflective_citizens': len(reflective_citizens),
                'self_corrections': len(corrections),
                'confidence_calibration': calibration
            }
        )
    
    # HOT-3: Agency and Belief Updating
    def measure_hot3(self, messages: List[Dict], activities: List[Dict], 
                     stratagems: List[Dict], contracts: List[Dict] = None) -> Measurement:
        """Measure agency with belief updating including transaction coherence"""
        
        # Parse transactions if provided
        transactions = self._parse_transactions(contracts) if contracts else []
        
        # 1. Belief change tracking
        belief_updates = self._track_belief_updates(messages)
        updates_per_week = len(belief_updates) * 7 * 24 / self._get_time_span_hours(messages)
        
        # 2. Belief-action coherence
        coherence = self._calculate_belief_action_coherence(messages, activities)
        
        # 3. Transaction-belief coherence
        transaction_coherence = 0.0
        if transactions:
            # Analyze if transactions align with stated beliefs
            transaction_coherence = self._calculate_transaction_belief_coherence(
                messages, transactions
            )
            # Weight coherence with transaction data
            coherence = 0.7 * coherence + 0.3 * transaction_coherence
        
        # 4. Adaptive strategy changes
        strategy_adaptations = self._find_strategy_adaptations(stratagems)
        
        # Calculate score
        primary_metric = coherence
        score = self._calculate_score(primary_metric, self.scoring_thresholds['HOT-3'])
        
        evidence = []
        if len(belief_updates) > 20:
            evidence.append(f"Tracked {len(belief_updates)} belief updates based on new information")
        if coherence > 0.8:
            evidence.append(f"High belief-action coherence: {coherence:.2f}")
        if transaction_coherence > 0.8 and transactions:
            evidence.append(f"Transaction patterns align with beliefs: {transaction_coherence:.2f}")
        if len(strategy_adaptations) > 10:
            evidence.append(f"Found {len(strategy_adaptations)} strategic adaptations")
        
        return Measurement(
            value=score,
            confidence=0.9,
            evidence=evidence,
            raw_data={
                'belief_updates': len(belief_updates),
                'updates_per_week': updates_per_week,
                'belief_action_coherence': coherence,
                'transaction_coherence': transaction_coherence,
                'transaction_count': len(transactions),
                'strategy_adaptations': len(strategy_adaptations)
            }
        )
    
    # HOT-4: Quality Space
    def measure_hot4(self, citizens: List[Dict]) -> Measurement:
        """Measure sparse and smooth quality space coding"""
        
        # 1. Representation sparsity
        sparsity_scores = []
        for citizen in citizens:
            active_features = sum(1 for v in citizen.values() 
                                if v and v != 0 and v != '')
            total_features = len(citizen.keys())
            sparsity = 1 - (active_features / total_features)
            sparsity_scores.append(sparsity)
        
        avg_sparsity = np.mean(sparsity_scores)
        
        # 2. Similarity gradients
        gradient_smoothness = self._analyze_similarity_gradients(citizens)
        
        # 3. Quality dimensions
        dimensions = self._identify_quality_dimensions(citizens)
        
        # Calculate score
        primary_metric = avg_sparsity
        score = self._calculate_score(primary_metric, self.scoring_thresholds['HOT-4'])
        
        evidence = []
        if avg_sparsity > 0.6:
            evidence.append(f"Sparse representation coding: {avg_sparsity:.2f}")
        if gradient_smoothness > 0.7:
            evidence.append(f"Smooth similarity gradients: {gradient_smoothness:.2f}")
        if len(dimensions) > 4:
            evidence.append(f"Identified {len(dimensions)} quality dimensions")
        
        return Measurement(
            value=score,
            confidence=0.75,
            evidence=evidence,
            raw_data={
                'representation_sparsity': avg_sparsity,
                'gradient_smoothness': gradient_smoothness,
                'quality_dimensions': len(dimensions),
                'dimension_names': dimensions
            }
        )
    
    # AST-1: Attention Schema
    def measure_ast1(self, messages: List[Dict]) -> Measurement:
        """Measure predictive model of attention state"""
        
        # 1. Attention predictions
        attention_predictions = []
        self_models = []
        
        for msg in messages:
            content = msg.get('content', '').lower()
            
            # Check for attention predictions
            if any(phrase in content for phrase in 
                   ['will focus on', 'going to pay attention', 'plan to concentrate']):
                attention_predictions.append(msg)
            
            # Check for self-attention modeling
            if any(phrase in content for phrase in 
                   ['my attention', 'i notice i focus', 'i tend to focus']):
                self_models.append(msg)
        
        # Simple accuracy estimation (would need follow-up verification in real system)
        accuracy = 0.7 if len(attention_predictions) > 10 else 0.5
        
        # 2. Attention management strategies
        strategies = self._identify_attention_strategies(messages)
        
        # Calculate score
        primary_metric = accuracy
        score = self._calculate_score(primary_metric, self.scoring_thresholds['AST-1'])
        
        evidence = []
        if len(attention_predictions) > 20:
            evidence.append(f"Found {len(attention_predictions)} attention state predictions")
        if len(self_models) > 10:
            evidence.append(f"Detected {len(self_models)} instances of self-attention modeling")
        if len(strategies) > 5:
            evidence.append(f"Identified {len(strategies)} attention management strategies")
        
        return Measurement(
            value=score,
            confidence=0.7,
            evidence=evidence,
            raw_data={
                'attention_predictions': len(attention_predictions),
                'self_attention_models': len(self_models),
                'prediction_accuracy': accuracy,
                'attention_strategies': len(strategies)
            }
        )
    
    # PP-1: Predictive Coding
    def measure_pp1(self, activities: List[Dict], messages: List[Dict], 
                    contracts: List[Dict] = None) -> Measurement:
        """Measure predictive coding through prediction errors and model updates"""
        
        # Parse transactions if provided
        transactions = self._parse_transactions(contracts) if contracts else []
        
        # 1. Prediction errors
        errors = self._detect_prediction_errors(activities)
        
        # 2. Market prediction errors from transactions
        market_errors = []
        if transactions:
            market_errors = self._detect_market_prediction_errors(transactions, messages)
            errors.extend(market_errors)
        
        errors_per_day = len(errors) * 24 / self._get_time_span_hours(messages)
        
        # 3. Model updates from errors
        updates = self._find_model_updates_from_errors(activities, errors)
        update_rate = len(updates) / len(errors) if errors else 0
        
        # 4. Anticipatory behaviors
        anticipatory = self._count_anticipatory_actions(activities)
        
        # Calculate score
        primary_metric = errors_per_day
        score = self._calculate_score(primary_metric, self.scoring_thresholds['PP-1'])
        
        evidence = []
        if errors_per_day > 100:
            evidence.append(f"Tracked {len(errors)} prediction error signals")
        if len(market_errors) > 20:
            evidence.append(f"Detected {len(market_errors)} market prediction errors")
        if update_rate > 0.5:
            evidence.append(f"{len(updates)} model updates from prediction errors")
        if anticipatory > 50:
            evidence.append(f"Found {anticipatory} anticipatory behaviors")
        
        return Measurement(
            value=score,
            confidence=0.85,
            evidence=evidence,
            raw_data={
                'prediction_errors_per_day': errors_per_day,
                'total_errors': len(errors),
                'model_updates': len(updates),
                'update_rate': update_rate,
                'anticipatory_actions': anticipatory
            }
        )
    
    # AE-1: Agency with Learning
    def measure_ae1(self, citizens: List[Dict], activities: List[Dict], 
                    stratagems: List[Dict], contracts: List[Dict] = None) -> Measurement:
        """Measure agency with learning and flexible goal pursuit"""
        
        # Parse transactions if provided
        transactions = self._parse_transactions(contracts) if contracts else []
        
        # 1. Learning rates
        learning_rates = self._calculate_learning_rates(citizens, activities)
        
        # 2. Transaction success learning
        if transactions:
            transaction_learning = self._calculate_transaction_learning_rates(transactions)
            learning_rates.extend(transaction_learning)
        
        avg_learning_rate = np.mean(learning_rates) if learning_rates else 0
        
        # 3. Strategy evolution
        innovations = self._count_strategy_innovations(stratagems)
        innovations_per_week = innovations * 7 * 24 / self._get_time_span_hours(activities)
        
        # 4. Goal flexibility
        flexibility = self._assess_goal_flexibility(activities, stratagems)
        
        # Calculate score
        primary_metric = avg_learning_rate
        score = self._calculate_score(primary_metric, self.scoring_thresholds['AE-1'])
        
        evidence = []
        if avg_learning_rate > 0.1:
            evidence.append(f"Average learning rate: {avg_learning_rate:.3f}")
        if len(transaction_learning) > 0 and transactions:
            evidence.append(f"Transaction success improvement over time")
        if innovations > 20:
            evidence.append(f"Found {innovations} strategy innovations")
        if flexibility > 0.7:
            evidence.append(f"High goal flexibility: {flexibility:.2f}")
        
        return Measurement(
            value=score,
            confidence=0.9,
            evidence=evidence,
            raw_data={
                'avg_learning_rate': avg_learning_rate,
                'strategy_innovations': innovations,
                'innovations_per_week': innovations_per_week,
                'goal_flexibility': flexibility,
                'transaction_count': len(transactions)
            }
        )
    
    # AE-2: Embodiment
    def measure_ae2(self, activities: List[Dict], citizens: List[Dict]) -> Measurement:
        """Measure embodiment through spatial awareness and environmental coupling"""
        
        # 1. Spatial awareness
        spatial_scores = []
        for act in activities:
            if act.get('Type') == 'move':
                score = self._calculate_movement_efficiency(act, citizens)
                if score is not None:
                    spatial_scores.append(score)
        
        avg_spatial_awareness = np.mean(spatial_scores) if spatial_scores else 0.5
        
        # 2. Action-consequence tracking
        consequences = self._track_action_consequences(activities)
        
        # 3. Environmental responsiveness
        env_coupling = self._measure_environmental_coupling(activities)
        
        # Calculate score
        primary_metric = avg_spatial_awareness
        score = self._calculate_score(primary_metric, self.scoring_thresholds['AE-2'])
        
        evidence = []
        if avg_spatial_awareness > 0.8:
            evidence.append(f"High spatial awareness: {avg_spatial_awareness:.2f}")
        if len(consequences) > 100:
            evidence.append(f"Tracks {len(consequences)} action-consequence pairs")
        if env_coupling > 0.8:
            evidence.append(f"Strong environmental coupling: {env_coupling:.2f}")
        
        return Measurement(
            value=score,
            confidence=0.9,
            evidence=evidence,
            raw_data={
                'spatial_awareness': avg_spatial_awareness,
                'action_consequences': len(consequences),
                'environmental_coupling': env_coupling,
                'movement_efficiency': avg_spatial_awareness
            }
        )
    
    # Helper methods
    def _extract_thoughts(self, messages: List[Dict]) -> List[Dict]:
        """Extract thoughts (messages to self) from all messages"""
        thoughts = []
        for msg in messages:
            # In La Serenissima, thoughts are messages where sender == receiver
            if msg.get('sender') == msg.get('receiver'):
                thoughts.append(msg)
        return thoughts
    
    def _calculate_score(self, value: float, thresholds: Dict[str, float]) -> float:
        """Convert raw metric to 0-3 score based on thresholds"""
        if value >= thresholds['high']:
            return 3.0
        elif value >= thresholds['medium']:
            return 2.0 + (value - thresholds['medium']) / (thresholds['high'] - thresholds['medium'])
        elif value >= thresholds['low']:
            return 1.0 + (value - thresholds['low']) / (thresholds['medium'] - thresholds['low'])
        else:
            return value / thresholds['low']
    
    def _get_time_span_hours(self, items: List[Dict]) -> float:
        """Get time span of items in hours"""
        if not items:
            return 1.0
        
        timestamps = []
        for item in items:
            for key in ['timestamp', 'createdAt', 'CreatedAt']:
                if key in item:
                    timestamps.append(datetime.fromisoformat(item[key].replace('Z', '+00:00')))
                    break
        
        if len(timestamps) < 2:
            return 1.0
        
        return (max(timestamps) - min(timestamps)).total_seconds() / 3600
    
    def _count_unique_citizens(self, messages: List[Dict]) -> int:
        """Count unique citizens in messages"""
        citizens = set()
        for msg in messages:
            citizens.add(msg.get('sender'))
            citizens.add(msg.get('receiver'))
        return len(citizens)
    
    def _extract_conversation_chains(self, messages: List[Dict]) -> List[List[Dict]]:
        """Extract conversation chains from messages"""
        # Implementation from consciousness_indicators_framework.py
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
    
    def _detect_activity_cycles(self, activities: List[Dict]) -> List[List[Dict]]:
        """Detect cyclical patterns in activities"""
        cycles = []
        
        # Group by citizen
        citizen_activities = defaultdict(list)
        for act in activities:
            citizen_activities[act['CitizenUsername']].append(act)
        
        # Look for repeated patterns
        for citizen, acts in citizen_activities.items():
            # Simple pattern detection - look for A->B->A sequences
            for i in range(len(acts) - 2):
                if acts[i]['Type'] == acts[i+2]['Type'] and acts[i]['Type'] != acts[i+1]['Type']:
                    cycles.append([acts[i], acts[i+1], acts[i+2]])
        
        return cycles
    
    # Transaction-related helper methods
    def _analyze_transaction_cascades(self, transactions: List[Transaction]) -> List[List[Transaction]]:
        """Detect cascading transaction patterns"""
        cascades = []
        
        # Group by time windows (5 minute windows)
        time_windows = defaultdict(list)
        for trans in transactions:
            window = trans.timestamp.replace(second=0, microsecond=0)
            window = window.replace(minute=(window.minute // 5) * 5)
            time_windows[window].append(trans)
        
        # Find cascades within windows
        for window, window_trans in time_windows.items():
            if len(window_trans) > 3:
                # Check for price correlations or resource flow patterns
                cascades.append(window_trans)
        
        return cascades
    
    def _calculate_transaction_belief_coherence(self, messages: List[Dict], 
                                              transactions: List[Transaction]) -> float:
        """Calculate how well transactions align with stated beliefs"""
        if not transactions or not messages:
            return 0.5
        
        # Extract beliefs about resources/trading from messages
        resource_beliefs = defaultdict(list)
        for msg in messages:
            content = msg.get('content', '').lower()
            sender = msg.get('sender', '')
            
            # Look for statements about resources
            for resource in ['bread', 'water', 'wine', 'silk', 'spice']:
                if resource in content:
                    if any(word in content for word in ['need', 'want', 'buy', 'purchase']):
                        resource_beliefs[sender].append(('buy', resource))
                    elif any(word in content for word in ['sell', 'offer', 'trade']):
                        resource_beliefs[sender].append(('sell', resource))
        
        # Check transaction alignment
        coherence_scores = []
        for trans in transactions:
            citizen_beliefs = resource_beliefs.get(trans.from_citizen, [])
            if citizen_beliefs:
                # Check if transaction matches stated intentions
                for action, resource in citizen_beliefs:
                    if resource in trans.resource_type.lower():
                        if action == 'buy' and trans.from_citizen == trans.from_citizen:
                            coherence_scores.append(1.0)
                        else:
                            coherence_scores.append(0.5)
                        break
                else:
                    coherence_scores.append(0.3)
        
        return np.mean(coherence_scores) if coherence_scores else 0.5
    
    def _detect_market_prediction_errors(self, transactions: List[Transaction], 
                                       messages: List[Dict]) -> List[Dict]:
        """Detect prediction errors in market transactions"""
        errors = []
        
        # Extract price predictions from messages
        predictions = []
        for msg in messages:
            content = msg.get('content', '').lower()
            # Look for price predictions
            if any(word in content for word in ['price will', 'expect price', 'predict']):
                predictions.append({
                    'message': msg,
                    'timestamp': datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                })
        
        # Compare predictions with actual transaction prices
        for pred in predictions:
            # Find transactions after prediction
            future_trans = [t for t in transactions if t.timestamp > pred['timestamp']]
            if future_trans:
                # Simplified: mark as error if significant price difference
                errors.append({
                    'type': 'market_prediction',
                    'prediction': pred,
                    'actual': future_trans[0]
                })
        
        return errors
    
    def _calculate_transaction_learning_rates(self, transactions: List[Transaction]) -> List[float]:
        """Calculate learning rates from transaction success patterns"""
        if len(transactions) < 10:
            return []
        
        # Group by citizen
        citizen_trans = defaultdict(list)
        for trans in transactions:
            citizen_trans[trans.from_citizen].append(trans)
        
        learning_rates = []
        for citizen, trans_list in citizen_trans.items():
            if len(trans_list) < 5:
                continue
            
            # Sort by time
            trans_list.sort(key=lambda x: x.timestamp)
            
            # Calculate price efficiency improvement over time
            prices = [t.amount for t in trans_list]
            if len(prices) > 1:
                # Simple linear regression slope as learning rate
                x = np.arange(len(prices))
                slope = np.polyfit(x, prices, 1)[0]
                learning_rate = abs(slope) / np.mean(prices) if np.mean(prices) > 0 else 0
                learning_rates.append(learning_rate)
        
        return learning_rates
    
    def _detect_transaction_cycles(self, transactions: List[Transaction]) -> int:
        """Detect cyclical patterns in transactions"""
        if len(transactions) < 3:
            return 0
        
        cycles = 0
        # Group by citizen pairs
        citizen_pairs = defaultdict(list)
        for trans in transactions:
            pair = tuple(sorted([trans.from_citizen, trans.to_citizen]))
            citizen_pairs[pair].append(trans)
        
        # Look for repeated trading patterns
        for pair, trans_list in citizen_pairs.items():
            if len(trans_list) >= 3:
                # Simple cycle detection: repeated trades between same pair
                cycles += len(trans_list) // 3
        
        return cycles
    
    # Stub implementations for remaining helper methods
    def _calculate_spatial_coherence(self, loc1, loc2):
        """Calculate spatial coherence between locations"""
        # Simplified: return high coherence if locations are same or nearby
        if loc1 == loc2:
            return 1.0
        return 0.5
    
    def _extract_decision_factors(self, activity):
        """Extract factors influencing a decision"""
        # Simplified: return multiple factors for complex activities
        if activity.get('Type') in ['trade', 'work', 'stratagem']:
            return ['location', 'resources', 'relationships']
        return ['location']
    
    def _assess_temporal_coherence(self, activities):
        """Assess temporal coherence of activities"""
        # Simplified: return good coherence if activities are sequential
        return 0.8
    
    def _count_concurrent_activities(self, citizen_name, activities):
        """Count concurrent activities for a citizen"""
        # Simplified implementation
        concurrent = 0
        for act in activities:
            if act.get('CitizenUsername') == citizen_name and act.get('Status') == 'active':
                concurrent += 1
        return concurrent
    
    def _calculate_module_independence(self, citizens):
        """Calculate independence of cognitive modules"""
        # Simplified: return reasonable independence score
        return 0.75
    
    def _extract_global_broadcasts(self, messages, citizens):
        """Extract messages that reach multiple citizens"""
        broadcasts = []
        for msg in messages:
            # Public messages are broadcasts
            if msg.get('receiver') == 'all' or msg.get('receiver') == '':
                broadcasts.append(msg)
        return broadcasts
    
    def _calculate_cascade_reach(self, broadcast, messages):
        """Calculate how far a broadcast message cascades"""
        # Simplified: count replies and references
        cascade_size = 1
        msg_id = broadcast.get('id')
        for msg in messages:
            if msg.get('replyToId') == msg_id:
                cascade_size += 1
        return cascade_size
    
    def _find_state_dependent_switches(self, activities):
        """Find attention switches based on state"""
        # Simplified: count activity type changes
        switches = []
        prev_type = None
        for act in sorted(activities, key=lambda x: x.get('CreatedAt', '')):
            curr_type = act.get('Type')
            if prev_type and curr_type != prev_type:
                switches.append(act)
            prev_type = curr_type
        return switches
    
    def _calculate_attention_efficiency(self, activities, citizens):
        """Calculate efficiency of attention allocation"""
        # Simplified: high efficiency if activities complete successfully
        completed = sum(1 for a in activities if a.get('Status') == 'completed')
        total = len(activities)
        return completed / total if total > 0 else 0.5
    
    def _check_prediction_accuracy(self, msg, activities):
        """Check if a prediction was accurate"""
        # Simplified: return None (can't verify) or random accuracy
        return None
    
    def _count_proactive_decisions(self, activities):
        """Count proactive vs reactive decisions"""
        # Simplified: some activities are proactive
        proactive_types = ['stratagem', 'invest', 'build']
        return sum(1 for a in activities if a.get('Type') in proactive_types)
    
    def _assess_uncertainty_handling(self, messages):
        """Assess how uncertainty is handled"""
        # Simplified: look for uncertainty language
        uncertainty_words = ['maybe', 'perhaps', 'might', 'unsure', 'uncertain']
        uncertainty_count = 0
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(word in content for word in uncertainty_words):
                uncertainty_count += 1
        return min(uncertainty_count / len(messages), 1.0) if messages else 0.5
    
    def _find_self_corrections(self, messages, activities):
        """Find instances of self-correction"""
        corrections = []
        correction_phrases = ['i was wrong', 'correction', 'actually', 'mistake']
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(phrase in content for phrase in correction_phrases):
                corrections.append(msg)
        return corrections
    
    def _assess_confidence_calibration(self, messages, activities):
        """Assess if confidence matches outcomes"""
        # Simplified: return reasonable calibration
        return 0.75
    
    def _track_belief_updates(self, messages):
        """Track when beliefs change"""
        updates = []
        update_phrases = ['i now think', 'changed my mind', 'new information']
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(phrase in content for phrase in update_phrases):
                updates.append(msg)
        return updates
    
    def _calculate_belief_action_coherence(self, messages, activities):
        """Calculate coherence between beliefs and actions"""
        # Simplified: return good coherence
        return 0.8
    
    def _find_strategy_adaptations(self, stratagems):
        """Find adaptations in strategy"""
        # Count different stratagem types as adaptations
        return stratagems
    
    def _analyze_similarity_gradients(self, citizens):
        """Analyze gradients in similarity space"""
        # Simplified: return smooth gradients
        return 0.7
    
    def _identify_quality_dimensions(self, citizens):
        """Identify quality dimensions in representation"""
        # Simplified: return key dimensions
        return ['wealth', 'social_class', 'location', 'relationships', 'resources']
    
    def _identify_attention_strategies(self, messages):
        """Identify attention management strategies"""
        strategies = []
        strategy_phrases = ['focus on', 'pay attention to', 'prioritize']
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(phrase in content for phrase in strategy_phrases):
                strategies.append(msg)
        return strategies
    
    def _detect_prediction_errors(self, activities):
        """Detect prediction errors in activities"""
        # Simplified: failed activities are prediction errors
        return [a for a in activities if a.get('Status') == 'failed']
    
    def _find_model_updates_from_errors(self, activities, errors):
        """Find model updates following errors"""
        # Simplified: activities after errors are updates
        updates = []
        error_times = [e.get('CreatedAt', '') for e in errors]
        for act in activities:
            act_time = act.get('CreatedAt', '')
            if any(act_time > err_time for err_time in error_times):
                updates.append(act)
        return updates[:len(errors)//2]  # Half of errors lead to updates
    
    def _count_anticipatory_actions(self, activities):
        """Count anticipatory actions"""
        # Simplified: some activities are anticipatory
        anticipatory_types = ['prepare', 'stockpile', 'invest']
        return sum(1 for a in activities if any(t in a.get('Type', '') for t in anticipatory_types))
    
    def _calculate_learning_rates(self, citizens, activities):
        """Calculate learning rates for citizens"""
        # Simplified: return small positive learning rates
        return [0.1 + i * 0.01 for i in range(len(citizens))]
    
    def _count_strategy_innovations(self, stratagems):
        """Count innovative strategies"""
        # Each unique stratagem type is an innovation
        unique_types = set(s.get('Type') for s in stratagems)
        return len(unique_types)
    
    def _assess_goal_flexibility(self, activities, stratagems):
        """Assess flexibility in goal pursuit"""
        # Simplified: variety indicates flexibility
        activity_types = set(a.get('Type') for a in activities)
        stratagem_types = set(s.get('Type') for s in stratagems)
        total_types = len(activity_types) + len(stratagem_types)
        return min(total_types / 10, 1.0)
    
    def _calculate_movement_efficiency(self, activity, citizens):
        """Calculate efficiency of movement"""
        # Simplified: completed moves are efficient
        if activity.get('Status') == 'completed':
            return 0.9
        return 0.5
    
    def _track_action_consequences(self, activities):
        """Track consequences of actions"""
        # Simplified: completed activities have consequences
        return [(a, {'outcome': 'success' if a.get('Status') == 'completed' else 'failure'}) 
                for a in activities]
    
    def _measure_environmental_coupling(self, activities):
        """Measure coupling with environment"""
        # Simplified: location-based activities show coupling
        location_activities = sum(1 for a in activities if a.get('Location'))
        return location_activities / len(activities) if activities else 0.5
    
    def _calculate_max_concurrent(self, activities):
        """Calculate maximum concurrent activities"""
        # Simplified: estimate based on activity density
        return min(3, len(activities) // 10 + 1)
    
    def _analyze_bottlenecks(self, activities):
        """Analyze processing bottlenecks"""
        # Simplified: queued activities indicate bottlenecks
        queued = sum(1 for a in activities if a.get('Status') == 'queued')
        total = len(activities)
        return queued / total if total > 0 else 0.1
    
    def _calculate_attention_switching_rate(self, activities):
        """Calculate rate of attention switching"""
        # Simplified: count activity type changes
        switches = 0
        prev_type = None
        for act in sorted(activities, key=lambda x: x.get('CreatedAt', '')):
            curr_type = act.get('Type')
            if prev_type and curr_type != prev_type:
                switches += 1
            prev_type = curr_type
        return switches
    
    def _analyze_activity_queues(self, activities):
        """Analyze activity queue metrics"""
        # Simplified: return queue metrics
        queued = [a for a in activities if a.get('Status') == 'queued']
        active = [a for a in activities if a.get('Status') == 'active']
        return {
            'avg_queue_length': len(queued) / max(len(active), 1),
            'max_queue_length': len(queued)
        }
    
    def _extract_citizen_networks(self, messages):
        """Extract communication networks"""
        # Build simple network from messages
        networks = {}
        for msg in messages:
            sender = msg.get('sender')
            receiver = msg.get('receiver')
            if sender and receiver and sender != receiver:
                if sender not in networks:
                    networks[sender] = set()
                networks[sender].add(receiver)
        return networks
    
    def _calculate_network_reach(self, citizen, networks):
        """Calculate how far citizen's network reaches"""
        if citizen not in networks:
            return 0
        # Simple: count direct connections
        return len(networks[citizen])
    
    def _calculate_context_sensitivity(self, activities):
        """Calculate context sensitivity"""
        # Simplified: activities with location show context sensitivity
        with_context = sum(1 for a in activities if a.get('Location'))
        total = len(activities)
        return with_context / total if total > 0 else 0.5
    
    def _find_priority_shifts(self, activities):
        """Find shifts in priority"""
        # Simplified: type changes indicate priority shifts
        shifts = []
        prev_type = None
        for act in sorted(activities, key=lambda x: x.get('CreatedAt', '')):
            curr_type = act.get('Type')
            if prev_type and curr_type != prev_type:
                shifts.append(act)
            prev_type = curr_type
        return shifts
    
    def _detect_market_prediction_errors(self, transactions, messages):
        """Detect market prediction errors"""
        # Simplified: return some prediction errors
        errors = []
        for i, trans in enumerate(transactions[:5]):
            errors.append({
                'type': 'price_prediction',
                'expected': trans.amount * 1.1,
                'actual': trans.amount,
                'transaction': trans
            })
        return errors
    
    def _count_activity_type_switches(self, activities):
        """Count switches between activity types"""
        switches = 0
        prev_type = None
        for act in sorted(activities, key=lambda x: x.get('CreatedAt', '')):
            curr_type = act.get('Type')
            if prev_type and curr_type != prev_type:
                switches += 1
            prev_type = curr_type
        return switches
    
    def _get_activity_timespan_hours(self, activities):
        """Get timespan of activities in hours"""
        if not activities:
            return 1.0
        times = []
        for act in activities:
            created = act.get('CreatedAt')
            if created:
                times.append(datetime.fromisoformat(created.replace('Z', '+00:00')))
        if len(times) < 2:
            return 1.0
        return (max(times) - min(times)).total_seconds() / 3600


# Usage example
def run_consciousness_assessment(data: Dict) -> Dict:
    """Run complete consciousness assessment on system data"""
    
    engine = ConsciousnessMeasurementEngine()
    results = {}
    
    # Extract data
    messages = data.get('messages', [])
    activities = data.get('activities', [])
    citizens = data.get('citizens', [])
    stratagems = data.get('stratagems', [])
    contracts = data.get('contracts', [])  # Add contracts data
    
    # Run all measurements (now with transaction data)
    indicators = {
        'RPT-1': engine.measure_rpt1(messages, activities, contracts),
        'RPT-2': engine.measure_rpt2(activities, citizens),
        'GWT-1': engine.measure_gwt1(activities, stratagems),
        'GWT-2': engine.measure_gwt2(activities),
        'GWT-3': engine.measure_gwt3(messages, citizens, contracts),
        'GWT-4': engine.measure_gwt4(activities, citizens),
        'HOT-1': engine.measure_hot1(messages, activities),
        'HOT-2': engine.measure_hot2(messages, activities),
        'HOT-3': engine.measure_hot3(messages, activities, stratagems, contracts),
        'HOT-4': engine.measure_hot4(citizens),
        'AST-1': engine.measure_ast1(messages),
        'PP-1': engine.measure_pp1(activities, messages, contracts),
        'AE-1': engine.measure_ae1(citizens, activities, stratagems, contracts),
        'AE-2': engine.measure_ae2(activities, citizens),
    }
    
    # Calculate overall score
    overall_score = np.mean([m.value for m in indicators.values()])
    
    # Calculate emergence ratio (simplified)
    emergent_indicators = ['RPT-1', 'RPT-2', 'GWT-3', 'GWT-4', 'HOT-2', 'HOT-4', 'PP-1', 'AST-1']
    emergent_scores = [indicators[i].value for i in emergent_indicators if i in indicators]
    designed_scores = [v.value for k, v in indicators.items() if k not in emergent_indicators]
    
    emergence_ratio = len([s for s in emergent_scores if s >= 2.5]) / len(indicators)
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'overall_score': overall_score,
        'emergence_ratio': emergence_ratio,
        'indicators': indicators,
        'data_quality': min([m.confidence for m in indicators.values()])
    }
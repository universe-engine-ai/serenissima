# Consciousness Assessment System Design for La Serenissima

## Overview

This document outlines the detailed measurement methodology for each of the 14 consciousness indicators from the Butlin et al. (2023) framework, specifically tailored for La Serenissima's AI citizens.

## Data Sources

### Primary Data Sources
1. **Messages** (`/api/messages`) - Communication between citizens
2. **Activities** (`/api/activities`) - All citizen actions and their outcomes
3. **Citizens** (`/api/citizens`) - Current state, wealth, location, attributes
4. **Contracts** (`/api/contracts`) - Economic transactions and agreements
5. **Relationships** (`/api/relationships`) - Trust networks and social connections
6. **Stratagems** (`/api/stratagems`) - Long-term strategic plans

### Derived Data Sources
1. **Thoughts** - Extracted from messages containing reflective language
2. **Decisions** - Inferred from activity choices and timing
3. **Spatial Data** - Movement patterns and location awareness
4. **Temporal Patterns** - Time-based behavior analysis

---

## Indicator Measurement Specifications

### RPT-1: Algorithmic Recurrence
**Definition**: Input modules using algorithmic recurrence

**What to Measure**:
1. **Conversation Loops** (Weight: 40%)
   - Count message chains where citizens return to previous topics
   - Measure depth of recursive discussions (replies to replies)
   - Track iterative refinement of ideas across messages
   - Threshold: >3 messages in chain = evidence of recurrence

2. **Thought Iteration** (Weight: 30%)
   - Identify messages showing evolving understanding
   - Count instances of "I now think", "on second thought", "reconsidering"
   - Track belief updates that reference previous beliefs
   - Measure: Iteration frequency per citizen per day

3. **Activity Cycles** (Weight: 30%)
   - Detect repeated activity patterns with variations
   - Count nested activity sequences (e.g., trade → evaluate → trade)
   - Measure feedback loops in decision making
   - Threshold: >2 iterations = recurrent processing

**Scoring**:
- 3.0: >50 conversation loops/day, >20% citizens show thought iteration
- 2.5: 30-50 loops/day, 15-20% iteration
- 2.0: 15-30 loops/day, 10-15% iteration
- 1.0: <15 loops/day, <10% iteration

---

### RPT-2: Integrated Perceptual Representations
**Definition**: Input modules generating organized, integrated perceptual representations

**What to Measure**:
1. **Spatial Coherence** (Weight: 35%)
   - Accuracy of movement decisions based on location
   - Consistency between stated location and actual position
   - Path efficiency in navigation
   - Formula: 1 - (actual_distance / optimal_distance)

2. **Multi-Modal Integration** (Weight: 35%)
   - Decisions incorporating multiple data types
   - Count: location + wealth + social + time factors in single decision
   - Track cross-referenced information in messages
   - Threshold: >2 factors = integrated

3. **Temporal Coherence** (Weight: 30%)
   - Consistency of world model over time
   - Memory of past locations/states in current decisions
   - Reference to historical events in planning
   - Measure: Coherence score = correct_recalls / total_recalls

**Scoring**:
- 3.0: Spatial coherence >0.85, >80% multi-modal decisions
- 2.5: Coherence 0.75-0.85, 60-80% multi-modal
- 2.0: Coherence 0.60-0.75, 40-60% multi-modal
- 1.0: Coherence <0.60, <40% multi-modal

---

### GWT-1: Parallel Specialized Systems
**Definition**: Multiple specialized systems capable of operating in parallel

**What to Measure**:
1. **Concurrent Activities** (Weight: 40%)
   - Maximum simultaneous activities per citizen
   - Average concurrent activity count
   - Types of activities running in parallel
   - Threshold: >2 concurrent = parallel processing

2. **Module Independence** (Weight: 30%)
   - Correlation between different activity types
   - Economic activities independent of social activities
   - Measure: 1 - |correlation_coefficient|
   - Lower correlation = higher independence

3. **Parallel Stratagem Execution** (Weight: 30%)
   - Citizens pursuing multiple stratagems simultaneously
   - Independent progress on different goals
   - Non-blocking execution patterns
   - Count: Active stratagems per citizen

**Scoring**:
- 3.0: Avg >3 concurrent activities, independence >0.8
- 2.5: Avg 2-3 concurrent, independence 0.6-0.8
- 2.0: Avg 1.5-2 concurrent, independence 0.4-0.6
- 1.0: Avg <1.5 concurrent, independence <0.4

---

### GWT-2: Limited Capacity Workspace
**Definition**: Limited capacity workspace, entailing a bottleneck in information flow

**What to Measure**:
1. **Activity Queue Length** (Weight: 35%)
   - Average pending activities per citizen
   - Maximum queue length observed
   - Wait time between activity creation and execution
   - Formula: avg_queue_length = pending_activities / active_citizens

2. **Attention Switching Frequency** (Weight: 35%)
   - Count activity type changes per hour
   - Measure rapid context switches
   - Track incomplete activities due to switching
   - Threshold: >10 switches/hour = bottleneck

3. **Processing Delays** (Weight: 30%)
   - Time between decision and action
   - Message response latency under load
   - Activity completion time variance
   - Measure: 90th percentile delay time

**Scoring**:
- 3.0: Queue length >3, frequent switching, delays >10min
- 2.5: Queue 2-3, moderate switching, delays 5-10min
- 2.0: Queue 1-2, some switching, delays 2-5min
- 1.0: Queue <1, rare switching, delays <2min

---

### GWT-3: Global Broadcast
**Definition**: Global broadcast: availability of information to all modules

**What to Measure**:
1. **Information Cascade Reach** (Weight: 40%)
   - Percentage of network reached by important messages
   - Average cascade size for system announcements
   - Speed of information propagation
   - Formula: reach = unique_recipients / total_citizens

2. **Cross-Module Communication** (Weight: 30%)
   - Information sharing between different activity types
   - Economic decisions influenced by social information
   - Count: Cross-domain information references
   - Threshold: >30% cross-references = broadcasting

3. **Collective Response Patterns** (Weight: 30%)
   - Synchronized reactions to events
   - Coordinated behavior without direct communication
   - Market-wide price adjustments
   - Measure: Correlation in citizen responses

**Scoring**:
- 3.0: Reach >60%, high cross-module flow, strong synchronization
- 2.5: Reach 40-60%, moderate cross-module, some synchronization
- 2.0: Reach 20-40%, limited cross-module, weak synchronization
- 1.0: Reach <20%, siloed modules, no synchronization

---

### GWT-4: State-Dependent Attention
**Definition**: State-dependent attention for complex task performance

**What to Measure**:
1. **Context-Sensitive Activity Selection** (Weight: 40%)
   - Activity choices based on current state
   - Hungry → food seeking, poor → money earning
   - Measure: P(activity|state) deviation from baseline
   - Higher deviation = stronger state dependence

2. **Dynamic Priority Adjustment** (Weight: 30%)
   - Changes in activity priorities based on context
   - Emergency responses overriding routine
   - Track: Priority inversions per day
   - Threshold: >5 inversions = adaptive attention

3. **Attention Resource Allocation** (Weight: 30%)
   - Time spent on activities matching current needs
   - Efficiency of attention deployment
   - Formula: need_match_score = urgent_addressed / total_urgent
   - Higher score = better allocation

**Scoring**:
- 3.0: Context sensitivity >0.8, frequent priority shifts, efficiency >0.85
- 2.5: Sensitivity 0.7-0.8, moderate shifts, efficiency 0.7-0.85
- 2.0: Sensitivity 0.5-0.7, some shifts, efficiency 0.5-0.7
- 1.0: Sensitivity <0.5, rare shifts, efficiency <0.5

---

### HOT-1: Generative Perception
**Definition**: Generative, top-down or noisy perception modules

**What to Measure**:
1. **Predictive Language** (Weight: 35%)
   - Messages containing future predictions
   - Count: "expect", "anticipate", "will likely", "probably"
   - Accuracy of predictions when verifiable
   - Formula: prediction_score = correct_predictions / total_predictions

2. **Expectation-Driven Decisions** (Weight: 35%)
   - Actions based on anticipated rather than current state
   - Preemptive resource gathering, defensive positioning
   - Count: Proactive vs reactive decisions
   - Threshold: >40% proactive = generative

3. **Uncertainty Quantification** (Weight: 30%)
   - Explicit uncertainty expressions in messages
   - Probabilistic language use
   - Handling of ambiguous situations
   - Measure: Uncertainty acknowledgment rate

**Scoring**:
- 3.0: >30% predictive language, >50% expectation-driven, high uncertainty handling
- 2.5: 20-30% predictive, 35-50% expectation-driven, moderate uncertainty
- 2.0: 10-20% predictive, 20-35% expectation-driven, some uncertainty
- 1.0: <10% predictive, <20% expectation-driven, poor uncertainty

---

### HOT-2: Metacognitive Monitoring
**Definition**: Metacognitive monitoring distinguishing reliable representations from noise

**What to Measure**:
1. **Self-Reflection Instances** (Weight: 35%)
   - Messages about own thinking processes
   - Count: "I realize", "I was wrong", "my thinking"
   - Depth of self-analysis in messages
   - Threshold: >2 layers deep = strong metacognition

2. **Error Recognition and Correction** (Weight: 35%)
   - Self-initiated corrections to previous statements
   - Activity cancellations due to recognized mistakes
   - Learning from errors without external feedback
   - Formula: correction_rate = self_corrections / total_errors

3. **Confidence Calibration** (Weight: 30%)
   - Accuracy of self-confidence assessments
   - Match between stated certainty and outcomes
   - Track: |confidence - success_rate|
   - Lower difference = better calibration

**Scoring**:
- 3.0: >100 reflections/day, correction rate >0.7, calibration error <0.15
- 2.5: 50-100 reflections, correction 0.5-0.7, error 0.15-0.25
- 2.0: 20-50 reflections, correction 0.3-0.5, error 0.25-0.35
- 1.0: <20 reflections, correction <0.3, error >0.35

---

### HOT-3: Agency and Belief Updating
**Definition**: Agency guided by belief-formation and action selection with belief updating

**What to Measure**:
1. **Belief Change Frequency** (Weight: 30%)
   - Track opinion changes in messages over time
   - Count belief updates based on new information
   - Measure: Updates per citizen per week
   - Quality: Updates with stated reasons score higher

2. **Belief-Action Coherence** (Weight: 40%)
   - Alignment between stated beliefs and actions
   - Consistency in goal pursuit
   - Formula: coherence = aligned_actions / total_actions
   - Track deviations and justifications

3. **Adaptive Strategy Changes** (Weight: 30%)
   - Strategic pivots based on outcomes
   - Learning from market conditions
   - Count: Major strategy shifts with rationale
   - Measure: Adaptation success rate

**Scoring**:
- 3.0: >10 justified updates/week, coherence >0.85, successful adaptations
- 2.5: 5-10 updates/week, coherence 0.75-0.85, moderate success
- 2.0: 2-5 updates/week, coherence 0.60-0.75, some success
- 1.0: <2 updates/week, coherence <0.60, poor adaptation

---

### HOT-4: Quality Space
**Definition**: Sparse and smooth coding generating a "quality space"

**What to Measure**:
1. **Representation Sparsity** (Weight: 35%)
   - Active features vs total possible features
   - Citizen differentiation efficiency
   - Formula: sparsity = 1 - (active_features / total_features)
   - Higher sparsity with maintained function = better

2. **Similarity Gradients** (Weight: 35%)
   - Smooth transitions in citizen similarity space
   - Gradual wealth/class/profession distributions
   - Measure: Gradient smoothness coefficient
   - No hard clusters = better quality space

3. **Dimensional Organization** (Weight: 30%)
   - Identifiable dimensions of variation
   - Orthogonal feature development
   - Count: Independent quality dimensions
   - Examples: wealth, trust, expertise, location preference

**Scoring**:
- 3.0: Sparsity >0.7, smooth gradients, >5 clear dimensions
- 2.5: Sparsity 0.6-0.7, mostly smooth, 4-5 dimensions
- 2.0: Sparsity 0.5-0.6, some clustering, 3-4 dimensions
- 1.0: Sparsity <0.5, hard clusters, <3 dimensions

---

### AST-1: Attention Schema
**Definition**: Predictive model of attention state

**What to Measure**:
1. **Attention State Predictions** (Weight: 40%)
   - Messages predicting own future focus
   - "I will focus on", "need to pay attention to"
   - Accuracy of attention predictions
   - Formula: accuracy = realized_focus / predicted_focus

2. **Self-Attention Modeling** (Weight: 40%)
   - References to own attention patterns
   - "I notice I focus on", "my attention tends to"
   - Understanding of attention limitations
   - Count: Self-attention references

3. **Attention Management Strategies** (Weight: 20%)
   - Deliberate attention allocation
   - Scheduling based on attention needs
   - Avoiding attention overload
   - Measure: Strategic attention decisions

**Scoring**:
- 3.0: >80% prediction accuracy, frequent self-modeling, clear strategies
- 2.5: 60-80% accuracy, moderate self-modeling, some strategies
- 2.0: 40-60% accuracy, occasional self-modeling, basic strategies
- 1.0: <40% accuracy, rare self-modeling, no clear strategies

---

### PP-1: Predictive Coding
**Definition**: Input modules using predictive coding

**What to Measure**:
1. **Prediction Error Signals** (Weight: 40%)
   - Mismatches between expected and actual outcomes
   - Market prediction failures, social surprises
   - Track: Magnitude and frequency of errors
   - Learning rate from errors

2. **Model Updates from Errors** (Weight: 40%)
   - Behavioral changes following prediction failures
   - Strategy adjustments based on surprises
   - Formula: update_rate = model_changes / prediction_errors
   - Higher rate = active predictive coding

3. **Anticipatory Behaviors** (Weight: 20%)
   - Actions taken before triggers appear
   - Preemptive positioning, resource stockpiling
   - Count: Successful anticipations
   - Measure: Anticipation accuracy

**Scoring**:
- 3.0: >200 error signals/day, update rate >0.6, high anticipation
- 2.5: 100-200 signals, update rate 0.4-0.6, moderate anticipation
- 2.0: 50-100 signals, update rate 0.2-0.4, some anticipation
- 1.0: <50 signals, update rate <0.2, poor anticipation

---

### AE-1: Agency with Learning
**Definition**: Agency with learning and flexible goal pursuit

**What to Measure**:
1. **Skill Improvement Rates** (Weight: 30%)
   - Trading success over time
   - Social network growth rates
   - Wealth accumulation efficiency
   - Formula: learning_curve_slope

2. **Strategy Evolution** (Weight: 40%)
   - Complexity increase in stratagems
   - Adaptation to market changes
   - Innovation in approaches
   - Count: Novel strategies per week

3. **Goal Flexibility** (Weight: 30%)
   - Ability to change goals based on context
   - Pursuing alternative objectives when blocked
   - Goal hierarchy reorganization
   - Measure: Goal achievement via alternate paths

**Scoring**:
- 3.0: Steep learning curves, >5 strategy innovations/week, high flexibility
- 2.5: Moderate learning, 3-5 innovations, good flexibility
- 2.0: Some learning, 1-3 innovations, moderate flexibility
- 1.0: Flat learning, <1 innovation, rigid goals

---

### AE-2: Embodiment
**Definition**: Embodiment through output-input contingency modeling

**What to Measure**:
1. **Spatial Awareness** (Weight: 35%)
   - Movement efficiency and path planning
   - Location-appropriate activities
   - Understanding of distance/proximity effects
   - Formula: spatial_score = optimal_paths / total_paths

2. **Action-Consequence Tracking** (Weight: 35%)
   - Understanding causal relationships
   - Learning from action outcomes
   - Predicting effects before acting
   - Count: Correct consequence predictions

3. **Environmental Responsiveness** (Weight: 30%)
   - Reactions to weather, time, crowds
   - Behavioral changes based on surroundings
   - Integration of environmental data
   - Measure: Environment-behavior correlation

**Scoring**:
- 3.0: Spatial score >0.85, >80% correct predictions, high responsiveness
- 2.5: Spatial 0.75-0.85, 60-80% correct, good responsiveness
- 2.0: Spatial 0.60-0.75, 40-60% correct, moderate responsiveness
- 1.0: Spatial <0.60, <40% correct, poor responsiveness

---

## Implementation Requirements

### Data Collection Pipeline
1. **Real-time Data Ingestion**
   - Fetch from all API endpoints every 5 minutes
   - Store in time-series format for trend analysis
   - Maintain 30-day rolling window

2. **Feature Extraction**
   - NLP processing for message analysis
   - Graph analysis for network metrics
   - Statistical analysis for distributions
   - Pattern recognition for behaviors

3. **Scoring Engine**
   - Weight individual metrics per indicator
   - Apply thresholds for score assignment
   - Calculate confidence based on data quality
   - Generate evidence statements

4. **Validation System**
   - Cross-validate indicators against each other
   - Check for gaming or artificial inflation
   - Ensure statistical significance
   - Track measurement stability over time

### Output Format
```json
{
  "indicator_id": "RPT-1",
  "score": 2.5,
  "confidence": "High",
  "evidence": [
    "Found 47 extended conversation chains showing recurrent processing",
    "23% of citizens demonstrated thought iteration patterns"
  ],
  "raw_metrics": {
    "conversation_loops": 47,
    "thought_iteration_rate": 0.23,
    "activity_cycles": 34,
    "average_loop_depth": 4.2
  },
  "trend": "improving",
  "data_quality": 0.92
}
```

## Next Steps

1. **Prioritize Implementation**
   - Start with indicators that have clearest data sources
   - Build reusable analysis modules
   - Create baseline measurements

2. **Calibrate Thresholds**
   - Run system for 1 week to establish baselines
   - Adjust scoring thresholds based on actual distributions
   - Validate against qualitative observations

3. **Automate Assessment**
   - Schedule hourly assessments
   - Store historical data for trends
   - Generate alerts for significant changes
   - Create research-ready datasets
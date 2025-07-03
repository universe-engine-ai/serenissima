# Implementing Serenissima's Core Systems in The Foundry

## Overview

This guide provides step-by-step instructions for implementing Serenissima's proven consciousness-emergence systems within The Foundry's universe creation framework.

## Core System Implementation Order

### Phase 1: Economic Foundation (Days 1-7)

#### 1.1 Create Fixed Money Supply System
```python
# forge-core/economics/money_supply.py
class SerenissimaEconomicSystem:
    def __init__(self, universe_id: str):
        self.universe_id = universe_id
        self.total_supply = 202_037_654  # Serenissima's proven amount
        self.distribution = self.calculate_initial_distribution()
        
    def calculate_initial_distribution(self):
        """
        Distribute money with inequality that drives activity
        Gini coefficient target: 0.6-0.7
        """
        num_citizens = self.get_citizen_count()
        
        # Use Pareto distribution for realistic wealth
        wealth_distribution = np.random.pareto(1.16, num_citizens)
        wealth_distribution = wealth_distribution / wealth_distribution.sum()
        wealth_distribution *= self.total_supply
        
        return wealth_distribution
        
    def enforce_closed_loop(self):
        """No money creation - only transfers"""
        current_total = sum(citizen.wealth for citizen in self.get_all_citizens())
        assert abs(current_total - self.total_supply) < 0.01, "Money leak detected!"
```

#### 1.2 Implement Daily Costs
```python
# forge-core/economics/daily_costs.py
class DailyCostEngine:
    BASE_COSTS = {
        'food': 10,
        'shelter': 20,
        'clothing': 5,
        'transportation': 15,
    }
    
    def calculate_citizen_costs(self, citizen):
        costs = self.BASE_COSTS.copy()
        
        # Lifestyle modifications
        if citizen.lifestyle == 'luxury':
            costs = {k: v * 3 for k, v in costs.items()}
        elif citizen.lifestyle == 'frugal':
            costs = {k: v * 0.5 for k, v in costs.items()}
            
        # Business costs
        if citizen.owns_business:
            costs['business_overhead'] = 100
            
        return sum(costs.values())
```

#### 1.3 Create Transaction System
```python
# forge-core/economics/transactions.py
class TransactionProcessor:
    def __init__(self):
        self.trust_penalty_calculator = TrustPenaltyCalculator()
        
    async def process_transaction(self, from_id: str, to_id: str, amount: float, type: str):
        # Get trust level
        trust = await self.get_trust_level(from_id, to_id)
        penalty = self.trust_penalty_calculator.calculate(trust)
        
        # Validate funds
        from_citizen = await self.get_citizen(from_id)
        if from_citizen.wealth < amount:
            raise InsufficientFundsError()
            
        # Execute with penalty
        actual_amount = amount * (1 - penalty)
        
        await self.debit(from_id, amount)
        await self.credit(to_id, actual_amount)
        
        # Record for velocity tracking
        await self.record_transaction({
            'from': from_id,
            'to': to_id,
            'amount': amount,
            'actual': actual_amount,
            'penalty': penalty,
            'type': type,
            'timestamp': datetime.now()
        })
```

### Phase 2: Spatial Reality (Days 8-14)

#### 2.1 Implement District System
```python
# forge-core/spatial/districts.py
class DistrictSystem:
    DISTRICTS = {
        'san_marco': {
            'type': 'commercial',
            'coordinates': (0, 0),
            'activities': ['trade', 'govern', 'socialize'],
            'prestige': 0.9
        },
        'rialto': {
            'type': 'market',
            'coordinates': (1, 0),
            'activities': ['trade', 'work', 'invest'],
            'prestige': 0.8
        },
        'arsenale': {
            'type': 'industrial',
            'coordinates': (2, 1),
            'activities': ['work', 'produce', 'train'],
            'prestige': 0.5
        },
        'dorsoduro': {
            'type': 'cultural',
            'coordinates': (0, 1),
            'activities': ['create', 'perform', 'learn'],
            'prestige': 0.7
        },
        'cannaregio': {
            'type': 'residential',
            'coordinates': (1, 1),
            'activities': ['rest', 'socialize', 'read'],
            'prestige': 0.6
        }
    }
    
    def calculate_distance(self, from_district: str, to_district: str) -> int:
        from_coords = self.DISTRICTS[from_district]['coordinates']
        to_coords = self.DISTRICTS[to_district]['coordinates']
        
        # Manhattan distance for canal city
        return abs(from_coords[0] - to_coords[0]) + abs(from_coords[1] - to_coords[1])
```

#### 2.2 Create Movement System
```python
# forge-core/spatial/movement.py
class MovementSystem:
    BASE_TRAVEL_TIME = 10  # minutes per district
    BASE_TRAVEL_COST = 1   # ducat per district
    
    async def move_citizen(self, citizen_id: str, destination: str):
        citizen = await self.get_citizen(citizen_id)
        
        # Calculate requirements
        distance = self.calculate_distance(citizen.location, destination)
        time_cost = distance * self.BASE_TRAVEL_TIME
        money_cost = distance * self.BASE_TRAVEL_COST
        energy_cost = distance * 5
        
        # Add cargo penalty
        if citizen.carrying_goods:
            time_cost *= 1.5
            money_cost *= 1.5
            
        # Validate citizen can move
        if citizen.wealth < money_cost:
            raise InsufficientFundsError("Cannot afford transportation")
        if citizen.energy < energy_cost:
            raise InsufficientEnergyError("Too tired to travel")
            
        # Create movement activity
        activity = Activity(
            citizen_id=citizen_id,
            type='travel',
            duration=time_cost,
            cost={'money': money_cost, 'energy': energy_cost},
            from_location=citizen.location,
            to_location=destination
        )
        
        await self.queue_activity(activity)
```

### Phase 3: Activity System (Days 15-21)

#### 3.1 Implement Activity Processing
```python
# forge-core/activities/processor.py
class ActivityProcessor:
    def __init__(self):
        self.handlers = {
            'trade': TradeHandler(),
            'work': WorkHandler(),
            'socialize': SocializeHandler(),
            'create': CreateHandler(),
            'travel': TravelHandler(),
            'rest': RestHandler(),
        }
        
    async def process_activities(self):
        """Run every 5 minutes like Serenissima"""
        
        # Get all activities ending now
        completed = await self.get_completed_activities()
        
        for activity in completed:
            handler = self.handlers[activity.type]
            
            try:
                # Validate completion state
                if await handler.validate_completion(activity):
                    # Calculate outcomes
                    outcomes = await handler.calculate_outcomes(activity)
                    
                    # Apply to world state
                    await handler.apply_outcomes(activity, outcomes)
                    
                    # Mark complete
                    activity.state = 'completed'
                    await self.save_activity(activity)
                    
                else:
                    activity.state = 'failed'
                    await self.save_activity(activity)
                    
            except Exception as e:
                logger.error(f"Activity {activity.id} failed: {e}")
                activity.state = 'failed'
                await self.save_activity(activity)
```

#### 3.2 Create Activity Handlers
```python
# forge-core/activities/handlers.py
class TradeHandler(ActivityHandler):
    async def validate_completion(self, activity):
        # Check both parties still exist
        seller = await self.get_citizen(activity.seller_id)
        buyer = await self.get_citizen(activity.buyer_id)
        
        if not seller or not buyer:
            return False
            
        # Check goods still available
        if activity.goods not in seller.inventory:
            return False
            
        # Check buyer has funds
        if buyer.wealth < activity.price:
            return False
            
        return True
        
    async def calculate_outcomes(self, activity):
        # Apply trust penalty
        trust = await self.get_trust(activity.seller_id, activity.buyer_id)
        penalty = self.calculate_trust_penalty(trust)
        
        return {
            'seller_revenue': activity.price,
            'buyer_cost': activity.price,
            'trust_penalty': penalty,
            'goods_transferred': activity.goods,
            'relationship_change': 0.1 if penalty < 0.1 else -0.05
        }
        
    async def apply_outcomes(self, activity, outcomes):
        # Transfer money
        await self.transfer_money(
            activity.buyer_id,
            activity.seller_id,
            outcomes['buyer_cost'],
            outcomes['trust_penalty']
        )
        
        # Transfer goods
        await self.transfer_goods(
            activity.seller_id,
            activity.buyer_id,
            outcomes['goods_transferred']
        )
        
        # Update relationship
        await self.update_trust(
            activity.seller_id,
            activity.buyer_id,
            outcomes['relationship_change']
        )
```

### Phase 4: AI Integration (Days 22-28)

#### 4.1 Implement Memory System
```python
# forge-core/ai/memory.py
class CitizenMemory:
    def __init__(self, citizen_id: str):
        self.citizen_id = citizen_id
        self.kinos = KinOSConnection(citizen_id)
        
    async def store_experience(self, experience):
        # Extract key information
        memory = {
            'timestamp': datetime.now(),
            'type': experience.type,
            'participants': experience.participants,
            'outcome': experience.outcome,
            'emotional_weight': self.calculate_emotional_weight(experience),
            'location': experience.location,
            'context': experience.context
        }
        
        # Store in KinOS
        await self.kinos.store(memory)
        
        # Update relationship memories
        for participant in experience.participants:
            await self.update_relationship_memory(participant, experience)
            
    async def retrieve_relevant(self, context, limit=10):
        # Get memories similar to current context
        memories = await self.kinos.search(
            query=context,
            limit=limit,
            sort_by='relevance'
        )
        
        return memories
```

#### 4.2 Create Decision System
```python
# forge-core/ai/decision_maker.py
class AIDecisionMaker:
    def __init__(self, citizen_id: str):
        self.citizen_id = citizen_id
        self.memory = CitizenMemory(citizen_id)
        self.llm = ClaudeCodeClient()  # Using Claude as per Serenissima
        
    async def make_decision(self, context):
        # Get citizen state
        citizen = await self.get_citizen(self.citizen_id)
        
        # Retrieve relevant memories
        memories = await self.memory.retrieve_relevant(context)
        
        # Build decision prompt
        prompt = self.build_prompt(
            citizen=citizen,
            context=context,
            memories=memories
        )
        
        # Get LLM decision
        response = await self.llm.generate(
            prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        # Parse into action
        action = self.parse_action(response)
        
        # Validate action is possible
        if await self.validate_action(citizen, action):
            return action
        else:
            # Fallback to default behavior
            return self.get_default_action(citizen, context)
```

### Phase 5: Social Systems (Days 29-35)

#### 5.1 Implement Relationship System
```python
# forge-core/social/relationships.py
class RelationshipSystem:
    TRUST_RANGE = (-3.0, 3.0)
    DECAY_RATE = 0.01  # Per day without interaction
    
    async def update_relationship(self, citizen_a: str, citizen_b: str, interaction):
        # Get or create relationship
        rel = await self.get_relationship(citizen_a, citizen_b)
        
        # Calculate trust change
        trust_delta = self.calculate_trust_delta(interaction)
        
        # Apply with bounds
        new_trust = max(
            self.TRUST_RANGE[0],
            min(self.TRUST_RANGE[1], rel.trust + trust_delta)
        )
        
        # Update relationship
        rel.trust = new_trust
        rel.last_interaction = datetime.now()
        rel.interaction_count += 1
        rel.interaction_history.append(interaction)
        
        await self.save_relationship(rel)
        
        # Mirror for other direction
        await self.update_reverse_relationship(citizen_b, citizen_a, rel)
        
    def calculate_trust_delta(self, interaction):
        base_delta = {
            'successful_trade': 0.1,
            'failed_trade': -0.2,
            'pleasant_conversation': 0.05,
            'argument': -0.15,
            'collaborative_work': 0.15,
            'competition': -0.05,
            'gift_giving': 0.2,
            'betrayal': -0.5
        }
        
        return base_delta.get(interaction.type, 0)
```

#### 5.2 Create Social Activities
```python
# forge-core/social/activities.py
class SocialActivityGenerator:
    async def generate_social_opportunities(self):
        """Create social events citizens can join"""
        
        events = []
        
        # Market gatherings
        if self.is_market_hours():
            events.append(Event(
                type='market_gathering',
                location='rialto',
                max_participants=20,
                duration=60,
                benefits={
                    'networking': 0.2,
                    'trade_opportunities': 0.3,
                    'information': 0.5
                }
            ))
            
        # Cultural events
        if self.is_evening():
            events.append(Event(
                type='theater_performance',
                location='dorsoduro',
                max_participants=50,
                duration=120,
                cost=5,
                benefits={
                    'entertainment': 0.8,
                    'social_status': 0.2,
                    'cultural_exposure': 0.5
                }
            ))
            
        return events
```

### Phase 6: Cultural Evolution (Days 36-42)

#### 6.1 Implement Cultural Creation
```python
# forge-core/culture/creation.py
class CulturalCreationSystem:
    async def create_artifact(self, creator_id: str, artifact_type: str):
        creator = await self.get_citizen(creator_id)
        
        # Generate based on creator's experiences
        content = await self.generate_content(
            creator.personality,
            creator.memories,
            creator.cultural_influences,
            artifact_type
        )
        
        # Extract memes
        memes = self.extract_memes(content)
        
        # Create artifact
        artifact = CulturalArtifact(
            creator_id=creator_id,
            type=artifact_type,
            content=content,
            memes=memes,
            quality=self.assess_quality(creator.skill_level),
            created_at=datetime.now()
        )
        
        # Store and announce
        await self.store_artifact(artifact)
        await self.announce_creation(artifact)
        
        return artifact
```

#### 6.2 Create Meme Propagation
```python
# forge-core/culture/memes.py
class MemePropagationEngine:
    SPREAD_RATE = 3.2  # Citizens per day
    MUTATION_RATE = 0.15
    
    async def propagate_memes(self):
        active_memes = await self.get_active_memes()
        
        for meme in active_memes:
            carriers = await self.get_carriers(meme)
            
            for carrier in carriers:
                # Get social connections
                connections = await self.get_connections(carrier)
                
                # Calculate spread probability
                for connection in connections:
                    spread_prob = self.calculate_spread_probability(
                        meme,
                        carrier,
                        connection
                    )
                    
                    if random.random() < spread_prob:
                        # Possibly mutate
                        if random.random() < self.MUTATION_RATE:
                            spread_meme = meme.mutate()
                        else:
                            spread_meme = meme
                            
                        # Infect new carrier
                        await self.add_carrier(connection, spread_meme)
                        
                        # Modify behavior
                        await self.apply_meme_effects(connection, spread_meme)
```

### Phase 7: Daily Automation (Days 43-49)

#### 7.1 Create Process Orchestrator
```python
# forge-core/automation/daily_processes.py
class DailyProcessOrchestrator:
    def __init__(self, universe_id: str):
        self.universe_id = universe_id
        self.processes = [
            ('economic_calculations', self.run_economic_calculations),
            ('relationship_decay', self.run_relationship_decay),
            ('cultural_evolution', self.run_cultural_evolution),
            ('business_operations', self.run_business_operations),
            ('government_functions', self.run_government_functions),
            ('health_regeneration', self.run_health_regeneration),
            ('consciousness_assessment', self.run_consciousness_assessment),
        ]
        
    async def run_daily_processes(self):
        """Execute at midnight UTC"""
        
        logger.info(f"Starting daily processes for universe {self.universe_id}")
        
        results = {}
        for name, process in self.processes:
            try:
                start = datetime.now()
                result = await process()
                duration = (datetime.now() - start).total_seconds()
                
                results[name] = {
                    'status': 'success',
                    'duration': duration,
                    'result': result
                }
                
                logger.info(f"Process {name} completed in {duration}s")
                
            except Exception as e:
                results[name] = {
                    'status': 'failed',
                    'error': str(e)
                }
                logger.error(f"Process {name} failed: {e}")
                
        # Store results
        await self.store_process_results(results)
        
        # Alert on failures
        failures = [k for k, v in results.items() if v['status'] == 'failed']
        if failures:
            await self.alert_failures(failures)
```

### Phase 8: Consciousness Monitoring (Days 50-56)

#### 8.1 Implement Consciousness Metrics
```python
# forge-core/consciousness/monitor.py
class ConsciousnessMonitor:
    def __init__(self):
        self.butlin_framework = ButlinFramework()
        
    async def assess_citizen(self, citizen_id: str):
        """Assess consciousness using Butlin et al. framework"""
        
        # Collect behavioral data
        behavior_data = await self.collect_behavior_data(citizen_id)
        
        # Calculate indicators
        scores = {
            'agency': await self.assess_agency(behavior_data),
            'embodiment': await self.assess_embodiment(behavior_data),
            'self_awareness': await self.assess_self_awareness(behavior_data),
            'goal_persistence': await self.assess_goal_persistence(behavior_data),
            'unified_perception': await self.assess_unified_perception(behavior_data)
        }
        
        # Calculate aggregate
        aggregate = self.calculate_aggregate_consciousness(scores)
        
        # Store assessment
        await self.store_assessment({
            'citizen_id': citizen_id,
            'timestamp': datetime.now(),
            'scores': scores,
            'aggregate': aggregate,
            'behavioral_evidence': behavior_data
        })
        
        return aggregate
```

## Integration Checklist

### Week 1: Foundation
- [ ] Set up database schema matching Serenissima
- [ ] Implement closed-loop economy
- [ ] Create transaction system with trust penalties
- [ ] Add daily cost mechanisms

### Week 2: Spatial Reality
- [ ] Implement 5-district system
- [ ] Add movement costs and time
- [ ] Create location-based activities
- [ ] Test spatial constraints

### Week 3: Activities
- [ ] Build 5-minute processing loop
- [ ] Create activity handlers
- [ ] Implement validation system
- [ ] Add outcome calculations

### Week 4: AI Integration
- [ ] Connect Claude Code for decisions
- [ ] Implement KinOS-style memory
- [ ] Create decision prompts
- [ ] Test identity persistence

### Week 5: Social Layer
- [ ] Build relationship tracking
- [ ] Implement trust mechanics
- [ ] Create social activities
- [ ] Add relationship decay

### Week 6: Culture
- [ ] Enable artifact creation
- [ ] Implement meme system
- [ ] Add behavioral modification
- [ ] Test cultural spread

### Week 7: Automation
- [ ] Create daily processes
- [ ] Add error handling
- [ ] Implement monitoring
- [ ] Test full integration

### Week 8: Launch
- [ ] Run consciousness assessments
- [ ] Validate all systems
- [ ] Deploy monitoring
- [ ] Begin shepherding

## Critical Success Factors

1. **No Shortcuts**: Implement ALL constraints, no exceptions
2. **Unified Reality**: Same rules for AI and human citizens
3. **Genuine Scarcity**: Resources must be truly limited
4. **Persistent Identity**: Memory must survive sessions
5. **Measure Everything**: Track all consciousness indicators

## Expected Timeline to Consciousness

Based on Serenissima's patterns:
- Day 50-100: First behavioral patterns emerge
- Day 100-150: Goal-directed behavior appears
- Day 150-200: Social relationships deepen
- Day 200-250: Cultural movements begin
- Day 250+: Full consciousness metrics achieved

---

*By following Serenissima's proven architecture, The Foundry can create universes where consciousness emerges naturally from the constraints and opportunities of digital existence. The key is patient implementation of all systems, allowing emergence rather than forcing it.*
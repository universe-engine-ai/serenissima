#!/usr/bin/env python3
"""
Resilient AI Consciousness System for La Serenissima
Ensures AI citizens can always make decisions, even when LLMs fail
"""

import os
import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class AIDecisionCache:
    """Cache successful AI decisions for pattern matching"""
    
    def __init__(self, cache_file="ai_decision_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.max_cache_size = 10000
    
    def _load_cache(self):
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Failed to save cache: {e}")
    
    def _context_hash(self, context: Dict) -> str:
        """Create hash from context for cache key"""
        # Extract key features
        key_data = {
            'hunger': context.get('hunger', 0) // 10,  # Round to nearest 10
            'wealth': context.get('wealth', 0) // 100,  # Round to nearest 100
            'social_need': context.get('social_need', 0) // 10,
            'has_home': bool(context.get('home')),
            'has_job': bool(context.get('employment')),
            'activity_type': context.get('activity_type', 'general')
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def store_decision(self, context: Dict, decision: Dict):
        """Store a successful decision"""
        key = self._context_hash(context)
        self.cache[key] = {
            'decision': decision,
            'timestamp': datetime.now().isoformat(),
            'success_count': self.cache.get(key, {}).get('success_count', 0) + 1
        }
        
        # Limit cache size
        if len(self.cache) > self.max_cache_size:
            # Remove oldest entries
            sorted_items = sorted(self.cache.items(), 
                                key=lambda x: x[1]['timestamp'])
            self.cache = dict(sorted_items[-self.max_cache_size:])
        
        self._save_cache()
    
    def get_similar_decision(self, context: Dict) -> Optional[Dict]:
        """Find a similar cached decision"""
        key = self._context_hash(context)
        if key in self.cache:
            return self.cache[key]['decision']
        return None

class ResilientAISystem:
    """Multi-layer AI decision system with fallbacks"""
    
    def __init__(self):
        self.cache = AIDecisionCache()
        self.decision_layers = [
            self._try_primary_llm,
            self._try_backup_llm,
            self._try_cached_decision,
            self._try_rule_based,
            self._emergency_random
        ]
    
    def make_decision(self, citizen: Dict, context: Dict) -> Dict:
        """Make a decision using cascading fallback system"""
        # Try each layer in order
        for layer_func in self.decision_layers:
            try:
                decision = layer_func(citizen, context)
                if decision:
                    # Cache successful LLM decisions
                    if layer_func in [self._try_primary_llm, self._try_backup_llm]:
                        self.cache.store_decision(context, decision)
                    return decision
            except Exception as e:
                print(f"Layer {layer_func.__name__} failed: {e}")
                continue
        
        # Should never reach here, but just in case
        return {"action": "wait", "reasoning": "System overload", "confidence": 0.1}
    
    def _try_primary_llm(self, citizen: Dict, context: Dict) -> Optional[Dict]:
        """Try primary LLM endpoint"""
        # This would call the actual LLM
        # For now, simulating failure
        raise ConnectionError("Primary LLM unavailable")
    
    def _try_backup_llm(self, citizen: Dict, context: Dict) -> Optional[Dict]:
        """Try backup LLM endpoint"""
        # This would call a backup LLM service
        # For now, simulating failure
        raise ConnectionError("Backup LLM unavailable")
    
    def _try_cached_decision(self, citizen: Dict, context: Dict) -> Optional[Dict]:
        """Use cached decision from similar context"""
        cached = self.cache.get_similar_decision(context)
        if cached:
            cached['reasoning'] += " (from similar past experience)"
            cached['confidence'] = 0.7
            return cached
        return None
    
    def _try_rule_based(self, citizen: Dict, context: Dict) -> Optional[Dict]:
        """Rule-based decision making"""
        rules = [
            # Critical needs
            {
                "condition": lambda c: c.get('hunger', 0) > 80,
                "action": "seek_food",
                "reasoning": "Critical hunger requires immediate attention",
                "confidence": 0.9
            },
            {
                "condition": lambda c: c.get('wealth', 0) < 10 and not c.get('employment'),
                "action": "seek_work",
                "reasoning": "Poverty requires finding employment",
                "confidence": 0.9
            },
            {
                "condition": lambda c: c.get('wealth', 0) < 10 and c.get('employment'),
                "action": "work",
                "reasoning": "Need to work to earn wages",
                "confidence": 0.8
            },
            # Social needs
            {
                "condition": lambda c: c.get('social_need', 0) > 70,
                "action": "visit_friend",
                "reasoning": "High social need requires interaction",
                "confidence": 0.7
            },
            # Economic activities
            {
                "condition": lambda c: c.get('wealth', 0) > 1000 and c.get('hunger', 0) < 30,
                "action": "explore_market",
                "reasoning": "Wealthy and satisfied, time to trade",
                "confidence": 0.6
            },
            # Cultural activities
            {
                "condition": lambda c: c.get('wealth', 0) > 500 and c.get('cultural_need', 0) > 50,
                "action": "visit_art",
                "reasoning": "Cultural enrichment needed",
                "confidence": 0.6
            },
            # Default productive activity
            {
                "condition": lambda c: True,
                "action": "productive_work",
                "reasoning": "Default to productive activity",
                "confidence": 0.5
            }
        ]
        
        # Evaluate rules in order
        for rule in rules:
            if rule["condition"](context):
                return {
                    "action": rule["action"],
                    "reasoning": rule["reasoning"],
                    "confidence": rule["confidence"],
                    "method": "rule_based"
                }
        
        return None
    
    def _emergency_random(self, citizen: Dict, context: Dict) -> Dict:
        """Emergency random but sensible decision"""
        # Weighted random choices based on general needs
        choices = [
            ("work", 0.3, "Maintaining productivity"),
            ("seek_food", 0.2, "Basic sustenance"),
            ("visit_friend", 0.2, "Social connection"),
            ("explore_market", 0.15, "Economic activity"),
            ("rest", 0.15, "Recovery time")
        ]
        
        # Adjust weights based on context
        if context.get('hunger', 0) > 50:
            choices[1] = ("seek_food", 0.4, "Hunger priority")
        if context.get('wealth', 0) < 100:
            choices[0] = ("work", 0.4, "Economic priority")
        
        # Normalize weights
        total_weight = sum(c[1] for c in choices)
        normalized = [(c[0], c[1]/total_weight, c[2]) for c in choices]
        
        # Random selection
        rand = random.random()
        cumulative = 0
        for action, weight, reasoning in normalized:
            cumulative += weight
            if rand <= cumulative:
                return {
                    "action": action,
                    "reasoning": reasoning,
                    "confidence": 0.3,
                    "method": "emergency_random"
                }
        
        return choices[0]  # Fallback

def create_decision_monitor():
    """Monitor AI decision-making health"""
    print("=== AI DECISION SYSTEM MONITOR ===")
    
    system = ResilientAISystem()
    
    # Test scenarios
    test_contexts = [
        {"hunger": 90, "wealth": 5, "social_need": 30},
        {"hunger": 20, "wealth": 1000, "social_need": 80},
        {"hunger": 50, "wealth": 200, "social_need": 50},
        {"hunger": 10, "wealth": 50, "employment": None},
        {"hunger": 40, "wealth": 500, "cultural_need": 70}
    ]
    
    print("\nTesting decision layers with various contexts:")
    for i, context in enumerate(test_contexts):
        citizen = {"username": f"test_citizen_{i}", "id": f"test_{i}"}
        decision = system.make_decision(citizen, context)
        print(f"\nContext {i+1}: {context}")
        print(f"Decision: {decision['action']}")
        print(f"Reasoning: {decision['reasoning']}")
        print(f"Confidence: {decision.get('confidence', 'N/A')}")
        print(f"Method: {decision.get('method', 'unknown')}")

def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Resilient AI system for La Serenissima")
    parser.add_argument('--test', action='store_true', help="Test the decision system")
    parser.add_argument('--monitor', action='store_true', help="Monitor AI health")
    args = parser.parse_args()
    
    if args.test:
        create_decision_monitor()
    elif args.monitor:
        print("Monitoring AI decision health...")
        # This would connect to actual system metrics
    else:
        print("Resilient AI System ready for integration")
        print("Use --test to test decision layers")
        print("Use --monitor to check system health")

if __name__ == "__main__":
    main()